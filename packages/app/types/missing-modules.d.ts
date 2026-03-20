/**
 * Stub type declarations for private packages that are not yet published
 * or whose types are not available during CI typecheck.
 *
 * Remove individual declarations once the corresponding package ships its own types.
 */

declare module "@thinkneverland/grounded-plugin" {
  import type { PixieDustPlugin } from "@thinkneverland/pixie-dust-fairy-ring";

  export const groundedPlugin: PixieDustPlugin;
  export const groundedUsagePlugin: PixieDustPlugin;
  export const groundedApiKeysPlugin: PixieDustPlugin;
  export const groundedReportsPlugin: PixieDustPlugin;
  export const groundedTeamPlugin: PixieDustPlugin;
  export const groundedAccountPlugin: PixieDustPlugin;
  export const groundedSiteAdminPlugin: PixieDustPlugin;
}

declare module "@grounded/stripe" {
  import type { PixieDustPlugin } from "@thinkneverland/pixie-dust-fairy-ring";

  export const groundedBillingPlugin: PixieDustPlugin;
}
