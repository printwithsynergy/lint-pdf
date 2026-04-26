use serde::{Deserialize, Serialize};

/// Token returned by the platform after registration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TokenResponse {
    /// FCM token (Android) or APNs hex token (iOS).
    pub token: String,
    /// Hint so the JS side can post to `/api/mobile/devices` with
    /// the right `platform` field.
    pub platform: Platform,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Platform {
    Ios,
    Android,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum PermissionStatus {
    /// User explicitly granted notifications.
    Granted,
    /// User declined or hasn't been asked yet (the OS doesn't
    /// distinguish on every platform — treat as "we shouldn't
    /// register without re-prompting").
    Denied,
    /// iOS-only state: user enabled "provisional" delivery (silent
    /// notifications). We treat this as granted for token-fetch
    /// purposes since the OS will still hand us a device token.
    Provisional,
}
