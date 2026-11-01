/** Polling policy for run progress: steady while visible, slow when the tab is hidden, stops at terminal states. */

import type { ProgressResponse, ReportStatus } from "../types";

export const VISIBLE_INTERVAL_MS = 2000;
export const HIDDEN_INTERVAL_MS = 15000;
export const MAX_INTERVAL_MS = 8000;

export const isRunning = (status: ReportStatus) => status === "processing";

/** Delay before the next poll: backs off a little for long runs; `null` = stop. */
export function nextDelay(status: ReportStatus, visible: boolean, attempt: number): number | null {
  if (!isRunning(status)) return null;
  if (!visible) return HIDDEN_INTERVAL_MS;
  return Math.min(VISIBLE_INTERVAL_MS + Math.floor(attempt / 10) * 1000, MAX_INTERVAL_MS);
}

export interface PollDeps {
  fetchProgress: () => Promise<ProgressResponse>;
  onUpdate: (progress: ProgressResponse) => void;
  onError?: (error: unknown) => void;
  isVisible: () => boolean;
  sleep: (ms: number) => Promise<void>;
  signal: AbortSignal;
}

/** Polls until the run leaves `processing`, the signal aborts, or 5 consecutive requests fail. Returns the last progress. */
export async function pollProgress(deps: PollDeps, initial: ReportStatus = "processing"): Promise<ProgressResponse | null> {
  let status: ReportStatus = initial;
  let last: ProgressResponse | null = null;
  let attempt = 0;
  let failures = 0;
  while (!deps.signal.aborted) {
    const delay = nextDelay(status, deps.isVisible(), attempt);
    if (delay === null) break;
    await deps.sleep(delay);
    if (deps.signal.aborted) break;
    try {
      last = await deps.fetchProgress();
      failures = 0;
      status = last.status;
      deps.onUpdate(last);
    } catch (error) {
      failures += 1;
      deps.onError?.(error);
      if (failures >= 5) break;
    }
    attempt += 1;
  }
  return last;
}

export function progressPercent(p: { done?: number; total?: number } | undefined): number | null {
  if (!p || !p.total) return null;
  return Math.max(0, Math.min(100, Math.round(((p.done ?? 0) / p.total) * 100)));
}
