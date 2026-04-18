export const docSections = [
  {
    heading: "Getting Started",
    items: [
      { slug: "getting-started", label: "Getting Started" },
      { slug: "authentication", label: "Authentication" },
      { slug: "desktop-app", label: "Desktop App" },
    ],
  },
  {
    heading: "API",
    items: [
      { slug: "api-reference", label: "API Reference" },
      { slug: "job-state", label: "Universal Job State" },
      { slug: "rulesets", label: "Rulesets" },
      { slug: "checks", label: "Checks" },
      { slug: "report-formats", label: "Report Formats" },
      { slug: "webhooks", label: "Webhooks" },
      { slug: "sdks", label: "SDKs" },
      { slug: "glossary", label: "Glossary" },
    ],
  },
  {
    heading: "Preflight Modes & Imports",
    items: [
      { slug: "preflight-modes", label: "Preflight Modes" },
      { slug: "external-imports", label: "External Preflight Imports" },
      { slug: "import-schema", label: "LintPDF Native Import Schema" },
      { slug: "custom-mappings", label: "Custom Import Mappings" },
      { slug: "viewer-only-mode", label: "Viewer-Only Submissions" },
      { slug: "viewer-capabilities", label: "Viewer Capabilities" },
      { slug: "importing-from-pitstop", label: "Importing from Enfocus PitStop" },
      { slug: "importing-from-callas", label: "Importing from callas pdfToolbox" },
      { slug: "importing-from-acrobat", label: "Importing from Adobe Acrobat" },
    ],
  },
  {
    heading: "Branding & Sharing",
    items: [
      { slug: "branding-and-anonymous", label: "Branded, LintPDF, and Anonymous" },
      { slug: "share-links", label: "Share Links" },
      { slug: "custom-domains", label: "Custom Domains" },
    ],
  },
  {
    heading: "Viewer & Workflow",
    items: [
      { slug: "viewer-comparison", label: "File Comparison" },
      { slug: "viewer-verdict", label: "Approval Verdicts" },
      { slug: "vanity-endpoints", label: "Vanity Submission Endpoints" },
    ],
  },
  {
    heading: "Color",
    items: [
      { slug: "color-management", label: "Color Management" },
      { slug: "color-quality-score", label: "Color Quality Score" },
      { slug: "standards-compliance", label: "Standards Compliance" },
      { slug: "ecg-readiness", label: "ECG Readiness" },
      { slug: "epm-readiness", label: "EPM Readiness" },
    ],
  },
  {
    heading: "AI Inspections",
    items: [
      { slug: "ai-getting-started", label: "Getting Started" },
      { slug: "ai-setup", label: "Setup" },
      { slug: "ai-configuration", label: "Configuration" },
      { slug: "ai-credits", label: "Credits" },
      { slug: "ai-inspections", label: "Inspections Reference" },
      { slug: "ai-presets", label: "Presets" },
      { slug: "ai-brand-config", label: "Brand Config" },
      { slug: "ai-findings", label: "Reading Findings" },
      { slug: "ai-regulatory", label: "Regulatory Compliance" },
      { slug: "ai-monitoring", label: "Usage Monitoring" },
      { slug: "ai-preflight-profiles", label: "Preflight Profiles" },
      { slug: "ai-faq", label: "FAQ" },
      { slug: "ai-api", label: "API Reference" },
      { slug: "ai-errors", label: "Errors" },
      { slug: "ai-examples", label: "Code Examples" },
    ],
  },
  {
    heading: "Integrations",
    items: [
      { slug: "integrations-overview", label: "Overview" },
      { slug: "integrations-enfocus-switch", label: "Enfocus Switch" },
      { slug: "integrations-esko-ae", label: "Esko Automation Engine" },
      { slug: "integrations-hybrid-cloudflow", label: "Hybrid CLOUDFLOW" },
      { slug: "integrations-label-traxx", label: "Label Traxx" },
      { slug: "integrations-cerm", label: "CERM" },
      { slug: "integrations-efi-pace", label: "EFI Pace" },
      { slug: "integrations-tharstern", label: "Tharstern" },
      { slug: "integrations-printvis", label: "PrintVis" },
      { slug: "integrations-zapier-make-n8n", label: "Zapier, Make & n8n" },
      { slug: "integrations-hot-folder", label: "Hot Folder (CLI & Desktop)" },
    ],
  },
];

export const allDocSlugs = docSections.flatMap((s) =>
  s.items.map((i) => i.slug),
);
