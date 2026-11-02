"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { toFa } from "../lib/jalali";
import type { ActivityItem, ActivityKind, Progress } from "../types";
import { Card } from "./common";

const KIND_STYLE: Record<ActivityKind, { dot: string; text: string; icon: string }> = {
  info: { dot: "bg-slate-300", text: "text-slate-600", icon: "•" },
  step: { dot: "bg-teal-500", text: "text-slate-800", icon: "›" },
  success: { dot: "bg-emerald-500", text: "text-emerald-800", icon: "✓" },
  warn: { dot: "bg-amber-500", text: "text-amber-900", icon: "!" },
  error: { dot: "bg-rose-500", text: "text-rose-800", icon: "✕" },
  question: { dot: "bg-violet-500", text: "text-violet-900", icon: "؟" },
};

const clock = (iso: string) => new Date(iso).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const day = (iso: string) => new Date(iso).toLocaleDateString("fa-IR", { month: "long", day: "numeric" });

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);
  return now;
}

function ago(seconds: number) {
  if (seconds < 60) return `${toFa(seconds)} ثانیه`;
  const m = Math.floor(seconds / 60);
  return m < 60 ? `${toFa(m)} دقیقه` : `${toFa(Math.floor(m / 60))} ساعت و ${toFa(m % 60)} دقیقه`;
}

/** Chronological log (oldest first, newest at the bottom) of what the report jobs did. Fed from the server, so it is the same
 *  every time the page opens; while a job runs it shows what the job is waiting on. */
export function ActivityPanel({ items, loaded, processing, progress }: { items: ActivityItem[]; loaded: boolean; processing: boolean; progress?: Progress }) {
  const now = useNow(processing);
  const bottom = useRef<HTMLLIElement>(null);
  const stick = useRef(true);
  const box = useRef<HTMLDivElement>(null);

  const attempts = useMemo(() => [...new Set(items.map((i) => i.attempt))], [items]);
  const last = items[items.length - 1];
  const idle = processing && last ? Math.max(0, Math.round((now - new Date(last.created_at).getTime()) / 1000)) : 0;
  const waitingOnModel = processing && progress?.step === "agent" && progress.agent_step;

  useEffect(() => {
    if (processing && stick.current) bottom.current?.scrollIntoView({ block: "nearest" });
  }, [items.length, processing]);

  return (
    <Card title="گزارش فعالیت">
      {!loaded ? (
        <p className="text-sm text-slate-500">در حال بارگذاری…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">{processing ? "کار در صف است و هنوز شروع نشده…" : "هنوز فعالیتی ثبت نشده است."}</p>
      ) : (
        <div
          ref={box}
          className="max-h-[28rem] overflow-y-auto pe-1"
          onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48; }}
        >
          <ol className="space-y-0.5">
            {items.map((item, index) => {
              const style = KIND_STYLE[item.kind] ?? KIND_STYLE.info;
              const startsAttempt = index === 0 || items[index - 1]?.attempt !== item.attempt;
              return (
                <li key={item.id}>
                  {startsAttempt && (attempts.length > 1 || index > 0) && (
                    <p className="my-2 border-t border-slate-100 pt-2 text-[11px] font-medium text-slate-400">اجرای {toFa(item.attempt)} — {day(item.created_at)}</p>
                  )}
                  <div className="flex items-start gap-2 py-1">
                    <span aria-hidden="true" className={`mt-1.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white ${style.dot}`}>{style.icon}</span>
                    <p className={`min-w-0 flex-1 text-sm leading-6 ${style.text}`}>{item.title}</p>
                    <time dateTime={item.created_at} className="shrink-0 pt-1 text-[11px] text-slate-400">{clock(item.created_at)}</time>
                  </div>
                </li>
              );
            })}
            {processing && (
              <li ref={bottom} role="status" aria-live="polite" className="flex items-start gap-2 py-1">
                <span aria-hidden="true" className="mt-1.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-teal-200 border-t-teal-600" />
                <p className="text-sm leading-6 text-teal-800">
                  {waitingOnModel ? `در انتظار پاسخ مدل — گام ${toFa(progress?.agent_step ?? 0)} از ${toFa(progress?.max_steps ?? 0)}` : "در حال انجام…"}
                  {idle >= 15 && <span className="ms-2 text-xs text-slate-400">({ago(idle)} از آخرین فعالیت)</span>}
                </p>
              </li>
            )}
          </ol>
        </div>
      )}
      {processing && idle >= 600 && <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">بیش از ۱۰ دقیقه است فعالیت تازه‌ای ثبت نشده؛ ممکن است مدل کند باشد یا کار متوقف شده باشد.</p>}
    </Card>
  );
}
