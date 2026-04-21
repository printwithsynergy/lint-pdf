/**
 * Navigation data — shared between Header and Footer.
 */

export interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

export const headerLinks: NavLink[] = [
  { href: "/#features", label: "Features" },
  { href: "/integrations", label: "Integrations" },
  { href: "/pricing", label: "Pricing" },
  { href: "/docs", label: "Docs" },
  { href: "/about", label: "About" },
];

export interface FooterGroup {
  title: string;
  links: NavLink[];
}

export const footerGroups: FooterGroup[] = [
  {
    title: "Product",
    links: [
      { href: "/#features", label: "Features" },
      { href: "/integrations", label: "Integrations" },
      { href: "/pricing", label: "Pricing" },
      { href: "/try-it", label: "Free PDF Test" },
      { href: "/docs", label: "Docs" },
    ],
  },
  {
    title: "Developers",
    links: [
      // /swagger is intentionally not listed here — Docs owns the single
      // discovery surface for everything API-related, and the /docs landing
      // hero + docs-nav both link to the live Swagger UI directly.
      { href: "/docs/postman", label: "Postman Collection" },
      { href: "/docs/authentication", label: "Authentication" },
    ],
  },
  {
    title: "Resources",
    links: [
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
