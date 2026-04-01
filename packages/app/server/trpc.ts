import {
  createTRPCInfra,
  type TRPCContext,
} from "@thinkneverland/pixie-dust-core";
import { prisma } from "@thinkneverland/pixie-dust-database/server";

const trpc = createTRPCInfra({ db: prisma });

export type { TRPCContext };
export const createTRPCContext = trpc.createTRPCContext;
export const createCallerFactory = trpc.createCallerFactory;
export const createTRPCRouter = trpc.createTRPCRouter;
export const publicProcedure = trpc.publicProcedure;
export const protectedProcedure = trpc.protectedProcedure;
export const tenantProcedure = trpc.tenantProcedure;
