package com.lintpdf.push

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Build
import android.webkit.WebView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import app.tauri.annotation.Command
import app.tauri.annotation.TauriPlugin
import app.tauri.plugin.Invoke
import app.tauri.plugin.JSObject
import app.tauri.plugin.Plugin
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging

/**
 * LintPDF push-notification Android plugin.
 *
 * Two responsibilities:
 *   1. `requestPermission` — for Android 13+ ask the user via the standard
 *       runtime permission flow; on older versions short-circuit to "granted"
 *       (notifications are auto-granted at install time).
 *   2. `registerForPush` — initialize FirebaseApp from `google-services.json`
 *       (developer drops this into `gen/android/app/`) then await the FCM
 *       token via `FirebaseMessaging.getInstance().getToken()`.
 */
@TauriPlugin
class LintpdfPushPlugin(private val activity: Activity) : Plugin(activity) {
    private val PERMISSION_REQUEST_CODE = 0xC0DE_PUSH

    private var pendingPermissionInvoke: Invoke? = null

    override fun load(webView: WebView) {
        super.load(webView)
        // Idempotent — Firebase initializes itself from google-services.json
        // when the FCM library hits its content provider, but calling this
        // explicitly makes the failure mode loud during dev (instead of a
        // silent missing-config-file).
        try {
            FirebaseApp.initializeApp(activity)
        } catch (e: Exception) {
            // FirebaseApp throws if google-services.json is missing —
            // that's the operator's job to drop in. Log and continue;
            // the first registerForPush() will fail with a clear error.
            android.util.Log.w("LintpdfPush", "Firebase init failed: ${e.message}")
        }
    }

    @Command
    fun requestPermission(invoke: Invoke) {
        // Android 13+ — POST_NOTIFICATIONS is a runtime permission.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                activity,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (granted) {
                invoke.resolve(JSObject().put("status", "granted"))
                return
            }
            pendingPermissionInvoke = invoke
            ActivityCompat.requestPermissions(
                activity,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                PERMISSION_REQUEST_CODE
            )
            return
        }
        // Pre-Android 13: notifications granted at install.
        invoke.resolve(JSObject().put("status", "granted"))
    }

    /**
     * Hook for the host activity to forward
     * `onRequestPermissionsResult` callbacks. The Tauri Android
     * scaffolding's MainActivity overrides
     * `onRequestPermissionsResult` and dispatches to every active
     * plugin; this method is the receive end.
     */
    fun handlePermissionResult(requestCode: Int, grantResults: IntArray) {
        if (requestCode != PERMISSION_REQUEST_CODE) return
        val invoke = pendingPermissionInvoke ?: return
        pendingPermissionInvoke = null
        val granted = grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        invoke.resolve(JSObject().put("status", if (granted) "granted" else "denied"))
    }

    @Command
    fun registerForPush(invoke: Invoke) {
        FirebaseMessaging.getInstance().token
            .addOnCompleteListener { task ->
                if (!task.isSuccessful) {
                    val msg = task.exception?.localizedMessage
                        ?: "FCM token retrieval failed"
                    invoke.reject(msg)
                    return@addOnCompleteListener
                }
                val token = task.result
                if (token.isNullOrEmpty()) {
                    invoke.reject("FCM returned an empty token")
                    return@addOnCompleteListener
                }
                val out = JSObject()
                out.put("token", token)
                out.put("platform", "android")
                invoke.resolve(out)
            }
    }
}
