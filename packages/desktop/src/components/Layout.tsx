import type { ReactNode } from "react";
import { FolderOpen, ClipboardList, Settings, Activity } from "lucide-react";
import type { Page } from "../App";
import { ConnectivityPill } from "./ConnectivityPill";

interface LayoutProps {
  page: Page;
  onNavigate: (page: Page) => void;
  activeCount: number;
  processingCount: number;
  children: ReactNode;
}

const NAV_ITEMS: {
  kind: Page["kind"];
  label: string;
  icon: typeof FolderOpen;
}[] = [
  { kind: "folders", label: "Folders", icon: FolderOpen },
  { kind: "results", label: "Results", icon: ClipboardList },
  { kind: "settings", label: "Settings", icon: Settings },
];

export function Layout({
  page,
  onNavigate,
  activeCount,
  processingCount,
  children,
}: LayoutProps) {
  return (
    <div className="flex h-screen flex-col">
      {/* Title bar / header */}
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-brand-600" />
          <h1 className="text-sm font-semibold text-gray-900">
            LintPDF Hot Folders
          </h1>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {activeCount > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              {activeCount} watching
            </span>
          )}
          {processingCount > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              {processingCount} processing
            </span>
          )}
          {activeCount === 0 && processingCount === 0 && (
            <span className="text-gray-400">Idle</span>
          )}
          <ConnectivityPill />
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar nav */}
        <nav className="flex w-48 flex-col border-r border-gray-200 bg-gray-50 p-2">
          {NAV_ITEMS.map((item) => {
            const active =
              page.kind === item.kind ||
              (page.kind === "folder-edit" && item.kind === "folders");
            return (
              <button
                key={item.kind}
                onClick={() => onNavigate({ kind: item.kind } as Page)}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>

      {/* Status bar */}
      <footer className="border-t border-gray-200 bg-gray-50 px-4 py-1.5 text-xs text-gray-500">
        {activeCount} folder{activeCount !== 1 ? "s" : ""} active
        {processingCount > 0 &&
          ` · ${processingCount} file${processingCount !== 1 ? "s" : ""} processing`}
      </footer>
    </div>
  );
}
