import type { LayerInfo } from "../../lib/types";

interface LayerPanelProps {
  layers: LayerInfo[];
  visibility: Record<number, boolean>;
  onChange: (ocgIndex: number, visible: boolean) => void;
}

export function LayerPanel({
  layers,
  visibility,
  onChange,
}: LayerPanelProps) {
  return (
    <div className="p-3 text-xs">
      <p className="mb-2 text-gray-500">
        Optional Content Groups (layers) declared in the PDF. Toggling
        here shows the user's intended visibility for each layer — the
        engine always renders the document's default state, so this
        panel doesn't re-render pages. Check the hosted viewer or an
        Acrobat-class tool if you need interactive layer isolation.
      </p>
      <ul className="space-y-1">
        {layers.map((layer) => {
          const on = visibility[layer.ocg_index] ?? layer.default_on;
          return (
            <li key={layer.ocg_index}>
              <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={(e) => onChange(layer.ocg_index, e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="flex-1 truncate" title={layer.name}>
                  {layer.name}
                </span>
                {!layer.default_on && (
                  <span className="text-[10px] uppercase text-gray-400">
                    off by default
                  </span>
                )}
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
