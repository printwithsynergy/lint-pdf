import { assertPermission } from "@thinkneverland/pixie-dust-auth";
import {
  prisma,
  createTenantClient,
} from "@thinkneverland/pixie-dust-database/server";
import { TRPCError } from "@trpc/server";
import { z } from "zod";

import { createTRPCRouter, protectedProcedure, tenantProcedure } from "../trpc";

export const tenantRouter = createTRPCRouter({
  create: protectedProcedure
    .input(
      z.object({
        name: z.string().min(2).max(100),
        slug: z
          .string()
          .min(2)
          .max(50)
          .regex(
            /^[a-z0-9-]+$/,
            "Slug must contain only lowercase letters, numbers, and hyphens",
          ),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const existing = await prisma.tenant.findUnique({
        where: { slug: input.slug },
      });

      if (existing) {
        throw new TRPCError({
          code: "CONFLICT",
          message: "A tenant with this slug already exists.",
        });
      }

      const tenant = await prisma.tenant.create({
        data: {
          name: input.name,
          slug: input.slug,
        },
      });

      await prisma.tenantUser.create({
        data: {
          userId: ctx.auth.userId,
          tenantId: tenant.id,
          role: "OWNER",
        },
      });

      await prisma.auditLog.create({
        data: {
          tenantId: tenant.id,
          userId: ctx.auth.userId,
          action: "tenant.created",
          entity: "Tenant",
          entityId: tenant.id,
        },
      });

      return { id: tenant.id, slug: tenant.slug };
    }),

  get: tenantProcedure
    .input(z.object({ tenantId: z.string() }))
    .query(async ({ ctx }) => {
      const db = createTenantClient(prisma, ctx.tenantAuth.tenantId);

      const tenant = await prisma.tenant.findUnique({
        where: { id: ctx.tenantAuth.tenantId },
      });

      if (!tenant) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Tenant not found.",
        });
      }

      const memberCount = await db.tenantUser.count();

      return {
        id: tenant.id,
        name: tenant.name,
        slug: tenant.slug,
        status: tenant.status,
        memberCount,
        createdAt: tenant.createdAt,
      };
    }),

  listMembers: tenantProcedure
    .input(z.object({ tenantId: z.string() }))
    .query(async ({ ctx }) => {
      const db = createTenantClient(prisma, ctx.tenantAuth.tenantId);

      const members = await db.tenantUser.findMany({
        include: {
          user: {
            select: { id: true, email: true, name: true, avatarUrl: true },
          },
        },
        orderBy: { joinedAt: "asc" },
      });

      return members.map((m: (typeof members)[number]) => ({
        id: m.id,
        userId: m.userId,
        role: m.role,
        joinedAt: m.joinedAt,
        user: m.user,
      }));
    }),

  updateSettings: tenantProcedure
    .input(
      z.object({
        tenantId: z.string(),
        name: z.string().min(2).max(100).optional(),
        settings: z.record(z.unknown()).optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      assertPermission(ctx.tenantAuth, "settings:manage");

      const data: Record<string, unknown> = {};
      if (input.name) data.name = input.name;
      if (input.settings) data.settings = input.settings;

      const tenant = await prisma.tenant.update({
        where: { id: ctx.tenantAuth.tenantId },
        data,
      });

      await prisma.auditLog.create({
        data: {
          tenantId: ctx.tenantAuth.tenantId,
          userId: ctx.tenantAuth.userId,
          action: "tenant.updated",
          entity: "Tenant",
          entityId: tenant.id,
          metadata: { changes: Object.keys(data) },
        },
      });

      return { id: tenant.id, name: tenant.name };
    }),

  removeMember: tenantProcedure
    .input(
      z.object({
        tenantId: z.string(),
        userId: z.string(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      assertPermission(ctx.tenantAuth, "members:manage");

      if (input.userId === ctx.tenantAuth.userId) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "You cannot remove yourself from the tenant.",
        });
      }

      const db = createTenantClient(prisma, ctx.tenantAuth.tenantId);

      const member = await db.tenantUser.findFirst({
        where: { userId: input.userId },
      });

      if (!member) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Member not found.",
        });
      }

      if (member.role === "OWNER" && !ctx.tenantAuth.isSuperAdmin) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Cannot remove the tenant owner.",
        });
      }

      await db.tenantUser.delete({ where: { id: member.id } });

      await prisma.auditLog.create({
        data: {
          tenantId: ctx.tenantAuth.tenantId,
          userId: ctx.tenantAuth.userId,
          action: "member.removed",
          entity: "TenantUser",
          entityId: member.id,
          metadata: { removedUserId: input.userId },
        },
      });

      return { success: true };
    }),
});
