/**
 * Team management plugin — manage tenant members and invites via Pixie Dust models.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

interface TeamDb {
  tenantUser: {
    findMany: (args: Record<string, unknown>) => Promise<unknown[]>;
    update: (args: Record<string, unknown>) => Promise<unknown>;
    delete: (args: Record<string, unknown>) => Promise<unknown>;
  };
  tenantInvite: {
    create: (args: Record<string, unknown>) => Promise<{ id: string }>;
    findMany: (args: Record<string, unknown>) => Promise<unknown[]>;
    update: (args: Record<string, unknown>) => Promise<unknown>;
  };
}

interface AuthServiceWithInvite {
  sendInviteEmail?: (params: {
    email: string;
    tenantId: string;
    inviteId: string;
  }) => Promise<void>;
}

export const groundedTeamPlugin: PixieDustPlugin = {
  name: "grounded-team",
  version: "0.1.0",
  description: "Team member and invite management for Grounded tenants",
  dependencies: ["grounded"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("team:manage", ["ADMIN", "OWNER"]);
    ctx.addPermission("team:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);

    // Navigation
    ctx.addNavItem({
      label: "Team",
      href: "/dashboard/team",
      icon: "users-cog",
      section: "admin",
      order: 55,
      requiredPermission: "team:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/team",
      title: "Team Members",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/team/invite",
      title: "Invite Member",
      layout: "dashboard",
    });

    // Routes
    const db = ctx.services.db as TeamDb;

    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/",
        auth: true,
        permission: "team:view",
        description: "List team members for the current tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const members = await db.tenantUser.findMany({
            where: { tenantId },
            include: {
              user: {
                select: { id: true, name: true, email: true, image: true },
              },
            },
            orderBy: { createdAt: "asc" },
          });
          return { status: 200, body: members };
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/invite",
        auth: true,
        permission: "team:manage",
        description: "Invite a new member to the tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }

          const { email, role } = req.body as { email?: string; role?: string };
          if (!email) {
            return { status: 400, body: { error: "Email is required" } };
          }

          const invite = await db.tenantInvite.create({
            data: {
              tenantId,
              email,
              role: role ?? "MEMBER",
              invitedById: req.auth?.userId,
              expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
            },
          });

          // Best-effort email notification
          try {
            const authService = ctx.services.auth as
              | AuthServiceWithInvite
              | undefined;
            if (
              authService &&
              typeof authService.sendInviteEmail === "function"
            ) {
              await authService.sendInviteEmail({
                email,
                tenantId,
                inviteId: invite.id,
              });
            }
          } catch {
            ctx.services.logger.warn(
              "Team plugin: failed to send invite email",
              {
                email,
                tenantId,
              },
            );
          }

          return { status: 201, body: invite };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/:userId/role",
        auth: true,
        permission: "team:manage",
        description: "Update a team member's role",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const { role } = req.body as { role?: string };
          if (!role) {
            return { status: 400, body: { error: "Role is required" } };
          }
          const updated = await db.tenantUser.update({
            where: {
              tenantId_userId: { tenantId, userId: req.params.userId },
            },
            data: { role },
          });
          return { status: 200, body: updated };
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/:userId",
        auth: true,
        permission: "team:manage",
        description: "Remove a member from the tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          await db.tenantUser.delete({
            where: {
              tenantId_userId: { tenantId, userId: req.params.userId },
            },
          });
          return { status: 204 };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/invites",
        auth: true,
        permission: "team:manage",
        description: "List pending invites for the current tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const invites = await db.tenantInvite.findMany({
            where: { tenantId, acceptedAt: null, revokedAt: null },
            orderBy: { createdAt: "desc" },
          });
          return { status: 200, body: invites };
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/invites/:inviteId",
        auth: true,
        permission: "team:manage",
        description: "Cancel a pending invite",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          await db.tenantInvite.update({
            where: { id: req.params.inviteId, tenantId },
            data: { revokedAt: new Date() },
          });
          return { status: 204 };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/grounded/team", routes);
  },
};
