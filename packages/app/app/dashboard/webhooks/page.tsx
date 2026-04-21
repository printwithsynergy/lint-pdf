"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { EmptyState } from "@thinkneverland/pixie-dust-ui";
import { useToast } from "@thinkneverland/pixie-dust-ui";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Button, Input, FormField } from "@thinkneverland/pixie-dust-ui";

interface WebhookEndpoint {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

const AVAILABLE_EVENTS = ["job.completed", "job.failed"];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newEvents, setNewEvents] = useState<string[]>([
    "job.completed",
    "job.failed",
  ]);
  const [creating, setCreating] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUrl, setEditUrl] = useState("");
  const [editEvents, setEditEvents] = useState<string[]>([]);

  // Test state
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
    status_code: number;
    error: string;
  } | null>(null);

  // Confirm dialog state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const { toast } = useToast();

  const fetchWebhooks = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/webhook-endpoints");
      if (!resp.ok) throw new Error("Failed to load webhooks");
      const data = await resp.json();
      setWebhooks(data.webhooks ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load webhooks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWebhooks();
  }, [fetchWebhooks]);

  async function handleCreate() {
    setCreating(true);
    try {
      const resp = await fetch("/api/lintpdf/webhook-endpoints", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: newUrl, events: newEvents }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to create webhook");
      }
      setNewUrl("");
      setNewEvents(["job.completed", "job.failed"]);
      setShowCreate(false);
      toast("Webhook created successfully", "success");
      await fetchWebhooks();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to create webhook", "error");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(id: string) {
    try {
      const resp = await fetch(`/api/lintpdf/webhook-endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: editUrl, events: editEvents }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to update webhook");
      }
      setEditingId(null);
      toast("Webhook updated", "success");
      await fetchWebhooks();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to update webhook", "error");
    }
  }

  async function handleToggle(id: string, is_active: boolean) {
    try {
      await fetch(`/api/lintpdf/webhook-endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !is_active }),
      });
      await fetchWebhooks();
    } catch {
      toast("Failed to toggle webhook", "error");
    }
  }

  async function handleDelete(id: string) {
    try {
      await fetch(`/api/lintpdf/webhook-endpoints/${id}`, {
        method: "DELETE",
      });
      toast("Webhook deleted", "success");
      await fetchWebhooks();
    } catch {
      toast("Failed to delete webhook", "error");
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    setTestResult(null);
    try {
      const resp = await fetch(`/api/lintpdf/webhook-endpoints/${id}/test`, {
        method: "POST",
      });
      const data = await resp.json();
      setTestResult({ id, ...data });
    } catch {
      setTestResult({
        id,
        success: false,
        status_code: 0,
        error: "Network error",
      });
    } finally {
      setTestingId(null);
    }
  }

  function toggleEvent(
    events: string[],
    setter: (e: string[]) => void,
    event: string,
  ) {
    setter(
      events.includes(event)
        ? events.filter((e) => e !== event)
        : [...events, event],
    );
  }

  if (loading) {
    return <SkeletonDashboard type="table" />;
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Webhooks</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Receive real-time notifications when preflight jobs complete or
            fail.
          </p>
        </div>
        <Button
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? "Cancel" : "Add Webhook"}
        </Button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">New Webhook</h2>
          <div className="mt-3 space-y-3">
            <FormField label="Endpoint URL (HTTPS)" htmlFor="webhook-url">
              <Input
                id="webhook-url"
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://your-app.com/webhooks/lintpdf"
              />
            </FormField>
            <div>
              <label className="block text-sm font-medium">Events</label>
              <div className="mt-1 flex flex-wrap gap-2">
                {AVAILABLE_EVENTS.map((event) => (
                  <label
                    key={event}
                    className="flex items-center gap-1.5 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={newEvents.includes(event)}
                      onChange={() =>
                        toggleEvent(newEvents, setNewEvents, event)
                      }
                    />
                    {event}
                  </label>
                ))}
              </div>
            </div>
            <Button
              onClick={handleCreate}
              disabled={!newUrl}
              loading={creating}
            >
              Create Webhook
            </Button>
          </div>
        </div>
      )}

      {/* Webhook list */}
      <div className="mt-6 space-y-4">
        {webhooks.length === 0 ? (
          <EmptyState
            icon="Webhook"
            title="No webhooks configured"
            description="Add one to start receiving event notifications."
            action={
              <Button
                onClick={() => setShowCreate(true)}
              >
                Add Webhook
              </Button>
            }
          />
        ) : (
          webhooks.map((wh) => (
            <div key={wh.id} className="rounded-lg border p-4">
              {editingId === wh.id ? (
                <div className="space-y-3">
                  <FormField label="Endpoint URL" htmlFor={`edit-url-${wh.id}`}>
                    <Input
                      id={`edit-url-${wh.id}`}
                      type="url"
                      value={editUrl}
                      onChange={(e) => setEditUrl(e.target.value)}
                    />
                  </FormField>
                  <div className="flex flex-wrap gap-2">
                    {AVAILABLE_EVENTS.map((event) => (
                      <label
                        key={event}
                        className="flex items-center gap-1.5 text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={editEvents.includes(event)}
                          onChange={() =>
                            toggleEvent(editEvents, setEditEvents, event)
                          }
                        />
                        {event}
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleUpdate(wh.id)}
                    >
                      Save
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${wh.is_active ? "bg-success" : "bg-muted"}`}
                        />
                        <code className="truncate text-sm">{wh.url}</code>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {wh.events.map((ev) => (
                          <span
                            key={ev}
                            className="rounded bg-muted px-1.5 py-0.5 text-xs"
                          >
                            {ev}
                          </span>
                        ))}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Created {new Date(wh.created_at).toLocaleDateString()}
                      </p>
                      {testResult?.id === wh.id && (
                        <div
                          className={`mt-2 rounded px-2 py-1 text-xs ${testResult.success ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}
                        >
                          {testResult.success
                            ? `Test delivered (HTTP ${testResult.status_code})`
                            : `Test failed: ${testResult.error}`}
                        </div>
                      )}
                    </div>
                    <div className="ml-4 flex shrink-0 items-center gap-1">
                      <Link
                        href={`/dashboard/webhooks/${wh.id}/deliveries`}
                        className="inline-flex"
                      >
                        <Button variant="secondary" size="sm">
                          Deliveries
                        </Button>
                      </Link>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleTest(wh.id)}
                        loading={testingId === wh.id}
                      >
                        Test
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setEditingId(wh.id);
                          setEditUrl(wh.url);
                          setEditEvents(wh.events);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleToggle(wh.id, wh.is_active)}
                      >
                        {wh.is_active ? "Disable" : "Enable"}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          setConfirmTarget(wh.id);
                          setConfirmOpen(true);
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        onConfirm={async () => {
          if (confirmTarget) await handleDelete(confirmTarget);
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        title="Delete webhook?"
        description="This action cannot be undone. You will stop receiving event notifications at this endpoint."
        variant="destructive"
        confirmLabel="Delete"
      />
    </>
  );
}
