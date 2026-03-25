"use client";

import { useState, useCallback, useRef } from "react";
import type { FormEvent, DragEvent } from "react";

type FormState = "idle" | "submitting" | "success" | "error";

interface SelectedFile {
  file: File;
  id: string;
}

const MAX_FILES = 5;
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

export default function TryItPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [state, setState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const toAdd: SelectedFile[] = [];
      for (const file of Array.from(newFiles)) {
        if (file.type !== "application/pdf") {
          setErrorMsg(
            `"${file.name}" is not a PDF. Only PDF files are accepted.`,
          );
          continue;
        }
        if (file.size > MAX_FILE_SIZE) {
          setErrorMsg(`"${file.name}" exceeds 50 MB limit.`);
          continue;
        }
        if (files.length + toAdd.length >= MAX_FILES) {
          setErrorMsg(`Maximum ${MAX_FILES} files allowed.`);
          break;
        }
        toAdd.push({ file, id: crypto.randomUUID() });
      }
      if (toAdd.length > 0) {
        setFiles((prev) => [...prev, ...toAdd]);
        setErrorMsg("");
      }
    },
    [files.length],
  );

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.length) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles],
  );

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setState("submitting");
      setErrorMsg("");

      if (files.length === 0) {
        setErrorMsg("Please add at least one PDF file.");
        setState("idle");
        return;
      }

      const formData = new FormData();
      formData.append("name", name.trim());
      formData.append("email", email.trim());
      formData.append("company", company.trim());
      formData.append("phone", phone.trim());
      formData.append("_hp_field", honeypot);
      for (const { file } of files) {
        formData.append("files", file);
      }

      try {
        const resp = await fetch("/api/try-it", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setErrorMsg(
            (data as { error?: string }).error ??
              "Something went wrong. Please try again.",
          );
          setState("error");
          return;
        }

        setState("success");
      } catch {
        setErrorMsg(
          "Network error. Please check your connection and try again.",
        );
        setState("error");
      }
    },
    [name, email, company, phone, honeypot, files],
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <main>
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h1 className="text-4xl font-bold text-slate-900 md:text-5xl mb-4">
            Got Messy PDFs?
            <br />
            <span className="bg-gradient-to-r from-brand-800 via-brand-600 to-brand-400 bg-clip-text text-transparent">
              We&rsquo;ll Sort Them Out.
            </span>
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            Upload your PDF files and our team will run a full preflight
            analysis — free of charge. We&rsquo;ll send you a detailed report
            with every issue we find.
          </p>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-xl px-6">
          <div className="rounded-2xl bg-slate-100/70 border border-slate-200/60 p-8">
            {state === "success" ? (
              <div className="rounded-2xl border border-brand-200 bg-brand-50/50 p-8 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
                  <svg
                    className="h-7 w-7 text-brand-700"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-2">
                  Files submitted!
                </h2>
                <p className="text-slate-500">
                  We&rsquo;ll review your files and send you a detailed
                  preflight report. Expect to hear from us within 1 business
                  day.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Honeypot */}
                <div className="absolute -left-[9999px]" aria-hidden="true">
                  <label htmlFor="try-hp">
                    Leave empty
                    <input
                      id="try-hp"
                      type="text"
                      tabIndex={-1}
                      autoComplete="off"
                      value={honeypot}
                      onChange={(e) => setHoneypot(e.target.value)}
                    />
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label
                      htmlFor="try-name"
                      className="block text-sm font-medium text-slate-700 mb-1"
                    >
                      Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="try-name"
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                      placeholder="Jane Smith"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="try-email"
                      className="block text-sm font-medium text-slate-700 mb-1"
                    >
                      Email <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="try-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                      placeholder="you@example.com"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label
                      htmlFor="try-company"
                      className="block text-sm font-medium text-slate-700 mb-1"
                    >
                      Company
                    </label>
                    <input
                      id="try-company"
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                      placeholder="Acme Print Co."
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="try-phone"
                      className="block text-sm font-medium text-slate-700 mb-1"
                    >
                      Phone
                    </label>
                    <input
                      id="try-phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 focus:outline-none"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>

                {/* File upload zone */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    PDF Files <span className="text-red-500">*</span>
                    <span className="text-slate-400 font-normal ml-1">
                      (max {MAX_FILES} files, 50 MB each)
                    </span>
                  </label>
                  <div
                    className={`relative rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                      dragActive
                        ? "border-brand-500 bg-brand-50"
                        : "border-slate-200 hover:border-brand-300 hover:bg-slate-50/50"
                    }`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                  >
                    <svg
                      className="mx-auto h-10 w-10 text-slate-300 mb-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    <p className="text-sm text-slate-500 mb-2">
                      Drag & drop PDFs here, or{" "}
                      <button
                        type="button"
                        className="text-brand-600 font-medium hover:text-brand-700 underline underline-offset-2"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        browse files
                      </button>
                    </p>
                    <p className="text-xs text-slate-400">PDF files only</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,application/pdf"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files?.length) {
                          addFiles(e.target.files);
                          e.target.value = "";
                        }
                      }}
                    />
                  </div>

                  {/* File list */}
                  {files.length > 0 && (
                    <ul className="mt-3 space-y-2">
                      {files.map(({ file, id }) => (
                        <li
                          key={id}
                          className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2"
                        >
                          <svg
                            className="h-5 w-5 text-red-500 shrink-0"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={1.5}
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <span className="text-sm text-slate-700 truncate flex-1">
                            {file.name}
                          </span>
                          <span className="text-xs text-slate-400 shrink-0">
                            {formatSize(file.size)}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeFile(id)}
                            className="text-slate-400 hover:text-red-500 transition-colors shrink-0"
                            aria-label={`Remove ${file.name}`}
                          >
                            <svg
                              className="h-4 w-4"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M6 18L18 6M6 6l12 12"
                              />
                            </svg>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {state === "error" && errorMsg && (
                  <p className="text-sm text-red-600">{errorMsg}</p>
                )}

                <button
                  type="submit"
                  disabled={state === "submitting"}
                  className="w-full rounded-xl bg-brand-900 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {state === "submitting"
                    ? "Uploading..."
                    : "Submit for Free Analysis"}
                </button>

                <p className="text-xs text-slate-400 text-center">
                  Your files are scanned for security and only used for
                  preflight analysis. We&rsquo;ll never share them.
                </p>
              </form>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
