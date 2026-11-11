/** Quantity formatting on decimal STRINGS only (no floating point): the backend sends exact decimals. */

import { toFa } from "./jalali";

export const UNIT_LABELS: Record<string, string> = {
  m3: "مترمکعب", m2: "مترمربع", m: "متر", kg: "کیلوگرم", t: "تن", m2cm: "مترمربع‌سانتی‌متر", m3km: "مترمکعب‌کیلومتر", hr: "ساعت",
  lump: "مقطوع", series: "سری", pct: "درصد", ea: "عدد", other: "—",
};
export const unitLabel = (unit: string | null | undefined) => (unit ? UNIT_LABELS[unit] ?? unit : "");

/** Rounds a plain decimal string half-up to `decimals` places using string arithmetic. Returns {negative, int, frac}. */
export function roundDecimalString(value: string, decimals: number): { negative: boolean; int: string; frac: string } | null {
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!m) return null;
  const negative = m[1] === "-";
  let int = m[2]!;
  let frac = (m[3] ?? "").padEnd(decimals + 1, "0");
  const roundUp = frac.charCodeAt(decimals) >= 53; // '5'
  frac = frac.slice(0, decimals);
  if (roundUp) {
    const digits = (int + frac).split("");
    let i = digits.length - 1;
    while (i >= 0) {
      if (digits[i] === "9") { digits[i] = "0"; i -= 1; } else { digits[i] = String(Number(digits[i]) + 1); break; }
    }
    const joined = (i < 0 ? "1" : "") + digits.join("");
    int = joined.slice(0, joined.length - decimals) || "0";
    frac = decimals ? joined.slice(joined.length - decimals) : "";
  }
  int = int.replace(/^0+(?=\d)/, "");
  const isZero = /^0*$/.test(int) && /^0*$/.test(frac);
  return { negative: negative && !isZero, int, frac };
}

/** "1949.3600", 2 -> "۱٬۹۴۹٫۳۶" (Persian digits, thousands separator, Persian decimal separator). */
export function formatQuantity(value: string | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const r = roundDecimalString(value, decimals);
  if (!r) return "—";
  const grouped = r.int.replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
  return toFa(`${r.negative ? "-" : ""}${grouped}${r.frac ? `٫${r.frac}` : ""}`);
}

/** Number + unit side by side: «۲٬۵۷۲٫۸۷ تن». */
export function formatQuantityWithUnit(value: string | null | undefined, unit: string | null | undefined, decimals = 2): string {
  const number = formatQuantity(value, decimals);
  return unit && number !== "—" ? `${number} ${unitLabel(unit)}` : number;
}

/** Chart axes need a JS number; only for drawing, never for displayed figures. */
export const toChartNumber = (value: string): number => Number.parseFloat(value);
export const formatInt = (n: number) => toFa(n.toLocaleString("en-US").replace(/,/g, "٬"));

/** Rial decimal string -> "میلیارد ریال" with 2 places, by integer arithmetic (no floats): "34000123354.00" -> "۳۴٫۰۰". */
export function formatBillionRial(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const m = /^(-?)(\d+)(?:\.\d+)?$/.exec(value.trim());
  if (!m) return "—";
  const hundredths = (BigInt(m[2]!) * BigInt(100) + BigInt(500_000_000)) / BigInt(1_000_000_000); // half-up
  const text = hundredths.toString().padStart(3, "0");
  const int = text.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
  return toFa(`${m[1] && hundredths > BigInt(0) ? "-" : ""}${int}٫${text.slice(-2)}`);
}

/** CPI / SPI ratio string ("1.05") -> Persian digits; null -> "—". */
export const formatRatio = (value: string | null | undefined): string => (value === null || value === undefined ? "—" : toFa(value.replace(".", "٫")));
