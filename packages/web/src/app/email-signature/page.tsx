"use client";

/**
 * Internal staff email signature helper.
 *
 * Mirrors the approach used by Print with Synergy's /email-signature —
 * renders the signature exactly as it should appear in Mac Mail, then lets
 * the user copy it as HTML (rich) or as plain text with one click.
 *
 * Not linked from site nav or sitemap.ts on purpose — this is shared
 * internally when onboarding teammates onto LintPDF email.
 */

import { useRef, useState } from "react";

const SIGNATURE_OWNER = {
  name: "Quincy Adams",
  title: "Founder & Principal Engineer",
  company: "LintPDF",
  tagline: "Preflights you won't hate.",
  email: "qadams@lintpdf.com",
  website: "lintpdf.com",
  websiteUrl: "https://lintpdf.com",
  logoUrl: "https://lintpdf.com/logo-marketing.png",
} as const;

function buildSignatureHtml() {
  // Inline styles only — every email client strips <style> blocks and
  // class names, so the signature has to carry its own CSS on each tag.
  return `<table cellpadding="0" cellspacing="0" border="0" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 14px; color: #475569; line-height: 1.5;">
  <tr>
    <td style="padding-right: 16px; vertical-align: top;">
      <a href="${SIGNATURE_OWNER.websiteUrl}" style="text-decoration: none;"><img src="${SIGNATURE_OWNER.logoUrl}" width="120" height="auto" alt="LintPDF" style="display: block; border: 0; max-width: 120px;"></a>
    </td>
    <td style="padding-left: 16px; border-left: 3px solid #2563eb; vertical-align: top;">
      <div style="font-size: 16px; font-weight: 700; color: #0F172A;">${SIGNATURE_OWNER.name}</div>
      <div style="color: #475569;">${SIGNATURE_OWNER.title} · ${SIGNATURE_OWNER.company}</div>
      <div style="color: #1e3a8a; font-style: italic; margin: 6px 0;">${SIGNATURE_OWNER.tagline}</div>
      <div>
        <a href="mailto:${SIGNATURE_OWNER.email}" style="color: #0F172A; text-decoration: none;">${SIGNATURE_OWNER.email}</a><br>
        <a href="${SIGNATURE_OWNER.websiteUrl}" style="color: #2563eb; text-decoration: none;">${SIGNATURE_OWNER.website}</a>
      </div>
    </td>
  </tr>
</table>`;
}

function buildSignatureText() {
  return `— ${SIGNATURE_OWNER.name}
${SIGNATURE_OWNER.title} · ${SIGNATURE_OWNER.company}
${SIGNATURE_OWNER.tagline}

${SIGNATURE_OWNER.email}
${SIGNATURE_OWNER.websiteUrl}`;
}

type CopyState = "idle" | "copied" | "error";

export default function EmailSignaturePage() {
  const previewRef = useRef<HTMLDivElement>(null);
  const [htmlCopyState, setHtmlCopyState] = useState<CopyState>("idle");
  const [textCopyState, setTextCopyState] = useState<CopyState>("idle");
  const [rawCopyState, setRawCopyState] = useState<CopyState>("idle");

  const signatureHtml = buildSignatureHtml();
  const signatureText = buildSignatureText();

  /**
   * Copy the *rendered* signature so Mac Mail receives styled HTML, not the
   * source markup. We pair text/html with text/plain via the async Clipboard
   * API so the plain-text fallback is also sensible if pasted into a
   * plain-text field.
   */
  const handleRichCopy = async () => {
    try {
      if (
        typeof window !== "undefined" &&
        window.ClipboardItem &&
        navigator.clipboard?.write
      ) {
        const blobHtml = new Blob([signatureHtml], { type: "text/html" });
        const blobText = new Blob([signatureText], { type: "text/plain" });
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": blobHtml,
            "text/plain": blobText,
          }),
        ]);
        setHtmlCopyState("copied");
        setTimeout(() => setHtmlCopyState("idle"), 2500);
        return;
      }

      // Fallback — select the rendered preview and execCommand("copy").
      // Works in older Safari where ClipboardItem isn't available.
      if (previewRef.current) {
        const range = document.createRange();
        range.selectNodeContents(previewRef.current);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
        const ok = document.execCommand("copy");
        sel?.removeAllRanges();
        if (ok) {
          setHtmlCopyState("copied");
          setTimeout(() => setHtmlCopyState("idle"), 2500);
          return;
        }
      }
      setHtmlCopyState("error");
      setTimeout(() => setHtmlCopyState("idle"), 3000);
    } catch {
      setHtmlCopyState("error");
      setTimeout(() => setHtmlCopyState("idle"), 3000);
    }
  };

  const handlePlainCopy = async () => {
    try {
      await navigator.clipboard.writeText(signatureText);
      setTextCopyState("copied");
      setTimeout(() => setTextCopyState("idle"), 2500);
    } catch {
      setTextCopyState("error");
      setTimeout(() => setTextCopyState("idle"), 3000);
    }
  };

  const handleRawHtmlCopy = async () => {
    try {
      await navigator.clipboard.writeText(signatureHtml);
      setRawCopyState("copied");
      setTimeout(() => setRawCopyState("idle"), 2500);
    } catch {
      setRawCopyState("error");
      setTimeout(() => setRawCopyState("idle"), 3000);
    }
  };

  return (
    <main>
      <section className="bg-brand-50/50 pt-20 pb-12">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            LintPDF Email Signature
          </h1>
          <p className="text-lg text-slate-500">
            One-click copy for Mac Mail, Outlook, Gmail, and anything else that
            accepts rich-text paste.
          </p>
        </div>
      </section>

      <section className="py-12">
        <div className="mx-auto max-w-3xl px-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Preview
            </h2>
            <span className="text-xs text-slate-400">
              This is exactly what recipients will see.
            </span>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div
              ref={previewRef}
              // Render the signature using the same HTML users will paste.
              // Keeps the preview in sync with what Copy actually copies.
              dangerouslySetInnerHTML={{ __html: signatureHtml }}
            />
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleRichCopy}
              className="flex-1 rounded-xl bg-brand-900 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg"
            >
              {htmlCopyState === "copied"
                ? "✓ Copied — paste into Mac Mail"
                : htmlCopyState === "error"
                  ? "Copy failed — try another browser"
                  : "Copy for Mac Mail (rich)"}
            </button>
            <button
              type="button"
              onClick={handlePlainCopy}
              className="flex-1 rounded-xl border border-slate-300 bg-white py-3 text-sm font-semibold text-slate-700 transition-all hover:border-brand-400 hover:text-brand-700"
            >
              {textCopyState === "copied"
                ? "✓ Plain text copied"
                : textCopyState === "error"
                  ? "Copy failed"
                  : "Copy plain text"}
            </button>
          </div>
        </div>
      </section>

      <section className="pb-12">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-xl font-bold text-slate-900 mb-4">
            Install in Mac Mail
          </h2>
          <ol className="space-y-3 text-slate-700">
            <li className="flex gap-3">
              <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-900">
                1
              </span>
              <span>
                Open{" "}
                <strong>
                  Mail → Settings → Signatures
                </strong>{" "}
                (on older macOS:{" "}
                <strong>Mail → Preferences → Signatures</strong>).
              </span>
            </li>
            <li className="flex gap-3">
              <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-900">
                2
              </span>
              <span>
                Click the{" "}
                <strong className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">
                  +
                </strong>{" "}
                under the middle column and name it{" "}
                <em>&ldquo;LintPDF&rdquo;</em>.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-900">
                3
              </span>
              <span>
                <strong>Uncheck</strong> &ldquo;Always match my default message
                font&rdquo; at the bottom of the window — critical, or Mail
                will strip colors and the blue accent bar.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-900">
                4
              </span>
              <span>
                Hit{" "}
                <strong>Copy for Mac Mail (rich)</strong> above, click into the
                signature editor on the right, and paste with{" "}
                <strong className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">
                  ⌘V
                </strong>
                .
              </span>
            </li>
            <li className="flex gap-3">
              <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-900">
                5
              </span>
              <span>
                Drag the new signature onto your{" "}
                <strong>@lintpdf.com</strong> account in the left column, then
                pick it from the{" "}
                <strong>Choose Signature</strong> dropdown to set it as the
                default.
              </span>
            </li>
          </ol>

          <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <strong>If pasting looks flat:</strong> some Safari versions strip
            the table on paste. Refresh this page, hit Copy again, and paste
            directly — don&rsquo;t paste through an intermediate doc. If
            it&rsquo;s still flat, use the{" "}
            <button
              type="button"
              onClick={handleRawHtmlCopy}
              className="underline hover:text-amber-700"
            >
              {rawCopyState === "copied"
                ? "✓ HTML source copied"
                : "copy raw HTML source"}
            </button>
            {" "}and paste into a tool like MailMate or the Mail signature file
            at{" "}
            <code className="rounded bg-amber-100 px-1 font-mono text-xs">
              ~/Library/Mail/V10/MailData/Signatures/
            </code>
            .
          </div>
        </div>
      </section>

      <section className="pb-20">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-xl font-bold text-slate-900 mb-4">
            Other clients
          </h2>
          <ul className="space-y-2 text-slate-700">
            <li>
              <strong>Gmail (web):</strong> Settings → See all settings →
              Signature → create new → paste. Save at the bottom.
            </li>
            <li>
              <strong>Outlook (Mac):</strong> Outlook → Settings → Signatures
              → + → paste into the editor.
            </li>
            <li>
              <strong>Outlook (Windows):</strong> File → Options → Mail →
              Signatures → New → paste. Windows Outlook sometimes drops the
              left accent bar — if that happens, the rest of the layout still
              renders correctly.
            </li>
            <li>
              <strong>Superhuman / HEY / Fastmail:</strong> settings →
              signature → paste. All three honor the inline HTML.
            </li>
          </ul>
        </div>
      </section>
    </main>
  );
}
