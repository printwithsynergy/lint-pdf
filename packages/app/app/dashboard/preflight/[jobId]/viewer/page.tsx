"use client";

import { useParams } from "next/navigation";
import { PdfViewer } from "@/components/viewer";

export default function ViewerPage() {
  const params = useParams<{ jobId: string }>();

  if (!params.jobId) {
    return <div className="p-8 text-destructive">Missing job ID</div>;
  }

  return <PdfViewer jobId={params.jobId} />;
}
