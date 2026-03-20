/**
 * Never Grounded brand constants — single source of truth for all pages.
 */

// ── Brand Language Glossary ─────────────────────────────────
export const glossary = [
  {
    concept: "Pass status",
    term: "Clear to Sail",
    usage: "Reports, API responses, UI",
  },
  {
    concept: "Fail status",
    term: "Aground",
    usage: "Reports, API responses, UI",
  },
  { concept: "Dashboard", term: "The Bridge", usage: "Navigation, docs" },
  {
    concept: "Preflight checklist/profile",
    term: "Voyage Plan",
    usage: "Docs, API, pricing",
  },
  { concept: "Report output", term: "Captain's Log", usage: "Docs, API" },
  { concept: "Audit history", term: "Logbook", usage: "Docs, dashboard" },
  { concept: "Blocker/critical issue", term: "Reef", usage: "Reports" },
  { concept: "User role (admin)", term: "Captain", usage: "Dashboard, docs" },
  { concept: "User role (standard)", term: "Crew", usage: "Dashboard, docs" },
  {
    concept: "Notifications/webhooks",
    term: "Harbor Signals",
    usage: "Docs, settings",
  },
  { concept: "Webhook callbacks", term: "Radio", usage: "API docs" },
  { concept: "API keys", term: "Boarding Pass", usage: "Dashboard, docs" },
  {
    concept: "Individual checks",
    term: "Inspections",
    usage: "Docs, API, reports",
  },
  { concept: "Severity: critical", term: "Aground", usage: "Reports, API" },
  { concept: "Severity: warning", term: "Squall", usage: "Reports, API" },
  { concept: "Severity: info", term: "Advisory", usage: "Reports, API" },
  { concept: "White-label tenants", term: "Fleets", usage: "Pricing, docs" },
  { concept: "Tenant onboarding", term: "Fleet Registration", usage: "Docs" },
  {
    concept: "Tenant branding config",
    term: "Livery",
    usage: "Dashboard, docs",
  },
  { concept: "File submission", term: "Launch", usage: "API docs" },
  { concept: "Processing queue", term: "The Channel", usage: "Status, docs" },
  { concept: "Processing in progress", term: "Underway", usage: "Status, API" },
  { concept: "Processing complete", term: "Docked", usage: "Status, API" },
] as const;

// ── API Endpoints ───────────────────────────────────────────
export const apiEndpoints = [
  {
    method: "POST",
    path: "/api/v1/launch",
    description: "Submit a PDF for preflight",
  },
  {
    method: "GET",
    path: "/api/v1/captains-log/{id}",
    description: "Get preflight results",
  },
  {
    method: "GET",
    path: "/api/v1/captains-log/{id}/report?format=pdf|json|xml",
    description: "Download report",
  },
  {
    method: "PUT",
    path: "/api/v1/livery",
    description: "Configure white-label branding",
  },
  {
    method: "GET",
    path: "/api/v1/voyage-plans",
    description: "List available preflight profiles",
  },
  {
    method: "POST",
    path: "/api/v1/voyage-plans",
    description: "Create custom profile",
  },
] as const;

// ── Pricing Tiers ───────────────────────────────────────────
export interface PricingTier {
  name: string;
  price: string;
  period: string;
  filesPerMonth: string;
  description: string;
  features: string[];
  cta: string;
  href: string;
  highlighted: boolean;
}

export const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    filesPerMonth: "50 files / month",
    description: "Get started with basic preflight.",
    features: [
      "50 files per month",
      "Basic Voyage Plan",
      "JSON output only",
      "250+ Inspections",
      "Community support",
    ],
    cta: "Start Free",
    href: "/beta/join",
    highlighted: false,
  },
  {
    name: "Starter",
    price: "$49",
    period: "/ month",
    filesPerMonth: "500 files / month",
    description: "For small teams and freelancers.",
    features: [
      "500 files per month",
      "All Voyage Plans",
      "PDF, JSON & XML reports",
      "250+ Inspections",
      "Email support",
    ],
    cta: "Get Started",
    href: "/beta/join",
    highlighted: false,
  },
  {
    name: "Growth",
    price: "$149",
    period: "/ month",
    filesPerMonth: "5,000 files / month",
    description: "For production workflows.",
    features: [
      "5,000 files per month",
      "Custom Voyage Plans",
      "PDF, JSON & XML reports",
      "Harbor Signals (webhooks)",
      "250+ Inspections",
      "Priority support",
    ],
    cta: "Get Started",
    href: "/beta/join",
    highlighted: true,
  },
  {
    name: "Scale",
    price: "$399",
    period: "/ month",
    filesPerMonth: "25,000 files / month",
    description: "For high-volume operations.",
    features: [
      "25,000 files per month",
      "Fleet (white-label / Livery)",
      "Custom Voyage Plans",
      "Priority Channel processing",
      "Harbor Signals (webhooks)",
      "PDF, JSON & XML reports",
    ],
    cta: "Get Started",
    href: "/beta/join",
    highlighted: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    filesPerMonth: "Unlimited",
    description: "SLA, dedicated infrastructure, custom integrations.",
    features: [
      "Unlimited files",
      "Full white-label / Livery",
      "Custom Voyage Plans",
      "Dedicated infrastructure",
      "SLA & onboarding",
      "Custom integrations",
    ],
    cta: "Contact Us",
    href: "mailto:sales@thinkneverland.com",
    highlighted: false,
  },
];

// ── Feature Comparison Matrix (for pricing page) ────────────
export interface ComparisonFeature {
  name: string;
  free: string | boolean;
  starter: string | boolean;
  growth: string | boolean;
  scale: string | boolean;
  enterprise: string | boolean;
}

export const comparisonFeatures: ComparisonFeature[] = [
  {
    name: "Files per month",
    free: "50",
    starter: "500",
    growth: "5,000",
    scale: "25,000",
    enterprise: "Unlimited",
  },
  {
    name: "Inspections",
    free: "250+",
    starter: "250+",
    growth: "250+",
    scale: "250+",
    enterprise: "250+",
  },
  {
    name: "Voyage Plans",
    free: "Basic",
    starter: "All built-in",
    growth: "Custom",
    scale: "Custom",
    enterprise: "Custom",
  },
  {
    name: "Report formats",
    free: "JSON",
    starter: "PDF, JSON, XML",
    growth: "PDF, JSON, XML",
    scale: "PDF, JSON, XML",
    enterprise: "PDF, JSON, XML",
  },
  {
    name: "White-label (Livery)",
    free: false,
    starter: false,
    growth: false,
    scale: true,
    enterprise: true,
  },
  {
    name: "Harbor Signals (webhooks)",
    free: false,
    starter: false,
    growth: true,
    scale: true,
    enterprise: true,
  },
  {
    name: "Priority Channel",
    free: false,
    starter: false,
    growth: false,
    scale: true,
    enterprise: true,
  },
  {
    name: "Custom integrations",
    free: false,
    starter: false,
    growth: false,
    scale: false,
    enterprise: true,
  },
  {
    name: "SLA",
    free: false,
    starter: false,
    growth: false,
    scale: false,
    enterprise: true,
  },
  {
    name: "Dedicated infrastructure",
    free: false,
    starter: false,
    growth: false,
    scale: false,
    enterprise: true,
  },
];

// ── Competitor Comparison ────────────────────────────────────
export interface Competitor {
  name: string;
  shortName: string;
}

export type CompetitorCellValue =
  | { type: "text"; value: string }
  | { type: "boolean"; value: boolean }
  | { type: "highlight"; value: string };

export interface ComparisonDimension {
  label: string;
  tooltip?: string;
  values: Record<string, CompetitorCellValue>;
}

export const competitors: Competitor[] = [
  { name: "Never Grounded", shortName: "grounded" },
  { name: "Enfocus PitStop", shortName: "pitstop" },
  { name: "Callas pdfToolbox", shortName: "pdftoolbox" },
  { name: "pdfRest", shortName: "pdfrest" },
  { name: "ConvertAPI", shortName: "convertapi" },
];

export const comparisonDimensions: ComparisonDimension[] = [
  {
    label: "Philosophy",
    values: {
      grounded: { type: "highlight", value: "Detection-only" },
      pitstop: { type: "text", value: "Inspect + correct" },
      pdftoolbox: { type: "text", value: "Inspect + correct" },
      pdfrest: { type: "text", value: "Inspect + correct" },
      convertapi: { type: "text", value: "Correction-focused" },
    },
  },
  {
    label: "Public pricing",
    values: {
      grounded: { type: "boolean", value: true },
      pitstop: { type: "boolean", value: false },
      pdftoolbox: { type: "boolean", value: false },
      pdfrest: { type: "boolean", value: true },
      convertapi: { type: "boolean", value: true },
    },
  },
  {
    label: "Free tier",
    values: {
      grounded: { type: "highlight", value: "50 files / mo" },
      pitstop: { type: "text", value: "None" },
      pdftoolbox: { type: "text", value: "None" },
      pdfrest: { type: "text", value: "300 calls / mo" },
      convertapi: { type: "text", value: "250 (trial only)" },
    },
  },
  {
    label: "Time to first preflight",
    tooltip: "From signup to running your first file",
    values: {
      grounded: { type: "highlight", value: "~5 minutes" },
      pitstop: { type: "text", value: "30+ minutes" },
      pdftoolbox: { type: "text", value: "Days (OEM)" },
      pdfrest: { type: "text", value: "~5 minutes" },
      convertapi: { type: "text", value: "~10 minutes" },
    },
  },
  {
    label: "Inspection depth",
    values: {
      grounded: { type: "highlight", value: "250+ checks" },
      pitstop: { type: "text", value: "Advanced" },
      pdftoolbox: { type: "text", value: "Advanced" },
      pdfrest: { type: "text", value: "Basic" },
      convertapi: { type: "text", value: "Limited" },
    },
  },
  {
    label: "AI-powered inspections",
    tooltip:
      "Barcode decode, regulatory compliance, image quality, brand checks",
    values: {
      grounded: { type: "highlight", value: "33 AI checks" },
      pitstop: { type: "boolean", value: false },
      pdftoolbox: { type: "text", value: "Barcode only" },
      pdfrest: { type: "boolean", value: false },
      convertapi: { type: "boolean", value: false },
    },
  },
  {
    label: "White-label reports",
    values: {
      grounded: { type: "boolean", value: true },
      pitstop: { type: "boolean", value: false },
      pdftoolbox: { type: "text", value: "OEM only" },
      pdfrest: { type: "boolean", value: false },
      convertapi: { type: "boolean", value: false },
    },
  },
  {
    label: "API integration",
    tooltip: "Number of API calls to complete a preflight",
    values: {
      grounded: { type: "highlight", value: "2 calls" },
      pitstop: { type: "text", value: "3+ calls" },
      pdftoolbox: { type: "text", value: "3+ calls" },
      pdfrest: { type: "text", value: "2–3 calls" },
      convertapi: { type: "text", value: "2+ calls" },
    },
  },
  {
    label: "Self-service signup",
    values: {
      grounded: { type: "boolean", value: true },
      pitstop: { type: "boolean", value: false },
      pdftoolbox: { type: "boolean", value: false },
      pdfrest: { type: "boolean", value: true },
      convertapi: { type: "boolean", value: true },
    },
  },
];

// ── Pricing FAQ ─────────────────────────────────────────────
export const pricingFaq = [
  {
    question: "What counts as a file?",
    answer:
      "Each PDF, EPS, PostScript, TIFF, JPEG, PNG, or AI file submitted via the Launch endpoint counts as one file toward your monthly limit.",
  },
  {
    question: "What happens when I exceed my monthly limit?",
    answer:
      "On paid plans, additional files are billed at $0.10 per file. On the Free plan, submissions are blocked until the next billing cycle.",
  },
  {
    question: "Can I upgrade or downgrade at any time?",
    answer:
      "Yes. Plan changes take effect immediately. When upgrading, you are prorated for the remainder of your billing cycle. When downgrading, the new rate applies at your next renewal.",
  },
  {
    question: "Do you offer annual billing?",
    answer:
      "Not yet, but annual plans with a discount are on our roadmap. Contact sales@thinkneverland.com if you need annual invoicing now.",
  },
  {
    question: "What is a Voyage Plan?",
    answer:
      "A Voyage Plan is a preflight profile — a collection of Inspections and thresholds that define what Never Grounded checks for. Built-in Voyage Plans include GWG Sheetfed, GWG Digital, PDF/X-4, and Packaging. Growth plans and above can create custom Voyage Plans.",
  },
  {
    question: "What are Harbor Signals?",
    answer:
      "Harbor Signals are webhook callbacks. When a file finishes processing (Docked), Never Grounded sends a POST request to your configured endpoint with the Captain's Log results. No polling required.",
  },
  {
    question: "What is Livery (white-label)?",
    answer:
      "Livery lets you brand PDF reports with your own logo, colors, and footer text. Your customers see your brand, not ours. Available on Scale and Enterprise plans.",
  },
  {
    question: "Is there a free trial for paid plans?",
    answer:
      "The Free plan is your trial — 50 files per month with full Inspection coverage. When you need more volume or features, upgrade to a paid plan.",
  },
  {
    question: "How do I get my Boarding Pass (API key)?",
    answer:
      "Join the waitlist to get early access. Once onboarded, navigate to The Bridge and generate a Boarding Pass from the API Keys section. You can create multiple keys per account.",
  },
  {
    question: "Does Never Grounded modify my files?",
    answer:
      "Never. Never Grounded is detection-only. We inspect your files and report findings. Your originals are never touched, altered, or re-saved. Zero risk of file damage.",
  },
];

// ── Supported File Formats ──────────────────────────────────
export const inputFormats = [
  { format: "PDF", description: "All versions through 2.0" },
  {
    format: "JPEG",
    description: "Converted to PDF internally, then preflighted",
  },
  {
    format: "PNG",
    description: "Converted to PDF internally, then preflighted",
  },
  { format: "EPS", description: "Converted via Ghostscript, then preflighted" },
  {
    format: "PostScript",
    description: "Converted via Ghostscript, then preflighted",
  },
  {
    format: "TIFF",
    description: "Converted to PDF internally, then preflighted",
  },
  {
    format: "AI",
    description:
      "PDF-compatible Illustrator files — PDF stream extracted, then preflighted",
  },
];

export const outputFormats = [
  {
    format: "PDF",
    description: "White-labeled with tenant Livery (logo, colors, footer)",
  },
  { format: "JSON", description: "Structured, machine-readable" },
  { format: "XML", description: "Legacy integration support" },
];

// ── AI Feature Categories ────────────────────────────────────
export interface AIInspection {
  id: string;
  name: string;
  description: string;
  tier: "text" | "vision";
  credits: number;
}

export interface AICategory {
  id: string;
  name: string;
  description: string;
  inspections: AIInspection[];
}

export const AI_CATEGORIES: AICategory[] = [
  {
    id: "barcode",
    name: "Barcode Detection",
    description:
      "AI-powered barcode and QR code analysis beyond ISO grading — type identification, decode verification, placement, and content matching.",
    inspections: [
      {
        id: "ai.barcode.decode",
        name: "Barcode Decode",
        description: "Decode and validate barcode content using AI recognition",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.qr_validation",
        name: "QR Validation",
        description:
          "Validate QR code structure, error correction, and scannability",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.dimensions",
        name: "Barcode Dimensions",
        description:
          "Verify barcode module width, height, and quiet zones meet spec",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.pharma_serialization",
        name: "Pharma Serialization",
        description:
          "Validate pharmaceutical serialization data in 2D barcodes",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.content",
        name: "Barcode Content",
        description:
          "Validate barcode payload against expected format and check digits",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.qr_human_readable",
        name: "QR Human Readable",
        description: "Check that human-readable text matches QR code content",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.barcode.content_match",
        name: "Barcode+QR Content Match",
        description:
          "Verify barcode and QR code on same label encode matching data",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "content_quality",
    name: "Content Quality",
    description:
      "Text-level analysis for spelling, language, and duplicate detection across submitted files.",
    inspections: [
      {
        id: "ai.content_quality.spell_check",
        name: "Spell Check",
        description: "AI-powered spell checking with custom dictionary support",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.content_quality.language_detection",
        name: "Language Detection",
        description: "Identify languages present and flag unexpected content",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.content_quality.duplicate_detection",
        name: "Duplicate Detection",
        description:
          "Identify duplicate or near-duplicate submissions across account",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "file_comparison",
    name: "File Comparison",
    description:
      "Visual and structural diff between file versions to catch unintended changes.",
    inspections: [
      {
        id: "ai.file_comparison.version_diff",
        name: "Version Diff",
        description:
          "Highlight differences in text, images, and layout between revisions",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "color_compliance",
    name: "Color Compliance",
    description:
      "Brand palette enforcement and accessibility contrast validation.",
    inspections: [
      {
        id: "ai.color_compliance.brand_palette",
        name: "Brand Palette Check",
        description:
          "Validate all colors against uploaded brand palette definitions",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.color_compliance.wcag_contrast",
        name: "WCAG Contrast",
        description:
          "Check text contrast ratios against WCAG 2.1 AA/AAA thresholds",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "trend_analysis",
    name: "Trend Analysis",
    description:
      "Aggregate findings across submissions to identify recurring issues.",
    inspections: [
      {
        id: "ai.trend_analysis.submission_quality_spc",
        name: "Submission Quality SPC",
        description:
          "Statistical process control tracking of submission quality over time",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "dieline",
    name: "Dieline Detection",
    description: "Detect and validate dieline layers in packaging artwork.",
    inspections: [
      {
        id: "ai.dieline.by_name",
        name: "Dieline by Name",
        description:
          "Detect dieline layers by naming convention and validate structure",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "regulatory",
    name: "Regulatory Compliance",
    description:
      "Automated compliance validation for FDA, EU FIR, GHS/CLP, and pharmaceutical labeling requirements.",
    inspections: [
      {
        id: "ai.regulatory.fda_nutrition",
        name: "FDA Nutrition Facts",
        description:
          "21 CFR 101.9 — panel structure, nutrient ordering, font sizes, serving size formatting",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.regulatory.eu_fir_1169",
        name: "EU FIR 1169/2011",
        description:
          "x-height validation, allergen emphasis, nutritional declaration ordering, mandatory fields",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.regulatory.ghs_clp",
        name: "GHS CLP 1272/2008",
        description:
          "Pictogram detection and sizing, signal words, H/P statement validation",
        tier: "text",
        credits: 1,
      },
      {
        id: "ai.regulatory.pharma_font",
        name: "Pharma Font Compliance",
        description:
          "EU FMD and FDA font size and readability requirements for pharmaceutical packaging",
        tier: "text",
        credits: 1,
      },
    ],
  },
  {
    id: "image_analysis",
    name: "Image Analysis",
    description:
      "Computer vision for image quality assessment and content safety screening.",
    inspections: [
      {
        id: "ai.image_analysis.quality",
        name: "Image Quality",
        description:
          "Visual quality assessment — blur, noise, compression artifacts, upscaling detection",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.image_analysis.nsfw",
        name: "NSFW Detection",
        description:
          "Content safety screening for inappropriate imagery in artwork",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.image_analysis.similarity",
        name: "Image Similarity",
        description:
          "Compare images across pages or files for consistency and duplication",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "document_classification",
    name: "Document Classification",
    description:
      "Automatic document type classification and Voyage Plan suggestion.",
    inspections: [
      {
        id: "ai.document_classification.classify",
        name: "File Classification",
        description:
          "Classify document type — packaging, label, leaflet, brochure, business card",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.document_classification.auto_voyage_plan",
        name: "Auto Voyage Plan",
        description:
          "Suggest optimal Voyage Plan based on detected document characteristics",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "logo_verification",
    name: "Logo Verification",
    description:
      "Compare detected logos against brand reference files for accuracy.",
    inspections: [
      {
        id: "ai.logo_verification.detect",
        name: "Logo Detection",
        description:
          "Detect and match logos against uploaded brand reference files",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "spatial_analysis",
    name: "Spatial Analysis",
    description:
      "Visual analysis of content placement relative to trim, fold, and safety zones.",
    inspections: [
      {
        id: "ai.spatial_analysis.safe_zone",
        name: "Safe Zone Violations",
        description:
          "Verify critical content placement relative to trim, fold, and perforation zones",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "nlp",
    name: "NLP Interfaces",
    description:
      "Natural language interfaces for querying and interpreting preflight data.",
    inspections: [
      {
        id: "ai.nlp.voyage_plan",
        name: "NL Voyage Plan",
        description: "Create Voyage Plans from natural language descriptions",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.nlp.report_interpret",
        name: "NL Report Interpret",
        description:
          "Plain-English summaries and explanations of Captain's Log findings",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "text_analysis",
    name: "Text Analysis",
    description:
      "Advanced text content analysis including translation and outline detection.",
    inspections: [
      {
        id: "ai.text_analysis.multi_language",
        name: "Multi-Language Translation",
        description:
          "Detect and translate text content across multiple languages",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.text_analysis.outlines",
        name: "Text as Outlines",
        description:
          "Detect text converted to outlines that cannot be edited or searched",
        tier: "vision",
        credits: 2,
      },
    ],
  },
  {
    id: "symbol_detection",
    name: "Symbol Detection",
    description:
      "Identify and validate regulatory symbols, recycling marks, and certification logos.",
    inspections: [
      {
        id: "ai.symbol_detection.regulatory",
        name: "Regulatory Symbols",
        description:
          "Detect regulatory symbols, recycling marks, and certification logos",
        tier: "vision",
        credits: 2,
      },
      {
        id: "ai.symbol_detection.processing_steps",
        name: "Processing Steps Fallback",
        description:
          "Fallback detection for processing step indicators when primary methods fail",
        tier: "vision",
        credits: 2,
      },
    ],
  },
];

// ── AI Presets ────────────────────────────────────────────────
export interface AIPreset {
  id: string;
  name: string;
  description: string;
  categories: string[];
  estimatedCredits: string;
}

export const AI_PRESETS: AIPreset[] = [
  {
    id: "fda-food-label",
    name: "FDA Food Label",
    description:
      "21 CFR 101.9 nutrition panel validation, barcode checks, and content quality for US food packaging.",
    categories: [
      "regulatory",
      "barcode",
      "content_quality",
      "symbol_detection",
    ],
    estimatedCredits: "8-14",
  },
  {
    id: "eu-food-label",
    name: "EU Food Label",
    description:
      "Regulation 1169/2011 compliance including allergen emphasis, x-height, and nutritional declarations.",
    categories: [
      "regulatory",
      "barcode",
      "content_quality",
      "symbol_detection",
    ],
    estimatedCredits: "8-14",
  },
  {
    id: "pharma-eu",
    name: "Pharma EU",
    description:
      "EU FMD serialization, Braille placeholder, font compliance, and pharmaceutical barcode validation.",
    categories: [
      "regulatory",
      "barcode",
      "content_quality",
      "symbol_detection",
    ],
    estimatedCredits: "8-14",
  },
  {
    id: "ghs-chemical",
    name: "GHS Chemical",
    description:
      "CLP 1272/2008 pictogram detection, signal words, H/P statements, and hazard communication compliance.",
    categories: [
      "regulatory",
      "symbol_detection",
      "content_quality",
      "spatial_analysis",
    ],
    estimatedCredits: "8-12",
  },
  {
    id: "packaging-qc",
    name: "Packaging QC",
    description:
      "Barcode grading, dieline detection, safe zone validation, image quality, and content checks for general packaging.",
    categories: [
      "barcode",
      "dieline",
      "spatial_analysis",
      "image_analysis",
      "content_quality",
    ],
    estimatedCredits: "12-20",
  },
  {
    id: "brand-compliance",
    name: "Brand Compliance",
    description:
      "Logo verification, brand palette enforcement, WCAG contrast, and spell checking for brand consistency.",
    categories: [
      "logo_verification",
      "color_compliance",
      "content_quality",
      "image_analysis",
    ],
    estimatedCredits: "8-14",
  },
  {
    id: "full-ai-scan",
    name: "Full AI Scan",
    description:
      "Run all 33 AI inspections across every category. Maximum coverage for comprehensive preflight.",
    categories: [
      "barcode",
      "content_quality",
      "file_comparison",
      "color_compliance",
      "trend_analysis",
      "dieline",
      "regulatory",
      "image_analysis",
      "document_classification",
      "logo_verification",
      "spatial_analysis",
      "nlp",
      "text_analysis",
      "symbol_detection",
    ],
    estimatedCredits: "45-55",
  },
];

// ── AI Credit Packages ────────────────────────────────────────
export interface AICreditPackage {
  name: string;
  credits: number;
  price: number;
  perCredit: string;
  savings: string;
  highlighted: boolean;
}

export const AI_CREDIT_PACKAGES: AICreditPackage[] = [
  {
    name: "Starter",
    credits: 100,
    price: 10,
    perCredit: "$0.10",
    savings: "Pay-as-you-go rate",
    highlighted: false,
  },
  {
    name: "Growth",
    credits: 500,
    price: 40,
    perCredit: "$0.08",
    savings: "Save 20%",
    highlighted: false,
  },
  {
    name: "Scale",
    credits: 2000,
    price: 120,
    perCredit: "$0.06",
    savings: "Save 40%",
    highlighted: true,
  },
  {
    name: "Enterprise",
    credits: 10000,
    price: 500,
    perCredit: "$0.05",
    savings: "Save 50%",
    highlighted: false,
  },
];
