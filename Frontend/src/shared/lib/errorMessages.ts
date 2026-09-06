import { ApiError } from "./apiClient";

export function friendlyErrorMessage(
  error: unknown,
  fallback = "مشکلی پیش آمد. دوباره تلاش کنید."
): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "نشست شما منقضی شده است. دوباره وارد شوید.";
    if (error.status === 403) return "برای انجام این کار دسترسی کافی ندارید.";
    if (error.status === 404) return "اطلاعات موردنظر پیدا نشد.";
    if (error.status === 413) return "حجم فایل بیشتر از حد مجاز است.";
    if (error.status === 429) return "تعداد درخواست‌ها زیاد است؛ کمی بعد دوباره تلاش کنید.";
    if (error.status >= 500) return "سرور موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.";
    return error.message || fallback;
  }

  if (error instanceof TypeError) {
    return "ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کنید.";
  }

  return error instanceof Error && error.message ? error.message : fallback;
}
