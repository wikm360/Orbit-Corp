/** Jalali (شمسی) calendar helpers, dependency-free. The API speaks Gregorian ISO dates (`YYYY-MM-DD`); users see/enter Jalali. */

const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const EN_FROM_FA = (s: string) => s.replace(/[۰-۹]/g, (d) => String(FA_DIGITS.indexOf(d))).replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660));
export const JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"] as const;

export interface JalaliDate { jy: number; jm: number; jd: number }

const DIV = (a: number, b: number) => ~~(a / b);
const MOD = (a: number, b: number) => a - ~~(a / b) * b;
const BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178];

function jalCal(jy: number) {
  let leapJ = -14;
  let jp = BREAKS[0]!;
  let jump = 0;
  for (let i = 1; i < BREAKS.length; i += 1) {
    const jm = BREAKS[i]!;
    jump = jm - jp;
    if (jy < jm) break;
    leapJ += DIV(jump, 33) * 8 + DIV(MOD(jump, 33), 4);
    jp = jm;
  }
  let n = jy - jp;
  leapJ += DIV(n, 33) * 8 + DIV(MOD(n, 33) + 3, 4);
  if (MOD(jump, 33) === 4 && jump - n === 4) leapJ += 1;
  const leapG = DIV(jy + 621, 4) - DIV((DIV(jy + 621, 100) + 1) * 3, 4) - 150;
  const march = 20 + leapJ - leapG;
  if (jump - n < 6) n = n - jump + DIV(jump + 4, 33) * 33;
  let leap = MOD(MOD(n + 1, 33) - 1, 4);
  if (leap === -1) leap = 4;
  return { leap, gy: jy + 621, march };
}

function g2d(gy: number, gm: number, gd: number): number {
  let d = DIV((gy + DIV(gm - 8, 6) + 100100) * 1461, 4) + DIV(153 * MOD(gm + 9, 12) + 2, 5) + gd - 34840408;
  d = d - DIV(DIV(gy + 100100 + DIV(gm - 8, 6), 100) * 3, 4) + 752;
  return d;
}
function d2g(jdn: number) {
  let j = 4 * jdn + 139361631;
  j = j + DIV(DIV(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
  const i = DIV(MOD(j, 1461), 4) * 5 + 308;
  const gd = DIV(MOD(i, 153), 5) + 1;
  const gm = MOD(DIV(i, 153), 12) + 1;
  const gy = DIV(j, 1461) - 100100 + DIV(8 - gm, 6);
  return { gy, gm, gd };
}
function j2d(jy: number, jm: number, jd: number): number {
  const r = jalCal(jy);
  return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - DIV(jm, 7) * (jm - 7) + jd - 1;
}
function d2j(jdn: number): JalaliDate {
  const gy = d2g(jdn).gy;
  let jy = gy - 621;
  const r = jalCal(jy);
  let k = jdn - g2d(gy, 3, r.march);
  if (k >= 0) {
    if (k <= 185) return { jy, jm: 1 + DIV(k, 31), jd: MOD(k, 31) + 1 };
    k -= 186;
  } else {
    jy -= 1;
    k += 179;
    if (r.leap === 1) k += 1;
  }
  return { jy, jm: 7 + DIV(k, 30), jd: MOD(k, 30) + 1 };
}

export function gregorianToJalali(gy: number, gm: number, gd: number): JalaliDate { return d2j(g2d(gy, gm, gd)); }
export function jalaliToGregorian(jy: number, jm: number, jd: number) { const g = d2g(j2d(jy, jm, jd)); return { gy: g.gy, gm: g.gm, gd: g.gd }; }

export function isLeapJalali(jy: number): boolean { return jalCal(jy).leap === 0; }
export function daysInJalaliMonth(jy: number, jm: number): number { return jm <= 6 ? 31 : jm <= 11 ? 30 : isLeapJalali(jy) ? 30 : 29; }
export function isValidJalali(jy: number, jm: number, jd: number): boolean {
  return Number.isInteger(jy) && jy >= 1300 && jy <= 1600 && jm >= 1 && jm <= 12 && jd >= 1 && jd <= daysInJalaliMonth(jy, jm);
}

const pad2 = (n: number) => String(n).padStart(2, "0");
export const toFa = (value: string | number) => String(value).replace(/\d/g, (d) => FA_DIGITS[Number(d)]!);

const PERSIAN_WEEKDAYS = [
  "یکشنبه",
  "دوشنبه",
  "سه‌شنبه",
  "چهارشنبه",
  "پنج‌شنبه",
  "جمعه",
  "شنبه",
] as const;

function parseIsoCalendarParts(iso: string): { gy: number; gm: number; gd: number } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const [gy, gm, gd] = [Number(m[1]), Number(m[2]), Number(m[3])] as const;
  const utc = new Date(Date.UTC(gy, gm - 1, gd));
  if (utc.getUTCFullYear() !== gy || utc.getUTCMonth() + 1 !== gm || utc.getUTCDate() !== gd) {
    return null;
  }
  return { gy, gm, gd };
}

/** "2026-11-04" -> "چهارشنبه" (date-only in UTC: no timezone shift). */
export function formatJalaliWeekday(iso: string | null | undefined): string {
  if (!iso) return "";
  const parts = parseIsoCalendarParts(iso);
  if (!parts) return "";
  const weekdayIndex = new Date(Date.UTC(parts.gy, parts.gm - 1, parts.gd)).getUTCDay();
  return PERSIAN_WEEKDAYS[weekdayIndex] ?? "";
}

/** "2026-11-04" -> "چهارشنبه ۱۴۰۵/۰۸/۱۳" (date-only: no timezone shift). */
export function formatJalaliDateWithWeekday(iso: string | null | undefined): string {
  const dateStr = formatJalaliDate(iso);
  if (dateStr === "—") return "—";
  const weekday = formatJalaliWeekday(iso);
  return weekday ? `${weekday} ${dateStr}` : dateStr;
}

/** "2026-09-23" -> "۱۴۰۵/۰۷/۰۱" (date-only: no timezone shift). */
export function isoToJalali(iso: string): JalaliDate | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? gregorianToJalali(Number(m[1]), Number(m[2]), Number(m[3])) : null;
}
export function formatJalaliDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const j = isoToJalali(iso);
  return j ? toFa(`${j.jy}/${pad2(j.jm)}/${pad2(j.jd)}`) : "—";
}
/** Date-time ISO (UTC) -> Jalali date + local HH:MM. */
export function formatJalaliDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const j = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  return toFa(`${j.jy}/${pad2(j.jm)}/${pad2(j.jd)} - ${pad2(d.getHours())}:${pad2(d.getMinutes())}`);
}

/** User text "1405/06/15" or "۱۴۰۵-۶-۱۵" -> ISO Gregorian, or null when it is not a real Jalali date. */
export function parseJalaliInput(text: string): string | null {
  const m = /^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$/.exec(EN_FROM_FA(text.trim()));
  if (!m) return null;
  const [jy, jm, jd] = [Number(m[1]), Number(m[2]), Number(m[3])] as const;
  if (!isValidJalali(jy, jm, jd)) return null;
  const g = jalaliToGregorian(jy, jm, jd);
  return `${g.gy}-${pad2(g.gm)}-${pad2(g.gd)}`;
}
export function jalaliInputFromIso(iso: string): string {
  const j = isoToJalali(iso);
  return j ? `${j.jy}/${pad2(j.jm)}/${pad2(j.jd)}` : "";
}

const WEEK_ORDINALS = ["اول", "دوم", "سوم", "چهارم", "پنجم"] as const;

export function formatWeekLabel(startIso: string | null | undefined): string {
  if (!startIso) return "";
  const start = isoToJalali(startIso);
  if (!start) return "";
  const weekIdx = Math.min(Math.floor((start.jd - 1) / 7), 4);
  const weekOrdinal = WEEK_ORDINALS[weekIdx] || "اول";
  return `هفته ${weekOrdinal} ${JALALI_MONTHS[start.jm - 1]} ${toFa(start.jy)}`;
}

/** Suggested label for the period: month periods "شهریور ۱۴۰۵" (month of the end date); weeks "هفته‌ی ۱۴۰۵/۰۶/۱۵ تا ۱۴۰۵/۰۶/۲۱". */
export function suggestPeriodLabel(type: "week" | "month", startIso: string, endIso: string): string {
  const end = isoToJalali(endIso);
  if (!end) return "";
  if (type === "month") return `${JALALI_MONTHS[end.jm - 1]} ${toFa(end.jy)}`;
  return `هفته‌ی ${formatJalaliDate(startIso)} تا ${formatJalaliDate(endIso)}`;
}
