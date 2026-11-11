"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { CompanyProfileBody } from "../components/CompanyProfileSlide";
import { CompanyMark, HoldingRadialOverview } from "../components/HoldingRadialOverview";
import { SummarySlideContent, SummaryVariantBar, fitTextMaxPx } from "../components/SummarySlideViews";
import { ErrorBox, LoadingBlock } from "../components/common";
import { runSoon } from "../lib/defer";
import { unitLabel } from "../lib/format";
import { formatJalaliDate, formatWeekLabel, toFa } from "../lib/jalali";
import {
  DEFAULT_SUMMARY_VARIANT,
  addDecimalStrings,
  buildOverviewWheelCompanies,
  computePieSlices,
  estimateScorecardTypography,
  estimateShareCardGeometry,
  formatCompanyScorecardPeriodNote,
  formatPresentationQuantity,
  getCompanyColor,
  isSummaryVariant,
  mergeCoatCatalog,
  mergeCoatResultRows,
  splitSharePages,
  type ScorecardTypography,
  type ShareCardGeometry,
  type SummaryVariant,
} from "../lib/presentation";
import type { CatalogItem, Company, CompanyNarrative, EvmResponse, ReportDetail, ResultRow, ResultsResponse } from "../types";

/** The slide canvas is 16in x 9in at 96dpi, so it prints 1:1 and is scaled down with CSS on screen (see globals.css). */
const SLIDE_W = 1536;
const SLIDE_H = 864;
const NAVY = "#252850";
const READY_STATUSES = new Set(["awaiting_user", "needs_review", "ready", "published"]);
const NARRATIVE_COMPANIES_PER_SLIDE = 2;
const SUMMARY_VARIANT_STORAGE_KEY = "vr-presentation-summary-variant";

function chunks<T>(items: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let index = 0; index < items.length; index += size) result.push(items.slice(index, index + size));
  return result;
}

interface ScorecardRow {
  id: string;
  name: string;
  companyName?: string;
  rows: Map<string, ResultRow>;
}

function groupByCompany(rows: ResultRow[], extraRows: ResultRow[] = []): ScorecardRow[] {
  const groups = new Map<string, ScorecardRow>();
  for (const row of [...rows, ...extraRows]) {
    if (!row.company_id) continue;
    if (!groups.has(row.company_id)) {
      groups.set(row.company_id, {
        id: row.company_id,
        name: row.company ?? "بدون نام",
        rows: new Map<string, ResultRow>(),
      });
    }
  }
  for (const row of rows) {
    if (!row.company_id) continue;
    groups.get(row.company_id)?.rows.set(row.item_key, row);
  }
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name, "fa"));
}

function groupByProject(rows: ResultRow[], extraRows: ResultRow[] = []): ScorecardRow[] {
  const groups = new Map<string, ScorecardRow>();
  for (const row of [...rows, ...extraRows]) {
    const id = row.site_id ?? row.site;
    if (!id) continue;
    if (!groups.has(id)) {
      groups.set(id, {
        id,
        name: row.site ?? "بدون نام",
        companyName: row.company ?? undefined,
        rows: new Map<string, ResultRow>(),
      });
    }
  }
  for (const row of rows) {
    const id = row.site_id ?? row.site;
    if (!id) continue;
    const g = groups.get(id);
    if (g) {
      g.rows.set(row.item_key, row);
      if (!g.companyName && row.company) g.companyName = row.company;
    }
  }
  // grouped by company (the order of the company scorecard), then by project name: one company's projects, then the next company's
  return Array.from(groups.values()).sort((a, b) => (a.companyName ?? "").localeCompare(b.companyName ?? "", "fa") || a.name.localeCompare(b.name, "fa"));
}

interface SlideSpec { key: string; render: (page: string) => ReactNode }

function Slide({
  title,
  subtitle,
  titleAside,
  headerRight,
  page,
  children,
}: {
  title: string;
  subtitle?: string;
  titleAside?: ReactNode;
  headerRight?: ReactNode;
  page: string;
  period: string;
  children: ReactNode;
}) {
  return (
    <section className="presentation-slide-print">
      <div
        className="slide-canvas flex flex-col bg-[#f7f7f5] px-8 pb-4 pt-6 text-slate-900"
        style={{ backgroundColor: "#f7f7f5", color: "#0f172a" }}
        data-slide-bg="#f7f7f5"
      >
        <div className="mb-4 flex shrink-0 items-end justify-between gap-6 border-b-2 border-[#252850]/10 pb-3">
          <div className="min-w-0 flex-1">
            {subtitle && <p className="mb-1 text-[14px] font-semibold text-[#9b7a05]">{subtitle}</p>}
            <div className="flex flex-nowrap items-center gap-3.5">
              <h2 className="shrink-0 text-[32px] font-black leading-tight text-[#252850]">{title}</h2>
              {titleAside}
            </div>
          </div>
          <div className="mb-1.5 flex shrink-0 items-center gap-4">
            {headerRight}
            <span className="h-1.5 w-24 shrink-0 rounded-full bg-[#fed836]" />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        <div className="mt-2.5 flex shrink-0 items-center justify-end text-[13px] text-slate-400">
          <span className="tabular-nums">{page}</span>
        </div>
      </div>
    </section>
  );
}

function ScorecardTable({
  entityType,
  groups,
  metrics,
  holdingMap,
  plannedHoldingMap,
  plannedGroupMap,
  showTotal,
}: {
  entityType: "company" | "project";
  groups: ScorecardRow[];
  metrics: CatalogItem[];
  holdingMap: Map<string, ResultRow>;
  plannedHoldingMap?: Map<string, ResultRow>;
  plannedGroupMap?: Map<string, Map<string, ResultRow>>;
  showTotal: boolean;
}) {
  const isCompany = entityType === "company";
  const metricTitles = useMemo(
    () => metrics.map((item) => (item.key === "asphalt_total" ? "آسفالت" : item.title_fa)),
    [metrics],
  );
  const metricUnits = useMemo(() => metrics.map((item) => unitLabel(item.output_unit)), [metrics]);
  const entityNames = useMemo(() => groups.map((g) => g.name), [groups]);
  const hasSubtitles = useMemo(() => !isCompany && groups.some((g) => Boolean(g.companyName)), [groups, isCompany]);

  const { hasPlanned, formattedValues, formattedPlanned, maxVal, maxPlan } = useMemo(() => {
    const vals: string[] = [];
    const plans: string[] = [];
    for (const group of groups) {
      const planGroup = plannedGroupMap?.get(group.id);
      for (const item of metrics) {
        const row = group.rows.get(item.key);
        if (row) vals.push(formatPresentationQuantity(row.qty));
        const planRow = planGroup?.get(item.key);
        if (planRow && Number.parseFloat(planRow.qty || "0") > 0) {
          plans.push(`برنامه: ${formatPresentationQuantity(planRow.qty)}`);
        }
      }
    }
    if (showTotal) {
      for (const item of metrics) {
        const row = holdingMap.get(item.key);
        if (row) vals.push(formatPresentationQuantity(row.qty));
        const planRow = plannedHoldingMap?.get(item.key);
        if (planRow && Number.parseFloat(planRow.qty || "0") > 0) {
          plans.push(`برنامه: ${formatPresentationQuantity(planRow.qty)}`);
        }
      }
    }
    const maxV = vals.reduce((a, b) => (b.length > a.length ? b : a), "۱۰٬۰۰۰");
    const maxP = plans.reduce((a, b) => (b.length > a.length ? b : a), "");
    return {
      hasPlanned: plans.length > 0,
      formattedValues: vals,
      formattedPlanned: plans,
      maxVal: maxV,
      maxPlan: maxP || undefined,
    };
  }, [groups, holdingMap, metrics, plannedGroupMap, plannedHoldingMap, showTotal]);

  const fallback = useMemo(
    () =>
      estimateScorecardTypography({
        metricTitles,
        metricUnits,
        entityNames,
        entityType,
        rowCount: groups.length,
        showTotal,
        hasSubtitles,
        hasPlanned,
        maxFormattedValue: maxVal,
        maxPlannedText: maxPlan,
      }),
    [entityNames, entityType, groups.length, hasPlanned, hasSubtitles, maxPlan, maxVal, metricTitles, metricUnits, showTotal],
  );

  const measurementKey = useMemo(
    () =>
      [
        entityType,
        String(showTotal),
        metricTitles.join(","),
        entityNames.join(","),
        formattedValues.join(","),
        formattedPlanned.join(","),
      ].join("|"),
    [entityNames, entityType, formattedPlanned, formattedValues, metricTitles, showTotal],
  );

  const [measured, setMeasured] = useState<{ key: string; typography: ScorecardTypography } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const probeRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const container = containerRef.current;
      const probe = probeRef.current;
      if (!container || !probe || container.clientWidth === 0 || container.clientHeight === 0) return;

      const canvasW = container.clientWidth;
      const canvasH = container.clientHeight;
      const est = estimateScorecardTypography({
        metricTitles,
        metricUnits,
        entityNames,
        entityType,
        rowCount: groups.length,
        showTotal,
        hasSubtitles,
        hasPlanned,
        maxFormattedValue: maxVal,
        maxPlannedText: maxPlan,
        canvasW,
        canvasH,
      });

      const metricColW = (canvasW - 2 - est.entityColW) / Math.max(metrics.length, 1);
      const innerMetricW = Math.max(metricColW - 8, 48);

      probe.style.fontWeight = "500";
      probe.style.fontVariantNumeric = "normal";
      let headerUnitPx = Math.min(15, Math.max(11, Math.round(est.headerHeightPx * 0.16)));
      for (const unit of metricUnits) {
        if (!unit) continue;
        headerUnitPx = Math.min(headerUnitPx, fitTextMaxPx(probe, unit, 10, headerUnitPx, innerMetricW));
      }

      probe.style.fontWeight = "700";
      const headerTitleCapH = Math.floor((est.headerHeightPx - headerUnitPx * 1.25 - 14) / (2 * 1.2));
      let headerTitlePx = Math.max(12, Math.min(21, headerTitleCapH));
      for (const title of metricTitles) {
        for (const word of title.split(/\s+/).filter(Boolean)) {
          headerTitlePx = Math.min(headerTitlePx, fitTextMaxPx(probe, word, 11, headerTitlePx, innerMetricW));
        }
        headerTitlePx = Math.min(headerTitlePx, fitTextMaxPx(probe, title, 11, headerTitlePx, innerMetricW * 1.85));
      }

      probe.style.fontWeight = "600";
      probe.style.fontVariantNumeric = "tabular-nums";
      let planTextPx = hasPlanned ? Math.max(10, Math.min(14, Math.floor(est.rowHeightPx * 0.2))) : 11;
      for (const plan of formattedPlanned) {
        planTextPx = Math.min(planTextPx, fitTextMaxPx(probe, plan, 10, planTextPx, innerMetricW));
      }

      probe.style.fontWeight = "800";
      const vertCellBudget = est.rowHeightPx - (hasPlanned ? Math.ceil(planTextPx * 1.35) + 10 : 10);
      let cellValuePx = Math.max(13, Math.min(34, Math.floor(vertCellBudget * 0.68)));
      for (const val of formattedValues) {
        if (!val || val === "—") continue;
        cellValuePx = Math.min(cellValuePx, fitTextMaxPx(probe, val, 13, cellValuePx, innerMetricW));
      }

      probe.style.fontWeight = "900";
      let totalValuePx = Math.max(cellValuePx, Math.min(cellValuePx + 1, Math.floor(vertCellBudget * 0.7)));
      for (const val of formattedValues) {
        if (!val || val === "—") continue;
        totalValuePx = Math.min(totalValuePx, fitTextMaxPx(probe, val, 13, totalValuePx, innerMetricW));
      }

      probe.style.fontWeight = "700";
      probe.style.fontVariantNumeric = "normal";
      const innerEntityW = Math.max(est.entityColW - (isCompany ? est.logoSizePx + 30 : 24), 90);
      const entityVertBudget = est.rowHeightPx - (hasSubtitles ? Math.ceil(est.entitySubPx * 1.3) + 10 : 12);
      let entityNamePx = Math.max(14, Math.min(23, Math.floor(entityVertBudget * 0.55)));
      for (const name of entityNames) {
        entityNamePx = Math.min(entityNamePx, fitTextMaxPx(probe, name, 13, entityNamePx, innerEntityW * 1.85));
      }

      const headerEntityPx = Math.max(15, Math.min(22, headerTitlePx + 3));
      const totalLabelPx = Math.max(15, Math.min(23, entityNamePx + 1));

      setMeasured({
        key: measurementKey,
        typography: {
          ...est,
          headerTitlePx,
          headerUnitPx,
          headerEntityPx,
          entityNamePx,
          cellValuePx,
          totalValuePx,
          totalLabelPx,
          planTextPx,
        },
      });
    };

    const cancelSoon = runSoon(measure);
    void document.fonts?.ready.then(measure);

    return () => {
      cancelled = true;
      cancelSoon();
    };
  }, [
    entityNames,
    entityType,
    formattedPlanned,
    formattedValues,
    groups.length,
    hasPlanned,
    hasSubtitles,
    isCompany,
    maxPlan,
    maxVal,
    measurementKey,
    metricTitles,
    metricUnits,
    metrics.length,
    showTotal,
  ]);

  const typo = measured?.key === measurementKey ? measured.typography : fallback;

  return (
    <div ref={containerRef} className="relative flex min-h-0 flex-1 flex-col">
      <span
        ref={probeRef}
        aria-hidden="true"
        className="pointer-events-none invisible absolute -top-[9999px] left-0 whitespace-nowrap"
      />
      <div
        className="overflow-hidden rounded-2xl border border-[#252850]/15 bg-white shadow-sm"
        style={{ height: `${typo.tableHeightPx}px` }}
      >
        <table className="h-full w-full table-fixed border-collapse" style={{ height: `${typo.tableHeightPx}px` }}>
          <thead className="bg-[#252850] text-white" style={{ height: `${typo.headerHeightPx}px` }}>
            <tr>
              <th
                className="text-start font-extrabold"
                style={{ width: `${typo.entityColW}px`, paddingInline: "12px", fontSize: `${typo.headerEntityPx}px` }}
              >
                {isCompany ? "شرکت" : "پروژه"}
              </th>
              {metrics.map((item, idx) => (
                <th
                  key={item.key}
                  className="border-s border-white/10 px-1 py-1.5 text-center font-bold leading-tight"
                >
                  <div className="line-clamp-2" style={{ fontSize: `${typo.headerTitlePx}px`, lineHeight: 1.2 }}>
                    {metricTitles[idx]}
                  </div>
                  <span
                    className="mt-0.5 block font-medium leading-tight text-white/75"
                    style={{ fontSize: `${typo.headerUnitPx}px` }}
                  >
                    {metricUnits[idx]}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => {
              const planGroup = plannedGroupMap?.get(group.id);
              return (
                <tr
                  key={group.id}
                  className="border-t border-slate-200/70 odd:bg-white even:bg-slate-50/75"
                  style={{ height: `${typo.rowHeightPx}px` }}
                >
                  <th
                    scope="row"
                    className="text-start align-middle font-bold text-[#252850]"
                    style={{ paddingInline: "12px" }}
                  >
                    {isCompany ? (
                      <span className="flex items-center gap-2.5">
                        <CompanyMark name={group.name} size={typo.logoSizePx} />
                        <span
                          className="line-clamp-2 font-bold leading-snug"
                          style={{ fontSize: `${typo.entityNamePx}px` }}
                        >
                          {group.name}
                        </span>
                      </span>
                    ) : (
                      <div className="flex min-w-0 flex-col">
                        <span
                          className="line-clamp-2 font-bold leading-snug text-[#252850]"
                          style={{ fontSize: `${typo.entityNamePx}px` }}
                        >
                          {group.name}
                        </span>
                        {group.companyName && (
                          <span
                            className="mt-0.5 truncate font-medium text-slate-400"
                            style={{ fontSize: `${typo.entitySubPx}px` }}
                          >
                            {group.companyName}
                          </span>
                        )}
                      </div>
                    )}
                  </th>
                  {metrics.map((item) => {
                    const row = group.rows.get(item.key);
                    const planRow = planGroup?.get(item.key);
                    const hasPlan = planRow && Number.parseFloat(planRow.qty || "0") > 0;
                    return (
                      <td key={item.key} className="border-s border-slate-100 px-1 py-1 text-center align-middle tabular-nums">
                        <div
                          className="whitespace-nowrap font-extrabold leading-none text-[#252850]"
                          style={{ fontSize: `${typo.cellValuePx}px` }}
                        >
                          {row ? formatPresentationQuantity(row.qty) : <span className="font-normal text-slate-300">—</span>}
                        </div>
                        {hasPlan && (
                          <div
                            className="mt-1 whitespace-nowrap font-semibold leading-none text-slate-500"
                            style={{ fontSize: `${typo.planTextPx}px` }}
                          >
                            برنامه: {formatPresentationQuantity(planRow.qty)}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {showTotal && (
              <tr
                className="border-t-2 border-[#252850] bg-[#fed836]/25"
                style={{ height: `${typo.rowHeightPx}px` }}
              >
                <th
                  scope="row"
                  className="text-start align-middle font-black text-[#252850]"
                  style={{ paddingInline: "12px", fontSize: `${typo.totalLabelPx}px` }}
                >
                  جمع هلدینگ
                </th>
                {metrics.map((item) => {
                  const row = holdingMap.get(item.key);
                  const planRow = plannedHoldingMap?.get(item.key);
                  const hasPlan = planRow && Number.parseFloat(planRow.qty || "0") > 0;
                  return (
                    <td
                      key={item.key}
                      className="border-s border-[#252850]/10 px-1 py-1 text-center align-middle tabular-nums"
                    >
                      <div
                        className="whitespace-nowrap font-black leading-none text-[#252850]"
                        style={{ fontSize: `${typo.totalValuePx}px` }}
                      >
                        {row ? formatPresentationQuantity(row.qty) : <span className="font-normal text-slate-300">—</span>}
                      </div>
                      {hasPlan && (
                        <div
                          className="mt-1 whitespace-nowrap font-bold leading-none text-[#9b7a05]"
                          style={{ fontSize: `${typo.planTextPx}px` }}
                        >
                          برنامه: {formatPresentationQuantity(planRow.qty)}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface CompanyContribution {
  companyId: string;
  companyName: string;
  qty: number;
  pct: number;
  color: string;
}

interface ItemShareData {
  item: CatalogItem;
  totalQty: number;
  totalQtyStr: string;
  contributions: CompanyContribution[];
}

function PieChart({
  contributions,
  size,
}: {
  contributions: CompanyContribution[];
  size: number;
}) {
  if (contributions.length === 0) {
    const emptyR = Math.max(40, size / 2 - 4);
    return (
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle cx={size / 2} cy={size / 2} r={emptyR} fill="#f8fafc" stroke="#e2e8f0" strokeWidth={2} />
        </svg>
        <span className="pointer-events-none absolute text-center text-[13px] font-semibold text-slate-400">
          فاقد تفکیک شرکتی
        </span>
      </div>
    );
  }

  const slices = computePieSlices(contributions, size);
  const center = size / 2;
  const radius = size / 2 - 3;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
        {slices.map((s) =>
          s.isFullCircle ? (
            <circle key={s.companyId} cx={center} cy={center} r={radius} fill={s.color}>
              <title>{`${s.companyName}: ${s.labelText}`}</title>
            </circle>
          ) : (
            <path
              key={s.companyId}
              d={s.pathD}
              fill={s.color}
              stroke="#ffffff"
              strokeWidth={2.5}
              strokeLinejoin="round"
            >
              <title>{`${s.companyName}: ${s.labelText}`}</title>
            </path>
          ),
        )}
      </svg>

      {slices.map((s) =>
        s.isOutside ? (
          <span
            key={s.companyId}
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border bg-white/95 px-1.5 py-0.5 font-black leading-none shadow-sm tabular-nums"
            style={{
              left: `${s.labelX}px`,
              top: `${s.labelY}px`,
              color: s.color,
              borderColor: `${s.color}40`,
              fontSize: `${s.labelFontPx}px`,
            }}
          >
            {s.labelText}
          </span>
        ) : (
          <span
            key={s.companyId}
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap font-black leading-none text-white tabular-nums"
            style={{
              left: `${s.labelX}px`,
              top: `${s.labelY}px`,
              fontSize: `${s.labelFontPx}px`,
              textShadow: "0 1px 3px rgba(15, 23, 42, 0.45)",
            }}
          >
            {s.labelText}
          </span>
        ),
      )}
    </div>
  );
}

function ShareCard({
  data,
  geo,
  chartBoxRef,
}: {
  data: ItemShareData;
  geo: ShareCardGeometry;
  chartBoxRef?: (el: HTMLDivElement | null) => void;
}) {
  const { item, totalQtyStr, contributions } = data;
  const title = item.key === "asphalt_total" ? "آسفالت" : item.title_fa;
  const unit = unitLabel(item.output_unit);
  const formattedTotal = formatPresentationQuantity(totalQtyStr);

  return (
    <div
      className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-[#252850]/15 bg-white shadow-sm"
      style={{ paddingInline: "14px", paddingBlock: "10px" }}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-100 pb-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className="truncate font-black leading-tight text-[#252850]"
            style={{ fontSize: `${geo.titlePx}px` }}
          >
            {title}
          </span>
          {item.key === "asphalt_total" && (
            <span className="shrink-0 rounded-md border border-[#252850]/15 bg-[#252850]/[0.05] px-1.5 py-0.5 text-[10.5px] font-semibold text-[#252850]/80">
              بیندر + توپکا
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-baseline gap-1 rounded-xl border border-[#252850]/12 bg-[#252850]/[0.05] px-2.5 py-0.5">
          <span
            className="font-black leading-none text-[#252850] tabular-nums"
            style={{ fontSize: `${geo.totalPx}px` }}
          >
            {formattedTotal}
          </span>
          <span
            className="font-bold leading-none text-[#252850]/75"
            style={{ fontSize: `${geo.unitPx}px` }}
          >
            {unit}
          </span>
        </div>
      </div>

      <div ref={chartBoxRef} className="flex min-h-0 min-w-0 flex-1 items-center justify-center pt-1">
        <PieChart contributions={contributions} size={geo.pieSizePx} />
      </div>
    </div>
  );
}

function ShareGrid({ items }: { items: ItemShareData[] }) {
  const fallback = useMemo(() => estimateShareCardGeometry(items.length), [items.length]);
  const measurementKey = useMemo(
    () => `${items.length}:${items.map((i) => i.item.key).join(",")}`,
    [items],
  );
  const [measured, setMeasured] = useState<{ key: string; geo: ShareCardGeometry } | null>(null);
  const chartBoxRef = useRef<HTMLDivElement | null>(null);

  const setFirstChartBoxRef = useCallback((el: HTMLDivElement | null) => {
    chartBoxRef.current = el;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const box = chartBoxRef.current;
      if (!box || box.clientWidth === 0 || box.clientHeight === 0) return;
      const pieSizePx = Math.max(160, Math.min(460, Math.floor(Math.min(box.clientWidth, box.clientHeight) - 6)));
      setMeasured({
        key: measurementKey,
        geo: {
          ...fallback,
          pieSizePx,
        },
      });
    };

    const cancelSoon = runSoon(measure);
    void document.fonts?.ready.then(measure);

    return () => {
      cancelled = true;
      cancelSoon();
    };
  }, [fallback, measurementKey]);

  const geo = measured?.key === measurementKey ? measured.geo : fallback;

  return (
    <div
      className="grid min-h-0 flex-1 gap-4"
      style={{
        gridTemplateColumns: `repeat(${geo.cols}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${geo.rows}, minmax(0, 1fr))`,
      }}
    >
      {items.map((data, index) => (
        <ShareCard
          key={data.item.key}
          data={data}
          geo={geo}
          chartBoxRef={index === 0 ? setFirstChartBoxRef : undefined}
        />
      ))}
    </div>
  );
}

function getCompanyNarrativeItems(narrative?: CompanyNarrative): string[] {
  if (!narrative) return [];
  if (Array.isArray(narrative.items) && narrative.items.length > 0) {
    const cleaned = narrative.items
      .map((item) => (typeof item === "string" ? item.trim() : ""))
      .filter(Boolean);
    if (cleaned.length > 0) return cleaned;
  }
  if (typeof narrative.raw_text === "string" && narrative.raw_text.trim()) {
    return [narrative.raw_text.trim()];
  }
  return [];
}

function CompanyNarrativeCard({
  company,
  index,
  items,
}: {
  company: ScorecardRow;
  index: number;
  items: string[];
}) {
  const accentColor = getCompanyColor(company.name, index);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-slate-200/90 bg-white shadow-sm">
      {/* Top accent bar */}
      <div className="h-2 w-full shrink-0" style={{ backgroundColor: accentColor }} />

      {/* Card Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-slate-100 bg-slate-50/60 px-6 py-4">
        <div className="flex items-center gap-3.5">
          <CompanyMark name={company.name} size={36} />
          <div>
            <h3 className="text-[19px] font-bold text-slate-900 leading-tight">{company.name}</h3>
            <span className="text-[12px] text-slate-400">گزارش اقدامات و پیشرفت پروژه‌ها</span>
          </div>
        </div>
        <div
          className="flex h-9 w-9 items-center justify-center rounded-2xl text-[14px] font-black text-white shadow-sm"
          style={{ backgroundColor: accentColor }}
        >
          {toFa(String(index + 1).padStart(2, "0"))}
        </div>
      </div>

      {/* Bullets List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {items.map((item, i) => {
          const lines = item.split("\n").map((l) => l.trim()).filter(Boolean);
          const mainTitle = lines[0] ?? "";
          const subLines = lines.slice(1);

          return (
            <div key={i} className="flex items-start gap-3 text-[14.5px] leading-relaxed text-slate-700">
              <span
                className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: accentColor }}
              />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-slate-800">{mainTitle}</p>
                {subLines.length > 0 && (
                  <div className="mt-1.5 space-y-1 ps-2 text-[13.5px] text-slate-600">
                    {subLines.map((sub, sIdx) => (
                      <p key={sIdx} className="leading-normal">{sub}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function useSlideScale() {
  const [scale, setScale] = useState(1);
  const observer = useRef<ResizeObserver | null>(null);
  const ref = useCallback((element: HTMLDivElement | null) => {
    observer.current?.disconnect();
    observer.current = null;
    if (!element) return;
    const update = () => setScale(element.clientWidth / SLIDE_W);
    update();
    observer.current = new ResizeObserver(update);
    observer.current.observe(element);
  }, []);
  useEffect(() => () => observer.current?.disconnect(), []);
  return { scale, ref };
}

function getSlideBackground(node: HTMLElement): string {
  const attr = node.getAttribute("data-slide-bg");
  if (attr) return attr;
  const styleBg = node.style.backgroundColor;
  if (styleBg && styleBg !== "transparent") return styleBg;
  const computed = window.getComputedStyle(node).backgroundColor;
  if (computed && computed !== "rgba(0, 0, 0, 0)" && computed !== "transparent") return computed;
  return "#f7f7f5";
}

/** Renders every slide to an image and assembles a real PDF in the browser, then downloads it. */
async function downloadPdf(fileName: string, onProgress: (done: number, total: number) => void) {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>(".presentation-page .slide-canvas"));
  if (!nodes.length) throw new Error("اسلایدی برای خروجی وجود ندارد.");
  if (document.fonts?.ready) await document.fonts.ready;
  const [{ toJpeg }, { jsPDF }] = await Promise.all([import("html-to-image"), import("jspdf")]);

  const pdf = new jsPDF({ orientation: "landscape", unit: "px", format: [SLIDE_W, SLIDE_H], hotfixes: ["px_scaling"], compress: true });

  const makeOptions = (node: HTMLElement) => {
    const bg = getSlideBackground(node);
    return {
      width: SLIDE_W,
      height: SLIDE_H,
      pixelRatio: 2,
      quality: 0.92,
      backgroundColor: bg,
      cacheBust: false,
      style: { transform: "none", top: "0", left: "0", backgroundColor: bg },
    };
  };

  // Warm-up pass using the first slide's correct background options
  await toJpeg(nodes[0]!, makeOptions(nodes[0]!)).catch(() => undefined);

  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index]!;
    const image = await toJpeg(node, makeOptions(node));
    if (index > 0) pdf.addPage([SLIDE_W, SLIDE_H], "landscape");
    pdf.addImage(image, "JPEG", 0, 0, SLIDE_W, SLIDE_H, undefined, "FAST");
    onProgress(index + 1, nodes.length);
  }
  pdf.save(`${fileName}.pdf`);
}

export function PresentationScreen({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [holding, setHolding] = useState<ResultsResponse | null>(null);
  const [companyRows, setCompanyRows] = useState<ResultRow[]>([]);
  const [siteRows, setSiteRows] = useState<ResultRow[]>([]);
  const [holdingPlanned, setHoldingPlanned] = useState<ResultsResponse | null>(null);
  const [companyPlannedRows, setCompanyPlannedRows] = useState<ResultRow[]>([]);
  const [sitePlannedRows, setSitePlannedRows] = useState<ResultRow[]>([]);
  const [settingsCompanies, setSettingsCompanies] = useState<Company[]>([]);
  const [evm, setEvm] = useState<EvmResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [exporting, setExporting] = useState<{ done: number; total: number } | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [summaryVariant, setSummaryVariant] = useState<SummaryVariant>(DEFAULT_SUMMARY_VARIANT);
  const { scale, ref: pageRef } = useSlideScale();

  useEffect(() => {
    return runSoon(() => {
      try {
        const param = new URLSearchParams(window.location.search).get("summary");
        if (isSummaryVariant(param)) {
          setSummaryVariant(param);
          return;
        }
        const saved = window.localStorage.getItem(SUMMARY_VARIANT_STORAGE_KEY);
        if (isSummaryVariant(saved)) setSummaryVariant(saved);
      } catch {
        // Ignore storage access failures in restricted environments.
      }
    });
  }, []);

  const handleSelectSummaryVariant = useCallback((next: SummaryVariant) => {
    setSummaryVariant(next);
    try {
      window.localStorage.setItem(SUMMARY_VARIANT_STORAGE_KEY, next);
    } catch {
      // Ignore storage access failures.
    }
  }, []);

  const scrollToSummarySlide = useCallback(() => {
    document.getElementById("slide-summary")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [
        detail,
        items,
        holdingResult,
        companyResult,
        siteResult,
        companyPlannedResult,
        holdingPlannedResult,
        sitePlannedResult,
        companySettings,
        evmResult,
      ] = await Promise.all([
        volumeReportApi.get(reportId),
        volumeReportApi.catalog(),
        volumeReportApi.results(reportId, "holding"),
        volumeReportApi.results(reportId, "company"),
        volumeReportApi.results(reportId, "site"),
        volumeReportApi.results(reportId, "company", [], "planned").catch(() => null),
        volumeReportApi.results(reportId, "holding", [], "planned").catch(() => null),
        volumeReportApi.results(reportId, "site", [], "planned").catch(() => null),
        volumeReportApi.settings.companies().catch(() => [] as Company[]),
        volumeReportApi.evm(reportId).catch(() => null),
      ]);
      setReport(detail);
      setCatalog(items);
      setHolding(holdingResult);
      setCompanyRows(companyResult.rows);
      setSiteRows(siteResult.rows);
      setCompanyPlannedRows(companyPlannedResult?.rows ?? []);
      setHoldingPlanned(holdingPlannedResult ?? null);
      setSitePlannedRows(sitePlannedResult?.rows ?? []);
      setSettingsCompanies(companySettings);
      setEvm(evmResult);
    } catch (reason) {
      setError(reason);
    }
  }, [reportId]);

  useEffect(() => runSoon(() => void load()), [load]);

  const weekSubtitle = useMemo(() => {
    if (!report) return "";
    if (report.period_label && /هفته\s+(اول|دوم|سوم|چهارم|پنجم)/i.test(report.period_label)) {
      return toFa(report.period_label);
    }
    if (report.period_start) {
      const derived = formatWeekLabel(report.period_start);
      if (derived) return derived;
    }
    if (report.period_label && !report.period_label.includes("تا")) {
      return toFa(report.period_label);
    }
    return "هفته اول آبان ۱۴۰۵";
  }, [report]);

  const slides = useMemo<SlideSpec[]>(() => {
    if (!report || !holding) return [];
    const { items: visibleItems, coatUnit, coatDecimals } = mergeCoatCatalog(catalog);
    const mergedHoldingRows = mergeCoatResultRows(holding.rows, coatUnit, coatDecimals);
    const mergedHoldingPlannedRows = mergeCoatResultRows(holdingPlanned?.rows ?? [], coatUnit, coatDecimals);
    const mergedCompanyRows = mergeCoatResultRows(companyRows, coatUnit, coatDecimals);
    const mergedCompanyPlannedRows = mergeCoatResultRows(companyPlannedRows, coatUnit, coatDecimals);
    const mergedSiteRows = mergeCoatResultRows(siteRows, coatUnit, coatDecimals);
    const mergedSitePlannedRows = mergeCoatResultRows(sitePlannedRows, coatUnit, coatDecimals);

    const holdingMap = new Map(mergedHoldingRows.map((row) => [row.item_key, row]));
    const holdingPlannedMap = new Map(mergedHoldingPlannedRows.map((row) => [row.item_key, row]));
    const companies = groupByCompany(mergedCompanyRows, mergedCompanyPlannedRows);
    const projects = groupByProject(mergedSiteRows, mergedSitePlannedRows);
    const period = weekSubtitle || report.period_label;
    const hasAnyReportPlanned =
      mergedCompanyPlannedRows.some((r) => Number.parseFloat(r.qty || "0") > 0) ||
      mergedSitePlannedRows.some((r) => Number.parseFloat(r.qty || "0") > 0);
    const result: SlideSpec[] = [];

    result.push({
      key: "cover",
      render: () => (
        <section className="presentation-slide-print">
          <div
            className="slide-canvas flex bg-[#252850] text-white"
            style={{ backgroundColor: NAVY, color: "#ffffff" }}
            data-slide-bg={NAVY}
          >
            <div className="absolute inset-y-0 start-0 w-4 bg-[#fed836]" />
            <div className="flex min-w-0 flex-1 flex-col justify-center ps-14 pe-8">
              <div className="mb-4 inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#fed836]" />
                <span className="text-[20px] font-bold text-[#fed836]">گزارش مدیریتی احجام عملیات اجرایی</span>
              </div>
              <h1 className="max-w-[820px] text-[64px] font-black leading-[1.25] text-white">گزارش عملکرد هلدینگ عمرانی</h1>
              <h2 className="mt-4 text-[32px] font-bold text-[#fed836]">{weekSubtitle}</h2>
              <div className="mt-8 h-1.5 w-32 rounded-full bg-[#fed836]" />
              <div className="mt-6 flex flex-col gap-1 text-[20px] text-white/80">
                <span className="text-[18px] text-white/60">{formatJalaliDate(report.period_start)} تا {formatJalaliDate(report.period_end)}</span>
              </div>
            </div>
            <div className="flex w-[44%] items-center justify-center pe-10">
              <div className="flex items-center justify-center gap-8 rounded-[40px] bg-white p-8 shadow-2xl">
                <div className="flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/volume-reports/jihad_nasr_kerman.png"
                    alt="لوگوی جهاد نصر کرمان"
                    loading="eager"
                    decoding="sync"
                    width={210}
                    height={190}
                    className="h-[190px] w-[210px] object-contain"
                  />
                </div>
                <div className="h-36 w-px bg-slate-200" />
                <div className="flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/volume-reports/logo_mehvar.png"
                    alt="لوگوی شرکت محور گستر نصر"
                    loading="eager"
                    decoding="sync"
                    width={210}
                    height={190}
                    className="h-[190px] w-[210px] object-contain"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      ),
    });

    const companySites = new Map<string, Set<string>>();
    for (const row of [...mergedSiteRows, ...mergedSitePlannedRows]) {
      const compKey = row.company_id ?? row.company;
      const siteKey = row.site_id ?? row.site;
      if (!compKey || !siteKey) continue;
      let sites = companySites.get(compKey);
      if (!sites) {
        sites = new Set();
        companySites.set(compKey, sites);
      }
      sites.add(siteKey);
    }
    const overviewCompanies = buildOverviewWheelCompanies(
      companies.map((company) => ({
        id: company.id,
        name: company.name,
        projectCount: (companySites.get(company.id) ?? companySites.get(company.name))?.size ?? 0,
      })),
      settingsCompanies,
    );
    result.push({
      key: "overview",
      render: (page) => (
        <Slide title="نمای کلی گزارش" subtitle={period} page={page} period={period}>
          <HoldingRadialOverview companies={overviewCompanies} totalProjects={projects.length} />
        </Slide>
      ),
    });

    result.push({
      key: "summary",
      render: (page) => (
        <>
          <div id="slide-summary" className="no-print">
            <SummaryVariantBar variant={summaryVariant} onSelect={handleSelectSummaryVariant} compact />
          </div>
          <Slide title="خلاصه عملکرد هلدینگ" subtitle={period} page={page} period={period}>
            <SummarySlideContent
              variant={summaryVariant}
              items={visibleItems}
              holdingMap={holdingMap}
              holdingPlannedMap={holdingPlannedMap}
              companyRows={mergedCompanyRows}
            />
          </Slide>
        </>
      ),
    });

    const plannedCompanyGroupMap = new Map<string, Map<string, ResultRow>>();
    for (const row of mergedCompanyPlannedRows) {
      if (!row.company_id) continue;
      let sub = plannedCompanyGroupMap.get(row.company_id);
      if (!sub) {
        sub = new Map();
        plannedCompanyGroupMap.set(row.company_id, sub);
      }
      sub.set(row.item_key, row);
    }

    const plannedProjectGroupMap = new Map<string, Map<string, ResultRow>>();
    for (const row of mergedSitePlannedRows) {
      const id = row.site_id ?? row.site;
      if (!id) continue;
      let sub = plannedProjectGroupMap.get(id);
      if (!sub) {
        sub = new Map();
        plannedProjectGroupMap.set(id, sub);
      }
      sub.set(row.item_key, row);
    }

    const activeItemKeys = new Set([
      ...mergedHoldingRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...mergedHoldingPlannedRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...mergedCompanyRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...mergedCompanyPlannedRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...mergedSiteRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...mergedSitePlannedRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
    ]);
    const filteredMetrics = visibleItems.filter((item) => activeItemKeys.has(item.key));
    const tableMetrics = filteredMetrics.length ? filteredMetrics : visibleItems;

    const tableLegend = hasAnyReportPlanned ? (
      <div className="flex items-center gap-3 rounded-full border border-[#252850]/10 bg-white/90 px-3.5 py-1 text-[12px] font-semibold text-slate-700 shadow-sm">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#252850]" />
          <span>عملکرد واقعی</span>
        </span>
        <span className="h-3 w-px bg-slate-300" />
        <span className="flex items-center gap-1.5">
          <span className="text-[#9b7a05]">برنامه:</span>
          <span className="text-slate-500">حجم مصوب</span>
        </span>
      </div>
    ) : undefined;

    const companyScorecardPeriodNote = formatCompanyScorecardPeriodNote(
      report.period_start,
      report.period_end,
    );
    const companyScorecardBadge = companyScorecardPeriodNote ? (
      <span className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-[#252850]/12 bg-white px-4 py-1 text-[14px] font-bold text-[#252850] shadow-sm">
        <span className="h-2 w-2 shrink-0 rounded-full bg-[#fed836]" />
        <span>{companyScorecardPeriodNote}</span>
      </span>
    ) : undefined;

    const COMPANY_ROWS_PER_SLIDE = 10;
    const companyPages = chunks(companies, COMPANY_ROWS_PER_SLIDE);
    if (!companyPages.length) companyPages.push([]);
    companyPages.forEach((groupSet, pageIndex) => {
      result.push({
        key: `companies-${pageIndex}`,
        render: (page) => (
          <Slide
            title="کارنامه شرکت‌ها"
            subtitle={companyPages.length > 1 ? `بخش ${toFa(pageIndex + 1)} از ${toFa(companyPages.length)}` : period}
            titleAside={companyScorecardBadge}
            headerRight={tableLegend}
            page={page}
            period={period}
          >
            <ScorecardTable
              entityType="company"
              groups={groupSet}
              metrics={tableMetrics}
              holdingMap={holdingMap}
              plannedHoldingMap={holdingPlannedMap}
              plannedGroupMap={plannedCompanyGroupMap}
              showTotal={pageIndex === companyPages.length - 1}
            />
          </Slide>
        ),
      });
    });

    // One page per company right after the scorecard: its EVM reading (SPI / CPI / PV / EV / AC).
    const evmByCompany = new Map((evm?.actual.companies ?? []).map((c) => [c.company_id, c]));
    const profileCompanies = [
      ...companies.map((c) => ({ id: c.id, name: c.name, rows: c.rows })),
      ...(evm?.actual.companies ?? []).filter((c) => !companies.some((x) => x.id === c.company_id)).map((c) => ({ id: c.company_id, name: c.company, rows: new Map<string, ResultRow>() })),
    ];
    profileCompanies.forEach((comp) => {
      result.push({
        key: `company-profile-${comp.id}`,
        render: (page) => (
          <Slide
            title={comp.name}
            subtitle={`کارنامه شرکت · ${period}`}
            titleAside={companyScorecardBadge}
            headerRight={<CompanyMark name={comp.name} size={54} />}
            page={page}
            period={period}
          >
            <CompanyProfileBody
              evm={evmByCompany.get(comp.id) ?? null}
            />
          </Slide>
        ),
      });
    });

    const shareDataList: ItemShareData[] = tableMetrics
      .map((item) => {
        const contributions: CompanyContribution[] = [];
        let sumQtyStr = "0";
        for (let cIdx = 0; cIdx < companies.length; cIdx += 1) {
          const comp = companies[cIdx]!;
          const row = comp.rows.get(item.key);
          const qty = row ? Number.parseFloat(row.qty || "0") : 0;
          if (qty > 0) {
            sumQtyStr = addDecimalStrings(sumQtyStr, row!.qty || "0");
            contributions.push({
              companyId: comp.id,
              companyName: comp.name,
              qty,
              pct: 0,
              color: getCompanyColor(comp.name, cIdx),
            });
          }
        }
        const holdingRow = holdingMap.get(item.key);
        const holdingQty = holdingRow ? Number.parseFloat(holdingRow.qty || "0") : 0;
        const sumQty = contributions.reduce((acc, c) => acc + c.qty, 0);
        const baseTotal = sumQty > 0 ? sumQty : holdingQty;
        const baseTotalStr = sumQty > 0 ? sumQtyStr : (holdingRow?.qty ?? "0");
        if (baseTotal > 0) {
          for (const c of contributions) {
            c.pct = (c.qty / baseTotal) * 100;
          }
          contributions.sort((a, b) => b.qty - a.qty);
        }
        return {
          item,
          totalQty: baseTotal,
          totalQtyStr: baseTotalStr,
          contributions,
        };
      })
      .filter((data) => data.totalQty > 0);

    const activeShareData =
      shareDataList.length > 0
        ? shareDataList
        : tableMetrics.map((item) => ({
            item,
            totalQty: 0,
            totalQtyStr: "0",
            contributions: [],
          }));

    const companyShareLegend = (
      <div
        className={`flex flex-wrap items-center gap-4 rounded-full border border-[#252850]/15 bg-white/95 font-bold text-[#252850] shadow-sm ${
          companies.length <= 6 ? "px-5 py-2 text-[14px]" : "px-4 py-1.5 text-[12.5px]"
        }`}
      >
        {companies.map((comp, idx) => (
          <span key={comp.id} className="flex items-center gap-2">
            <span
              className="h-3 w-3 shrink-0 rounded-full shadow-sm"
              style={{ backgroundColor: getCompanyColor(comp.name, idx) }}
            />
            <span className="max-w-[160px] truncate">{comp.name}</span>
          </span>
        ))}
      </div>
    );

    const sharePages = splitSharePages(activeShareData, 8);
    sharePages.forEach((pageItems, pageIndex) => {
      result.push({
        key: `company-shares-${pageIndex}`,
        render: (page) => (
          <Slide
            title="سهم شرکت‌ها در احجام عملیات"
            subtitle={
              sharePages.length > 1
                ? `بخش ${toFa(pageIndex + 1)} از ${toFa(sharePages.length)}`
                : "توزیع درصدی عملکرد هر شرکت نسبت به کل هلدینگ"
            }
            headerRight={companyShareLegend}
            page={page}
            period={period}
          >
            <ShareGrid items={pageItems} />
          </Slide>
        ),
      });
    });

    const PROJECT_ROWS_PER_SLIDE = 10;
    const projectPages = chunks(projects, PROJECT_ROWS_PER_SLIDE);
    if (!projectPages.length) projectPages.push([]);
    projectPages.forEach((groupSet, pageIndex) => {
      result.push({
        key: `projects-${pageIndex}`,
        render: (page) => (
          <Slide
            title="کارنامه پروژه‌ها"
            subtitle={projectPages.length > 1 ? `بخش ${toFa(pageIndex + 1)} از ${toFa(projectPages.length)}` : period}
            headerRight={tableLegend}
            page={page}
            period={period}
          >
            <ScorecardTable
              entityType="project"
              groups={groupSet}
              metrics={tableMetrics}
              holdingMap={holdingMap}
              plannedHoldingMap={holdingPlannedMap}
              plannedGroupMap={plannedProjectGroupMap}
              showTotal={pageIndex === projectPages.length - 1}
            />
          </Slide>
        ),
      });
    });

    const narrativeCompanies = companies
      .map((comp) => {
        const narrative = report.narratives?.[comp.id] || report.narratives?.[comp.name];
        const items = getCompanyNarrativeItems(narrative);
        return { comp, items };
      })
      .filter(({ items }) => items.length > 0);

    const narrativePages = chunks(narrativeCompanies, NARRATIVE_COMPANIES_PER_SLIDE);
    narrativePages.forEach((pageCompanies, pageIndex) => {
      result.push({
        key: `narratives-${pageIndex}`,
        render: (page) => (
          <Slide
            title="گزارش عملکرد پروژه‌های عمرانی"
            subtitle={
              narrativePages.length > 1
                ? `مرور وضعیت و اقدامات شرکت‌ها · بخش ${toFa(pageIndex + 1)} از ${toFa(narrativePages.length)}`
                : "مرور وضعیت و اقدامات شرکت‌ها"
            }
            page={page}
            period={period}
          >
            <div className="grid min-h-0 flex-1 grid-cols-2 gap-6">
              {pageCompanies.map(({ comp, items }, idx) => {
                const globalIdx = pageIndex * NARRATIVE_COMPANIES_PER_SLIDE + idx;
                return (
                  <CompanyNarrativeCard
                    key={comp.id}
                    company={comp}
                    index={globalIdx}
                    items={items}
                  />
                );
              })}
            </div>
          </Slide>
        ),
      });
    });

    result.push({
      key: "closing",
      render: () => (
        <section className="presentation-slide-print">
          <div
            className="slide-canvas flex flex-col items-center justify-center bg-[#252850] text-center text-white"
            style={{ backgroundColor: NAVY, color: "#ffffff" }}
            data-slide-bg={NAVY}
          >
            <div className="absolute inset-y-0 start-0 w-4 bg-[#fed836]" />
            <div className="flex items-center justify-center gap-6 rounded-[32px] bg-white px-8 py-6 shadow-2xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/volume-reports/jihad_nasr_kerman.png"
                alt="لوگوی جهاد نصر کرمان"
                loading="eager"
                decoding="sync"
                width={160}
                height={140}
                className="h-[140px] w-[160px] object-contain"
              />
              <div className="h-24 w-px bg-slate-200" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/volume-reports/logo_mehvar.png"
                alt="لوگوی شرکت محور گستر نصر"
                loading="eager"
                decoding="sync"
                width={160}
                height={140}
                className="h-[140px] w-[160px] object-contain"
              />
            </div>
            <h2 className="mt-10 text-[52px] font-black">گزارش عملکرد هلدینگ عمرانی</h2>
            <div className="mt-6 h-1.5 w-28 rounded-full bg-[#fed836]" />
            <p className="mt-6 text-[22px] text-white/70">{period} · {formatJalaliDate(report.period_end)}</p>
          </div>
        </section>
      ),
    });
    return result;
  }, [
    catalog,
    companyPlannedRows,
    companyRows,
    evm,
    handleSelectSummaryVariant,
    holding,
    holdingPlanned,
    report,
    settingsCompanies,
    sitePlannedRows,
    siteRows,
    summaryVariant,
    weekSubtitle,
  ]);

  async function exportPdf() {
    if (!report || exporting) return;
    setExportError(null);
    setExporting({ done: 0, total: slides.length });
    try {
      await downloadPdf(report.title.replace(/[\\/:*?"<>|]+/g, " ").trim() || "volume-report", (done, total) => setExporting({ done, total }));
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : "ساخت PDF ناموفق بود.");
    } finally {
      setExporting(null);
    }
  }

  if (error) return <div className="p-6"><ErrorBox error={error} onRetry={() => void load()} /></div>;
  if (!report || !holding) return <LoadingBlock />;

  if (!READY_STATUSES.has(report.status)) {
    return (
      <div className="mx-auto max-w-2xl p-8 text-center">
        <p className="text-lg font-semibold text-slate-800">ارائه هنوز آماده نیست</p>
        <p className="mt-2 text-sm text-slate-500">ابتدا پردازش گزارش را کامل کنید.</p>
        <Link href={`/volume-reports/${reportId}`} className="mt-5 inline-flex rounded-xl bg-[#252850] px-4 py-2 text-sm text-white">بازگشت به گزارش</Link>
      </div>
    );
  }

  return (
    <div className="presentation-page min-h-full bg-[#edf0f3] p-3 md:p-6" dir="rtl" lang="fa">
      <div className="no-print mx-auto mb-4 flex max-w-[1600px] flex-col gap-3 rounded-2xl bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href={`/volume-reports/${reportId}`} className="text-xs text-slate-500 hover:text-[#252850]">بازگشت به گزارش</Link>
            <h1 className="mt-1 text-base font-bold text-[#252850]">گزارش عملکرد هلدینگ عمرانی — {weekSubtitle}</h1>
            <p className="mt-1 text-[11px] text-slate-500">{toFa(slides.length)} اسلاید</p>
          </div>
          <div className="flex items-center gap-3">
            {exportError && <span className="text-xs text-red-600">{exportError}</span>}
            <button type="button" disabled={Boolean(exporting)} onClick={() => void exportPdf()} className="rounded-xl bg-[#252850] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1e2246] disabled:opacity-60">
              {exporting ? `در حال ساخت PDF… ${toFa(exporting.done)} از ${toFa(exporting.total)}` : "دانلود PDF"}
            </button>
          </div>
        </div>
        <SummaryVariantBar
          variant={summaryVariant}
          onSelect={handleSelectSummaryVariant}
          onJumpToSlide={scrollToSummarySlide}
        />
      </div>
      <div ref={pageRef} className="print-only-container mx-auto flex max-w-[1600px] flex-col gap-5" style={{ ["--slide-scale" as string]: scale }}>
        {slides.map((slide, index) => <SlideItem key={slide.key} slide={slide} page={toFa(index + 1)} />)}
      </div>
    </div>
  );
}

function SlideItem({ slide, page }: { slide: SlideSpec; page: string }) {
  return <>{slide.render(page)}</>;
}
