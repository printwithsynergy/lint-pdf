//! Tauri 2 mobile shell for the LintPDF companion app.
//!
//! Six commands fronting the JS bridge in `src/lib/tauri.ts`:
//!   * `get_platform`   — "ios" | "android" | "<desktop os>" so the
//!                         frontend can branch on capability.
//!   * `set_tenant`     — persist captured tenant id + branding via
//!                         `tauri-plugin-store`.
//!   * `get_tenant`     — read it back (returns null when unset).
//!   * `clear_tenant`   — wipe the captured tenant + API key together
//!                         (the Settings → "Change tenant" path).
//!   * `set_api_key`    — store the API key for authenticated calls.
//!   * `get_api_key`    — read it back (returns null when unset).
//!
//! Push-token registration (`register_for_push`) intentionally lives
//! in a follow-up slice — it requires platform-native FCM/APNs code
//! in `gen/apple/` and `gen/android/` that the developer scaffolds
//! once via `tauri ios init` / `tauri android init`. The current
//! shell is fully functional without it: viewer, approval, and
//! tenant onboarding all work; push notifications layer on top.
//!
//! Deep-link routing is wired through the JS-side
//! `tauri-plugin-deep-link` listener so a tap on
//! `https://app.lintpdf.com/view/{token}` (after universal-link
//! verification) lands in `App.tsx` via a `router.navigate()` call.

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{Manager, State};
use tauri_plugin_store::StoreExt;

const STORE_PATH: &str = "lintpdf-mobile.json";
const STORE_KEY_TENANT: &str = "tenant";
const STORE_KEY_API_KEY: &str = "api_key";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapturedTenant {
    pub tenant_id: String,
    pub name: String,
    pub slug: String,
    pub domain: Option<String>,
    /// Pixie Dust branding blob — kept as raw JSON because the shape
    /// evolves upstream and we want the desktop / mobile shells to
    /// round-trip new optional columns without breaking on every
    /// upstream release.
    pub branding: serde_json::Value,
    pub captured_at: String,
}

/// In-memory cache so callers don't pay a `store.get` round-trip on
/// every UI render. Initialised lazily on first command call.
#[derive(Default)]
pub struct AppState {
    pub tenant: Mutex<Option<CapturedTenant>>,
    pub api_key: Mutex<Option<String>>,
}

#[tauri::command]
fn get_platform() -> String {
    if cfg!(target_os = "ios") {
        "ios".to_string()
    } else if cfg!(target_os = "android") {
        "android".to_string()
    } else if cfg!(target_os = "macos") {
        "macos".to_string()
    } else if cfg!(target_os = "windows") {
        "windows".to_string()
    } else if cfg!(target_os = "linux") {
        "linux".to_string()
    } else {
        "unknown".to_string()
    }
}

#[tauri::command]
fn get_tenant(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<Option<CapturedTenant>, String> {
    {
        let cache = state.tenant.lock().map_err(|e| e.to_string())?;
        if let Some(t) = cache.clone() {
            return Ok(Some(t));
        }
    }
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("Failed to open tenant store: {}", e))?;
    let raw = store.get(STORE_KEY_TENANT);
    let tenant: Option<CapturedTenant> = match raw {
        Some(value) => serde_json::from_value(value)
            .map_err(|e| format!("Stored tenant is malformed: {}", e))?,
        None => None,
    };
    {
        let mut cache = state.tenant.lock().map_err(|e| e.to_string())?;
        *cache = tenant.clone();
    }
    Ok(tenant)
}

#[tauri::command]
fn set_tenant(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    tenant: CapturedTenant,
) -> Result<(), String> {
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("Failed to open tenant store: {}", e))?;
    let value = serde_json::to_value(&tenant)
        .map_err(|e| format!("Failed to serialize tenant: {}", e))?;
    store.set(STORE_KEY_TENANT, value);
    store
        .save()
        .map_err(|e| format!("Failed to persist tenant: {}", e))?;
    let mut cache = state.tenant.lock().map_err(|e| e.to_string())?;
    *cache = Some(tenant);
    Ok(())
}

#[tauri::command]
fn clear_tenant(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("Failed to open tenant store: {}", e))?;
    store.delete(STORE_KEY_TENANT);
    store.delete(STORE_KEY_API_KEY);
    store
        .save()
        .map_err(|e| format!("Failed to persist clear: {}", e))?;
    {
        let mut cache = state.tenant.lock().map_err(|e| e.to_string())?;
        *cache = None;
    }
    {
        let mut cache = state.api_key.lock().map_err(|e| e.to_string())?;
        *cache = None;
    }
    Ok(())
}

#[tauri::command]
fn get_api_key(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<Option<String>, String> {
    {
        let cache = state.api_key.lock().map_err(|e| e.to_string())?;
        if let Some(k) = cache.clone() {
            return Ok(Some(k));
        }
    }
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("Failed to open store: {}", e))?;
    let raw = store.get(STORE_KEY_API_KEY);
    let key: Option<String> = match raw {
        Some(value) => value.as_str().map(|s| s.to_string()),
        None => None,
    };
    {
        let mut cache = state.api_key.lock().map_err(|e| e.to_string())?;
        *cache = key.clone();
    }
    Ok(key)
}

#[tauri::command]
fn set_api_key(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    api_key: String,
) -> Result<(), String> {
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("Failed to open store: {}", e))?;
    if api_key.is_empty() {
        store.delete(STORE_KEY_API_KEY);
    } else {
        store.set(STORE_KEY_API_KEY, serde_json::Value::String(api_key.clone()));
    }
    store
        .save()
        .map_err(|e| format!("Failed to persist api key: {}", e))?;
    let mut cache = state.api_key.lock().map_err(|e| e.to_string())?;
    *cache = if api_key.is_empty() { None } else { Some(api_key) };
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_deep_link::init())
        .setup(|app| {
            app.manage(AppState::default());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_platform,
            get_tenant,
            set_tenant,
            clear_tenant,
            get_api_key,
            set_api_key,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
