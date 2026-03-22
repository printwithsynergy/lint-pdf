use std::fs;
use std::path::{Path, PathBuf};

use crate::db::JobRecord;

/// Move file to target directory and optionally write sidecar report.
/// Returns the destination path if the file was moved.
pub fn route_file(
    source: &Path,
    target_dir: &str,
    record: &JobRecord,
    write_sidecar: bool,
) -> Option<String> {
    if target_dir.is_empty() {
        // No target dir configured — write sidecar in place if requested
        if write_sidecar {
            write_sidecar_report(source, record);
        }
        return None;
    }

    let target_path = Path::new(target_dir);
    if let Err(e) = fs::create_dir_all(target_path) {
        log::error!("Failed to create directory {}: {}", target_dir, e);
        return None;
    }

    let file_name = source
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("file");

    let dest = resolve_collision(target_path, file_name);

    match fs::rename(source, &dest) {
        Ok(_) => {
            log::info!("Routed {} -> {}", source.display(), dest.display());
            if write_sidecar {
                write_sidecar_report(&dest, record);
            }
            Some(dest.to_string_lossy().to_string())
        }
        Err(e) => {
            // rename might fail across filesystems, try copy+delete
            match fs::copy(source, &dest) {
                Ok(_) => {
                    fs::remove_file(source).ok();
                    log::info!("Copied {} -> {}", source.display(), dest.display());
                    if write_sidecar {
                        write_sidecar_report(&dest, record);
                    }
                    Some(dest.to_string_lossy().to_string())
                }
                Err(copy_err) => {
                    log::error!(
                        "Failed to move {} to {}: rename={}, copy={}",
                        source.display(),
                        dest.display(),
                        e,
                        copy_err
                    );
                    None
                }
            }
        }
    }
}

fn resolve_collision(dir: &Path, file_name: &str) -> PathBuf {
    let dest = dir.join(file_name);
    if !dest.exists() {
        return dest;
    }

    let stem = Path::new(file_name)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or(file_name);
    let ext = Path::new(file_name)
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| format!(".{}", e))
        .unwrap_or_default();

    for i in 1..1000 {
        let candidate = dir.join(format!("{}_{}{}", stem, i, ext));
        if !candidate.exists() {
            return candidate;
        }
    }

    // Fallback with UUID
    dir.join(format!("{}_{}{}", stem, uuid::Uuid::new_v4(), ext))
}

fn write_sidecar_report(file_path: &Path, record: &JobRecord) {
    let sidecar_name = format!(
        "{}.lintpdf.json",
        file_path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("file")
    );

    let sidecar_path = file_path.with_file_name(sidecar_name);

    let report = serde_json::json!({
        "job_id": record.job_id,
        "file_name": record.file_name,
        "status": record.status,
        "summary": record.summary,
        "submitted_at": record.submitted_at,
        "completed_at": record.completed_at,
        "error_message": record.error_message,
    });

    match serde_json::to_string_pretty(&report) {
        Ok(json) => {
            if let Err(e) = fs::write(&sidecar_path, json) {
                log::error!("Failed to write sidecar {}: {}", sidecar_path.display(), e);
            }
        }
        Err(e) => {
            log::error!("Failed to serialize sidecar: {}", e);
        }
    }
}
