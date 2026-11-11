"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { runSoon } from "../lib/defer";
import { unitLabel } from "../lib/format";
import { toFa } from "../lib/jalali";
import {
  SUMMARY_VARIANTS,
  buildExecutiveSplitColumns,
  countActiveCompaniesByItem,
  estimateClassicSummaryTypography,
  estimateSummaryTypography,
  formatPresentationQuantity,
  getSummaryDepartmentTitle,
  groupSummaryDepartments,
  planSymmetricBentoGrid,
  splitInfographicItems,
  splitSummaryRows,
  type BentoCellPlan,
  type ClassicSummaryTypography,
  type ExecutiveSplitRow,
  type InfographicBarItem,
  type SummaryDepartmentGroup,
  type SummaryTypography,
  type SummaryVariant,
} from "../lib/presentation";
import type { CatalogItem, ResultRow } from "../types";

function formatMetricTitle(item: CatalogItem): string {
  return item.key === "asphalt_total" ? "آسفالت" : item.title_fa;
}

export function fitTextMaxPx(probe: HTMLSpanElement, text: string, minPx: number, maxPx: number, maxWidth: number): number {
  let lo = minPx;
  let hi = maxPx;
  let best = minPx;
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    probe.style.fontSize = `${mid}px`;
    probe.textContent = text;
    if (probe.offsetWidth <= maxWidth) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return best;
}

function AsphaltBadge({ muted = false, dark = false }: { muted?: boolean; dark?: boolean }) {
  return (
    <span
      className={`shrink-0 rounded-md border px-2 py-0.5 text-[10.5px] font-bold leading-tight ${
        dark
          ? "border-[#fed836]/35 bg-[#fed836]/15 text-[#fed836]"
          : muted
            ? "border-slate-200 bg-slate-100 text-slate-400"
            : "border-[#252850]/15 bg-[#252850]/[0.05] text-[#252850]/85"
      }`}
    >
      بیندر + توپکا
    </span>
  );
}

function UnitBadge({
  unit,
  fontPx = 12.5,
  muted = false,
  dark = false,
}: {
  unit: string;
  fontPx?: number;
  muted?: boolean;
  dark?: boolean;
}) {
  return (
    <span
      className={`inline-flex w-fit shrink-0 items-center rounded-lg border px-2.5 py-0.5 font-bold leading-tight ${
        dark
          ? "border-white/20 bg-white/10 text-white"
          : muted
            ? "border-slate-200 bg-slate-100 text-slate-400"
            : "border-[#252850]/15 bg-[#252850]/[0.05] text-[#252850]"
      }`}
      style={{ fontSize: `${fontPx}px` }}
    >
      {unitLabel(unit)}
    </span>
  );
}

function InactiveItemsStrip({ items }: { items: CatalogItem[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 rounded-2xl border border-[#252850]/10 bg-white/85 px-4 py-2">
      <span className="text-[12px] font-extrabold text-slate-500">بدون عملکرد در این دوره:</span>
      {items.map((item) => (
        <span
          key={item.key}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[12px] font-bold text-slate-500"
        >
          <span>{formatMetricTitle(item)}</span>
          <span className="text-[10.5px] text-slate-400">({unitLabel(item.output_unit)})</span>
        </span>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Idea 1: 4 Engineering Department Panels (Default)                          */
/* -------------------------------------------------------------------------- */

function SummaryMetricCell({
  item,
  row,
  typography,
  wide,
  spanTwoCols,
  bodyRef,
}: {
  item: CatalogItem;
  row: ResultRow | undefined;
  typography: SummaryTypography;
  wide: boolean;
  spanTwoCols: boolean;
  bodyRef: (el: HTMLDivElement | null) => void;
}) {
  const empty = !row;
  const title = formatMetricTitle(item);
  const titleSpec = typography.titleFontByKey[item.key] ?? { fontPx: wide ? 24 : 21, singleLine: true };
  const valueText = row ? formatPresentationQuantity(row.qty) : "—";
  const valueFontPx = empty ? Math.min(typography.numberFontPx, 46) : typography.numberFontPx;

  return (
    <div
      className={`min-h-0 min-w-0 ${spanTwoCols ? "col-span-2" : ""} ${
        empty ? "bg-slate-50/75" : "bg-white"
      }`}
    >
      {wide ? (
        <div
          ref={bodyRef}
          data-wide="1"
          className="flex h-full min-h-0 items-center justify-between gap-4"
          style={{ paddingInline: "24px", paddingBlock: "12px" }}
        >
          <div className="flex min-w-0 flex-col justify-center gap-1.5">
            <div className="flex items-center gap-2">
              <p
                className={`font-black leading-snug ${titleSpec.singleLine ? "whitespace-nowrap" : ""} ${
                  empty ? "text-slate-400" : "text-[#252850]"
                }`}
                style={{ fontSize: `${titleSpec.fontPx}px`, lineHeight: 1.25 }}
              >
                {title}
              </p>
              {item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
            </div>
            <UnitBadge unit={item.output_unit} fontPx={typography.unitFontPx} muted={empty} />
          </div>
          <p
            className={`shrink-0 whitespace-nowrap font-black leading-none tabular-nums ${
              empty ? "text-slate-300" : "text-[#252850]"
            }`}
            style={{ fontSize: `${valueFontPx}px` }}
          >
            {valueText}
          </p>
        </div>
      ) : (
        <div
          ref={bodyRef}
          data-wide="0"
          className="flex h-full min-h-0 flex-col justify-between gap-1"
          style={{ paddingInline: "18px", paddingBlock: "10px" }}
        >
          <div className="flex shrink-0 items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-1.5">
              <p
                className={`font-extrabold leading-snug ${titleSpec.singleLine ? "whitespace-nowrap" : ""} ${
                  empty ? "text-slate-400" : "text-[#252850]"
                }`}
                style={{ fontSize: `${titleSpec.fontPx}px`, lineHeight: 1.25 }}
              >
                {title}
              </p>
              {item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
            </div>
            <UnitBadge unit={item.output_unit} fontPx={typography.unitFontPx} muted={empty} />
          </div>
          <div className="flex min-h-0 flex-1 items-center">
            <p
              className={`whitespace-nowrap font-black leading-none tabular-nums ${
                empty ? "text-slate-300" : "text-[#252850]"
              }`}
              style={{ fontSize: `${valueFontPx}px` }}
            >
              {valueText}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryDepartmentPanel({
  group,
  holdingMap,
  typography,
  setCellBodyRef,
}: {
  group: SummaryDepartmentGroup;
  holdingMap: Map<string, ResultRow>;
  typography: SummaryTypography;
  setCellBodyRef: (key: string) => (el: HTMLDivElement | null) => void;
}) {
  const count = group.items.length;
  const isSingleCol = count <= 2;
  const innerRows = count === 1 ? 1 : isSingleCol ? 2 : Math.ceil(count / 2);
  const activeCount = group.items.filter((item) => holdingMap.has(item.key)).length;

  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-[#252850]/15 bg-white shadow-sm">
      <div className="flex h-11 shrink-0 items-center justify-between bg-[#252850] px-5 text-white">
        <div className="flex items-center gap-2.5">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#fed836]" />
          <h3 className="text-[17px] font-black leading-none">{group.title}</h3>
        </div>
        <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11.5px] font-bold leading-none text-white/85 tabular-nums">
          {activeCount === count ? `${toFa(count)} شاخص` : `${toFa(activeCount)} از ${toFa(count)} فعال`}
        </span>
      </div>

      <div
        className="grid min-h-0 flex-1 gap-px bg-slate-200/80"
        style={{
          gridTemplateColumns: `repeat(${isSingleCol ? 1 : 2}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${innerRows}, minmax(0, 1fr))`,
        }}
      >
        {group.items.map((item, idx) => {
          const isWide = isSingleCol || (idx === 0 && count % 2 === 1);
          const spanTwoCols = !isSingleCol && isWide;
          return (
            <SummaryMetricCell
              key={item.key}
              item={item}
              row={holdingMap.get(item.key)}
              typography={typography}
              wide={isWide}
              spanTwoCols={spanTwoCols}
              bodyRef={setCellBodyRef(item.key)}
            />
          );
        })}
      </div>
    </div>
  );
}

function DepartmentsSummaryView({ items, holdingMap }: { items: CatalogItem[]; holdingMap: Map<string, ResultRow> }) {
  const groups = useMemo(() => groupSummaryDepartments(items), [items]);
  const fallback = useMemo(() => estimateSummaryTypography(groups, holdingMap), [groups, holdingMap]);
  const measurementKey = useMemo(
    () =>
      groups
        .map(
          (g) =>
            `${g.id}:${g.items.map((i) => `${i.key}=${holdingMap.get(i.key) ? formatPresentationQuantity(holdingMap.get(i.key)!.qty) : "-"}`).join(",")}`,
        )
        .join("|"),
    [groups, holdingMap],
  );

  const [measured, setMeasured] = useState<{ key: string; typography: SummaryTypography } | null>(null);
  const probeRef = useRef<HTMLSpanElement | null>(null);
  const cellBodyRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const setCellBodyRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      if (el) cellBodyRefs.current.set(key, el);
      else cellBodyRefs.current.delete(key);
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const probe = probeRef.current;
      if (!probe || items.length === 0) return;

      const cellMetrics: {
        item: CatalogItem;
        bodyW: number;
        bodyH: number;
        isWide: boolean;
        title: string;
        qtyText: string;
        hasBadge: boolean;
      }[] = [];

      for (const group of groups) {
        for (const item of group.items) {
          const bodyEl = cellBodyRefs.current.get(item.key);
          if (!bodyEl || bodyEl.clientWidth === 0 || bodyEl.clientHeight === 0) return;
          const row = holdingMap.get(item.key);
          cellMetrics.push({
            item,
            bodyW: bodyEl.clientWidth,
            bodyH: bodyEl.clientHeight,
            isWide: bodyEl.getAttribute("data-wide") === "1",
            title: formatMetricTitle(item),
            qtyText: row ? formatPresentationQuantity(row.qty) : "—",
            hasBadge: item.key === "asphalt_total",
          });
        }
      }
      if (cellMetrics.length === 0) return;

      const unitFontPx = 12.5;
      const minHalfH = Math.min(...cellMetrics.map((m) => m.bodyH));
      const wideTitleFontPx = Math.min(26, Math.max(20, Math.round(minHalfH * 0.21)));
      const halfBaseTitlePx = Math.min(23, Math.max(18, Math.round(minHalfH * 0.185)));

      probe.style.fontWeight = "700";
      probe.style.fontVariantNumeric = "normal";
      probe.style.fontSize = "11.5px";
      probe.textContent = "بیندر + توپکا";
      const badgeReserve = probe.offsetWidth + 24;

      const titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }> = {};
      let maxNumPx = 68;

      for (const m of cellMetrics) {
        probe.style.fontWeight = "700";
        probe.style.fontSize = `${unitFontPx}px`;
        probe.textContent = unitLabel(m.item.output_unit);
        const unitReserve = probe.offsetWidth + 28;

        if (m.isWide) {
          probe.style.fontWeight = "900";
          const availWideTitleW = Math.max(m.bodyW * 0.52 - (m.hasBadge ? badgeReserve : 0), 100);
          const fitPx = fitTextMaxPx(probe, m.title, 18, wideTitleFontPx, availWideTitleW);
          titleFontByKey[m.item.key] = { fontPx: fitPx, singleLine: true };
          maxNumPx = Math.min(maxNumPx, Math.floor(m.bodyH * 0.68));
        } else {
          probe.style.fontWeight = "800";
          const availTitleW = Math.max(m.bodyW - unitReserve - (m.hasBadge ? badgeReserve : 0) - 44, 70);
          probe.style.fontSize = `${halfBaseTitlePx}px`;
          probe.textContent = m.title;

          let spec: { fontPx: number; singleLine: boolean };
          if (probe.offsetWidth <= availTitleW) {
            spec = { fontPx: halfBaseTitlePx, singleLine: true };
          } else {
            probe.style.fontSize = "16px";
            if (probe.offsetWidth <= availTitleW) {
              spec = { fontPx: fitTextMaxPx(probe, m.title, 16, halfBaseTitlePx, availTitleW), singleLine: true };
            } else {
              spec = { fontPx: fitTextMaxPx(probe, m.title, 14, 18, availTitleW * 1.75), singleLine: false };
            }
          }
          titleFontByKey[m.item.key] = spec;

          const titleH = spec.singleLine ? Math.ceil(spec.fontPx * 1.3) : Math.ceil(spec.fontPx * 1.25 * 2);
          const vertBudget = Math.floor(m.bodyH - titleH - 26);
          maxNumPx = Math.min(maxNumPx, Math.max(26, vertBudget));
        }
      }

      probe.style.fontWeight = "900";
      probe.style.fontVariantNumeric = "tabular-nums";
      let bestNumPx = Math.min(68, Math.max(26, maxNumPx));

      for (const m of cellMetrics) {
        if (m.qtyText === "—") continue;
        const padX = m.isWide ? 48 : 36;
        const availW = m.isWide ? Math.max((m.bodyW - padX) * 0.44, 120) : Math.max(m.bodyW - padX - 4, 80);
        bestNumPx = Math.min(bestNumPx, fitTextMaxPx(probe, m.qtyText, 20, bestNumPx, availW));
      }

      setMeasured({
        key: measurementKey,
        typography: {
          numberFontPx: bestNumPx,
          unitFontPx,
          wideTitleFontPx,
          titleFontByKey,
        },
      });
    };

    const cancelSoon = runSoon(measure);
    void document.fonts?.ready.then(measure);

    return () => {
      cancelled = true;
      cancelSoon();
    };
  }, [groups, holdingMap, items.length, measurementKey]);

  const typography = measured?.key === measurementKey ? measured.typography : fallback;
  const panelCols = groups.length <= 1 ? 1 : 2;
  const panelRows = Math.max(Math.ceil(groups.length / panelCols), 1);

  return (
    <div
      className="relative grid min-h-0 flex-1 gap-4"
      style={{
        gridTemplateColumns: `repeat(${panelCols}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${panelRows}, minmax(0, 1fr))`,
      }}
    >
      <span
        ref={probeRef}
        aria-hidden="true"
        className="pointer-events-none invisible absolute -top-[9999px] left-0 whitespace-nowrap"
      />
      {groups.map((group) => (
        <SummaryDepartmentPanel
          key={group.id}
          group={group}
          holdingMap={holdingMap}
          typography={typography}
          setCellBodyRef={setCellBodyRef}
        />
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Previous Balanced-Cards Design (`classic`)                                 */
/* -------------------------------------------------------------------------- */

function ClassicSummaryView({ items, holdingMap }: { items: CatalogItem[]; holdingMap: Map<string, ResultRow> }) {
  const rows = useMemo(() => splitSummaryRows(items, 4), [items]);
  const fallback = useMemo(() => estimateClassicSummaryTypography(rows, holdingMap), [rows, holdingMap]);
  const measurementKey = useMemo(
    () =>
      items
        .map((i) => `${i.key}=${holdingMap.get(i.key) ? formatPresentationQuantity(holdingMap.get(i.key)!.qty) : "-"}`)
        .join("|"),
    [holdingMap, items],
  );

  const [measured, setMeasured] = useState<{ key: string; typography: ClassicSummaryTypography } | null>(null);
  const probeRef = useRef<HTMLSpanElement | null>(null);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const setCardRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      if (el) cardRefs.current.set(key, el);
      else cardRefs.current.delete(key);
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const probe = probeRef.current;
      if (!probe || items.length === 0) return;

      const cardMetrics: { item: CatalogItem; w: number; h: number; title: string; qtyText: string; hasBadge: boolean }[] = [];
      for (const item of items) {
        const el = cardRefs.current.get(item.key);
        if (!el || el.clientWidth === 0 || el.clientHeight === 0) return;
        const row = holdingMap.get(item.key);
        cardMetrics.push({
          item,
          w: el.clientWidth,
          h: el.clientHeight,
          title: formatMetricTitle(item),
          qtyText: row ? formatPresentationQuantity(row.qty) : "—",
          hasBadge: item.key === "asphalt_total",
        });
      }
      if (cardMetrics.length === 0) return;

      const unitFontPx = 13;
      const minH = Math.min(...cardMetrics.map((m) => m.h));
      const baseTitlePx = Math.min(24, Math.max(18, Math.round(minH * 0.15)));

      probe.style.fontWeight = "700";
      probe.style.fontVariantNumeric = "normal";
      probe.style.fontSize = "11px";
      probe.textContent = "بیندر + توپکا";
      const badgeReserve = probe.offsetWidth + 24;

      const titleFontByKey: Record<string, { fontPx: number; singleLine: boolean }> = {};
      let maxNumPx = Math.min(70, Math.round(minH * 0.44));

      for (const m of cardMetrics) {
        probe.style.fontWeight = "700";
        probe.style.fontSize = `${unitFontPx}px`;
        probe.textContent = unitLabel(m.item.output_unit);
        const unitReserve = probe.offsetWidth + 28;
        const availTitleW = Math.max(m.w - 44 - unitReserve - (m.hasBadge ? badgeReserve : 0), 80);

        probe.style.fontWeight = "900";
        probe.style.fontSize = `${baseTitlePx}px`;
        probe.textContent = m.title;

        let spec: { fontPx: number; singleLine: boolean };
        if (probe.offsetWidth <= availTitleW) {
          spec = { fontPx: baseTitlePx, singleLine: true };
        } else {
          probe.style.fontSize = "16px";
          if (probe.offsetWidth <= availTitleW) {
            spec = { fontPx: fitTextMaxPx(probe, m.title, 16, baseTitlePx, availTitleW), singleLine: true };
          } else {
            spec = { fontPx: fitTextMaxPx(probe, m.title, 14, 18, availTitleW * 1.75), singleLine: false };
          }
        }
        titleFontByKey[m.item.key] = spec;

        const titleH = spec.singleLine ? Math.ceil(spec.fontPx * 1.3) : Math.ceil(spec.fontPx * 1.25 * 2);
        maxNumPx = Math.min(maxNumPx, Math.floor(m.h - titleH - 44));
      }

      probe.style.fontWeight = "900";
      probe.style.fontVariantNumeric = "tabular-nums";
      let bestNumPx = Math.min(70, Math.max(28, maxNumPx));

      for (const m of cardMetrics) {
        if (m.qtyText === "—") continue;
        bestNumPx = Math.min(bestNumPx, fitTextMaxPx(probe, m.qtyText, 24, bestNumPx, Math.max(m.w - 48, 90)));
      }

      setMeasured({
        key: measurementKey,
        typography: {
          numberFontPx: bestNumPx,
          unitFontPx,
          titleFontByKey,
        },
      });
    };

    const cancelSoon = runSoon(measure);
    void document.fonts?.ready.then(measure);

    return () => {
      cancelled = true;
      cancelSoon();
    };
  }, [holdingMap, items, measurementKey]);

  const typography = measured?.key === measurementKey ? measured.typography : fallback;

  return (
    <div className="relative flex min-h-0 flex-1 flex-col gap-4">
      <span
        ref={probeRef}
        aria-hidden="true"
        className="pointer-events-none invisible absolute -top-[9999px] left-0 whitespace-nowrap"
      />
      {rows.map((rowItems, rowIndex) => (
        <div
          key={`classic-row-${rowIndex}`}
          className="grid min-h-0 flex-1 gap-4"
          style={{ gridTemplateColumns: `repeat(${Math.max(rowItems.length, 1)}, minmax(0, 1fr))` }}
        >
          {rowItems.map((item) => {
            const row = holdingMap.get(item.key);
            const empty = !row;
            const titleSpec = typography.titleFontByKey[item.key] ?? { fontPx: 20, singleLine: true };
            const qtyText = row ? formatPresentationQuantity(row.qty) : "—";
            return (
              <div
                key={item.key}
                ref={setCardRef(item.key)}
                className={`flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border shadow-sm ${
                  empty ? "border-slate-200 bg-slate-50/80" : "border-[#252850]/15 bg-white"
                }`}
              >
                <div className={`h-1.5 shrink-0 ${empty ? "bg-slate-200" : "bg-[#252850]"}`} />
                <div className="flex min-h-0 flex-1 flex-col justify-between px-5 py-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                      <p
                        className={`font-black leading-snug ${titleSpec.singleLine ? "whitespace-nowrap" : ""} ${
                          empty ? "text-slate-400" : "text-[#252850]"
                        }`}
                        style={{ fontSize: `${titleSpec.fontPx}px`, lineHeight: 1.25 }}
                      >
                        {formatMetricTitle(item)}
                      </p>
                      {item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
                    </div>
                    <UnitBadge unit={item.output_unit} fontPx={typography.unitFontPx} muted={empty} />
                  </div>
                  <p
                    className={`whitespace-nowrap font-black leading-none tabular-nums ${
                      empty ? "text-slate-300" : "text-[#252850]"
                    }`}
                    style={{ fontSize: `${empty ? Math.min(typography.numberFontPx, 48) : typography.numberFontPx}px` }}
                  >
                    {qtyText}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Idea 2 (`hero_bento`) & Idea 5 (`aligned_split`): Symmetric Bento Views    */
/* -------------------------------------------------------------------------- */

function BentoVariantView({
  mode,
  items,
  holdingMap,
  companyRows,
}: {
  mode: "hero_bento" | "aligned_split";
  items: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  companyRows: ResultRow[];
}) {
  const plan = useMemo(() => planSymmetricBentoGrid(items, holdingMap), [holdingMap, items]);
  const companyCounts = useMemo(() => countActiveCompaniesByItem(companyRows), [companyRows]);

  const measurementKey = useMemo(
    () =>
      `${mode}:${plan.cells
        .map((c) => `${c.item.key}:${c.colSpan}=${holdingMap.get(c.item.key) ? formatPresentationQuantity(holdingMap.get(c.item.key)!.qty) : "-"}`)
        .join("|")}`,
    [holdingMap, mode, plan.cells],
  );

  const [measured, setMeasured] = useState<{
    key: string;
    regularNumPx: number;
    heroNumPx: number;
    titleByKey: Record<string, number>;
  } | null>(null);

  const probeRef = useRef<HTMLSpanElement | null>(null);
  const cellRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const setCellRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      if (el) cellRefs.current.set(key, el);
      else cellRefs.current.delete(key);
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const probe = probeRef.current;
      if (!probe || plan.cells.length === 0) return;

      const entries: {
        cell: BentoCellPlan;
        w: number;
        h: number;
        title: string;
        qtyText: string;
        bottomLabel: string;
      }[] = [];
      for (const cell of plan.cells) {
        const el = cellRefs.current.get(cell.item.key);
        if (!el || el.clientWidth === 0 || el.clientHeight === 0) return;
        const row = holdingMap.get(cell.item.key);
        const activeCount = companyCounts.get(cell.item.key) ?? 0;
        entries.push({
          cell,
          w: el.clientWidth,
          h: el.clientHeight,
          title: formatMetricTitle(cell.item),
          qtyText: row ? formatPresentationQuantity(row.qty) : "—",
          bottomLabel: activeCount > 0 ? `${toFa(activeCount)} شرکت فعال` : getSummaryDepartmentTitle(cell.item.key),
        });
      }
      if (entries.length === 0) return;

      const minH = Math.min(...entries.map((e) => e.h));
      const baseTitlePx = Math.min(23, Math.max(17, Math.round(minH * 0.145)));
      const titleByKey: Record<string, number> = {};

      probe.style.fontWeight = "700";
      probe.style.fontVariantNumeric = "normal";
      probe.style.fontSize = "11px";
      probe.textContent = "بیندر + توپکا";
      const badgeReserve = probe.offsetWidth + 24;

      let regularMax = Math.min(70, Math.round(minH * 0.44));
      let heroMax = Math.min(76, Math.round(minH * 0.48));

      for (const e of entries) {
        probe.style.fontWeight = "700";
        probe.style.fontSize = "12.5px";
        probe.textContent = unitLabel(e.cell.item.output_unit);
        const unitReserve = probe.offsetWidth + 28;
        const availTitleW = Math.max(
          e.w - 44 - unitReserve - (e.cell.item.key === "asphalt_total" ? badgeReserve : 0),
          85,
        );

        probe.style.fontWeight = "900";
        const targetTitlePx = e.cell.colSpan === 2 ? Math.min(25, baseTitlePx + 2) : baseTitlePx;
        const titlePx = fitTextMaxPx(probe, e.title, 15, targetTitlePx, availTitleW * 1.15);
        titleByKey[e.cell.item.key] = titlePx;

        const maxForHeight = Math.floor(e.h - titlePx * 1.4 - (mode === "aligned_split" ? 48 : 44));
        if (mode === "aligned_split" && e.cell.isHero) heroMax = Math.min(heroMax, maxForHeight);
        else regularMax = Math.min(regularMax, maxForHeight);
      }

      let regularNumPx = Math.max(26, regularMax);
      let heroNumPx = Math.max(28, heroMax);

      for (const e of entries) {
        if (e.qtyText === "—") continue;
        let subLabelReserve = 0;
        if (mode === "aligned_split") {
          probe.style.fontWeight = "700";
          probe.style.fontSize = "11.5px";
          probe.textContent = e.bottomLabel;
          subLabelReserve = Math.min(probe.offsetWidth + 14, 118);
        }
        probe.style.fontWeight = "900";
        probe.style.fontVariantNumeric = "tabular-nums";
        const availW = Math.max(e.w - 44 - subLabelReserve, 95);
        const capPx = mode === "aligned_split" && e.cell.isHero ? heroNumPx : regularNumPx;
        const fit = fitTextMaxPx(probe, e.qtyText, 22, capPx, availW);
        if (mode === "aligned_split" && e.cell.isHero) heroNumPx = Math.min(heroNumPx, fit);
        else regularNumPx = Math.min(regularNumPx, fit);
      }

      heroNumPx = mode === "hero_bento" ? regularNumPx : Math.max(regularNumPx, heroNumPx);
      setMeasured({
        key: measurementKey,
        regularNumPx,
        heroNumPx,
        titleByKey,
      });
    };

    const cancelSoon = runSoon(measure);
    void document.fonts?.ready.then(measure);

    return () => {
      cancelled = true;
      cancelSoon();
    };
  }, [companyCounts, holdingMap, measurementKey, mode, plan.cells]);

  const regularNumPx = measured?.key === measurementKey ? measured.regularNumPx : 46;
  const heroNumPx = measured?.key === measurementKey ? measured.heroNumPx : 52;

  return (
    <div className="relative flex min-h-0 flex-1 flex-col gap-3">
      <span
        ref={probeRef}
        aria-hidden="true"
        className="pointer-events-none invisible absolute -top-[9999px] left-0 whitespace-nowrap"
      />
      <div
        className="grid min-h-0 flex-1 gap-4"
        style={{
          gridTemplateColumns: `repeat(${plan.cols}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${plan.rows}, minmax(0, 1fr))`,
        }}
      >
        {plan.cells.map((cell) => {
          const { item, colSpan, isHero } = cell;
          const row = holdingMap.get(item.key);
          const empty = !row;
          const qtyText = row ? formatPresentationQuantity(row.qty) : "—";
          const titlePx = (measured?.key === measurementKey ? measured.titleByKey[item.key] : undefined) ?? 20;
          const darkCard = mode === "hero_bento" && !empty;
          const activeCompanies = companyCounts.get(item.key) ?? 0;

          if (mode === "aligned_split") {
            return (
              <div
                key={item.key}
                ref={setCellRef(item.key)}
                className={`flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border shadow-sm ${
                  colSpan === 2 ? "col-span-2" : ""
                } ${empty ? "border-slate-200 bg-slate-50/80" : "border-[#252850]/15 bg-white"}`}
              >
                <div className={`h-1.5 shrink-0 ${empty ? "bg-slate-200" : isHero ? "bg-[#fed836]" : "bg-[#252850]"}`} />
                <div className="flex min-h-0 flex-1 flex-col justify-between px-5 py-3.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                      <p
                        className={`font-black leading-snug ${empty ? "text-slate-400" : "text-[#252850]"}`}
                        style={{ fontSize: `${titlePx}px`, lineHeight: 1.25 }}
                      >
                        {formatMetricTitle(item)}
                      </p>
                      {item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
                    </div>
                    <UnitBadge unit={item.output_unit} muted={empty} />
                  </div>

                  <div className="flex items-end justify-between gap-2">
                    <span className="max-w-[118px] truncate text-[11.5px] font-bold text-slate-500 tabular-nums">
                      {activeCompanies > 0 ? `${toFa(activeCompanies)} شرکت فعال` : getSummaryDepartmentTitle(item.key)}
                    </span>
                    <p
                      dir="ltr"
                      className={`whitespace-nowrap text-left font-black leading-none tabular-nums ${
                        empty ? "text-slate-300" : "text-[#252850]"
                      }`}
                      style={{ fontSize: `${isHero ? heroNumPx : regularNumPx}px` }}
                    >
                      {qtyText}
                    </p>
                  </div>
                </div>
              </div>
            );
          }

          return (
            <div
              key={item.key}
              ref={setCellRef(item.key)}
              className={`flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border shadow-sm ${
                colSpan === 2 ? "col-span-2" : ""
              } ${
                darkCard
                  ? "border-[#252850] bg-[#252850] text-white"
                  : empty
                    ? "border-slate-200 bg-slate-50/80"
                    : "border-[#252850]/15 bg-white"
              }`}
            >
              <div
                className={`h-1.5 shrink-0 ${
                  darkCard ? "bg-[#fed836]" : empty ? "bg-slate-200" : "bg-[#252850]/85"
                }`}
              />
              <div className="flex min-h-0 flex-1 flex-col justify-between px-5 py-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <p
                      className={`font-black leading-snug ${
                        darkCard ? "text-white" : empty ? "text-slate-400" : "text-[#252850]"
                      }`}
                      style={{ fontSize: `${titlePx}px`, lineHeight: 1.25 }}
                    >
                      {formatMetricTitle(item)}
                    </p>
                    {item.key === "asphalt_total" && <AsphaltBadge muted={empty} dark={darkCard} />}
                  </div>
                  <UnitBadge unit={item.output_unit} muted={empty} dark={darkCard} />
                </div>

                <div className="flex min-h-0 items-center">
                  <p
                    className={`whitespace-nowrap font-black leading-none tabular-nums ${
                      darkCard ? "text-[#fed836]" : empty ? "text-slate-300" : "text-[#252850]"
                    }`}
                    style={{ fontSize: `${regularNumPx}px` }}
                  >
                    {qtyText}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <InactiveItemsStrip items={plan.inactiveItems} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Idea 3: Dual Infographic View (`m3` comparison bars + metric cards)        */
/* -------------------------------------------------------------------------- */

function InfographicBarRow({ entry, idx, dense }: { entry: InfographicBarItem; idx: number; dense: boolean }) {
  const isLeader = idx === 0;
  return (
    <div className="flex min-h-0 flex-1 flex-col justify-center gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span
            className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[12px] font-black tabular-nums ${
              isLeader ? "bg-[#fed836] text-[#252850]" : "bg-[#252850]/10 text-[#252850]"
            }`}
          >
            {toFa(idx + 1)}
          </span>
          <p className={`truncate font-black text-[#252850] ${dense ? "text-[17px]" : "text-[19px]"}`}>
            {formatMetricTitle(entry.item)}
          </p>
        </div>
        <div className="flex shrink-0 items-baseline gap-1.5">
          <span
            className={`font-black leading-none text-[#252850] tabular-nums ${
              dense ? "text-[24px]" : "text-[28px]"
            }`}
          >
            {entry.formattedQty}
          </span>
          <span className="text-[11.5px] font-bold text-slate-400">مترمکعب</span>
        </div>
      </div>
      <div className="flex items-center gap-2.5">
        <div className="h-3.5 min-w-0 flex-1 overflow-hidden rounded-full bg-[#252850]/[0.07]">
          <div
            className={`h-full rounded-full ${
              isLeader ? "bg-[#252850]" : idx <= 2 ? "bg-[#252850]/85" : "bg-[#252850]/65"
            }`}
            style={{ width: `${entry.barPct}%` }}
          />
        </div>
        <span className="w-12 shrink-0 text-left text-[12px] font-extrabold text-[#252850]/75 tabular-nums">
          {entry.sharePctLabel}
        </span>
      </div>
    </div>
  );
}

function InfographicSummaryView({ items, holdingMap }: { items: CatalogItem[]; holdingMap: Map<string, ResultRow> }) {
  const plan = useMemo(() => splitInfographicItems(items, holdingMap), [holdingMap, items]);
  const hasM3 = plan.m3Items.length > 0;
  const hasOther = plan.otherItems.length > 0;
  const otherCols = plan.otherItems.length <= 2 ? 1 : 2;
  const otherRows = plan.otherItems.length <= 2 ? Math.max(plan.otherItems.length, 1) : Math.ceil(plan.otherItems.length / 2);
  const denseBars = plan.m3Items.length > 6;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div
        className="grid min-h-0 flex-1 gap-5"
        style={{
          gridTemplateColumns: hasM3 && hasOther ? "1.18fr 1fr" : "1fr",
        }}
      >
        {hasM3 && (
          <div className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-[#252850]/15 bg-white shadow-sm">
            <div className="flex h-12 shrink-0 items-center justify-between bg-[#252850] px-5 text-white">
              <div className="flex items-center gap-2.5">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#fed836]" />
                <h3 className="text-[17px] font-black leading-none">مقایسه احجام خاکی و بتنی (مترمکعب)</h3>
              </div>
              <span className="rounded-full bg-white/10 px-3 py-1 text-[11.5px] font-bold text-white/90 tabular-nums">
                {toFa(plan.m3Items.length)} شاخص حجمی
              </span>
            </div>
            <div className="flex min-h-0 flex-1 flex-col justify-between divide-y divide-slate-100 px-6 py-3">
              {plan.m3Items.map((entry, idx) => (
                <InfographicBarRow key={entry.item.key} entry={entry} idx={idx} dense={denseBars} />
              ))}
            </div>
          </div>
        )}

        {hasOther && (
          <div className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-[#252850]/15 bg-white shadow-sm">
            <div className="flex h-12 shrink-0 items-center justify-between bg-[#252850] px-5 text-white">
              <div className="flex items-center gap-2.5">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#fed836]" />
                <h3 className="text-[17px] font-black leading-none">آسفالت، قیر، آرماتور و طولی</h3>
              </div>
              <span className="rounded-full bg-white/10 px-3 py-1 text-[11.5px] font-bold text-white/90 tabular-nums">
                {toFa(plan.otherItems.length)} شاخص
              </span>
            </div>
            <div
              className="grid min-h-0 flex-1 gap-px bg-slate-200/80"
              style={{
                gridTemplateColumns: `repeat(${otherCols}, minmax(0, 1fr))`,
                gridTemplateRows: `repeat(${otherRows}, minmax(0, 1fr))`,
              }}
            >
              {plan.otherItems.map((entry, idx) => {
                const isWide = otherCols === 2 && idx === 0 && plan.otherItems.length % 2 === 1;
                const empty = !entry.row;
                if (isWide) {
                  return (
                    <div
                      key={entry.item.key}
                      className="col-span-2 flex min-h-0 items-center justify-between gap-4 bg-white px-6 py-4"
                    >
                      <div className="flex min-w-0 flex-col justify-center gap-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className={`text-[23px] font-black leading-snug ${empty ? "text-slate-400" : "text-[#252850]"}`}>
                            {formatMetricTitle(entry.item)}
                          </p>
                          {entry.item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
                        </div>
                        <UnitBadge unit={entry.item.output_unit} muted={empty} />
                      </div>
                      <p
                        className={`shrink-0 whitespace-nowrap font-black leading-none tabular-nums ${
                          empty ? "text-slate-300" : "text-[#252850]"
                        }`}
                        style={{ fontSize: "60px" }}
                      >
                        {entry.formattedQty}
                      </p>
                    </div>
                  );
                }
                return (
                  <div
                    key={entry.item.key}
                    className="flex min-h-0 flex-col justify-between bg-white px-5 py-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                        <p className={`text-[19px] font-black leading-snug ${empty ? "text-slate-400" : "text-[#252850]"}`}>
                          {formatMetricTitle(entry.item)}
                        </p>
                        {entry.item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
                      </div>
                      <UnitBadge unit={entry.item.output_unit} muted={empty} />
                    </div>
                    <p
                      className={`whitespace-nowrap font-black leading-none tabular-nums ${
                        empty ? "text-slate-300" : "text-[#252850]"
                      }`}
                      style={{ fontSize: `${plan.otherItems.length <= 4 ? 56 : 52}px` }}
                    >
                      {entry.formattedQty}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <InactiveItemsStrip items={plan.inactiveItems} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Idea 4: Balanced Two-Column Executive List (`split_rows`)                  */
/* -------------------------------------------------------------------------- */

function ExecutiveSplitRowCell({ entry, numFontPx }: { entry: ExecutiveSplitRow; numFontPx: number }) {
  const empty = !entry.row;
  return (
    <div className="flex min-h-0 items-center justify-between gap-4 bg-white px-6 py-2.5">
      <div className="flex min-w-0 items-center gap-3.5">
        <span
          className={`h-10 w-1.5 shrink-0 rounded-full ${
            empty ? "bg-slate-200" : entry.item.key === "asphalt_total" ? "bg-[#fed836]" : "bg-[#252850]"
          }`}
        />
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className={`truncate text-[19px] font-black leading-snug ${empty ? "text-slate-400" : "text-[#252850]"}`}>
              {formatMetricTitle(entry.item)}
            </p>
            {entry.item.key === "asphalt_total" && <AsphaltBadge muted={empty} />}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] font-bold text-slate-500">
            <span>
              {entry.activeCompanyCount > 0 ? `مشارکت ${toFa(entry.activeCompanyCount)} شرکت` : getSummaryDepartmentTitle(entry.item.key)}
            </span>
            {entry.planPct !== null && (
              <span className="rounded-md border border-[#252850]/15 bg-[#fed836]/25 px-2 py-0.5 text-[11px] font-extrabold text-[#252850] tabular-nums">
                تحقق برنامه: {toFa(entry.planPct)}٪
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 flex-col items-end justify-center gap-1">
        <p
          className={`whitespace-nowrap font-black leading-none tabular-nums ${empty ? "text-slate-300" : "text-[#252850]"}`}
          style={{ fontSize: `${numFontPx}px` }}
        >
          {entry.formattedQty}
        </p>
        <span className="text-[12px] font-extrabold text-slate-500">{unitLabel(entry.item.output_unit)}</span>
      </div>
    </div>
  );
}

function SplitRowsSummaryView({
  items,
  holdingMap,
  holdingPlannedMap,
  companyRows,
}: {
  items: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  holdingPlannedMap: Map<string, ResultRow>;
  companyRows: ResultRow[];
}) {
  const plan = useMemo(
    () => buildExecutiveSplitColumns(items, holdingMap, holdingPlannedMap, companyRows),
    [companyRows, holdingMap, holdingPlannedMap, items],
  );
  const maxRows = Math.max(...plan.columns.map((c) => c.length), 1);
  const numFontPx = maxRows <= 5 ? 38 : maxRows === 6 ? 34 : 30;
  const activeTotal = plan.columns.reduce((acc, col) => acc + col.length, 0);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div
        className="grid min-h-0 flex-1 gap-5"
        style={{ gridTemplateColumns: `repeat(${Math.max(plan.columns.length, 1)}, minmax(0, 1fr))` }}
      >
        {plan.columns.map((col, colIdx) => (
          <div
            key={`split-col-${colIdx}`}
            className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-[#252850]/15 bg-white shadow-sm"
          >
            <div className="flex h-11 shrink-0 items-center justify-between bg-[#252850] px-6 text-white">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#fed836]" />
                <span className="text-[15.5px] font-black leading-none">عنوان شاخص و مشارکت</span>
              </div>
              <span className="text-[13px] font-bold text-white/80">حجم کل عملکرد</span>
            </div>
            <div
              className="grid min-h-0 flex-1 divide-y divide-slate-200/90"
              style={{ gridTemplateRows: `repeat(${maxRows}, minmax(0, 1fr))` }}
            >
              {col.map((entry) => (
                <ExecutiveSplitRowCell key={entry.item.key} entry={entry} numFontPx={numFontPx} />
              ))}
              {col.length < maxRows && (
                <div className="flex items-center justify-between bg-slate-50/75 px-6 text-[13px] font-bold text-slate-500">
                  <span>جمع شاخص‌های فعال هلدینگ</span>
                  <span className="rounded-full bg-[#252850]/10 px-3 py-1 text-[12.5px] font-black text-[#252850] tabular-nums">
                    {toFa(activeTotal)} از {toFa(items.length)} شاخص
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <InactiveItemsStrip items={plan.inactiveItems} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Public Dispatcher Component                                                */
/* -------------------------------------------------------------------------- */

export function SummaryVariantBar({
  variant,
  onSelect,
  onJumpToSlide,
  compact = false,
}: {
  variant: SummaryVariant;
  onSelect: (next: SummaryVariant) => void;
  onJumpToSlide?: () => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-2 ${
        compact ? "rounded-2xl border border-[#252850]/10 bg-white px-4 py-2.5 shadow-sm" : "border-t border-slate-100 pt-3"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-[#252850]">چیدمان خلاصه عملکرد هلدینگ:</span>
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="انتخاب چیدمان صفحه خلاصه عملکرد هلدینگ">
          {SUMMARY_VARIANTS.map((option) => {
            const active = option.id === variant;
            return (
              <button
                key={option.id}
                type="button"
                data-summary-variant={option.id}
                aria-pressed={active}
                onClick={() => onSelect(option.id)}
                className={`rounded-xl border px-3 py-1.5 text-xs font-bold transition ${
                  active
                    ? "border-[#252850] bg-[#252850] text-white shadow-sm"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:border-[#252850]/35 hover:bg-slate-100 hover:text-[#252850]"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
      {onJumpToSlide && (
        <button
          type="button"
          onClick={onJumpToSlide}
          className="shrink-0 rounded-xl border border-[#252850]/20 bg-[#fed836]/25 px-3 py-1.5 text-xs font-extrabold text-[#252850] transition hover:bg-[#fed836]/45"
        >
          مشاهده صفحه خلاصه
        </button>
      )}
    </div>
  );
}

export interface SummarySlideContentProps {
  variant: SummaryVariant;
  items: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  holdingPlannedMap: Map<string, ResultRow>;
  companyRows: ResultRow[];
}

export function SummarySlideContent({
  variant,
  items,
  holdingMap,
  holdingPlannedMap,
  companyRows,
}: SummarySlideContentProps) {
  switch (variant) {
    case "classic":
      return <ClassicSummaryView items={items} holdingMap={holdingMap} />;
    case "hero_bento":
      return <BentoVariantView mode="hero_bento" items={items} holdingMap={holdingMap} companyRows={companyRows} />;
    case "infographic":
      return <InfographicSummaryView items={items} holdingMap={holdingMap} />;
    case "split_rows":
      return (
        <SplitRowsSummaryView
          items={items}
          holdingMap={holdingMap}
          holdingPlannedMap={holdingPlannedMap}
          companyRows={companyRows}
        />
      );
    case "aligned_split":
      return <BentoVariantView mode="aligned_split" items={items} holdingMap={holdingMap} companyRows={companyRows} />;
    case "departments":
    default:
      return <DepartmentsSummaryView items={items} holdingMap={holdingMap} />;
  }
}
