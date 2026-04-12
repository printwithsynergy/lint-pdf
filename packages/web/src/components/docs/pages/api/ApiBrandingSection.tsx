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
  "default_brand_profile_id": "bp_01HXY..."
}`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/tenant/branding-defaults"
        description="Set the tenant default. Requires the branding:manage permission."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenant/branding-defaults \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "mode": "anonymous" }'`}
        response={`{ "mode": "anonymous", "default_brand_profile_id": null }`}
      />

      <FieldTable
        rows={[
          { name: "mode", type: '"anonymous" | "profile" | "lintpdf"', required: true, description: "How brand resolves when a job/report does not override." },
          { name: "default_brand_profile_id", type: "uuid | null", description: "Required when mode=profile. Must reference a BrandProfile in the current tenant." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Brand profiles</h4>
      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/brand-profiles"
        description="Create a new BrandProfile. Scale/Enterprise entitlement. Supports logo upload at .../logo."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenants/tn_01.../brand-profiles \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Acme Print",
    "primary_color": "#1a365d",
    "footer_text": "Preflight by Acme Print"
  }'`}
        response={`{ "id": "bp_01HXY...", "name": "Acme Print" }`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/tenants/{tenant_id}/default-brand-profile"
        description="Convenience endpoint to pin a tenant default BrandProfile without touching branding-defaults."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenants/tn_01.../default-brand-profile \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "brand_profile_id": "bp_01HXY..." }'`}
        response={`{ "default_brand_profile_id": "bp_01HXY..." }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Custom domains</h4>
      <p className="text-slate-600 mb-3">
        White-label reports and viewer on <code className="bg-slate-100 px-1 rounded">reports.yourbrand.com</code> and
        {" "}<code className="bg-slate-100 px-1 rounded">viewer.yourbrand.com</code>. Point a CNAME at
        {" "}<code className="bg-slate-100 px-1 rounded">reports.lintpdf.com</code> and register the hostname:
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/custom-domain"
        description="Register a custom report domain. Hostname must not collide with the tenant blocklist; 409 returned on duplicates."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenants/tn_01.../custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "hostname": "reports.acmeprint.com" }'`}
        response={`{
  "hostname": "reports.acmeprint.com",
  "verified": false,
  "cname_target": "reports.lintpdf.com"
}`}
      />

      <p className="text-slate-600 mt-4 mb-3">
        Per-BrandProfile custom domains (for reseller scenarios) and the
        dashboard app domain are configured on parallel endpoints:
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/brand-profiles/{id}/custom-domain"
        description="Attach a custom domain to a single BrandProfile. Useful for agencies servicing multiple end brands from one tenant."
        auth
        request={`curl -X POST \\
  https://api.lintpdf.com/api/v1/tenants/tn_01.../brand-profiles/bp_01.../custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "hostname": "proofs.end-brand.com" }'`}
        response={`{ "hostname": "proofs.end-brand.com", "verified": false }`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/tenants/{tenant_id}/app-custom-domain"
        description="Register a dashboard/viewer app domain (app.yourbrand.com). Separate from reports.* domains."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenants/tn_01.../app-custom-domain \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "hostname": "app.acmeprint.com" }'`}
        response={`{ "hostname": "app.acmeprint.com", "verified": false }`}
      />
    </section>
  );
}
