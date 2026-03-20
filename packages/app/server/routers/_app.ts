import { createTRPCRouter } from "../trpc";

import { tenantRouter } from "./tenant";

export const appRouter = createTRPCRouter({
  tenant: tenantRouter,
});

export type AppRouter = typeof appRouter;
