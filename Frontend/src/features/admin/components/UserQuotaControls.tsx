"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { formatQuotaReset, friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { QuotaWindowName, User, UserQuota } from "@/shared/types";
import { adminApi } from "../api/adminApi";
import { WINDOW_LABEL, parseAmount, usd } from "../lib/quotaFormat";

const NAMES: QuotaWindowName[] = ["five_hour", "weekly", "monthly"];

/** Dollar quota of one user: the three windows (used / cap) for everyone who may see it; super admins can also set a per-user
 *  exception (an empty cap follows the role's plan; "نامحدود" removes every cap). The server enforces the same rules. */
export function UserQuotaControls({ user, canEdit }: { user: User; canEdit: boolean }) {
  const [quota, setQuota] = useState<UserQuota | null>(null);
  const [fields, setFields] = useState<Record<QuotaWindowName, string>>({ five_hour: "", weekly: "", monthly: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await adminApi.userQuota(user.id);
      setQuota(data);
      setFields(Object.fromEntries(data.windows.map((w) => [w.name, w.overridden && w.limit_usd !== null ? String(w.limit_usd) : ""])) as Record<QuotaWindowName, string>);
      setError(null);
    } catch (err) { setError(friendlyErrorMessage(err, "دریافت سهمیه‌ی دلاری ناموفق بود.")); }
  }, [user.id]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function save(unlimited: boolean) {
    const values = NAMES.map((name) => parseAmount(fields[name]));
    if (values.some((v) => v !== null && (Number.isNaN(v) || v <= 0))) { setError("هر سقف باید عدد مثبت (دلار) یا خالی باشد."); return; }
    setBusy(true);
    try {
      setQuota(await adminApi.setUserQuota(user.id, { five_hour_usd: values[0] ?? null, weekly_usd: values[1] ?? null, monthly_usd: values[2] ?? null, unlimited }));
      setError(null);
      await load();
    } catch (err) { setError(friendlyErrorMessage(err, "ذخیره ناموفق بود.")); } finally { setBusy(false); }
  }

  if (user.role === "super_admin") return null;
  if (!quota) return error ? <p className="text-xs text-rose-700">{error}</p> : null;

  return <div className="w-full space-y-2 rounded-xl bg-slate-50 p-3 text-xs">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="font-medium text-gray-700">سهمیه‌ی دلاری{quota.unlimited ? " — نامحدود (استثنا)" : ""}{quota.enforced ? "" : " — فقط پایش (اعمال نمی‌شود)"}</span>
    </div>
    <div className="grid gap-2 sm:grid-cols-3">{quota.windows.map((w) => {
      const percent = w.limit_usd ? Math.min(100, Math.round((w.used_usd / w.limit_usd) * 100)) : 0;
      return <div key={w.name} className="space-y-1">
        <p className="text-gray-700">{WINDOW_LABEL[w.name]}{w.overridden ? " ✎" : ""}: {usd(w.used_usd)}{w.limit_usd !== null ? ` از ${usd(w.limit_usd)}` : " (بدون سقف)"}</p>
        {w.limit_usd !== null && <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`${WINDOW_LABEL[w.name]} ${user.email}`}>
          <div className={`h-full rounded-full ${w.exhausted ? "bg-rose-500" : percent >= 80 ? "bg-amber-500" : "bg-teal-600"}`} style={{ width: `${percent}%` }} />
        </div>}
        {w.exhausted && <p className="text-rose-700">تمام شده {formatQuotaReset(w.resets_at)}</p>}
      </div>;
    })}</div>
    {canEdit && <div className="flex flex-wrap items-end gap-2 border-t border-slate-200 pt-2">
      {NAMES.map((name) => <Input key={name} aria-label={`سقف ${WINDOW_LABEL[name]} ${user.email} (دلار)`} label={`${WINDOW_LABEL[name]} (دلار)`} inputMode="decimal" placeholder="طبق پلن" value={fields[name]} onChange={(event) => setFields((c) => ({ ...c, [name]: event.target.value }))} className="w-32" />)}
      <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => void save(false)}>ذخیره استثنا</Button>
      <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => void save(true)}>نامحدود</Button>
      <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => { setFields({ five_hour: "", weekly: "", monthly: "" }); void adminApi.setUserQuota(user.id, { five_hour_usd: null, weekly_usd: null, monthly_usd: null, unlimited: false }).then(load).catch((err) => setError(friendlyErrorMessage(err))); }}>بازگشت به پلن</Button>
    </div>}
    {error && <p className="text-rose-700">{error}</p>}
  </div>;
}
