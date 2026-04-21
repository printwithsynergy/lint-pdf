/**
 * Admin docs navigation data.
 *
 * Source of truth for the sidebar, landing-page group cards, and
 * canonical page ordering. Every entry here must map to an `.md` file
 * under ``packages/app/content/docs-admin/``.
 */

export interface AdminDocItem {
  /** Slug relative to content/docs-admin/, e.g. ``panels/webhooks``. */
  slug: string;
  label: string;
  description?: string;
}

export interface AdminDocSection {
  /** URL segment for the group index at /dashboard/admin/docs/<key>. */
  key: string;
  heading: string;
  blurb: string;
  items: AdminDocItem[];
}

export const adminDocSections: AdminDocSection[] = [
  {
    key: "overview",
    heading: "Admin overview",
    blurb: "How the admin surface is organised and which docs live where.",
    items: [
      { slug: "overview", label: "Admin docs home" },
      { slug: "admin-api", label: "Admin APIs + Swagger" },
    ],
  },
  {
    key: "panels",
    heading: "Admin panels",
    blurb:
      "One page per /dashboard/admin/* route — what it does, who can use it, the backing APIs.",
    items: [
      { slug: "panels/overview", label: "Admin dashboard overview" },
      { slug: "panels/appearance", label: "Appearance" },
      { slug: "panels/audit", label: "Audit (preflight history)" },
      { slug: "panels/billing", label: "Billing" },
      { slug: "panels/branding", label: "Branding" },
      { slug: "panels/custom-domains", label: "Custom domains" },
      { slug: "panels/health", label: "System health" },
      { slug: "panels/jobs", label: "Jobs" },
      { slug: "panels/swagger", label: "Swagger (full API)" },
      { slug: "panels/tenants", label: "Tenants" },
      { slug: "panels/trials", label: "Trial submissions" },
      { slug: "panels/warming", label: "Tile warming" },
      { slug: "panels/webhooks", label: "Webhook DLQ" },
    ],
  },
  {
    key: "runbooks",
    heading: "Ops runbooks",
    blurb: "Step-by-step procedures for common operator tasks.",
    items: [
      {
        slug: "runbooks/webhook-dlq-replay",
        label: "Replay a dead webhook delivery",
      },
      {
        slug: "runbooks/pws-onboarding",
        label: "Seed the Print-With-Synergy demo tenant",
      },
      {
        slug: "runbooks/run-preflight-script",
        label: "Run the preflight script end-to-end",
      },
    ],
  },
];

/** Flat list of every admin-docs slug across all groups. */
export const allAdminDocSlugs: string[] = adminDocSections.flatMap((s) =>
  s.items.map((i) => i.slug),
);

/** Map of group key → section. */
export const adminDocSectionsByKey: Record<string, AdminDocSection> =
  Object.fromEntries(adminDocSections.map((s) => [s.key, s]));
