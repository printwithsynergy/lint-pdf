"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface BrandSpecColor {
  name: string;
  value: string;
  pantone?: string | null;
  notes?: string | null;
}

interface BrandSpecRichBlack {
  c: number;
  m: number;
  y: number;
  k: number;
}

interface BrandSpec {
  id: string;
  tenant_id: string;
  name: string;
  customer_name: string | null;
  description: string | null;
  colors: BrandSpecColor[];
  rich_black_spec: BrandSpecRichBlack | null;
  is_default: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

const EMPTY_COLOR: BrandSpecColor = { name: "", value: "#000000" };
const EMPTY_RICH_BLACK: BrandSpecRichBlack = { c: 60, m: 50, y: 50, k: 100 };

export default function BrandSpecsPage() {
  const [specs, setSpecs] = useState<BrandSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);

  // Create / edit state. A null editingId means "no form shown"; the
  // string "new" means the create form is open; any other string is
  // the id of the spec being patched.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftCustomer, setDraftCustomer] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftColors, setDraftColors] = useState<BrandSpecColor[]>([]);
  const [draftIsDefault, setDraftIsDefault] = useState(false);
  const [draftRichBlack, setDraftRichBlack] = useState<BrandSpecRichBlack | null>(
    null,
  );
  const [saving, setSaving] = useState(false);

  const fetchSpecs = useCallback(async () => {
    try {
      const qs = includeArchived ? "?include_archived=true" : "";
      const resp = await fetch(`/api/lintpdf/brand-specs${qs}`);
      if (resp.ok) {
        const data = await resp.json();
        setSpecs(data.brand_specs ?? []);
      } else {
        setError(`Failed to load brand specs (${resp.status})`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load brand specs");
    } finally {
      setLoading(false);
    }
  }, [includeArchived]);

  useEffect(() => {
    fetchSpecs();
  }, [fetchSpecs]);

  function resetDraft() {
    setDraftName("");
    setDraftCustomer("");
    setDraftDescription("");
    setDraftColors([]);
    setDraftIsDefault(false);
    setDraftRichBlack(null);
  }

  function openCreate() {
    resetDraft();
    setEditingId("new");
  }

  function openEdit(spec: BrandSpec) {
    setDraftName(spec.name);
    setDraftCustomer(spec.customer_name ?? "");
    setDraftDescription(spec.description ?? "");
    setDraftColors(spec.colors.map((c) => ({ ...c })));
    setDraftIsDefault(spec.is_default);
    setDraftRichBlack(spec.rich_black_spec ? { ...spec.rich_black_spec } : null);
    setEditingId(spec.id);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    const body = {
      name: draftName,
      customer_name: draftCustomer || null,
      description: draftDescription || null,
      colors: draftColors
        .map((c) => ({ ...c, name: c.name.trim(), value: c.value.trim() }))
        .filter((c) => c.name && c.value),
      rich_black_spec: draftRichBlack,
      is_default: draftIsDefault,
    };
    try {
      const url =
        editingId === "new"
          ? "/api/lintpdf/brand-specs"
          : `/api/lintpdf/brand-specs/${editingId}`;
      const resp = await fetch(url, {
        method: editingId === "new" ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail ?? data.error ?? "Failed to save spec");
      }
      setEditingId(null);
      resetDraft();
      await fetchSpecs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save spec");
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive(id: string) {
    if (!confirm("Archive this brand spec? Historical jobs still resolve to it.")) {
      return;
    }
    try {
      const resp = await fetch(`/api/lintpdf/brand-specs/${id}`, {
        method: "DELETE",
      });
      if (!resp.ok && resp.status !== 204) {
        throw new Error(`Archive failed (${resp.status})`);
      }
      await fetchSpecs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Archive failed");
    }
  }

  async function handleRestore(id: string) {
    try {
      const resp = await fetch(`/api/lintpdf/brand-specs/${id}/restore`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error(`Restore failed (${resp.status})`);
      await fetchSpecs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Restore failed");
    }
  }

  if (loading) return <SkeletonDashboard type="table" />;

  const isEditing = editingId !== null;

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Brand Specs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Named colour specifications, one per end-customer. Specs plug into
            preflight at three levels: the tenant-default row catches every job
            with no explicit override; endpoints can pin a default for every
            submission through them; individual submissions can pass{" "}
            <code>brand_spec_id</code> to override both.
          </p>
        </div>
        {!isEditing && <Button onClick={openCreate}>New Brand Spec</Button>}
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {isEditing && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">
            {editingId === "new" ? "New brand spec" : "Edit brand spec"}
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">Spec name</label>
              <input
                type="text"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                placeholder="Coca-Cola"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">
                Customer name (optional)
              </label>
              <input
                type="text"
                value={draftCustomer}
                onChange={(e) => setDraftCustomer(e.target.value)}
                placeholder="Coca-Cola Co."
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="mt-3">
            <label className="block text-sm font-medium">Description</label>
            <textarea
              value={draftDescription}
              onChange={(e) => setDraftDescription(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <SwatchEditor colors={draftColors} onChange={setDraftColors} />
          <RichBlackEditor spec={draftRichBlack} onChange={setDraftRichBlack} />
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={draftIsDefault}
              onChange={(e) => setDraftIsDefault(e.target.checked)}
            />
            Use as tenant-default spec (applies to every job without an
            explicit override)
          </label>
          <div className="mt-4 flex gap-2">
            <Button onClick={handleSave} loading={saving} disabled={!draftName}>
              {editingId === "new" ? "Create" : "Save"}
            </Button>
            <button
              onClick={() => {
                setEditingId(null);
                resetDraft();
              }}
              className="rounded-md border px-3 py-1.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <div className="text-sm font-medium text-muted-foreground">
          {specs.length} spec{specs.length === 1 ? "" : "s"}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          Show archived
        </label>
      </div>

      <div className="mt-3 space-y-3">
        {specs.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
            No brand specs yet. Create one to unlock per-customer palette
            enforcement on your preflight jobs.
          </div>
        ) : (
          specs.map((s) => (
            <div
              key={s.id}
              className={`rounded-lg border p-4 ${s.is_archived ? "opacity-60" : ""}`}
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-base font-semibold">{s.name}</h3>
                    {s.is_default && (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                        Tenant default
                      </span>
                    )}
                    {s.is_archived && (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                        Archived
                      </span>
                    )}
                  </div>
                  {s.customer_name && (
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {s.customer_name}
                    </p>
                  )}
                  {s.description && (
                    <p className="mt-1 text-sm">{s.description}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {s.colors.map((c, i) => (
                      <span
                        key={i}
                        title={`${c.name} — ${c.value}`}
                        className="flex h-6 w-6 rounded border"
                        style={{ background: c.value }}
                      />
                    ))}
                    {s.colors.length === 0 && (
                      <span className="text-xs text-muted-foreground">
                        No swatches yet
                      </span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex shrink-0 gap-1">
                  {!s.is_archived && (
                    <button
                      onClick={() => openEdit(s)}
                      className="rounded border px-2 py-1 text-xs hover:bg-muted"
                    >
                      Edit
                    </button>
                  )}
                  {s.is_archived ? (
                    <button
                      onClick={() => handleRestore(s.id)}
                      className="rounded border px-2 py-1 text-xs hover:bg-muted"
                    >
                      Restore
                    </button>
                  ) : (
                    <button
                      onClick={() => handleArchive(s.id)}
                      className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                    >
                      Archive
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}

function SwatchEditor({
  colors,
  onChange,
}: {
  colors: BrandSpecColor[];
  onChange: (next: BrandSpecColor[]) => void;
}) {
  function update(i: number, patch: Partial<BrandSpecColor>) {
    const next = colors.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  }
  return (
    <div className="mt-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Swatches</label>
        <button
          type="button"
          onClick={() => onChange([...colors, { ...EMPTY_COLOR }])}
          className="rounded border px-2 py-1 text-xs hover:bg-muted"
        >
          Add swatch
        </button>
      </div>
      {colors.length === 0 ? (
        <p className="mt-1 text-xs text-muted-foreground">
          Add at least one swatch to unlock strict colour advisories.
        </p>
      ) : (
        <div className="mt-2 space-y-2">
          {colors.map((c, i) => (
            <div
              key={i}
              className="grid grid-cols-[auto_1fr_1fr_1fr_auto] items-center gap-2"
            >
              <input
                type="color"
                value={/^#[0-9a-fA-F]{6}$/.test(c.value) ? c.value : "#000000"}
                onChange={(e) => update(i, { value: e.target.value })}
                className="h-9 w-9 rounded border"
              />
              <input
                type="text"
                value={c.name}
                onChange={(e) => update(i, { name: e.target.value })}
                placeholder="Swatch name"
                className="rounded-md border px-2 py-1.5 text-sm"
              />
              <input
                type="text"
                value={c.value}
                onChange={(e) => update(i, { value: e.target.value })}
                placeholder="#RRGGBB or cmyk(...)"
                className="rounded-md border px-2 py-1.5 text-sm font-mono"
              />
              <input
                type="text"
                value={c.pantone ?? ""}
                onChange={(e) => update(i, { pantone: e.target.value || null })}
                placeholder="PMS (optional)"
                className="rounded-md border px-2 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={() => onChange(colors.filter((_, j) => j !== i))}
                className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RichBlackEditor({
  spec,
  onChange,
}: {
  spec: BrandSpecRichBlack | null;
  onChange: (next: BrandSpecRichBlack | null) => void;
}) {
  return (
    <div className="mt-4">
      <label className="flex items-center gap-2 text-sm font-medium">
        <input
          type="checkbox"
          checked={spec !== null}
          onChange={(e) => onChange(e.target.checked ? { ...EMPTY_RICH_BLACK } : null)}
        />
        Target rich-black composition
      </label>
      {spec && (
        <div className="mt-2 grid grid-cols-4 gap-2">
          {(["c", "m", "y", "k"] as const).map((ch) => (
            <label key={ch} className="text-xs font-mono uppercase">
              {ch}
              <input
                type="number"
                min={0}
                max={100}
                value={spec[ch]}
                onChange={(e) => onChange({ ...spec, [ch]: Number(e.target.value) })}
                className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
              />
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
