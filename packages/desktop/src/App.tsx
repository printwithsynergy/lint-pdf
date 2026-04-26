import { useEffect, useState, useCallback } from "react";
import { Layout } from "./components/Layout";
import { ThemeProvider } from "./components/ThemeProvider";
import { FolderList } from "./pages/FolderList";
import { FolderEdit } from "./pages/FolderEdit";
import { Onboarding } from "./pages/Onboarding";
import { Results } from "./pages/Results";
import { Settings } from "./pages/Settings";
import { ViewerPane } from "./components/viewer/ViewerPane";
import type {
  AppConfig,
  FolderConfig,
  JobResult,
  WatcherStatus,
} from "./lib/types";
import * as api from "./lib/tauri";

export type Page =
  | { kind: "folders" }
  | { kind: "folder-edit"; folder: FolderConfig; isNew: boolean }
  | { kind: "results" }
  | { kind: "settings" }
  | { kind: "viewer"; job: JobResult };

function isOnboarded(config: AppConfig): boolean {
  return Boolean(config.tenant_id) && Boolean(config.api_key);
}

export default function App() {
  const [page, setPage] = useState<Page>({ kind: "folders" });
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [jobs, setJobs] = useState<JobResult[]>([]);
  const [statuses, setStatuses] = useState<WatcherStatus[]>([]);

  const refreshConfig = useCallback(async () => {
    try {
      const cfg = await api.getConfig();
      setConfig(cfg);
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  }, []);

  const refreshJobs = useCallback(async () => {
    try {
      const recent = await api.getRecentJobs(200);
      setJobs(recent);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    }
  }, []);

  const refreshStatuses = useCallback(async () => {
    try {
      const s = await api.getWatcherStatuses();
      setStatuses(s);
    } catch (err) {
      console.error("Failed to load statuses:", err);
    }
  }, []);

  useEffect(() => {
    refreshConfig();
  }, [refreshConfig]);

  // Background services (jobs, watcher events) are only meaningful once
  // the user has finished Onboarding. Wiring them up earlier would
  // surface authentication failures before the user has a chance to
  // enter their API key.
  useEffect(() => {
    if (!config || !isOnboarded(config)) return;

    refreshJobs();
    refreshStatuses();

    const interval = setInterval(refreshStatuses, 3000);

    const unlistenJob = api.onJobUpdate((job) => {
      setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)]);
    });

    const unlistenStatus = api.onWatcherStatus((status) => {
      setStatuses((prev) =>
        prev.map((s) => (s.folder_id === status.folder_id ? status : s)),
      );
    });

    return () => {
      clearInterval(interval);
      unlistenJob.then((fn) => fn());
      unlistenStatus.then((fn) => fn());
    };
  }, [config, refreshJobs, refreshStatuses]);

  if (!config) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Loading…</p>
      </div>
    );
  }

  if (!isOnboarded(config)) {
    return (
      <ThemeProvider branding={config.tenant_branding}>
        <Onboarding
          config={config}
          onComplete={async (next) => {
            await api.saveConfig(next);
            setConfig(next);
          }}
        />
      </ThemeProvider>
    );
  }

  const activeCount = statuses.filter((s) => s.active).length;
  const processingCount = jobs.filter(
    (j) => j.status === "processing" || j.status === "queued",
  ).length;

  return (
    <ThemeProvider branding={config.tenant_branding}>
      <Layout
        page={page}
        onNavigate={setPage}
        activeCount={activeCount}
        processingCount={processingCount}
      >
        {page.kind === "folders" && (
          <FolderList
            config={config}
            statuses={statuses}
            jobs={jobs}
            onEdit={(folder) =>
              setPage({ kind: "folder-edit", folder, isNew: false })
            }
            onAdd={(folder) =>
              setPage({ kind: "folder-edit", folder, isNew: true })
            }
            onRefresh={refreshConfig}
            onRefreshStatuses={refreshStatuses}
          />
        )}
        {page.kind === "folder-edit" && (
          <FolderEdit
            folder={page.folder}
            isNew={page.isNew}
            onSave={async (folder) => {
              if (page.isNew) {
                await api.addFolder(folder);
              } else {
                await api.updateFolder(folder);
              }
              await refreshConfig();
              setPage({ kind: "folders" });
            }}
            onCancel={() => setPage({ kind: "folders" })}
            onDelete={async (id) => {
              await api.removeFolder(id);
              await refreshConfig();
              setPage({ kind: "folders" });
            }}
          />
        )}
        {page.kind === "results" && (
          <Results
            jobs={jobs}
            folders={config.folders}
            onClear={async () => {
              await api.clearHistory();
              setJobs([]);
            }}
            onOpenViewer={(job) => setPage({ kind: "viewer", job })}
          />
        )}
        {page.kind === "viewer" && (
          <ViewerPane
            job={page.job}
            onClose={() => setPage({ kind: "results" })}
          />
        )}
        {page.kind === "settings" && (
          <Settings
            config={config}
            onSave={async (updated) => {
              await api.saveConfig(updated);
              setConfig(updated);
            }}
            onChangeTenant={async () => {
              const cleared: AppConfig = {
                ...config,
                api_key: "",
                tenant_id: "",
                tenant_name: "",
                tenant_branding: null,
              };
              await api.saveConfig(cleared);
              setConfig(cleared);
              setPage({ kind: "folders" });
            }}
          />
        )}
      </Layout>
    </ThemeProvider>
  );
}
