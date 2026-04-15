//! Connectivity monitor.
//!
//! Periodically probes the engine's unauthenticated `GET /health`
//! endpoint and tracks online/offline state. Fires a desktop
//! notification on offline→online transitions when there are queued
//! rows waiting to drain, and wakes the [`drainer`](crate::drainer)
//! so the outbox flushes without user intervention.
//!
//! Reasons this uses a simple periodic probe rather than OS network
//! APIs:
//!   * Cross-platform (macOS, Windows, Linux) via one path.
//!   * Works when the network is "up" but the engine is down or
//!     blocked by a captive portal — exactly the case the user needs
//!     to recover from.
//!   * No extra capability permissions required beyond the HTTP
//!     access we already use.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};
use tauri_plugin_notification::NotificationExt;
use tokio::sync::Notify;

use crate::config::ConfigManager;
use crate::db::Database;

const PROBE_INTERVAL: Duration = Duration::from_secs(15);
const PROBE_TIMEOUT: Duration = Duration::from_secs(5);

/// Shared state for the connectivity monitor. Cloned into each task
/// that needs to read or wait on connectivity changes (drainer,
/// Tauri commands).
#[derive(Clone)]
pub struct ConnectivityState {
    online: Arc<AtomicBool>,
    last_success_at: Arc<std::sync::Mutex<Option<chrono::DateTime<chrono::Utc>>>>,
    last_checked_at: Arc<std::sync::Mutex<Option<chrono::DateTime<chrono::Utc>>>>,
    /// Signaled on every connectivity transition AND manual probe,
    /// so the drainer can react immediately.
    pub changed: Arc<Notify>,
    /// Signaled when the user clicks "Retry now" in the UI.
    force_probe: Arc<Notify>,
}

impl ConnectivityState {
    pub fn new() -> Self {
        Self {
            // Assume online at boot so that the first successful
            // submission doesn't require waiting for a 15s probe.
            online: Arc::new(AtomicBool::new(true)),
            last_success_at: Arc::new(std::sync::Mutex::new(None)),
            last_checked_at: Arc::new(std::sync::Mutex::new(None)),
            changed: Arc::new(Notify::new()),
            force_probe: Arc::new(Notify::new()),
        }
    }

    pub fn is_online(&self) -> bool {
        self.online.load(Ordering::Acquire)
    }

    pub fn snapshot(&self) -> ConnectivitySnapshot {
        ConnectivitySnapshot {
            online: self.is_online(),
            last_success_at: self
                .last_success_at
                .lock()
                .unwrap()
                .map(|d| d.to_rfc3339()),
            last_checked_at: self
                .last_checked_at
                .lock()
                .unwrap()
                .map(|d| d.to_rfc3339()),
        }
    }

    /// Wake the probe loop — used by the "Retry now" button.
    pub fn force_check(&self) {
        self.force_probe.notify_one();
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct ConnectivitySnapshot {
    pub online: bool,
    pub last_success_at: Option<String>,
    pub last_checked_at: Option<String>,
}

/// Spawn the probe loop on the caller's tokio runtime. Returns a
/// handle the caller stores in `AppState`.
pub fn start(
    runtime: &tokio::runtime::Handle,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    app_handle: AppHandle,
) -> ConnectivityState {
    let state = ConnectivityState::new();
    let loop_state = state.clone();
    runtime.spawn(async move {
        probe_loop(loop_state, config_mgr, db, app_handle).await;
    });
    state
}

async fn probe_loop(
    state: ConnectivityState,
    config_mgr: Arc<ConfigManager>,
    db: Arc<Database>,
    app_handle: AppHandle,
) {
    let client = reqwest::Client::builder()
        .timeout(PROBE_TIMEOUT)
        .build()
        .expect("Failed to build reqwest client");

    // `last_offline_toast` suppresses repeated "still offline" toasts
    // — we only fire that once per offline session.
    let mut last_offline_toast: Option<Instant> = None;
    let mut offline_since: Option<Instant> = None;

    loop {
        let base_url = config_mgr.get().base_url;
        let probe_ok = run_probe(&client, &base_url).await;
        let now = chrono::Utc::now();
        *state.last_checked_at.lock().unwrap() = Some(now);

        let was_online = state.is_online();
        state.online.store(probe_ok, Ordering::Release);

        if probe_ok {
            *state.last_success_at.lock().unwrap() = Some(now);
        }

        match (was_online, probe_ok) {
            (true, false) => {
                offline_since = Some(Instant::now());
                last_offline_toast = None;
                log::info!("Connectivity lost (probe failed against {})", base_url);
                emit_change(&app_handle, &state, &db);
            }
            (false, true) => {
                offline_since = None;
                last_offline_toast = None;
                let queued = db.count_queued().unwrap_or(0);
                log::info!(
                    "Connectivity restored — {} queued row(s) ready to drain",
                    queued
                );
                emit_change(&app_handle, &state, &db);
                if queued > 0 && notifications_enabled(&config_mgr) {
                    let body = if queued == 1 {
                        "Back online — 1 file ready to submit.".to_string()
                    } else {
                        format!("Back online — {} files ready to submit.", queued)
                    };
                    let _ = app_handle
                        .notification()
                        .builder()
                        .title("LintPDF Hot Folders")
                        .body(body)
                        .show();
                }
                state.changed.notify_waiters();
            }
            (false, false) => {
                // Still offline. Fire one toast at the 10-minute mark
                // if there's backlog, then suppress until we recover.
                if let Some(since) = offline_since {
                    if since.elapsed() >= Duration::from_secs(600)
                        && last_offline_toast.is_none()
                    {
                        let queued = db.count_queued().unwrap_or(0);
                        if queued > 0 && notifications_enabled(&config_mgr) {
                            let body = format!(
                                "Still offline — {} file(s) waiting. Will resume automatically.",
                                queued
                            );
                            let _ = app_handle
                                .notification()
                                .builder()
                                .title("LintPDF Hot Folders")
                                .body(body)
                                .show();
                            last_offline_toast = Some(Instant::now());
                        }
                    }
                }
            }
            (true, true) => {
                // Steady-state online, nothing to announce.
            }
        }

        // Wait either for the next scheduled probe, or a forced one.
        tokio::select! {
            _ = tokio::time::sleep(PROBE_INTERVAL) => {},
            _ = state.force_probe.notified() => {},
        }
    }
}

async fn run_probe(client: &reqwest::Client, base_url: &str) -> bool {
    let url = format!("{}/health", base_url.trim_end_matches('/'));
    match client.get(&url).send().await {
        Ok(resp) => resp.status().is_success(),
        Err(_) => false,
    }
}

fn emit_change(app: &AppHandle, state: &ConnectivityState, db: &Database) {
    let mut snap = serde_json::to_value(state.snapshot()).unwrap_or_default();
    if let Some(obj) = snap.as_object_mut() {
        obj.insert(
            "queued_count".to_string(),
            serde_json::json!(db.count_queued().unwrap_or(0)),
        );
    }
    app.emit("connectivity-change", snap).ok();
}

fn notifications_enabled(config_mgr: &ConfigManager) -> bool {
    config_mgr.get().notifications_enabled
}
