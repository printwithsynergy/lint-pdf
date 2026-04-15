import type { ViewerAnnotation } from "../../lib/types";

interface AnnotationPanelProps {
  annotations: ViewerAnnotation[];
  onJump: (annotation: ViewerAnnotation) => void;
}

export function AnnotationPanel({
  annotations,
  onJump,
}: AnnotationPanelProps) {
  if (annotations.length === 0) {
    return (
      <div className="p-4 text-xs text-gray-500">No annotations on this job.</div>
    );
  }
  return (
    <ul className="divide-y divide-gray-100 text-xs">
      {annotations.map((a) => (
        <li
          key={a.id}
          onClick={() => onJump(a)}
          className="cursor-pointer px-3 py-2 hover:bg-gray-50"
        >
          <p className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded"
              style={{ backgroundColor: a.color ?? "#6b7280" }}
            />
            <span className="font-medium">{a.kind}</span>
            <span className="text-gray-400">· page {a.page_num}</span>
          </p>
          {a.text && (
            <p className="mt-1 whitespace-pre-wrap break-words text-gray-700">
              {a.text}
            </p>
          )}
          {a.author_email && (
            <p className="mt-1 text-[10px] text-gray-400">
              {a.author_email}
              {a.created_at
                ? ` · ${new Date(a.created_at).toLocaleString()}`
                : ""}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
