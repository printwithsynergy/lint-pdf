"""Resend-backed email service for tenant notifications."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Module-level container — set via configure_email() or set_email_client()
_email_state: dict[str, Any] = {
    "client": None,
    "from_address": "LintPDF <noreply@thinkneverland.com>",
}
_email_lock = threading.Lock()


def configure_email(api_key: str, *, from_address: str | None = None) -> None:
    """Initialize the Resend client.

    Args:
        api_key: Resend API key.
        from_address: Sender address override.
    """
    with _email_lock:
        if _email_state["client"] is not None:
            return
        import resend

        resend.api_key = api_key
        _email_state["client"] = resend.Emails
        if from_address:
            _email_state["from_address"] = from_address


def set_email_client(client: Any) -> None:
    """Override the email client (for testing)."""
    _email_state["client"] = client


def get_email_client() -> Any:
    """Return the current email client."""
    return _email_state["client"]


@dataclass
class EmailResult:
    """Result of sending an email."""

    success: bool
    email_id: str | None = None
    error: str | None = None


def send_api_key_issued(*, to: str, tenant_name: str, api_key: str) -> EmailResult:
    """Send API key notification to a new tenant.

    Args:
        to: Recipient email address.
        tenant_name: Name of the tenant organization.
        api_key: The raw API key (shown only once).
    """
    subject = f"Your LintPDF API Key — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e293b;">Welcome to LintPDF</h2>
  <p>Your API key for <strong>{tenant_name}</strong> has been issued.</p>
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <code style="font-size: 14px; word-break: break-all;">{api_key}</code>
  </div>
  <p style="color: #ef4444; font-size: 14px;">
    <strong>Save this key now.</strong> It cannot be retrieved after this email.
  </p>
  <p style="font-size: 14px; color: #64748b;">
    Include it in your requests as:<br>
    <code>Authorization: Bearer YOUR_API_KEY</code>
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_job_complete(
    *, to: str, tenant_name: str, job_id: str, file_name: str, finding_count: int
) -> EmailResult:
    """Notify tenant that a preflight job completed.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        job_id: The completed job ID.
        file_name: Original uploaded file name.
        finding_count: Number of findings detected.
    """
    status_text = "passed" if finding_count == 0 else f"found {finding_count} issue(s)"
    subject = f"Preflight {status_text} — {file_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e293b;">Preflight Complete</h2>
  <p>Job for <strong>{file_name}</strong> has finished.</p>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr>
      <td style="padding: 8px; color: #64748b;">Organization</td>
      <td style="padding: 8px;"><strong>{tenant_name}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Job ID</td>
      <td style="padding: 8px;"><code>{job_id}</code></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Findings</td>
      <td style="padding: 8px;"><strong>{finding_count}</strong></td>
    </tr>
  </table>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_rate_limit_warning(*, to: str, tenant_name: str, used: int, limit: int) -> EmailResult:
    """Warn tenant they are approaching or have hit their daily rate limit.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        used: Current daily usage count.
        limit: Daily rate limit.
    """
    pct = int((used / limit) * 100) if limit > 0 else 100
    subject = f"Rate limit {pct}% — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #f59e0b;">Rate Limit Warning</h2>
  <p><strong>{tenant_name}</strong> has used <strong>{used}</strong> of <strong>{limit}</strong> daily requests ({pct}%).</p>
  <p style="font-size: 14px; color: #64748b;">
    Upgrade your plan to increase your daily limit.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_overage_started(
    *, to: str, tenant_name: str, used: int, limit: int, rate_cents: int, cost_cents: int
) -> EmailResult:
    """Notify tenant that billable overage charges have begun.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        used: Current daily usage count.
        limit: Daily rate limit (included jobs).
        rate_cents: Per-job overage rate in cents.
        cost_cents: Current total overage cost in cents.
    """
    rate_dollars = f"${rate_cents / 100:.2f}"
    cost_dollars = f"${cost_cents / 100:.2f}"
    subject = f"Overage billing active — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #f59e0b;">Overage Billing Active</h2>
  <p><strong>{tenant_name}</strong> has used <strong>{used}</strong> of <strong>{limit}</strong> daily included jobs.</p>
  <p>Additional jobs are being charged at <strong>{rate_dollars}/job</strong>.</p>
  <p>Current overage cost today: <strong>{cost_dollars}</strong></p>
  <p style="font-size: 14px; color: #64748b;">
    Upgrade your plan for more included jobs, or set a spending cap in your dashboard.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_report(
    *,
    to: str,
    tenant_name: str,
    job_id: str,
    report_url: str,
    finding_count: int,
    passed: bool,
    brand_name: str = "LintPDF",
    brand_primary_color: str = "#0ea5e9",
) -> EmailResult:
    """Send a preflight report email with link to hosted report.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        job_id: The completed job ID.
        report_url: URL to the hosted interactive report.
        finding_count: Number of findings detected.
        passed: Whether the document passed preflight.
        brand_name: White-label brand name.
        brand_primary_color: Brand primary color.
    """
    status_text = "passed" if passed else f"found {finding_count} issue(s)"
    subject = f"Preflight Report — {status_text}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: {brand_primary_color};">{brand_name} Preflight Report</h2>
  <p>Preflight for <strong>{tenant_name}</strong> job <code>{job_id}</code> has {status_text}.</p>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr>
      <td style="padding: 8px; color: #64748b;">Status</td>
      <td style="padding: 8px;"><strong>{"PASS" if passed else "FAIL"}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Findings</td>
      <td style="padding: 8px;"><strong>{finding_count}</strong></td>
    </tr>
  </table>
  <div style="margin: 24px 0;">
    <a href="{report_url}" style="display: inline-block; padding: 12px 24px; background: {brand_primary_color}; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
      View Interactive Report
    </a>
  </div>
  <p style="font-size: 12px; color: #9ca3af;">
    This report is hosted and may expire. Save or print it for permanent records.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_trial_report_email(
    *,
    to: str,
    name: str,
    report_urls: list[str],
    finding_count: int,
    passed: bool,
) -> EmailResult:
    """Send a free trial preflight report to a prospect.

    Args:
        to: Recipient email address.
        name: Prospect's name.
        report_urls: URLs to the hosted interactive reports.
        finding_count: Total findings across all files.
        passed: Whether all documents passed preflight.
    """
    status_text = "passed" if passed else f"found {finding_count} issue(s)"
    subject = "Your Free LintPDF Preflight Report"

    report_links = "\n".join(
        f'    <a href="{url}" style="display: inline-block; margin: 4px 0; padding: 10px 20px; '
        f"background: #1e3a8a; color: white; text-decoration: none; border-radius: 6px; "
        f'font-weight: bold; font-size: 14px;">View Report {i + 1}</a><br>'
        for i, url in enumerate(report_urls)
    )

    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e3a8a;">Your Free Preflight Report</h2>
  <p>Hi {name},</p>
  <p>Thanks for submitting your files to LintPDF. We've run our preflight analysis and your files {status_text}.</p>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr>
      <td style="padding: 8px; color: #64748b;">Status</td>
      <td style="padding: 8px;"><strong>{"PASS" if passed else "NEEDS ATTENTION"}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Total Findings</td>
      <td style="padding: 8px;"><strong>{finding_count}</strong></td>
    </tr>
  </table>
  <div style="margin: 24px 0;">
{report_links}
  </div>
  <p style="font-size: 14px; color: #334155;">
    Want to run preflights like this on every file, automatically? LintPDF integrates with your
    existing workflow via API, hot folders, or our dashboard.
  </p>
  <div style="margin: 20px 0;">
    <a href="https://lintpdf.com/try-it" style="display: inline-block; padding: 10px 20px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
      Learn More
    </a>
  </div>
  <p style="font-size: 12px; color: #9ca3af;">
    Questions? Just reply to this email &mdash; we'd love to help.<br>
    Reports are hosted and may expire after 30 days.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _send(*, to: str, subject: str, html: str) -> EmailResult:
    """Send an email via the configured client.

    Returns:
        EmailResult with success status.
    """
    # Validate email to prevent header injection
    if not _EMAIL_RE.match(to) or "\n" in to or "\r" in to:
        logger.warning("Invalid email address rejected: %s", to)
        return EmailResult(success=False, error="Invalid email address")

    if _email_state["client"] is None:
        logger.warning("Email client not configured — skipping send to %s", to)
        return EmailResult(success=False, error="Email client not configured")

    try:
        result = _email_state["client"].send(
            {
                "from": _email_state["from_address"],
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else None
        return EmailResult(success=True, email_id=email_id)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return EmailResult(success=False, error="Send failed")


def send_approval_request(
    *,
    to: str,
    approver_name: str | None,
    step_name: str,
    step_number: int,
    total_steps: int,
    approve_url: str,
    viewer_url: str,
    brand_name: str = "LintPDF",
    brand_primary_color: str = "#1e3a8a",
    chain_id: str = "",
) -> EmailResult:
    """Ask an approver to review and approve/reject a preflight report."""
    salutation = f"Hi {approver_name}," if approver_name else "Hello,"
    subject = f"{brand_name}: Approval needed — {step_name} ({step_number}/{total_steps})"

    # Progress bar
    pct = int(((step_number - 1) / max(total_steps, 1)) * 100)
    html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1f2937;">
  <h2 style="color: {brand_primary_color}; margin: 0 0 16px;">{brand_name} Approval Request</h2>
  <p>{salutation}</p>
  <p>A preflight report is awaiting your review as <strong>{step_name}</strong> (step {step_number} of {total_steps}).</p>

  <div style="background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 20px 0;">
    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Progress</div>
    <div style="background: #e2e8f0; border-radius: 999px; height: 8px; overflow: hidden;">
      <div style="background: {brand_primary_color}; height: 100%; width: {pct}%;"></div>
    </div>
    <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Step {step_number} of {total_steps}: <strong>{step_name}</strong></div>
  </div>

  <div style="margin: 28px 0; text-align: center;">
    <a href="{approve_url}" style="display: inline-block; padding: 14px 32px; background: {brand_primary_color}; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 15px;">
      Review &amp; Approve
    </a>
  </div>

  <p style="font-size: 13px; color: #6b7280; text-align: center;">
    Or view the full interactive report: <a href="{viewer_url}" style="color: {brand_primary_color};">{viewer_url}</a>
  </p>

  <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 32px 0;" />
  <p style="font-size: 11px; color: #9ca3af;">
    This approval link is specific to you. If you did not expect this email, please ignore it.
    <br />Reference: <code>{chain_id}</code>
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_approval_step_decided(
    *,
    to: str,
    step_name: str,
    decision: str,
    approver_email: str,
    notes: str | None,
    viewer_url: str,
    brand_name: str = "LintPDF",
    brand_primary_color: str = "#1e3a8a",
) -> EmailResult:
    """Notify the chain initiator/tenant that an approver made a decision."""
    subject = f"{brand_name}: {step_name} {decision}"
    color = "#22c55e" if decision == "approved" else "#ef4444"
    notes_html = (
        f'<p style="background: #f1f5f9; border-left: 3px solid {color}; padding: 12px 16px; margin: 12px 0; border-radius: 4px; font-size: 13px;"><em>Notes:</em> {notes}</p>'
        if notes
        else ""
    )
    html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1f2937;">
  <h2 style="color: {brand_primary_color}; margin: 0 0 16px;">{brand_name} — Step Update</h2>
  <p><strong>{step_name}</strong> was <span style="color: {color}; font-weight: 700; text-transform: uppercase;">{decision}</span> by {approver_email}.</p>
  {notes_html}
  <div style="margin: 24px 0;">
    <a href="{viewer_url}" style="display: inline-block; padding: 10px 24px; background: {brand_primary_color}; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
      View Report
    </a>
  </div>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_approval_chain_completed(
    *,
    to: str,
    final_status: str,
    file_name: str,
    viewer_url: str,
    brand_name: str = "LintPDF",
    brand_primary_color: str = "#1e3a8a",
) -> EmailResult:
    """Notify the chain initiator that the full chain completed."""
    color = "#22c55e" if final_status == "approved" else "#ef4444"
    subject = f"{brand_name}: Approval chain {final_status} — {file_name}"
    html = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1f2937;">
  <h2 style="color: {brand_primary_color}; margin: 0 0 16px;">{brand_name} — Chain Complete</h2>
  <div style="background: {color}; color: white; padding: 16px; border-radius: 8px; font-size: 18px; font-weight: 700; text-align: center; text-transform: uppercase;">
    {final_status}
  </div>
  <p>The approval chain for <strong>{file_name}</strong> has completed with status <strong>{final_status}</strong>.</p>
  <div style="margin: 24px 0;">
    <a href="{viewer_url}" style="display: inline-block; padding: 10px 24px; background: {brand_primary_color}; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
      View Full Report
    </a>
  </div>
</div>"""
    return _send(to=to, subject=subject, html=html)
