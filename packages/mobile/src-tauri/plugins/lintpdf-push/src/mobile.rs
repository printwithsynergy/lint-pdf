//! Mobile (iOS + Android) FFI to the platform-native plugin code.
//!
//! On iOS, `register_for_push` calls into `LintpdfPushPlugin.swift`,
//! which:
//!   1. Asks `UNUserNotificationCenter` for alert/badge/sound
//!      permission (or returns the cached state on subsequent calls).
//!   2. Calls `UIApplication.shared.registerForRemoteNotifications()`.
//!   3. Resolves with the APNs device token once the AppDelegate's
//!      `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`
//!      fires.
//!
//! On Android, it calls into `LintpdfPushPlugin.kt`, which:
//!   1. Initializes `FirebaseApp` from `google-services.json` at the
//!      app level (developer must drop the file into
//!      `gen/android/app/`).
//!   2. Awaits `FirebaseMessaging.getInstance().getToken()`.
//!   3. Resolves with the FCM token string.

use serde::de::DeserializeOwned;
use tauri::{
    plugin::{PluginApi, PluginHandle},
    AppHandle, Runtime,
};

use crate::{PermissionStatus, Result, TokenResponse};

#[cfg(target_os = "ios")]
tauri::ios_plugin_binding!(init_plugin_lintpdf_push);

pub fn init<R: Runtime, C: DeserializeOwned>(
    _app: &AppHandle<R>,
    api: PluginApi<R, C>,
) -> Result<LintpdfPush<R>> {
    #[cfg(target_os = "android")]
    let handle = api.register_android_plugin("com.lintpdf.push", "LintpdfPushPlugin")?;
    #[cfg(target_os = "ios")]
    let handle = api.register_ios_plugin(init_plugin_lintpdf_push)?;
    Ok(LintpdfPush(handle))
}

pub struct LintpdfPush<R: Runtime>(PluginHandle<R>);

impl<R: Runtime> LintpdfPush<R> {
    pub async fn register_for_push(&self) -> Result<TokenResponse> {
        Ok(self
            .0
            .run_mobile_plugin("registerForPush", ())
            .map_err(crate::Error::PluginInvoke)?)
    }

    pub async fn request_permission(&self) -> Result<PermissionStatus> {
        Ok(self
            .0
            .run_mobile_plugin("requestPermission", ())
            .map_err(crate::Error::PluginInvoke)?)
    }
}
