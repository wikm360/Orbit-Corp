"use client";

import { useEffect, useState } from "react";
import { authApi } from "@/features/auth/api/authApi";
import { QUOTA_WINDOW_LABEL, formatQuotaReset } from "@/shared/lib/errorMessages";
import type { QuotaWindow } from "@/shared/types";

type Notice = { exhausted: boolean; text: string };

const usd = (value: number) => value.toLocaleString("fa-IR", { minimumFractionDigits: 2, maximumFractionDigits: value < 1 ? 3 : 2 });

/** The tightest dollar-quota window that is exhausted or at 80% (only while the quota is enforced). */
function dollarNotice(windows: QuotaWindow[]): Notice | null {
  const exhausted = windows.find((w) => w.exhausted);
  if (exhausted) {
    const reset = formatQuotaReset(exhausted.resets_at);
    return { exhausted: true, text: `سقف مصرف ${QUOTA_WINDOW_LABEL[exhausted.name]} شما به پایان رسیده است${reset ? `؛ ${reset} صبر کنید` : ""}. در صورت نیاز با مدیر سیستم تماس بگیرید.` };
  }
  const near = windows.filter((w) => w.limit_usd).map((w) => ({ w, ratio: w.used_usd / (w.limit_usd ?? 1) })).filter((x) => x.ratio >= 0.8).sort((a, b) => b.ratio - a.ratio)[0];
  if (!near) return null;
  return { exhausted: false, text: `${Math.floor(near.ratio * 100).toLocaleString("fa-IR")}٪ از سقف مصرف ${QUOTA_WINDOW_LABEL[near.w.name]} شما (${usd(near.w.used_usd)} از ${usd(near.w.limit_usd ?? 0)} دلار) استفاده شده است.` };
}

/** Warns the signed-in user when a quota is nearly or fully used: the dollar windows (5 hours / 7 days / Jalali month) when the
 *  quota is enforced, else the legacy token limit. Fetched fresh: the persisted user can be stale. */
export function TokenQuotaBanner() {
  const [notice, setNotice] = useState<Notice | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [me, quota] = await Promise.all([authApi.me(), authApi.myQuota().catch(() => null)]);
        if (cancelled) return;
        const fromDollars = quota?.enforced && !quota.unlimited ? dollarNotice(quota.windows) : null;
        if (fromDollars) return setNotice(fromDollars);
        const limit = me.token_limit;
        const used = me.tokens_used ?? 0;
        if (!limit || used < limit * 0.8) return setNotice(null);
        setNotice(used >= limit
          ? { exhausted: true, text: "سقف مصرف توکن شما به پایان رسیده است؛ برای ادامه با مدیر سیستم تماس بگیرید." }
          : { exhausted: false, text: `بیش از ${Math.floor((used / limit) * 100).toLocaleString("fa-IR")}٪ از سقف مصرف توکن شما استفاده شده است.` });
      } catch { /* the banner is best-effort */ }
    };
    void load();
    const onVisible = () => { if (document.visibilityState === "visible") void load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => { cancelled = true; document.removeEventListener("visibilitychange", onVisible); };
  }, []);
  if (!notice) return null;
  return <p role="status" className={`mx-4 mt-3 rounded-xl p-3 text-xs ${notice.exhausted ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-900"}`}>{notice.text}</p>;
}
