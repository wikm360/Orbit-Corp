"use client";

import { useEffect, useRef } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { pollProgress } from "../lib/polling";
import type { ProgressResponse } from "../types";

/** A sleep that ends early when the tab becomes visible again, so a hidden tab (slow polling) refreshes as soon as you return. */
function visibilityAwareSleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => { clearTimeout(timer); document.removeEventListener("visibilitychange", onVisible); signal.removeEventListener("abort", done); resolve(); };
    const onVisible = () => { if (document.visibilityState === "visible") done(); };
    const timer = setTimeout(done, ms);
    document.addEventListener("visibilitychange", onVisible);
    signal.addEventListener("abort", done, { once: true });
  });
}

/** Polls `GET /progress` while `active` (never a WebSocket). `onSettled` fires once the run leaves `processing`. */
export function useRunProgress(reportId: string, active: boolean, onUpdate: (p: ProgressResponse) => void, onSettled: (p: ProgressResponse | null) => void) {
  const handlers = useRef({ onUpdate, onSettled });
  useEffect(() => { handlers.current = { onUpdate, onSettled }; });
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void pollProgress({
      fetchProgress: () => volumeReportApi.progress(reportId),
      onUpdate: (p) => handlers.current.onUpdate(p),
      isVisible: () => document.visibilityState === "visible",
      sleep: (ms) => visibilityAwareSleep(ms, controller.signal),
      signal: controller.signal,
    }).then((last) => { if (!controller.signal.aborted) handlers.current.onSettled(last); });
    return () => controller.abort();
  }, [reportId, active]);
}
