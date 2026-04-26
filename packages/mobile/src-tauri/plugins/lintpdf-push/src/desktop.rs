//! Desktop / web-preview no-op implementation.
//!
//! Push notifications need an OS-managed registration with FCM
//! (Android) or APNs (iOS) — neither is meaningful on macOS /
//! Windows / Linux desktop builds. Instead of crashing the dev
//! loop, both methods return a structured `Unsupported` error so
//! the JS side can branch (silently skip registration on desktop).

use std::marker::PhantomData;
use tauri::{plugin::PluginApi, AppHandle, Runtime};

use crate::{Error, PermissionStatus, Result, TokenResponse};

pub struct LintpdfPush<R: Runtime>(PhantomData<R>);

pub fn init<R: Runtime, C: serde::de::DeserializeOwned>(
    _app: &AppHandle<R>,
    _api: PluginApi<R, C>,
) -> Result<LintpdfPush<R>> {
    Ok(LintpdfPush(PhantomData))
}

impl<R: Runtime> LintpdfPush<R> {
    pub async fn register_for_push(&self) -> Result<TokenResponse> {
        Err(Error::Unsupported)
    }

    pub async fn request_permission(&self) -> Result<PermissionStatus> {
        Err(Error::Unsupported)
    }
}
