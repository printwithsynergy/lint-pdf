use reqwest::multipart;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, Emitter};

use crate::config::{BrandMode, ConfigManager, FolderConfig};
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
    error_count: Option<u32>,
    warning_count: Option<u32>,
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
        share_links: None,
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
    let submit_result = submit_file(
        &client,
        &config.base_url,
        &config.api_key,
        &file.path,
        &folder,
        &file.jdf_path,
    )
    .await;

    let api_job_id = match submit_result {
        Ok(id) => id,
        Err(e) => {
            log::error!("Submit failed for {}: {}", file_name, e);
            record.status = "error".to_string();
            record.error_message = Some(format!("Submission failed: {}", e));
            record.completed_at = Some(chrono::Utc::now().to_rfc3339());
            db.update_job(&record).ok();
            emit_job_update(&app_handle, &record);
            router::route_file(&file.path, &folder.error_dir, &record, folder.write_sidecar, file.jdf_path.as_deref());
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
                error_count: s.error_count.unwrap_or(0),
                warning_count: s.warning_count.unwrap_or(0),
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

            if let Some(routed) = router::route_file(&file.path, target_dir, &record, folder.write_sidecar, file.jdf_path.as_deref()) {
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
            router::route_file(&file.path, &folder.error_dir, &record, folder.write_sidecar, file.jdf_path.as_deref());
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
    folder: &FolderConfig,
    jdf_path: &Option<PathBuf>,
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

    let mut form = multipart::Form::new()
        .text("profile_id", folder.profile_id.clone())
        .part("file", part);

    // Branding — forward the folder's configured brand mode so the engine
    // applies the right report branding. Matches `parse_brand_param` in
    // `lintpdf/reports/service.py`.
    if let Some(brand) = resolve_brand_param(folder) {
        form = form.text("brand", brand);
    }

    // Attach companion JDF/XJDF file if present
    if let Some(jdf) = jdf_path {
        if jdf.exists() {
            match tokio::fs::read(jdf).await {
                Ok(jdf_bytes) => {
                    let jdf_name = jdf
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("file.jdf")
                        .to_string();
                    let jdf_part = multipart::Part::bytes(jdf_bytes)
                        .file_name(jdf_name)
                        .mime_str("application/octet-stream")
                        .map_err(|e| format!("JDF MIME error: {}", e))?;
                    form = form.part("jdf_file", jdf_part);
                }
                Err(e) => {
                    log::warn!("Failed to read JDF sidecar {}: {}", jdf.display(), e);
                }
            }
        }
    }

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

/// Build the `brand=<value>` form field (or `None` to fall back to the tenant
/// default). Profile mode with a missing / blank UUID is treated as `Default`
/// rather than sending an obviously invalid value — the engine would 422 it.
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
    use crate::config::BrandMode;

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
        }
    }

    #[test]
    fn brand_default_sends_nothing() {
        assert_eq!(resolve_brand_param(&make_folder(BrandMode::Default, None)), None);
    }

    #[test]
    fn brand_anonymous_serializes() {
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Anonymous, None)),
            Some("anonymous".to_string())
        );
    }

    #[test]
    fn brand_lintpdf_serializes() {
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Lintpdf, None)),
            Some("lintpdf".to_string())
        );
    }

    #[test]
    fn brand_profile_formats_uuid() {
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Profile, Some("abc-123"))),
            Some("profile:abc-123".to_string())
        );
    }

    #[test]
    fn brand_profile_without_id_falls_back() {
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Profile, None)),
            None
        );
        assert_eq!(
            resolve_brand_param(&make_folder(BrandMode::Profile, Some("   "))),
            None
        );
    }
}
