"use client";

import { useCallback, useEffect, useState } from "react";

interface TeamMember {
  userId: string;
  role: string;
  joinedAt: string;
  user: {
    id: string;
    name: string | null;
    email: string;
    image: string | null;
  };
}

interface PendingInvite {
  id: string;
  email: string;
  role: string;
  createdAt: string;
  expiresAt: string;
}

const ROLES = ["VIEWER", "MEMBER", "OPERATOR", "ADMIN", "OWNER"];

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Invite form
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [inviting, setInviting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [membersResp, invitesResp] = await Promise.all([
        fetch("/api/grounded/team"),
        fetch("/api/grounded/team/invites"),
      ]);
      if (membersResp.ok) {
        const data = await membersResp.json();
        setMembers(Array.isArray(data) ? data : []);
      }
      if (invitesResp.ok) {
        const data = await invitesResp.json();
        setInvites(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load team data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleInvite() {
    setInviting(true);
    setError("");
    try {
      const resp = await fetch("/api/grounded/team/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to send invite");
      }
      setInviteEmail("");
      setShowInvite(false);
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send invite");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: string) {
    try {
      await fetch(`/api/grounded/team/${userId}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRole }),
      });
      await fetchData();
    } catch {
      setError("Failed to update role");
    }
  }

  async function handleRemove(userId: string) {
    if (!confirm("Remove this team member?")) return;
    try {
      await fetch(`/api/grounded/team/${userId}`, { method: "DELETE" });
      await fetchData();
    } catch {
      setError("Failed to remove member");
    }
  }

  async function handleCancelInvite(inviteId: string) {
    try {
      await fetch(`/api/grounded/team/invites/${inviteId}`, {
        method: "DELETE",
      });
      await fetchData();
    } catch {
      setError("Failed to cancel invite");
    }
  }

  if (loading) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Team</h1>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Team</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage team members and their access permissions.
          </p>
        </div>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showInvite ? "Cancel" : "Invite Member"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Invite form */}
      {showInvite && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Invite Team Member</h2>
          <div className="mt-3 flex gap-3">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="email@example.com"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
            >
              {ROLES.filter((r) => r !== "OWNER").map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
            <button
              onClick={handleInvite}
              disabled={inviting || !inviteEmail}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {inviting ? "Sending..." : "Send Invite"}
            </button>
          </div>
        </div>
      )}

      {/* Members */}
      <div className="mt-6 space-y-2">
        <h2 className="text-lg font-semibold">Members ({members.length})</h2>
        {members.map((m) => (
          <div
            key={m.userId}
            className="flex items-center justify-between rounded-lg border p-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {(m.user.name ?? m.user.email).charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="font-medium">{m.user.name ?? m.user.email}</div>
                <div className="text-xs text-muted-foreground">
                  {m.user.email}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={m.role}
                onChange={(e) => handleRoleChange(m.userId, e.target.value)}
                className="rounded border px-2 py-1 text-xs"
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
              {m.role !== "OWNER" && (
                <button
                  onClick={() => handleRemove(m.userId)}
                  className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Pending invites */}
      {invites.length > 0 && (
        <div className="mt-6 space-y-2">
          <h2 className="text-lg font-semibold">
            Pending Invites ({invites.length})
          </h2>
          {invites.map((inv) => (
            <div
              key={inv.id}
              className="flex items-center justify-between rounded-lg border border-dashed p-3"
            >
              <div>
                <div className="font-medium">{inv.email}</div>
                <div className="text-xs text-muted-foreground">
                  Role: {inv.role} &middot; Expires{" "}
                  {new Date(inv.expiresAt).toLocaleDateString()}
                </div>
              </div>
              <button
                onClick={() => handleCancelInvite(inv.id)}
                className="rounded border px-2 py-1 text-xs hover:bg-muted"
              >
                Cancel
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
