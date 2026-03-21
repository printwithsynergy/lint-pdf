import { DocsNav } from "@/components/DocsNav";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-16 lg:flex lg:gap-12">
      <DocsNav />
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
