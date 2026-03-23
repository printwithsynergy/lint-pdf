"use client";

import { useCallback, useEffect, useState } from "react";

interface ApiKey {
  id: string;
  label: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [creating, setCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchKeys = useCallback(async () => {
    try {
      const resp = await fetch("/api/grounded/keys");
      if (!resp.ok) throw new Error("Failed to load API keys");
      const data = await resp.json();
      setKeys(Array.isArray(data) ? data : data.keys ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  async function handleCreate() {
    setCreating(true);
    setError("");
    try {
      const resp = await fetch("/api/grounded/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: newLabel || "Default" }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to create key");
      }
      const data = await resp.json();
      setNewlyCreatedKey(data.api_key ?? data.key ?? null);
      setNewLabel("");
      await fetchKeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    if (!confirm("Revoke this API key? This action cannot be undone.")) return;
    try {
      await fetch(`/api/grounded/keys/${id}`, { method: "DELETE" });
      await fetchKeys();
    } catch {
      setError("Failed to revoke key");
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">API Keys</h1>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">API Keys</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage API keys for authenticating with the LintPDF engine.
          </p>
        </div>
        <button
          onClick={() => {
            setShowCreate(!showCreate);
            setNewlyCreatedKey(null);
          }}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreate ? "Cancel" : "Create Key"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Newly created key banner */}
      {newlyCreatedKey && (
        <div className="mt-4 rounded-md border border-green-200 bg-green-50 p-4">
          <p className="text-sm font-medium text-green-800">
            API key created! Copy it now — it will not be shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 rounded bg-white px-3 py-2 text-sm font-mono">
              {newlyCreatedKey}
            </code>
            <button
              onClick={() => copyToClipboard(newlyCreatedKey)}
              className="rounded-md border px-3 py-2 text-sm hover:bg-gray-50"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      {showCreate && !newlyCreatedKey && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">New API Key</h2>
          <div className="mt-3 flex gap-3">
            <input
              type="text"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="Key label (e.g. Production)"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
            />
            <button
              onClick={handleCreate}
              disabled={creating}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      {/* Key list */}
      <div className="mt-6 space-y-2">
        {keys.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
            No API keys. Create one to authenticate with the LintPDF API.
          </div>
        ) : (
          keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{key.label}</span>
                  <code className="text-xs text-muted-foreground">
                    {key.key_prefix}...
                  </code>
                </div>
                <div className="mt-0.5 flex gap-3 text-xs text-muted-foreground">
                  <span>
                    Created {new Date(key.created_at).toLocaleDateString()}
                  </span>
                  {key.last_used_at && (
                    <span>
                      Last used{" "}
                      {new Date(key.last_used_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleRevoke(key.id)}
                className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
              >
                Revoke
              </button>
            </div>
          ))
        )}
      </div>
    </main>
  );
}
