import { useState } from "react";
import { Save, Eye, EyeOff } from "lucide-react";
import type { AppConfig } from "../lib/types";

interface SettingsProps {
  config: AppConfig;
  onSave: (config: AppConfig) => Promise<void>;
}

export function Settings({ config: initial, onSave }: SettingsProps) {
  const [config, setConfig] = useState<AppConfig>({ ...initial });
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function update(partial: Partial<AppConfig>) {
    setConfig((prev) => ({ ...prev, ...partial }));
    setSaved(false);
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

  return (
    <div className="max-w-xl">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Settings</h2>

      <div className="space-y-5">
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
