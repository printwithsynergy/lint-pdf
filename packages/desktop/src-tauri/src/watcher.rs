use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use crate::config::FolderConfig;

pub struct StabilizedFile {
    pub path: PathBuf,
    pub folder_id: String,
}

struct PendingFile {
    size: u64,
    last_changed: Instant,
}

struct FolderWatcher {
    _watcher: RecommendedWatcher,
}

pub struct WatcherManager {
    watchers: Mutex<HashMap<String, FolderWatcher>>,
    ready_tx: mpsc::Sender<StabilizedFile>,
    pending: Arc<Mutex<HashMap<PathBuf, (PendingFile, String)>>>,
}

impl WatcherManager {
    pub fn new(ready_tx: mpsc::Sender<StabilizedFile>) -> Self {
        let pending: Arc<Mutex<HashMap<PathBuf, (PendingFile, String)>>> =
            Arc::new(Mutex::new(HashMap::new()));

        // Stabilization checker thread
        let pending_clone = Arc::clone(&pending);
        let tx_clone = ready_tx.clone();
        std::thread::spawn(move || {
            loop {
                std::thread::sleep(Duration::from_millis(500));
                let mut ready = Vec::new();
                {
                    let mut map = pending_clone.lock().unwrap();
                    let now = Instant::now();
                    map.retain(|path, (pf, folder_id)| {
                        if now.duration_since(pf.last_changed) >= Duration::from_secs(2) {
                            ready.push(StabilizedFile {
                                path: path.clone(),
                                folder_id: folder_id.clone(),
                            });
                            false
                        } else {
                            true
                        }
                    });
                }
                for file in ready {
                    tx_clone.send(file).ok();
                }
            }
        });

        Self {
            watchers: Mutex::new(HashMap::new()),
            ready_tx,
            pending,
        }
    }

    pub fn start(&self, folder: &FolderConfig) -> Result<(), String> {
        let watch_dir = Path::new(&folder.watch_dir);
        if !watch_dir.exists() {
            return Err(format!("Directory does not exist: {}", folder.watch_dir));
        }

        // Stop existing watcher for this folder
        self.stop(&folder.id);

        let extensions = folder.file_extensions.clone();
        let folder_id = folder.id.clone();
        let pending = Arc::clone(&self.pending);

        let mut watcher = RecommendedWatcher::new(
            move |result: Result<Event, notify::Error>| {
                if let Ok(event) = result {
                    match event.kind {
                        EventKind::Create(_) | EventKind::Modify(_) => {
                            for path in &event.paths {
                                if is_supported_file(path, &extensions) {
                                    let size = std::fs::metadata(path)
                                        .map(|m| m.len())
                                        .unwrap_or(0);
                                    let mut map = pending.lock().unwrap();
                                    map.insert(
                                        path.clone(),
                                        (
                                            PendingFile {
                                                size,
                                                last_changed: Instant::now(),
                                            },
                                            folder_id.clone(),
                                        ),
                                    );
                                }
                            }
                        }
                        _ => {}
                    }
                }
            },
            Config::default(),
        )
        .map_err(|e| format!("Failed to create watcher: {}", e))?;

        watcher
            .watch(watch_dir, RecursiveMode::NonRecursive)
            .map_err(|e| format!("Failed to watch directory: {}", e))?;

        // Scan for existing files
        if let Ok(entries) = std::fs::read_dir(watch_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if is_supported_file(&path, &folder.file_extensions) {
                    self.ready_tx
                        .send(StabilizedFile {
                            path,
                            folder_id: folder.id.clone(),
                        })
                        .ok();
                }
            }
        }

        let fw = FolderWatcher { _watcher: watcher };

        self.watchers.lock().unwrap().insert(folder.id.clone(), fw);
        log::info!("Started watching: {} ({})", folder.watch_dir, folder.name);
        Ok(())
    }

    pub fn stop(&self, folder_id: &str) {
        if self.watchers.lock().unwrap().remove(folder_id).is_some() {
            // Remove pending files for this folder
            self.pending
                .lock()
                .unwrap()
                .retain(|_, (_, fid)| fid != folder_id);
            log::info!("Stopped watching folder: {}", folder_id);
        }
    }

    pub fn is_active(&self, folder_id: &str) -> bool {
        self.watchers.lock().unwrap().contains_key(folder_id)
    }

    pub fn active_ids(&self) -> Vec<String> {
        self.watchers.lock().unwrap().keys().cloned().collect()
    }

    pub fn queued_count(&self, folder_id: &str) -> usize {
        self.pending
            .lock()
            .unwrap()
            .values()
            .filter(|(_, fid)| fid == folder_id)
            .count()
    }
}

fn is_supported_file(path: &Path, extensions: &[String]) -> bool {
    if !path.is_file() {
        return false;
    }
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| format!(".{}", e.to_lowercase()));
    match ext {
        Some(e) => extensions.iter().any(|supported| supported == &e),
        None => false,
    }
}
