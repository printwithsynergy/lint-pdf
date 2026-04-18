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
  { href: "/swagger", label: "API" },
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
      { href: "/swagger", label: "API Reference" },
      { href: "/docs/postman", label: "Postman Collection" },
      { href: "/docs/webhooks", label: "Webhooks" },
      { href: "/docs/job-state", label: "Universal Job State" },
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
      {
        href: "https://github.com/thinkneverland/lint-pdf",
        label: "GitHub",
        external: true,
      },
      { href: "/contact", label: "Contact Us" },
    ],
  },
];
