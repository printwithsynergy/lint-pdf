//! Outbox drainer — the one place that decides what submits, when.
//!
//! The submitter only exposes pure `attempt_single` / `attempt_batch`
//! primitives. This module is the supervisor:
//!
//! 1. Waits for a wake signal (connectivity change, new intake,
//!    periodic tick, or app startup).
//! 2. If online, queries `jobs` for rows eligible to submit
//!    (`status IN (queued_offline, queued_retry)` with
//!    `next_retry_at` in the past).
//! 3. Groups rows by `batch_group`; null groups are singletons.
//! 4. Dispatches each group to the matching attempt primitive.
//! 5. Also resumes jobs stuck in `processing` at startup — the engine
//!    accepted them, we just need to keep polling.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tauri::AppHandle;
use tokio::sync::Notify;

use crate::config::ConfigManager;
use crate::connectivity::ConnectivityState;
use crate::db::{Database, JobRecord};
use crate::submitter;

const PERIODIC_TICK: Duration = Duration::from_secs(30);

/// Spawn the drainer loop on the caller's tokio runtime. The returned
/// `Arc<Notify>` is the "wake me" handle — signal it after every
/// file intake to trigger an immediate drain attempt.
pub fn start(
    runtime: &tokio::runtime::Handle,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    connectivity: ConnectivityState,
    app_handle: AppHandle,
) -> Arc<Notify> {
    let wake = Arc::new(Notify::new());
    let loop_wake = Arc::clone(&wake);
    runtime.spawn(async move {
        // Wait for the connectivity monitor's first probe to complete
        // before we do anything else. Otherwise, on cold-boot with an
        // offline host, we'd start submitting against the optimistic
        // `online: true` assumption and burn a round-trip per row.
        connectivity.initial_probe_done.notified().await;

        // Startup: resume any rows that were mid-flight when the app
        // last quit. The engine already has these jobs; we just need
        // to poll to completion. Skip if offline — polling is synced
        // to connectivity state inside the submitter.
        resume_in_flight(&config_mgr, &db, &connectivity, &app_handle).await;

        drain_loop(loop_wake, config_mgr, db, connectivity, app_handle).await;
    });
    wake
}

async fn drain_loop(
    wake: Arc<Notify>,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    connectivity: ConnectivityState,
    app_handle: AppHandle,
) {
    loop {
        // Wait for: connectivity change, new intake, or periodic tick.
        tokio::select! {
            _ = wake.notified() => {},
            _ = connectivity.changed.notified() => {},
            _ = tokio::time::sleep(PERIODIC_TICK) => {},
        }

        if !connectivity.is_online() {
            continue;
        }

        let now = chrono::Utc::now().to_rfc3339();
        let ready = match db.get_queued_ready(&now) {
            Ok(r) => r,
            Err(e) => {
                log::error!("Drainer query failed: {}", e);
                continue;
            }
        };
        if ready.is_empty() {
            continue;
        }

        // Group by batch_group. `None` goes into singleton bucket
        // (every row a group of 1); non-null collapses rows together.
        let (singles, batches) = partition_by_group(ready);

        let config = config_mgr.get();
        let base_url = config.base_url.clone();
        let api_key = config.api_key.clone();

        for record in singles {
            let folder = match config_mgr.get_folder(&record.folder_id) {
                Some(f) => f,
                None => {
                    log::warn!(
                        "Drainer: orphan row {} — folder {} is gone, skipping",
                        record.id,
                        record.folder_id
                    );
                    continue;
                }
            };
            let db = Arc::clone(&db);
            let handle = app_handle.clone();
            let conn = connectivity.clone();
            let base = base_url.clone();
            let key = api_key.clone();
            tokio::spawn(async move {
                let _ = submitter::attempt_single(
                    record, folder, base, key, conn, db, handle,
                )
                .await;
            });
        }

        for (_group_key, group) in batches {
            // Every row in a batch group shares the same folder by
            // construction (`batch_group` key is folder-scoped), so
            // resolving from the first row is safe.
            let folder_id = match group.first() {
                Some(r) => r.folder_id.clone(),
                None => continue,
            };
            let folder = match config_mgr.get_folder(&folder_id) {
                Some(f) => f,
                None => {
                    log::warn!("Drainer: batch orphan — folder {} gone", folder_id);
                    continue;
                }
            };
            let db = Arc::clone(&db);
            let handle = app_handle.clone();
            let conn = connectivity.clone();
            let base = base_url.clone();
            let key = api_key.clone();
            tokio::spawn(async move {
                let _ =
                    submitter::attempt_batch(group, folder, base, key, conn, db, handle).await;
            });
        }
    }
}

/// Separate rows into (singletons, batched groups). Batched groups
/// are keyed by their `batch_group` string so the caller can iterate
/// each group independently.
pub fn partition_by_group(
    rows: Vec<JobRecord>,
) -> (Vec<JobRecord>, HashMap<String, Vec<JobRecord>>) {
    let mut singles = Vec::new();
    let mut groups: HashMap<String, Vec<JobRecord>> = HashMap::new();
    for row in rows {
        match row.batch_group.clone() {
            Some(key) if !key.is_empty() => {
                groups.entry(key).or_default().push(row);
            }
            _ => singles.push(row),
        }
    }
    (singles, groups)
}

async fn resume_in_flight(
    config_mgr: &ConfigManager,
    db: &Arc<Database>,
    connectivity: &ConnectivityState,
    app_handle: &AppHandle,
) {
    let rows = match db.get_in_flight() {
        Ok(r) => r,
        Err(e) => {
            log::warn!("Drainer: get_in_flight failed: {}", e);
            return;
        }
    };
    if rows.is_empty() {
        return;
    }
    log::info!("Resuming {} in-flight row(s) after restart", rows.len());
    let config = config_mgr.get();
    for record in rows {
        let folder = match config_mgr.get_folder(&record.folder_id) {
            Some(f) => f,
            None => continue,
        };
        let db = Arc::clone(db);
        let handle = app_handle.clone();
        let conn = connectivity.clone();
        let base = config.base_url.clone();
        let key = config.api_key.clone();
        tokio::spawn(async move {
            let _ =
                submitter::resume_polling(record, folder, base, key, conn, db, handle).await;
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::{status, JobRecord, ShareLinks};

    fn make_row(id: &str, group: Option<&str>) -> JobRecord {
        JobRecord {
            id: id.into(),
            folder_id: "f1".into(),
            file_name: format!("{}.pdf", id),
            file_path: format!("/w/{}.pdf", id),
            status: status::QUEUED_OFFLINE.into(),
            job_id: None,
            summary: None,
            routed_to: None,
            submitted_at: "2026-04-15T00:00:00Z".into(),
            completed_at: None,
            error_message: None,
            share_links: None::<ShareLinks>.map(|_| ShareLinks::default()),
            jdf_path: None,
            batch_group: group.map(String::from),
            batch_id: None,
            next_retry_at: None,
            retry_attempts: 0,
        }
    }

    #[test]
    fn partition_groups_by_batch_key() {
        let rows = vec![
            make_row("a", None),
            make_row("b", Some("f1-100")),
            make_row("c", Some("f1-100")),
            make_row("d", Some("f1-101")),
            make_row("e", None),
        ];
        let (singles, groups) = partition_by_group(rows);
        assert_eq!(singles.len(), 2);
        assert_eq!(groups.len(), 2);
        assert_eq!(groups.get("f1-100").unwrap().len(), 2);
        assert_eq!(groups.get("f1-101").unwrap().len(), 1);
    }

    #[test]
    fn partition_treats_empty_group_as_singleton() {
        let rows = vec![make_row("a", Some(""))];
        let (singles, groups) = partition_by_group(rows);
        assert_eq!(singles.len(), 1);
        assert!(groups.is_empty());
    }
}
