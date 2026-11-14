"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { CostSummary, ModelPrice, QuotaOverview } from "@/shared/types";
import { adminApi } from "../api/adminApi";
import { PURPOSE_LABEL, WINDOW_LABEL, parseAmount, usd } from "../lib/quotaFormat";

const ROLES = [{ key: "user", label: "کاربر" }, { key: "admin", label: "مدیر" }] as const;
const FIELDS = [{ key: "five_hour_usd", label: WINDOW_LABEL.five_hour }, { key: "weekly_usd", label: WINDOW_LABEL.weekly }, { key: "monthly_usd", label: WINDOW_LABEL.monthly }] as const;
type PlanKey = (typeof FIELDS)[number]["key"];

/** Cost management: plans per role, the enforcement switch, the setup pool, the organisation cap, model prices and the last 30
 *  days' cost. Everyone with the admin panel reads it; only `canEdit` (super admin) writes (the server enforces the same). */
export function QuotaAdminPanel({ canEdit }: { canEdit: boolean }) {
  const [overview, setOverview] = useState<QuotaOverview | null>(null);
  const [prices, setPrices] = useState<ModelPrice[]>([]);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [plans, setPlans] = useState<Record<string, Record<PlanKey, string>>>({});
  const [poolBudget, setPoolBudget] = useState("");
  const [orgCap, setOrgCap] = useState("");
  const [priceDraft, setPriceDraft] = useState<Record<string, { input: string; output: string; page: string }>>({});
  const [newModel, setNewModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((data: QuotaOverview) => {
    setOverview(data);
    setPlans(Object.fromEntries(ROLES.map(({ key }) => [key, Object.fromEntries(FIELDS.map(({ key: f }) => [f, String(data.plans[key]?.[f] ?? "")]))])) as Record<string, Record<PlanKey, string>>);
    setPoolBudget(String(data.setup_pool.budget_usd));
    setOrgCap(data.org.monthly_cap_usd === null ? "" : String(data.org.monthly_cap_usd));
  }, []);

  const load = useCallback(async () => {
    try {
      const [o, p, s] = await Promise.all([adminApi.quotaOverview(), adminApi.modelPrices(), adminApi.costSummary(30)]);
      apply(o); setPrices(p); setSummary(s);
      setPriceDraft(Object.fromEntries(p.map((row) => [row.model, { input: String(row.input_per_m), output: String(row.output_per_m), page: row.per_page_usd === null ? "" : String(row.per_page_usd) }])));
      setError(null);
    } catch (err) { setError(friendlyErrorMessage(err, "دریافت اطلاعات هزینه ناموفق بود.")); }
  }, [apply]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function run(action: () => Promise<QuotaOverview | unknown>, reload = false) {
    setBusy(true);
    try {
      const result = await action();
      if (reload) await load(); else if (result && typeof result === "object" && "plans" in result) apply(result as QuotaOverview);
      setError(null);
    } catch (err) { setError(friendlyErrorMessage(err, "ذخیره ناموفق بود.")); } finally { setBusy(false); }
  }

  const savePlan = (role: string) => {
    const values = FIELDS.map(({ key }) => parseAmount(plans[role]?.[key] ?? ""));
    if (values.some((v) => v === null || Number.isNaN(v) || v <= 0)) return setError("سقف‌های پلن باید عدد مثبت (دلار) باشند.");
    if (!(values[0]! <= values[1]! && values[1]! <= values[2]!)) return setError("ترتیب سقف‌ها باید ۵ ساعت ≤ هفته ≤ ماه باشد.");
    void run(() => adminApi.setQuotaPlan(role, { five_hour_usd: values[0]!, weekly_usd: values[1]!, monthly_usd: values[2]! }));
  };
  const savePrice = (model: string, draft: { input: string; output: string; page: string }) => {
    const [input, output, page] = [parseAmount(draft.input) ?? 0, parseAmount(draft.output) ?? 0, parseAmount(draft.page)];
    if ([input, output].some(Number.isNaN) || Number.isNaN(page)) return setError("قیمت‌ها باید عدد (دلار) باشند.");
    void run(() => adminApi.setModelPrice(model, { input_per_m: input, output_per_m: output, per_page_usd: page }), true);
  };

  if (!overview) return <section className="rounded-2xl border border-gray-200 bg-white p-5 text-sm text-gray-500">{error ?? "در حال بارگذاری مدیریت هزینه..."}</section>;
  const { setup_pool: pool, org } = overview;

  return <section className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h2 className="font-semibold text-gray-800">مدیریت هزینه و سهمیه‌ی دلاری</h2>
        <p className="mt-1 text-xs text-gray-500">سقف هر کاربر در سه بازه (۵ ساعت و ۷ روز شناور، ماه شمسی) از مجموع هزینه‌ی چت، OCR و embedding او حساب می‌شود. {canEdit ? "" : "فقط مدیر ارشد می‌تواند تغییر دهد."}</p>
      </div>
      <div className="flex items-center gap-2">
        {overview.enforced ? <Badge tone="green">اعمال می‌شود</Badge> : <Badge tone="gray">فقط پایش (shadow)</Badge>}
        {canEdit && <Button type="button" size="sm" variant={overview.enforced ? "ghost" : "secondary"} disabled={busy} onClick={() => { if (overview.enforced || window.confirm("با روشن‌کردن، کاربران با رسیدن به سقف مسدود می‌شوند. ادامه می‌دهید؟")) void run(() => adminApi.setQuotaEnforced(!overview.enforced)); }}>{overview.enforced ? "خاموش‌کردن اعمال سقف" : "روشن‌کردن اعمال سقف"}</Button>}
      </div>
    </div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-xs text-red-700">{error}</p>}

    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-800">پلن هر سطح (دلار)</h3>
      {ROLES.map(({ key, label }) => <div key={key} className="flex flex-wrap items-end gap-2 text-xs">
        <span className="w-14 pb-2 font-medium text-gray-700">{label}</span>
        {FIELDS.map(({ key: f, label: fieldLabel }) => <Input key={f} label={fieldLabel} aria-label={`${label} ${fieldLabel} (دلار)`} inputMode="decimal" disabled={!canEdit} value={plans[key]?.[f] ?? ""} onChange={(event) => setPlans((c) => ({ ...c, [key]: { ...c[key]!, [f]: event.target.value } }))} className="w-28" />)}
        {canEdit && <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => savePlan(key)}>ذخیره</Button>}
      </div>)}
      <p className="text-xs text-gray-500">مدیر ارشد هرگز محدود نمی‌شود. استثنا برای هر کاربر در فهرست کاربران پایین همین صفحه تنظیم می‌شود.</p>
    </div>

    <div className="grid gap-4 md:grid-cols-2">
      <div className="space-y-2 rounded-xl bg-slate-50 p-3 text-xs">
        <h3 className="text-sm font-medium text-gray-800">اعتبار مشترک راه‌اندازی (ورود اسناد پروژه‌ها)</h3>
        <p className="text-gray-600">تا وقتی روشن است، هزینه‌ی OCR و embedding اسناد پروژه از این اعتبار کم می‌شود، نه از سهمیه‌ی آپلودکننده. مصرف: {usd(pool.used_usd)} از {usd(pool.budget_usd)} (مانده {usd(pool.remaining_usd)}).</p>
        <div className="flex flex-wrap items-end gap-2">
          {pool.enabled ? <Badge tone="green">روشن</Badge> : <Badge tone="gray">خاموش</Badge>}
          {canEdit && <>
            <Input label="بودجه‌ی کل (دلار)" aria-label="بودجه‌ی اعتبار راه‌اندازی (دلار)" inputMode="decimal" value={poolBudget} onChange={(event) => setPoolBudget(event.target.value)} className="w-28" />
            <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => { const v = parseAmount(poolBudget); if (v === null || Number.isNaN(v) || v <= 0) return setError("بودجه باید عدد مثبت باشد."); void run(() => adminApi.setSetupPool({ budget_usd: v })); }}>ذخیره بودجه</Button>
            <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => adminApi.setSetupPool({ enabled: !pool.enabled }))}>{pool.enabled ? "خاموش‌کردن" : "روشن‌کردن"}</Button>
          </>}
        </div>
      </div>
      <div className="space-y-2 rounded-xl bg-slate-50 p-3 text-xs">
        <h3 className="text-sm font-medium text-gray-800">سقف کل سازمان (ماه شمسی)</h3>
        <p className="text-gray-600">مصرف این ماه: {usd(org.month_used_usd)}{org.monthly_cap_usd !== null ? ` از ${usd(org.monthly_cap_usd)} (${(org.percent ?? 0).toLocaleString("fa-IR")}٪)` : " — سقفی تعیین نشده"}. با رسیدن به سقف، همه جز مدیر ارشد متوقف می‌شوند.</p>
        {org.percent !== null && org.percent >= 80 && <p className="text-amber-800">هشدار: مصرف سازمان از ۸۰٪ سقف گذشته است.</p>}
        {canEdit && <div className="flex flex-wrap items-end gap-2">
          <Input label="سقف ماهانه (دلار)" aria-label="سقف ماهانه‌ی کل سازمان (دلار)" inputMode="decimal" placeholder="بدون سقف" value={orgCap} onChange={(event) => setOrgCap(event.target.value)} className="w-28" />
          <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => { const v = parseAmount(orgCap); if (Number.isNaN(v) || (v !== null && v <= 0)) return setError("سقف باید عدد مثبت یا خالی باشد."); void run(() => adminApi.setOrgCap(v)); }}>ذخیره</Button>
        </div>}
      </div>
    </div>

    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-800">قیمت مدل‌ها (دلار به‌ازای هر ۱ میلیون توکن؛ OCR صفحه‌ای: به‌ازای هر صفحه)</h3>
      <div className="space-y-2 text-xs">{prices.map((row) => { const draft = priceDraft[row.model] ?? { input: "", output: "", page: "" }; const set = (patch: Partial<typeof draft>) => setPriceDraft((c) => ({ ...c, [row.model]: { ...draft, ...patch } })); return <div key={row.model} className="flex flex-wrap items-end gap-2">
        <span className="min-w-48 flex-1 break-all pb-2 font-mono text-gray-700" dir="ltr">{row.model}</span>
        <Input label="ورودی" aria-label={`قیمت ورودی ${row.model}`} inputMode="decimal" disabled={!canEdit} value={draft.input} onChange={(event) => set({ input: event.target.value })} className="w-24" />
        <Input label="خروجی" aria-label={`قیمت خروجی ${row.model}`} inputMode="decimal" disabled={!canEdit} value={draft.output} onChange={(event) => set({ output: event.target.value })} className="w-24" />
        <Input label="هر صفحه" aria-label={`قیمت هر صفحه ${row.model}`} inputMode="decimal" placeholder="—" disabled={!canEdit} value={draft.page} onChange={(event) => set({ page: event.target.value })} className="w-24" />
        {canEdit && <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => savePrice(row.model, draft)}>ذخیره</Button>}
      </div>; })}</div>
      {canEdit && <div className="flex flex-wrap items-end gap-2 text-xs">
        <Input label="مدل جدید" aria-label="نام مدل جدید" dir="ltr" placeholder="mistral-ocr-latest" value={newModel} onChange={(event) => setNewModel(event.target.value)} className="w-64" />
        <Button type="button" size="sm" variant="secondary" disabled={busy || !newModel.trim()} onClick={() => { const model = newModel.trim(); setNewModel(""); setPriceDraft((c) => ({ ...c, [model]: { input: "0", output: "0", page: "" } })); setPrices((c) => c.some((p) => p.model === model) ? c : [...c, { model, input_per_m: 0, output_per_m: 0, per_page_usd: null, updated_at: "" }]); }}>افزودن ردیف</Button>
      </div>}
      <p className="text-xs text-gray-500">مدلی که اینجا نباشد با گران‌ترین قیمت جدول حساب می‌شود، نه رایگان. قیمت Mistral OCR را در «هر صفحه» بگذارید؛ تا آن موقع هزینه‌اش صفر ثبت می‌شود.</p>
    </div>

    {summary && <div className="space-y-1 text-xs text-gray-700">
      <h3 className="text-sm font-medium text-gray-800">هزینه‌ی {summary.days.toLocaleString("fa-IR")} روز اخیر: {usd(summary.total_usd)}</h3>
      <p>بر اساس هدف: {summary.by_purpose.map((r) => `${PURPOSE_LABEL[r.purpose] ?? r.purpose} ${usd(r.cost_usd)}`).join(" · ") || "—"}</p>
      <p>بر اساس مدل: {summary.by_model.map((r) => `${r.model} ${usd(r.cost_usd)}`).join(" · ") || "—"}</p>
      <p>بر اساس کاربر: {summary.by_user.slice(0, 10).map((r) => `${r.email} ${usd(r.cost_usd)}`).join(" · ") || "—"}</p>
    </div>}
  </section>;
}
