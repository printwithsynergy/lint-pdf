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
        description="List every page in the job with its index and rotation."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../pages \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "pages": [
    { "page_num": 1, "rotation": 0, "width_pt": 595.28, "height_pt": 841.89 }
  ]
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/tile?dpi=150"
        description="Render a single page as a PNG tile. dpi range 72–600."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../pages/1/tile?dpi=200" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output page-1.png`}
        response={`200 OK
Content-Type: image/png`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/info"
        description="Page geometry — media/crop/trim/bleed boxes plus rotation."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/d4e5f6a7-.../pages/1/info \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "media_box": [0, 0, 595.28, 841.89],
  "crop_box":  [0, 0, 595.28, 841.89],
  "trim_box":  [14.17, 14.17, 581.10, 827.72],
  "bleed_box": [0, 0, 595.28, 841.89],
  "rotation": 0
}`}
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
  "separations": [
    { "name": "Cyan", "kind": "process" },
    { "name": "Magenta", "kind": "process" },
    { "name": "Yellow", "kind": "process" },
    { "name": "Black", "kind": "process" },
    { "name": "PANTONE 185 C", "kind": "spot", "alt_rgb": [228, 0, 43] }
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
        description="Total Area Coverage heatmap. Pixels above the limit are tinted red."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/tac-heatmap?tac_limit=300" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output tac-page1.png`}
        response={`200 OK
Content-Type: image/png`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/pages/{page_num}/sample?x=200&y=300&dpi=150"
        description="Single-pixel densitometer sample. Returns RGB, hex, and TAC for the point."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../pages/1/sample?x=200&y=300" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "rgb": [12, 99, 180], "hex": "#0C63B4", "tac": 278 }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Layers, verdict, config</h4>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/layers"
        description="PDF Optional Content Groups (OCG). Not fillable after job creation."
        auth
        request={`curl https://api.lintpdf.com/api/v1/viewer/jobs/.../layers \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "layers": [ { "name": "Varnish", "visible": true } ] }`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/jobs/{job_id}/config?brand=anonymous"
        description="Effective viewer configuration. The brand query param follows the same enum as the submit field."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/jobs/.../config?brand=lintpdf" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "preflight_source": "engine",
  "data_capabilities": {
    "pages": true, "separations": true, "fonts": true, "images": true,
    "tac": true, "layers": false, "findings": true
  },
  "enable_findings_panel": true,
  "enable_separations": true,
  "enable_tac": true,
  "enable_densitometer": true,
  "toolbar_position": "top",
  "dark_mode": false,
  "branding": { "mode": "lintpdf", "logo_url": null }
}`}
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
        description="Queue an analyzer run for the named capability. Returns immediately; poll config to see it flip true."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/.../capabilities/separations \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "status": "queued", "task_id": "tsk_01HXY..." }`}
      />
      <CodeBlock>{`# Python polling pattern
import time, requests
r = requests.post(f"{BASE}/viewer/jobs/{jid}/capabilities/tac", headers=H)
while True:
    cfg = requests.get(f"{BASE}/viewer/jobs/{jid}/config", headers=H).json()
    if cfg["data_capabilities"]["tac"]:
        break
    time.sleep(1.5)`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Verdict</h4>
      <Endpoint
        method="POST"
        path="/api/v1/viewer/jobs/{job_id}/verdict"
        description="Record an approval verdict."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/.../verdict \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "status": "approved", "comments": "Proceed to print" }'`}
        response={`{ "status": "approved", "reviewer_name": "Alex Chen", "reviewed_at": "2026-04-12T15:22:11Z" }`}
      />
      <FieldTable
        rows={[
          { name: "status", type: '"approved" | "rejected" | "needs_review"', required: true, description: "Target verdict state." },
          { name: "comments", type: "string | null", description: "Free-form reviewer notes up to 4096 characters." },
          { name: "reviewer_name", type: "string", description: "Override the key-derived reviewer name on integration calls." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">File comparison</h4>
      <Endpoint
        method="POST"
        path="/api/v1/viewer/compare"
        description="Create a comparison between two complete jobs. Must have matching page counts."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/viewer/compare \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "job_id_1": "d4e5f6a7-...", "job_id_2": "a1b2c3d4-..." }'`}
        response={`{ "comparison_id": "cmp_8e7d6c5b4a3f", "page_count": 12 }`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/viewer/compare/{comparison_id}/pages/{page_num}/diff?dpi=150"
        description="RGBA diff heatmap PNG. Green=ink in job_1 only, red=ink in job_2 only, amber=color delta beyond tolerance."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/viewer/compare/cmp_.../pages/1/diff?dpi=150" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  --output diff-page1.png`}
        response={`200 OK
Content-Type: image/png`}
      />
    </section>
  );
}
