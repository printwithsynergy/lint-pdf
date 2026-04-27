use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, State};

use crate::config::{AppConfig, ConfigManager, FolderConfig};
use crate::connectivity::{ConnectivitySnapshot, ConnectivityState};
use crate::db::{Database, JobRecord, ShareLinks};
use crate::watcher::WatcherManager;

pub struct AppState {
    pub config_mgr: Arc<ConfigManager>,
    pub watcher_mgr: Arc<WatcherManager>,
    pub db: Arc<Database>,
    pub connectivity: ConnectivityState,
    /// Handle to the drainer's wake-up `Notify`. Commands that create
    /// or revive outbox rows (retry, re-queue, future bulk actions)
    /// signal this to trigger an immediate drain pass.
    pub drainer_wake: Arc<tokio::sync::Notify>,
}

/// Fail fast when a Tauri command that talks to the engine is invoked
/// while offline. Better than letting the HTTP call time out after
/// 30s — the UI can surface a clear "offline" message instantly.
fn require_online(state: &AppState, op: &str) -> Result<(), String> {
    if state.connectivity.is_online() {
        Ok(())
    } else {
        Err(format!("Offline — {} needs connectivity.", op))
    }
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
    for folder in &config.folders {
        folder.validate()?;
    }
    state.config_mgr.save(config)
}

#[tauri::command]
pub fn add_folder(state: State<'_, AppState>, folder: FolderConfig) -> Result<(), String> {
    folder.validate()?;
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
    folder.validate()?;
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
    require_online(&state, "listing brand profiles")?;
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
    // ``url`` is nullable because the engine supports an opt-in inline
    // return mode (POST /reports with {"format":"json","return":"inline"})
    // that omits the signed-token URL. Desktop always sends bare
    // format strings, which the engine maps to return="url", so in
    // practice this field is always Some — the Option is purely for
    // schema parity with the widened server response.
    #[serde(default)]
    url: Option<String>,
    #[serde(default)]
    #[allow(dead_code)]
    token: Option<String>,
    #[serde(default)]
    #[allow(dead_code)]
    expires_at: Option<String>,
    // Present only when the caller requested inline/both on text formats.
    // Desktop ignores these for now; captured so serde_json::from_str
    // doesn't fail on the additive fields.
    #[serde(default)]
    #[allow(dead_code)]
    data: Option<serde_json::Value>,
    #[serde(default)]
    #[allow(dead_code)]
    content_type: Option<String>,
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
    require_online(&state, "minting share links")?;
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
        // Desktop only mints url-mode (see body at line 275: bare
        // format strings). An inline-only response row would carry a
        // None url; skip it defensively so we don't overwrite a
        // previously cached URL with nothing.
        let Some(report_url) = report.url else {
            log::info!(
                "mint response for format {} had no url (inline-only?); skipping",
                report.format
            );
            continue;
        };
        match report.format.as_str() {
            "html" => links.html = Some(report_url),
            "pdf" => links.pdf = Some(report_url),
            "json" => links.json = Some(report_url),
            "xml" => links.xml = Some(report_url),
            "annotated_pdf" => links.annotated_pdf = Some(report_url),
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
    require_online(&state, "listing endpoints")?;
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
    require_online(&state, "listing approval templates")?;
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

/// Fetch a plain-language AI review of a completed job's findings via
/// `GET /api/v1/ai-review/{job_id}/interpret`. Returns a typed struct so
/// the UI can render the summary + per-finding explanations.
#[tauri::command]
pub async fn get_ai_interpretation(
    state: State<'_, AppState>,
    api_job_id: String,
) -> Result<AiInterpretation, String> {
    require_online(&state, "fetching AI review")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }

    let url = format!(
        "{}/api/v1/ai-review/{}/interpret",
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

// ── Connectivity ──────────────────────────────────────────────

#[derive(serde::Serialize)]
pub struct ConnectivityStatusResponse {
    #[serde(flatten)]
    pub snap: ConnectivitySnapshot,
    pub queued_count: u32,
}

#[tauri::command]
pub fn get_connectivity_status(
    state: State<'_, AppState>,
) -> Result<ConnectivityStatusResponse, String> {
    Ok(ConnectivityStatusResponse {
        snap: state.connectivity.snapshot(),
        queued_count: state.db.count_queued().unwrap_or(0),
    })
}

/// Force an immediate /health probe regardless of the 15s schedule.
/// Used by the "Retry now" button in the header pill.
#[tauri::command]
pub fn force_connectivity_check(state: State<'_, AppState>) -> Result<(), String> {
    state.connectivity.force_check();
    Ok(())
}

// ── Viewer window ─────────────────────────────────────────────

/// Open the hosted viewer for a job in a new Tauri child window.
/// Callers pass a pre-minted `/r/{token}` share-link URL.
#[tauri::command]
pub async fn open_viewer_window(
    app: AppHandle,
    url: String,
    title: String,
) -> Result<(), String> {
    use tauri::{WebviewUrl, WebviewWindowBuilder};

    let parsed = url::Url::parse(&url).map_err(|e| format!("Invalid URL: {}", e))?;
    // Unique label per invocation so a user can open several viewers
    // side-by-side.
    let label = format!("viewer-{}", uuid::Uuid::new_v4().simple());
    WebviewWindowBuilder::new(&app, label, WebviewUrl::External(parsed))
        .title(title)
        .inner_size(1400.0, 900.0)
        .resizable(true)
        .build()
        .map_err(|e| format!("Failed to open viewer window: {}", e))?;
    Ok(())
}

// ── Test connection ──────────────────────────────────────────

#[derive(serde::Serialize)]
pub struct TestConnectionResult {
    /// True when `GET {base_url}/health` returned 2xx. This tells us
    /// the engine is reachable and responding.
    pub health_ok: bool,
    /// True when the authenticated probe (a cheap GET against
    /// `/api/v1/usage`) succeeded. False implies a bad API key or
    /// a tenant permission problem even if `health_ok` is true.
    pub auth_ok: bool,
    /// Round-trip milliseconds of the health probe, for UI display.
    pub latency_ms: u64,
    /// Detailed message when something failed (e.g. HTTP status +
    /// first 200 chars of body). Null on full success.
    pub error: Option<String>,
}

/// Settings-page "Test connection" button. Probes `/health` (reachability)
/// and `/api/v1/usage` (auth) with the **candidate** `base_url` / `api_key`
/// so users can validate before saving.
#[tauri::command]
pub async fn test_connection(
    base_url: String,
    api_key: String,
) -> Result<TestConnectionResult, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Build client: {}", e))?;

    let trimmed = base_url.trim_end_matches('/');
    let health_url = format!("{}/health", trimmed);
    let auth_url = format!("{}/api/v1/usage", trimmed);

    let start = std::time::Instant::now();
    let health_resp = client.get(&health_url).send().await;
    let latency_ms = start.elapsed().as_millis() as u64;

    let (health_ok, health_err) = match health_resp {
        Ok(r) if r.status().is_success() => (true, None),
        Ok(r) => (
            false,
            Some(format!(
                "Health check returned {}: {}",
                r.status(),
                snippet(r.text().await.unwrap_or_default())
            )),
        ),
        Err(e) => (false, Some(format!("Engine unreachable: {}", e))),
    };

    // Only probe auth when health passed AND the user provided a key.
    // Otherwise the auth error would be a confusing consequence of the
    // prior failure.
    let (auth_ok, auth_err) = if !health_ok {
        (false, None)
    } else if api_key.trim().is_empty() {
        (false, Some("API key is empty.".to_string()))
    } else {
        match client
            .get(&auth_url)
            .header("Authorization", format!("Bearer {}", api_key))
            .send()
            .await
        {
            Ok(r) if r.status().is_success() => (true, None),
            Ok(r) => {
                let status = r.status();
                let body = snippet(r.text().await.unwrap_or_default());
                if status == 401 || status == 403 {
                    (false, Some(format!("API key rejected ({}).", status)))
                } else {
                    (false, Some(format!("Auth probe {}: {}", status, body)))
                }
            }
            Err(e) => (false, Some(format!("Auth probe failed: {}", e))),
        }
    };

    let error = health_err.or(auth_err);

    Ok(TestConnectionResult {
        health_ok,
        auth_ok,
        latency_ms,
        error,
    })
}

fn snippet(s: String) -> String {
    let max = 200;
    if s.chars().count() <= max {
        s
    } else {
        let mut t: String = s.chars().take(max).collect();
        t.push('…');
        t
    }
}

// ── Manual retry ─────────────────────────────────────────────

/// Flip an `error` row back to `queued_retry` and wake the drainer.
/// Used by the "Retry" button in Results when the user wants to try
/// a terminal failure again (e.g. after fixing the profile id or
/// putting the file back into the watch folder).
#[tauri::command]
pub fn retry_job(state: State<'_, AppState>, local_id: String) -> Result<(), String> {
    use crate::db::status;
    let mut record = state
        .db
        .get_by_local_id(&local_id)?
        .ok_or_else(|| format!("Job not found: {}", local_id))?;

    if !std::path::Path::new(&record.file_path).exists() {
        return Err(format!(
            "Source file no longer exists: {}. Drop the file back into the \
             watch folder to re-queue it.",
            record.file_path
        ));
    }

    record.status = status::QUEUED_RETRY.to_string();
    record.retry_attempts = 0;
    record.next_retry_at = None;
    record.error_message = None;
    record.completed_at = None;
    state.db.update_job(&record)?;
    // Wake the drainer so the retry kicks off immediately.
    state.drainer_wake.notify_waiters();
    Ok(())
}

// ─── v2 playbook commands ────────────────────────────────────────────────
//
// AI-Explain (Q-C4/C5), EPM verdict, decisions audit, and cost-cap. Each
// command shells out to the engine's tenant-scoped REST surface using the
// configured API key + base URL. HTTP 402 (cost-cap exceeded) is mapped to
// a specific Err string the frontend can branch on.

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct ExplanationResponse {
    pub finding_id: String,
    #[serde(default, alias = "explanation")]
    pub text: String,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub cached: bool,
    #[serde(default)]
    pub cost_cents: Option<f64>,
}

#[tauri::command]
pub async fn explain_finding(
    state: State<'_, AppState>,
    job_id: String,
    finding_id: String,
) -> Result<ExplanationResponse, String> {
    require_online(&state, "explaining finding")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!(
        "{}/api/v1/jobs/{}/findings/{}/explain",
        config.base_url.trim_end_matches('/'),
        job_id,
        finding_id,
    );
    let resp = reqwest::Client::new()
        .post(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .header("Content-Type", "application/json")
        .json(&serde_json::json!({}))
        .timeout(Duration::from_secs(60))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if resp.status().as_u16() == 402 {
        return Err("Cost cap exceeded".to_string());
    }
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    resp.json::<ExplanationResponse>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct EpmVerdictResponse {
    pub job_id: String,
    pub tier: String,
    #[serde(default)]
    pub rejection_drivers: Vec<String>,
    #[serde(default)]
    pub advisories: Vec<String>,
    #[serde(default)]
    pub recommends_indichrome: bool,
    #[serde(default)]
    pub legacy_codes_fired: Vec<String>,
    #[serde(default)]
    pub epm_findings_count: i32,
}

#[tauri::command]
pub async fn get_epm_verdict(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<EpmVerdictResponse, String> {
    require_online(&state, "fetching EPM verdict")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!(
        "{}/api/v1/jobs/{}/epm",
        config.base_url.trim_end_matches('/'),
        job_id,
    );
    let resp = reqwest::Client::new()
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    resp.json::<EpmVerdictResponse>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
pub struct DecisionResponse {
    pub id: String,
    pub job_id: String,
    #[serde(default)]
    pub finding_id: Option<String>,
    pub decision_type: String,
    #[serde(default)]
    pub decision_value: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
    pub decided_by_user_id: String,
    #[serde(default)]
    pub decided_at: Option<String>,
    pub source: String,
    #[serde(default)]
    pub is_active: bool,
    #[serde(default)]
    pub revoked_at: Option<String>,
    #[serde(default)]
    pub revoked_reason: Option<String>,
}

#[derive(serde::Deserialize)]
struct DecisionListRaw {
    decisions: Vec<DecisionResponse>,
}

#[tauri::command]
pub async fn list_decisions(
    state: State<'_, AppState>,
    job_id: String,
    include_revoked: Option<bool>,
) -> Result<Vec<DecisionResponse>, String> {
    require_online(&state, "listing decisions")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!(
        "{}/api/v1/jobs/{}/decisions?include_revoked={}&limit=200",
        config.base_url.trim_end_matches('/'),
        job_id,
        include_revoked.unwrap_or(false),
    );
    let resp = reqwest::Client::new()
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    let parsed: DecisionListRaw = resp
        .json()
        .await
        .map_err(|e| format!("Parse error: {}", e))?;
    Ok(parsed.decisions)
}

#[derive(serde::Deserialize)]
pub struct RecordDecisionInput {
    pub decision_type: String,
    pub decided_by_user_id: String,
    #[serde(default = "default_source")]
    pub source: String,
    #[serde(default)]
    pub finding_id: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

fn default_source() -> String {
    "desktop".to_string()
}

#[tauri::command]
pub async fn record_decision(
    state: State<'_, AppState>,
    job_id: String,
    input: RecordDecisionInput,
) -> Result<DecisionResponse, String> {
    require_online(&state, "recording decision")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let path = match &input.finding_id {
        Some(fid) => format!(
            "{}/api/v1/jobs/{}/findings/{}/decisions",
            config.base_url.trim_end_matches('/'),
            job_id,
            fid,
        ),
        None => format!(
            "{}/api/v1/jobs/{}/decisions",
            config.base_url.trim_end_matches('/'),
            job_id,
        ),
    };
    let body = serde_json::json!({
        "decision_type": input.decision_type,
        "decided_by_user_id": input.decided_by_user_id,
        "source": input.source,
        "notes": input.notes,
    });
    let resp = reqwest::Client::new()
        .post(&path)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .header("Content-Type", "application/json")
        .json(&body)
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    resp.json::<DecisionResponse>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct CostCapResponse {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub monthly_cap_cents: i64,
    #[serde(default)]
    pub alert_threshold_pct: i32,
    #[serde(default)]
    pub used_cents: Option<i64>,
}

#[tauri::command]
pub async fn get_cost_cap(state: State<'_, AppState>) -> Result<CostCapResponse, String> {
    require_online(&state, "fetching cost cap")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!(
        "{}/api/v1/ai/cost-cap",
        config.base_url.trim_end_matches('/'),
    );
    let resp = reqwest::Client::new()
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    resp.json::<CostCapResponse>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}

#[derive(serde::Deserialize)]
pub struct CostCapInput {
    pub enabled: bool,
    #[serde(default)]
    pub monthly_cap_cents: Option<i64>,
    #[serde(default)]
    pub alert_threshold_pct: Option<i32>,
}

#[tauri::command]
pub async fn set_cost_cap(
    state: State<'_, AppState>,
    input: CostCapInput,
) -> Result<CostCapResponse, String> {
    require_online(&state, "setting cost cap")?;
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!(
        "{}/api/v1/ai/cost-cap",
        config.base_url.trim_end_matches('/'),
    );
    let body = serde_json::json!({
        "enabled": input.enabled,
        "monthly_cap_cents": input.monthly_cap_cents,
        "alert_threshold_pct": input.alert_threshold_pct,
    });
    let resp = reqwest::Client::new()
        .post(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .header("Content-Type", "application/json")
        .json(&body)
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("API error {}: {}", resp.status(), resp.text().await.unwrap_or_default()));
    }
    resp.json::<CostCapResponse>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}
