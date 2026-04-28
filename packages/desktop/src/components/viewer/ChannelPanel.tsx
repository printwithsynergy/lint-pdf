import type { SeparationsResponse } from "../../lib/types";

interface ChannelPanelProps {
  separations: SeparationsResponse;
  activeChannel: string | null;
  onChange: (channel: string | null) => void;
}

/** Visual hint for process channels. Spot channels render as grey
 * swatches since the engine doesn't give us a color hint. */
const PROCESS_SWATCH: Record<string, string> = {
  Cyan: "bg-cyan-400",
  Magenta: "bg-fuchsia-500",
  Yellow: "bg-yellow-300",
  Black: "bg-neutral-800",
};

export function ChannelPanel({
  separations,
  activeChannel,
  onChange,
}: ChannelPanelProps) {
  return (
    <div className="p-3 text-xs">
      <p className="mb-2 text-gray-500">
        Isolate one separation as a grayscale overlay. Useful for spotting
        registration issues or over-inked regions per channel.
      </p>
      <ul className="space-y-1">
        <li>
          <button
            onClick={() => onChange(null)}
            className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${
              activeChannel === null
                ? "bg-brand-50 text-brand-700"
                : "hover:bg-gray-50"
            }`}
          >
            <span className="h-3 w-3 rounded border border-gray-300 bg-white" />
            All channels (composite)
          </button>
        </li>
        {separations.channels.map((c) => {
          const swatch =
            PROCESS_SWATCH[c.name] ?? "bg-gray-300 border border-gray-400";
          const isActive = activeChannel === c.name;
          return (
            <li key={c.name}>
              <button
                onClick={() => onChange(c.name)}
                className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "hover:bg-gray-50"
                }`}
              >
                <span className={`h-3 w-3 rounded ${swatch}`} />
                <span className="flex-1 truncate" title={c.name}>
                  {c.name}
                </span>
                {c.type === "spot" && (
                  <span className="text-[10px] uppercase text-gray-400">
                    spot
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
