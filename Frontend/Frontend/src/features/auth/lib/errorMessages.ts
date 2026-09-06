import { ApiError } from "@/shared/lib/apiClient";

/** Turns backend / network errors into a friendly Persian sentence for the auth forms. */
export function authErrorMessage(err: unknown, mode: "login" | "register"): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 401:
        return "ایمیل یا رمز عبور درست نیست. یک بار دیگر امتحان کن.";
      case 409:
        return "این ایمیل قبلاً ثبت شده. اگر حساب داری، وارد شو.";
      case 422:
        return mode === "register"
          ? "لطفاً یک ایمیل معتبر و رمز عبور حداقل ۸ کاراکتری وارد کن."
          : "ایمیل یا رمز عبور به‌درستی وارد نشده.";
      case 429:
        return "تعداد تلاش‌ها زیاد شده؛ چند دقیقه بعد دوباره امتحان کن.";
      default:
        if (err.status >= 500) return "سرور فعلاً پاسخ نمی‌دهد. کمی بعد دوباره تلاش کن.";
        return err.message || "مشکلی پیش آمد. دوباره امتحان کن.";
    }
  }
  if (err instanceof TypeError) {
    // fetch() rejects with TypeError when the server is unreachable / CORS fails
    return "ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کن.";
  }
  return "مشکلی پیش آمد. دوباره امتحان کن.";
}
