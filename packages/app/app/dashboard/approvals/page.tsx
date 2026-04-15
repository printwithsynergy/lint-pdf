"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@thinkneverland/pixie-dust-ui";

interface Approver {
  email: string;
  name?: string;
  role?: string;
}

interface Step {
  name: string;
  approvers: Approver[];
  require_all: boolean;
  webhook_url?: string | null;
  timeout_hours?: number | null;
  on_timeout: "reject" | "advance" | "notify";
}

interface Template {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  steps: Step[];
  created_at: string;
  updated_at: string;
}

const EMPTY_STEP: Step = {
  name: "",
  approvers: [{ email: "", name: "", role: "" }],
  require_all: false,
  webhook_url: null,
  timeout_hours: null,
  on_timeout: "notify",
};

const EMPTY_TEMPLATE: Omit<Template, "id" | "created_at" | "updated_at"> = {
  name: "",
  description: "",
  is_default: false,
  steps: [{ ...EMPTY_STEP, approvers: [{ email: "", name: "", role: "" }] }],
};

export default function ApprovalsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<
    | (Partial<Template> & { steps: Step[]; name: string; description?: string | null; is_default: boolean })
    | null
  >(null);
  const [saving, setSaving] = useState(false);

  const fetchTemplates = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/approval-templates");
      if (resp.status === 403) {
        setError("upgrade");
        setLoading(false);
        return;
      }
      if (!resp.ok) throw new Error("Failed to load templates");
      const data = await resp.json();
      setTemplates(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  function openNew() {
    setEditing({ ...EMPTY_TEMPLATE });
  }
  function openEdit(t: Template) {
    setEditing({
      id: t.id,
      name: t.name,
      description: t.description,
      is_default: t.is_default,
      steps: t.steps.map((s) => ({
        ...s,
        approvers: s.approvers.length > 0 ? s.approvers : [{ email: "" }],
      })),
    });
  }
  function closeEdit() {
    setEditing(null);
    setError("");
  }

  function addStep() {
    if (!editing) return;
    setEditing({
      ...editing,
      steps: [...editing.steps, { ...EMPTY_STEP, approvers: [{ email: "" }] }],
    });
  }
  function removeStep(i: number) {
    if (!editing || editing.steps.length <= 1) return;
    setEditing({ ...editing, steps: editing.steps.filter((_, idx) => idx !== i) });
  }
  function moveStep(i: number, dir: -1 | 1) {
    if (!editing) return;
    const j = i + dir;
    if (j < 0 || j >= editing.steps.length) return;
    const steps = [...editing.steps];
    // i/j are numeric indices into a local array we just bounds-checked.
    // eslint-disable-next-line security/detect-object-injection
    [steps[i], steps[j]] = [steps[j]!, steps[i]!];
    setEditing({ ...editing, steps });
  }
  function updateStep(i: number, patch: Partial<Step>) {
    if (!editing) return;
    const steps = [...editing.steps];
    // i is a numeric index supplied by our own map() callers.
    // eslint-disable-next-line security/detect-object-injection
    steps[i] = { ...steps[i]!, ...patch };
    setEditing({ ...editing, steps });
  }
  function addApprover(stepIdx: number) {
    if (!editing) return;
    const steps = [...editing.steps];
    // stepIdx is a numeric index supplied by our own map() callers.
    // eslint-disable-next-line security/detect-object-injection
    steps[stepIdx]!.approvers.push({ email: "" });
    setEditing({ ...editing, steps });
  }
  function removeApprover(stepIdx: number, approverIdx: number) {
    if (!editing) return;
    const steps = [...editing.steps];
    // stepIdx/approverIdx are numeric indices supplied by our own map() callers.
    // eslint-disable-next-line security/detect-object-injection
    if (steps[stepIdx]!.approvers.length <= 1) return;
    // eslint-disable-next-line security/detect-object-injection
    steps[stepIdx]!.approvers = steps[stepIdx]!.approvers.filter((_, idx) => idx !== approverIdx);
    setEditing({ ...editing, steps });
  }
  function updateApprover(stepIdx: number, approverIdx: number, patch: Partial<Approver>) {
    if (!editing) return;
    const steps = [...editing.steps];
    // stepIdx/approverIdx are numeric indices supplied by our own map() callers.
    // eslint-disable-next-line security/detect-object-injection
    steps[stepIdx]!.approvers[approverIdx] = { ...steps[stepIdx]!.approvers[approverIdx]!, ...patch };
    setEditing({ ...editing, steps });
  }

  async function save() {
    if (!editing) return;
    setError("");

    // Validate
    if (!editing.name.trim()) {
      setError("Template name is required");
      return;
    }
    for (const [si, step] of editing.steps.entries()) {
      if (!step.name.trim()) {
        setError(`Step ${si + 1}: name is required`);
        return;
      }
      const validApprovers = step.approvers.filter((a) => a.email.trim());
      if (validApprovers.length === 0) {
        setError(`Step ${si + 1}: at least one approver email is required`);
        return;
      }
      const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      for (const a of validApprovers) {
        if (!emailRe.test(a.email.trim())) {
          setError(`Step ${si + 1}: invalid email "${a.email}"`);
          return;
        }
      }
    }

    setSaving(true);
    try {
      const payload = {
        name: editing.name.trim(),
        description: editing.description?.trim() || null,
        is_default: editing.is_default,
        steps: editing.steps.map((s) => ({
          name: s.name.trim(),
          approvers: s.approvers
            .filter((a) => a.email.trim())
            .map((a) => ({
              email: a.email.trim(),
              name: a.name?.trim() || null,
              role: a.role?.trim() || null,
            })),
          require_all: s.require_all,
          webhook_url: s.webhook_url?.trim() || null,
          timeout_hours: s.timeout_hours ?? null,
          on_timeout: s.on_timeout,
        })),
      };

      const url = editing.id
        ? `/api/lintpdf/approval-templates/${editing.id}`
        : "/api/lintpdf/approval-templates";
      const method = editing.id ? "PATCH" : "POST";
      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to save template");
      }
      await fetchTemplates();
      closeEdit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this template? This cannot be undone.")) return;
    try {
      const resp = await fetch(`/api/lintpdf/approval-templates/${id}`, { method: "DELETE" });
      if (!resp.ok) throw new Error("Failed to delete");
      await fetchTemplates();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <svg className="h-8 w-8 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error === "upgrade") {
    return (
      <div className="mx-auto max-w-2xl p-8">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
          <h1 className="mb-2 text-2xl font-bold text-amber-900">Approval Chains — Upgrade Required</h1>
          <p className="mb-4 text-sm text-amber-800">
            Multi-step approval chains are available on Growth, Scale, and Enterprise plans.
            Build reusable approval templates and let your team sign off on preflight reports
            with email notifications and external webhooks at each step.
          </p>
          <Link
            href="/dashboard/billing"
            className="inline-block rounded-md bg-amber-600 px-5 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            View Plans
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Approval Chains</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Build reusable multi-step approval workflows for your preflight reports.
          </p>
        </div>
        {!editing && (
          <Button onClick={openNew}>+ New Template</Button>
        )}
      </div>

      {!editing && (
        <>
          {templates.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-12 text-center">
              <h2 className="mb-2 font-semibold">No approval templates yet</h2>
              <p className="mb-4 text-sm text-muted-foreground">
                Create your first template to enable multi-step approval workflows on preflight reports.
              </p>
              <Button onClick={openNew}>Create Template</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((t) => (
                <div
                  key={t.id}
                  className="rounded-lg border bg-card p-4 shadow-sm"
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{t.name}</h3>
                        {t.is_default && (
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold uppercase text-blue-700">
                            Default
                          </span>
                        )}
                      </div>
                      {t.description && (
                        <p className="mt-1 text-sm text-muted-foreground">{t.description}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEdit(t)}
                        className="rounded border px-3 py-1 text-xs hover:bg-muted"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => remove(t.id)}
                        className="rounded border border-red-200 px-3 py-1 text-xs text-red-600 hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {t.steps.map((s, i) => (
                      <span
                        key={i}
                        className="rounded bg-slate-100 px-2 py-1 text-slate-700"
                      >
                        <span className="mr-1 font-bold text-slate-500">{i + 1}.</span>
                        {s.name}{" "}
                        <span className="text-slate-400">
                          ({s.approvers.length}{" "}
                          {s.approvers.length === 1 ? "approver" : "approvers"})
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {editing && (
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {editing.id ? "Edit Template" : "New Template"}
            </h2>
            <button
              onClick={closeEdit}
              className="text-sm text-muted-foreground hover:underline"
            >
              Cancel
            </button>
          </div>

          {error && error !== "upgrade" && (
            <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium">
              Name <span className="text-destructive">*</span>
              <input
                type="text"
                value={editing.name}
                onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                placeholder="Standard Print Approval"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </label>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium">
              Description
              <input
                type="text"
                value={editing.description ?? ""}
                onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                placeholder="Used for all production print jobs"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </label>
          </div>

          <label className="mb-6 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={editing.is_default}
              onChange={(e) => setEditing({ ...editing, is_default: e.target.checked })}
            />
            <span>Mark as default template</span>
            <span className="text-xs text-muted-foreground">
              (can be auto-attached to new jobs)
            </span>
          </label>

          <div className="mb-4">
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Approval Steps
            </h3>

            {editing.steps.map((step, si) => (
              <div
                key={si}
                className="mb-3 rounded-lg border bg-slate-50 p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {si + 1}
                    </span>
                    <input
                      type="text"
                      value={step.name}
                      onChange={(e) => updateStep(si, { name: e.target.value })}
                      placeholder="Production Manager"
                      className="flex-1 rounded-md border px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="ml-2 flex gap-1">
                    <button
                      onClick={() => moveStep(si, -1)}
                      disabled={si === 0}
                      className="rounded p-1 text-slate-500 hover:bg-slate-200 disabled:opacity-30"
                      title="Move up"
                    >
                      ↑
                    </button>
                    <button
                      onClick={() => moveStep(si, 1)}
                      disabled={si === editing.steps.length - 1}
                      className="rounded p-1 text-slate-500 hover:bg-slate-200 disabled:opacity-30"
                      title="Move down"
                    >
                      ↓
                    </button>
                    <button
                      onClick={() => removeStep(si)}
                      disabled={editing.steps.length <= 1}
                      className="rounded p-1 text-red-500 hover:bg-red-50 disabled:opacity-30"
                      title="Remove step"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Approvers
                </div>
                {step.approvers.map((a, ai) => (
                  <div key={ai} className="mb-2 flex gap-2">
                    <input
                      type="email"
                      value={a.email}
                      onChange={(e) => updateApprover(si, ai, { email: e.target.value })}
                      placeholder="approver@company.com"
                      className="flex-1 rounded-md border px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-primary"
                    />
                    <input
                      type="text"
                      value={a.name ?? ""}
                      onChange={(e) => updateApprover(si, ai, { name: e.target.value })}
                      placeholder="Name (optional)"
                      className="w-32 rounded-md border px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-primary"
                    />
                    <input
                      type="text"
                      value={a.role ?? ""}
                      onChange={(e) => updateApprover(si, ai, { role: e.target.value })}
                      placeholder="Role"
                      className="w-28 rounded-md border px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-primary"
                    />
                    <button
                      onClick={() => removeApprover(si, ai)}
                      disabled={step.approvers.length <= 1}
                      className="rounded px-2 text-red-500 hover:bg-red-50 disabled:opacity-30"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => addApprover(si)}
                  className="mb-3 text-xs text-primary hover:underline"
                >
                  + Add approver
                </button>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={step.require_all}
                      onChange={(e) => updateStep(si, { require_all: e.target.checked })}
                    />
                    <span>Require ALL approvers</span>
                  </label>
                  <label className="block text-xs">
                    Timeout (hours)
                    <input
                      type="number"
                      min={0}
                      max={720}
                      value={step.timeout_hours ?? ""}
                      onChange={(e) =>
                        updateStep(si, {
                          timeout_hours: e.target.value ? Number(e.target.value) : null,
                        })
                      }
                      placeholder="No timeout"
                      className="mt-1 w-full rounded-md border px-2 py-1 text-xs"
                    />
                  </label>
                  <label className="block text-xs">
                    On timeout
                    <select
                      value={step.on_timeout}
                      onChange={(e) =>
                        updateStep(si, {
                          on_timeout: e.target.value as "reject" | "advance" | "notify",
                        })
                      }
                      className="mt-1 w-full rounded-md border px-2 py-1 text-xs"
                    >
                      <option value="notify">Re-notify</option>
                      <option value="reject">Auto-reject</option>
                      <option value="advance">Auto-approve</option>
                    </select>
                  </label>
                </div>

                <label className="mt-3 block text-xs">
                  Webhook URL (optional)
                  <input
                    type="url"
                    value={step.webhook_url ?? ""}
                    onChange={(e) => updateStep(si, { webhook_url: e.target.value })}
                    placeholder="https://your-system.com/approval-webhook"
                    className="mt-1 w-full rounded-md border px-2 py-1 text-xs font-mono"
                  />
                </label>
              </div>
            ))}

            <button
              onClick={addStep}
              className="w-full rounded-md border-2 border-dashed border-slate-300 px-4 py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary"
            >
              + Add Step
            </button>
          </div>

          <div className="flex justify-end gap-2 border-t pt-4">
            <Button variant="secondary" onClick={closeEdit}>
              Cancel
            </Button>
            <Button onClick={save} disabled={saving} loading={saving}>
              {editing.id ? "Save Changes" : "Create Template"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
