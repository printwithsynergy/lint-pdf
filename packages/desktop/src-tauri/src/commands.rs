use std::sync::Arc;
use tauri::State;

use crate::config::{AppConfig, ConfigManager, FolderConfig};
use crate::db::{Database, JobRecord};
use crate::watcher::WatcherManager;

pub struct AppState {
    pub config_mgr: Arc<ConfigManager>,
    pub watcher_mgr: Arc<WatcherManager>,
    pub db: Arc<Database>,
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
    state.config_mgr.save(config)
}

#[tauri::command]
pub fn add_folder(state: State<'_, AppState>, folder: FolderConfig) -> Result<(), String> {
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
