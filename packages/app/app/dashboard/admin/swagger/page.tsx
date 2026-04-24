import { redirect } from "next/navigation";

/**
 * Back-compat alias for the old Swagger URL. Canonical path is now
 * /dashboard/admin/api-reference — keep this route around so existing
 * bookmarks, in-app links, and external references resolve.
 */
export default function AdminSwaggerRedirect(): never {
  redirect("/dashboard/admin/api-reference");
}
