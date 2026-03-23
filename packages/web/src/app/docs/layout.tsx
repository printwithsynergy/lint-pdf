import { DocsNav } from "@/components/DocsNav";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 pt-8 pb-16 lg:pt-16 lg:flex lg:gap-12">
      <DocsNav />
      <main className="min-w-0 flex-1 mt-6 lg:mt-0">{children}</main>
    </div>
  );
}
