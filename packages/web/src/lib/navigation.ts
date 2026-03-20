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
      { href: "/pricing", label: "Pricing" },
      { href: "/docs", label: "API Docs" },
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
    ],
  },
];
