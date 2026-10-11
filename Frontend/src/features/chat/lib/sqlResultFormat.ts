import type { ColumnKind } from "../types";

const faInt = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 });
const faDecimal = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 });
const faPercent = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 });
const faDay = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "UTC" });

export interface FormattedCell {
  text: string;
  /** Secondary muted line (e.g. the Toman equivalent of a Rial amount). */
  hint?: string;
  align: "start" | "end";
  numeric: boolean;
}

/** «≈ ۲۰۵ میلیون تومان» for a Rial amount, or undefined when the amount is too small for a useful summary. */
export function tomanHint(rial: number): string | undefined {
  const toman = Math.abs(rial) / 10;
  if (toman < 1_000_000) return undefined;
  const sign = rial < 0 ? "−" : "";
  if (toman >= 1_000_000_000) return `≈ ${sign}${faDecimal.format(toman / 1_000_000_000)} میلیارد تومان`;
  return `≈ ${sign}${faDecimal.format(toman / 1_000_000)} میلیون تومان`;
}

/** ISO calendar date (YYYY-MM-DD…) -> Jalali; anything else (already-Jalali text, free text) is shown unchanged. */
export function formatDateValue(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}/.test(value)) return value;
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : faDay.format(date);
}

export function formatCell(kind: ColumnKind, value: unknown): FormattedCell {
  if (value === null || value === undefined || value === "") return { text: "—", align: "start", numeric: false };
  if (typeof value === "number" && Number.isFinite(value)) {
    if (kind === "money") return { text: faInt.format(Math.round(value)), hint: tomanHint(value), align: "end", numeric: true };
    if (kind === "ratio") return { text: `${faPercent.format(value * 100)}٪`, align: "end", numeric: true };
    if (kind === "text" || kind === "date") return { text: String(value), align: "start", numeric: false };
    return { text: Number.isInteger(value) ? faInt.format(value) : faDecimal.format(value), align: "end", numeric: true };
  }
  if (typeof value === "boolean") return { text: value ? "بله" : "خیر", align: "start", numeric: false };
  const text = String(value);
  return { text: kind === "date" ? formatDateValue(text) : text, align: "start", numeric: false };
}

/** Pick the freshness notes worth showing next to a result. Keys come from ai.data_freshness (Persian labels). */
export function freshnessNotes(dataAsOf: Record<string, string>): string[] {
  const find = (prefix: string) => Object.entries(dataAsOf).find(([key]) => key.startsWith(prefix))?.[1];
  const latest = find("آخرین تاریخ سند حسابداری معتبر");
  const reviewed = find("آخرین تاریخ سند بررسی‌شده");
  const notes: string[] = [];
  if (latest) notes.push(`داده تا ${formatDateValue(latest)}`);
  if (reviewed && latest && reviewed < latest) notes.push(`اسناد بعد از ${formatDateValue(reviewed)} هنوز موقت‌اند`);
  return notes;
}
