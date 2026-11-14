import { ApiError } from "./apiClient";

export const QUOTA_WINDOW_LABEL: Record<string, string> = {
  five_hour: "پنج‌ساعته", weekly: "هفتگی", monthly: "ماهانه", org_monthly: "کل سازمان",
};

/** "تا ساعت ۱۴:۳۰" / "تا ۲۳ آبان": when a quota window frees up (approximate for the rolling windows). */
export function formatQuotaReset(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const sameDay = date.toDateString() === new Date().toDateString();
  return sameDay
    ? `تا ساعت ${date.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" })}`
    : `تا ${date.toLocaleDateString("fa-IR", { day: "numeric", month: "long" })}`;
}

export function friendlyErrorMessage(
  error: unknown,
  fallback = "مشکلی پیش آمد. دوباره تلاش کنید."
): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "نشست شما منقضی شده است. دوباره وارد شوید.";
    if (error.status === 403) return "برای انجام این کار دسترسی کافی ندارید.";
    if (error.status === 404) return "اطلاعات موردنظر پیدا نشد.";
    if (error.status === 409) return "این مورد از قبل وجود دارد.";
    if (error.status === 413) return "حجم فایل یا مجموعهٔ ارسالی بیشتر از حد مجاز سرور است.";
    if (error.status === 429 && error.message === "setup_pool_exhausted") return "اعتبار مشترک ورود اسناد پروژه تمام شده است. برای ادامه با مدیر ارشد تماس بگیرید.";
    if (error.status === 429 && error.message === "token_quota_exceeded") {
      const window = error.headers?.get("X-Quota-Window");
      const reset = formatQuotaReset(error.headers?.get("X-Quota-Resets-At"));
      if (window) return `سقف مصرف ${QUOTA_WINDOW_LABEL[window] ?? ""} به پایان رسیده است${reset ? `؛ ${reset} صبر کنید` : ""}. در صورت نیاز با مدیر سیستم تماس بگیرید.`;
      return "سقف مصرف توکن شما به پایان رسیده است. برای ادامه با مدیر سیستم تماس بگیرید.";
    }
    if (error.status === 429) return "تعداد درخواست‌ها زیاد است؛ کمی بعد دوباره تلاش کنید.";
    if (error.status >= 500) return "سرور موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.";
    return error.message || fallback;
  }

  if (error instanceof TypeError) {
    return "ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کنید.";
  }

  return error instanceof Error && error.message ? error.message : fallback;
}
