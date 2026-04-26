use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;

const KEYRING_SERVICE: &str = "com.lintpdf.desktop";
const KEYRING_USER: &str = "api_key";

/// Read the API key from the OS keyring (macOS Keychain, Windows Credential
/// Manager, Linux Secret Service). Returns `None` when the keyring backend
/// isn't available (e.g. headless Linux without D-Bus) or no key has been
/// stored — callers fall back to `AppConfig::api_key`.
fn keyring_read() -> Option<String> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .ok()
        .and_then(|entry| entry.get_password().ok())
        .filter(|s| !s.is_empty())
}

/// Write the API key to the OS keyring. Returns `Err` when the backend
/// rejects the write — the caller decides whether to fall back.
fn keyring_write(value: &str) -> Result<(), String> {
    let entry = keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| format!("Keyring unavailable: {}", e))?;
    entry
        .set_password(value)
        .map_err(|e| format!("Keyring write failed: {}", e))
}

fn keyring_delete() {
    if let Ok(entry) = keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER) {
        let _ = entry.delete_credential();
    }
}

/// How a folder should brand the reports it submits.
///
/// Mirrors the `brand` query-parameter values accepted by
/// `POST /api/v1/jobs` (see `parse_brand_param` in the engine).
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum BrandMode {
    /// Use the tenant-level default (nothing sent on submit).
    #[default]
    Default,
    /// `brand=anonymous` — strip branding entirely.
    Anonymous,
    /// `brand=lintpdf` — use the LintPDF default branding.
    Lintpdf,
    /// `brand=profile:<uuid>` — use a specific tenant BrandProfile.
    Profile,
}

fn default_brand_mode() -> BrandMode {
    BrandMode::Default
}

fn default_jdf_timeout() -> f64 {
    30.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FolderConfig {
    pub id: String,
    pub name: String,
    pub enabled: bool,
    pub watch_dir: String,
    pub profile_id: String,
    pub pass_dir: String,
    pub fail_dir: String,
    pub error_dir: String,
    pub write_sidecar: bool,
    pub stabilization_secs: f64,
    pub poll_interval_secs: f64,
    pub file_extensions: Vec<String>,

    /// Branding mode for reports emitted by this folder.
    /// Omitted in older configs — defaults to `BrandMode::Default`.
    #[serde(default = "default_brand_mode")]
    pub brand_mode: BrandMode,

    /// Tenant BrandProfile UUID, used only when `brand_mode == Profile`.
    #[serde(default)]
    pub brand_profile_id: Option<String>,

    /// How long to wait for a JDF/XJDF companion file after a PDF
    /// stabilizes, before submitting the PDF without a companion.
    #[serde(default = "default_jdf_timeout")]
    pub jdf_companion_timeout_secs: f64,

    /// Route submissions from this folder through a tenant custom endpoint
    /// (`POST /api/v1/endpoints/{identifier}/submit`) instead of the default
    /// `POST /api/v1/jobs`. When set, the endpoint's bound profile / brand
    /// win — `profile_id` and `brand_*` become ignored for submit, though
    /// they still act as the UI's display value.
    #[serde(default)]
    pub endpoint_id: Option<String>,

    /// Treat files matching `external_extensions` as pre-existing external
    /// preflight reports. Submitted via `/api/v1/jobs` with
    /// `preflight_source=external`. Set to `None` for "auto-detect" (the
    /// engine sniffs the report shape at ingest).
    #[serde(default)]
    pub external_format: Option<String>,

    /// Approval-chain template to attach to every job submitted from this
    /// folder. UUID of a row in `GET /api/v1/approval-templates`.
    #[serde(default)]
    pub approval_template_id: Option<String>,

    /// Group stabilized files into batches submitted via
    /// `POST /api/v1/batch/submit`. The engine's batch endpoint only
    /// accepts `profile_id` + files, so this is mutually-exclusive
    /// with custom endpoints, external imports, and any brand
    /// override — see [`FolderConfig::validate`].
    #[serde(default)]
    pub batch_enabled: bool,

    /// Window size in seconds. Files arriving within the same floor-
    /// bucketed window share a `batch_group` and drain together.
    #[serde(default = "default_batch_window")]
    pub batch_window_secs: f64,
}

fn default_batch_window() -> f64 {
    10.0
}

impl FolderConfig {
    /// Enforce the engine-side constraints that the batch endpoint
    /// silently drops. Called by `save_config` / `update_folder` so a
    /// CLI-edited `config.json` can't produce a silently-broken folder.
    pub fn validate(&self) -> Result<(), String> {
        if !self.batch_enabled {
            return Ok(());
        }
        if self.endpoint_id.as_ref().is_some_and(|s| !s.trim().is_empty()) {
            return Err(
                "Batch mode is incompatible with custom endpoints — the \
                 engine's /api/v1/batch/submit endpoint doesn't route through \
                 tenant endpoints."
                    .to_string(),
            );
        }
        if self
            .external_format
            .as_ref()
            .is_some_and(|s| !s.trim().is_empty())
        {
            return Err(
                "Batch mode is incompatible with external report imports — \
                 the batch endpoint ignores `preflight_source`."
                    .to_string(),
            );
        }
        if self.brand_mode != BrandMode::Default {
            return Err(
                "Batch mode is incompatible with per-folder brand overrides — \
                 the batch endpoint ignores `brand` / `unbranded`."
                    .to_string(),
            );
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub version: u32,
    pub api_key: String,
    pub base_url: String,

    /// Base URL for the LintPDF Next.js app — separate from `base_url`
    /// (which is the engine API). The Onboarding screen calls
    /// `${app_base_url}/api/public/tenant-lookup` to resolve a tenant
    /// before the user has authenticated.
    #[serde(default = "default_app_base_url")]
    pub app_base_url: String,

    /// LintPDF tenant id captured during first-run Onboarding. Empty
    /// string when not yet onboarded — the React shell uses the
    /// presence of both `tenant_id` and `api_key` to decide whether
    /// the Onboarding gate is satisfied.
    #[serde(default)]
    pub tenant_id: String,

    /// Display name of the captured tenant, shown in Settings.
    #[serde(default)]
    pub tenant_name: String,

    /// Cached AppSettings branding blob from
    /// `/api/public/tenant-lookup`. JSON-typed because the Pixie Dust
    /// branding shape evolves over time and we don't want the desktop
    /// to break the moment a new optional column appears upstream.
    #[serde(default)]
    pub tenant_branding: Option<serde_json::Value>,

    pub folders: Vec<FolderConfig>,
    pub notifications_enabled: bool,
    pub start_minimized: bool,
    pub launch_at_login: bool,
}

fn default_app_base_url() -> String {
    "https://app.lintpdf.com".to_string()
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            version: 1,
            api_key: String::new(),
            base_url: "https://api.lintpdf.com".to_string(),
            app_base_url: default_app_base_url(),
            tenant_id: String::new(),
            tenant_name: String::new(),
            tenant_branding: None,
            folders: Vec::new(),
            notifications_enabled: true,
            start_minimized: false,
            launch_at_login: false,
        }
    }
}

pub struct ConfigManager {
    config: Mutex<AppConfig>,
    config_path: PathBuf,
}

impl ConfigManager {
    pub fn new() -> Self {
        let config_dir = dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("lintpdf-desktop");

        fs::create_dir_all(&config_dir).ok();
        let config_path = config_dir.join("config.json");

        let mut config = if config_path.exists() {
            match fs::read_to_string(&config_path) {
                Ok(data) => serde_json::from_str(&data).unwrap_or_default(),
                Err(_) => AppConfig::default(),
            }
        } else {
            AppConfig::default()
        };

        // Key migration:
        // 1) If the keyring has a key, that wins — copy it into memory and
        //    blank any legacy plaintext copy on disk.
        // 2) Otherwise, if config.json still has a plaintext key from a
        //    pre-keyring install, push it into the keyring and blank it on
        //    disk on the next save.
        if let Some(key) = keyring_read() {
            config.api_key = key;
            // Ensure the on-disk file doesn't retain stale plaintext.
            // Write only when needed to avoid churning mtimes on launch.
        } else if !config.api_key.is_empty() {
            if keyring_write(&config.api_key).is_ok() {
                log::info!(
                    "Migrated API key from config.json to OS keyring ({})",
                    KEYRING_SERVICE
                );
            } else {
                log::warn!(
                    "OS keyring unavailable; API key remains in config.json"
                );
            }
        }

        let manager = Self {
            config: Mutex::new(config.clone()),
            config_path,
        };

        // Re-persist (without the plaintext key) if we just pulled it from
        // the keyring. This scrubs any plaintext residue from older versions.
        if keyring_read().is_some() && !config.api_key.is_empty() {
            let _ = manager.save(config);
        }

        manager
    }

    /// Returns the in-memory config, which already has the real API key —
    /// callers never need to consult the keyring directly.
    pub fn get(&self) -> AppConfig {
        self.config.lock().unwrap().clone()
    }

    pub fn save(&self, config: AppConfig) -> Result<(), String> {
        // Try to stash the API key in the OS keyring first. If that
        // succeeds, we blank the plaintext copy in the on-disk file. On
        // backends where the keyring is unavailable (headless Linux,
        // locked-down kiosks) we fall back to keeping it in config.json,
        // exactly like before this change.
        let mut on_disk = config.clone();
        let keyring_ok = if config.api_key.is_empty() {
            keyring_delete();
            true
        } else {
            match keyring_write(&config.api_key) {
                Ok(()) => {
                    on_disk.api_key = String::new();
                    true
                }
                Err(e) => {
                    log::warn!("{} — keeping API key in config.json", e);
                    false
                }
            }
        };

        let json = serde_json::to_string_pretty(&on_disk)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;
        fs::write(&self.config_path, json)
            .map_err(|e| format!("Failed to write config: {}", e))?;

        // In-memory we always keep the real key so callers don't have to
        // re-read the keyring on every request.
        *self.config.lock().unwrap() = config;

        // Emit a tiny log trace so support can distinguish "kept in keyring"
        // from "fell back to disk" in bug reports.
        log::debug!(
            "Config saved (keyring={})",
            if keyring_ok { "ok" } else { "fallback" }
        );
        Ok(())
    }

    pub fn update<F>(&self, f: F) -> Result<(), String>
    where
        F: FnOnce(&mut AppConfig),
    {
        let mut config = self.get();
        f(&mut config);
        self.save(config)
    }

    pub fn get_folder(&self, id: &str) -> Option<FolderConfig> {
        self.get().folders.iter().find(|f| f.id == id).cloned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_folder() -> FolderConfig {
        FolderConfig {
            id: "f1".into(),
            name: "".into(),
            enabled: true,
            watch_dir: "".into(),
            profile_id: "lintpdf-default".into(),
            pass_dir: "".into(),
            fail_dir: "".into(),
            error_dir: "".into(),
            write_sidecar: true,
            stabilization_secs: 2.0,
            poll_interval_secs: 5.0,
            file_extensions: vec![],
            brand_mode: BrandMode::Default,
            brand_profile_id: None,
            jdf_companion_timeout_secs: 30.0,
            endpoint_id: None,
            external_format: None,
            approval_template_id: None,
            batch_enabled: false,
            batch_window_secs: 10.0,
        }
    }

    #[test]
    fn validate_passes_when_batch_disabled() {
        let mut f = base_folder();
        f.brand_mode = BrandMode::Anonymous;
        f.endpoint_id = Some("ep".into());
        f.external_format = Some("pitstop_xml".into());
        // Everything conflicting, but batch is off — valid.
        assert!(f.validate().is_ok());
    }

    #[test]
    fn validate_passes_on_clean_batch() {
        let mut f = base_folder();
        f.batch_enabled = true;
        assert!(f.validate().is_ok());
    }

    #[test]
    fn batch_conflicts_with_brand() {
        let mut f = base_folder();
        f.batch_enabled = true;
        f.brand_mode = BrandMode::Anonymous;
        assert!(f.validate().unwrap_err().contains("brand"));
    }

    #[test]
    fn batch_conflicts_with_endpoint() {
        let mut f = base_folder();
        f.batch_enabled = true;
        f.endpoint_id = Some("some-endpoint".into());
        assert!(f.validate().unwrap_err().contains("custom endpoints"));
    }

    #[test]
    fn batch_conflicts_with_external_format() {
        let mut f = base_folder();
        f.batch_enabled = true;
        f.external_format = Some("pitstop_xml".into());
        assert!(f.validate().unwrap_err().contains("external report"));
    }

    #[test]
    fn batch_blank_strings_do_not_conflict() {
        // Whitespace-only values should be treated as "unset".
        let mut f = base_folder();
        f.batch_enabled = true;
        f.endpoint_id = Some("   ".into());
        f.external_format = Some("".into());
        assert!(f.validate().is_ok());
    }
}
