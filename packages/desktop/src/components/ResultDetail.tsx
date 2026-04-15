import { useEffect, useState } from "react";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  X,
  Copy,
  Link as LinkIcon,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import type {
  AiInterpretation,
  ConnectivityStatus,
  JobResult,
  ShareLinks,
} from "../lib/types";
import {
  getAiInterpretation,
  getConnectivityStatus,
  mintShareLink,
  onConnectivityChange,
  openViewerWindow,
} from "../lib/tauri";

interface ResultDetailProps {
  job: JobResult;
  onClose: () => void;
  onJobUpdate?: (job: JobResult) => void;
}

type ReportFormat = "html" | "pdf" | "json" | "xml" | "annotated_pdf";

const FORMAT_LABELS: Record<ReportFormat, string> = {
  html: "HTML",
  pdf: "PDF",
  json: "JSON",
  xml: "XML",
  annotated_pdf: "Annotated PDF",
};

export function ResultDetail({ job, onClose, onJobUpdate }: ResultDetailProps) {
  const [links, setLinks] = useState<ShareLinks>(job.share_links ?? {});
  const [busy, setBusy] = useState<ReportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<ReportFormat | null>(null);

  const [interpretation, setInterpretation] = useState<AiInterpretation | null>(
    null,
  );
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const [viewerBusy, setViewerBusy] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);

  const [online, setOnline] = useState(true);
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    getConnectivityStatus()
      .then((s) => {
        if (!cancelled) setOnline(s.online);
      })
      .catch(() => {});
    onConnectivityChange((s: ConnectivityStatus) => {
      if (!cancelled) setOnline(s.online);
    }).then((fn) => {
      unlisten = fn;
    });
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  const canShare =
    !!job.job_id && (job.status === "passed" || job.status === "failed");
  const canInterpret = canShare && online;
  // "Open viewer" needs either a cached HTML link (works offline, browser
  // will show its offline page) OR online + job.job_id so we can mint one.
  const hasCachedHtml = !!links.html;
  const canOpenViewer = canShare && (hasCachedHtml || online);

  async function handleOpenViewer() {
    if (!job.job_id || viewerBusy) return;
    setViewerBusy(true);
    setViewerError(null);
    try {
      let url = links.html;
      if (!url) {
        const merged = await mintShareLink(job.id, job.job_id, ["html"]);
        setLinks(merged);
        url = merged.html;
        onJobUpdate?.({ ...job, share_links: merged });
      }
      if (!url) {
        throw new Error("No viewer URL available");
      }
      await openViewerWindow(url, job.file_name);
    } catch (e: unknown) {
      setViewerError(String(e));
    } finally {
      setViewerBusy(false);
    }
  }

  async function handleInterpret() {
    if (!job.job_id || aiBusy) return;
    setAiBusy(true);
    setAiError(null);
    try {
      const result = await getAiInterpretation(job.job_id);
      setInterpretation(result);
    } catch (e: unknown) {
      setAiError(String(e));
    } finally {
      setAiBusy(false);
    }
  }

  async function handleMint(format: ReportFormat) {
    if (!job.job_id || busy) return;
    setBusy(format);
    setError(null);
    try {
      const merged = await mintShareLink(job.id, job.job_id, [format]);
      setLinks(merged);
      onJobUpdate?.({ ...job, share_links: merged });
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function handleCopy(format: ReportFormat, url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(format);
      setTimeout(() => setCopied((c) => (c === format ? null : c)), 1500);
    } catch {
      // clipboard may be unavailable in some webviews — fall back to prompt.
      window.prompt("Copy link:", url);
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-gray-400" />
          <div>
            <h3 className="text-sm font-semibold font-mono">{job.file_name}</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Job ID: {job.job_id || "N/A"}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="label">Status</span>
          <div className="flex items-center gap-1.5">
            {job.status === "passed" && (
              <CheckCircle className="h-4 w-4 text-green-600" />
            )}
            {job.status === "failed" && (
              <XCircle className="h-4 w-4 text-red-600" />
            )}
            {job.status === "error" && (
              <AlertTriangle className="h-4 w-4 text-amber-600" />
            )}
            <span className="capitalize">{job.status}</span>
          </div>
        </div>
        <div>
          <span className="label">Submitted</span>
          <p className="text-xs">
            {job.submitted_at
              ? new Date(job.submitted_at).toLocaleString()
              : "—"}
          </p>
        </div>
        {job.completed_at && (
          <div>
            <span className="label">Completed</span>
            <p className="text-xs">
              {new Date(job.completed_at).toLocaleString()}
            </p>
          </div>
        )}
        {job.routed_to && (
          <div>
            <span className="label">Routed to</span>
            <p className="text-xs font-mono truncate">{job.routed_to}</p>
          </div>
        )}
      </div>

      {job.summary && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <span className="label">Findings</span>
          <div className="flex items-center gap-6 mt-1">
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.error_count > 0 ? "text-red-600" : "text-gray-300"}`}
              >
                {job.summary.error_count}
              </p>
              <p className="text-xs text-gray-500">Error</p>
            </div>
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.warning_count > 0 ? "text-amber-600" : "text-gray-300"}`}
              >
                {job.summary.warning_count}
              </p>
              <p className="text-xs text-gray-500">Warning</p>
            </div>
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.advisory_count > 0 ? "text-blue-600" : "text-gray-300"}`}
              >
                {job.summary.advisory_count}
              </p>
              <p className="text-xs text-gray-500">Advisory</p>
            </div>
          </div>
        </div>
      )}

      {canShare && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <button
            onClick={() => void handleOpenViewer()}
            disabled={!canOpenViewer || viewerBusy}
            className="btn-primary text-xs w-full mb-3"
            title={
              online
                ? "Open the hosted viewer in a new window"
                : hasCachedHtml
                  ? "Open the cached viewer link (will show the browser's offline page if still disconnected)"
                  : "Offline — viewer unavailable. Reconnect to mint a share link."
            }
          >
            <ExternalLink className="h-3.5 w-3.5" />
            {viewerBusy ? "Opening…" : "Open viewer"}
          </button>
          {viewerError && (
            <p className="mb-2 text-xs text-red-600 whitespace-pre-wrap">
              {viewerError}
            </p>
          )}
          <div className="flex items-center gap-1.5">
            <LinkIcon className="h-3.5 w-3.5 text-gray-400" />
            <span className="label !mb-0">Share</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Generate tokenised report URLs. Branding is frozen at mint time.
          </p>
          <div className="mt-2 space-y-1.5">
            {(Object.keys(FORMAT_LABELS) as ReportFormat[]).map((format) => {
              const url = links[format];
              const isBusy = busy === format;
              return (
                <div key={format} className="flex items-center gap-2 text-xs">
                  <span className="w-10 font-mono text-gray-500">
                    {FORMAT_LABELS[format]}
                  </span>
                  {url ? (
                    <>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 truncate text-brand-600 hover:underline"
                        title={url}
                      >
                        {url}
                      </a>
                      <button
                        onClick={() => void handleCopy(format, url)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        title="Copy link"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      {copied === format && (
                        <span className="text-green-600">Copied</span>
                      )}
                    </>
                  ) : (
                    <button
                      onClick={() => void handleMint(format)}
                      disabled={isBusy}
                      className="btn-secondary text-xs py-1"
                    >
                      {isBusy ? "Minting…" : "Mint link"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
          {error && (
            <p className="mt-2 text-xs text-red-600 whitespace-pre-wrap">
              {error}
            </p>
          )}
        </div>
      )}

      {canInterpret && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-violet-500" />
              <span className="label !mb-0">AI interpretation</span>
            </div>
            {!interpretation && (
              <button
                onClick={() => void handleInterpret()}
                disabled={aiBusy}
                className="btn-secondary text-xs py-1"
              >
                {aiBusy ? "Asking…" : "Interpret"}
              </button>
            )}
          </div>
          {aiError && (
            <p className="mt-1 text-xs text-amber-600">{aiError}</p>
          )}
          {interpretation && (
            <div className="mt-2 space-y-2">
              {interpretation.summary && (
                <p className="text-xs leading-relaxed text-gray-700 whitespace-pre-wrap">
                  {interpretation.summary}
                </p>
              )}
              {interpretation.interpretations.map((item, idx) => (
                <div
                  key={item.inspection_id ?? idx}
                  className="rounded border border-gray-100 p-2"
                >
                  {item.explanation && (
                    <p className="text-xs text-gray-700">{item.explanation}</p>
                  )}
                  {item.why_it_matters && (
                    <p className="mt-1 text-xs text-gray-500">
                      <span className="font-medium">Why it matters: </span>
                      {item.why_it_matters}
                    </p>
                  )}
                  {item.suggestion && (
                    <p className="mt-1 text-xs text-violet-700">
                      <span className="font-medium">Suggestion: </span>
                      {item.suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {job.error_message && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 text-xs text-red-700">
          <p className="font-medium">Error</p>
          <p className="mt-1">{job.error_message}</p>
        </div>
      )}
    </div>
  );
}
