"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { ErrorBox, LoadingBlock } from "../components/common";
import { runSoon } from "../lib/defer";
import { formatQuantity, unitLabel } from "../lib/format";
import { formatJalaliDate, formatWeekLabel, toFa } from "../lib/jalali";
import type { CatalogItem, CompanyNarrative, ReportDetail, ResultRow, ResultsResponse } from "../types";

/** The slide canvas is 16in x 9in at 96dpi, so it prints 1:1 and is scaled down with CSS on screen (see globals.css). */
const SLIDE_W = 1536;
const SLIDE_H = 864;
const NAVY = "#252850";
const READY_STATUSES = new Set(["awaiting_user", "needs_review", "ready", "published"]);
const NARRATIVE_COMPANIES_PER_SLIDE = 2;

const LOGOS: { match: string[]; src: string; label: string }[] = [
  { match: ["فراگیر", "faragir"], src: "/volume-reports/logo_faragir.png", label: "فراگیر عمران نصر" },
  { match: ["سیستان", "sistan"], src: "/volume-reports/logo_sistan.png", label: "جهاد نصر سیستان" },
  { match: ["گلومک", "golomak"], src: "/volume-reports/logo_golomak.png", label: "گلومک سازه نصر" },
  { match: ["آبادگران", "abadgaran"], src: "/volume-reports/logo_abadgaran.png", label: "آبادگران رفاه نصر" },
  { match: ["محورگستر", "محور گستر", "mehvar"], src: "/volume-reports/logo_mehvar.png", label: "محور گستر نصر" },
  { match: ["تژه", "tezhe"], src: "/volume-reports/logo_tezheh.png", label: "تژه نصر" },
];

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
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name, "fa"));
}

function matchLogo(name: string) {
  const normalized = name.toLocaleLowerCase("fa");
  return LOGOS.find((logo) => logo.match.some((part) => normalized.includes(part)));
}

function CompanyMark({ name, size }: { name: string; size: number }) {
  const logo = matchLogo(name);
  if (logo) {
    // Plain <img>: next/image can defer or skip loading in print, which left the logos blank in the PDF.
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={logo.src} alt={logo.label} loading="eager" decoding="sync" style={{ width: size * 1.25, height: size }} className="shrink-0 object-contain" />;
  }
  return <span style={{ width: size, height: size }} className="grid shrink-0 place-items-center rounded-lg bg-[#252850] text-sm font-bold text-[#fed836]">{name.slice(0, 1)}</span>;
}

interface SlideSpec { key: string; render: (page: string) => ReactNode }

function Slide({
  title,
  subtitle,
  headerRight,
  page,
  period,
  children,
}: {
  title: string;
  subtitle?: string;
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
          <div>
            {subtitle && <p className="mb-1 text-[14px] font-semibold text-[#9b7a05]">{subtitle}</p>}
            <h2 className="text-[32px] font-black leading-tight text-[#252850]">{title}</h2>
          </div>
          <div className="mb-1.5 flex items-center gap-4">
            {headerRight}
            <span className="h-1.5 w-24 shrink-0 rounded-full bg-[#fed836]" />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        <div className="mt-2.5 flex shrink-0 items-center justify-between text-[13px] text-slate-400">
          <span>جهاد نصر کرمان · {period}</span>
          <span className="tabular-nums">{page}</span>
        </div>
      </div>
    </section>
  );
}

function SummaryCard({ item, row }: { item: CatalogItem; row: ResultRow | undefined }) {
  const empty = !row;
  const title = item.key === "asphalt_total" ? "آسفالت" : item.title_fa;
  return (
    <div className={`flex flex-col justify-between rounded-2xl border border-[#252850]/10 bg-white p-5 shadow-sm ${empty ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[17px] font-bold text-slate-800">{title}</p>
        {item.key === "asphalt_total" && (
          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">بیندر + توپکا</span>
        )}
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-2">
        <p className="text-[32px] font-black leading-none tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : "—"}</p>
        <p className="text-[14px] font-medium text-slate-400">{unitLabel(item.output_unit)}</p>
      </div>
    </div>
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
  return (
    <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white shadow-sm">
      <table className="w-full table-fixed border-collapse text-[15px]">
        <thead className="bg-[#252850] text-white">
          <tr>
            <th className="w-[210px] px-3.5 py-3 text-start text-[15px] font-bold">
              {isCompany ? "شرکت" : "پروژه"}
            </th>
            {metrics.map((item) => (
              <th key={item.key} className="px-1.5 py-2.5 text-center text-[13.5px] font-semibold leading-snug">
                <div className="truncate">{item.key === "asphalt_total" ? "آسفالت" : item.title_fa}</div>
                <span className="block text-[11px] font-normal text-white/60">{unitLabel(item.output_unit)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => {
            const planGroup = plannedGroupMap?.get(group.id);
            return (
              <tr key={group.id} className="h-[46px] border-t border-slate-100 odd:bg-white even:bg-slate-50/70">
                <th scope="row" className="px-3.5 text-start font-bold text-slate-800">
                  {isCompany ? (
                    <span className="flex items-center gap-2.5">
                      <CompanyMark name={group.name} size={26} />
                      <span className="truncate text-[14.5px]">{group.name}</span>
                    </span>
                  ) : (
                    <div className="flex flex-col min-w-0">
                      <span className="truncate text-[14.5px] font-bold text-slate-800">{group.name}</span>
                      {group.companyName && (
                        <span className="truncate text-[11.5px] font-normal text-slate-400">{group.companyName}</span>
                      )}
                    </div>
                  )}
                </th>
                {metrics.map((item) => {
                  const row = group.rows.get(item.key);
                  const planRow = planGroup?.get(item.key);
                  const hasPlan = planRow && Number.parseFloat(planRow.qty || "0") > 0;
                  return (
                    <td key={item.key} className="px-1 py-1 text-center tabular-nums">
                      <div className="text-[14px] font-bold text-[#252850]">
                        {row ? formatQuantity(row.qty, item.decimals) : <span className="text-slate-300 font-normal">—</span>}
                      </div>
                      {hasPlan && (
                        <div className="text-[10.5px] font-medium text-slate-500">
                          برنامه: {formatQuantity(planRow.qty, item.decimals)}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {showTotal && (
            <tr className="h-[50px] border-t-2 border-[#252850] bg-[#fed836]/25">
              <th scope="row" className="px-3.5 text-start text-[15.5px] font-black text-[#252850]">
                جمع هلدینگ
              </th>
              {metrics.map((item) => {
                const row = holdingMap.get(item.key);
                const planRow = plannedHoldingMap?.get(item.key);
                const hasPlan = planRow && Number.parseFloat(planRow.qty || "0") > 0;
                return (
                  <td key={item.key} className="px-1 py-1 text-center tabular-nums">
                    <div className="text-[14.5px] font-black text-[#252850]">
                      {row ? formatQuantity(row.qty, item.decimals) : <span className="text-slate-300 font-normal">—</span>}
                    </div>
                    {hasPlan && (
                      <div className="text-[11px] font-bold text-[#9b7a05]">
                        برنامه: {formatQuantity(planRow.qty, item.decimals)}
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
  contributions: CompanyContribution[];
}

const COMPANY_PALETTE: { match: string[]; color: string; label: string }[] = [
  { match: ["محورگستر", "محور گستر", "mehvar"], color: "#252850", label: "محور گستر نصر" },
  { match: ["آبادگران", "abadgaran"], color: "#d97706", label: "آبادگران رفاه نصر" },
  { match: ["فراگیر", "faragir"], color: "#059669", label: "فراگیر عمران نصر" },
  { match: ["گلومک", "golomak"], color: "#7c3aed", label: "گلومک سازه نصر" },
  { match: ["سیستان", "sistan"], color: "#0284c7", label: "جهاد نصر سیستان" },
  { match: ["تژه", "tezhe"], color: "#e11d48", label: "تژه نصر" },
];

const FALLBACK_COLORS = ["#252850", "#d97706", "#059669", "#7c3aed", "#0284c7", "#e11d48", "#0891b2", "#ea580c", "#4f46e5", "#16a34a"];

function getCompanyColor(name: string, index = 0): string {
  const normalized = name.toLocaleLowerCase("fa");
  const found = COMPANY_PALETTE.find((item) => item.match.some((part) => normalized.includes(part)));
  return found?.color ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length]!;
}

function DonutChart({
  contributions,
  totalFormatted,
  unit,
  size = 146,
  strokeWidth = 18,
}: {
  contributions: CompanyContribution[];
  totalFormatted: string;
  unit: string;
  size?: number;
  strokeWidth?: number;
}) {
  const center = size / 2;
  const radius = center - strokeWidth / 2 - 2;
  const circumference = 2 * Math.PI * radius;
  const hasMultiple = contributions.length > 1;
  const gap = hasMultiple ? 2.5 : 0;

  const slices: { c: CompanyContribution; strokeLength: number; dashoffset: number }[] = [];
  let offset = 0;
  for (const c of contributions) {
    const sliceLength = (c.pct / 100) * circumference;
    const strokeLength = Math.max(sliceLength - gap, 1);
    slices.push({ c, strokeLength, dashoffset: -offset });
    offset += sliceLength;
  }

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#f1f5f9"
          strokeWidth={strokeWidth}
        />

        {/* Slices */}
        {slices.map(({ c, strokeLength, dashoffset }) => (
          <circle
            key={c.companyId}
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={c.color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${strokeLength} ${circumference - strokeLength}`}
            strokeDashoffset={dashoffset}
            transform={`rotate(-90 ${center} ${center})`}
            className="transition-all"
          >
            <title>{`${c.companyName}: %${toFa(Math.round(c.pct))}`}</title>
          </circle>
        ))}
      </svg>

      {/* Center content */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-2 text-center">
        <span className="text-[10px] font-semibold text-slate-400">جمع کل</span>
        <span className="text-[15px] font-black leading-tight text-[#252850] tabular-nums">
          {totalFormatted}
        </span>
        <span className="text-[10px] font-bold text-slate-400">{unit}</span>
      </div>
    </div>
  );
}

function DonutShareCard({ data }: { data: ItemShareData }) {
  const { item, totalQty, contributions } = data;
  const title = item.key === "asphalt_total" ? "آسفالت" : item.title_fa;
  const unit = unitLabel(item.output_unit);
  const formattedTotal = formatQuantity(totalQty.toString(), item.decimals);

  return (
    <div className="flex min-h-0 flex-col justify-between rounded-3xl border border-[#252850]/10 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[16px] font-black text-[#252850]">{title}</span>
          {item.key === "asphalt_total" && (
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10.5px] font-semibold text-slate-500">
              بیندر + توپکا
            </span>
          )}
        </div>
      </div>

      {/* Donut Chart */}
      <div className="my-2.5 flex items-center justify-center">
        <DonutChart
          contributions={contributions}
          totalFormatted={formattedTotal}
          unit={unit}
          size={146}
          strokeWidth={18}
        />
      </div>

      {/* Company Share Pills */}
      <div className="flex flex-wrap items-center justify-center gap-1.5 pt-1">
        {contributions.length === 0 ? (
          <span className="text-[11.5px] text-slate-400">فاقد عملکرد در این دوره</span>
        ) : (
          contributions.map((c) => (
            <div
              key={c.companyId}
              className="flex items-center gap-1.5 rounded-full border border-slate-200/70 bg-slate-50/90 px-2.5 py-0.5 shadow-2xs"
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: c.color }}
              />
              <span className="max-w-[110px] truncate text-[11.5px] font-bold text-slate-700">
                {c.companyName}
              </span>
              <span className="text-[12px] font-black tabular-nums" style={{ color: c.color }}>
                %{toFa(Math.round(c.pct))}
              </span>
            </div>
          ))
        )}
      </div>
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
          className="flex h-9 w-9 items-center justify-center rounded-2xl text-[14px] font-black text-white shadow-xs"
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
  const [error, setError] = useState<unknown>(null);
  const [exporting, setExporting] = useState<{ done: number; total: number } | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const { scale, ref: pageRef } = useSlideScale();

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
      ] = await Promise.all([
        volumeReportApi.get(reportId),
        volumeReportApi.catalog(),
        volumeReportApi.results(reportId, "holding"),
        volumeReportApi.results(reportId, "company"),
        volumeReportApi.results(reportId, "site"),
        volumeReportApi.results(reportId, "company", [], "planned").catch(() => null),
        volumeReportApi.results(reportId, "holding", [], "planned").catch(() => null),
        volumeReportApi.results(reportId, "site", [], "planned").catch(() => null),
      ]);
      setReport(detail);
      setCatalog(items);
      setHolding(holdingResult);
      setCompanyRows(companyResult.rows);
      setSiteRows(siteResult.rows);
      setCompanyPlannedRows(companyPlannedResult?.rows ?? []);
      setHoldingPlanned(holdingPlannedResult ?? null);
      setSitePlannedRows(sitePlannedResult?.rows ?? []);
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
    const EXCLUDED_ITEM_KEYS = new Set(["asphalt_binder", "asphalt_topka"]);
    const visibleItems = catalog.filter((item) => (!item.is_rollup || item.key === "asphalt_total") && !EXCLUDED_ITEM_KEYS.has(item.key));
    const holdingMap = new Map(holding.rows.map((row) => [row.item_key, row]));
    const holdingPlannedMap = new Map((holdingPlanned?.rows ?? []).map((row) => [row.item_key, row]));
    const companies = groupByCompany(companyRows, companyPlannedRows);
    const projects = groupByProject(siteRows, sitePlannedRows);
    const period = weekSubtitle || report.period_label;
    const hasAnyReportPlanned =
      companyPlannedRows.some((r) => Number.parseFloat(r.qty || "0") > 0) ||
      sitePlannedRows.some((r) => Number.parseFloat(r.qty || "0") > 0);
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

    const overviewStats = [
      { label: "شرکت‌های دارای عملکرد", value: toFa(companies.length) },
      { label: "پروژه‌های دارای عملکرد", value: toFa(projects.length) },
    ];
    const logoCols = companies.length > 6 ? 4 : 3;
    result.push({
      key: "overview",
      render: (page) => (
        <Slide title="نمای کلی گزارش" subtitle={period} page={page} period={period}>
          <div className="grid grid-cols-2 gap-6">
            {overviewStats.map((stat) => (
              <div key={stat.label} className="rounded-3xl border border-[#252850]/10 bg-white p-6">
                <p className="text-[18px] text-slate-500">{stat.label}</p>
                <p className="mt-3 text-[56px] font-black leading-none tabular-nums text-[#252850]">{stat.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 grid min-h-0 flex-1 gap-5" style={{ gridTemplateColumns: `repeat(${logoCols}, minmax(0, 1fr))`, gridAutoRows: "1fr" }}>
            {companies.map((company) => (
              <div key={company.id} className="flex items-center gap-5 rounded-3xl border border-[#252850]/10 bg-white px-6">
                <CompanyMark name={company.name} size={72} />
                <div className="min-w-0">
                  <p className="text-[24px] font-black leading-snug text-[#252850]">{company.name}</p>
                </div>
              </div>
            ))}
          </div>
        </Slide>
      ),
    });

    result.push({
      key: "summary",
      render: (page) => (
        <Slide title="خلاصه عملکرد هلدینگ" subtitle={period} page={page} period={period}>
          <div className="grid min-h-0 flex-1 grid-cols-4 gap-4" style={{ gridAutoRows: "1fr" }}>
            {visibleItems.map((item) => <SummaryCard key={item.key} item={item} row={holdingMap.get(item.key)} />)}
          </div>
        </Slide>
      ),
    });

    const plannedCompanyGroupMap = new Map<string, Map<string, ResultRow>>();
    for (const row of companyPlannedRows) {
      if (!row.company_id) continue;
      let sub = plannedCompanyGroupMap.get(row.company_id);
      if (!sub) {
        sub = new Map();
        plannedCompanyGroupMap.set(row.company_id, sub);
      }
      sub.set(row.item_key, row);
    }

    const plannedProjectGroupMap = new Map<string, Map<string, ResultRow>>();
    for (const row of sitePlannedRows) {
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
      ...holding.rows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...(holdingPlanned?.rows ?? []).filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...companyRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...companyPlannedRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...siteRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
      ...sitePlannedRows.filter((r) => Number.parseFloat(r.qty || "0") > 0).map((r) => r.item_key),
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

    const shareDataList: ItemShareData[] = tableMetrics
      .map((item) => {
        const contributions: CompanyContribution[] = [];
        for (let cIdx = 0; cIdx < companies.length; cIdx += 1) {
          const comp = companies[cIdx]!;
          const row = comp.rows.get(item.key);
          const qty = row ? Number.parseFloat(row.qty || "0") : 0;
          if (qty > 0) {
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
        if (baseTotal > 0) {
          for (const c of contributions) {
            c.pct = (c.qty / baseTotal) * 100;
          }
          contributions.sort((a, b) => b.qty - a.qty);
        }
        return {
          item,
          totalQty: baseTotal,
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
            contributions: [],
          }));

    const companyShareLegend = (
      <div className="flex flex-wrap items-center gap-4 rounded-full border border-[#252850]/10 bg-white/95 px-4 py-1.5 text-[12.5px] font-bold text-slate-700 shadow-sm">
        {companies.map((comp, idx) => (
          <span key={comp.id} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full shadow-xs"
              style={{ backgroundColor: getCompanyColor(comp.name, idx) }}
            />
            <span className="max-w-[140px] truncate">{comp.name}</span>
          </span>
        ))}
      </div>
    );

    const SHARE_ITEMS_PER_SLIDE = 8;
    const sharePages = chunks(activeShareData, SHARE_ITEMS_PER_SLIDE);
    if (!sharePages.length) sharePages.push([]);
    sharePages.forEach((pageItems, pageIndex) => {
      const gridCols =
        pageItems.length <= 4
          ? "grid-cols-2 lg:grid-cols-4"
          : pageItems.length <= 6
          ? "grid-cols-3"
          : "grid-cols-4";

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
            <div
              className={`grid min-h-0 flex-1 gap-4 ${gridCols}`}
              style={{ gridAutoRows: "1fr" }}
            >
              {pageItems.map((data) => (
                <DonutShareCard key={data.item.key} data={data} />
              ))}
            </div>
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
  }, [catalog, companyPlannedRows, companyRows, holding, holdingPlanned, report, sitePlannedRows, siteRows, weekSubtitle]);

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
      <div className="no-print mx-auto mb-4 flex max-w-[1600px] flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm">
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
      <div ref={pageRef} className="print-only-container mx-auto flex max-w-[1600px] flex-col gap-5" style={{ ["--slide-scale" as string]: scale }}>
        {slides.map((slide, index) => <SlideItem key={slide.key} slide={slide} page={toFa(index + 1)} />)}
      </div>
    </div>
  );
}

function SlideItem({ slide, page }: { slide: SlideSpec; page: string }) {
  return <>{slide.render(page)}</>;
}
