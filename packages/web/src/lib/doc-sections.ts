/**
 * Docs navigation data.
 *
 * Single source of truth for both the top-level `/docs` landing page
 * and the inner `[slug]` page's sidebar + prev/next nav. Every entry
 * here must correspond to either an `.md` file in `src/content/docs/`
 * or a JSX page registered in `app/docs/[slug]/page.tsx`.
 *
 * The `key` on each section is the URL slug for the auto-generated
 * group-index page at `/docs/<key>` (e.g. `/docs/preflight` lists all
 * entries in the Preflights group). Group keys are picked so they
 * don't collide with existing content slugs.
 */

export interface DocItem {
  /** Content slug. Matches the `.md` filename (no extension) or JSX key. */
  slug: string;
  /** Short label shown in sidebar + cards. */
  label: string;
  /** One-line description shown on the group-index page. Optional. */
  description?: string;
}

export interface DocSection {
  /** URL key for the group-index page at `/docs/<key>`. */
  key: string;
  /** Display heading shown on the landing page + sidebar. */
  heading: string;
  /** One-sentence description shown on the landing page card. */
  blurb: string;
  items: DocItem[];
}

export const docSections: DocSection[] = [
  {
    key: "start",
    heading: "Start here",
    blurb:
      "Sign up, authenticate, and run your first preflight in under two minutes.",
    items: [
      {
        slug: "getting-started",
        label: "Getting started",
        description: "Product overview, accounts, and first-run tour.",
      },
      {
        slug: "authentication",
        label: "Authentication",
        description: "Bearer API keys, rate limits, and auth failure modes.",
      },
      {
        slug: "desktop-app",
        label: "Desktop app",
        description: "Tauri-based GUI for drag-and-drop preflighting.",
      },
    ],
  },
  {
    key: "preflight",
    heading: "Preflights",
    blurb:
      "How LintPDF runs the checks: modes, rulesets, profiles, and the job lifecycle.",
    items: [
      {
        slug: "preflight-modes",
        label: "Preflight modes",
        description:
          "Detect vs. interpret: when the engine stops vs. drills deeper.",
      },
      {
        slug: "rulesets",
        label: "Rulesets",
        description: "How to pick, clone, and author custom rulesets.",
      },
      {
        slug: "checks",
        label: "Checks reference",
        description: "500+ individual checks, grouped by category.",
      },
      {
        slug: "job-state",
        label: "Universal job state",
        description: "The one JSON envelope every job surfaces.",
      },
      {
        slug: "report-formats",
        label: "Report formats",
        description: "JSON, HTML, PDF — what each one is for.",
      },
    ],
  },
  {
    key: "ai",
    heading: "AI preflights",
    blurb:
      "Brand compliance, regulatory labelling, spell-check, and barcode analysis — all on top of detection.",
    items: [
      {
        slug: "ai/overview",
        label: "AI overview",
        description:
          "Enable, configure, submit — the full turn-on walkthrough.",
      },
      {
        slug: "ai-presets",
        label: "Presets",
        description: "Curated inspection bundles for common use cases.",
      },
      {
        slug: "ai-credits",
        label: "Credits",
        description: "How AI usage is metered and priced.",
      },
      { slug: "ai-monitoring", label: "Usage monitoring" },
      { slug: "ai-brand-config", label: "Brand config" },
      { slug: "ai-findings", label: "Reading findings" },
      { slug: "ai-regulatory", label: "Regulatory compliance" },
      { slug: "ai-preflight-profiles", label: "Preflight profiles" },
      { slug: "ai-api", label: "AI API reference" },
      { slug: "ai-inspections", label: "Inspections reference" },
      { slug: "ai-examples", label: "Code examples" },
      {
        slug: "ai/troubleshooting",
        label: "Troubleshooting",
        description: "FAQ + full error-code reference.",
      },
      {
        slug: "ai-in-rulesets",
        label: "AI in rulesets",
        description:
          "Use AI presets, add AI categories to custom rulesets, or override per-request.",
      },
    ],
  },
  {
    key: "imports",
    heading: "Imports & external reports",
    blurb:
      "Hand LintPDF a PitStop, callas, or Acrobat report and it becomes a fully branded LintPDF preflight.",
    items: [
      {
        slug: "external-imports",
        label: "External imports overview",
        description:
          "Send us someone else's report; get back yours — branded, searchable, shareable.",
      },
      {
        slug: "import-schema",
        label: "LintPDF native import schema",
        description: "Canonical JSON shape for custom upstream tooling.",
      },
      {
        slug: "custom-mappings",
        label: "Custom import mappings",
        description: "Teach the engine how to parse your vendor's XML/JSON.",
      },
      {
        slug: "imports/vendors",
        label: "Importing from PitStop, callas & Acrobat",
        description: "Flow + field mapping for all three vendors, in one place.",
      },
      {
        slug: "viewer-only-mode",
        label: "Viewer-only submissions",
        description: "Skip the preflight; just open a PDF in the viewer.",
      },
      {
        slug: "viewer-capabilities",
        label: "Viewer capabilities",
        description: "Separations, TAC, fonts — what the viewer can show.",
      },
    ],
  },
  {
    key: "branding",
    heading: "Branding & sharing",
    blurb:
      "White-label reports with your domain, logo, and colours; fine-grained share-link controls.",
    items: [
      {
        slug: "branding-and-anonymous",
        label: "Branded, LintPDF, and anonymous",
        description: "Three report-branding modes and when to use each.",
      },
      {
        slug: "share-links",
        label: "Share links",
        description: "Expiring tokens, viewer-only vs. download, access logs.",
      },
      {
        slug: "custom-domains",
        label: "Custom domains",
        description: "reports.yourcompany.com + app.yourcompany.com.",
      },
    ],
  },
  {
    key: "viewer",
    heading: "Viewer & workflow",
    blurb:
      "Compare files, collect verdicts, and embed branded submission endpoints.",
    items: [
      { slug: "viewer-comparison", label: "File comparison" },
      { slug: "viewer-verdict", label: "Approval verdicts" },
      { slug: "vanity-endpoints", label: "Vanity submission endpoints" },
    ],
  },
  {
    key: "color",
    heading: "Color",
    blurb:
      "Color management, quality scoring, and conformance to PDF/X + ECG/EPM standards.",
    items: [
      { slug: "color-management", label: "Color management" },
      {
        slug: "color-quality-score",
        label: "Color quality score",
        description: "Single-number summary of a PDF's color readiness.",
      },
      {
        slug: "color/standards",
        label: "Standards & conformance",
        description:
          "PDF/X + G7 + ISO 12647, ECG readiness, HP Indigo EPM — consolidated.",
      },
    ],
  },
  {
    key: "integrations",
    heading: "Integrations",
    blurb:
      "Drop LintPDF into Enfocus Switch, Esko Automation Engine, Zapier, or a hot folder — no code required.",
    items: [
      { slug: "integrations-overview", label: "Overview" },
      { slug: "integrations-enfocus-switch", label: "Enfocus Switch" },
      {
        slug: "integrations-esko-ae",
        label: "Esko Automation Engine",
      },
      { slug: "integrations-hybrid-cloudflow", label: "Hybrid CLOUDFLOW" },
      { slug: "integrations-label-traxx", label: "Label Traxx" },
      { slug: "integrations-cerm", label: "CERM" },
      { slug: "integrations-efi-pace", label: "EFI Pace" },
      { slug: "integrations-tharstern", label: "Tharstern" },
      { slug: "integrations-printvis", label: "PrintVis" },
      {
        slug: "integrations-zapier-make-n8n",
        label: "Zapier, Make & n8n",
      },
      {
        slug: "integrations-hot-folder",
        label: "Hot folder (CLI & Desktop)",
      },
    ],
  },
  {
    key: "api",
    heading: "Full API reference",
    blurb:
      "OpenAPI, Postman, webhooks, SDKs — everything a developer needs to hit the engine directly.",
    items: [
      {
        slug: "api-reference",
        label: "API reference",
        description: "Interactive reference for every tenant-facing route.",
      },
      {
        slug: "postman",
        label: "Postman collection",
        description: "Download-and-go Postman JSON for both tenant + admin.",
      },
      {
        slug: "webhooks",
        label: "Webhooks",
        description: "Register endpoints, verify HMAC, replay dead letters.",
      },
      {
        slug: "sdks",
        label: "SDKs",
        description: "Official client libraries for Python, Node, Ruby, Go.",
      },
    ],
  },
  {
    key: "panels",
    heading: "Tenant dashboard",
    blurb:
      "Every screen in the LintPDF dashboard — what it does, who can use it, and which API backs it.",
    items: [
      {
        slug: "panels/overview",
        label: "Dashboard overview",
        description: "The /dashboard landing page at a glance.",
      },
      {
        slug: "panels/preflight",
        label: "Preflight",
        description: "Drag-and-drop single-file preflight.",
      },
      {
        slug: "panels/reports",
        label: "Reports",
        description: "Search, filter, and re-run every past job.",
      },
      {
        slug: "panels/rulesets",
        label: "Rulesets",
        description: "Pick or clone a preflight profile.",
      },
      {
        slug: "panels/profile",
        label: "Brand profile",
        description: "Logo, colours, custom domain.",
      },
      {
        slug: "panels/endpoints",
        label: "Custom endpoints",
        description: "Vanity submission URLs scoped to a profile + brand.",
      },
      {
        slug: "panels/approvals",
        label: "Approvals",
        description: "Review chains with audit-trail PDFs.",
      },
      {
        slug: "panels/api-keys",
        label: "API keys",
        description: "Mint, rotate, and revoke Bearer tokens.",
      },
      {
        slug: "panels/api-reference",
        label: "API reference (in-app)",
        description: "Interactive Swagger inside the dashboard.",
      },
      {
        slug: "panels/webhooks",
        label: "Webhooks",
        description: "Register endpoints, inspect deliveries, replay dead letters.",
      },
      {
        slug: "panels/billing",
        label: "Billing",
        description: "Plan + invoices + payment method.",
      },
      {
        slug: "panels/usage",
        label: "Usage",
        description: "Consumption charts for jobs, AI credits, file packs.",
      },
      {
        slug: "panels/team",
        label: "Team",
        description: "Invite, promote, demote, remove teammates.",
      },
      {
        slug: "panels/account",
        label: "Account",
        description: "Personal profile, password, MFA, sessions.",
      },
      {
        slug: "panels/downloads",
        label: "Downloads",
        description: "Desktop app, CLI, SDK binaries.",
      },
      {
        slug: "panels/waitlist",
        label: "Waitlist",
        description: "Pre-launch feature sign-ups.",
      },
    ],
  },
  {
    key: "reference",
    heading: "Reference",
    blurb: "Glossary and canonical definitions.",
    items: [
      {
        slug: "glossary",
        label: "Glossary",
        description: "LintPDF terminology in one place.",
      },
    ],
  },
];

/** Flat list of every slug across all groups. Used by prev/next nav. */
export const allDocSlugs = docSections.flatMap((s) =>
  s.items.map((i) => i.slug),
);

/** Map of group key → section, for O(1) lookup in route handlers. */
export const docSectionsByKey: Record<string, DocSection> = Object.fromEntries(
  docSections.map((s) => [s.key, s]),
);

/** Reverse map: slug → group key. Used to render "part of <group>" context. */
export const docGroupBySlug: Record<string, string> = Object.fromEntries(
  docSections.flatMap((s) => s.items.map((i) => [i.slug, s.key])),
);
