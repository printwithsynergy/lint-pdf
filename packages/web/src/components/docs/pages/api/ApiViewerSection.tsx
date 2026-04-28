import Link from "next/link";
import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiViewerSection() {
  return (
    <section className="mb-12">
      <h3 id="viewer" className="text-xl font-bold text-slate-900 mb-3">
        Viewer
      </h3>
      <p className="text-slate-600 mb-4">
        The Viewer surface lets you embed or build a PDF viewer against any
        complete job — engine, external, or minimal. Tiles, separations, TAC
        heatmaps, densitometer samples, and layer metadata are served as
        JSON/PNG from a dedicated route group.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages"
        description="List every page in the job with its geometry and rotation."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../pages \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "page_count": 1,
  "pages": [
    {
      "page_num": 1,
      "width_pts": 595.28,
      "height_pts": 841.89,
      "media_box": { "x0": 0, "y0": 0, "x1": 595.28, "y1": 841.89 },
      "crop_box":  { "x0": 0, "y0": 0, "x1": 595.28, "y1": 841.89 },
      "trim_box":  { "x0": 14.17, "y0": 14.17, "x1": 581.10, "y1": 827.72 },
      "bleed_box": null,
      "rotation": 0
    }
  ]
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/tile?dpi=150"
        description="Render a single page as a PNG tile. dpi range 36–600. Optional ocg_on / ocg_off query params render the page with specific OCG (layer) indices toggled — see the Layers section below."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../pages/1/tile?dpi=200&ocg_on=0,3&ocg_off=2" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output page-1.png`}
        response={`200 OK
Content-Type: image/png
# 422 if ocg_on/ocg_off conflict, indices are out of range, or the PDF has no OCGs.`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Separations &amp; channels</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/separations"
        description="List every ink plate (process + spot) present in the job."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../separations \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "channels": [
    { "name": "Cyan", "type": "process" },
    { "name": "Magenta", "type": "process" },
    { "name": "Yellow", "type": "process" },
    { "name": "Black", "type": "process" },
    { "name": "PANTONE 185 C", "type": "spot" }
  ]
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/channel/{name}?dpi=150"
        description="Single-channel greyscale render. name is URL-encoded (use + for spaces). Returns PNG."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/channel/PANTONE+185+C?dpi=150" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output pantone-185c-page1.png`}
        response={`200 OK
Content-Type: image/png`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">TAC heatmap &amp; densitometer</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/tac-heatmap?dpi=150&tac_limit=300"
        description="Total Area Coverage heatmap. Pixels above the limit (100–500%) are tinted red."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/tac-heatmap?tac_limit=300" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output tac-page1.png`}
        response={`200 OK
Content-Type: image/png`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/tac-heatmap/runs?dpi=150&tac_limit=300"
        description="Per-text-run mean TAC metadata for interactive tooltips. Coordinates are in PDF points with origin top-left (matching poppler pdftotext -bbox). Powers the hover readout on the TAC heatmap overlay."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/tac-heatmap/runs?tac_limit=300" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "page_num": 1,
  "dpi": 150,
  "tac_limit": 300.0,
  "runs": [
    { "x0": 102.3, "y0": 88.1, "x1": 440.7, "y1": 112.5, "mean_tac": 342.8, "limit": 300.0, "exceeds": true }
  ]
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/sample?x=200&y=300&dpi=300"
        description="Single-pixel color-picker sample. Returns RGB + hex for the point (origin lower-left, PDF points). Not a densitometer — see /densitometer below for per-channel readings."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/sample?x=200&y=300" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "x": 200, "y": 300, "rgb": [12, 99, 180], "hex": "#0c63b4", "tac": null }`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/densitometer?x=200&y=300&dpi=300&tac_limit=300"
        description="Per-channel CMYK + spot densitometer reading at the requested point. Runs Ghostscript tiffsep on the page (cached in S3 after the first call) and samples a 3x3 patch on each channel."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/densitometer?x=200&y=300" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "x": 200, "y": 300, "dpi": 300,
  "channels": [
    { "name": "Cyan", "percent": 62.3 },
    { "name": "Magenta", "percent": 18.1 },
    { "name": "Yellow", "percent": 4.7 },
    { "name": "Black", "percent": 91.5 }
  ],
  "tac": 176.6,
  "tac_limit": 300,
  "limit_exceeded": false
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Tile pre-warming progress</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/tile-warming"
        description="Progress of the background Celery task (lintpdf.viewer.warm_tiles) that pre-renders every page tile into S3 when a job completes. Poll every ~1.5s to show a readiness badge; once status=complete the frontend kicks off a browser-side prefetch pass so page clicks paint from the browser HTTP cache (<20 ms)."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/.../tile-warming \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "status": "in_progress",
  "rendered": 7,
  "total": 20,
  "dpi": 150,
  "percent": 35,
  "started_at": "2026-04-14T10:22:13Z",
  "completed_at": null,
  "error": null
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Layers</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/layers"
        description="PDF Optional Content Groups (OCG). Not fillable after ingest — if layers were absent at parse time, they stay absent."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/.../layers \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "layers": [
    { "name": "Varnish", "ocg_index": 0, "default_on": true },
    { "name": "Dieline", "ocg_index": 1, "default_on": false }
  ]
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Viewer config</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/config?brand=anonymous"
        description="Effective viewer configuration. The brand query param follows the same enum as the submit field."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../config?brand=lintpdf" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "enable_separations": true,
  "enable_tac_heatmap": true,
  "enable_annotations": true,
  "enable_measurement": true,
  "enable_comparison": true,
  "enable_layers": true,
  "enable_findings_panel": true,
  "enable_page_thumbnails": true,
  "enable_zoom": true,
  "enable_download": true,
  "enable_html_report_link": true,
  "verdict_mode": "auto",
  "default_zoom": 100,
  "default_dpi": 150,
  "default_tac_limit": 300.0,
  "viewer_logo_url": null,
  "viewer_accent_color": null,
  "toolbar_position": "top",
  "dark_mode": false,
  "brand_name": "LintPDF",
  "brand_logo_url": "https://lintpdf.com/logo.svg",
  "brand_primary_color": "#1a3a7a",
  "brand_accent_color": "#2563eb",
  "anonymous": false,
  "tenant_name": "Acme Print",
  "support_email": "support@acmeprint.com",
  "preflight_source": "engine",
  "capabilities": {
    "separations": true, "tac": true, "tac_runs": true, "tiles_warmed": true,
    "fonts": true, "images": true, "layers": false,
    "text_regions": false,
    "ai_explain": true, "epm_verdict": true
  },
  "capability_fillin_enabled": true,
  "annotations_enabled": true,
  "allowed_report_formats": ["json", "html", "pdf", "xml"]
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Viewer config fields</h4>
      <FieldTable
        rows={[
          { name: "enable_separations", type: "boolean", default: "true", description: "Show the separations / channels panel." },
          { name: "enable_tac_heatmap", type: "boolean", default: "true", description: "Show the TAC heatmap overlay toggle." },
          { name: "enable_annotations", type: "boolean", default: "true", description: "Show the annotation/markup tools." },
          { name: "enable_measurement", type: "boolean", default: "true", description: "Show the ruler / measurement tool." },
          { name: "enable_comparison", type: "boolean", default: "true", description: "Show the file-comparison entry point." },
          { name: "enable_layers", type: "boolean", default: "true", description: "Show the OCG layers panel." },
          { name: "enable_findings_panel", type: "boolean", default: "true", description: "Show the findings sidebar." },
          { name: "enable_page_thumbnails", type: "boolean", default: "true", description: "Show the page thumbnail strip." },
          { name: "enable_zoom", type: "boolean", default: "true", description: "Show zoom controls." },
          { name: "enable_download", type: "boolean", default: "true", description: "Show the download-original button." },
          { name: "enable_html_report_link", type: "boolean", default: "true", description: "Show the link to the HTML report." },
          { name: "verdict_mode", type: '"auto" | "manual" | "off"', default: '"auto"', description: "Verdict workflow: auto uses summary.passed, manual requires a reviewer action, off hides the panel." },
          { name: "default_zoom", type: "integer", default: "100", description: "Initial zoom percentage." },
          { name: "default_dpi", type: "integer", default: "150", description: "Initial tile render DPI." },
          { name: "default_tac_limit", type: "float", default: "300.0", description: "Initial TAC threshold for the heatmap." },
          { name: "viewer_logo_url", type: "string | null", description: "Optional viewer-chrome logo override." },
          { name: "viewer_accent_color", type: "string | null", description: "Optional viewer-chrome accent override." },
          { name: "toolbar_position", type: '"top" | "bottom" | "left" | "right"', default: '"top"', description: "Toolbar edge." },
          { name: "dark_mode", type: "boolean", default: "false", description: "Dark theme." },
          { name: "brand_name", type: "string | null", description: "Resolved brand name (null when anonymous)." },
          { name: "brand_logo_url", type: "string | null", description: "Resolved brand logo URL (null when anonymous)." },
          { name: "brand_primary_color", type: "string | null", description: "Resolved brand primary color (null when anonymous)." },
          { name: "brand_accent_color", type: "string | null", description: "Resolved brand accent color (null when anonymous)." },
          { name: "anonymous", type: "boolean", description: "True when all tenant + LintPDF chrome is stripped." },
          { name: "tenant_name", type: "string | null", description: "Tenant display name (null when anonymous)." },
          { name: "support_email", type: "string | null", description: "Tenant support email (null when anonymous)." },
          { name: "preflight_source", type: '"engine" | "external" | "minimal"', description: "How findings were produced. Drives the viewer's Load-button affordances." },
          { name: "capabilities", type: "Record<string, boolean>", description: "Per-capability availability map. Fillable keys: separations, tac, fonts, images, text_regions (PR 2 OCR/ML — shared OCR pass that highlights outlined captions and fold-zone text; on-demand via POST /api/v1/viewer/jobs/{id}/capabilities/text_regions, persists to Job.detected_text_regions). Non-fillable: layers (extracted at ingest), tac_runs (derived on demand, tracks the tac flag), tiles_warmed (flipped by the background warm_tiles task; see /tile-warming endpoint), ai_explain (on-call via POST /api/v1/jobs/{id}/findings/{fid}/explain — cost-cap gates with HTTP 402), epm_verdict (computed at ingest from fired LPDF_EPM_* findings; mirrored on JobResponse.epm_verdict and via GET /api/v1/jobs/{id}/epm)." },
          { name: "capability_fillin_enabled", type: "boolean", description: "Plan gate. When false the fill-in endpoint returns 403 plan_upgrade_required — render an UpgradePrompt instead of Load buttons. Viewer tier: false. Starter+: true." },
          { name: "annotations_enabled", type: "boolean", description: "Plan gate. When false the annotation toolbar must be hidden; annotation write endpoints return 403; share-link minting forces allow_annotations=false. Viewer tier: false. Starter+: true." },
          { name: "allowed_report_formats", type: "string[]", description: "Plan gate. Formats the tenant may request on POST /api/v1/jobs/{id}/reports. Empty list means report downloads are disabled (Viewer tier) — the share link is the only output. Starter+ includes json/html/pdf/xml; Scale+ adds annotated_pdf." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">On-demand capability fill-in</h4>
      <p className="text-slate-600 mb-3">
        Missing analyzer output can be filled lazily. Fillable capabilities:
        {" "}<code className="bg-slate-100 px-1 rounded">separations</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">tac</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">fonts</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">images</code>.
        {" "}<code className="bg-slate-100 px-1 rounded">layers</code> is read-only (detected at parse time).
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/viewer/jobs/{job_id}/capabilities/{capability}"
        description="Queue an analyzer run for the named capability. Returns 202; poll config to see it flip true."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/.../capabilities/separations \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "capability": "separations",
  "status": "queued",
  "task_id": "tsk_01HXY..."
}`}
      />
      <p className="text-slate-600 text-sm mt-2">
        When the capability is already populated the response comes back
        with <code className="bg-slate-100 px-1 rounded">status: &quot;already_filled&quot;</code> and
        no <code className="bg-slate-100 px-1 rounded">task_id</code>. Non-fillable capabilities return 422.
      </p>
      <CodeBlock>{`# Python polling pattern
import time, requests
r = requests.post(f"{BASE}/viewer/jobs/{jid}/capabilities/tac", headers=H)
while True:
    cfg = requests.get(f"{BASE}/viewer/jobs/{jid}/config", headers=H).json()
    if cfg["capabilities"].get("tac"):
        break
    time.sleep(1.5)`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Verdict</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/verdict"
        description="Return the current verdict state for a job."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/.../verdict \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "verdict": "pass",
  "auto_passed": true,
  "verdict_by": "reviewer@acmeprint.com",
  "verdict_at": "2026-04-12T15:22:11Z",
  "notes": null
}`}
      />
      <Endpoint
        method="POST"
        path="/api/v1/viewer/jobs/{job_id}/verdict"
        description="Record a manual pass/fail verdict. Fail requires notes."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/.../verdict \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "verdict": "fail", "notes": "Low-res image on page 4" }'`}
        response={`{
  "verdict": "fail",
  "auto_passed": false,
  "verdict_by": "reviewer@acmeprint.com",
  "verdict_at": "2026-04-12T15:22:11Z",
  "notes": "Low-res image on page 4"
}`}
      />
      <FieldTable
        rows={[
          { name: "verdict", type: '"pass" | "fail"', required: true, description: "Manual verdict. Anything else returns 422." },
          { name: "notes", type: "string | null", description: "Free-form reviewer notes. Required when verdict=fail." },
        ]}
      />
      <p className="text-slate-600 text-sm mt-2">
        <code className="bg-slate-100 px-1 rounded">auto_passed</code> reflects
        the engine&apos;s summary verdict; <code className="bg-slate-100 px-1 rounded">verdict</code> reflects
        a reviewer&apos;s manual call. A job can be auto-passed and manually failed
        at the same time — clients should render both.
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">File comparison</h4>
      <Endpoint
        method="POST"
        path="/api/v1/viewer/compare"
        description="Compare two complete jobs owned by the same tenant. Returns per-page similarity scores."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/compare \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "job_a": "d4e5f6a7-...", "job_b": "a1b2c3d4-...", "dpi": 150 }'`}
        response={`{
  "comparison_id": "cmp_8e7d6c5b4a3f",
  "page_count_a": 12,
  "page_count_b": 12,
  "pages": [
    { "page_num": 1, "ssim_score": 0.987, "diff_pixel_count": 1842, "total_pixels": 1404000 }
  ]
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/compare/{comparison_id}/pages/{page_num}/diff?dpi=150"
        description="RGBA diff heatmap PNG. Green=ink in job_a only, red=ink in job_b only, amber=color delta beyond tolerance."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/compare/cmp_.../pages/1/diff?dpi=150" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output diff-page1.png`}
        response={`200 OK
Content-Type: image/png`}
      />

      <h4 className="font-semibold text-slate-900 mt-8 mb-2">Annotations + comments</h4>
      <p className="text-slate-600 mb-3">
        <code className="bg-slate-100 px-1 rounded">GET /api/v1/viewer/jobs/{"{job_id}"}/annotations</code>
        {" "}returns the flat annotation list by default (back-compat).
        Pass <code className="bg-slate-100 px-1 rounded">?include=comments</code>
        {" "}to embed each annotation&apos;s full comment thread inline in one
        round trip — no N+1 fan-out of per-annotation comment fetches.
        The aggregated <Link href="/docs/job-state" className="text-blue-600 underline">GET /api/v1/jobs/{"{id}"}/state</Link>
        {" "}endpoint uses the same embedding.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/annotations?include=comments"
        description="Annotation list with each comment thread embedded inline under items[].comments."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../annotations?include=comments" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`[
  {
    "id": "...", "page_num": 1, "kind": "rect",
    "geometry": { "x": 10, "y": 10, "w": 100, "h": 50 },
    "color": "#dc2626", "text": "Fix the bleed",
    "author_email": "reviewer@example.com",
    "comments": [
      { "id": "...", "annotation_id": "...",
        "author_email": "reviewer@example.com", "body": "Will do by EOD." }
    ]
  }
]`}
      />
      <FieldTable
        rows={[
          {
            name: "include",
            type: "string",
            default: "unset",
            description:
              'Optional. Set to "comments" to embed each annotation\'s comment thread inline. Any other value returns 422. Omit the param for the legacy shape (flat AnnotationResponse list without a comments key).',
          },
        ]}
      />
      <p className="text-slate-600 text-sm mt-3">
        The same <code className="bg-slate-100 px-1 rounded">?include=comments</code>
        {" "}param works on the share-link mirror
        {" "}<code className="bg-slate-100 px-1 rounded">GET /api/v1/viewer/public/{"{token}"}/annotations?include=comments</code>
        {" "}— unauthenticated read, subject to the token&apos;s expiry.
      </p>

      <h4 className="font-semibold text-slate-900 mt-8 mb-2">
        Public share-link state digest
      </h4>
      <p className="text-slate-600 mb-3">
        Mirror of the authenticated universal-state endpoint for share
        links. Returns the same stitched digest (summary + approval chain +
        verdict + annotations + comments) minus the{" "}
        <code className="bg-slate-100 px-1 rounded">reports</code> section —
        those are scoped to the issuing tenant and shouldn&apos;t leak sibling
        tokens. See <Link className="text-blue-600 underline" href="/docs/job-state">Universal Job State</Link> for the full field reference.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/public/{token}/state"
        description="Unauthenticated state digest for a share link. Same payload shape as /api/v1/jobs/{id}/state minus reports[]. Accepts ?include=approval_chain,verdict,annotations."
        auth={false}
        request={`curl "https://api.lintpdf.com/api/v1/viewer/public/CahsfLjcly.../state?include=verdict,annotations"`}
        response={`{
  "job": { "job_id": "...", "status": "complete" },
  "summary": { "total_findings": 275, "passed": true },
  "approval_chain": { "status": "approved", "step_history": [ ... ] },
  "verdict": { "verdict": "pass", "auto_passed": true, "notes": "..." },
  "annotations": { "total": 1, "by_page": {"1": 1}, "items": [ ... ] }
}`}
      />
    </section>
  );
}
