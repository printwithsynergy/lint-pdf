//! LintPDF push-notification plugin for Tauri 2 mobile.
//!
//! Wraps the platform-native FCM (Android) and APNs (iOS) registration
//! APIs so the JS side can request a device token via a single
//! `register_for_push()` invoke, and prompt the user for notification
//! permission via `request_permission()`.
//!
//! Desktop builds get a no-op implementation that returns an
//! `Unsupported` error — the LintPDF mobile bundle also runs on
//! desktop in `pnpm dev` for fast iteration, and crashing there
//! would break the dev loop.

pub use models::*;

#[cfg(desktop)]
mod desktop;
#[cfg(mobile)]
mod mobile;

mod commands;
mod error;
mod models;

pub use error::{Error, Result};

#[cfg(desktop)]
use desktop::LintpdfPush;
#[cfg(mobile)]
use mobile::LintpdfPush;

use tauri::{
    plugin::{Builder, TauriPlugin},
    Manager, Runtime,
};

/// Extension trait so callers can do
/// `app.lintpdf_push().register_for_push(...)`.
pub trait LintpdfPushExt<R: Runtime> {
    fn lintpdf_push(&self) -> &LintpdfPush<R>;
}

impl<R: Runtime, T: Manager<R>> LintpdfPushExt<R> for T {
    fn lintpdf_push(&self) -> &LintpdfPush<R> {
        self.state::<LintpdfPush<R>>().inner()
    }
}

pub fn init<R: Runtime>() -> TauriPlugin<R> {
    Builder::new("lintpdf-push")
        .invoke_handler(tauri::generate_handler![
            commands::register_for_push,
            commands::request_permission,
        ])
        .setup(|app, api| {
            #[cfg(mobile)]
            let plugin = mobile::init(app, api)?;
            #[cfg(desktop)]
            let plugin = desktop::init(app, api)?;
            app.manage(plugin);
            Ok(())
        })
        .build()
}
