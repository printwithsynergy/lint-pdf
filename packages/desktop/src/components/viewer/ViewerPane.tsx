import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Loader,
  ZoomIn,
  ZoomOut,
  Maximize,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type {
  DensitometerResponse,
  JobResult,
  LayersResponse,
  PagesResponse,
  SeparationsResponse,
  TacRunsResponse,
  ViewerAnnotation,
  ViewerConfig,
  ViewerFinding,
} from "../../lib/types";
import {
  viewerAnnotations,
  viewerChannelTile,
  viewerConfig,
  viewerDensitometer,
  viewerFindings,
  viewerLayers,
  viewerPages,
  viewerSeparations,
  viewerTacHeatmap,
  viewerTacRuns,
  viewerTile,
  type OcgMask,
} from "../../lib/tauri";
import { PageCanvas } from "./PageCanvas";
import { FindingsPanel } from "./FindingsPanel";
import { ChannelPanel } from "./ChannelPanel";
import { TACPanel } from "./TACPanel";
import { LayerPanel } from "./LayerPanel";
import { AnnotationPanel } from "./AnnotationPanel";
import { DensitometerReadout } from "./DensitometerReadout";
import { PageThumbnails } from "./PageThumbnails";

interface ViewerPaneProps {
  job: JobResult;
  onClose: () => void;
}

type SidePanel =
  | "findings"
  | "channels"
  | "tac"
  | "layers"
  | "annotations"
  | "densitometer";

const DEFAULT_DPI = 150;
const HI_DPI = 300;

export function ViewerPane({ job, onClose }: ViewerPaneProps) {
  const apiJobId = job.job_id;

  const [pages, setPages] = useState<PagesResponse | null>(null);
  const [config, setConfig] = useState<ViewerConfig | null>(null);
  const [findings, setFindings] = useState<ViewerFinding[]>([]);
  const [separations, setSeparations] = useState<SeparationsResponse | null>(
    null,
  );
  const [layers, setLayers] = useState<LayersResponse | null>(null);
  const [annotations, setAnnotations] = useState<ViewerAnnotation[]>([]);

  const [loadError, setLoadError] = useState<string | null>(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [currentImagePath, setCurrentImagePath] = useState<string | null>(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const [activePanel, setActivePanel] = useState<SidePanel>("findings");
  const [selectedFinding, setSelectedFinding] = useState<number | null>(null);

  // Channel isolation
  const [activeChannel, setActiveChannel] = useState<string | null>(null);
  const [channelImagePath, setChannelImagePath] = useState<string | null>(null);

  // TAC
  const [tacEnabled, setTacEnabled] = useState(false);
  const [tacLimit, setTacLimit] = useState(300);
  const [tacImagePath, setTacImagePath] = useState<string | null>(null);
  const [tacRuns, setTacRuns] = useState<TacRunsResponse | null>(null);

  // Layer toggles. We keep the user's intended visibility per OCG
  // index; the effective mask is computed against the PDF's declared
  // defaults (``layer.default_on``) so re-showing a layer that was
  // off-by-default produces ``on=[idx]``, hiding a layer that was
  // on-by-default produces ``off=[idx]``. Default matches = empty
  // mask = Phase 4 cache hit.
  const [layerVisibility, setLayerVisibility] = useState<Record<number, boolean>>(
    {},
  );

  // Densitometer
  const [densSample, setDensSample] = useState<DensitometerResponse | null>(
    null,
  );
  const [densLoading, setDensLoading] = useState(false);
  const [densError, setDensError] = useState<string | null>(null);

  // Zoom determines DPI: ≤1.5× uses 150 DPI, >1.5× uses 300 DPI for
  // crisp zoomed detail without spamming 600 DPI requests.
  const effectiveDpi = zoom > 1.5 ? HI_DPI : DEFAULT_DPI;

  // Compute the OCG override mask from user toggles vs PDF defaults.
  // `useMemo` with a stable string key avoids triggering fetch
  // effects on every render when the mask is unchanged.
  const ocgMask = useMemo<OcgMask>(() => {
    if (!layers) return { on: [], off: [] };
    const on: number[] = [];
    const off: number[] = [];
    for (const layer of layers.layers) {
      const userOn = layerVisibility[layer.ocg_index] ?? layer.default_on;
      if (userOn && !layer.default_on) on.push(layer.ocg_index);
      else if (!userOn && layer.default_on) off.push(layer.ocg_index);
    }
    on.sort((a, b) => a - b);
    off.sort((a, b) => a - b);
    return { on, off };
  }, [layers, layerVisibility]);

  /** Serialized form used as a stable dependency for fetch effects
   * — React's default reference equality would re-fetch every
   * render otherwise. */
  const ocgKey = `${ocgMask.on.join(",")}|${ocgMask.off.join(",")}`;

  // Keep a ref so that page-fetch effects can detect staleness.
  const fetchTokenRef = useRef(0);

  // ── Initial load ─────────────────────────────────────────

  useEffect(() => {
    if (!apiJobId) {
      setLoadError("Job has no engine id yet.");
      return;
    }
    let cancelled = false;

    async function load() {
      setLoadError(null);
      const results = await Promise.allSettled([
        viewerPages(apiJobId!),
        viewerConfig(apiJobId!),
        viewerFindings(apiJobId!),
      ]);
      if (cancelled) return;

      const [pagesRes, configRes, findingsRes] = results;
      if (pagesRes.status === "rejected") {
        setLoadError(`Could not load pages: ${String(pagesRes.reason)}`);
        return;
      }
      setPages(pagesRes.value);
      if (configRes.status === "fulfilled") setConfig(configRes.value);
      if (findingsRes.status === "fulfilled") setFindings(findingsRes.value);

      // These three are feature-gated so we don't bark on a tenant
      // without them.
      viewerSeparations(apiJobId!)
        .then((s) => {
          if (!cancelled) setSeparations(s);
        })
        .catch(() => {});
      viewerLayers(apiJobId!)
        .then((l) => {
          if (!cancelled) {
            setLayers(l);
            const initial: Record<number, boolean> = {};
            for (const layer of l.layers) {
              initial[layer.ocg_index] = layer.default_on;
            }
            setLayerVisibility(initial);
          }
        })
        .catch(() => {});
      viewerAnnotations(apiJobId!)
        .then((a) => {
          if (!cancelled) setAnnotations(a);
        })
        .catch(() => {});
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [apiJobId]);

  // ── Page raster fetch ────────────────────────────────────

  useEffect(() => {
    if (!apiJobId || !pages) return;
    const token = ++fetchTokenRef.current;
    setPageLoading(true);
    setPageError(null);
    viewerTile(apiJobId, currentPage, effectiveDpi, ocgMask)
      .then((r) => {
        if (token !== fetchTokenRef.current) return; // superseded
        setCurrentImagePath(r.path);
      })
      .catch((e: unknown) => {
        if (token !== fetchTokenRef.current) return;
        setPageError(String(e));
        setCurrentImagePath(null);
      })
      .finally(() => {
        if (token === fetchTokenRef.current) setPageLoading(false);
      });
    // `ocgKey` is the serialized mask; keeps the effect stable when
    // the mask object identity changes but the values don't.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiJobId, pages, currentPage, effectiveDpi, ocgKey]);

  // ── Channel overlay fetch ────────────────────────────────

  useEffect(() => {
    if (!apiJobId || !activeChannel) {
      setChannelImagePath(null);
      return;
    }
    let cancelled = false;
    viewerChannelTile(apiJobId, currentPage, activeChannel, effectiveDpi, ocgMask)
      .then((r) => {
        if (!cancelled) setChannelImagePath(r.path);
      })
      .catch(() => {
        if (!cancelled) setChannelImagePath(null);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiJobId, activeChannel, currentPage, effectiveDpi, ocgKey]);

  // ── TAC heatmap + runs fetch ─────────────────────────────

  useEffect(() => {
    if (!apiJobId || !tacEnabled) {
      setTacImagePath(null);
      setTacRuns(null);
      return;
    }
    let cancelled = false;
    viewerTacHeatmap(apiJobId, currentPage, effectiveDpi, tacLimit, ocgMask)
      .then((r) => {
        if (!cancelled) setTacImagePath(r.path);
      })
      .catch(() => {
        if (!cancelled) setTacImagePath(null);
      });
    viewerTacRuns(apiJobId, currentPage, effectiveDpi, tacLimit)
      .then((r) => {
        if (!cancelled) setTacRuns(r);
      })
      .catch(() => {
        if (!cancelled) setTacRuns(null);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiJobId, tacEnabled, currentPage, effectiveDpi, tacLimit, ocgKey]);

  // ── Helpers ──────────────────────────────────────────────

  const currentPageInfo = useMemo(
    () => pages?.pages.find((p) => p.page_num === currentPage) ?? null,
    [pages, currentPage],
  );

  const pageFindings = useMemo(
    () => findings.filter((f) => f.page_num === currentPage),
    [findings, currentPage],
  );

  const pageAnnotations = useMemo(
    () => annotations.filter((a) => a.page_num === currentPage),
    [annotations, currentPage],
  );

  const jumpToFinding = useCallback(
    (idx: number) => {
      const f = findings[idx];
      if (!f) return;
      if (f.page_num && f.page_num !== currentPage) {
        setCurrentPage(f.page_num);
      }
      setSelectedFinding(idx);
    },
    [findings, currentPage],
  );

  const jumpToAnnotation = useCallback(
    (a: ViewerAnnotation) => {
      if (a.page_num !== currentPage) setCurrentPage(a.page_num);
    },
    [currentPage],
  );

  async function handleProbe(x: number, y: number) {
    if (!apiJobId) return;
    setDensLoading(true);
    setDensError(null);
    setActivePanel("densitometer");
    try {
      const res = await viewerDensitometer(
        apiJobId,
        currentPage,
        x,
        y,
        HI_DPI, // probes always sample at 300 DPI for finer geometry
        tacLimit,
      );
      setDensSample(res);
    } catch (e: unknown) {
      setDensError(String(e));
      setDensSample(null);
    } finally {
      setDensLoading(false);
    }
  }

  // ── Render ───────────────────────────────────────────────

  if (!apiJobId) {
    return (
      <div className="p-6">
        <button onClick={onClose} className="btn-secondary text-xs mb-4">
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </button>
        <p className="text-sm text-red-600">
          This job hasn't been submitted to the engine yet.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-gray-200 bg-white px-3 py-2">
        <button
          onClick={onClose}
          className="btn-secondary text-xs"
          title="Close viewer"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </button>
        <div className="flex-1 truncate font-mono text-xs text-gray-600">
          {job.file_name}
        </div>

        {pages && (
          <div className="flex items-center gap-1 text-xs text-gray-600">
            <button
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
              title="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span>
              <input
                type="number"
                min={1}
                max={pages.page_count}
                value={currentPage}
                onChange={(e) => {
                  const n = parseInt(e.target.value, 10);
                  if (!Number.isNaN(n)) {
                    setCurrentPage(Math.max(1, Math.min(pages.page_count, n)));
                  }
                }}
                className="w-12 rounded border border-gray-200 px-1 text-center text-xs"
              />{" "}
              / {pages.page_count}
            </span>
            <button
              disabled={currentPage >= pages.page_count}
              onClick={() =>
                setCurrentPage((p) => Math.min(pages.page_count, p + 1))
              }
              className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.25, z / 1.25))}
            className="rounded p-1 hover:bg-gray-100"
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="w-10 text-center text-xs text-gray-600">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(8, z * 1.25))}
            className="rounded p-1 hover:bg-gray-100"
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="rounded p-1 hover:bg-gray-100"
            title="Reset zoom"
          >
            <Maximize className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Thumbnail strip */}
        {pages && pages.page_count > 1 && config?.enable_page_thumbnails !== false && (
          <PageThumbnails
            jobId={apiJobId}
            pages={pages.pages}
            currentPage={currentPage}
            onSelect={setCurrentPage}
          />
        )}

        {/* Page area */}
        <div className="flex min-h-0 flex-1 items-start justify-center overflow-auto bg-gray-100 p-4">
          {loadError ? (
            <p className="m-auto text-sm text-red-600">{loadError}</p>
          ) : !pages || !currentPageInfo ? (
            <div className="m-auto flex flex-col items-center gap-2 text-gray-400">
              <Loader className="h-5 w-5 animate-spin" />
              <span className="text-sm">Loading pages…</span>
            </div>
          ) : (
            <div>
              {pageError && (
                <p className="mb-2 text-xs text-red-600">{pageError}</p>
              )}
              {pageLoading && !currentImagePath && (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Loader className="h-4 w-4 animate-spin" />
                  Fetching page {currentPage}…
                </div>
              )}
              <PageCanvas
                imagePath={currentImagePath}
                page={currentPageInfo}
                renderedDpi={effectiveDpi}
                zoom={zoom}
                findings={pageFindings}
                selectedFinding={
                  selectedFinding !== null
                    ? pageFindings.indexOf(findings[selectedFinding])
                    : null
                }
                tacRuns={tacEnabled && tacRuns ? tacRuns.runs : []}
                annotations={pageAnnotations}
                onProbe={handleProbe}
                overlayImagePath={
                  tacEnabled ? tacImagePath : activeChannel ? channelImagePath : null
                }
                overlayOpacity={tacEnabled ? 0.5 : 0.7}
              />
            </div>
          )}
        </div>

        {/* Side tabs */}
        <aside className="flex w-80 shrink-0 flex-col border-l border-gray-200 bg-white">
          <nav className="flex gap-1 border-b border-gray-100 px-2 py-1 text-[11px] font-medium">
            <PanelTab
              id="findings"
              label={`Findings${findings.length ? ` (${findings.length})` : ""}`}
              active={activePanel}
              setActive={setActivePanel}
            />
            {config?.enable_separations !== false && separations && (
              <PanelTab
                id="channels"
                label="Channels"
                active={activePanel}
                setActive={setActivePanel}
              />
            )}
            {config?.enable_tac_heatmap !== false && (
              <PanelTab
                id="tac"
                label="TAC"
                active={activePanel}
                setActive={setActivePanel}
              />
            )}
            {config?.enable_layers !== false && layers && layers.layers.length > 0 && (
              <PanelTab
                id="layers"
                label="Layers"
                active={activePanel}
                setActive={setActivePanel}
              />
            )}
            {annotations.length > 0 && (
              <PanelTab
                id="annotations"
                label={`Notes (${annotations.length})`}
                active={activePanel}
                setActive={setActivePanel}
              />
            )}
            <PanelTab
              id="densitometer"
              label="Probe"
              active={activePanel}
              setActive={setActivePanel}
            />
          </nav>

          <div className="min-h-0 flex-1 overflow-auto">
            {activePanel === "findings" && (
              <FindingsPanel
                findings={findings}
                selectedIdx={selectedFinding}
                onSelect={jumpToFinding}
                currentPage={currentPage}
              />
            )}
            {activePanel === "channels" && separations && (
              <ChannelPanel
                separations={separations}
                activeChannel={activeChannel}
                onChange={setActiveChannel}
              />
            )}
            {activePanel === "tac" && (
              <TACPanel
                enabled={tacEnabled}
                tacLimit={tacLimit}
                onToggle={setTacEnabled}
                onLimitChange={setTacLimit}
                runs={tacRuns?.runs ?? []}
              />
            )}
            {activePanel === "layers" && layers && (
              <LayerPanel
                layers={layers.layers}
                visibility={layerVisibility}
                onChange={(idx, visible) =>
                  setLayerVisibility((prev) => ({ ...prev, [idx]: visible }))
                }
              />
            )}
            {activePanel === "annotations" && (
              <AnnotationPanel
                annotations={annotations}
                onJump={jumpToAnnotation}
              />
            )}
            {activePanel === "densitometer" && (
              <DensitometerReadout
                sample={densSample}
                loading={densLoading}
                error={densError}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function PanelTab({
  id,
  label,
  active,
  setActive,
}: {
  id: SidePanel;
  label: string;
  active: SidePanel;
  setActive: (id: SidePanel) => void;
}) {
  const isActive = active === id;
  return (
    <button
      onClick={() => setActive(id)}
      className={`rounded px-2 py-1 ${
        isActive
          ? "bg-brand-50 text-brand-700"
          : "text-gray-500 hover:bg-gray-100"
      }`}
    >
      {label}
    </button>
  );
}
