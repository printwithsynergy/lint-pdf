import { TeamPage } from "@thinkneverland/pixie-dust-dashboard";

// Upstream TeamPage wraps its content in `mx-auto max-w-5xl`, but the
// rest of the LintPDF dashboard pages render full-bleed under
// DashboardShell. Override the inner max-width so the team page matches
// the canonical width of the rest of the dashboard.
export default function Team() {
  return (
    <div className="[&>div]:!max-w-none [&>div]:!mx-0">
      <TeamPage />
    </div>
  );
}
