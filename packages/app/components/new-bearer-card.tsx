"use client";

/**
 * Shared "fresh bearer / secret" copy-once card.
 *
 * Used by admin pages that mint or rotate a credential where the engine
 * surfaces the cleartext value exactly once — API keys (`admin/api-keys`)
 * and webhook HMAC secrets (`admin/webhook-endpoints`). Extracted so both
 * pages stay visually aligned after the PR D / PR E sweeps.
 */

interface NewBearerCardProps {
  /** Display label — "New API key", "New webhook secret", etc. */
  title: string;
  /** Body of the cleartext credential. */
  secret: string;
  /** Optional explanatory subtitle shown above the secret block. */
  subtitle?: string;
  /** Dismiss handler. */
  onDismiss: () => void;
}

export function NewBearerCard({
  title,
  secret,
  subtitle = "Copy it now — it's shown only once and cannot be retrieved later.",
  onDismiss,
}: NewBearerCardProps) {
  return (
    <div className="mt-4 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm">
      <div className="font-semibold text-emerald-800">{title}</div>
      <p className="mt-1 text-emerald-700">{subtitle}</p>
      <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-xs">
        {secret}
      </code>
      <button
        type="button"
        className="mt-2 text-xs text-emerald-800 underline"
        onClick={onDismiss}
      >
        Dismiss
      </button>
    </div>
  );
}
