export function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="rounded-lg border border-slate-200 bg-brand-950 p-4 text-sm text-slate-300 overflow-x-auto leading-relaxed">
      <code>{children}</code>
    </pre>
  );
}
