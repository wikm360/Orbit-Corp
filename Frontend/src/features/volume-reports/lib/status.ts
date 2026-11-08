import type { LineEffect, ReportStatus, Role } from "../types";

export const STATUS_LABELS: Record<ReportStatus, string> = {
  draft: "پیش‌نویس", processing: "در حال پردازش", awaiting_user: "منتظر پاسخ", needs_review: "نیازمند بازبینی", ready: "آماده", published: "منتشرشده", failed: "ناموفق",
};
export const STATUS_TONES: Record<ReportStatus, string> = {
  draft: "bg-slate-100 text-slate-700", processing: "bg-sky-100 text-sky-800", awaiting_user: "bg-amber-100 text-amber-800",
  needs_review: "bg-orange-100 text-orange-800", ready: "bg-emerald-100 text-emerald-800", published: "bg-teal-700 text-white", failed: "bg-red-100 text-red-700",
};
export const PERIOD_LABELS = { week: "هفتگی", month: "ماهانه" } as const;
export const ROLE_LABELS: Record<Role, string> = { supply: "تهیه", execute: "اجرا", combined: "ترکیبی", na: "نامشخص" };
export const SITE_KIND_LABELS = { road: "راهسازی", mining: "معدن", other: "سایر" } as const;

export const EFFECT_LABELS: Record<LineEffect, string> = {
  counted: "شمرده‌شده", supply_ignored: "تهیه (نادیده)", supply_only_not_counted: "فقط تهیه (شمرده نشد)", duplicate_ignored: "تکراری",
  excluded: "حذف‌شده", unmatched: "نامنطبق", nonphysical: "بدون حجم فیزیکی", unit_mismatch: "ناسازگاری واحد", no_conversion: "نیازمند پارامتر تبدیل",
  site_kind_mismatch: "نوع کارگاه نامناسب", needs_input: "نیازمند تصمیم",
};

export const GATE_LABELS: Record<string, string> = {
  open_questions: "سؤال بی‌پاسخ", unconfirmed_counted: "ردیف شمرده‌شده‌ی تأییدنشده", needs_input: "گروه بدون تصمیم",
  unit_mismatch: "ناسازگاری واحد", no_conversion: "پارامتر تبدیل ناموجود", site_kind_unconfirmed: "نوع کارگاه تأییدنشده",
};
export const GATE_HINTS: Record<string, string> = {
  open_questions: "در تب «بازبینی» به سؤال‌ها پاسخ دهید یا ردشان کنید.",
  unconfirmed_counted: "گروه‌های پیشنهادی agent را در «تأیید گروهی» تأیید یا اصلاح کنید.",
  needs_input: "برای این گروه‌ها آیتم یا دلیل حذف مشخص کنید.",
  unit_mismatch: "واحد ردیف با آیتم نمی‌خواند؛ آیتم را اصلاح یا ردیف را حذف کنید.",
  no_conversion: "پارامتر تبدیل (چگالی، ضخامت یا مقطع) را وارد کنید.",
  site_kind_unconfirmed: "نوع کارگاه را تأیید کنید.",
};
export const gateLabel = (code: string) => GATE_LABELS[code] ?? code;

export const SHEET_REASON_LABELS: Record<string, string> = {
  hidden: "شیت پنهان", planned_sheet: "شیت برنامه‌ای", expense_sheet: "شیت هزینه", not_income_sheet: "شیت درآمد نیست", layout_unknown: "چیدمان ناشناخته", planned_layout_unknown: "برنامه‌ی پیش‌بینی با چیدمان ناشناخته",
};
export const WARNING_LABELS: Record<string, string> = {
  period_label_mismatch: "ماه عنوان شیت با دوره‌ی واردشده نمی‌خواند", unit_missing: "ردیف بدون واحد", cached_values_missing: "مقدار فرمول‌ها ذخیره نشده است",
};

export const STEP_LABELS: Record<string, string> = {
  queued: "در صف", parse: "خواندن فایل‌ها", classify: "دسته‌بندی ردیف‌ها", agent: "بررسی هوشمند", compute: "محاسبه و تجمیع", done: "پایان",
};

/** Backend error for a blocked publish: `Publish blocked: [{"code":"…","count":n}]`. Returns the causes, or null for any other message. */
export function parseGateError(message: string): { code: string; count: number }[] | null {
  const i = message.indexOf("[");
  if (!message.startsWith("Publish blocked") || i < 0) return null;
  try {
    const parsed = JSON.parse(message.slice(i));
    return Array.isArray(parsed) ? parsed.filter((c) => c && typeof c.code === "string") : null;
  } catch {
    return null;
  }
}
