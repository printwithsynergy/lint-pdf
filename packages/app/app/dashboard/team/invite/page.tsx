import { requirePermission } from "@/lib/require-permission";
import { redirect } from "next/navigation";

export default async function TeamInvitePage() {
  await requirePermission("team:manage");
  redirect("/dashboard/team");
}
