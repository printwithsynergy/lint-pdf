import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";

export default function AiApiPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-4">
        AI API Reference
      </h2>
      <p className="text-slate-500 text-sm mb-8">
        All AI endpoints require a valid API Key and AI features enabled on your
        account.
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/submit"
        description="Submit a file with AI inspections. Include ai_preset or ai_categories alongside your standard Submit parameters."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@label.pdf \\
  -F ruleset=packaging \\
  -F ai_preset=fda-food

# Or specify categories directly:
curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@label.pdf \\
  -F ruleset=packaging \\
  -F ai_categories=barcode,regulatory_fda,content_quality`}
        response={`{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "ruleset": "packaging",
  "ai_preset": "fda-food",
  "ai_inspections_requested": 12,
  "file_name": "label.pdf",
  "created_at": "2026-03-16T10:30:00Z"
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/ai/credits"
        description="Retrieve your current AI credit balance, billing mode, and consumption statistics."
        auth
        request={`curl https://api.lintpdf.com/api/v1/ai/credits \\
  -H "Authorization: Bearer lpdf_..."`}
        response={`{
  "balance": 4250,
  "billing_mode": "package",
  "auto_topup": false,
  "consumed_this_month": 750,
  "consumed_total": 3250
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/ai/credits/topup"
        description="Purchase a credit package. Available packages: starter (1,000), growth (5,000), scale (25,000)."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/ai/credits/topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{"package": "starter"}'`}
        response={`{
  "balance": 5250,
  "package_purchased": "starter",
  "credits_added": 1000,
  "amount_charged": "$50.00"
}`}
      />

      <Endpoint
        method="PUT"
        path="/api/v1/ai/credits/auto-topup"
        description="Configure automatic credit top-up. When balance drops below threshold, the specified package is purchased automatically."
        auth
        request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/credits/auto-topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }'`}
        response={`{
  "auto_topup": {
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/ai/presets"
        description="List all available AI presets with their included categories and inspection counts."
        auth
        request={`curl https://api.lintpdf.com/api/v1/ai/presets \\
  -H "Authorization: Bearer lpdf_..."`}
        response={`{
  "presets": [
    {
      "id": "fda-food",
      "name": "FDA Food",
      "inspections": 12,
      "categories": ["barcode", "content_quality", "regulatory_fda"],
      "tier": "gpu"
    },
    {
      "id": "full-ai",
      "name": "Full AI Scan",
      "inspections": 33,
      "categories": ["all"],
      "tier": "gpu"
    }
  ]
}`}
      />

      <Endpoint
        method="PUT"
        path="/api/v1/ai/brand/palette"
        description="Configure your brand color palette for the ai.color.brand_palette inspection. Set approved colors and Delta E tolerance."
        auth
        request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/palette \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "colors": [
      {"hex": "#1a365d", "name": "Primary Navy"},
      {"hex": "#3b6fb5", "name": "Secondary Blue"},
      {"hex": "#e2a832", "name": "Accent Gold"}
    ],
    "tolerance": 5
  }'`}
        response={`{
  "palette": {
    "colors": [
      {"hex": "#1a365d", "name": "Primary Navy"},
      {"hex": "#3b6fb5", "name": "Secondary Blue"},
      {"hex": "#e2a832", "name": "Accent Gold"}
    ],
    "tolerance": 5,
    "updated_at": "2026-03-16T10:30:00Z"
  }
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/ai/brand/logos"
        description="Upload a reference logo for the ai.brand.logo_match inspection. Supports PNG, SVG, PDF, EPS."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/ai/brand/logos \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@logo-horizontal.png \\
  -F name="Horizontal Logo" \\
  -F variant="horizontal"`}
        response={`{
  "logo": {
    "id": "logo_abc123",
    "name": "Horizontal Logo",
    "variant": "horizontal",
    "file_type": "image/png",
    "created_at": "2026-03-16T10:30:00Z"
  }
}`}
      />

      <Endpoint
        method="PUT"
        path="/api/v1/ai/brand/dictionary"
        description="Manage the custom dictionary for ai.content.spell_check. Use mode 'append' to add words or 'replace' to overwrite."
        auth
        request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/dictionary \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "words": ["LintPDF", "PreflightPro", "XtraShield"],
    "mode": "append"
  }'`}
        response={`{
  "dictionary": {
    "word_count": 47,
    "mode": "append",
    "words_added": 3,
    "updated_at": "2026-03-16T10:30:00Z"
  }
}`}
      />
    </>
  );
}
