/** Pure data-merging, grid-layout, and typography helpers for the management presentation slides. */

import { formatQuantity } from "./format";
import { formatJalaliDateWithWeekday, toFa } from "./jalali";
import type { CatalogItem, ResultRow } from "../types";

export const COMBINED_COAT_KEY = "prime_tack_total";
export const COMBINED_COAT_TITLE = "پریمکت و تک‌کت";
export const COAT_SOURCE_KEYS = new Set(["prime_coat", "tack_coat"]);
export const PRESENTATION_EXCLUDED_KEYS = new Set(["asphalt_binder", "asphalt_topka", "prime_coat", "tack_coat"]);

export const SUMMARY_CANVAS_W = 1472; // 1536 - 2*32 horizontal padding
export const SUMMARY_CANVAS_H = 699; // 864 - header - footer - vertical padding
export const SUMMARY_GAP = 16;

/** Formats quantities rounded half-up to whole integers (no decimal places) across presentation slides.
 * When decimals is specified, formats with that precision. */
export function formatPresentationQuantity(value: string | null | undefined, decimals = 0): string {
  return formatQuantity(value, decimals);
}

function parseDecimalToBigInt(raw: string): { value: bigint; scale: number } | null {
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(raw.trim());
  if (!m) return null;
  const neg = m[1] === "-";
  const intPart = m[2]!;
  const fracPart = m[3] ?? "";
  const scale = fracPart.length;
  const digits = `${intPart}${fracPart}`;
  const value = BigInt(digits);
  return { value: neg ? -value : value, scale };
}

function formatBigIntDecimal(value: bigint, scale: number): string {
  const neg = value < 0n;
  const abs = neg ? -value : value;
  const str = abs.toString().padStart(scale + 1, "0");
  if (scale === 0) return `${neg && abs > 0n ? "-" : ""}${str}`;
  const intPart = str.slice(0, str.length - scale);
  const fracPart = str.slice(str.length - scale);
  return `${neg && abs > 0n ? "-" : ""}${intPart}.${fracPart}`;
}

/** Exact decimal-string addition using BigInt (no floating-point precision loss). */
export function addDecimalStrings(a: string, b: string): string {
  const pa = parseDecimalToBigInt(a);
  const pb = parseDecimalToBigInt(b);
  if (!pa && !pb) return "0";
  if (!pa) return b.trim();
  if (!pb) return a.trim();
  const scale = Math.max(pa.scale, pb.scale);
  const va = pa.value * 10n ** BigInt(scale - pa.scale);
  const vb = pb.value * 10n ** BigInt(scale - pb.scale);
  return formatBigIntDecimal(va + vb, scale);
}

/** Exact kg <-> t conversion when prime_coat and tack_coat use different mass units. */
export function convertMassDecimal(value: string, fromUnit: string, toUnit: string): string {
  if (fromUnit === toUnit) return value;
  const parsed = parseDecimalToBigInt(value);
  if (!parsed) return value;
  if (fromUnit === "t" && toUnit === "kg") {
    const newScale = Math.max(0, parsed.scale - 3);
    const factor = parsed.scale < 3 ? 10n ** BigInt(3 - parsed.scale) : 1n;
    return formatBigIntDecimal(parsed.value * factor, newScale);
  }
  if (fromUnit === "kg" && toUnit === "t") {
    return formatBigIntDecimal(parsed.value, parsed.scale + 3);
  }
  return value;
}

/**
 * Prepares the presentation catalog by hiding individual binder/topka & prime/tack items
 * and inserting a single combined `prime_tack_total` item where prime/tack first appeared.
 */
export function mergeCoatCatalog(catalog: CatalogItem[]): { items: CatalogItem[]; coatUnit: string; coatDecimals: number } {
  const primeItem = catalog.find((c) => c.key === "prime_coat");
  const tackItem = catalog.find((c) => c.key === "tack_coat");
  const existingCombined = catalog.find((c) => c.key === COMBINED_COAT_KEY);

  const coatUnit = existingCombined?.output_unit ?? primeItem?.output_unit ?? tackItem?.output_unit ?? "kg";
  const coatDecimals = existingCombined?.decimals ?? Math.max(primeItem?.decimals ?? 1, tackItem?.decimals ?? 1);

  const items: CatalogItem[] = [];
  let combinedInserted = false;

  for (const item of catalog) {
    if (item.key === COMBINED_COAT_KEY) {
      if (!combinedInserted) {
        items.push(item);
        combinedInserted = true;
      }
      continue;
    }
    if (COAT_SOURCE_KEYS.has(item.key)) {
      if (!combinedInserted && !existingCombined) {
        items.push({
          key: COMBINED_COAT_KEY,
          title_fa: COMBINED_COAT_TITLE,
          description_fa: "جمع پریمکت و تک‌کت",
          dimension: item.dimension,
          output_unit: coatUnit,
          decimals: coatDecimals,
          is_rollup: true,
          rollup_of: ["prime_coat", "tack_coat"],
          mining_only: false,
        });
        combinedInserted = true;
      }
      continue;
    }
    if (item.is_rollup && item.key !== "asphalt_total") continue;
    if (PRESENTATION_EXCLUDED_KEYS.has(item.key)) continue;
    items.push(item);
  }

  return { items, coatUnit, coatDecimals };
}

function rowEntityKey(row: ResultRow): string {
  if (row.scope === "company") return `company:${row.company_id ?? row.company ?? ""}`;
  if (row.scope === "site") return `site:${row.site_id ?? row.site ?? ""}`;
  return "holding";
}

/**
 * Combines `prime_coat` and `tack_coat` rows per entity (`holding`, `company`, or `site`)
 * into a single `prime_tack_total` row using exact decimal-string arithmetic.
 */
export function mergeCoatResultRows(rows: ResultRow[], targetUnit = "kg", targetDecimals = 1): ResultRow[] {
  const result: ResultRow[] = [];
  const grouped = new Map<string, ResultRow>();

  for (const row of rows) {
    if (!COAT_SOURCE_KEYS.has(row.item_key)) {
      result.push(row);
      continue;
    }
    const entityKey = rowEntityKey(row);
    const convertedQty = convertMassDecimal(row.qty || "0", row.unit, targetUnit);
    const existing = grouped.get(entityKey);
    if (!existing) {
      grouped.set(entityKey, {
        ...row,
        item_key: COMBINED_COAT_KEY,
        item: COMBINED_COAT_TITLE,
        unit: targetUnit,
        decimals: Math.max(row.decimals, targetDecimals),
        qty: convertedQty,
      });
    } else {
      grouped.set(entityKey, {
        ...existing,
        decimals: Math.max(existing.decimals, row.decimals, targetDecimals),
        sort: Math.min(existing.sort, row.sort),
        qty: addDecimalStrings(existing.qty, convertedQty),
        n_lines: existing.n_lines + row.n_lines,
        has_unconfirmed: existing.has_unconfirmed || row.has_unconfirmed,
      });
    }
  }

  for (const merged of grouped.values()) {
    result.push(merged);
  }
  return result;
}

function splitBalanced<T>(items: T[], maxPerGroup: number): T[][] {
  const n = items.length;
  if (n === 0) return [];
  if (n <= maxPerGroup) return [items];

  const groupCount = Math.ceil(n / maxPerGroup);
  const base = Math.floor(n / groupCount);
  const extra = n % groupCount;
  const groups: T[][] = [];
  let cursor = 0;

  for (let i = 0; i < groupCount; i += 1) {
    const size = i < extra ? base + 1 : base;
    groups.push(items.slice(cursor, cursor + size));
    cursor += size;
  }
  return groups;
}

export type SummaryVariant =
  | "departments"
  | "hero_bento"
  | "infographic"
  | "split_rows"
  | "aligned_split"
  | "classic";

export interface SummaryVariantOption {
  id: SummaryVariant;
  label: string;
}

export const SUMMARY_VARIANTS: SummaryVariantOption[] = [
  { id: "departments", label: "ایده ۱: ۴ پنل موضوعی" },
  { id: "hero_bento", label: "ایده ۲: Bento شاخص" },
  { id: "infographic", label: "ایده ۳: داشبورد حجمی" },
  { id: "split_rows", label: "ایده ۴: فهرست دو ستونه" },
  { id: "aligned_split", label: "ایده ۵: کارت متقارن دوطرفه" },
  { id: "classic", label: "دیزاین قبلی: کارت‌های متوازن" },
];

export const DEFAULT_SUMMARY_VARIANT: SummaryVariant = "departments";

export function isSummaryVariant(value: string | null | undefined): value is SummaryVariant {
  return Boolean(value && SUMMARY_VARIANTS.some((v) => v.id === value));
}

/** Splits catalog metrics across horizontal rows so no sparse single-item orphan row appears. */
export function splitSummaryRows<T>(items: T[], maxPerRow = 4): T[][] {
  return splitBalanced(items, maxPerRow);
}

/**
 * Splits share chart items evenly across slides (max 8 per slide by default)
 * so slides stay symmetrical (e.g. 12 items -> [6, 6] instead of [8, 4]).
 */
export function splitSharePages<T>(items: T[], maxPerSlide = 8): T[][] {
  if (items.length === 0) return [[]];
  return splitBalanced(items, maxPerSlide);
}

export interface SummaryDepartmentGroup {
  id: "earthwork" | "asphalt" | "concrete" | "infrastructure";
  title: string;
  items: CatalogItem[];
}

const SUMMARY_DEPARTMENTS: {
  id: SummaryDepartmentGroup["id"];
  title: string;
  keys: string[];
}[] = [
  {
    id: "earthwork",
    title: "عملیات خاکی و زیرسازی",
    keys: ["excavation", "fill", "subbase", "base"],
  },
  {
    id: "asphalt",
    title: "آسفالت و قیرپاشی",
    keys: ["asphalt_total", "prime_tack_total"],
  },
  {
    id: "concrete",
    title: "بتن و سازه‌های فنی",
    keys: ["concrete", "rebar", "formwork", "precast"],
  },
  {
    id: "infrastructure",
    title: "معدن و تأسیسات",
    keys: ["mining_load", "pipe_laying", "pile_drilling"],
  },
];

/** Returns the concise Persian engineering group label for any catalog key. */
export function getSummaryDepartmentTitle(key: string): string {
  for (const dept of SUMMARY_DEPARTMENTS) {
    if (dept.keys.includes(key)) return dept.title;
  }
  return "تجمیع هلدینگ";
}

/**
 * Organizes presentation catalog items into 4 thematic engineering departments
 * for the balanced 2x2 executive summary slide. Any unrecognized catalog keys append
 * to the fourth panel so no metric is ever dropped.
 */
export function groupSummaryDepartments(items: CatalogItem[]): SummaryDepartmentGroup[] {
  const byKey = new Map(items.map((item) => [item.key, item]));
  const assigned = new Set<string>();
  const groups: SummaryDepartmentGroup[] = [];

  for (const dept of SUMMARY_DEPARTMENTS) {
    const matched: CatalogItem[] = [];
    for (const key of dept.keys) {
      const found = byKey.get(key);
      if (found) {
        matched.push(found);
        assigned.add(key);
      }
    }
    groups.push({ id: dept.id, title: dept.title, items: matched });
  }

  const remaining = items.filter((item) => !assigned.has(item.key));
  if (remaining.length > 0) {
    groups[groups.length - 1]!.items.push(...remaining);
  }

  return groups.filter((group) => group.items.length > 0);
}

export interface SummaryTypography {
  numberFontPx: number;
  unitFontPx: number;
  wideTitleFontPx: number;
  titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }>;
}

/** Approximates rendered width in `em` for Persian digits/separators & Persian letters. */
function estimateTextEm(text: string, isNumeric: boolean): number {
  let em = 0;
  for (const ch of text) {
    if (ch === "\u200c") continue;
    if (ch === "٬" || ch === "٫" || ch === "." || ch === ",") em += 0.3;
    else if (ch === " ") em += 0.25;
    else if (isNumeric) em += 0.6;
    else em += 0.42;
  }
  return Math.max(em, 1);
}

/**
 * Deterministic fallback sizing for the 2x2 grouped department panels on the 1472x699 canvas,
 * keeping a unified number scale across all 4 panels with zero clipping or overflow.
 */
export function estimateSummaryTypography(
  groups: SummaryDepartmentGroup[],
  holdingMap: Map<string, ResultRow>,
): SummaryTypography {
  const panelCols = groups.length <= 1 ? 1 : 2;
  const panelRows = Math.max(Math.ceil(groups.length / panelCols), 1);
  const panelW = (SUMMARY_CANVAS_W - (panelCols - 1) * SUMMARY_GAP) / panelCols;
  const panelH = (SUMMARY_CANVAS_H - (panelRows - 1) * SUMMARY_GAP) / panelRows;
  const headerH = 44;
  const bodyH = Math.max(panelH - headerH - 2, 160);

  const unitFontPx = 12.5;
  const wideTitleFontPx = Math.min(26, Math.max(20, Math.round(bodyH * 0.088)));
  const halfBaseTitlePx = Math.min(23, Math.max(18, Math.round(bodyH * 0.078)));

  const titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }> = {};
  let maxNumberPx = 68;

  for (const group of groups) {
    const count = Math.max(group.items.length, 1);
    const innerRows = count === 1 ? 1 : Math.ceil(count / 2);
    const cellH = (bodyH - (innerRows - 1)) / innerRows;
    const isSingleCol = count <= 2;

    for (let idx = 0; idx < group.items.length; idx += 1) {
      const item = group.items[idx]!;
      const isWide = isSingleCol || (idx === 0 && count % 2 === 1);
      const cellW = isWide ? panelW - 2 : (panelW - 3) / 2;
      const padX = isWide ? 48 : 36;
      const padY = isWide ? 24 : 20;
      const innerW = Math.max(cellW - padX, 120);
      const innerH = Math.max(cellH - padY, 64);

      const title = item.key === "asphalt_total" ? "آسفالت" : item.title_fa;
      const badgeReserve = item.key === "asphalt_total" ? 90 : 0;
      const unitReserve = isWide ? 0 : 76;
      const availTitleW = Math.max(innerW - badgeReserve - unitReserve - 8, 80);

      if (isWide) {
        const titleSpecPx = Math.min(
          wideTitleFontPx,
          Math.floor((innerW * 0.56 - badgeReserve) / estimateTextEm(title, false)),
        );
        titleFontByKey[item.key] = { fontPx: Math.max(18, titleSpecPx), singleLine: true };
      } else {
        const maxSingle = Math.floor(availTitleW / estimateTextEm(title, false));
        if (maxSingle >= halfBaseTitlePx) {
          titleFontByKey[item.key] = { fontPx: halfBaseTitlePx, singleLine: true };
        } else if (maxSingle >= 16) {
          titleFontByKey[item.key] = { fontPx: maxSingle, singleLine: true };
        } else {
          titleFontByKey[item.key] = { fontPx: 16, singleLine: false };
        }
      }

      const resultRow = holdingMap.get(item.key);
      if (resultRow) {
        const formatted = formatPresentationQuantity(resultRow.qty);
        if (formatted !== "—") {
          const numEm = estimateTextEm(formatted, true);
          const availNumW = isWide ? innerW * 0.44 : innerW - 4;
          const fitW = Math.floor(availNumW / numEm);
          const titleSpec = titleFontByKey[item.key]!;
          const titleH = titleSpec.singleLine ? titleSpec.fontPx * 1.3 : titleSpec.fontPx * 1.25 * 2;
          const fitH = isWide ? Math.floor(innerH * 0.85) : Math.floor(innerH - titleH - 8);
          maxNumberPx = Math.min(maxNumberPx, fitW, fitH);
        }
      }
    }
  }

  return {
    numberFontPx: Math.min(68, Math.max(26, maxNumberPx)),
    unitFontPx,
    wideTitleFontPx,
    titleFontByKey,
  };
}

function parsePositiveQty(row: ResultRow | undefined): number {
  if (!row) return 0;
  const n = Number.parseFloat(row.qty || "0");
  return Number.isFinite(n) && n > 0 ? n : 0;
}

/** Counts distinct companies with positive actual volume per catalog item key. */
export function countActiveCompaniesByItem(companyRows: ResultRow[]): Map<string, number> {
  const byItem = new Map<string, Set<string>>();
  for (const row of companyRows) {
    if (parsePositiveQty(row) <= 0) continue;
    const entity = row.company_id ?? row.company;
    if (!entity) continue;
    let set = byItem.get(row.item_key);
    if (!set) {
      set = new Set();
      byItem.set(row.item_key, set);
    }
    set.add(entity);
  }
  const counts = new Map<string, number>();
  for (const [key, set] of byItem.entries()) counts.set(key, set.size);
  return counts;
}

export interface ClassicSummaryTypography {
  numberFontPx: number;
  unitFontPx: number;
  titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }>;
}

/** Deterministic fallback sizing for the balanced multi-row KPI cards (`classic` design). */
export function estimateClassicSummaryTypography(
  rows: CatalogItem[][],
  holdingMap: Map<string, ResultRow>,
): ClassicSummaryTypography {
  const rowCount = Math.max(rows.length, 1);
  const cardH = (SUMMARY_CANVAS_H - (rowCount - 1) * SUMMARY_GAP) / rowCount;
  const unitFontPx = 13;
  const baseTitlePx = Math.min(24, Math.max(18, Math.round(cardH * 0.145)));
  const titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }> = {};
  let maxNumberPx = Math.min(70, Math.round(cardH * 0.43));

  for (const row of rows) {
    const colCount = Math.max(row.length, 1);
    const cardW = (SUMMARY_CANVAS_W - (colCount - 1) * SUMMARY_GAP) / colCount;
    const innerW = Math.max(cardW - 44, 140);
    const innerH = Math.max(cardH - 36, 90);

    for (const item of row) {
      const title = item.key === "asphalt_total" ? "آسفالت (بیندر + توپکا)" : item.title_fa;
      const availTitleW = Math.max(innerW - 78, 90);
      const fitTitle = Math.floor(availTitleW / estimateTextEm(title, false));
      const spec =
        fitTitle >= baseTitlePx
          ? { fontPx: baseTitlePx, singleLine: true }
          : fitTitle >= 16
            ? { fontPx: fitTitle, singleLine: true }
            : { fontPx: Math.max(15, Math.min(18, fitTitle * 1.6)), singleLine: false };
      titleFontByKey[item.key] = spec;

      const rowResult = holdingMap.get(item.key);
      if (rowResult) {
        const formatted = formatPresentationQuantity(rowResult.qty);
        if (formatted !== "—") {
          const fitW = Math.floor((innerW - 8) / estimateTextEm(formatted, true));
          const titleH = spec.singleLine ? spec.fontPx * 1.3 : spec.fontPx * 1.25 * 2;
          const fitH = Math.floor(innerH - titleH - 18);
          maxNumberPx = Math.min(maxNumberPx, fitW, fitH);
        }
      }
    }
  }

  return {
    numberFontPx: Math.min(70, Math.max(28, maxNumberPx)),
    unitFontPx,
    titleFontByKey,
  };
}

export interface BentoCellPlan {
  item: CatalogItem;
  colSpan: 1 | 2;
  isHero: boolean;
}

export interface BentoGridPlan {
  cols: number;
  rows: number;
  cells: BentoCellPlan[];
  inactiveItems: CatalogItem[];
}

const HERO_PRIORITY_KEYS = ["excavation", "fill", "asphalt_total", "concrete", "base", "subbase", "rebar"];

/**
 * Packs active metrics into an exact zero-hole rectangular Bento grid (`cols x rows`)
 * by promoting flagship engineering metrics to `colSpan: 2` when `cols * rows > N`,
 * while moving zero-value metrics to a compact footer strip.
 */
export function planSymmetricBentoGrid(
  items: CatalogItem[],
  holdingMap: Map<string, ResultRow>,
): BentoGridPlan {
  const active = items.filter((item) => parsePositiveQty(holdingMap.get(item.key)) > 0);
  const inactive = items.filter((item) => parsePositiveQty(holdingMap.get(item.key)) <= 0);
  const source = active.length > 0 ? active : items;
  const inactiveItems = active.length > 0 ? inactive : [];
  const n = source.length;

  if (n === 0) {
    return { cols: 1, rows: 1, cells: [], inactiveItems: [] };
  }

  let cols = 4;
  let rows = 3;
  if (n <= 3) {
    cols = n;
    rows = 1;
  } else if (n === 4) {
    cols = 2;
    rows = 2;
  } else if (n <= 6) {
    cols = 3;
    rows = 2;
  } else if (n <= 8) {
    cols = 4;
    rows = 2;
  } else if (n <= 12) {
    cols = 4;
    rows = 3;
  } else if (n <= 15) {
    cols = 5;
    rows = 3;
  } else {
    cols = 5;
    rows = Math.ceil(n / 5);
  }

  const deficit = Math.max(0, cols * rows - n);
  const heroTarget = Math.max(deficit, n <= 4 ? 1 : n <= 8 ? 2 : 3);
  const ranked = source
    .map((item, idx) => {
      const pIdx = HERO_PRIORITY_KEYS.indexOf(item.key);
      return { item, rank: pIdx >= 0 ? pIdx : 100 + idx };
    })
    .sort((a, b) => a.rank - b.rank);

  const heroKeys = new Set(ranked.slice(0, Math.min(heroTarget, n)).map((r) => r.item.key));
  const wideKeys = new Set(ranked.slice(0, Math.min(deficit, n)).map((r) => r.item.key));

  const wideQueue = source.filter((item) => wideKeys.has(item.key));
  const normalQueue = source.filter((item) => !wideKeys.has(item.key));
  const cells: BentoCellPlan[] = [];

  for (let r = 0; r < rows; r += 1) {
    let remainingCols = cols;
    if (wideQueue.length > 0 && remainingCols >= 2) {
      const wideItem = wideQueue.shift()!;
      cells.push({ item: wideItem, colSpan: 2, isHero: true });
      remainingCols -= 2;
    }
    while (remainingCols > 0 && normalQueue.length > 0) {
      const normalItem = normalQueue.shift()!;
      cells.push({
        item: normalItem,
        colSpan: 1,
        isHero: heroKeys.has(normalItem.key),
      });
      remainingCols -= 1;
    }
  }

  return { cols, rows, cells, inactiveItems };
}

export interface InfographicBarItem {
  item: CatalogItem;
  row: ResultRow | undefined;
  numericQty: number;
  formattedQty: string;
  barPct: number;
  sharePctLabel: string;
}

export interface InfographicPlan {
  m3Items: InfographicBarItem[];
  otherItems: { item: CatalogItem; row: ResultRow | undefined; formattedQty: string }[];
  inactiveItems: CatalogItem[];
  maxM3: number;
}

/** Splits holding metrics into proportional cubic-meter bars (`m3`) vs non-volume KPI cards. */
export function splitInfographicItems(
  items: CatalogItem[],
  holdingMap: Map<string, ResultRow>,
): InfographicPlan {
  const m3Raw: InfographicBarItem[] = [];
  const otherItems: { item: CatalogItem; row: ResultRow | undefined; formattedQty: string }[] = [];
  const inactiveItems: CatalogItem[] = [];

  for (const item of items) {
    const row = holdingMap.get(item.key);
    const qty = parsePositiveQty(row);
    if (qty <= 0) {
      inactiveItems.push(item);
      continue;
    }
    if (item.output_unit === "m3") {
      m3Raw.push({
        item,
        row,
        numericQty: qty,
        formattedQty: formatPresentationQuantity(row!.qty),
        barPct: 0,
        sharePctLabel: "۰٪",
      });
    } else {
      otherItems.push({
        item,
        row,
        formattedQty: formatPresentationQuantity(row!.qty),
      });
    }
  }

  m3Raw.sort((a, b) => b.numericQty - a.numericQty);
  const maxM3 = m3Raw[0]?.numericQty ?? 0;
  const totalM3 = m3Raw.reduce((acc, entry) => acc + entry.numericQty, 0);
  const m3Items = m3Raw.map((entry) => {
    const sharePct = totalM3 > 0 ? Math.round((entry.numericQty / totalM3) * 100) : 0;
    return {
      ...entry,
      barPct: maxM3 > 0 ? Math.max(4, Math.round((entry.numericQty / maxM3) * 100)) : 0,
      sharePctLabel: sharePct === 0 && entry.numericQty > 0 ? "زیر ۱٪" : `${toFa(sharePct)}٪`,
    };
  });

  if (m3Items.length === 0 && otherItems.length === 0) {
    return {
      m3Items: [],
      otherItems: items.map((item) => ({ item, row: undefined, formattedQty: "—" })),
      inactiveItems: [],
      maxM3: 0,
    };
  }

  return { m3Items, otherItems, inactiveItems, maxM3 };
}

export interface ExecutiveSplitRow {
  item: CatalogItem;
  row: ResultRow | undefined;
  formattedQty: string;
  activeCompanyCount: number;
  planFormatted: string | null;
  planPct: number | null;
}

export interface ExecutiveSplitPlan {
  columns: ExecutiveSplitRow[][];
  inactiveItems: CatalogItem[];
}

/** Organizes holding metrics into two balanced executive row lists with real company counts & plan attainment. */
export function buildExecutiveSplitColumns(
  items: CatalogItem[],
  holdingMap: Map<string, ResultRow>,
  holdingPlannedMap: Map<string, ResultRow>,
  companyRows: ResultRow[],
): ExecutiveSplitPlan {
  const companyCounts = countActiveCompaniesByItem(companyRows);
  const activeSource: CatalogItem[] = [];
  const inactiveItems: CatalogItem[] = [];

  for (const item of items) {
    if (parsePositiveQty(holdingMap.get(item.key)) > 0) activeSource.push(item);
    else inactiveItems.push(item);
  }

  const effectiveSource = activeSource.length > 0 ? activeSource : items;
  const effectiveInactive = activeSource.length > 0 ? inactiveItems : [];

  const enriched: ExecutiveSplitRow[] = effectiveSource.map((item) => {
    const row = holdingMap.get(item.key);
    const actualQty = parsePositiveQty(row);
    const planRow = holdingPlannedMap.get(item.key);
    const planQty = parsePositiveQty(planRow);
    const planPct = planQty > 0 ? Math.round((actualQty / planQty) * 100) : null;
    return {
      item,
      row,
      formattedQty: row ? formatPresentationQuantity(row.qty) : "—",
      activeCompanyCount: companyCounts.get(item.key) ?? 0,
      planFormatted: planQty > 0 && planRow ? formatPresentationQuantity(planRow.qty) : null,
      planPct,
    };
  });

  const maxPerCol = Math.max(1, Math.ceil(enriched.length / 2));
  const columns = splitBalanced(enriched, maxPerCol);
  return { columns, inactiveItems: effectiveInactive };
}

export interface ScorecardTypography {
  tableHeightPx: number;
  entityColW: number;
  headerHeightPx: number;
  rowHeightPx: number;
  headerTitlePx: number;
  headerUnitPx: number;
  headerEntityPx: number;
  entityNamePx: number;
  entitySubPx: number;
  logoSizePx: number;
  cellValuePx: number;
  totalValuePx: number;
  totalLabelPx: number;
  planTextPx: number;
}

export interface ScorecardEstimateInput {
  metricTitles: string[];
  metricUnits: string[];
  entityNames: string[];
  entityType: "company" | "project";
  rowCount: number;
  showTotal: boolean;
  hasSubtitles: boolean;
  hasPlanned: boolean;
  maxFormattedValue: string;
  maxPlannedText?: string;
  canvasW?: number;
  canvasH?: number;
}

/**
 * Computes balanced table geometry and maximally readable typography for ScorecardTable
 * so company and project scorecards fill slide space with zero horizontal/vertical overflow.
 */
export function estimateScorecardTypography(input: ScorecardEstimateInput): ScorecardTypography {
  const canvasW = input.canvasW ?? SUMMARY_CANVAS_W;
  const canvasH = input.canvasH ?? SUMMARY_CANVAS_H;
  const metricCount = Math.max(input.metricTitles.length, 1);
  const totalDataRows = Math.max(input.rowCount + (input.showTotal ? 1 : 0), 1);

  const entityRatio = metricCount <= 6 ? 0.22 : metricCount <= 9 ? 0.19 : 0.165;
  const entityColW = Math.round(Math.max(216, Math.min(320, canvasW * entityRatio)));
  const metricColW = (canvasW - 2 - entityColW) / metricCount;
  const innerMetricW = Math.max(metricColW - 8, 48);

  const headerHeightPx = Math.round(
    Math.min(100, Math.max(68, canvasH * (totalDataRows <= 6 ? 0.14 : totalDataRows <= 8 ? 0.12 : 0.105))),
  );
  const tableHeightPx = Math.min(canvasH, headerHeightPx + totalDataRows * 145);
  const rowHeightPx = Math.max(40, Math.floor((tableHeightPx - headerHeightPx - 2) / totalDataRows));

  const maxUnitEm = input.metricUnits.reduce((acc, u) => Math.max(acc, estimateTextEm(u, false)), 3);
  const maxHeaderUnitW = Math.floor(innerMetricW / maxUnitEm);
  const headerUnitPx = Math.max(11, Math.min(15, maxHeaderUnitW, Math.round(headerHeightPx * 0.16)));

  let headerTitleCapW = 22;
  for (const title of input.metricTitles) {
    const words = title.split(/\s+/).filter(Boolean);
    for (const word of words) {
      headerTitleCapW = Math.min(headerTitleCapW, Math.floor(innerMetricW / estimateTextEm(word, false)));
    }
    const fullEm = estimateTextEm(title, false);
    headerTitleCapW = Math.min(headerTitleCapW, Math.floor((innerMetricW * 1.85) / fullEm));
  }
  const headerTitleCapH = Math.floor((headerHeightPx - headerUnitPx * 1.25 - 16) / (2 * 1.2));
  const headerTitlePx = Math.max(12, Math.min(21, headerTitleCapW, headerTitleCapH));

  const planText = input.maxPlannedText ?? `برنامه: ${input.maxFormattedValue}`;
  const planTextPx = input.hasPlanned
    ? Math.max(10, Math.min(14, Math.floor(innerMetricW / estimateTextEm(planText, true)), Math.floor(rowHeightPx * 0.2)))
    : 11;

  const numText = input.maxFormattedValue && input.maxFormattedValue !== "—" ? input.maxFormattedValue : "۱۰٬۰۰۰";
  const fitCellW = Math.floor(innerMetricW / estimateTextEm(numText, true));
  const vertCellBudget = rowHeightPx - (input.hasPlanned ? Math.ceil(planTextPx * 1.35) + 10 : 12);
  const fitCellH = Math.floor(vertCellBudget * 0.68);
  const cellValuePx = Math.max(13, Math.min(34, fitCellW, fitCellH));
  const totalValuePx = Math.max(14, Math.min(34, fitCellW, Math.max(cellValuePx, Math.min(cellValuePx + 1, fitCellH))));

  const hasLogo = input.entityType === "company";
  const logoSizePx = hasLogo ? Math.max(24, Math.min(48, Math.round((rowHeightPx - 12) * 0.44))) : 0;
  const innerEntityW = Math.max(entityColW - (hasLogo ? logoSizePx + 30 : 24), 90);
  const longestEntity = input.entityNames.reduce((a, b) => (b.length > a.length ? b : a), "شرکت نمونه");
  const entityEm = estimateTextEm(longestEntity, false);
  const fitEntityW = Math.floor((innerEntityW * 1.85) / entityEm);
  const entitySubPx = input.hasSubtitles ? Math.max(11, Math.min(14, Math.round(rowHeightPx * 0.2))) : 12;
  const entityVertBudget = rowHeightPx - (input.hasSubtitles ? Math.ceil(entitySubPx * 1.3) + 10 : 12);
  const entityNamePx = Math.max(14, Math.min(23, fitEntityW, Math.floor(entityVertBudget * 0.55)));
  const headerEntityPx = Math.max(15, Math.min(22, headerTitlePx + 3));
  const totalLabelPx = Math.max(15, Math.min(23, entityNamePx + 1));

  return {
    tableHeightPx,
    entityColW,
    headerHeightPx,
    rowHeightPx,
    headerTitlePx,
    headerUnitPx,
    headerEntityPx,
    entityNamePx,
    entitySubPx,
    logoSizePx,
    cellValuePx,
    totalValuePx,
    totalLabelPx,
    planTextPx,
  };
}

export interface PieContributionInput {
  companyId: string;
  companyName: string;
  pct: number;
  color: string;
}

export interface PieSliceLayout {
  companyId: string;
  companyName: string;
  color: string;
  pctRounded: number;
  isFullCircle: boolean;
  pathD: string;
  labelX: number;
  labelY: number;
  labelText: string;
  labelFontPx: number;
  isOutside: boolean;
}

export interface ShareCardGeometry {
  cols: number;
  rows: number;
  pieSizePx: number;
  titlePx: number;
  totalPx: number;
  unitPx: number;
}

/**
 * Computes responsive grid column/row counts and large filled-pie dimensions
 * for a single share slide inside the 1472x699 canvas body.
 */
export function estimateShareCardGeometry(
  cardCountOnSlide: number,
  canvasW = SUMMARY_CANVAS_W,
  canvasH = SUMMARY_CANVAS_H,
): ShareCardGeometry {
  const n = Math.max(cardCountOnSlide, 1);
  const cols = n <= 3 ? n : n === 4 ? 2 : n <= 6 ? 3 : 4;
  const rows = Math.ceil(n / cols);
  const cardW = (canvasW - (cols - 1) * SUMMARY_GAP) / cols;
  const cardH = (canvasH - (rows - 1) * SUMMARY_GAP) / rows;
  const headerH = rows === 1 ? 52 : 46;
  const chartBoxW = Math.max(cardW - 24, 160);
  const chartBoxH = Math.max(cardH - headerH - 22, 160);
  const pieSizePx = Math.max(160, Math.min(460, Math.floor(Math.min(chartBoxW, chartBoxH) - 6)));
  const compact = cols >= 4;
  return {
    cols,
    rows,
    pieSizePx,
    titlePx: compact ? 17 : rows === 1 ? 23 : 19,
    totalPx: compact ? 17 : rows === 1 ? 22 : 19,
    unitPx: compact ? 11.5 : 13,
  };
}

/**
 * Computes SVG wedge paths and inside percentage label coordinates for filled pie charts,
 * staggering adjacent narrow slices radially and keeping tiny <3% labels crisp outside the rim.
 */
export function computePieSlices(contributions: PieContributionInput[], size: number): PieSliceLayout[] {
  if (contributions.length === 0) return [];
  const center = size / 2;

  if (contributions.length === 1) {
    const only = contributions[0]!;
    const pctRounded = 100;
    return [
      {
        companyId: only.companyId,
        companyName: only.companyName,
        color: only.color,
        pctRounded,
        isFullCircle: true,
        pathD: "",
        labelX: center,
        labelY: center,
        labelText: `${toFa(pctRounded)}٪`,
        labelFontPx: Math.max(20, Math.min(38, Math.round(size * 0.145))),
        isOutside: false,
      },
    ];
  }

  const totalPct = contributions.reduce((sum, c) => sum + c.pct, 0) || 100;
  const hasTinySlice = contributions.some((c) => c.pct > 0 && (c.pct / totalPct) * 360 < 10);
  const radius = Math.max(40, size / 2 - (hasTinySlice ? 24 : 3));

  const result: PieSliceLayout[] = [];
  let cumDeg = -90;
  let prevStaggered = false;

  for (const c of contributions) {
    const sweepDeg = (c.pct / totalPct) * 360;
    const startRad = (cumDeg * Math.PI) / 180;
    const endRad = ((cumDeg + sweepDeg) * Math.PI) / 180;
    const midRad = ((cumDeg + sweepDeg / 2) * Math.PI) / 180;
    cumDeg += sweepDeg;

    const pctRounded = c.pct > 0 ? Math.max(1, Math.round(c.pct)) : 0;
    const labelText = `${toFa(pctRounded)}٪`;

    if (sweepDeg >= 359.95) {
      result.push({
        companyId: c.companyId,
        companyName: c.companyName,
        color: c.color,
        pctRounded: 100,
        isFullCircle: true,
        pathD: "",
        labelX: center,
        labelY: center,
        labelText: `${toFa(100)}٪`,
        labelFontPx: Math.max(18, Math.min(36, Math.round(size * 0.14))),
        isOutside: false,
      });
      prevStaggered = false;
      continue;
    }

    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);
    const largeArc = sweepDeg > 180 ? 1 : 0;
    const pathD = `M ${center.toFixed(2)} ${center.toFixed(2)} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${radius.toFixed(2)} ${radius.toFixed(2)} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;

    let isOutside = false;
    let rFrac = 0.58;
    let labelFontPx = 18;

    if (sweepDeg < 10) {
      isOutside = true;
      rFrac = 1.09;
      labelFontPx = Math.max(11, Math.min(14, Math.round(size * 0.05)));
      prevStaggered = false;
    } else if (sweepDeg < 28) {
      rFrac = prevStaggered ? 0.64 : 0.78;
      labelFontPx = Math.max(11, Math.min(16, Math.round(size * 0.058)));
      prevStaggered = !prevStaggered;
    } else if (sweepDeg < 72) {
      rFrac = 0.66;
      labelFontPx = Math.max(13, Math.min(22, Math.round(size * 0.08)));
      prevStaggered = false;
    } else if (sweepDeg < 180) {
      rFrac = 0.56;
      labelFontPx = Math.max(15, Math.min(26, Math.round(size * 0.095)));
      prevStaggered = false;
    } else {
      rFrac = sweepDeg > 250 ? 0.36 : 0.46;
      labelFontPx = Math.max(17, Math.min(30, Math.round(size * 0.11)));
      prevStaggered = false;
    }

    result.push({
      companyId: c.companyId,
      companyName: c.companyName,
      color: c.color,
      pctRounded,
      isFullCircle: false,
      pathD,
      labelX: center + radius * rFrac * Math.cos(midRad),
      labelY: center + radius * rFrac * Math.sin(midRad),
      labelText,
      labelFontPx,
      isOutside,
    });
  }

  return result;
}

export interface CompanyLogoAsset {
  match: string[];
  src: string;
  label: string;
}

export const COMPANY_LOGOS: CompanyLogoAsset[] = [
  { match: ["فراگیر", "faragir"], src: "/volume-reports/logo_faragir.png", label: "فراگیر عمران نصر" },
  { match: ["سیستان", "sistan"], src: "/volume-reports/logo_sistan.png", label: "جهاد نصر سیستان" },
  { match: ["گلومک", "golomak"], src: "/volume-reports/logo_golomak.png", label: "گلومک سازه نصر" },
  { match: ["آبادگران", "abadgaran"], src: "/volume-reports/logo_abadgaran.png", label: "آبادگران رفاه نصر" },
  { match: ["محورگستر", "محور گستر", "mehvar"], src: "/volume-reports/logo_mehvar.png", label: "محور گستر نصر" },
  { match: ["تژه", "tezhe"], src: "/volume-reports/logo_tezheh.png", label: "تژه نصر" },
];

const COMPANY_COLOR_PALETTE: { match: string[]; color: string }[] = [
  { match: ["محورگستر", "محور گستر", "mehvar"], color: "#252850" },
  { match: ["آبادگران", "abadgaran"], color: "#d97706" },
  { match: ["فراگیر", "faragir"], color: "#059669" },
  { match: ["گلومک", "golomak"], color: "#7c3aed" },
  { match: ["سیستان", "sistan"], color: "#0284c7" },
  { match: ["تژه", "tezhe"], color: "#e11d48" },
];

const COMPANY_FALLBACK_COLORS = [
  "#252850",
  "#d97706",
  "#059669",
  "#7c3aed",
  "#0284c7",
  "#e11d48",
  "#0891b2",
  "#ea580c",
  "#4f46e5",
  "#16a34a",
];

/** Finds matching static logo metadata for a subsidiary company name. */
export function matchCompanyLogo(name: string): CompanyLogoAsset | undefined {
  const normalized = name.toLocaleLowerCase("fa");
  return COMPANY_LOGOS.find((logo) => logo.match.some((part) => normalized.includes(part)));
}

/** Normalizes Persian/Arabic text and strips whitespace/punctuation for company identity checks. */
function normalizeCompanyMatchKey(name: string): string {
  return name
    .toLocaleLowerCase("fa")
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[\s\u200c\u200f\-_()（）]+/g, "");
}

/**
 * Excludes entities that must not render in Slide 2's outer ring:
 * Mehvar Gostar Nasr (shown in the center hub) and Jihad Nasr Kerman (removed from overview).
 */
export function isExcludedFromOverviewRing(name: string): boolean {
  const compact = normalizeCompanyMatchKey(name);
  if (compact.includes("محورگستر") || compact.includes("mehvar")) return true;
  if (compact.includes("جهادنصر") && compact.includes("کرمان")) return true;
  if (compact.includes("jihad") && compact.includes("kerman")) return true;
  return false;
}

export interface OverviewHoldingCompanyInput {
  id: string;
  name: string;
  projectCount: number;
}

function isTezheCompany(name: string): boolean {
  const compact = normalizeCompanyMatchKey(name);
  return compact.includes("تژه") || compact.includes("tezhe");
}

/**
 * Prepares Slide 2 outer ring companies: excludes Mehvar Gostar (center hub)
 * and Jihad Nasr Kerman, and always includes Tezhe ("عضو هلدینگ") even when
 * it has no volume-report rows or projects.
 */
export function buildOverviewWheelCompanies(
  reportCompanies: OverviewHoldingCompanyInput[],
  settingsCompanies: { id: string; name: string; is_active?: boolean }[] = [],
): OverviewHoldingCompanyInput[] {
  const filtered = reportCompanies.filter((c) => !isExcludedFromOverviewRing(c.name));
  if (!filtered.some((c) => isTezheCompany(c.name))) {
    const configuredTezhe = settingsCompanies.find(
      (c) => (c.is_active ?? true) && isTezheCompany(c.name) && !isExcludedFromOverviewRing(c.name),
    );
    filtered.push({
      id: configuredTezhe?.id ?? "overview-tezhe",
      name: configuredTezhe?.name ?? "تژه نصر",
      projectCount: 0,
    });
  }
  return filtered.sort((a, b) => a.name.localeCompare(b.name, "fa"));
}

/** Returns the consistent brand color assigned to a subsidiary across all presentation slides. */
export function getCompanyColor(name: string, index = 0): string {
  const normalized = name.toLocaleLowerCase("fa");
  const found = COMPANY_COLOR_PALETTE.find((item) => item.match.some((part) => normalized.includes(part)));
  return found?.color ?? COMPANY_FALLBACK_COLORS[index % COMPANY_FALLBACK_COLORS.length]!;
}

export interface OverviewRadarInput {
  id: string;
  name: string;
  color: string;
  projectCount: number;
  sublabel: string;
}

export interface OverviewRadarNode {
  id: string;
  name: string;
  color: string;
  projectCount: number;
  sublabel: string;
  angleDeg: number;
  x: number;
  y: number;
  spokeX1: number;
  spokeY1: number;
  spokeX2: number;
  spokeY2: number;
  cardW: number;
  logoSizePx: number;
  nameFontPx: number;
  badgeFontPx: number;
}

export interface OverviewRadarLayout {
  width: number;
  height: number;
  cx: number;
  originY: number;
  radius: number;
  primaryArcPath: string;
  innerArcPath: string;
  outerArcPath: string;
  hubArcPath: string;
  nodes: OverviewRadarNode[];
}

function semicircleArcPath(
  cx: number,
  cy: number,
  radius: number,
  startDeg: number,
  endDeg: number,
): string {
  const sRad = (startDeg * Math.PI) / 180;
  const eRad = (endDeg * Math.PI) / 180;
  const x1 = cx + radius * Math.cos(sRad);
  const y1 = cy + radius * Math.sin(sRad);
  const x2 = cx + radius * Math.cos(eRad);
  const y2 = cy + radius * Math.sin(eRad);
  const sweep = startDeg - endDeg;
  const largeArc = sweep > 180 ? 1 : 0;
  // Counter-clockwise sweep (0) draws the lower semicircular arc below the top-center hub.
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${radius.toFixed(2)} ${radius.toFixed(2)} 0 ${largeArc} 0 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

function resolveRadarAngles(count: number): number[] {
  if (count <= 0) return [];
  if (count === 1) return [90];
  if (count === 2) return [125, 55];
  if (count === 3) return [145, 90, 35];
  if (count === 4) return [155, 112, 68, 25];
  if (count === 5) return [160, 125, 90, 55, 20];
  return Array.from({ length: count }, (_, idx) => {
    const start = 164;
    const end = 16;
    return Math.round((start - ((start - end) * idx) / (count - 1)) * 10) / 10;
  });
}

/**
 * Computes geometry for Slide 2's top-down semi-circular Holding Arc/Radar diagram:
 * Mother card anchored at top-center with subsidiary cards distributed downward along
 * a semicircular orbit (`x = cx + R cos(θ)`, `y = originY + R sin(θ)`).
 */
export function computeOverviewRadarLayout(
  companies: OverviewRadarInput[],
  width = SUMMARY_CANVAS_W,
  height = SUMMARY_CANVAS_H - 5,
): OverviewRadarLayout {
  const cx = width / 2;
  const originY = Math.round(height * 0.19);
  const spokeStartY = Math.round(height * 0.26);
  const radius = Math.min(Math.round(height * 0.605), Math.round(width * 0.34));
  const n = companies.length;
  const angles = resolveRadarAngles(n);

  let cardW = 196;
  let logoSizePx = 74;
  let nameFontPx = 15.5;
  let badgeFontPx = 12.5;
  if (n === 6) {
    cardW = 178;
    logoSizePx = 62;
    nameFontPx = 14.5;
    badgeFontPx = 12;
  } else if (n === 7 || n === 8) {
    cardW = 156;
    logoSizePx = 52;
    nameFontPx = 13.5;
    badgeFontPx = 11.5;
  } else if (n > 8) {
    cardW = 136;
    logoSizePx = 44;
    nameFontPx = 12.5;
    badgeFontPx = 11;
  }

  const nodes: OverviewRadarNode[] = companies.map((company, idx) => {
    const angleDeg = angles[idx]!;
    const rad = (angleDeg * Math.PI) / 180;
    const x = Math.round((cx + radius * Math.cos(rad)) * 100) / 100;
    const y = Math.round((originY + radius * Math.sin(rad)) * 100) / 100;
    return {
      ...company,
      angleDeg,
      x,
      y,
      spokeX1: cx,
      spokeY1: spokeStartY,
      spokeX2: x,
      spokeY2: y,
      cardW,
      logoSizePx,
      nameFontPx,
      badgeFontPx,
    };
  });

  const primaryStartDeg = n >= 2 ? angles[0]! : 160;
  const primaryEndDeg = n >= 2 ? angles[n - 1]! : 20;

  return {
    width,
    height,
    cx,
    originY,
    radius,
    primaryArcPath: semicircleArcPath(cx, originY, radius, primaryStartDeg, primaryEndDeg),
    innerArcPath: semicircleArcPath(cx, originY, Math.round(radius * 0.72), 165, 15),
    outerArcPath: semicircleArcPath(cx, originY, radius + 62, 165, 15),
    hubArcPath: semicircleArcPath(cx, originY, Math.round(radius * 0.48), 165, 15),
    nodes,
  };
}

/**
 * Formats the weekly report period string shown beside the «کارنامه شرکت‌ها» slide title, e.g.:
 * «گزارش هفتگی هلدینگ عمرانی از تاریخ چهارشنبه ۱۴۰۵/۰۸/۱۳ تا تاریخ سه‌شنبه ۱۴۰۵/۰۸/۱۹».
 */
export function formatCompanyScorecardPeriodNote(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string | null {
  const start = formatJalaliDateWithWeekday(startIso);
  const end = formatJalaliDateWithWeekday(endIso);
  if (start === "—" && end === "—") return null;
  if (start !== "—" && end !== "—") {
    return `گزارش هفتگی هلدینگ عمرانی از تاریخ ${start} تا تاریخ ${end}`;
  }
  return `گزارش هفتگی هلدینگ عمرانی · ${start !== "—" ? start : end}`;
}
