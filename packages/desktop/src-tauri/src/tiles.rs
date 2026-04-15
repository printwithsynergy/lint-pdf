//! Viewer-tile fetcher with durable disk cache.
//!
//! The engine serves whole-page rasters at a caller-chosen DPI via a
//! handful of endpoints:
//!
//! - `/api/v1/viewer/jobs/{job}/pages/{page}/tile?dpi=N`
//! - `/api/v1/viewer/jobs/{job}/pages/{page}/channel/{channel}?dpi=N`
//! - `/api/v1/viewer/jobs/{job}/pages/{page}/tac-heatmap?dpi=N&tac_limit=L`
//!
//! These are raw PNG bytes. They're expensive to render on the engine
//! (on-demand fallback goes through Ghostscript, ~500ms–2s). We cache
//! every successful response on disk keyed by endpoint-specific inputs
//! so subsequent reads are instant, and the user can open the viewer
//! offline if they've already seen the page.
//!
//! Cache layout (under `{data_dir}/lintpdf-desktop/tiles/{job_id}/`):
//!   - `p{page}-dpi{dpi}-base.png`
//!   - `p{page}-dpi{dpi}-ch-{channel}.png`   (channel is url-sanitized)
//!   - `p{page}-dpi{dpi}-tac{limit}.png`
//!
//! The cache has a configurable byte budget (default 1 GB) and prunes
//! oldest-accessed files first on crossing the ceiling.

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use crate::config::ConfigManager;
use crate::connectivity::ConnectivityState;

/// Default cache budget in bytes (1 GiB).
const DEFAULT_CACHE_BUDGET: u64 = 1024 * 1024 * 1024;

/// Returns the tiles directory, creating it if necessary.
fn tiles_root() -> PathBuf {
    let dir = dirs::data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("lintpdf-desktop")
        .join("tiles");
    std::fs::create_dir_all(&dir).ok();
    dir
}

fn job_dir(job_id: &str) -> PathBuf {
    // Strip anything that could escape the tiles root. Engine gives us
    // UUIDs in practice but we defend anyway.
    let safe: String = job_id
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '-' || *c == '_')
        .collect();
    let dir = tiles_root().join(safe);
    std::fs::create_dir_all(&dir).ok();
    dir
}

/// Make a cache filename safe: url-encode characters that aren't
/// portable across filesystems. Spot colours like "PANTONE 485 C"
/// need this.
fn sanitize(component: &str) -> String {
    component
        .chars()
        .map(|c| match c {
            'A'..='Z' | 'a'..='z' | '0'..='9' | '-' | '_' => c,
            _ => '_',
        })
        .collect()
}

/// Key describing a single cached tile.
#[derive(Debug, Clone)]
pub enum TileKey {
    Base {
        job_id: String,
        page: u32,
        dpi: u32,
    },
    Channel {
        job_id: String,
        page: u32,
        dpi: u32,
        channel: String,
    },
    TacHeatmap {
        job_id: String,
        page: u32,
        dpi: u32,
        tac_limit: u32,
    },
}

impl TileKey {
    fn job_id(&self) -> &str {
        match self {
            Self::Base { job_id, .. }
            | Self::Channel { job_id, .. }
            | Self::TacHeatmap { job_id, .. } => job_id,
        }
    }

    fn file_name(&self) -> String {
        match self {
            Self::Base { page, dpi, .. } => format!("p{}-dpi{}-base.png", page, dpi),
            Self::Channel {
                page, dpi, channel, ..
            } => format!("p{}-dpi{}-ch-{}.png", page, dpi, sanitize(channel)),
            Self::TacHeatmap {
                page,
                dpi,
                tac_limit,
                ..
            } => format!("p{}-dpi{}-tac{}.png", page, dpi, tac_limit),
        }
    }

    fn cache_path(&self) -> PathBuf {
        job_dir(self.job_id()).join(self.file_name())
    }

    fn endpoint_url(&self, base_url: &str) -> String {
        let base = base_url.trim_end_matches('/');
        match self {
            Self::Base { job_id, page, dpi } => format!(
                "{}/api/v1/viewer/jobs/{}/pages/{}/tile?dpi={}",
                base, job_id, page, dpi
            ),
            Self::Channel {
                job_id,
                page,
                dpi,
                channel,
            } => format!(
                "{}/api/v1/viewer/jobs/{}/pages/{}/channel/{}?dpi={}",
                base,
                job_id,
                page,
                urlencoding::encode(channel),
                dpi
            ),
            Self::TacHeatmap {
                job_id,
                page,
                dpi,
                tac_limit,
            } => format!(
                "{}/api/v1/viewer/jobs/{}/pages/{}/tac-heatmap?dpi={}&tac_limit={}",
                base, job_id, page, dpi, tac_limit
            ),
        }
    }
}

/// Result surfaced back to the UI: the absolute local path where the
/// tile now lives on disk. Tauri can serve it via the custom
/// `asset://` protocol. Also includes the byte size for UI telemetry.
#[derive(Debug, serde::Serialize)]
pub struct TileResult {
    pub path: String,
    pub bytes: u64,
    pub from_cache: bool,
}

/// Fetch a tile, honouring the disk cache. Blocks until the bytes are
/// on disk (fast: ~50-100ms for a cache hit on NVMe, reads are
/// already memory-mapped by the OS).
pub async fn fetch_tile(
    key: TileKey,
    config_mgr: Arc<ConfigManager>,
    connectivity: ConnectivityState,
) -> Result<TileResult, String> {
    let path = key.cache_path();
    if path.exists() {
        // Touch atime by re-reading metadata — LRU prune keys off
        // mtime-or-atime depending on platform. Good enough.
        let meta = std::fs::metadata(&path).map_err(|e| format!("stat cache: {}", e))?;
        let _ = filetime::set_file_atime(
            &path,
            filetime::FileTime::from_system_time(std::time::SystemTime::now()),
        );
        return Ok(TileResult {
            path: path.to_string_lossy().to_string(),
            bytes: meta.len(),
            from_cache: true,
        });
    }

    if !connectivity.is_online() {
        return Err("Offline — tile not in cache.".to_string());
    }

    let config = config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = key.endpoint_url(&config.base_url);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|e| format!("build client: {}", e))?;

    let resp = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .send()
        .await
        .map_err(|e| format!("tile HTTP: {}", e))?;

    if resp.status() == reqwest::StatusCode::UNAUTHORIZED
        || resp.status() == reqwest::StatusCode::FORBIDDEN
    {
        connectivity.record_auth_failure();
    }

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        let snippet: String = body.chars().take(200).collect();
        return Err(format!("tile API {}: {}", status, snippet));
    }

    let bytes = resp
        .bytes()
        .await
        .map_err(|e| format!("read tile body: {}", e))?;

    // Write to a temp file then rename atomically, so a crashed write
    // never leaves a corrupt cache entry.
    let tmp = path.with_extension("png.tmp");
    tokio::fs::write(&tmp, &bytes)
        .await
        .map_err(|e| format!("write tile: {}", e))?;
    tokio::fs::rename(&tmp, &path)
        .await
        .map_err(|e| format!("rename tile: {}", e))?;

    connectivity.record_auth_success();

    // Fire-and-forget prune if the cache has grown past budget.
    let budget = DEFAULT_CACHE_BUDGET;
    tokio::spawn(async move {
        if let Err(e) = prune_to_budget(&tiles_root(), budget) {
            log::warn!("tile cache prune: {}", e);
        }
    });

    Ok(TileResult {
        path: path.to_string_lossy().to_string(),
        bytes: bytes.len() as u64,
        from_cache: false,
    })
}

/// Enumerate the cache, drop oldest-atime files until total bytes <=
/// `budget`. Walks one job directory at a time so partial failures
/// don't wedge the whole cache.
fn prune_to_budget(root: &Path, budget: u64) -> std::io::Result<()> {
    let mut entries: Vec<(PathBuf, u64, std::time::SystemTime)> = Vec::new();
    for job_dir in std::fs::read_dir(root)?.flatten() {
        if !job_dir.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        for f in std::fs::read_dir(job_dir.path())?.flatten() {
            if let Ok(meta) = f.metadata() {
                if meta.is_file() {
                    let atime = meta
                        .accessed()
                        .or_else(|_| meta.modified())
                        .unwrap_or(std::time::UNIX_EPOCH);
                    entries.push((f.path(), meta.len(), atime));
                }
            }
        }
    }

    let total: u64 = entries.iter().map(|(_, size, _)| size).sum();
    if total <= budget {
        return Ok(());
    }

    // Oldest first.
    entries.sort_by_key(|(_, _, atime)| *atime);

    let mut freed: u64 = 0;
    let target = total.saturating_sub(budget);
    for (path, size, _) in entries {
        if freed >= target {
            break;
        }
        if std::fs::remove_file(&path).is_ok() {
            freed += size;
        }
    }
    Ok(())
}

/// Clear the entire tile cache for one job. Called by UI "clear
/// cache" action or when a user deletes job history.
pub fn clear_job_cache(job_id: &str) -> Result<(), String> {
    let dir = job_dir(job_id);
    if dir.exists() {
        std::fs::remove_dir_all(&dir).map_err(|e| format!("clear: {}", e))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_preserves_safe_chars() {
        assert_eq!(sanitize("Cyan"), "Cyan");
        assert_eq!(sanitize("PANTONE 485 C"), "PANTONE_485_C");
        assert_eq!(sanitize("../../etc/passwd"), "______etc_passwd");
    }

    #[test]
    fn tile_key_generates_distinct_filenames() {
        let k1 = TileKey::Base {
            job_id: "abc".into(),
            page: 1,
            dpi: 150,
        };
        let k2 = TileKey::Base {
            job_id: "abc".into(),
            page: 1,
            dpi: 300,
        };
        let k3 = TileKey::Channel {
            job_id: "abc".into(),
            page: 1,
            dpi: 150,
            channel: "Cyan".into(),
        };
        let k4 = TileKey::TacHeatmap {
            job_id: "abc".into(),
            page: 1,
            dpi: 150,
            tac_limit: 300,
        };
        assert_ne!(k1.file_name(), k2.file_name());
        assert_ne!(k1.file_name(), k3.file_name());
        assert_ne!(k3.file_name(), k4.file_name());
    }

    #[test]
    fn endpoint_urls_match_engine_routes() {
        let base = "https://api.lintpdf.com";
        let k = TileKey::Base {
            job_id: "j1".into(),
            page: 3,
            dpi: 150,
        };
        assert_eq!(
            k.endpoint_url(base),
            "https://api.lintpdf.com/api/v1/viewer/jobs/j1/pages/3/tile?dpi=150"
        );
        let k = TileKey::Channel {
            job_id: "j1".into(),
            page: 1,
            dpi: 300,
            channel: "PANTONE 485 C".into(),
        };
        assert!(k
            .endpoint_url(base)
            .contains("/pages/1/channel/PANTONE%20485%20C"));
        let k = TileKey::TacHeatmap {
            job_id: "j1".into(),
            page: 2,
            dpi: 150,
            tac_limit: 320,
        };
        assert_eq!(
            k.endpoint_url(base),
            "https://api.lintpdf.com/api/v1/viewer/jobs/j1/pages/2/tac-heatmap?dpi=150&tac_limit=320"
        );
    }
}
