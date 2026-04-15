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
struct MintReportInfo {
    format: String,
    url: String,
    #[serde(default)]
    #[allow(dead_code)]
    token: Option<String>,
    #[serde(default)]
    #[allow(dead_code)]
    expires_at: Option<String>,
}

#[derive(serde::Deserialize)]
struct MintReportsResponse {
    reports: Vec<MintReportInfo>,
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
    for report in parsed.reports {
        match report.format.as_str() {
            "html" => links.html = Some(report.url),
            "pdf" => links.pdf = Some(report.url),
            "json" => links.json = Some(report.url),
            "xml" => links.xml = Some(report.url),
            "annotated_pdf" => links.annotated_pdf = Some(report.url),
            other => {
                log::info!("Unknown report format in mint response: {}", other);
            }
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
            if links.annotated_pdf.is_some() {
                combined.annotated_pdf = links.annotated_pdf.clone();
            }
            existing.share_links = Some(combined.clone());
            state.db.update_job(&existing)?;
            combined
        }
        None => links,
    };

    Ok(merged)
}

// ── List helpers (endpoints / approval templates) ─────────────

#[derive(serde::Serialize, Clone, Debug)]
pub struct EndpointSummary {
    pub id: String,
    pub slug: String,
    pub profile_id: String,
    pub description: Option<String>,
    pub is_active: bool,
}

#[derive(serde::Deserialize)]
struct EndpointRaw {
    id: String,
    slug: String,
    #[serde(default)]
    profile_id: String,
    #[serde(default)]
    description: Option<String>,
    #[serde(default = "yes")]
    is_active: bool,
}

fn yes() -> bool {
    true
}

#[tauri::command]
pub async fn list_endpoints(
    state: State<'_, AppState>,
) -> Result<Vec<EndpointSummary>, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/endpoints",
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

    let raw: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse endpoints response: {}", e))?;

    // Engine returns `EndpointListResponse { endpoints: [...] }`.
    let arr = raw
        .get("endpoints")
        .and_then(|v| v.as_array())
        .cloned()
        .or_else(|| raw.as_array().cloned())
        .ok_or_else(|| "Unexpected endpoints shape".to_string())?;

    Ok(arr
        .into_iter()
        .filter_map(|v| serde_json::from_value::<EndpointRaw>(v).ok())
        .filter(|e| e.is_active)
        .map(|e| EndpointSummary {
            id: e.id,
            slug: e.slug,
            profile_id: e.profile_id,
            description: e.description,
            is_active: e.is_active,
        })
        .collect())
}

#[derive(serde::Serialize, Clone, Debug)]
pub struct ApprovalTemplateSummary {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub is_default: bool,
}

#[derive(serde::Deserialize)]
struct ApprovalTemplateRaw {
    id: String,
    name: String,
    #[serde(default)]
    description: Option<String>,
    #[serde(default)]
    is_default: bool,
}

#[tauri::command]
pub async fn list_approval_templates(
    state: State<'_, AppState>,
) -> Result<Vec<ApprovalTemplateSummary>, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/approval-templates",
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

    // Engine returns a bare list.
    let raw: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse templates response: {}", e))?;
    let arr = raw
        .as_array()
        .cloned()
        .or_else(|| raw.get("templates").and_then(|v| v.as_array()).cloned())
        .ok_or_else(|| "Unexpected approval-templates shape".to_string())?;

    Ok(arr
        .into_iter()
        .filter_map(|v| serde_json::from_value::<ApprovalTemplateRaw>(v).ok())
        .map(|t| ApprovalTemplateSummary {
            id: t.id,
            name: t.name,
            description: t.description,
            is_default: t.is_default,
        })
        .collect())
}

// ── AI interpretation ────────────────────────────────────────

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct AiInterpretationItem {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inspection_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub explanation: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub why_it_matters: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub suggestion: Option<String>,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct AiInterpretation {
    pub summary: String,
    #[serde(default)]
    pub interpretations: Vec<AiInterpretationItem>,
}

/// Fetch a plain-language interpretation of a completed job's findings via
/// `GET /api/v1/captains-log/{job_id}/interpret`. Returns a typed struct so
/// the UI can render the summary + per-finding explanations.
#[tauri::command]
pub async fn get_ai_interpretation(
    state: State<'_, AppState>,
    api_job_id: String,
) -> Result<AiInterpretation, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/captains-log/{}/interpret",
        config.base_url.trim_end_matches('/'),
        api_job_id
    );

    let client = reqwest::Client::new();
    let resp = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .timeout(Duration::from_secs(120))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;

    if resp.status().as_u16() == 403 {
        return Err(
            "AI interpretation requires an AI-enabled plan. Upgrade in the LintPDF dashboard."
                .to_string(),
        );
    }

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("API error {}: {}", status, body));
    }

    resp.json::<AiInterpretation>()
        .await
        .map_err(|e| format!("Failed to parse interpretation response: {}", e))
}
