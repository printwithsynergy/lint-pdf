use tauri::{command, AppHandle, Runtime};

use crate::{LintpdfPushExt, PermissionStatus, Result, TokenResponse};

#[command]
pub(crate) async fn register_for_push<R: Runtime>(
    app: AppHandle<R>,
) -> Result<TokenResponse> {
    app.lintpdf_push().register_for_push().await
}

#[command]
pub(crate) async fn request_permission<R: Runtime>(
    app: AppHandle<R>,
) -> Result<PermissionStatus> {
    app.lintpdf_push().request_permission().await
}
