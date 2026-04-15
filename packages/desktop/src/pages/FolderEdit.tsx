import { useEffect, useState } from "react";
import { ArrowLeft, Save, Trash2 } from "lucide-react";
import type { BrandMode, BrandProfileSummary, FolderConfig } from "../lib/types";
import { DEFAULT_EXTENSIONS } from "../lib/types";
import { DirectoryPicker } from "../components/DirectoryPicker";
import { listBrandProfiles } from "../lib/tauri";

interface FolderEditProps {
  folder: FolderConfig;
  isNew: boolean;
  onSave: (folder: FolderConfig) => Promise<void>;
  onCancel: () => void;
  onDelete: (id: string) => Promise<void>;
}

export function FolderEdit({
  folder: initial,
  isNew,
  onSave,
  onCancel,
  onDelete,
}: FolderEditProps) {
  const [folder, setFolder] = useState<FolderConfig>({ ...initial });
  const [saving, setSaving] = useState(false);
  const [brandProfiles, setBrandProfiles] = useState<BrandProfileSummary[]>([]);
  const [brandProfilesError, setBrandProfilesError] = useState<string | null>(
    null,
  );

  function update(partial: Partial<FolderConfig>) {
    setFolder((prev) => ({ ...prev, ...partial }));
  }

  // Lazily fetch BrandProfiles the first time the user picks "profile" mode.
  useEffect(() => {
    if (folder.brand_mode !== "profile" || brandProfiles.length > 0) return;
    let cancelled = false;
    listBrandProfiles()
      .then((profiles) => {
        if (!cancelled) setBrandProfiles(profiles);
      })
      .catch((e: unknown) => {
        if (!cancelled) setBrandProfilesError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [folder.brand_mode, brandProfiles.length]);

  function toggleExtension(ext: string) {
    setFolder((prev) => {
      const exts = prev.file_extensions.includes(ext)
        ? prev.file_extensions.filter((e) => e !== ext)
        : [...prev.file_extensions, ext];
      return { ...prev, file_extensions: exts };
    });
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(folder);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (confirm(`Delete "${folder.name || "this folder"}"?`)) {
      await onDelete(folder.id);
    }
  }

  const canSave = folder.name.trim() && folder.watch_dir.trim();

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={onCancel}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {isNew ? "Add Hot Folder" : "Edit Hot Folder"}
          </h2>
        </div>
      </div>

      <div className="space-y-5">
        {/* Basic info */}
        <div className="card p-4 space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Basic</h3>

          <div>
            <label className="label">Name</label>
            <input
              type="text"
              className="input"
              value={folder.name}
              onChange={(e) => update({ name: e.target.value })}
              placeholder="e.g., Offset Print Jobs"
            />
          </div>

          <DirectoryPicker
            label="Watch Directory"
            value={folder.watch_dir}
            onChange={(watch_dir) => update({ watch_dir })}
            placeholder="/path/to/watch"
          />

          <div>
            <label className="label">Preflight Profile</label>
            <input
              type="text"
              className="input"
              value={folder.profile_id}
              onChange={(e) => update({ profile_id: e.target.value })}
              placeholder="lintpdf-default"
            />
            <p className="text-xs text-gray-400 mt-1">
              The Ruleset profile ID to use for preflight checks
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={folder.enabled}
              onChange={(e) => update({ enabled: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="enabled" className="text-sm text-gray-700">
              Enabled
            </label>
          </div>
        </div>

        {/* Output directories */}
        <div className="card p-4 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-900">
              Output Directories
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Files are moved to these directories after preflight. Leave empty
              to keep files in place.
            </p>
          </div>

          <DirectoryPicker
            label="Pass Directory"
            value={folder.pass_dir}
            onChange={(pass_dir) => update({ pass_dir })}
            placeholder="e.g., /watch/_passed"
            optional
          />

          <DirectoryPicker
            label="Fail Directory"
            value={folder.fail_dir}
            onChange={(fail_dir) => update({ fail_dir })}
            placeholder="e.g., /watch/_failed"
            optional
          />

          <DirectoryPicker
            label="Error Directory"
            value={folder.error_dir}
            onChange={(error_dir) => update({ error_dir })}
            placeholder="e.g., /watch/_errors"
            optional
          />

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="sidecar"
              checked={folder.write_sidecar}
              onChange={(e) => update({ write_sidecar: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="sidecar" className="text-sm text-gray-700">
              Write JSON sidecar reports (.lintpdf.json)
            </label>
          </div>
        </div>

        {/* Branding */}
        <div className="card p-4 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-900">Branding</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Applied to every report and viewer link emitted by this folder.
              Overrides your tenant default.
            </p>
          </div>

          <div>
            <label className="label">Brand</label>
            <select
              className="input"
              value={folder.brand_mode}
              onChange={(e) =>
                update({ brand_mode: e.target.value as BrandMode })
              }
            >
              <option value="default">Use tenant default</option>
              <option value="anonymous">Anonymous (strip branding)</option>
              <option value="lintpdf">LintPDF default</option>
              <option value="profile">BrandProfile…</option>
            </select>
          </div>

          {folder.brand_mode === "profile" && (
            <div>
              <label className="label">Brand Profile</label>
              {brandProfiles.length > 0 ? (
                <select
                  className="input"
                  value={folder.brand_profile_id ?? ""}
                  onChange={(e) =>
                    update({ brand_profile_id: e.target.value || null })
                  }
                >
                  <option value="">Select a profile…</option>
                  {brandProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                      {p.is_default ? " (default)" : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="input font-mono text-xs"
                  value={folder.brand_profile_id ?? ""}
                  onChange={(e) =>
                    update({ brand_profile_id: e.target.value || null })
                  }
                  placeholder="Brand profile UUID"
                />
              )}
              {brandProfilesError && (
                <p className="text-xs text-amber-600 mt-1">
                  Could not load profiles ({brandProfilesError}). Paste the
                  UUID from the dashboard.
                </p>
              )}
            </div>
          )}
        </div>

        {/* File types */}
        <div className="card p-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-900">File Types</h3>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_EXTENSIONS.map((ext) => {
              const active = folder.file_extensions.includes(ext);
              return (
                <button
                  key={ext}
                  onClick={() => toggleExtension(ext)}
                  className={`rounded-full px-3 py-1 text-xs font-mono transition-colors ${
                    active
                      ? "bg-brand-100 text-brand-700 ring-1 ring-brand-300"
                      : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                  }`}
                >
                  {ext}
                </button>
              );
            })}
          </div>
        </div>

        {/* Advanced */}
        <div className="card p-4 space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Advanced</h3>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Stabilization (seconds)</label>
              <input
                type="number"
                className="input"
                value={folder.stabilization_secs}
                onChange={(e) =>
                  update({
                    stabilization_secs: parseFloat(e.target.value) || 2,
                  })
                }
                min={0.5}
                step={0.5}
              />
              <p className="text-xs text-gray-400 mt-1">
                Wait for file size to stabilize before processing
              </p>
            </div>
            <div>
              <label className="label">Poll Interval (seconds)</label>
              <input
                type="number"
                className="input"
                value={folder.poll_interval_secs}
                onChange={(e) =>
                  update({
                    poll_interval_secs: parseFloat(e.target.value) || 5,
                  })
                }
                min={1}
                step={1}
              />
              <p className="text-xs text-gray-400 mt-1">
                How often to check job status
              </p>
            </div>
            <div>
              <label className="label">JDF Companion Timeout (seconds)</label>
              <input
                type="number"
                className="input"
                value={folder.jdf_companion_timeout_secs}
                onChange={(e) =>
                  update({
                    jdf_companion_timeout_secs:
                      parseFloat(e.target.value) || 0,
                  })
                }
                min={0}
                step={5}
              />
              <p className="text-xs text-gray-400 mt-1">
                How long to wait for a matching .jdf / .xjdf file after a PDF
                stabilizes. Set to 0 to submit PDFs immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <div>
            {!isNew && (
              <button onClick={handleDelete} className="btn-danger text-xs">
                <Trash2 className="h-3.5 w-3.5" /> Delete Folder
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onCancel} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!canSave || saving}
              className="btn-primary text-xs"
            >
              <Save className="h-3.5 w-3.5" />
              {saving ? "Saving..." : isNew ? "Add Folder" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
