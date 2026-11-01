"use client";

import { toFa } from "../lib/jalali";
import { progressPercent } from "../lib/polling";
import { STEP_LABELS } from "../lib/status";
import type { Progress } from "../types";
import { Card } from "./common";

export function ProgressCard({ progress }: { progress: Progress | undefined }) {
  const percent = progressPercent(progress);
  const step = progress?.step ? STEP_LABELS[progress.step] ?? progress.step : "در صف";
  return (
    <Card>
      <div role="status" aria-live="polite" className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-slate-800">{step}{progress?.message ? ` — ${progress.message}` : ""}</span>
          {percent !== null && <span className="text-slate-500">{toFa(percent)}٪</span>}
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
          <div className={percent === null ? "h-full w-1/3 animate-pulse rounded-full bg-teal-500" : "h-full rounded-full bg-teal-600 transition-all"} style={percent === null ? undefined : { width: `${percent}%` }} />
        </div>
        <p className="text-xs text-slate-500">پردازش در سرور ادامه دارد؛ می‌توانید صفحه را ترک کنید و بعداً برگردید.</p>
      </div>
    </Card>
  );
}
