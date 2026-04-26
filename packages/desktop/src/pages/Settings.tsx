import { useState } from "react";
import {
  Save,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Loader,
  Zap,
  Building2,
} from "lucide-react";
import type { AppConfig, TestConnectionResult } from "../lib/types";
import { testConnection } from "../lib/tauri";

interface SettingsProps {
  config: AppConfig;
  onSave: (config: AppConfig) => Promise<void>;
  onChangeTenant: () => Promise<void>;
}

export function Settings({
  config: initial,
  onSave,
  onChangeTenant,
}: SettingsProps) {
  const [config, setConfig] = useState<AppConfig>({ ...initial });
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(
    null,
  );

  function update(partial: Partial<AppConfig>) {
    setConfig((prev) => ({ ...prev, ...partial }));
    setSaved(false);
    setTestResult(null);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(config);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection(config.base_url, config.api_key);
      setTestResult(result);
    } catch (e: unknown) {
      // Invoke-level failure (rare — would usually mean the Rust command
      // itself panicked). Surface as a synthetic failing result.
      setTestResult({
        health_ok: false,
        auth_ok: false,
        latency_ms: 0,
        error: String(e),
      });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Settings</h2>

      <div className="space-y-5">
        {/* Tenant */}
        <div className="card p-4 space-y-3">
          <h3 className="flex items-center gap-2 text-sm font-medium text-gray-900">
            <Building2 className="h-4 w-4 text-brand-600" />
            Tenant
          </h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">
                {config.tenant_name || "(unset)"}
              </p>
              {config.tenant_id && (
                <p className="font-mono text-xs text-gray-500">
                  {config.tenant_id}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => void onChangeTenant()}
              className="btn-secondary text-xs"
              title="Sign out and re-run Onboarding to switch tenants"
            >
              Change tenant
            </button>
          </div>
          <p className="text-xs text-gray-400">
            Change tenant clears your API key and tenant branding, then
            re-runs the Onboarding screen.
          </p>
        </div>

        {/* API Configuration */}
        <div className="card p-4 space-y-4">
          <h3 className="text-sm font-medium text-gray-900">
            API Configuration
          </h3>

          <div>
            <label className="label">API Key</label>
            <div className="flex gap-2">
              <input
                type={showKey ? "text" : "password"}
                className="input flex-1 font-mono text-xs"
                value={config.api_key}
                onChange={(e) => update({ api_key: e.target.value })}
                placeholder="Enter your LintPDF API key"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="btn-secondary px-3"
              >
                {showKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Get your API key from the LintPDF dashboard
            </p>
          </div>

          <div>
            <label className="label">API Base URL</label>
            <input
              type="url"
              className="input font-mono text-xs"
              value={config.base_url}
              onChange={(e) => update({ base_url: e.target.value })}
              placeholder="https://api.lintpdf.com"
            />
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={() => void handleTest()}
              disabled={testing || !config.base_url.trim()}
              className="btn-secondary text-xs"
            >
              {testing ? (
                <Loader className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Zap className="h-3.5 w-3.5" />
              )}
              {testing ? "Testing…" : "Test connection"}
            </button>
            {testResult && (
              <div className="flex-1 text-xs">
                {testResult.health_ok && testResult.auth_ok ? (
                  <span className="flex items-center gap-1.5 text-green-700">
                    <CheckCircle className="h-3.5 w-3.5" />
                    Connected ({testResult.latency_ms}ms)
                  </span>
                ) : testResult.health_ok && !testResult.auth_ok ? (
                  <span className="flex items-center gap-1.5 text-amber-700">
                    <XCircle className="h-3.5 w-3.5" />
                    {testResult.error ??
                      "Engine reachable but API key rejected."}
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-red-700">
                    <XCircle className="h-3.5 w-3.5" />
                    {testResult.error ?? "Engine unreachable."}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* App Behavior */}
        <div className="card p-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-900">Behavior</h3>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="notifications"
              checked={config.notifications_enabled}
              onChange={(e) =>
                update({ notifications_enabled: e.target.checked })
              }
              className="rounded border-gray-300"
            />
            <label htmlFor="notifications" className="text-sm text-gray-700">
              Enable desktop notifications
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="startMinimized"
              checked={config.start_minimized}
              onChange={(e) => update({ start_minimized: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="startMinimized" className="text-sm text-gray-700">
              Start minimized to system tray
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="launchAtLogin"
              checked={config.launch_at_login}
              onChange={(e) => update({ launch_at_login: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="launchAtLogin" className="text-sm text-gray-700">
              Launch at login
            </label>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div>
            {saved && (
              <span className="text-xs text-green-600">Settings saved</span>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary text-xs"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
