/**
 * Profile proxy routes — forward requests to the Grounded API.
 */

import type { RouteDefinition, RouteResponse } from "@thinkneverland/pixie-dust-fairy-ring";
import { getClient } from "../index";

export function profileRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/profiles",
      auth: true,
      permission: "preflight:view",
      description: "List available preflight profiles (flight plans)",
      handler: async (): Promise<RouteResponse> => {
        const client = getClient();
        if (!client) {
          return { status: 503, body: { error: "Grounded API not configured" } };
        }
        const profiles = await client.listProfiles();
        return { status: 200, body: profiles };
      },
    },
  ];
}
