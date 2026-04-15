use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;

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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub version: u32,
    pub api_key: String,
    pub base_url: String,
    pub folders: Vec<FolderConfig>,
    pub notifications_enabled: bool,
    pub start_minimized: bool,
    pub launch_at_login: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            version: 1,
            api_key: String::new(),
            base_url: "https://api.lintpdf.com".to_string(),
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

        let config = if config_path.exists() {
            match fs::read_to_string(&config_path) {
                Ok(data) => serde_json::from_str(&data).unwrap_or_default(),
                Err(_) => AppConfig::default(),
            }
        } else {
            AppConfig::default()
        };

        Self {
            config: Mutex::new(config),
            config_path,
        }
    }

    pub fn get(&self) -> AppConfig {
        self.config.lock().unwrap().clone()
    }

    pub fn save(&self, config: AppConfig) -> Result<(), String> {
        let json = serde_json::to_string_pretty(&config)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;
        fs::write(&self.config_path, json)
            .map_err(|e| format!("Failed to write config: {}", e))?;
        *self.config.lock().unwrap() = config;
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
