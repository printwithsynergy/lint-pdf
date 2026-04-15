//! Viewer-API Tauri commands.
//!
//! Thin pass-through wrappers around the engine's `/api/v1/viewer/…`
//! routes. Keeping them in one module (rather than interspersed with
//! the submit commands in `commands.rs`) makes the read/write split
//! obvious: everything here is read-only from the engine's
//! perspective.
//!
//! The heavy binary-tile endpoints (page raster, channel raster,
//! TAC heatmap) route through [`crate::tiles`] for disk caching;
//! everything else is a simple JSON round-trip.

use std::sync::Arc;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::State;

use crate::commands::AppState;
use crate::connectivity::ConnectivityState;
use crate::tiles::{self, OcgMask, TileKey};

fn ocg_mask(on: Option<Vec<i32>>, off: Option<Vec<i32>>) -> OcgMask {
    OcgMask {
        on: on.unwrap_or_default(),
        off: off.unwrap_or_default(),
    }
}

fn require_online(c: &ConnectivityState, op: &str) -> Result<(), String> {
    if c.is_online() {
        Ok(())
    } else {
        Err(format!("Offline — {} needs connectivity.", op))
    }
}

fn http() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|e| format!("build client: {}", e))
}

/// Shared JSON GET helper — bearer-auth, parses to any Deserialize.
async fn get_json<T: for<'de> Deserialize<'de>>(
    state: &AppState,
    path: &str,
) -> Result<T, String> {
    let config = state.config_mgr.get();
    if config.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    let url = format!("{}{}", config.base_url.trim_end_matches('/'), path);
    let resp = http()?
        .get(&url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .send()
        .await
        .map_err(|e| format!("HTTP: {}", e))?;
    let status = resp.status();
    if status == reqwest::StatusCode::UNAUTHORIZED
        || status == reqwest::StatusCode::FORBIDDEN
    {
        state.connectivity.record_auth_failure();
    }
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        let snippet: String = body.chars().take(300).collect();
        return Err(format!("API {}: {}", status, snippet));
    }
    state.connectivity.record_auth_success();
    resp.json::<T>()
        .await
        .map_err(|e| format!("parse JSON: {}", e))
}

// ── JSON response shapes ─────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageBox {
    pub x0: f64,
    pub y0: f64,
    pub x1: f64,
    pub y1: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageInfo {
    pub page_num: u32,
    pub width_pts: f64,
    pub height_pts: f64,
    pub media_box: PageBox,
    #[serde(default)]
    pub crop_box: Option<PageBox>,
    #[serde(default)]
    pub trim_box: Option<PageBox>,
    #[serde(default)]
    pub bleed_box: Option<PageBox>,
    #[serde(default)]
    pub rotation: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PagesResponse {
    pub job_id: String,
    pub page_count: u32,
    pub pages: Vec<PageInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeparationChannel {
    pub name: String,
    #[serde(rename = "type")]
    pub kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeparationsResponse {
    pub job_id: String,
    pub channels: Vec<SeparationChannel>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayerInfo {
    pub name: String,
    pub ocg_index: u32,
    #[serde(default = "default_true")]
    pub default_on: bool,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayersResponse {
    pub job_id: String,
    pub layers: Vec<LayerInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnnotationResponse {
    pub id: String,
    pub job_id: String,
    pub page_num: u32,
    pub kind: String,
    pub geometry: serde_json::Value,
    #[serde(default)]
    pub color: Option<String>,
    #[serde(default)]
    pub text: Option<String>,
    #[serde(default)]
    pub author_email: Option<String>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TacRunResponse {
    pub x0: f64,
    pub y0: f64,
    pub x1: f64,
    pub y1: f64,
    pub mean_tac: f64,
    pub limit: f64,
    pub exceeds: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TacRunsResponse {
    pub job_id: String,
    pub page_num: u32,
    pub dpi: u32,
    pub tac_limit: f64,
    pub runs: Vec<TacRunResponse>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DensitometerChannel {
    pub name: String,
    pub percent: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DensitometerResponse {
    pub x: f64,
    pub y: f64,
    pub dpi: u32,
    pub channels: Vec<DensitometerChannel>,
    pub tac: f64,
    pub tac_limit: f64,
    pub limit_exceeded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViewerConfigResponse {
    #[serde(default = "default_true")]
    pub enable_separations: bool,
    #[serde(default = "default_true")]
    pub enable_tac_heatmap: bool,
    #[serde(default = "default_true")]
    pub enable_annotations: bool,
    #[serde(default = "default_true")]
    pub enable_measurement: bool,
    #[serde(default = "default_true")]
    pub enable_layers: bool,
    #[serde(default = "default_true")]
    pub enable_findings_panel: bool,
    #[serde(default = "default_true")]
    pub enable_page_thumbnails: bool,
    #[serde(default = "default_true")]
    pub enable_zoom: bool,
    #[serde(default)]
    pub default_zoom: Option<u32>,
    #[serde(default)]
    pub default_dpi: Option<u32>,
    #[serde(default)]
    pub default_tac_limit: Option<f64>,
    #[serde(default)]
    pub preflight_source: Option<String>,
    #[serde(default)]
    pub capabilities: std::collections::HashMap<String, bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerdictResponse {
    #[serde(default)]
    pub verdict: Option<String>,
    #[serde(default)]
    pub auto_passed: Option<bool>,
    #[serde(default)]
    pub verdict_by: Option<String>,
    #[serde(default)]
    pub verdict_at: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

/// The engine's per-finding shape, stripped to the fields the
/// desktop viewer needs. We tolerate extra fields from server-side
/// evolution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FindingResponse {
    pub inspection_id: String,
    pub severity: String,
    pub message: String,
    #[serde(default)]
    pub page_num: Option<u32>,
    #[serde(default)]
    pub bbox: Option<Vec<f64>>,
    #[serde(default)]
    pub category: Option<String>,
    #[serde(default)]
    pub source: Option<String>,
    #[serde(default)]
    pub object_id: Option<String>,
    #[serde(default)]
    pub object_type: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct JobEnvelope {
    #[serde(default)]
    findings: Option<Vec<FindingResponse>>,
}

// ── Commands: pages / separations / layers / annotations / config / verdict / findings ──

#[tauri::command]
pub async fn viewer_pages(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<PagesResponse, String> {
    require_online(&state.connectivity, "viewing pages")?;
    let path = format!("/api/v1/viewer/jobs/{}/pages", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_separations(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<SeparationsResponse, String> {
    require_online(&state.connectivity, "loading separations")?;
    let path = format!("/api/v1/viewer/jobs/{}/separations", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_layers(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<LayersResponse, String> {
    require_online(&state.connectivity, "loading layers")?;
    let path = format!("/api/v1/viewer/jobs/{}/layers", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_annotations(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<Vec<AnnotationResponse>, String> {
    require_online(&state.connectivity, "loading annotations")?;
    let path = format!("/api/v1/viewer/jobs/{}/annotations", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_config(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<ViewerConfigResponse, String> {
    require_online(&state.connectivity, "loading viewer config")?;
    let path = format!("/api/v1/viewer/jobs/{}/config", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_verdict(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<VerdictResponse, String> {
    require_online(&state.connectivity, "loading verdict")?;
    let path = format!("/api/v1/viewer/jobs/{}/verdict", job_id);
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_findings(
    state: State<'_, AppState>,
    job_id: String,
) -> Result<Vec<FindingResponse>, String> {
    require_online(&state.connectivity, "loading findings")?;
    let path = format!("/api/v1/jobs/{}", job_id);
    let envelope: JobEnvelope = get_json(&state, &path).await?;
    Ok(envelope.findings.unwrap_or_default())
}

#[tauri::command]
pub async fn viewer_tac_runs(
    state: State<'_, AppState>,
    job_id: String,
    page_num: u32,
    dpi: u32,
    tac_limit: u32,
) -> Result<TacRunsResponse, String> {
    require_online(&state.connectivity, "loading TAC runs")?;
    let path = format!(
        "/api/v1/viewer/jobs/{}/pages/{}/tac-heatmap/runs?dpi={}&tac_limit={}",
        job_id, page_num, dpi, tac_limit
    );
    get_json(&state, &path).await
}

#[tauri::command]
pub async fn viewer_densitometer(
    state: State<'_, AppState>,
    job_id: String,
    page_num: u32,
    x: f64,
    y: f64,
    dpi: Option<u32>,
    tac_limit: Option<f64>,
) -> Result<DensitometerResponse, String> {
    require_online(&state.connectivity, "probing densitometer")?;
    let dpi = dpi.unwrap_or(300);
    let tac_limit = tac_limit.unwrap_or(300.0);
    let path = format!(
        "/api/v1/viewer/jobs/{}/pages/{}/densitometer?x={}&y={}&dpi={}&tac_limit={}",
        job_id, page_num, x, y, dpi, tac_limit
    );
    get_json(&state, &path).await
}

// ── Tile commands — route through the disk cache ─────────────

#[tauri::command]
pub async fn viewer_tile(
    state: State<'_, AppState>,
    job_id: String,
    page_num: u32,
    dpi: Option<u32>,
    ocg_on: Option<Vec<i32>>,
    ocg_off: Option<Vec<i32>>,
) -> Result<tiles::TileResult, String> {
    let dpi = dpi.unwrap_or(150);
    let key = TileKey::Base {
        job_id,
        page: page_num,
        dpi,
        ocg: ocg_mask(ocg_on, ocg_off),
    };
    tiles::fetch_tile(
        key,
        Arc::clone(&state.config_mgr),
        state.connectivity.clone(),
    )
    .await
}

#[tauri::command]
pub async fn viewer_channel_tile(
    state: State<'_, AppState>,
    job_id: String,
    page_num: u32,
    channel: String,
    dpi: Option<u32>,
    ocg_on: Option<Vec<i32>>,
    ocg_off: Option<Vec<i32>>,
) -> Result<tiles::TileResult, String> {
    let dpi = dpi.unwrap_or(150);
    let key = TileKey::Channel {
        job_id,
        page: page_num,
        dpi,
        channel,
        ocg: ocg_mask(ocg_on, ocg_off),
    };
    tiles::fetch_tile(
        key,
        Arc::clone(&state.config_mgr),
        state.connectivity.clone(),
    )
    .await
}

#[tauri::command]
pub async fn viewer_tac_heatmap(
    state: State<'_, AppState>,
    job_id: String,
    page_num: u32,
    dpi: Option<u32>,
    tac_limit: Option<u32>,
    ocg_on: Option<Vec<i32>>,
    ocg_off: Option<Vec<i32>>,
) -> Result<tiles::TileResult, String> {
    let dpi = dpi.unwrap_or(150);
    let tac_limit = tac_limit.unwrap_or(300);
    let key = TileKey::TacHeatmap {
        job_id,
        page: page_num,
        dpi,
        tac_limit,
        ocg: ocg_mask(ocg_on, ocg_off),
    };
    tiles::fetch_tile(
        key,
        Arc::clone(&state.config_mgr),
        state.connectivity.clone(),
    )
    .await
}

#[tauri::command]
pub fn viewer_clear_tile_cache(job_id: String) -> Result<(), String> {
    tiles::clear_job_cache(&job_id)
}
