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
    pub jdf_path: Option<PathBuf>,
}

struct PendingFile {
    size: u64,
    last_changed: Instant,
    folder_id: String,
    /// Captured at insert time from `FolderConfig::jdf_companion_timeout_secs`.
    /// Zero disables the wait.
    jdf_timeout: Duration,
}

/// A PDF that stabilized without a JDF companion and is waiting for one
/// to arrive.
struct AwaitingJdf {
    folder_id: String,
    awaiting_since: Instant,
    timeout: Duration,
}

struct FolderWatcher {
    _watcher: RecommendedWatcher,
}

pub struct WatcherManager {
    watchers: Mutex<HashMap<String, FolderWatcher>>,
    pending: Arc<Mutex<HashMap<PathBuf, PendingFile>>>,
    awaiting_jdf: Arc<Mutex<HashMap<PathBuf, AwaitingJdf>>>,
}

impl WatcherManager {
    pub fn new(ready_tx: mpsc::Sender<StabilizedFile>) -> Self {
        let pending: Arc<Mutex<HashMap<PathBuf, PendingFile>>> =
            Arc::new(Mutex::new(HashMap::new()));
        let awaiting_jdf: Arc<Mutex<HashMap<PathBuf, AwaitingJdf>>> =
            Arc::new(Mutex::new(HashMap::new()));

        // Stabilization checker thread. Runs two sweeps on every tick:
        //   1. Move stable entries out of `pending` — emit immediately if
        //      they already have a JDF companion, otherwise park in
        //      `awaiting_jdf`.
        //   2. Sweep `awaiting_jdf` — emit if the companion has since
        //      arrived, or if the per-folder timeout has expired.
        let pending_clone = Arc::clone(&pending);
        let awaiting_clone = Arc::clone(&awaiting_jdf);
        let tx_clone = ready_tx.clone();
        std::thread::spawn(move || {
            loop {
                std::thread::sleep(Duration::from_millis(500));
                let mut ready: Vec<StabilizedFile> = Vec::new();

                // --- Sweep 1: stabilization -----------------------------
                {
                    let mut map = pending_clone.lock().unwrap();
                    let mut awaiting = awaiting_clone.lock().unwrap();
                    let now = Instant::now();
                    map.retain(|path, pf| {
                        if now.duration_since(pf.last_changed) < Duration::from_secs(2) {
                            return true;
                        }

                        let ext = path
                            .extension()
                            .and_then(|e| e.to_str())
                            .map(|e| e.to_lowercase())
                            .unwrap_or_default();

                        if ext == "jdf" || ext == "xjdf" {
                            // JDF/XJDF files are never submitted alone. Sweep 2
                            // will spot them as they arrive and promote the
                            // waiting PDF.
                            return false;
                        }

                        if ext == "pdf" {
                            if let Some(jdf) = find_companion_jdf(path) {
                                ready.push(StabilizedFile {
                                    path: path.clone(),
                                    folder_id: pf.folder_id.clone(),
                                    jdf_path: Some(jdf),
                                });
                            } else if pf.jdf_timeout > Duration::ZERO {
                                // Park — maybe the JDF is still being copied.
                                awaiting.insert(
                                    path.clone(),
                                    AwaitingJdf {
                                        folder_id: pf.folder_id.clone(),
                                        awaiting_since: now,
                                        timeout: pf.jdf_timeout,
                                    },
                                );
                            } else {
                                ready.push(StabilizedFile {
                                    path: path.clone(),
                                    folder_id: pf.folder_id.clone(),
                                    jdf_path: None,
                                });
                            }
                        } else {
                            // Other supported formats: no companion logic.
                            ready.push(StabilizedFile {
                                path: path.clone(),
                                folder_id: pf.folder_id.clone(),
                                jdf_path: None,
                            });
                        }
                        false
                    });
                }

                // --- Sweep 2: JDF companion timeout ---------------------
                {
                    let mut awaiting = awaiting_clone.lock().unwrap();
                    let now = Instant::now();
                    awaiting.retain(|path, state| {
                        if !path.exists() {
                            // PDF was deleted / moved out — give up silently.
                            return false;
                        }
                        if let Some(jdf) = find_companion_jdf(path) {
                            log::info!(
                                "JDF companion arrived for {}",
                                path.display()
                            );
                            ready.push(StabilizedFile {
                                path: path.clone(),
                                folder_id: state.folder_id.clone(),
                                jdf_path: Some(jdf),
                            });
                            return false;
                        }
                        if now.duration_since(state.awaiting_since) >= state.timeout {
                            log::info!(
                                "JDF companion timeout expired for {} — submitting without companion",
                                path.display()
                            );
                            ready.push(StabilizedFile {
                                path: path.clone(),
                                folder_id: state.folder_id.clone(),
                                jdf_path: None,
                            });
                            return false;
                        }
                        true
                    });
                }

                for file in ready {
                    tx_clone.send(file).ok();
                }
            }
        });

        Self {
            watchers: Mutex::new(HashMap::new()),
            pending,
            awaiting_jdf,
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
        let jdf_timeout = Duration::from_secs_f64(folder.jdf_companion_timeout_secs.max(0.0));

        let folder_id_inner = folder_id.clone();
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
                                        PendingFile {
                                            size,
                                            last_changed: Instant::now(),
                                            folder_id: folder_id_inner.clone(),
                                            jdf_timeout,
                                        },
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

        // Scan for existing files — funnel them through the same pending/
        // awaiting-JDF pipeline so timeout / companion logic stays uniform.
        if let Ok(entries) = std::fs::read_dir(watch_dir) {
            let mut map = self.pending.lock().unwrap();
            for entry in entries.flatten() {
                let path = entry.path();
                if !is_supported_file(&path, &folder.file_extensions) {
                    continue;
                }
                let ext = path
                    .extension()
                    .and_then(|e| e.to_str())
                    .map(|e| e.to_lowercase())
                    .unwrap_or_default();

                if ext == "jdf" || ext == "xjdf" {
                    // Standalone JDF — the matching PDF will pick it up
                    // either immediately (if already present) or via the
                    // awaiting-JDF sweep.
                    continue;
                }

                let size = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
                map.insert(
                    path,
                    PendingFile {
                        size,
                        last_changed: Instant::now()
                            .checked_sub(Duration::from_secs(3))
                            .unwrap_or_else(Instant::now),
                        folder_id: folder.id.clone(),
                        jdf_timeout,
                    },
                );
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
                .retain(|_, pf| pf.folder_id != folder_id);
            self.awaiting_jdf
                .lock()
                .unwrap()
                .retain(|_, state| state.folder_id != folder_id);
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
        let pending = self
            .pending
            .lock()
            .unwrap()
            .values()
            .filter(|pf| pf.folder_id == folder_id)
            .count();
        let awaiting = self
            .awaiting_jdf
            .lock()
            .unwrap()
            .values()
            .filter(|s| s.folder_id == folder_id)
            .count();
        pending + awaiting
    }
}

/// Look for a companion `.jdf` or `.xjdf` file with the same stem in the same directory.
fn find_companion_jdf(path: &Path) -> Option<PathBuf> {
    let stem = path.file_stem()?;
    let parent = path.parent()?;
    let stem_str = stem.to_string_lossy();

    for ext in &["jdf", "xjdf"] {
        let candidate = parent.join(format!("{}.{}", stem_str, ext));
        if candidate.exists() {
            return Some(candidate);
        }
    }
    None
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
