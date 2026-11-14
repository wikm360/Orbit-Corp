export const WINDOW_LABEL = { five_hour: "۵ ساعت اخیر", weekly: "۷ روز اخیر", monthly: "ماه شمسی جاری" } as const;
export const PURPOSE_LABEL: Record<string, string> = { chat: "چت", sql: "پرس‌وجوی مالی", rerank: "رتبه‌بندی جست‌وجو", vr_agent: "گزارش حجم", ocr: "OCR اسناد", embedding: "embedding" };

/** USD with 2 digits (4 for tiny amounts), Persian numerals. */
export const usd = (value: number) => `${value.toLocaleString("fa-IR", { minimumFractionDigits: 2, maximumFractionDigits: Math.abs(value) < 1 && value !== 0 ? 4 : 2 })} دلار`;

/** Parses a user-typed amount (Persian/Arabic digits accepted); null when empty, NaN when invalid. */
export function parseAmount(text: string): number | null {
  const normal = text.trim().replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d))).replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d))).replace("٫", ".").replace(",", ".");
  if (normal === "") return null;
  return /^\d+(\.\d+)?$/.test(normal) ? Number(normal) : Number.NaN;
}
