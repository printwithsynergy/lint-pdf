//! Submission primitives.
//!
//! After Phase 2, the submitter no longer owns the control flow —
//! it exposes pure async operations that the [`drainer`](crate::drainer)
//! invokes. Watcher emits `StabilizedFile`s into `intake_file`, which
//! persists an outbox row (status `queued_offline`) and signals the
//! drainer. The drainer wakes when online, pulls ready rows, and calls
//! [`attempt_single`] / [`attempt_batch`] which handle upload, polling,
//! and routing.

use reqwest::multipart;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, Emitter};

use crate::config::{BrandMode, ConfigManager, FolderConfig};
use crate::connectivity::ConnectivityState;
use crate::db::{status, Database, JobRecord, JobSummary};
use crate::router;
use crate::watcher::StabilizedFile;

#[derive(Debug, Deserialize)]
struct SubmitResponse {
    job_id: String,
}

#[derive(Debug, Deserialize)]
struct BatchSubmitResponse {
    batch_id: String,
    jobs: Vec<BatchJobInfo>,
}

#[derive(Debug, Deserialize)]
struct BatchJobInfo {
    job_id: String,
    file_name: String,
    #[serde(default)]
    #[allow(dead_code)]
    status: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BatchStatusResponse {
    status: String,
    jobs: Vec<BatchJobInfo>,
}

#[derive(Debug, Deserialize)]
struct JobStatusResponse {
    status: String,
    summary: Option<ApiSummary>,
    #[allow(dead_code)]
    findings: Option<Vec<serde_json::Value>>,
}

#[derive(Debug, Deserialize)]
struct ApiSummary {
    passed: Option<bool>,
    error_count: Option<u32>,
    warning_count: Option<u32>,
    advisory_count: Option<u32>,
}

/// Error classification the drainer uses to decide whether to retry.
#[derive(Debug, Clone)]
pub enum SubmitError {
    /// Transport / 5xx / 429 / offline. Flip row to `queued_retry`
    /// with exponential backoff; drainer will try again.
    Transient(String),
    /// 4xx, local FS error, malformed response. Row goes to `error`.
    Terminal(String),
}

impl SubmitError {
    pub fn message(&self) -> &str {
        match self {
            SubmitError::Transient(m) | SubmitError::Terminal(m) => m,
        }
    }
    pub fn is_transient(&self) -> bool {
        matches!(self, SubmitError::Transient(_))
    }
}

/// Consume stabilized files from the watcher channel, drop them into
/// the outbox, and wake the drainer. Running in its own OS thread so
/// the mpsc receiver can block without stalling the tokio runtime.
pub fn start_intake(
    rx: mpsc::Receiver<StabilizedFile>,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    app_handle: AppHandle,
    drainer_wake: Arc<tokio::sync::Notify>,
) {
    std::thread::spawn(move || {
        for file in rx {
            if let Err(e) = intake_one(&file, &config_mgr, &db, &app_handle) {
                log::error!("Intake failed for {}: {}", file.path.display(), e);
            }
            drainer_wake.notify_waiters();
        }
    });
}

fn intake_one(
    file: &StabilizedFile,
    config_mgr: &ConfigManager,
    db: &Database,
    app_handle: &AppHandle,
) -> Result<(), String> {
    let file_name = file
        .path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let folder = config_mgr
        .get_folder(&file.folder_id)
        .ok_or_else(|| format!("Folder config not found: {}", file.folder_id))?;

    // Compute batch_group at intake time so that windows stay stable
    // even if the folder config changes later. A file dropped into a
    // batch-enabled folder at time T always submits with its peers
    // from the same window, regardless of later toggles.
    let batch_group = if folder.batch_enabled {
        Some(batch_group_key(
            &folder.id,
            folder.batch_window_secs.max(1.0),
            chrono::Utc::now().timestamp(),
        ))
    } else {
        None
    };

    let record = JobRecord {
        id: uuid::Uuid::new_v4().to_string(),
        folder_id: file.folder_id.clone(),
        file_name,
        file_path: file.path.to_string_lossy().to_string(),
        status: status::QUEUED_OFFLINE.to_string(),
        job_id: None,
        summary: None,
        routed_to: None,
        submitted_at: chrono::Utc::now().to_rfc3339(),
        completed_at: None,
        error_message: None,
        share_links: None,
        jdf_path: file
            .jdf_path
            .as_ref()
            .map(|p| p.to_string_lossy().to_string()),
        batch_group,
        batch_id: None,
        next_retry_at: None,
        retry_attempts: 0,
    };

    db.insert_job(&record)?;
    emit_job_update(app_handle, &record);
    Ok(())
}

/// `{folder_id}-{floor(now / window)}` — identical for files that
/// arrive within the same window, different once the window rolls.
pub fn batch_group_key(folder_id: &str, window_secs: f64, now_epoch: i64) -> String {
    let window = window_secs.max(1.0) as i64;
    let bucket = now_epoch / window;
    format!("{}-{}", folder_id, bucket)
}

fn emit_job_update(app_handle: &AppHandle, record: &JobRecord) {
    app_handle.emit("job-update", record).ok();
}

// ── Submission primitives ─────────────────────────────────────

/// Attempt one submit + poll cycle for a single queued row. Updates
/// the DB row and emits `job-update` on every state change. Returns
/// `Ok(())` on terminal success, an `Err(SubmitError)` that the
/// drainer classifies to decide between retry and permanent failure.
pub async fn attempt_single(
    record: JobRecord,
    folder: FolderConfig,
    base_url: String,
    api_key: String,
    connectivity: ConnectivityState,
    db: Arc<Database>,
    app_handle: AppHandle,
) -> Result<(), SubmitError> {
    let mut record = record;
    let client = http_client();
    let file_path = PathBuf::from(&record.file_path);
    let jdf_path = record.jdf_path.as_ref().map(PathBuf::from);

    // Mark processing just before the actual upload — brief, but gives
    // the UI a "submitting" state while the multipart is on the wire.
    record.status = status::PROCESSING.to_string();
    record.next_retry_at = None;
    db.update_job(&record).ok();
    emit_job_update(&app_handle, &record);

    let api_job_id = match submit_single(&client, &base_url, &api_key, &file_path, &folder, &jdf_path, &connectivity).await {
        Ok(id) => id,
        Err(e) => return handle_submit_err(&mut record, &folder, e, &db, &app_handle, &jdf_path),
    };

    // Auth probe via /health stays green during an auth outage, so a
    // successful submit is the only reliable "yes, the key works"
    // signal. Clear any stale auth-failure flag now.
    connectivity.record_auth_success();

    record.job_id = Some(api_job_id.clone());
    record.retry_attempts = 0;
    db.update_job(&record).ok();
    emit_job_update(&app_handle, &record);

    // Approval chain attach — non-fatal.
    if let Some(tpl) = folder.approval_template_id.as_deref() {
        let tpl = tpl.trim();
        if !tpl.is_empty() {
            if let Err(e) =
                attach_approval_chain(&client, &base_url, &api_key, &api_job_id, tpl).await
            {
                log::warn!("Approval chain attach failed: {}", e);
                record.error_message = Some(advisory(
                    &record.error_message,
                    &format!("Approval chain attach failed: {}", e),
                ));
                db.update_job(&record).ok();
                emit_job_update(&app_handle, &record);
            }
        }
    }

    let interval = Duration::from_secs_f64(folder.poll_interval_secs.max(1.0));
    let poll_result =
        poll_until_done(&client, &base_url, &api_key, &api_job_id, interval, &connectivity).await;

    finalize(&mut record, &folder, poll_result, &db, &app_handle, &jdf_path)
}

/// Batch variant — one POST /api/v1/batch/submit for a group of
/// records, then one poll loop on /api/v1/batch/{id} that fans
/// per-file status out to each record.
pub async fn attempt_batch(
    mut records: Vec<JobRecord>,
    folder: FolderConfig,
    base_url: String,
    api_key: String,
    connectivity: ConnectivityState,
    db: Arc<Database>,
    app_handle: AppHandle,
) -> Result<(), SubmitError> {
    let client = http_client();

    // Flip all rows to `processing` up-front so the UI reflects intent.
    for record in &mut records {
        record.status = status::PROCESSING.to_string();
        record.next_retry_at = None;
        db.update_job(record).ok();
        emit_job_update(&app_handle, record);
    }

    let submit_result =
        submit_batch(&client, &base_url, &api_key, &mut records, &folder, &connectivity, &db, &app_handle)
            .await;

    let batch = match submit_result {
        Ok(b) => b,
        Err(e) => {
            // All rows in the batch share the fate of the submit call.
            let is_transient = e.is_transient();
            for record in records.iter_mut() {
                record.error_message = Some(e.message().to_string());
                if is_transient {
                    record.status = status::QUEUED_RETRY.to_string();
                    record.retry_attempts = record.retry_attempts.saturating_add(1);
                    record.next_retry_at = Some(next_retry(record.retry_attempts));
                } else {
                    record.status = status::ERROR.to_string();
                    record.completed_at = Some(chrono::Utc::now().to_rfc3339());
                    let jdf = record.jdf_path.as_ref().map(PathBuf::from);
                    router::route_file(
                        &PathBuf::from(&record.file_path),
                        &folder.error_dir,
                        record,
                        folder.write_sidecar,
                        jdf.as_deref(),
                    );
                }
                db.update_job(record).ok();
                emit_job_update(&app_handle, record);
            }
            return Err(e);
        }
    };

    // Batch POST succeeded → the API key works.
    connectivity.record_auth_success();

    // Pair engine-assigned job ids back onto local records by
    // file_name. Engine preserves file names, and watcher guarantees
    // unique file names within a batch window (same-stem PDFs can't
    // stabilize twice in the same window).
    for info in &batch.jobs {
        if let Some(r) = records.iter_mut().find(|r| r.file_name == info.file_name) {
            r.job_id = Some(info.job_id.clone());
            r.batch_id = Some(batch.batch_id.clone());
            r.retry_attempts = 0;
            db.update_job(r).ok();
            emit_job_update(&app_handle, r);
        }
    }

    // Poll the batch endpoint and fan out per-file results.
    let interval = Duration::from_secs_f64(folder.poll_interval_secs.max(1.0));
    let poll_result =
        poll_batch_until_done(&client, &base_url, &api_key, &batch.batch_id, interval, &connectivity).await;

    match poll_result {
        Ok(final_status) => {
            // For each record, pull its current status by polling the
            // single-job endpoint — the batch-status response only tells
            // us aggregate completion, not per-file verdict.
            for record in records.iter_mut() {
                if let Some(api_job_id) = record.job_id.clone() {
                    match fetch_job_status(&client, &base_url, &api_key, &api_job_id).await {
                        Ok(resp) => apply_final(record, &folder, resp, &db, &app_handle),
                        Err(e) => {
                            if e.is_transient() {
                                record.status = status::QUEUED_RETRY.to_string();
                                record.retry_attempts =
                                    record.retry_attempts.saturating_add(1);
                                record.next_retry_at = Some(next_retry(record.retry_attempts));
                            } else {
                                record.status = status::ERROR.to_string();
                                record.error_message = Some(e.message().to_string());
                                record.completed_at = Some(chrono::Utc::now().to_rfc3339());
                            }
                            db.update_job(record).ok();
                            emit_job_update(&app_handle, record);
                        }
                    }
                }
            }
            log::info!(
                "Batch {} finished (status={}, {} rows)",
                batch.batch_id,
                final_status,
                records.len()
            );
            Ok(())
        }
        Err(e) => {
            let is_transient = e.is_transient();
            for record in records.iter_mut() {
                if is_transient {
                    record.status = status::QUEUED_RETRY.to_string();
                    record.retry_attempts = record.retry_attempts.saturating_add(1);
                    record.next_retry_at = Some(next_retry(record.retry_attempts));
                } else {
                    record.status = status::ERROR.to_string();
                    record.error_message = Some(e.message().to_string());
                    record.completed_at = Some(chrono::Utc::now().to_rfc3339());
                }
                db.update_job(record).ok();
                emit_job_update(&app_handle, record);
            }
            Err(e)
        }
    }
}

/// Resume an in-flight row after app restart: the engine already has
/// the job, we just need to keep polling until it's done. Classifies
/// errors the same way `attempt_single` does.
pub async fn resume_polling(
    record: JobRecord,
    folder: FolderConfig,
    base_url: String,
    api_key: String,
    connectivity: ConnectivityState,
    db: Arc<Database>,
    app_handle: AppHandle,
) -> Result<(), SubmitError> {
    let mut record = record;
    let api_job_id = match record.job_id.clone() {
        Some(id) => id,
        None => {
            // Inconsistent: processing without an engine id. Push
            // back to retry — drainer will resubmit.
            record.status = status::QUEUED_RETRY.to_string();
            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
            return Ok(());
        }
    };
    let client = http_client();
    let jdf_path = record.jdf_path.as_ref().map(PathBuf::from);
    let interval = Duration::from_secs_f64(folder.poll_interval_secs.max(1.0));
    let poll_result =
        poll_until_done(&client, &base_url, &api_key, &api_job_id, interval, &connectivity).await;
    finalize(&mut record, &folder, poll_result, &db, &app_handle, &jdf_path)
}

// ── Low-level HTTP helpers ────────────────────────────────────

fn http_client() -> reqwest::Client {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(120))
        .build()
        .expect("build reqwest client")
}

fn classify_status(status: reqwest::StatusCode, body: &str) -> SubmitError {
    let s = status.as_u16();
    if s == 429 || (500..=599).contains(&s) {
        SubmitError::Transient(format!("API {}: {}", status, body))
    } else {
        SubmitError::Terminal(format!("API {}: {}", status, body))
    }
}

/// Check if a status code indicates an auth failure (401 or 403).
/// Callers use this to flip the connectivity pill to "auth failing".
fn is_auth_failure(status: reqwest::StatusCode) -> bool {
    status == reqwest::StatusCode::UNAUTHORIZED
        || status == reqwest::StatusCode::FORBIDDEN
}

fn classify_transport(e: reqwest::Error) -> SubmitError {
    // reqwest doesn't neatly expose "timeout vs offline vs reset"
    // without feature flags. Treat every transport error as
    // transient — 4xx/5xx are handled by `classify_status`.
    SubmitError::Transient(format!("Transport: {}", e))
}

/// Exponential backoff schedule: 15s, 30s, 1m, 2m, 4m, cap 15m.
fn next_retry(attempt: u32) -> String {
    let seconds: i64 = match attempt.saturating_sub(1).min(6) {
        0 => 15,
        1 => 30,
        2 => 60,
        3 => 120,
        4 => 240,
        5 => 480,
        _ => 900,
    };
    (chrono::Utc::now() + chrono::Duration::seconds(seconds)).to_rfc3339()
}

fn advisory(existing: &Option<String>, note: &str) -> String {
    match existing.as_deref() {
        Some(s) if !s.is_empty() => format!("{} | {}", s, note),
        _ => note.to_string(),
    }
}

fn handle_submit_err(
    record: &mut JobRecord,
    folder: &FolderConfig,
    err: SubmitError,
    db: &Database,
    app_handle: &AppHandle,
    jdf_path: &Option<PathBuf>,
) -> Result<(), SubmitError> {
    let is_transient = err.is_transient();
    record.error_message = Some(err.message().to_string());
    if is_transient {
        record.status = status::QUEUED_RETRY.to_string();
        record.retry_attempts = record.retry_attempts.saturating_add(1);
        record.next_retry_at = Some(next_retry(record.retry_attempts));
    } else {
        record.status = status::ERROR.to_string();
        record.completed_at = Some(chrono::Utc::now().to_rfc3339());
        router::route_file(
            &PathBuf::from(&record.file_path),
            &folder.error_dir,
            record,
            folder.write_sidecar,
            jdf_path.as_deref(),
        );
    }
    db.update_job(record).ok();
    emit_job_update(app_handle, record);
    Err(err)
}

fn finalize(
    record: &mut JobRecord,
    folder: &FolderConfig,
    poll_result: Result<JobStatusResponse, SubmitError>,
    db: &Database,
    app_handle: &AppHandle,
    jdf_path: &Option<PathBuf>,
) -> Result<(), SubmitError> {
    match poll_result {
        Ok(resp) => {
            apply_final(record, folder, resp, db, app_handle);
            Ok(())
        }
        Err(e) => {
            let is_transient = e.is_transient();
            record.error_message = Some(e.message().to_string());
            if is_transient {
                record.status = status::QUEUED_RETRY.to_string();
                record.retry_attempts = record.retry_attempts.saturating_add(1);
                record.next_retry_at = Some(next_retry(record.retry_attempts));
            } else {
                record.status = status::ERROR.to_string();
                record.completed_at = Some(chrono::Utc::now().to_rfc3339());
                router::route_file(
                    &PathBuf::from(&record.file_path),
                    &folder.error_dir,
                    record,
                    folder.write_sidecar,
                    jdf_path.as_deref(),
                );
            }
            db.update_job(record).ok();
            emit_job_update(app_handle, record);
            Err(e)
        }
    }
}

fn apply_final(
    record: &mut JobRecord,
    folder: &FolderConfig,
    resp: JobStatusResponse,
    db: &Database,
    app_handle: &AppHandle,
) {
    let summary = resp.summary.map(|s| JobSummary {
        passed: s.passed.unwrap_or(false),
        error_count: s.error_count.unwrap_or(0),
        warning_count: s.warning_count.unwrap_or(0),
        advisory_count: s.advisory_count.unwrap_or(0),
    });
    let passed = summary.as_ref().map(|s| s.passed).unwrap_or(false);
    record.status = if passed { status::PASSED } else { status::FAILED }.to_string();
    record.summary = summary;
    record.completed_at = Some(chrono::Utc::now().to_rfc3339());

    let target_dir = if passed { &folder.pass_dir } else { &folder.fail_dir };
    let jdf = record.jdf_path.as_ref().map(PathBuf::from);
    if let Some(routed) = router::route_file(
        &PathBuf::from(&record.file_path),
        target_dir,
        record,
        folder.write_sidecar,
        jdf.as_deref(),
    ) {
        record.routed_to = Some(routed);
    }
    db.update_job(record).ok();
    emit_job_update(app_handle, record);
}

// ── Single-file submit ────────────────────────────────────────

async fn submit_single(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    file_path: &Path,
    folder: &FolderConfig,
    jdf_path: &Option<PathBuf>,
    connectivity: &ConnectivityState,
) -> Result<String, SubmitError> {
    let file_bytes = tokio::fs::read(file_path)
        .await
        .map_err(|e| SubmitError::Terminal(format!("Failed to read file: {}", e)))?;

    let file_name = file_path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("file")
        .to_string();

    // Custom endpoint path — takes only `file`.
    if let Some(endpoint_id) = folder.endpoint_id.as_deref() {
        let endpoint_id = endpoint_id.trim();
        if !endpoint_id.is_empty() {
            let part = multipart::Part::bytes(file_bytes)
                .file_name(file_name)
                .mime_str("application/octet-stream")
                .map_err(|e| SubmitError::Terminal(format!("MIME error: {}", e)))?;
            let form = multipart::Form::new().part("file", part);
            let url = format!(
                "{}/api/v1/endpoints/{}/submit",
                base_url.trim_end_matches('/'),
                endpoint_id
            );
            return send_for_job_id(client, &url, api_key, form, connectivity).await;
        }
    }

    // External preflight report — `preflight_source=external`.
    if is_external_report(file_path, folder) {
        let report_part = multipart::Part::bytes(file_bytes)
            .file_name(file_name)
            .mime_str("application/octet-stream")
            .map_err(|e| SubmitError::Terminal(format!("MIME error: {}", e)))?;
        let mut form = multipart::Form::new()
            .text("preflight_source", "external")
            .part("external_report", report_part);
        if let Some(fmt) = folder.external_format.as_deref() {
            let fmt = fmt.trim();
            if !fmt.is_empty() {
                form = form.text("external_format", fmt.to_string());
            }
        }
        if let Some(brand) = resolve_brand_param(folder) {
            form = form.text("brand", brand);
        }
        let url = format!("{}/api/v1/jobs", base_url.trim_end_matches('/'));
        return send_for_job_id(client, &url, api_key, form, connectivity).await;
    }

    // Default preflight path.
    let part = multipart::Part::bytes(file_bytes)
        .file_name(file_name)
        .mime_str("application/octet-stream")
        .map_err(|e| SubmitError::Terminal(format!("MIME error: {}", e)))?;
    let mut form = multipart::Form::new()
        .text("profile_id", folder.profile_id.clone())
        .part("file", part);
    if let Some(brand) = resolve_brand_param(folder) {
        form = form.text("brand", brand);
    }
    if let Some(jdf) = jdf_path {
        if jdf.exists() {
            if let Ok(bytes) = tokio::fs::read(jdf).await {
                let jdf_name = jdf
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("file.jdf")
                    .to_string();
                if let Ok(part) = multipart::Part::bytes(bytes)
                    .file_name(jdf_name)
                    .mime_str("application/octet-stream")
                {
                    form = form.part("jdf_file", part);
                }
            }
        }
    }
    let url = format!("{}/api/v1/jobs", base_url.trim_end_matches('/'));
    send_for_job_id(client, &url, api_key, form, connectivity).await
}

async fn send_for_job_id(
    client: &reqwest::Client,
    url: &str,
    api_key: &str,
    form: multipart::Form,
    connectivity: &ConnectivityState,
) -> Result<String, SubmitError> {
    let resp = client
        .post(url)
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .send()
        .await
        .map_err(classify_transport)?;
    if !resp.status().is_success() {
        let status = resp.status();
        if is_auth_failure(status) {
            connectivity.record_auth_failure();
        }
        let body = resp.text().await.unwrap_or_default();
        return Err(classify_status(status, &body));
    }
    let data: SubmitResponse = resp
        .json()
        .await
        .map_err(|e| SubmitError::Terminal(format!("Parse: {}", e)))?;
    Ok(data.job_id)
}

// ── Batch submit ──────────────────────────────────────────────

/// Build and post a batch request, skipping (and marking `error`)
/// any records whose source file is no longer on disk. Returns the
/// batch response. When zero files survive the disk check, returns
/// `Terminal("No readable files in batch")`.
async fn submit_batch(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    records: &mut [JobRecord],
    folder: &FolderConfig,
    connectivity: &ConnectivityState,
    db: &Database,
    app_handle: &AppHandle,
) -> Result<BatchSubmitResponse, SubmitError> {
    let mut form = multipart::Form::new().text("profile_id", folder.profile_id.clone());
    let mut any_files = false;
    for record in records.iter_mut() {
        let path = PathBuf::from(&record.file_path);
        let bytes = match tokio::fs::read(&path).await {
            Ok(b) => b,
            Err(e) => {
                // Don't abort the whole batch because one source
                // file moved/was deleted. Mark this row `error` and
                // keep building the form from the rest.
                log::warn!(
                    "Batch: skipping {} (read failed: {})",
                    path.display(),
                    e
                );
                record.status = status::ERROR.to_string();
                record.error_message = Some(format!(
                    "Source file no longer readable: {}",
                    e
                ));
                record.completed_at = Some(chrono::Utc::now().to_rfc3339());
                db.update_job(record).ok();
                emit_job_update(app_handle, record);
                continue;
            }
        };
        let file_name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("file")
            .to_string();
        let part = multipart::Part::bytes(bytes)
            .file_name(file_name)
            .mime_str("application/octet-stream")
            .map_err(|e| SubmitError::Terminal(format!("MIME: {}", e)))?;
        form = form.part("files", part);
        any_files = true;
    }

    if !any_files {
        return Err(SubmitError::Terminal(
            "No readable files in batch.".to_string(),
        ));
    }

    let url = format!("{}/api/v1/batch/submit", base_url.trim_end_matches('/'));
    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .send()
        .await
        .map_err(classify_transport)?;
    if !resp.status().is_success() {
        let status = resp.status();
        if is_auth_failure(status) {
            connectivity.record_auth_failure();
        }
        let body = resp.text().await.unwrap_or_default();
        return Err(classify_status(status, &body));
    }
    resp.json::<BatchSubmitResponse>()
        .await
        .map_err(|e| SubmitError::Terminal(format!("Parse batch response: {}", e)))
}

async fn poll_batch_until_done(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    batch_id: &str,
    interval: Duration,
    connectivity: &ConnectivityState,
) -> Result<String, SubmitError> {
    let url = format!(
        "{}/api/v1/batch/{}",
        base_url.trim_end_matches('/'),
        batch_id
    );
    let max_attempts = 240; // ~20 minutes at 5s intervals
    for _ in 0..max_attempts {
        tokio::time::sleep(interval).await;
        if !connectivity.is_online() {
            return Err(SubmitError::Transient("Offline during polling".into()));
        }
        let resp = client
            .get(&url)
            .header("Authorization", format!("Bearer {}", api_key))
            .send()
            .await
            .map_err(classify_transport)?;
        if resp.status() == 429 {
            continue;
        }
        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(classify_status(status, &body));
        }
        let data: BatchStatusResponse = resp
            .json()
            .await
            .map_err(|e| SubmitError::Terminal(format!("Parse: {}", e)))?;
        match data.status.as_str() {
            "complete" | "failed" | "partial" => return Ok(data.status),
            _ => continue,
        }
    }
    Err(SubmitError::Transient("Batch polling timed out".into()))
}

// ── Per-job polling ───────────────────────────────────────────

async fn poll_until_done(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    job_id: &str,
    interval: Duration,
    connectivity: &ConnectivityState,
) -> Result<JobStatusResponse, SubmitError> {
    let max_attempts = 240;
    for _ in 0..max_attempts {
        tokio::time::sleep(interval).await;
        if !connectivity.is_online() {
            return Err(SubmitError::Transient("Offline during polling".into()));
        }
        match fetch_job_status_with_auth_tracking(
            client,
            base_url,
            api_key,
            job_id,
            connectivity,
        )
        .await
        {
            Ok(resp) => match resp.status.as_str() {
                "complete" | "completed" | "failed" => return Ok(resp),
                _ => continue,
            },
            Err(SubmitError::Transient(_)) => {
                // Keep polling on transient errors — the engine may
                // momentarily blip (e.g. rolling deploy). Limit is
                // `max_attempts` so we won't spin forever.
                continue;
            }
            Err(e) => return Err(e),
        }
    }
    Err(SubmitError::Transient("Polling timed out".into()))
}

async fn fetch_job_status(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    job_id: &str,
) -> Result<JobStatusResponse, SubmitError> {
    fetch_job_status_inner(client, base_url, api_key, job_id, None).await
}

async fn fetch_job_status_with_auth_tracking(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    job_id: &str,
    connectivity: &ConnectivityState,
) -> Result<JobStatusResponse, SubmitError> {
    fetch_job_status_inner(client, base_url, api_key, job_id, Some(connectivity)).await
}

async fn fetch_job_status_inner(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    job_id: &str,
    connectivity: Option<&ConnectivityState>,
) -> Result<JobStatusResponse, SubmitError> {
    let url = format!("{}/api/v1/jobs/{}", base_url.trim_end_matches('/'), job_id);
    let resp = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .send()
        .await
        .map_err(classify_transport)?;
    if resp.status() == 429 {
        return Err(SubmitError::Transient("Rate limited".into()));
    }
    if !resp.status().is_success() {
        let status = resp.status();
        if is_auth_failure(status) {
            if let Some(c) = connectivity {
                c.record_auth_failure();
            }
        }
        let body = resp.text().await.unwrap_or_default();
        return Err(classify_status(status, &body));
    }
    resp.json::<JobStatusResponse>()
        .await
        .map_err(|e| SubmitError::Terminal(format!("Parse: {}", e)))
}

// ── Approval chain attach ─────────────────────────────────────

async fn attach_approval_chain(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    api_job_id: &str,
    template_id: &str,
) -> Result<(), String> {
    let url = format!(
        "{}/api/v1/jobs/{}/approval-chain",
        base_url.trim_end_matches('/'),
        api_job_id
    );
    let body = serde_json::json!({ "template_id": template_id });
    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;
    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("API error {}: {}", status, body));
    }
    Ok(())
}

// ── Shared helpers ────────────────────────────────────────────

/// Returns `true` only when the folder has opted into external-report
/// submission AND the file extension is one the engine expects.
fn is_external_report(path: &Path, folder: &FolderConfig) -> bool {
    if folder
        .external_format
        .as_ref()
        .map(|s| s.trim().is_empty())
        .unwrap_or(true)
    {
        return false;
    }
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase());
    matches!(ext.as_deref(), Some("xml") | Some("json"))
}

/// Build the `brand=<value>` form field (or `None` to fall back to the tenant
/// default). Profile mode with a missing / blank UUID is treated as `Default`.
fn resolve_brand_param(folder: &FolderConfig) -> Option<String> {
    match folder.brand_mode {
        BrandMode::Default => None,
        BrandMode::Anonymous => Some("anonymous".to_string()),
        BrandMode::Lintpdf => Some("lintpdf".to_string()),
        BrandMode::Profile => folder
            .brand_profile_id
            .as_ref()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .map(|id| format!("profile:{}", id)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn batch_group_key_is_stable_within_window() {
        // Same window → same key.
        let k1 = batch_group_key("f1", 10.0, 1_000_000);
        let k2 = batch_group_key("f1", 10.0, 1_000_009);
        assert_eq!(k1, k2);
    }

    #[test]
    fn batch_group_key_rolls_at_boundary() {
        let k1 = batch_group_key("f1", 10.0, 1_000_009);
        let k2 = batch_group_key("f1", 10.0, 1_000_010);
        assert_ne!(k1, k2);
    }

    #[test]
    fn batch_group_key_is_folder_scoped() {
        let k1 = batch_group_key("f1", 10.0, 1_000_000);
        let k2 = batch_group_key("f2", 10.0, 1_000_000);
        assert_ne!(k1, k2);
    }

    #[test]
    fn batch_group_key_rejects_sub_second_window() {
        // window clamp: 0s or 0.5s should still produce a deterministic key.
        let k = batch_group_key("f1", 0.0, 1_000_000);
        assert!(k.starts_with("f1-"));
    }

    fn make_folder(mode: BrandMode, profile: Option<&str>) -> FolderConfig {
        FolderConfig {
            id: "test".to_string(),
            name: "test".to_string(),
            enabled: true,
            watch_dir: String::new(),
            profile_id: "lintpdf-default".to_string(),
            pass_dir: String::new(),
            fail_dir: String::new(),
            error_dir: String::new(),
            write_sidecar: false,
            stabilization_secs: 2.0,
            poll_interval_secs: 5.0,
            file_extensions: vec![],
            brand_mode: mode,
            brand_profile_id: profile.map(String::from),
            jdf_companion_timeout_secs: 30.0,
            endpoint_id: None,
            external_format: None,
            approval_template_id: None,
            batch_enabled: false,
            batch_window_secs: 10.0,
        }
    }

    #[test]
    fn external_report_only_when_opted_in() {
        let mut folder = make_folder(BrandMode::Default, None);
        assert!(!is_external_report(&PathBuf::from("/w/report.xml"), &folder));
        folder.external_format = Some("pitstop_xml".to_string());
        assert!(is_external_report(&PathBuf::from("/w/report.xml"), &folder));
        assert!(is_external_report(&PathBuf::from("/w/report.json"), &folder));
        assert!(!is_external_report(&PathBuf::from("/w/art.pdf"), &folder));
    }

    #[test]
    fn brand_param_serialization() {
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Default, None)),
            None
        );
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Anonymous, None)),
            Some("anonymous".into())
        );
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Lintpdf, None)),
            Some("lintpdf".into())
        );
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Profile, Some("abc"))),
            Some("profile:abc".into())
        );
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Profile, None)),
            None
        );
    }

    #[test]
    fn next_retry_is_monotonically_increasing_until_cap() {
        // First attempt = 15s, second = 30s, etc. We can't compare
        // RFC3339 strings directly — parse them.
        let t0 = chrono::DateTime::parse_from_rfc3339(&next_retry(1)).unwrap();
        let t1 = chrono::DateTime::parse_from_rfc3339(&next_retry(2)).unwrap();
        let t5 = chrono::DateTime::parse_from_rfc3339(&next_retry(5)).unwrap();
        let t10 = chrono::DateTime::parse_from_rfc3339(&next_retry(10)).unwrap();
        assert!(t1 > t0);
        assert!(t5 > t1);
        // Capped — attempt 10 shouldn't be 10× attempt 5.
        assert!(
            (t10 - t5).num_seconds() < 1000,
            "backoff should cap, got {}s",
            (t10 - t5).num_seconds()
        );
    }

    #[test]
    fn classify_status_splits_retryable_from_terminal() {
        let err = classify_status(reqwest::StatusCode::from_u16(503).unwrap(), "");
        assert!(matches!(err, SubmitError::Transient(_)));
        let err = classify_status(reqwest::StatusCode::from_u16(429).unwrap(), "");
        assert!(matches!(err, SubmitError::Transient(_)));
        let err = classify_status(reqwest::StatusCode::from_u16(400).unwrap(), "");
        assert!(matches!(err, SubmitError::Terminal(_)));
        let err = classify_status(reqwest::StatusCode::from_u16(403).unwrap(), "");
        assert!(matches!(err, SubmitError::Terminal(_)));
    }
}
