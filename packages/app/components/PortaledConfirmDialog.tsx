"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { ConfirmDialog as PixieConfirmDialog } from "@thinkneverland/pixie-dust-ui";

type Props = React.ComponentProps<typeof PixieConfirmDialog>;

// Wraps the upstream ConfirmDialog in a portal that mounts to
// document.body. Fixes a long-standing bug where the dialog's
// fixed-positioned overlay gets trapped inside a positioned/transformed
// ancestor (DashboardShell, table containers) causing the backdrop to
// stop short of the viewport and the underlying page chrome to bleed
// through. Mounting directly under <body> guarantees the overlay covers
// the full viewport regardless of where the dialog is rendered in the
// component tree.
export function ConfirmDialog(props: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  if (!mounted) return null;
  return createPortal(<PixieConfirmDialog {...props} />, document.body);
}
