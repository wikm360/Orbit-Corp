"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { BrandLogo } from "@/features/branding/BrandLogo";
import { useBranding } from "@/features/branding/BrandingProvider";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { ApiError } from "@/shared/lib/apiClient";
import type { Branding } from "@/shared/types";
import { adminApi } from "../api/adminApi";

const TEXT_FIELDS = [
  { key: "name", label: "نام کامل سازمان", hint: "در صفحه‌ی ورود نمایش داده می‌شود" },
  { key: "short_name", label: "نام کوتاه", hint: "کنار لوگو در نوار کناری" },
  { key: "app_title", label: "عنوان برنامه", hint: "عنوان تب مرورگر" },
  { key: "tagline", label: "شعار کوتاه", hint: "زیر نام سازمان در صفحه‌ی ورود" },
  { key: "product_label", label: "برچسب لاتین محصول", hint: "زیر نام کوتاه در نوار کناری (انگلیسی)" },
  { key: "login_headline", label: "تیتر صفحه‌ی ورود", hint: "" },
  { key: "login_footer", label: "متن پایین صفحه‌ی ورود", hint: "" },
  { key: "description", label: "توضیح برنامه", hint: "برای موتورهای جست‌وجو و پیش‌نمایش لینک" },
] as const;
const COLOR_FIELDS = [
  { key: "color_brand", label: "رنگ اصلی (زمینه‌ی تیره)", hint: "پس‌زمینه‌ی پنل ورود و رنگ سرتیترها؛ باید با متن سفید خوانا باشد" },
  { key: "color_highlight", label: "رنگ برجسته", hint: "دکمه‌ها و لینک‌ها؛ باید با متن سفید خوانا باشد" },
  { key: "color_accent", label: "رنگ تأکیدی", hint: "نشانگرها و جزئیات تزئینی" },
] as const;
type FormState = Record<(typeof TEXT_FIELDS)[number]["key"] | (typeof COLOR_FIELDS)[number]["key"], string>;

function toForm(b: Branding): FormState {
  return {
    name: b.name, short_name: b.short_name, app_title: b.app_title, tagline: b.tagline, product_label: b.product_label,
    login_headline: b.login_headline, login_footer: b.login_footer, description: b.description,
    color_brand: b.colors.brand, color_highlight: b.colors.highlight, color_accent: b.colors.accent,
  };
}

/** Identity of this deployment: names, texts, three brand colours and the logo. Super admins only (the server enforces it). */
export function BrandingPanel() {
  const router = useRouter();
  const current = useBranding();
  const [saved, setSaved] = useState(current);
  const [form, setForm] = useState<FormState>(() => toForm(current as Branding));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const dirty = (Object.keys(form) as (keyof FormState)[]).some((k) => form[k] !== toForm(saved as Branding)[k]);
  const hexOk = (v: string) => /^#[0-9a-fA-F]{6}$/.test(v);

  async function run(action: () => Promise<Branding>, okText: string) {
    setBusy(true);
    setMessage(null);
    try {
      const next = await action();
      setSaved(next);
      setForm(toForm(next));
      setMessage({ ok: true, text: okText });
      router.refresh(); // re-runs the root layout: colours, names and logo apply everywhere without a manual reload
    } catch (err) {
      const detail = err instanceof ApiError && err.status === 400 ? `ذخیره نشد: ${err.message}` : friendlyErrorMessage(err, "ذخیره ناموفق بود.");
      setMessage({ ok: false, text: detail });
    } finally { setBusy(false); }
  }

  const save = () => {
    const bad = COLOR_FIELDS.find(({ key }) => !hexOk(form[key]));
    if (bad) return setMessage({ ok: false, text: `«${bad.label}» باید یک رنگ معتبر مثل #3446b8 باشد.` });
    void run(() => adminApi.updateBranding(form), "هویت سازمان ذخیره شد.");
  };

  return <section className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5">
    <div>
      <h2 className="font-semibold text-gray-800">هویت سازمان (برند)</h2>
      <p className="mt-1 text-xs text-gray-500">نام، لوگو، رنگ‌ها و متن‌های صفحه‌ی ورود این نصب. تغییرات برای همه‌ی کاربران و در صفحه‌ی ورود اعمال می‌شود.</p>
    </div>
    {message && <p role={message.ok ? "status" : "alert"} className={`rounded-xl p-3 text-xs ${message.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-700"}`}>{message.text}</p>}

    <div className="flex flex-wrap items-center gap-4 rounded-xl bg-slate-50 p-4">
      <BrandLogo className="h-16 w-16" rounded="rounded-xl" />
      <div className="space-y-2 text-xs">
        <p className="text-gray-600">لوگو: PNG، JPEG یا WebP، حداکثر ۵۱۲ کیلوبایت و ۲۰۴۸ پیکسل. تصویر با پس‌زمینه‌ی شفاف یا سفید بهتر دیده می‌شود.</p>
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" aria-label="انتخاب فایل لوگو"
            onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; if (file) void run(() => adminApi.uploadBrandLogo(file), "لوگو به‌روز شد."); }} />
          <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => fileRef.current?.click()}>{saved.logo_url ? "جایگزینی لوگو" : "بارگذاری لوگو"}</Button>
          {saved.logo_url && <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => adminApi.deleteBrandLogo(), "لوگو حذف شد.")}>حذف لوگو</Button>}
        </div>
      </div>
    </div>

    <div className="grid gap-4 sm:grid-cols-3">{COLOR_FIELDS.map(({ key, label, hint }) => <div key={key} className="space-y-1.5">
      <p className="text-sm font-medium text-gray-700">{label}</p>
      <div className="flex items-center gap-2">
        <input type="color" aria-label={label} value={hexOk(form[key]) ? form[key] : "#000000"} onChange={(event) => setForm((c) => ({ ...c, [key]: event.target.value }))} className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-gray-200 bg-white p-1" />
        <Input aria-label={`${label} (کد رنگ)`} dir="ltr" value={form[key]} onChange={(event) => setForm((c) => ({ ...c, [key]: event.target.value.trim() }))} error={hexOk(form[key]) ? undefined : "کد رنگ نامعتبر"} className="w-32 font-mono" />
      </div>
      <p className="text-[11px] text-gray-500">{hint}</p>
    </div>)}</div>

    <div className="grid gap-4 sm:grid-cols-2">{TEXT_FIELDS.map(({ key, label, hint }) => <Input key={key} label={label} hint={hint || undefined} dir={key === "product_label" ? "ltr" : undefined} value={form[key]} onChange={(event) => setForm((c) => ({ ...c, [key]: event.target.value }))} />)}</div>

    <div className="rounded-xl p-4 text-white" style={{ background: hexOk(form.color_brand) ? form.color_brand : undefined }} aria-label="پیش‌نمایش">
      <p className="text-xs opacity-80">پیش‌نمایش رنگ‌ها (پس از ذخیره، سایه‌های کامل ساخته می‌شود)</p>
      <p className="mt-1 text-lg font-bold">{form.name}</p>
      <p className="text-sm opacity-90">{form.tagline}</p>
      <div className="mt-3 flex gap-2">
        <span className="rounded-lg px-3 py-1.5 text-xs font-medium text-white" style={{ background: hexOk(form.color_highlight) ? form.color_highlight : undefined }}>دکمه</span>
        <span className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-900" style={{ background: hexOk(form.color_accent) ? form.color_accent : undefined }}>تأکید</span>
      </div>
    </div>

    <div className="flex flex-wrap items-center gap-2">
      <Button type="button" onClick={save} isLoading={busy} disabled={busy || !dirty}>ذخیره‌ی هویت سازمان</Button>
      <Button type="button" variant="ghost" disabled={busy || !dirty} onClick={() => { setForm(toForm(saved as Branding)); setMessage(null); }}>بازگردانی تغییرات</Button>
    </div>
  </section>;
}
