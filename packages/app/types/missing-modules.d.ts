/**
 * Stub type declarations for private packages that are not yet published
 * or whose types are not available during CI typecheck.
 *
 * Remove individual declarations once the corresponding package ships its own types.
 */

declare module "@thinkneverland/grounded-plugin" {
  import type { PixieDustPlugin } from "@thinkneverland/pixie-dust-fairy-ring";

  export const lintpdfPlugin: PixieDustPlugin;
  export const lintpdfUsagePlugin: PixieDustPlugin;
  export const lintpdfApiKeysPlugin: PixieDustPlugin;
  export const lintpdfReportsPlugin: PixieDustPlugin;
  export const lintpdfTeamPlugin: PixieDustPlugin;
  export const lintpdfAccountPlugin: PixieDustPlugin;
  export const lintpdfSiteAdminPlugin: PixieDustPlugin;
  export const lintpdfWebhooksPlugin: PixieDustPlugin;
  export const lintpdfEndpointsPlugin: PixieDustPlugin;
  export const lintpdfSuperAdminPlugin: PixieDustPlugin;
}

declare module "@lintpdf/stripe" {
  import type { PixieDustPlugin } from "@thinkneverland/pixie-dust-fairy-ring";

  export const lintpdfBillingPlugin: PixieDustPlugin;
}
