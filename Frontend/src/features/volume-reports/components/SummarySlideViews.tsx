"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { runSoon } from "../lib/defer";
import { unitLabel } from "../lib/format";
import { toFa } from "../lib/jalali";
import {
  formatPresentationQuantity,
  planSymmetricBentoGrid,
  type BentoCellPlan,
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

export interface BentoSummaryViewProps {
  items: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  previousHoldingMap?: Map<string, ResultRow>;
  previousReportLabel?: string;
}

export function BentoSummaryView({
  items,
  holdingMap,
  previousHoldingMap,
  previousReportLabel,
}: BentoSummaryViewProps) {
  const plan = useMemo(() => planSymmetricBentoGrid(items, holdingMap), [holdingMap, items]);

  const measurementKey = useMemo(
    () =>
      `bento:${plan.cells
        .map((c) => `${c.item.key}:${c.colSpan}=${holdingMap.get(c.item.key) ? formatPresentationQuantity(holdingMap.get(c.item.key)!.qty) : "-"}`)
        .join("|")}`,
    [holdingMap, plan.cells],
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
      }[] = [];
      for (const cell of plan.cells) {
        const el = cellRefs.current.get(cell.item.key);
        if (!el || el.clientWidth === 0 || el.clientHeight === 0) return;
        const row = holdingMap.get(cell.item.key);
        entries.push({
          cell,
          w: el.clientWidth,
          h: el.clientHeight,
          title: formatMetricTitle(cell.item),
          qtyText: row ? formatPresentationQuantity(row.qty) : "—",
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

      // Reserve space for top stripe (6px), padding (32px), title (~30px), comparison footer (~38px), gaps (~16px)
      let regularMax = Math.min(62, Math.max(26, Math.round(minH * 0.36)));
      let heroMax = Math.min(68, Math.max(28, Math.round(minH * 0.40)));

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

        // Ensure vertical space leaves at least 38px for comparison footer
        const maxForHeight = Math.floor(e.h - titlePx * 1.35 - 76);
        regularMax = Math.min(regularMax, maxForHeight);
        heroMax = Math.min(heroMax, maxForHeight);
      }

      let regularNumPx = Math.max(26, regularMax);
      let heroNumPx = Math.max(28, heroMax);

      for (const e of entries) {
        if (e.qtyText === "—") continue;
        probe.style.fontWeight = "900";
        probe.style.fontVariantNumeric = "tabular-nums";
        const availW = Math.max(e.w - 44, 95);
        const capPx = e.cell.colSpan === 2 ? heroNumPx : regularNumPx;
        const fit = fitTextMaxPx(probe, e.qtyText, 22, capPx, availW);
        if (e.cell.colSpan === 2) heroNumPx = Math.min(heroNumPx, fit);
        else regularNumPx = Math.min(regularNumPx, fit);
      }

      heroNumPx = Math.max(regularNumPx, heroNumPx);
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
  }, [holdingMap, measurementKey, plan.cells]);

  const regularNumPx = measured?.key === measurementKey ? measured.regularNumPx : 44;
  const heroNumPx = measured?.key === measurementKey ? measured.heroNumPx : 50;

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
          const { item, colSpan } = cell;
          const row = holdingMap.get(item.key);
          const empty = !row;
          const qtyText = row ? formatPresentationQuantity(row.qty) : "—";
          const titlePx = (measured?.key === measurementKey ? measured.titleByKey[item.key] : undefined) ?? 20;
          const darkCard = !empty;

          // Comparison data with previous period
          const prevRow = previousHoldingMap?.get(item.key);
          const hasPrev = Boolean(prevRow && prevRow.qty);
          const prevQtyNum = prevRow ? Number.parseFloat(prevRow.qty || "0") : 0;
          const curQtyNum = row ? Number.parseFloat(row.qty || "0") : 0;
          const prevQtyText = hasPrev && prevQtyNum > 0 ? formatPresentationQuantity(prevRow!.qty) : hasPrev ? "۰" : "—";

          let trend: "up" | "down" | "flat" | "new" | "none" = "none";
          let pctText = "";
          if (hasPrev && prevQtyNum > 0) {
            const diff = curQtyNum - prevQtyNum;
            const pct = (diff / prevQtyNum) * 100;
            if (Math.abs(pct) < 0.5) {
              trend = "flat";
              pctText = "۰٪";
            } else if (pct > 0) {
              trend = "up";
              pctText = `${toFa(Math.round(pct))}٪+`;
            } else {
              trend = "down";
              pctText = `${toFa(Math.abs(Math.round(pct)))}٪-`;
            }
          } else if (curQtyNum > 0 && (!hasPrev || prevQtyNum === 0)) {
            trend = "new";
            pctText = "جدید";
          }

          return (
            <div
              key={item.key}
              ref={setCellRef(item.key)}
              className={`flex min-h-0 flex-col justify-between overflow-hidden rounded-2xl border shadow-md transition-shadow ${
                colSpan === 2 ? "col-span-2" : ""
              } ${
                darkCard
                  ? "border-[#1e2246] bg-[#252850] text-white"
                  : "border-slate-200 bg-slate-50/80 text-slate-400"
              }`}
            >
              <div
                className={`h-1.5 shrink-0 ${
                  darkCard ? "bg-[#fed836]" : "bg-slate-200"
                }`}
              />
              <div className="flex min-h-0 flex-1 flex-col justify-between px-5 py-4">
                {/* Header: Title + Unit */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <p
                      className={`font-black leading-snug ${
                        darkCard ? "text-white" : "text-slate-400"
                      }`}
                      style={{ fontSize: `${titlePx}px`, lineHeight: 1.25 }}
                    >
                      {formatMetricTitle(item)}
                    </p>
                    {item.key === "asphalt_total" && <AsphaltBadge muted={empty} dark={darkCard} />}
                  </div>
                  <UnitBadge unit={item.output_unit} muted={empty} dark={darkCard} />
                </div>

                {/* Main Value */}
                <div className="flex min-h-0 items-center py-2">
                  <p
                    className={`whitespace-nowrap font-black leading-none tabular-nums ${
                      darkCard ? "text-[#fed836]" : "text-slate-300"
                    }`}
                    style={{ fontSize: `${colSpan === 2 ? heroNumPx : regularNumPx}px` }}
                  >
                    {qtyText}
                  </p>
                </div>

                {/* Footer: Previous Week Comparison (open, unboxed layout with larger typography) */}
                {darkCard ? (
                  <div className="flex items-center justify-between border-t border-white/10 pt-2.5">
                    <div className="flex min-w-0 items-baseline gap-2">
                      <span className="text-[14px] font-medium text-white/65">هفته قبل:</span>
                      <span className="text-[18px] font-black text-white tabular-nums tracking-tight">{prevQtyText}</span>
                    </div>
                    {trend === "up" && (
                      <span className="inline-flex items-center gap-1 rounded-lg border border-emerald-400/40 bg-emerald-500/25 px-2.5 py-0.5 text-[13px] font-black text-emerald-300">
                        <span>▲</span>
                        <span className="tabular-nums">{pctText}</span>
                      </span>
                    )}
                    {trend === "down" && (
                      <span className="inline-flex items-center gap-1 rounded-lg border border-rose-400/40 bg-rose-500/25 px-2.5 py-0.5 text-[13px] font-black text-rose-300">
                        <span>▼</span>
                        <span className="tabular-nums">{pctText}</span>
                      </span>
                    )}
                    {trend === "flat" && (
                      <span className="inline-flex items-center rounded-lg border border-white/15 bg-white/10 px-2.5 py-0.5 text-[13px] font-bold text-white/70">
                        {pctText}
                      </span>
                    )}
                    {trend === "new" && (
                      <span className="inline-flex items-center rounded-lg border border-[#fed836]/40 bg-[#fed836]/25 px-2.5 py-0.5 text-[13px] font-bold text-[#fed836]">
                        {pctText}
                      </span>
                    )}
                    {trend === "none" && (
                      <span className="text-[14px] font-medium text-white/40">—</span>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-between border-t border-slate-200 pt-2.5">
                    <div className="flex min-w-0 items-baseline gap-2">
                      <span className="text-[14px] font-medium text-slate-400">هفته قبل:</span>
                      <span className="text-[18px] font-black text-slate-700 tabular-nums tracking-tight">{prevQtyText}</span>
                    </div>
                    <span className="text-[14px] font-medium text-slate-400">—</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <InactiveItemsStrip items={plan.inactiveItems} />
    </div>
  );
}

export interface SummarySlideContentProps {
  items: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  previousHoldingMap?: Map<string, ResultRow>;
  previousReportLabel?: string;
}

export function SummarySlideContent({
  items,
  holdingMap,
  previousHoldingMap,
  previousReportLabel,
}: SummarySlideContentProps) {
  return (
    <BentoSummaryView
      items={items}
      holdingMap={holdingMap}
      previousHoldingMap={previousHoldingMap}
      previousReportLabel={previousReportLabel}
    />
  );
}
