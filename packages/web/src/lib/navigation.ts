/**
 * Navigation data — shared between Header and Footer.
 *
 * Mode-aware: in OSS mode (NEXT_PUBLIC_ENABLE_SAAS=false) nav strips
 * pricing/integrations/blog/changelog/docs/try-it links and surfaces
 * /engine instead. The build-time mode flag means the wrong-mode links
 * are tree-shaken from the client bundle entirely.
 */

import { isSaasMode, ossRepoIsLive, OSS_REPO_URL } from "./site-mode";

export interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

export const headerLinks: NavLink[] = isSaasMode()
  ? [
      { href: "/#features", label: "Features" },
      { href: "/integrations", label: "Integrations" },
      { href: "/pricing", label: "Pricing" },
      { href: "/docs", label: "Docs" },
      { href: "/about", label: "About" },
    ]
  : [
      { href: "/#features", label: "Features" },
      { href: "/engine", label: "Engine" },
      { href: "/about", label: "About" },
      { href: "/contact", label: "Contact" },
    ];

export interface FooterGroup {
  title: string;
  links: NavLink[];
}

const SAAS_FOOTER: FooterGroup[] = [
  {
    title: "Product",
    links: [
      { href: "/#features", label: "Features" },
      { href: "/integrations", label: "Integrations" },
      { href: "/pricing", label: "Pricing" },
      { href: "/try-it", label: "Free PDF Test" },
    ],
  },
  {
    title: "Resources",
    links: [
      // /swagger is intentionally not listed here — Docs owns the single
      // discovery surface for everything API-related, and the /docs landing
      // hero + docs-nav both link to the live Swagger UI directly.
      { href: "/docs", label: "Docs" },
      { href: "/docs/postman", label: "Postman Collection" },
      { href: "/docs/authentication", label: "Authentication" },
      { href: "/blog", label: "Blog" },
      { href: "/changelog", label: "Changelog" },
      { href: "/status", label: "Status" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      {
        href: "https://thinkneverland.com",
        label: "Think Neverland",
        external: true,
      },
      { href: "/contact", label: "Contact Us" },
    ],
  },
];

const OSS_FOOTER: FooterGroup[] = [
  {
    title: "Product",
    links: [
      { href: "/#features", label: "Features" },
      { href: "/engine", label: "Engine" },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "/status", label: "Status" },
      { href: "/compliance", label: "Compliance" },
      ...(ossRepoIsLive() && OSS_REPO_URL
        ? [{ href: OSS_REPO_URL, label: "GitHub", external: true }]
        : []),
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      {
        href: "https://thinkneverland.com",
        label: "Think Neverland",
        external: true,
      },
      { href: "/contact", label: "Contact" },
    ],
  },
];

export const footerGroups: FooterGroup[] = isSaasMode() ? SAAS_FOOTER : OSS_FOOTER;
