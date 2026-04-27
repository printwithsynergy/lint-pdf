mod commands;
mod config;
mod connectivity;
mod db;
mod drainer;
mod router;
mod submitter;
mod tiles;
mod tray;
mod viewer;
mod watcher;

use commands::AppState;
use config::ConfigManager;
use db::Database;
use std::sync::Arc;
use tauri::Manager;
use watcher::WatcherManager;

pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            let config_mgr = Arc::new(ConfigManager::new());
            let db = Arc::new(
                Database::new().expect("Failed to initialize database"),
            );

            let (ready_tx, ready_rx) = std::sync::mpsc::channel();
            let watcher_mgr = Arc::new(WatcherManager::new(ready_tx));

            // Build a multi-threaded tokio runtime that outlives the
            // setup closure. We leak its Handle via a static OnceLock
            // pattern through the tasks we spawn — simpler than
            // threading a runtime handle through every module.
            let rt = tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .worker_threads(2)
                .build()
                .expect("Failed to create tokio runtime");
            let rt_handle = rt.handle().clone();
            // Keep the runtime alive for the lifetime of the process.
            std::mem::forget(rt);

            // Connectivity monitor: probes /health every 15s, emits
            // `connectivity-change` events, fires the "Back online"
            // notification when there are queued rows.
            let connectivity = connectivity::start(
                &rt_handle,
                Arc::clone(&config_mgr),
                Arc::clone(&db),
                app.handle().clone(),
            );

            // Drainer: supervises the outbox. Returns the `wake`
            // handle the intake thread signals after every stabilized
            // file.
            let drainer_wake = drainer::start(
                &rt_handle,
                Arc::clone(&config_mgr),
                Arc::clone(&db),
                connectivity.clone(),
                app.handle().clone(),
            );

            // Intake thread: pulls `StabilizedFile`s from the watcher
            // channel and writes outbox rows, then pokes the drainer.
            submitter::start_intake(
                ready_rx,
                Arc::clone(&config_mgr),
                Arc::clone(&db),
                app.handle().clone(),
                Arc::clone(&drainer_wake),
            );

            // Request OS-level notification permission once on startup.
            // Fire-and-forget on a tokio task: if the user denies (or
            // was prompted previously), the "Back online" toast just
            // silently drops. Better than blocking setup on a user
            // dialog.
            {
                use tauri::plugin::PermissionState;
                use tauri_plugin_notification::NotificationExt;
                let handle = app.handle().clone();
                rt_handle.spawn(async move {
                    if let Ok(state) = handle.notification().permission_state() {
                        if matches!(
                            state,
                            PermissionState::Prompt
                                | PermissionState::PromptWithRationale
                        ) {
                            let _ = handle.notification().request_permission();
                        }
                    }
                });
            }

            // Setup system tray
            tray::setup_tray(app.handle())
                .map_err(|e| format!("Tray setup failed: {}", e))?;

            // Handle close-to-tray: hide window instead of quitting
            let window = app.get_webview_window("main").unwrap();
            let window_clone = window.clone();
            window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    window_clone.hide().ok();
                }
            });

            app.manage(AppState {
                config_mgr,
                watcher_mgr,
                db,
                connectivity,
                drainer_wake,
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_config,
            commands::save_config,
            commands::add_folder,
            commands::remove_folder,
            commands::update_folder,
            commands::start_watching,
            commands::stop_watching,
            commands::start_all,
            commands::stop_all,
            commands::get_watcher_statuses,
            commands::get_recent_jobs,
            commands::clear_history,
            commands::list_brand_profiles,
            commands::mint_share_link,
            commands::list_endpoints,
            commands::list_approval_templates,
            commands::get_ai_interpretation,
            commands::get_connectivity_status,
            commands::force_connectivity_check,
            commands::open_viewer_window,
            commands::test_connection,
            commands::retry_job,
            commands::explain_finding,
            commands::get_epm_verdict,
            commands::list_decisions,
            commands::record_decision,
            commands::revoke_decision,
            commands::get_cost_cap,
            commands::set_cost_cap,
            viewer::viewer_pages,
            viewer::viewer_separations,
            viewer::viewer_layers,
            viewer::viewer_annotations,
            viewer::viewer_config,
            viewer::viewer_verdict,
            viewer::viewer_findings,
            viewer::viewer_tac_runs,
            viewer::viewer_densitometer,
            viewer::viewer_tile,
            viewer::viewer_channel_tile,
            viewer::viewer_tac_heatmap,
            viewer::viewer_clear_tile_cache,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
