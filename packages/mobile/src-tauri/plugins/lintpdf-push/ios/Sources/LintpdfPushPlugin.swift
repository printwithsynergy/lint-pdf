import Foundation
import Tauri
import UIKit
import UserNotifications
import WebKit

/// LintPDF push-notification iOS plugin.
///
/// Two responsibilities:
///   1. `requestPermission` — prompt the user (UNUserNotificationCenter) for
///       alert/badge/sound and resolve with `granted | denied | provisional`.
///   2. `registerForPush` — call `registerForRemoteNotifications()` on the main
///       UI thread and resolve with the APNs device token (hex string) once
///       `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`
///       fires on the AppDelegate.
///
/// Because iOS only delivers the device token via the AppDelegate callback,
/// we hold the pending Tauri `Invoke` here and resolve it from a Notification
/// observer the AppDelegate posts.
class LintpdfPushPlugin: Plugin {
  private var pendingTokenInvoke: Invoke?

  override init() {
    super.init()
    // Listen for the token-arrived notification posted by the AppDelegate
    // shim (`application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`)
    // — see `gen/apple/Sources/lintpdf_iOS/AppDelegate.swift` after `tauri ios init`.
    NotificationCenter.default.addObserver(
      self,
      selector: #selector(handleTokenArrived(_:)),
      name: Notification.Name("LintpdfPushTokenArrived"),
      object: nil
    )
    NotificationCenter.default.addObserver(
      self,
      selector: #selector(handleTokenFailed(_:)),
      name: Notification.Name("LintpdfPushTokenFailed"),
      object: nil
    )
  }

  @objc public func requestPermission(_ invoke: Invoke) {
    let center = UNUserNotificationCenter.current()
    center.requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
      if let error = error {
        invoke.reject(error.localizedDescription)
        return
      }
      // Provisional only when the caller asked for it explicitly,
      // which we don't — but read the actual settings so the
      // resolved status reflects reality.
      center.getNotificationSettings { settings in
        let status: String
        switch settings.authorizationStatus {
        case .authorized: status = "granted"
        case .provisional: status = "provisional"
        case .denied, .notDetermined, .ephemeral: status = "denied"
        @unknown default: status = "denied"
        }
        // Tauri serializes plain strings as JSON-encoded; the JS
        // side parses them as the matching `PermissionStatus` enum.
        invoke.resolve([
          "status": granted ? "granted" : status
        ])
      }
    }
  }

  @objc public func registerForPush(_ invoke: Invoke) {
    if pendingTokenInvoke != nil {
      invoke.reject("Push registration already in progress")
      return
    }
    pendingTokenInvoke = invoke
    DispatchQueue.main.async {
      UIApplication.shared.registerForRemoteNotifications()
    }
  }

  @objc private func handleTokenArrived(_ notification: Notification) {
    guard let invoke = pendingTokenInvoke else { return }
    pendingTokenInvoke = nil
    if let token = notification.userInfo?["token"] as? String {
      invoke.resolve([
        "token": token,
        "platform": "ios",
      ])
    } else {
      invoke.reject("APNs returned an empty token")
    }
  }

  @objc private func handleTokenFailed(_ notification: Notification) {
    guard let invoke = pendingTokenInvoke else { return }
    pendingTokenInvoke = nil
    let reason = notification.userInfo?["reason"] as? String ?? "Unknown APNs error"
    invoke.reject(reason)
  }
}

@_cdecl("init_plugin_lintpdf_push")
func initPlugin() -> Plugin {
  return LintpdfPushPlugin()
}
