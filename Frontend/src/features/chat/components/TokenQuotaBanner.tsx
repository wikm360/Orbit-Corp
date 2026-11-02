"use client";

import { useEffect, useState } from "react";
import { authApi } from "@/features/auth/api/authApi";

/** Warns the signed-in user when their token quota is nearly or fully used (fetched fresh: the persisted user can be stale). */
export function TokenQuotaBanner() {
  const [quota, setQuota] = useState<{ limit: number; used: number } | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = () => authApi.me().then((me) => {
      if (!cancelled) setQuota(me.token_limit ? { limit: me.token_limit, used: me.tokens_used ?? 0 } : null);
    }).catch(() => {});
    void load();
    const onVisible = () => { if (document.visibilityState === "visible") void load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => { cancelled = true; document.removeEventListener("visibilitychange", onVisible); };
  }, []);
  if (!quota || quota.used < quota.limit * 0.8) return null;
  const exhausted = quota.used >= quota.limit;
  return <p role="status" className={`mx-4 mt-3 rounded-xl p-3 text-xs ${exhausted ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-900"}`}>
    {exhausted ? "سقف مصرف توکن شما به پایان رسیده است؛ برای ادامه با مدیر سیستم تماس بگیرید." : `بیش از ${Math.floor((quota.used / quota.limit) * 100).toLocaleString("fa-IR")}٪ از سقف مصرف توکن شما استفاده شده است.`}
  </p>;
}
