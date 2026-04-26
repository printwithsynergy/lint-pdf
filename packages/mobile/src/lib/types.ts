export interface TenantBranding {
  brandName?: string | null;
  brandLogoUrl?: string | null;
  brandLogoUrlDark?: string | null;
  brandTagline?: string | null;
  primaryColor?: string | null;
  accentColor?: string | null;
  emailButtonColor?: string | null;
  loginBgColor?: string | null;
  loginCardColor?: string | null;
  loginTextColor?: string | null;
  faviconUrl?: string | null;
  loginHeading?: string | null;
  loginSubheading?: string | null;
  // Branding shapes evolve upstream — keep room for fields the mobile
  // app does not yet read so JSON round-trips without loss.
  [key: string]: unknown;
}

export interface TenantLookupResponse {
  tenantId: string;
  name: string;
  slug: string;
  domain: string | null;
  branding: TenantBranding;
}

export interface CapturedTenant {
  tenantId: string;
  name: string;
  slug: string;
  domain: string | null;
  branding: TenantBranding;
  capturedAt: string;
}
