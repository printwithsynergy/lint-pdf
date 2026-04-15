mod commands;
mod config;
mod db;
mod router;
mod submitter;
mod tray;
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

            // Start submitter thread
            submitter::start_submitter(
                ready_rx,
                Arc::clone(&config_mgr),
                Arc::clone(&db),
                app.handle().clone(),
            );

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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
