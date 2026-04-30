"use client";

import { useState } from "react";
import { useViewerApi } from "../../types";

interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  token: string;
  viewerUrl: string;
}

export function ShareDialog({ isOpen, onClose, token: _token, viewerUrl }: ShareDialogProps) {
  const { apiBase } = useViewerApi();
  const [emailsInput, setEmailsInput] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ sent: number; total: number; errors: string[] } | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const parseEmails = (input: string): string[] => {
    return input
      .split(/[\s,;\n]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
  };

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    const emails = parseEmails(emailsInput);
    if (emails.length === 0) {
      setError("Enter at least one email address.");
      return;
    }
    const invalid = emails.filter((e) => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e));
    if (invalid.length > 0) {
      setError(`Invalid email addresses: ${invalid.join(", ")}`);
      return;
    }

    setSending(true);
    try {
      const resp = await fetch(`${apiBase}/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emails, message: message.trim() || null }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.error || data.detail || "Failed to send emails");
      } else {
        setResult(data);
        if (data.sent === data.total) {
          setEmailsInput("");
          setMessage("");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSending(false);
    }
  }

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(viewerUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      const el = document.createElement("textarea");
      el.value = viewerUrl;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Dialog */}
      <div className="fixed left-1/2 top-1/2 z-[101] w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-slate-900 p-5 shadow-2xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Share Preflight Report</h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Copy link section */}
        <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800 p-3">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Shareable Link
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={viewerUrl}
              readOnly
              className="flex-1 truncate rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-300"
              onFocus={(e) => e.target.select()}
            />
            <button
              onClick={handleCopyLink}
              className="shrink-0 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>

        <form onSubmit={handleSend}>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Email Recipients
          </label>
          <textarea
            value={emailsInput}
            onChange={(e) => setEmailsInput(e.target.value)}
            placeholder="alice@example.com, bob@example.com"
            rows={2}
            className="mb-3 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-blue-500"
          />
          <p className="-mt-2 mb-3 text-[10px] text-slate-500">
            Separate multiple emails with commas, spaces, or new lines (max 20).
          </p>

          {error && (
            <div className="mb-3 rounded border border-red-700/50 bg-red-900/30 px-3 py-2 text-xs text-red-300">
              {error}
            </div>
          )}
          {result && (
            <div className={`mb-3 rounded border px-3 py-2 text-xs ${
              result.sent === result.total
                ? "border-green-700/50 bg-green-900/30 text-green-300"
                : "border-amber-700/50 bg-amber-900/30 text-amber-300"
            }`}>
              Sent {result.sent} of {result.total} {result.total === 1 ? "email" : "emails"}.
              {result.errors.length > 0 && (
                <div className="mt-1 text-[10px] opacity-80">
                  Errors: {result.errors.join("; ")}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={sending || !emailsInput.trim()}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              {sending ? "Sending…" : "Send Email"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
