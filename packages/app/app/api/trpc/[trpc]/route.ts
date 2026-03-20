export const dynamic = "force-dynamic";

import { createTRPCHandler } from "@thinkneverland/pixie-dust-core";

import { appRouter } from "@/server/routers/_app";
import { createTRPCContext } from "@/server/trpc";

const handler = createTRPCHandler({
  router: appRouter,
  createContext: createTRPCContext,
});

export { handler as GET, handler as POST };
