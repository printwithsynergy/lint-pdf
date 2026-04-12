"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Badge,
  Button,
  EmptyState,
  FormField,
  Input,
  Select,
  useToast,
} from "@thinkneverland/pixie-dust-ui";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Canonical finding-field keys understood by the engine's CustomMappingParser.
 * Kept in sync with ``_CANONICAL_FIELDS`` in
 * ``packages/engine/src/lintpdf/imports/custom.py``.
 */
const CANONICAL_FIELDS = [
  "severity",
  "message",
  "page",
  "bbox",
  "check_id",
  "object_id",
  "object_type",
  "category",
  "iso_clause",
] as const;
type CanonicalField = (typeof CANONICAL_FIELDS)[number];

interface FieldRow {
  /** Canonical field key — or "" when the row is fresh and unassigned. */
  field: CanonicalField | "";
  /** Selector expression (XML path / JSON dotted path). */
  selector: string;
}

interface SeverityRow {
  raw: string;
  mapped: "error" | "warning" | "advisory" | "";
}

interface MappingRow {
  id: string;
  name: string;
  description: string | null;
  format: "xml" | "json";
  config: Record<string, unknown>;
  sample_payload: string | null;
  sample_mime: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PreviewFinding {
  severity: string;
  message: string;
  page_num: number;
  inspection_id: string;
  bbox: [number, number, number, number] | null;
  object_id: string | null;
  object_type: string | null;
  category: string | null;
}

interface PreviewResult {
  ok: boolean;
  findings_count: number;
  sample_findings: PreviewFinding[];
  error: string | null;
}

// ---------------------------------------------------------------------------
// Form ↔ config conversion
// ---------------------------------------------------------------------------

function parseFields(
  cfg: Record<string, unknown> | null | undefined,
): FieldRow[] {
  const fields = (cfg?.fields ?? {}) as Record<string, unknown>;
  const rows: FieldRow[] = [];
  for (const [key, value] of Object.entries(fields)) {
    if (!CANONICAL_FIELDS.includes(key as CanonicalField)) continue;
    const selector =
      typeof value === "string"
        ? value
        : typeof value === "object" && value !== null && "selector" in value
          ? String((value as Record<string, unknown>).selector ?? "")
          : "";
    rows.push({ field: key as CanonicalField, selector });
  }
  return rows;
}

function parseSeverityMap(
  cfg: Record<string, unknown> | null | undefined,
): SeverityRow[] {
  const sev = (cfg?.severity_map ?? {}) as Record<string, unknown>;
  return Object.entries(sev).map(([raw, mapped]) => ({
    raw,
    mapped: (String(mapped) as SeverityRow["mapped"]) || "",
  }));
}

function buildConfig(
  format: "xml" | "json",
  itemSelector: string,
  fieldRows: FieldRow[],
  severityRows: SeverityRow[],
  defaultSeverity: string,
  sourceTool: string,
): Record<string, unknown> {
  const fields: Record<string, string> = {};
  for (const row of fieldRows) {
    if (!row.field || !row.selector.trim()) continue;
    fields[row.field] = row.selector.trim();
  }
  const severity_map: Record<string, string> = {};
  for (const row of severityRows) {
    if (!row.raw.trim() || !row.mapped) continue;
    severity_map[row.raw.trim()] = row.mapped;
  }
  const cfg: Record<string, unknown> = {
    format,
    item_selector: itemSelector.trim(),
    fields,
  };
  if (Object.keys(severity_map).length > 0) cfg.severity_map = severity_map;
  if (defaultSeverity.trim()) cfg.default_severity = defaultSeverity.trim();
  if (sourceTool.trim()) cfg.source_tool = sourceTool.trim();
  return cfg;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ImportMappingsPage() {
  const [mappings, setMappings] = useState<MappingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<PreviewResult | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [format, setFormat] = useState<"xml" | "json">("xml");
  const [itemSelector, setItemSelector] = useState("");
  const [fieldRows, setFieldRows] = useState<FieldRow[]>([
    { field: "message", selector: "" },
  ]);
  const [severityRows, setSeverityRows] = useState<SeverityRow[]>([]);
  const [defaultSeverity, setDefaultSeverity] = useState("warning");
  const [sourceTool, setSourceTool] = useState("");
  const [samplePayload, setSamplePayload] = useState("");
  const [sampleMime, setSampleMime] = useState("");
  const [isActive, setIsActive] = useState(true);

  const { toast } = useToast();

  // ── Drag-and-drop ────────────────────────────────────────────────
  // Two DnD surfaces:
  //   1. Drop a sample report file onto the payload textarea to auto-fill
  //      both the textarea content and the MIME field.
  //   2. Reorder field rows via native HTML5 drag-and-drop.
  const [isDropping, setIsDropping] = useState(false);
  const [dragFieldIndex, setDragFieldIndex] = useState<number | null>(null);
  const payloadRef = useRef<HTMLDivElement | null>(null);

  const onPayloadDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      if (!e.dataTransfer?.types?.includes("Files")) return;
      e.preventDefault();
      setIsDropping(true);
    },
    [],
  );

  const onPayloadDragLeave = useCallback(() => {
    setIsDropping(false);
  }, []);

  const onPayloadDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDropping(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      // Guard against oversized files — the engine caps at 50 MB but we
      // stop far sooner in the editor because the textarea isn't built
      // for huge payloads.
      const maxBytes = 5 * 1024 * 1024;
      if (file.size > maxBytes) {
        toast({
          title: "File too large",
          description: `Sample files in the editor must be under ${maxBytes / 1024 / 1024} MB. Use a smaller sample.`,
          variant: "destructive",
        });
        return;
      }
      try {
        const text = await file.text();
        setSamplePayload(text);
        // Infer MIME + format from the file extension.
        const lower = file.name.toLowerCase();
        if (lower.endsWith(".json")) {
          setSampleMime(file.type || "application/json");
          setFormat("json");
        } else if (lower.endsWith(".xml")) {
          setSampleMime(file.type || "application/xml");
          setFormat("xml");
        } else if (file.type) {
          setSampleMime(file.type);
        }
        toast({
          title: "Sample loaded",
          description: `${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
        });
      } catch {
        toast({ title: "Could not read file", variant: "destructive" });
      }
    },
    [toast],
  );

  function onFieldDragStart(idx: number) {
    setDragFieldIndex(idx);
  }

  function onFieldDragOver(e: React.DragEvent<HTMLTableRowElement>) {
    if (dragFieldIndex === null) return;
    e.preventDefault();
  }

  function onFieldDrop(targetIdx: number) {
    if (dragFieldIndex === null || dragFieldIndex === targetIdx) {
      setDragFieldIndex(null);
      return;
    }
    setFieldRows((rows) => {
      const next = rows.slice();
      const [moved] = next.splice(dragFieldIndex, 1);
      next.splice(targetIdx, 0, moved);
      return next;
    });
    setDragFieldIndex(null);
  }

  const resetForm = useCallback(() => {
    setName("");
    setDescription("");
    setFormat("xml");
    setItemSelector("");
    setFieldRows([{ field: "message", selector: "" }]);
    setSeverityRows([]);
    setDefaultSeverity("warning");
    setSourceTool("");
    setSamplePayload("");
    setSampleMime("");
    setIsActive(true);
    setEditingId(null);
    setPreview(null);
  }, []);

  const loadMappings = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await fetch("/api/lintpdf/import-mappings");
      if (!resp.ok) throw new Error("Failed to load mappings");
      const data = await resp.json();
      setMappings(data.mappings ?? []);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load mappings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMappings();
  }, [loadMappings]);

  function beginEdit(row: MappingRow) {
    setEditingId(row.id);
    setName(row.name);
    setDescription(row.description ?? "");
    setFormat(row.format);
    setItemSelector(String(row.config?.item_selector ?? ""));
    const parsed = parseFields(row.config);
    setFieldRows(parsed.length ? parsed : [{ field: "message", selector: "" }]);
    setSeverityRows(parseSeverityMap(row.config));
    setDefaultSeverity(String(row.config?.default_severity ?? "warning"));
    setSourceTool(String(row.config?.source_tool ?? ""));
    setSamplePayload(row.sample_payload ?? "");
    setSampleMime(row.sample_mime ?? "");
    setIsActive(row.is_active);
    setPreview(null);
    setShowForm(true);
  }

  function buildPayload() {
    return {
      name: name.trim(),
      description: description.trim() || null,
      format,
      config: buildConfig(
        format,
        itemSelector,
        fieldRows,
        severityRows,
        defaultSeverity,
        sourceTool,
      ),
      sample_payload: samplePayload || null,
      sample_mime: sampleMime.trim() || null,
      is_active: isActive,
    };
  }

  async function save() {
    if (!name.trim() || !itemSelector.trim()) {
      toast({
        title: "Missing required fields",
        description: "Name and item selector are required.",
        variant: "destructive",
      });
      return;
    }
    setSaving(true);
    try {
      const payload = buildPayload();
      const url = editingId
        ? `/api/lintpdf/import-mappings/${editingId}`
        : "/api/lintpdf/import-mappings";
      const resp = await fetch(url, {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      toast({ title: editingId ? "Mapping updated" : "Mapping created" });
      setShowForm(false);
      resetForm();
      await loadMappings();
    } catch (e) {
      toast({
        title: "Save failed",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    if (
      !window.confirm(
        "Deactivate this mapping? Existing jobs keep their history.",
      )
    ) {
      return;
    }
    const resp = await fetch(`/api/lintpdf/import-mappings/${id}`, {
      method: "DELETE",
    });
    if (!resp.ok) {
      toast({
        title: "Delete failed",
        description: `HTTP ${resp.status}`,
        variant: "destructive",
      });
      return;
    }
    toast({ title: "Mapping deactivated" });
    await loadMappings();
  }

  async function runPreview() {
    // The preview route needs a persisted row. If we're editing we can
    // post overrides so the dry-run reflects unsaved edits.
    if (!editingId) {
      toast({
        title: "Save first to preview",
        description:
          "Create the mapping before previewing — we need a row to hang the dry-run on.",
      });
      return;
    }
    setPreviewing(true);
    try {
      const payload = buildPayload();
      const resp = await fetch(
        `/api/lintpdf/import-mappings/${editingId}/preview`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            config: payload.config,
            sample_payload: payload.sample_payload,
          }),
        },
      );
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const result = (await resp.json()) as PreviewResult;
      setPreview(result);
    } catch (e) {
      setPreview({
        ok: false,
        findings_count: 0,
        sample_findings: [],
        error: e instanceof Error ? e.message : "Preview failed",
      });
    } finally {
      setPreviewing(false);
    }
  }

  const fieldsAvailable = useMemo(() => {
    const used = new Set(fieldRows.map((r) => r.field).filter(Boolean));
    return CANONICAL_FIELDS.filter((f) => !used.has(f));
  }, [fieldRows]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Custom import mappings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Teach LintPDF how to read your proprietary preflight XML or JSON.
            Each mapping describes where severity, message, page, and other
            fields live in your payload — we’ll translate it into LintPDF
            findings at submit time.
          </p>
        </div>
        <Button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
        >
          New mapping
        </Button>
      </header>

      {error ? (
        <div className="rounded border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : mappings.length === 0 ? (
        <EmptyState
          title="No mappings yet"
          description="Create your first mapping to import findings from a custom preflight tool."
        />
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="py-2">Name</th>
              <th className="py-2">Format</th>
              <th className="py-2">Status</th>
              <th className="py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((m) => (
              <tr key={m.id} className="border-b last:border-0">
                <td className="py-3">
                  <div className="font-medium">{m.name}</div>
                  {m.description ? (
                    <div className="text-xs text-muted-foreground">
                      {m.description}
                    </div>
                  ) : null}
                </td>
                <td className="py-3 uppercase">{m.format}</td>
                <td className="py-3">
                  {m.is_active ? (
                    <Badge variant="default">Active</Badge>
                  ) : (
                    <Badge variant="outline">Inactive</Badge>
                  )}
                </td>
                <td className="py-3 text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => beginEdit(m)}
                  >
                    Edit
                  </Button>{" "}
                  {m.is_active ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(m.id)}
                    >
                      Deactivate
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showForm ? (
        <section className="rounded border p-4">
          <h2 className="text-lg font-semibold">
            {editingId ? "Edit mapping" : "New mapping"}
          </h2>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <FormField label="Name" htmlFor="mapping-name">
              <Input
                id="mapping-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Acme PitStop-lite"
              />
            </FormField>
            <FormField label="Format" htmlFor="mapping-format">
              <Select
                id="mapping-format"
                value={format}
                onChange={(e) =>
                  setFormat(e.target.value as "xml" | "json")
                }
              >
                <option value="xml">XML</option>
                <option value="json">JSON</option>
              </Select>
            </FormField>
          </div>

          <FormField
            label="Description"
            htmlFor="mapping-description"
            className="mt-4"
          >
            <Input
              id="mapping-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional notes — e.g. vendor + version"
            />
          </FormField>

          <FormField
            label="Item selector"
            htmlFor="mapping-item-selector"
            className="mt-4"
            description={
              format === "xml"
                ? "Path to each finding element. Examples: Issues/Issue, //Hit. Namespaces handled by localname."
                : "Dotted path to each finding. Examples: results[*].issues[*], data.findings[*]."
            }
          >
            <Input
              id="mapping-item-selector"
              value={itemSelector}
              onChange={(e) => setItemSelector(e.target.value)}
              placeholder={
                format === "xml" ? "Issues/Issue" : "results[*].issues[*]"
              }
            />
          </FormField>

          {/* ── Field rows ── */}
          <section className="mt-6">
            <header className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Fields</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setFieldRows((rows) => [
                    ...rows,
                    {
                      field: (fieldsAvailable[0] ?? "") as CanonicalField | "",
                      selector: "",
                    },
                  ])
                }
                disabled={fieldsAvailable.length === 0}
              >
                Add field
              </Button>
            </header>
            <p className="mt-1 text-xs text-muted-foreground">
              Map each canonical LintPDF field to a selector relative to the
              item. ``message`` is required; rows without it are dropped.
            </p>
            <table className="mt-3 w-full text-sm">
              <thead className="text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="py-1 w-8" aria-label="Drag handle"></th>
                  <th className="py-1 w-40">Field</th>
                  <th className="py-1">Selector</th>
                  <th className="py-1 w-16"></th>
                </tr>
              </thead>
              <tbody>
                {fieldRows.map((row, idx) => (
                  <tr
                    key={idx}
                    draggable
                    onDragStart={() => onFieldDragStart(idx)}
                    onDragOver={onFieldDragOver}
                    onDrop={() => onFieldDrop(idx)}
                    className={`border-b last:border-0 ${
                      dragFieldIndex === idx ? "opacity-50" : ""
                    }`}
                    aria-grabbed={dragFieldIndex === idx}
                  >
                    <td
                      className="py-2 pr-2 cursor-move text-muted-foreground"
                      title="Drag to reorder"
                    >
                      <span aria-hidden>☰</span>
                    </td>
                    <td className="py-2 pr-2">
                      <Select
                        value={row.field}
                        onChange={(e) =>
                          setFieldRows((rows) =>
                            rows.map((r, i) =>
                              i === idx
                                ? {
                                    ...r,
                                    field: e.target.value as
                                      | CanonicalField
                                      | "",
                                  }
                                : r,
                            ),
                          )
                        }
                      >
                        <option value="">Select…</option>
                        {CANONICAL_FIELDS.map((f) => (
                          <option
                            key={f}
                            value={f}
                            disabled={
                              f !== row.field &&
                              fieldRows.some((x) => x.field === f)
                            }
                          >
                            {f}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td className="py-2 pr-2">
                      <Input
                        value={row.selector}
                        onChange={(e) =>
                          setFieldRows((rows) =>
                            rows.map((r, i) =>
                              i === idx
                                ? { ...r, selector: e.target.value }
                                : r,
                            ),
                          )
                        }
                        placeholder={
                          format === "xml"
                            ? "@level  or  Description  or  Geometry/Box"
                            : "sev  or  loc.page  or  loc.box"
                        }
                      />
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setFieldRows((rows) =>
                            rows.filter((_, i) => i !== idx),
                          )
                        }
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* ── Severity map ── */}
          <section className="mt-6">
            <header className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Severity map</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setSeverityRows((rows) => [...rows, { raw: "", mapped: "" }])
                }
              >
                Add row
              </Button>
            </header>
            <p className="mt-1 text-xs text-muted-foreground">
              Translate your tool’s severity words into LintPDF’s canonical
              error / warning / advisory. Unmapped values fall through to our
              fuzzy normaliser.
            </p>
            <table className="mt-3 w-full text-sm">
              <thead className="text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="py-1 w-1/2">Raw value</th>
                  <th className="py-1">Mapped to</th>
                  <th className="py-1 w-16"></th>
                </tr>
              </thead>
              <tbody>
                {severityRows.map((row, idx) => (
                  <tr key={idx} className="border-b last:border-0">
                    <td className="py-2 pr-2">
                      <Input
                        value={row.raw}
                        onChange={(e) =>
                          setSeverityRows((rows) =>
                            rows.map((r, i) =>
                              i === idx ? { ...r, raw: e.target.value } : r,
                            ),
                          )
                        }
                        placeholder="HIGH"
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <Select
                        value={row.mapped}
                        onChange={(e) =>
                          setSeverityRows((rows) =>
                            rows.map((r, i) =>
                              i === idx
                                ? {
                                    ...r,
                                    mapped: e.target
                                      .value as SeverityRow["mapped"],
                                  }
                                : r,
                            ),
                          )
                        }
                      >
                        <option value="">Select…</option>
                        <option value="error">error</option>
                        <option value="warning">warning</option>
                        <option value="advisory">advisory</option>
                      </Select>
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setSeverityRows((rows) =>
                            rows.filter((_, i) => i !== idx),
                          )
                        }
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <FormField
              label="Default severity"
              htmlFor="mapping-default-severity"
            >
              <Select
                id="mapping-default-severity"
                value={defaultSeverity}
                onChange={(e) => setDefaultSeverity(e.target.value)}
              >
                <option value="error">error</option>
                <option value="warning">warning</option>
                <option value="advisory">advisory</option>
              </Select>
            </FormField>
            <FormField
              label="Source tool label"
              htmlFor="mapping-source-tool"
              description="Shown on reports; e.g. 'Acme Preflight 2.1'"
            >
              <Input
                id="mapping-source-tool"
                value={sourceTool}
                onChange={(e) => setSourceTool(e.target.value)}
              />
            </FormField>
          </div>

          {/* ── Sample payload + preview ── */}
          <div
            ref={payloadRef}
            onDragOver={onPayloadDragOver}
            onDragLeave={onPayloadDragLeave}
            onDrop={onPayloadDrop}
            className={`relative mt-6 rounded transition ${
              isDropping
                ? "ring-2 ring-primary ring-offset-2 ring-offset-background"
                : ""
            }`}
          >
            <FormField
              label="Sample payload"
              htmlFor="mapping-sample-payload"
              description="Paste a real report (no PDF — just the XML/JSON), or drop a .xml / .json file here. We’ll use this to preview mapping output without running a full job."
            >
              <textarea
                id="mapping-sample-payload"
                value={samplePayload}
                onChange={(e) => setSamplePayload(e.target.value)}
                rows={8}
                className="w-full rounded border bg-background p-2 font-mono text-xs"
                placeholder={
                  format === "xml"
                    ? "<PreflightLog>…</PreflightLog>"
                    : "{ \"results\": [ … ] }"
                }
              />
            </FormField>
            {isDropping ? (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded bg-primary/10 text-sm font-medium text-primary">
                Drop XML or JSON sample to load
              </div>
            ) : null}
          </div>

          <div className="mt-2 flex items-center gap-3">
            <FormField label="Active" htmlFor="mapping-is-active">
              <input
                id="mapping-is-active"
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
              />
            </FormField>
          </div>

          {preview ? (
            <div
              className={`mt-4 rounded border p-3 text-sm ${
                preview.ok
                  ? "border-emerald-400/40 bg-emerald-400/5"
                  : "border-destructive/40 bg-destructive/5 text-destructive"
              }`}
            >
              {preview.ok ? (
                <>
                  <div className="font-medium">
                    {preview.findings_count} finding
                    {preview.findings_count === 1 ? "" : "s"} extracted
                  </div>
                  {preview.sample_findings.length > 0 ? (
                    <ul className="mt-2 space-y-1 text-xs">
                      {preview.sample_findings.map((f, i) => (
                        <li key={i}>
                          <span className="uppercase">[{f.severity}]</span>{" "}
                          p{f.page_num} — {f.message}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </>
              ) : (
                <>
                  <div className="font-medium">Preview failed</div>
                  <div className="mt-1 text-xs">{preview.error}</div>
                </>
              )}
            </div>
          ) : null}

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setShowForm(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              variant="outline"
              onClick={runPreview}
              disabled={previewing || !editingId}
              title={
                editingId
                  ? undefined
                  : "Save the mapping first, then preview reflects unsaved edits"
              }
            >
              {previewing ? "Previewing…" : "Preview"}
            </Button>
            <Button onClick={save} disabled={saving}>
              {saving ? "Saving…" : editingId ? "Save changes" : "Create"}
            </Button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
