import { useEffect, useState } from "react";
import { Cloud, CloudOff, RefreshCw, AlertCircle } from "lucide-react";
import type { ConnectivityStatus } from "../lib/types";
import {
  forceConnectivityCheck,
  getConnectivityStatus,
  onConnectivityChange,
} from "../lib/tauri";

/**
 * Header pill showing online/offline state + queued count. Listens
 * for `connectivity-change` events from Rust and updates live. The
 * icon is clickable — it forces an immediate probe (wraps
 * `force_connectivity_check`).
 */
export function ConnectivityPill() {
  const [status, setStatus] = useState<ConnectivityStatus | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    // Initial fetch so we don't flash "offline" before the first event.
    getConnectivityStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        /* harmless — pill stays null */
      });

    onConnectivityChange((s) => {
      if (!cancelled) setStatus(s);
    }).then((fn) => {
      unlisten = fn;
    });

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  async function handleRetry() {
    setChecking(true);
    try {
      await forceConnectivityCheck();
      const s = await getConnectivityStatus();
      setStatus(s);
    } finally {
      // Small debounce so the spinner is visible to the user.
      setTimeout(() => setChecking(false), 400);
    }
  }

  if (!status) {
    return null;
  }

  const { online, auth_failure, queued_count } = status;

  // Auth-failure state wins over plain online/offline: the engine is
  // reachable but the API key is wrong — the user needs to fix that
  // before anything else will work.
  const state: "auth" | "online" | "offline" = auth_failure
    ? "auth"
    : online
      ? "online"
      : "offline";

  const color =
    state === "auth"
      ? "bg-amber-100 text-amber-800"
      : state === "online"
        ? "bg-green-100 text-green-700"
        : queued_count > 0
          ? "bg-amber-100 text-amber-700"
          : "bg-gray-100 text-gray-500";

  const Icon =
    state === "auth" ? AlertCircle : state === "online" ? Cloud : CloudOff;

  const label = (() => {
    if (state === "auth") {
      return queued_count > 0
        ? `Auth failing · ${queued_count} queued`
        : "Auth failing";
    }
    if (state === "online") {
      return queued_count > 0 ? `Online · ${queued_count} queued` : "Online";
    }
    return queued_count > 0 ? `Offline · ${queued_count} queued` : "Offline";
  })();

  const title = (() => {
    if (state === "auth") {
      return "Engine is reachable but recent submissions were rejected (401/403). Check your API key in Settings.";
    }
    if (state === "online") {
      return "Connected to LintPDF — click to re-check";
    }
    return "Offline — click to retry connection now";
  })();

  return (
    <button
      onClick={handleRetry}
      disabled={checking}
      className={`flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium transition-colors hover:opacity-80 disabled:opacity-50 ${color}`}
      title={title}
    >
      {checking ? (
        <RefreshCw className="h-3 w-3 animate-spin" />
      ) : (
        <Icon className="h-3 w-3" />
      )}
      {label}
    </button>
  );
}
