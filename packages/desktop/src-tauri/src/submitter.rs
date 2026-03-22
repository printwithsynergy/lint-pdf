use reqwest::multipart;
use serde::Deserialize;
use std::path::Path;
use std::sync::mpsc;
use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, Emitter};

use crate::config::ConfigManager;
use crate::db::{Database, JobRecord, JobSummary};
use crate::router;
use crate::watcher::StabilizedFile;

#[derive(Debug, Deserialize)]
struct SubmitResponse {
    job_id: String,
}

#[derive(Debug, Deserialize)]
struct JobStatusResponse {
    status: String,
    summary: Option<ApiSummary>,
    findings: Option<Vec<serde_json::Value>>,
}

#[derive(Debug, Deserialize)]
struct ApiSummary {
    passed: Option<bool>,
    aground_count: Option<u32>,
    squall_count: Option<u32>,
    advisory_count: Option<u32>,
}

pub fn start_submitter(
    rx: mpsc::Receiver<StabilizedFile>,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    app_handle: AppHandle,
) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .worker_threads(2)
            .build()
            .expect("Failed to create tokio runtime");

        for file in rx {
            let config_mgr = Arc::clone(&config_mgr);
            let db = Arc::clone(&db);
            let handle = app_handle.clone();

            rt.spawn(async move {
                process_file(file, config_mgr, db, handle).await;
            });
        }
    });
}

async fn process_file(
    file: StabilizedFile,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    app_handle: AppHandle,
) {
    let file_name = file
        .path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let job_id_local = uuid::Uuid::new_v4().to_string();

    let mut record = JobRecord {
        id: job_id_local.clone(),
        folder_id: file.folder_id.clone(),
        file_name: file_name.clone(),
        file_path: file.path.to_string_lossy().to_string(),
        status: "processing".to_string(),
        job_id: None,
        summary: None,
        routed_to: None,
        submitted_at: chrono::Utc::now().to_rfc3339(),
        completed_at: None,
        error_message: None,
    };

    db.insert_job(&record).ok();
    emit_job_update(&app_handle, &record);

    let config = config_mgr.get();
    let folder = match config.folders.iter().find(|f| f.id == file.folder_id) {
        Some(f) => f.clone(),
        None => {
            record.status = "error".to_string();
            record.error_message = Some("Folder config not found".to_string());
            record.completed_at = Some(chrono::Utc::now().to_rfc3339());
            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
            return;
        }
    };

    // Submit to API
    let client = reqwest::Client::new();
    let submit_result = submit_file(&client, &config.base_url, &config.api_key, &file.path, &folder.profile_id).await;

    let api_job_id = match submit_result {
        Ok(id) => id,
        Err(e) => {
            log::error!("Submit failed for {}: {}", file_name, e);
            record.status = "error".to_string();
            record.error_message = Some(format!("Submission failed: {}", e));
            record.completed_at = Some(chrono::Utc::now().to_rfc3339());
            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
            router::route_file(&file.path, &folder.error_dir, &record, folder.write_sidecar);
            return;
        }
    };

    record.job_id = Some(api_job_id.clone());
    db.update_job(&record).ok();
    emit_job_update(&app_handle, &record);

    // Poll for results
    let poll_result = poll_job(
        &client,
        &config.base_url,
        &config.api_key,
        &api_job_id,
        Duration::from_secs_f64(folder.poll_interval_secs),
    )
    .await;

    match poll_result {
        Ok(status) => {
            let summary = status.summary.map(|s| JobSummary {
                passed: s.passed.unwrap_or(false),
                aground_count: s.aground_count.unwrap_or(0),
                squall_count: s.squall_count.unwrap_or(0),
                advisory_count: s.advisory_count.unwrap_or(0),
            });

            let passed = summary.as_ref().map(|s| s.passed).unwrap_or(false);
            record.status = if passed { "passed" } else { "failed" }.to_string();
            record.summary = summary;
            record.completed_at = Some(chrono::Utc::now().to_rfc3339());

            let target_dir = if passed {
                &folder.pass_dir
            } else {
                &folder.fail_dir
            };

            if let Some(routed) = router::route_file(&file.path, target_dir, &record, folder.write_sidecar) {
                record.routed_to = Some(routed);
            }

            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
        }
        Err(e) => {
            log::error!("Polling failed for {}: {}", file_name, e);
            record.status = "error".to_string();
            record.error_message = Some(format!("Polling failed: {}", e));
            record.completed_at = Some(chrono::Utc::now().to_rfc3339());
            router::route_file(&file.path, &folder.error_dir, &record, folder.write_sidecar);
            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
        }
    }
}

async fn submit_file(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    file_path: &Path,
    profile_id: &str,
) -> Result<String, String> {
    let file_bytes = tokio::fs::read(file_path)
        .await
        .map_err(|e| format!("Failed to read file: {}", e))?;

    let file_name = file_path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("file")
        .to_string();

    let part = multipart::Part::bytes(file_bytes)
        .file_name(file_name)
        .mime_str("application/octet-stream")
        .map_err(|e| format!("MIME error: {}", e))?;

    let form = multipart::Form::new()
        .text("profile_id", profile_id.to_string())
        .part("file", part);

    let url = format!("{}/api/v1/jobs", base_url.trim_end_matches('/'));

    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .timeout(Duration::from_secs(120))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;

    if resp.status() == 429 {
        let retry_after = resp
            .headers()
            .get("retry-after")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(5);
        tokio::time::sleep(Duration::from_secs(retry_after)).await;
        return Err("Rate limited, retrying...".to_string());
    }

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("API error {}: {}", status, body));
    }

    let data: SubmitResponse = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(data.job_id)
}

async fn poll_job(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    job_id: &str,
    interval: Duration,
) -> Result<JobStatusResponse, String> {
    let url = format!("{}/api/v1/jobs/{}", base_url.trim_end_matches('/'), job_id);
    let max_attempts = 120; // 10 minutes at 5s intervals

    for _ in 0..max_attempts {
        tokio::time::sleep(interval).await;

        let resp = client
            .get(&url)
            .header("Authorization", format!("Bearer {}", api_key))
            .timeout(Duration::from_secs(30))
            .send()
            .await
            .map_err(|e| format!("Poll HTTP error: {}", e))?;

        if resp.status() == 429 {
            let retry_after = resp
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(10);
            tokio::time::sleep(Duration::from_secs(retry_after)).await;
            continue;
        }

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(format!("Poll API error {}: {}", status, body));
        }

        let data: JobStatusResponse = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse poll response: {}", e))?;

        match data.status.as_str() {
            "complete" | "completed" | "failed" => return Ok(data),
            _ => continue,
        }
    }

    Err("Polling timed out after 10 minutes".to_string())
}

fn emit_job_update(app_handle: &AppHandle, record: &JobRecord) {
    app_handle.emit("job-update", record).ok();
}
