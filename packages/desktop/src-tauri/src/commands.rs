use std::sync::Arc;
use std::time::Duration;
use tauri::State;

use crate::config::{AppConfig, ConfigManager, FolderConfig};
use crate::db::{Database, JobRecord, ShareLinks};
use crate::watcher::WatcherManager;

pub struct AppState {
    pub config_mgr: Arc<ConfigManager>,
    pub watcher_mgr: Arc<WatcherManager>,
    pub db: Arc<Database>,
}

#[derive(serde::Serialize)]
pub struct WatcherStatusResponse {
    pub folder_id: String,
    pub active: bool,
    pub files_queued: usize,
    pub files_processed: u32,
    pub last_error: Option<String>,
}

// ── Config commands ───────────────────────────────────────────

#[tauri::command]
pub fn get_config(state: State<'_, AppState>) -> Result<AppConfig, String> {
    Ok(state.config_mgr.get())
}

#[tauri::command]
pub fn save_config(state: State<'_, AppState>, config: AppConfig) -> Result<(), String> {
    state.config_mgr.save(config)
}

#[tauri::command]
pub fn add_folder(state: State<'_, AppState>, folder: FolderConfig) -> Result<(), String> {
    state.config_mgr.update(|config| {
        config.folders.push(folder);
    })
}

#[tauri::command]
pub fn remove_folder(state: State<'_, AppState>, folder_id: String) -> Result<(), String> {
    state.watcher_mgr.stop(&folder_id);
    state.config_mgr.update(|config| {
        config.folders.retain(|f| f.id != folder_id);
    })
}

#[tauri::command]
pub fn update_folder(state: State<'_, AppState>, folder: FolderConfig) -> Result<(), String> {
    state.config_mgr.update(|config| {
        if let Some(existing) = config.folders.iter_mut().find(|f| f.id == folder.id) {
            *existing = folder;
        }
    })
}

// ── Watcher commands ──────────────────────────────────────────

#[tauri::command]
pub fn start_watching(state: State<'_, AppState>, folder_id: String) -> Result<(), String> {
    let folder = state
        .config_mgr
        .get_folder(&folder_id)
        .ok_or_else(|| format!("Folder not found: {}", folder_id))?;

    if !folder.enabled {
        return Err("Folder is disabled".to_string());
    }

    state.watcher_mgr.start(&folder)
}

#[tauri::command]
pub fn stop_watching(state: State<'_, AppState>, folder_id: String) -> Result<(), String> {
    state.watcher_mgr.stop(&folder_id);
    Ok(())
}

#[tauri::command]
pub fn start_all(state: State<'_, AppState>) -> Result<(), String> {
    let config = state.config_mgr.get();
    let mut errors = Vec::new();
    for folder in &config.folders {
        if folder.enabled && !folder.watch_dir.is_empty() {
            if let Err(e) = state.watcher_mgr.start(folder) {
                errors.push(format!("{}: {}", folder.name, e));
            }
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors.join("; "))
    }
}

#[tauri::command]
pub fn stop_all(state: State<'_, AppState>) -> Result<(), String> {
    let ids = state.watcher_mgr.active_ids();
    for id in ids {
        state.watcher_mgr.stop(&id);
    }
    Ok(())
}

#[tauri::command]
pub fn get_watcher_statuses(state: State<'_, AppState>) -> Result<Vec<WatcherStatusResponse>, String> {
    let config = state.config_mgr.get();
    let statuses = config
        .folders
        .iter()
        .map(|f| WatcherStatusResponse {
            folder_id: f.id.clone(),
            active: state.watcher_mgr.is_active(&f.id),
            files_queued: state.watcher_mgr.queued_count(&f.id),
            files_processed: 0, // TODO: track in watcher manager
            last_error: None,
        })
        .collect();
    Ok(statuses)
}

// ── Job history commands ──────────────────────────────────────

#[tauri::command]
pub fn get_recent_jobs(state: State<'_, AppState>, limit: u32) -> Result<Vec<JobRecord>, String> {
    state.db.get_recent(limit)
}

#[tauri::command]
pub fn clear_history(state: State<'_, AppState>) -> Result<(), String> {
    state.db.clear()
}

// ── Engine API helpers ────────────────────────────────────────

#[derive(serde::Serialize, Clone, Debug)]
pub struct BrandProfileSummary {
    pub id: String,
    pub name: String,
    pub is_default: bool,
}

#[derive(serde::Deserialize)]
struct BrandProfileRaw {
    id: String,
    name: String,
    #[serde(default)]
    is_default: bool,
}

/// List tenant BrandProfiles via `GET /api/v1/branding/profiles`.
/// Called lazily by the Brand dropdown in the React UI.
#[tauri::command]
pub async fn list_brand_profiles(
    state: State<'_, AppState>,
) -> Result<Vec<BrandProfileSummary>, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/branding/profiles",
        config.base_url.trim_end_matches('/')
    );

    let client = reqwest::Client::new();
    let resp = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("API error {}: {}", status, body));
    }

    // The engine returns either a bare array or an object with a `profiles`
    // key depending on version; handle both.
    let raw: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse profiles response: {}", e))?;

    let items = if let Some(arr) = raw.as_array() {
        arr.clone()
    } else if let Some(arr) = raw.get("profiles").and_then(|v| v.as_array()) {
        arr.clone()
    } else {
        return Err("Unexpected branding/profiles shape".to_string());
    };

    let profiles = items
        .into_iter()
        .filter_map(|v| serde_json::from_value::<BrandProfileRaw>(v).ok())
        .map(|p| BrandProfileSummary {
            id: p.id,
            name: p.name,
            is_default: p.is_default,
        })
        .collect();

    Ok(profiles)
}

#[derive(serde::Deserialize)]
struct MintReportsResponse {
    #[serde(default)]
    html_url: Option<String>,
    #[serde(default)]
    pdf_url: Option<String>,
    #[serde(default)]
    json_url: Option<String>,
    #[serde(default)]
    xml_url: Option<String>,
    // Alternative shape: { tokens: { html: "...", pdf: "..." } }
    #[serde(default)]
    urls: Option<std::collections::HashMap<String, String>>,
}

/// Mint share links for a completed job and persist them on the local record.
/// Wraps `POST /api/v1/jobs/{job_id}/reports`.
#[tauri::command]
pub async fn mint_share_link(
    state: State<'_, AppState>,
    local_id: String,
    api_job_id: String,
    formats: Vec<String>,
) -> Result<ShareLinks, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/jobs/{}/reports",
        config.base_url.trim_end_matches('/'),
        api_job_id
    );

    let body = serde_json::json!({ "formats": formats });

    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .json(&body)
        .timeout(Duration::from_secs(60))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("API error {}: {}", status, body));
    }

    let parsed: MintReportsResponse = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse reports response: {}", e))?;

    let mut links = ShareLinks::default();
    if let Some(url) = parsed.html_url {
        links.html = Some(url);
    }
    if let Some(url) = parsed.pdf_url {
        links.pdf = Some(url);
    }
    if let Some(url) = parsed.json_url {
        links.json = Some(url);
    }
    if let Some(url) = parsed.xml_url {
        links.xml = Some(url);
    }
    if let Some(map) = parsed.urls {
        if links.html.is_none() {
            links.html = map.get("html").cloned();
        }
        if links.pdf.is_none() {
            links.pdf = map.get("pdf").cloned();
        }
        if links.json.is_none() {
            links.json = map.get("json").cloned();
        }
        if links.xml.is_none() {
            links.xml = map.get("xml").cloned();
        }
    }

    // Merge with existing cached links (additive: keep previously minted
    // formats so the user doesn't have to re-mint all at once).
    let merged = match state.db.get_by_local_id(&local_id)? {
        Some(mut existing) => {
            let mut combined = existing.share_links.clone().unwrap_or_default();
            if links.html.is_some() {
                combined.html = links.html.clone();
            }
            if links.pdf.is_some() {
                combined.pdf = links.pdf.clone();
            }
            if links.json.is_some() {
                combined.json = links.json.clone();
            }
            if links.xml.is_some() {
                combined.xml = links.xml.clone();
            }
            existing.share_links = Some(combined.clone());
            state.db.update_job(&existing)?;
            combined
        }
        None => links,
    };

    Ok(merged)
}
