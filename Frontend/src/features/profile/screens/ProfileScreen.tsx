"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { formatQuotaReset, friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { MyUsage, QuotaWindow, UserQuota } from "@/shared/types";

const ROLE_LABEL = { super_admin: "مدیر ارشد سازمان", admin: "مدیر سازمان", user: "عضو سازمان" } as const;
const WINDOW_LABEL = { five_hour: "۵ ساعت اخیر", weekly: "۷ روز اخیر", monthly: "ماه شمسی جاری" } as const;
const WINDOW_HINT = { five_hour: "پنجره‌ی شناور", weekly: "پنجره‌ی شناور", monthly: "از اول ماه شمسی" } as const;
const PURPOSE_LABEL: Record<string, string> = { chat: "چت و دستیار", sql: "پرس‌وجوی مالی", rerank: "رتبه‌بندی جست‌وجو", vr_agent: "گزارش حجم", ocr: "خواندن اسناد (OCR)", embedding: "ایندکس اسناد" };

const usd = (value: number) => `${value.toLocaleString("fa-IR", { minimumFractionDigits: 2, maximumFractionDigits: Math.abs(value) < 1 && value !== 0 ? 4 : 2 })} دلار`;

function WindowCard({ window: w }: { window: QuotaWindow }) {
  const limit = w.limit_usd;
  const percent = limit ? Math.min(100, Math.round((w.used_usd / limit) * 100)) : 0;
  const remaining = limit === null ? null : Math.max(limit - w.used_usd, 0);
  const tone = w.exhausted ? "bg-rose-500" : percent >= 80 ? "bg-amber-500" : "bg-teal-600";
  return <div className="space-y-2 rounded-xl border border-gray-100 p-4">
    <div className="flex items-baseline justify-between gap-2">
      <h3 className="text-sm font-semibold text-gray-800">{WINDOW_LABEL[w.name]}</h3>
      <span className="text-[11px] text-gray-400">{WINDOW_HINT[w.name]}</span>
    </div>
    <p className="text-lg font-bold text-gray-900">{usd(w.used_usd)}</p>
    {limit !== null
      ? <>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`مصرف ${WINDOW_LABEL[w.name]}`}>
          <div className={`h-full rounded-full transition-all ${tone}`} style={{ width: `${percent}%` }} />
        </div>
        <p className="text-xs text-gray-600">سقف {usd(limit)} · باقی‌مانده <span className="font-semibold">{usd(remaining ?? 0)}</span> ({percent.toLocaleString("fa-IR")}٪ مصرف‌شده)</p>
        {w.exhausted && <p className="text-xs text-rose-700">این سقف تمام شده است؛ {formatQuotaReset(w.resets_at) || "کمی بعد"} می‌توانید ادامه دهید.</p>}
      </>
      : <p className="text-xs text-gray-500">بدون سقف</p>}
  </div>;
}

/** The signed-in user's own consumption: the three quota windows (used / cap / remaining), this month by purpose, the last days. */
export function ProfileScreen() {
  const user = useAuthStore((state) => state.user);
  const [quota, setQuota] = useState<UserQuota | null>(null);
  const [usage, setUsage] = useState<MyUsage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [q, u] = await Promise.all([authApi.myQuota(), authApi.myUsage(30)]);
      setQuota(q); setUsage(u); setError(null);
    } catch (err) { setError(friendlyErrorMessage(err, "دریافت اطلاعات مصرف ناموفق بود.")); } finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  const maxDay = Math.max(0, ...(usage?.daily.map((d) => d.cost_usd) ?? []));
  const label = user?.full_name?.trim() || user?.email || "حساب کاربری";

  return <main className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6 lg:p-8">
    <div className="flex items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">پروفایل و مصرف من</h1>
        <p className="mt-1 text-sm text-gray-500">{label}{user ? ` — ${ROLE_LABEL[user.role]}` : ""}{user?.full_name ? ` · ${user.email}` : ""}</p>
      </div>
      <Button type="button" variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>به‌روزرسانی</Button>
    </div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {loading && !quota && <p className="text-sm text-gray-500">در حال بارگذاری...</p>}

    {quota && <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold text-gray-800">سهمیه‌ی مصرف</h2>
        {quota.unlimited ? <Badge tone="green">بدون سقف</Badge> : quota.enforced ? <Badge tone="green">سقف اعمال می‌شود</Badge> : <Badge tone="gray">فقط پایش؛ هنوز مسدود نمی‌شوید</Badge>}
      </div>
      <p className="text-xs text-gray-500">مصرف شما هزینه‌ی چت، پرس‌وجوها، گزارش‌ها و پردازش فایل‌هایی است که خودتان آپلود می‌کنید. سه سقف هم‌زمان اعمال می‌شود و هر کدام زودتر پر شود شما را نگه می‌دارد.</p>
      {quota.unlimited
        ? <p className="rounded-xl bg-slate-50 p-4 text-sm text-gray-700">برای حساب شما سقفی تعریف نشده است. مصرف‌تان همچنان ثبت می‌شود.</p>
        : <div className="grid gap-3 md:grid-cols-3">{quota.windows.map((w) => <WindowCard key={w.name} window={w} />)}</div>}
    </section>}

    {usage && <section className="space-y-4 rounded-2xl border border-gray-200 bg-white p-5">
      <div>
        <h2 className="font-semibold text-gray-800">مصرف این ماه (ماه شمسی)</h2>
        <p className="mt-1 text-sm text-gray-700">جمع: <span className="font-bold">{usd(usage.month_used_usd)}</span>
          {" "}از {new Date(usage.month.start).toLocaleDateString("fa-IR")}</p>
      </div>
      {usage.by_purpose.length === 0 ? <p className="text-sm text-gray-500">در این ماه مصرفی ثبت نشده است.</p>
        : <ul className="space-y-2">{usage.by_purpose.map((row) => {
          const share = usage.month_used_usd > 0 ? Math.round((row.cost_usd / usage.month_used_usd) * 100) : 0;
          return <li key={row.purpose} className="space-y-1 text-sm">
            <div className="flex justify-between gap-2"><span className="text-gray-700">{PURPOSE_LABEL[row.purpose] ?? row.purpose} <span className="text-xs text-gray-400">({row.calls.toLocaleString("fa-IR")} فراخوانی)</span></span><span className="font-medium text-gray-900">{usd(row.cost_usd)}</span></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-500" style={{ width: `${share}%` }} /></div>
          </li>;
        })}</ul>}
      {usage.setup_pool_usd > 0 && <p className="rounded-xl bg-slate-50 p-3 text-xs text-gray-600">{usd(usage.setup_pool_usd)} از پردازش اسناد پروژه‌هایی که آپلود کرده‌اید از «اعتبار مشترک راه‌اندازی» سازمان پرداخت شده و از سهمیه‌ی شخصی شما کم نشده است.</p>}

      <div className="space-y-2 border-t border-gray-100 pt-4">
        <h3 className="text-sm font-semibold text-gray-800">مصرف روزانه (۳۰ روز اخیر)</h3>
        {usage.daily.length === 0 ? <p className="text-sm text-gray-500">مصرفی ثبت نشده است.</p>
          : <div className="flex h-28 items-end gap-1" role="img" aria-label="نمودار مصرف روزانه">{usage.daily.map((d) =>
            <div key={d.date} className="group relative flex-1" title={`${new Date(d.date).toLocaleDateString("fa-IR")}: ${usd(d.cost_usd)}`}>
              <div className="w-full rounded-t bg-teal-500/80 group-hover:bg-teal-600" style={{ height: `${maxDay ? Math.max(4, Math.round((d.cost_usd / maxDay) * 100)) : 4}%` }} />
            </div>)}</div>}
        <p className="text-[11px] text-gray-400">با نگه‌داشتن ماوس روی هر ستون، مبلغ آن روز دیده می‌شود. هزینه‌ها بر اساس تعرفه‌ی تنظیم‌شده‌ی سازمان محاسبه شده‌اند و تخمینی‌اند.</p>
      </div>
    </section>}
  </main>;
}
