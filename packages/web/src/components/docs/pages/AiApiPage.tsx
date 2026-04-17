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
  "credit_balance": 4250,
  "billing_mode": "pay_per_use",
  "packages_active": 2,
  "package_credits_remaining": 4250,
  "monthly_spent": 12.34,
  "monthly_spending_limit": 100.0
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/ai/credits/packages"
        description="List every AI credit package granted to your tenant, including plan-monthly, purchase, and admin_grant sources."
        auth
        request={`curl https://api.lintpdf.com/api/v1/ai/credits/packages \\
  -H "Authorization: Bearer lpdf_..."`}
        response={`{
  "packages": [
    {
      "id": "b538a0a5-...",
      "kind": "credits",
      "source": "purchase",
      "credits_purchased": 2000,
      "credits_remaining": 1750,
      "price_paid": 90.00,
      "purchased_at": "2026-04-17T17:54:46Z",
      "expires_at": "2027-04-17T17:54:46Z"
    }
  ]
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/ai/credits/topup"
        description='Create a Stripe Checkout session for a credit pack. Packs: "500" ($25), "2000" ($90, 10% off), "10000" ($400, 20% off). Redirect the customer to the returned checkout_url; the engine inserts the package row only when Stripe posts checkout.session.completed to the webhook.'
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/ai/credits/topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{"pack": "500"}'`}
        response={`{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_live_...",
  "session_id": "cs_live_a1qhsQgX9HVVefrYX...",
  "pack_size": 500,
  "usd_cents": 2500
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/files/quota"
        description="Current metered file quota — monthly allotment plus any purchased file packs that are still active."
        auth
        request={`curl https://api.lintpdf.com/api/v1/files/quota \\
  -H "Authorization: Bearer lpdf_..."`}
        response={`{
  "tenant_id": "a660f3e2-...",
  "total_remaining": 3250,
  "monthly_allotment_remaining": 500,
  "purchased_remaining": 2750,
  "active_packages": 1,
  "monthly_allotment": 500
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/files/topup"
        description='Create a Stripe Checkout session for a file pack. Packs: "500" ($15), "2500" ($60, 20% off), "10000" ($200, 33% off).'
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/files/topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{"pack": "2500"}'`}
        response={`{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_live_...",
  "session_id": "cs_live_...",
  "pack_size": 2500,
  "usd_cents": 6000
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/files/packages"
        description="List every file pack granted to your tenant (tenant-scoped, same shape as credits/packages)."
        auth
        request={`curl https://api.lintpdf.com/api/v1/files/packages \\
  -H "Authorization: Bearer lpdf_..."`}
        response={`{
  "packages": [
    {
      "id": "e...",
      "kind": "files",
      "source": "plan_monthly",
      "credits_purchased": 2500,
      "credits_remaining": 2140,
      "price_paid": 0.0,
      "purchased_at": "2026-04-01T00:00:00Z",
      "expires_at": "2026-05-03T00:00:00Z"
    }
  ]
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
