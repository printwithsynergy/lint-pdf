import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiBrandingSection() {
  return (
    <section className="mb-12">
      <h3 id="branding" className="text-xl font-bold text-slate-900 mb-3">
        Branding &amp; custom domains
      </h3>
      <p className="text-slate-600 mb-4">
        LintPDF resolves branding in three modes: <code className="bg-slate-100 px-1 rounded">anonymous</code> (no brand
        at all), <code className="bg-slate-100 px-1 rounded">lintpdf</code> (our default branding), or a
        specific tenant <code className="bg-slate-100 px-1 rounded">BrandProfile</code> by UUID.
        The submit form <code className="bg-slate-100 px-1 rounded">brand</code> field overrides the
        tenant default on a per-request basis.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/tenant/branding-defaults"
        description="Read the tenant's default brand resolution."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenant/branding-defaults \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "mode": "profile",
  "unbranded_by_default": false,
  "default_brand_profile_id": "2f7c1e8a-1b4d-4e1a-9a2b-9c8d7e6f5a4b"
}`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/tenant/branding-defaults"
        description="Set the tenant default. Requires the branding:manage permission. Anonymous mode strips all branding + sanitises PDF metadata by default (broker → distributor use case)."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenant/branding-defaults \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "mode": "anonymous" }'`}
        response={`{
  "mode": "anonymous",
  "unbranded_by_default": true,
  "default_brand_profile_id": null
}`}
      />

      <FieldTable
        rows={[
          { name: "mode", type: '"anonymous" | "profile" | "lintpdf"', required: true, description: "How brand resolves when a job/report does not override." },
          { name: "brand_profile_id", type: "uuid | null", description: "Required when mode=profile. Must reference a BrandProfile in the current tenant. Returns 404 if the profile doesn't exist." },
        ]}
      />
      <p className="text-slate-600 text-sm mt-2">
        The response also carries <code className="bg-slate-100 px-1 rounded">unbranded_by_default</code> (mirrors
        the tenant flag) and <code className="bg-slate-100 px-1 rounded">default_brand_profile_id</code> (the
        currently-pinned profile, or null).
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Brand profiles</h4>
      <Endpoint
        method="GET"
        path="/api/v1/tenants/{tenant_id}/brand-profiles"
        description="List every BrandProfile owned by the tenant."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "profiles": [ { "id": "...", "name": "Acme Print", "profile_type": "custom", ... } ] }`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/brand-profiles"
        description="Create a new BrandProfile. Scale/Enterprise entitlement."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Acme Print",
    "profile_type": "custom",
    "brand_name": "Acme Print",
    "logo_url": "https://acmeprint.com/logo.svg",
    "primary_color": "#1a365d",
    "accent_color": "#2563eb",
    "footer_text": "Preflight by Acme Print",
    "hide_footer": false
  }'`}
        response={`{
  "id": "9f8e7d6c-5b4a-4321-9876-543210fedcba",
  "name": "Acme Print",
  "profile_type": "custom",
  "brand_name": "Acme Print",
  "logo_url": "https://acmeprint.com/logo.svg",
  "primary_color": "#1a365d",
  "accent_color": "#2563eb",
  "footer_text": "Preflight by Acme Print",
  "hide_footer": false,
  "is_default": false,
  "created_at": "2026-04-12T10:30:00Z",
  "updated_at": "2026-04-12T10:30:00Z"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-2 mb-2">BrandProfile fields</h4>
      <FieldTable
        rows={[
          { name: "name", type: "string", required: true, description: "Internal label (1–255 chars)." },
          { name: "profile_type", type: '"custom" | "lintpdf" | "none"', default: '"custom"', description: "custom uses this profile's brand fields; lintpdf falls back to LintPDF defaults; none produces a neutral/blind output." },
          { name: "brand_name", type: "string | null", description: "Display name on reports and the viewer chrome (max 255)." },
          { name: "logo_url", type: "string | null", description: "Absolute HTTPS URL to the logo (max 2048)." },
          { name: "primary_color", type: "string | null", description: "Hex colour, #RRGGBB (max 7)." },
          { name: "accent_color", type: "string | null", description: "Hex colour, #RRGGBB (max 7)." },
          { name: "footer_text", type: "string | null", description: "Footer copy baked into reports (max 500)." },
          { name: "hide_footer", type: "boolean", default: "false", description: "Suppress the footer entirely." },
        ]}
      />

      <Endpoint
        method="GET"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}"
        description="Retrieve a single BrandProfile."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles/PROFILE \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "id": "...", "name": "Acme Print", ... }`}
      />

      <Endpoint
        method="PUT"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}"
        description="Replace a BrandProfile. All update fields optional; omitted fields keep their current value."
        auth
        request={`curl -X PUT https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles/PROFILE \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "primary_color": "#0f172a", "hide_footer": true }'`}
        response={`{ "id": "...", "primary_color": "#0f172a", "hide_footer": true, ... }`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}"
        description="Delete a BrandProfile. Jobs that used this profile historically retain their rendered branding. Returns 204."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles/PROFILE \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 204 No Content`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/logo"
        description="Upload a logo file (PNG, JPEG, or SVG). Stored on the CDN and referenced by logo_url."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles/PROFILE/logo \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F file=@logo.png`}
        response={`{ "id": "...", "logo_url": "https://cdn.lintpdf.com/brand-logos/...", ... }`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/tenants/{tenant_id}/default-brand-profile"
        description="Convenience endpoint to pin a tenant default BrandProfile. Pass null to clear."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenants/TENANT/default-brand-profile \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "brand_profile_id": "9f8e7d6c-..." }'`}
        response={`{ "id": "9f8e7d6c-...", "is_default": true, ... }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Custom report domain</h4>
      <p className="text-slate-600 mb-3">
        White-label reports on <code className="bg-slate-100 px-1 rounded">reports.yourbrand.com</code>. Each
        domain gets a unique <code className="bg-slate-100 px-1 rounded">dns_target</code> in the form
        <code className="bg-slate-100 px-1 rounded">{`{slug}-reports.custom.lintpdf.com`}</code> — customers
        CNAME to <em>that</em> exact target (not the shared LintPDF hostname). Scale/Enterprise only — the
        engine returns 403 on lower tiers.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/tenants/{tenant_id}/custom-domain"
        description="Read the current state of the tenant's report-domain claim."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenants/TENANT/custom-domain \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "tenant_id": "...",
  "domain": "reports.acmeprint.com",
  "verified": false,
  "requested_at": "2026-04-12T10:30:00Z",
  "plan_allows_whitelabel": true,
  "dns_target": "7c9a4b0e-custom.lintpdf.com"
}`}
      />
      <Endpoint
        method="PATCH"
        path="/api/v1/tenants/{tenant_id}/custom-domain"
        description="Register or clear the tenant's report domain. Setting a new domain resets verified to false. 409 on duplicate claim, 422 on blocklisted hostnames."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenants/TENANT/custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "domain": "reports.acmeprint.com" }'`}
        response={`{
  "tenant_id": "...",
  "domain": "reports.acmeprint.com",
  "verified": false,
  "requested_at": "2026-04-12T10:30:00Z",
  "plan_allows_whitelabel": true,
  "dns_target": "7c9a4b0e-custom.lintpdf.com"
}`}
      />
      <p className="text-slate-600 text-sm mt-2">
        To clear the domain, PATCH with <code className="bg-slate-100 px-1 rounded">{`{ "domain": null }`}</code>.
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Per-BrandProfile domain</h4>
      <p className="text-slate-600 mb-3">
        Agencies serving multiple end-clients can point each BrandProfile at
        its own subdomain.
      </p>
      <Endpoint
        method="PATCH"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/custom-domain"
        description="Attach (or clear) a custom domain for a single BrandProfile."
        auth
        request={`curl -X PATCH \\
  https://api.lintpdf.com/api/v1/tenants/TENANT/brand-profiles/PROFILE/custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "domain": "proofs.end-brand.com" }'`}
        response={`{ "id": "...", "custom_domain": "proofs.end-brand.com", "custom_domain_verified": false, ... }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">App / viewer domain</h4>
      <Endpoint
        method="GET"
        path="/api/v1/tenants/{tenant_id}/app-custom-domain"
        description="Read the current dashboard/viewer domain claim."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenants/TENANT/app-custom-domain \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "tenant_id": "...",
  "domain": "app.acmeprint.com",
  "verified": false,
  "requested_at": "2026-04-12T10:30:00Z",
  "plan_allows_whitelabel": true
}`}
      />
      <Endpoint
        method="PATCH"
        path="/api/v1/tenants/{tenant_id}/app-custom-domain"
        description="Register or clear the dashboard/viewer app domain. Separate from the reports domain."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenants/TENANT/app-custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "domain": "app.acmeprint.com" }'`}
        response={`{
  "tenant_id": "...",
  "domain": "app.acmeprint.com",
  "verified": false,
  "requested_at": "2026-04-12T10:30:00Z",
  "plan_allows_whitelabel": true
}`}
      />
    </section>
  );
}
