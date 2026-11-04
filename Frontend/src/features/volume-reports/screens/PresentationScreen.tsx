"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { ErrorBox, LoadingBlock } from "../components/common";
import { runSoon } from "../lib/defer";
import { formatQuantity, unitLabel } from "../lib/format";
import { formatJalaliDate, toFa } from "../lib/jalali";
import type { CatalogItem, ReportDetail, ResultRow, ResultsResponse, SourceInfo } from "../types";

/** The slide canvas is 16in x 9in at 96dpi, so it prints 1:1 and is scaled down with CSS on screen (see globals.css). */
const SLIDE_W = 1536;
const NAVY = "#252850";
const READY_STATUSES = new Set(["awaiting_user", "needs_review", "ready", "published"]);
const HERO_KEYS = ["excavation", "fill", "asphalt_total", "concrete"];
const MAX_METRIC_COLUMNS = 11;
const COMPANY_ROWS_PER_SLIDE = 12;
const CHART_BARS_MAX = 9;
const SOURCE_ROWS_PER_SLIDE = 12;

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

/** Splits into the fewest, evenly sized groups of at most `max` entries. */
function balancedChunks<T>(items: T[], max: number): T[][] {
  if (!items.length) return [];
  const parts = Math.ceil(items.length / max);
  return chunks(items, Math.ceil(items.length / parts));
}

type CompanyGroup = { id: string; name: string; rows: Map<string, ResultRow> };

function groupByCompany(rows: ResultRow[]): CompanyGroup[] {
  const groups = new Map<string, CompanyGroup>();
  for (const row of rows) {
    if (!row.company_id) continue;
    const group = groups.get(row.company_id) ?? { id: row.company_id, name: row.company ?? "بدون نام", rows: new Map<string, ResultRow>() };
    group.rows.set(row.item_key, row);
    groups.set(row.company_id, group);
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

function Slide({ title, subtitle, page, period, children }: { title: string; subtitle?: string; page: string; period: string; children: ReactNode }) {
  return (
    <section className="presentation-slide-print">
      <div className="slide-canvas flex flex-col bg-[#f7f7f5] px-14 pb-5 pt-10 text-slate-900">
        <div className="mb-6 flex shrink-0 items-end justify-between gap-6 border-b-2 border-[#252850]/10 pb-4">
          <div>
            {subtitle && <p className="mb-1 text-[15px] font-semibold text-[#9b7a05]">{subtitle}</p>}
            <h2 className="text-[36px] font-black leading-tight text-[#252850]">{title}</h2>
          </div>
          <span className="mb-2 h-1.5 w-24 shrink-0 rounded-full bg-[#fed836]" />
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        <div className="mt-3 flex shrink-0 items-center justify-between text-[13px] text-slate-400">
          <span>جهاد نصر کرمان · {period}</span>
          <span className="tabular-nums">{page}</span>
        </div>
      </div>
    </section>
  );
}

function SummaryCard({ item, row, hero }: { item: CatalogItem; row: ResultRow | undefined; hero: boolean }) {
  const empty = !row;
  if (hero) {
    return (
      <div className="flex flex-col justify-between rounded-3xl bg-[#252850] p-6 text-white">
        <p className="text-[18px] font-semibold text-white/80">{item.title_fa}</p>
        <div>
          <p className="text-[44px] font-black leading-none tabular-nums text-[#fed836]">{row ? formatQuantity(row.qty, item.decimals) : "—"}</p>
          <p className="mt-2 text-[15px] text-white/60">{unitLabel(item.output_unit)}</p>
        </div>
      </div>
    );
  }
  return (
    <div className={`flex flex-col justify-between rounded-2xl border border-[#252850]/10 bg-white p-5 ${empty ? "opacity-50" : ""}`}>
      <p className="text-[17px] font-semibold text-slate-700">{item.title_fa}</p>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[30px] font-black leading-none tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : "—"}</p>
        <p className="text-[14px] text-slate-400">{unitLabel(item.output_unit)}</p>
      </div>
    </div>
  );
}

function ChartCard({ item, rows, total }: { item: CatalogItem; rows: ResultRow[]; total: ResultRow | undefined }) {
  const entries = groupByCompany(rows.filter((row) => row.item_key === item.key))
    .map((company) => ({ company, row: company.rows.get(item.key)!, value: Number.parseFloat(company.rows.get(item.key)?.qty ?? "0") }))
    .sort((a, b) => b.value - a.value)
    .slice(0, CHART_BARS_MAX);
  const maxValue = Math.max(0, ...entries.map((entry) => entry.value));
  return (
    <div className="flex min-h-0 flex-col rounded-3xl border border-[#252850]/10 bg-white p-6">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h3 className="text-[22px] font-black text-[#252850]">{item.title_fa}</h3>
        <span className="text-[15px] text-slate-500">
          {total ? <><b className="tabular-nums text-[#252850]">{formatQuantity(total.qty, item.decimals)}</b> {unitLabel(item.output_unit)}</> : unitLabel(item.output_unit)}
        </span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col justify-around gap-2">
        {entries.map(({ company, row, value }, index) => {
          const width = maxValue > 0 ? Math.max(value > 0 ? 1.5 : 0, (value / maxValue) * 100) : 0;
          return (
            <div key={company.id} className="grid grid-cols-[170px_1fr_110px] items-center gap-3 text-[15px]">
              <span className="truncate font-medium text-slate-700">{company.name}</span>
              <div className="h-4 overflow-hidden rounded-full bg-[#e7e8f0]">
                <div className="h-full rounded-full" style={{ width: `${width}%`, backgroundColor: index === 0 ? NAVY : "#8d90b5" }} />
              </div>
              <span className="text-end font-bold tabular-nums text-[#252850]">{formatQuantity(row.qty, item.decimals)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CompanyTable({ groups, metrics, holdingMap, showTotal }: { groups: CompanyGroup[]; metrics: CatalogItem[]; holdingMap: Map<string, ResultRow>; showTotal: boolean }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white">
      <table className="w-full table-fixed border-collapse text-[16px]">
        <thead className="bg-[#252850] text-white">
          <tr>
            <th className="w-[230px] px-4 py-3 text-start text-[17px] font-bold">شرکت</th>
            {metrics.map((item) => (
              <th key={item.key} className="px-2 py-3 text-start text-[15px] font-semibold leading-snug">
                {item.title_fa}
                <span className="block text-[12px] font-normal text-white/60">{unitLabel(item.output_unit)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.id} className="h-[48px] border-t border-slate-100 odd:bg-white even:bg-slate-50">
              <th scope="row" className="px-4 text-start font-bold text-slate-800">
                <span className="flex items-center gap-3"><CompanyMark name={group.name} size={28} /><span className="truncate">{group.name}</span></span>
              </th>
              {metrics.map((item) => {
                const row = group.rows.get(item.key);
                return <td key={item.key} className="px-2 font-semibold tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : <span className="text-slate-300">—</span>}</td>;
              })}
            </tr>
          ))}
          {showTotal && (
            <tr className="h-[52px] border-t-2 border-[#252850] bg-[#fed836]/25">
              <th scope="row" className="px-4 text-start text-[17px] font-black text-[#252850]">جمع هولدینگ</th>
              {metrics.map((item) => {
                const row = holdingMap.get(item.key);
                return <td key={item.key} className="px-2 font-black tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : <span className="text-slate-300">—</span>}</td>;
              })}
            </tr>
          )}
        </tbody>
      </table>
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

/** Waits for every image on the page so the PDF never prints a logo placeholder. */
async function printWhenImagesReady() {
  const pending = Array.from(document.images).filter((image) => !image.complete);
  await Promise.all(pending.map((image) => image.decode().catch(() => undefined)));
  window.print();
}

export function PresentationScreen({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [holding, setHolding] = useState<ResultsResponse | null>(null);
  const [companyRows, setCompanyRows] = useState<ResultRow[]>([]);
  const [siteRows, setSiteRows] = useState<ResultRow[]>([]);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [error, setError] = useState<unknown>(null);
  const { scale, ref: pageRef } = useSlideScale();

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, items, holdingResult, companyResult, siteResult, sourceFiles] = await Promise.all([
        volumeReportApi.get(reportId),
        volumeReportApi.catalog(),
        volumeReportApi.results(reportId, "holding"),
        volumeReportApi.results(reportId, "company"),
        volumeReportApi.results(reportId, "site"),
        volumeReportApi.sources(reportId),
      ]);
      setReport(detail);
      setCatalog(items);
      setHolding(holdingResult);
      setCompanyRows(companyResult.rows);
      setSiteRows(siteResult.rows);
      setSources(sourceFiles);
    } catch (reason) {
      setError(reason);
    }
  }, [reportId]);

  useEffect(() => runSoon(() => void load()), [load]);

  const slides = useMemo<SlideSpec[]>(() => {
    if (!report || !holding) return [];
    const visibleItems = catalog.filter((item) => !item.is_rollup || item.key === "asphalt_total");
    const holdingMap = new Map(holding.rows.map((row) => [row.item_key, row]));
    const companies = groupByCompany(companyRows);
    const siteCount = new Set(siteRows.map((row) => row.site_id).filter(Boolean)).size;
    const period = report.period_label;
    const result: SlideSpec[] = [];

    result.push({
      key: "cover",
      render: () => (
        <section className="presentation-slide-print">
          <div className="slide-canvas flex bg-[#252850] text-white">
            <div className="absolute inset-y-0 start-0 w-4 bg-[#fed836]" />
            <div className="flex min-w-0 flex-1 flex-col justify-center ps-24 pe-12">
              <p className="mb-6 text-[22px] font-bold text-[#fed836]">گزارش مدیریتی احجام عملیات اجرایی</p>
              <h1 className="max-w-[820px] text-[68px] font-black leading-[1.45]">{report.title}</h1>
              <div className="mt-12 h-1.5 w-32 rounded-full bg-[#fed836]" />
              <div className="mt-8 flex flex-col gap-2 text-[22px] text-white/80">
                <span>{period}</span>
                <span className="text-[18px] text-white/60">{formatJalaliDate(report.period_start)} تا {formatJalaliDate(report.period_end)}</span>
              </div>
            </div>
            <div className="flex w-[40%] items-center justify-center pe-16">
              <div className="rounded-[40px] bg-white p-8 shadow-2xl">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/volume-reports/jihad_nasr_kerman.png" alt="لوگوی جهاد نصر کرمان" loading="eager" decoding="sync" width={420} height={385} className="h-[385px] w-[420px] object-contain" />
              </div>
            </div>
          </div>
        </section>
      ),
    });

    const activeItems = visibleItems.filter((item) => holdingMap.has(item.key));
    const overviewStats = [
      { label: "شرکت‌های دارای عملکرد", value: toFa(companies.length) },
      { label: "کارگاه‌های دارای عملکرد", value: toFa(siteCount) },
      { label: "آیتم‌های دارای حجم", value: toFa(activeItems.length) },
      { label: "فایل‌های مأخذ", value: toFa(report.files.length) },
    ];
    const logoCols = companies.length > 6 ? 4 : 3;
    result.push({
      key: "overview",
      render: (page) => (
        <Slide title="نمای کلی گزارش" subtitle={period} page={page} period={period}>
          <div className="grid grid-cols-4 gap-5">
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
                  <p className="text-[22px] font-black leading-snug text-[#252850]">{company.name}</p>
                  <p className="mt-1 text-[15px] text-slate-500">{toFa(company.rows.size)} آیتم دارای حجم</p>
                </div>
              </div>
            ))}
          </div>
        </Slide>
      ),
    });

    const heroItems = HERO_KEYS.map((key) => visibleItems.find((item) => item.key === key)).filter((item): item is CatalogItem => Boolean(item && holdingMap.has(item.key)));
    const heroKeys = new Set(heroItems.map((item) => item.key));
    const otherItems = visibleItems.filter((item) => !heroKeys.has(item.key));
    result.push({
      key: "summary",
      render: (page) => (
        <Slide title="خلاصه عملکرد هولدینگ" subtitle={period} page={page} period={period}>
          {heroItems.length > 0 && (
            <div className="mb-5 grid h-[170px] shrink-0 grid-cols-4 gap-5">
              {heroItems.map((item) => <SummaryCard key={item.key} item={item} row={holdingMap.get(item.key)} hero />)}
            </div>
          )}
          <div className="grid min-h-0 flex-1 grid-cols-4 gap-4" style={{ gridAutoRows: "1fr" }}>
            {otherItems.map((item) => <SummaryCard key={item.key} item={item} row={holdingMap.get(item.key)} hero={false} />)}
          </div>
        </Slide>
      ),
    });

    const chartItems = visibleItems.filter((item) => companyRows.some((row) => row.item_key === item.key && Number.parseFloat(row.qty) > 0));
    const perSlide = companies.length > 6 ? 4 : 6;
    const chartPages = chunks(chartItems, perSlide);
    chartPages.forEach((itemSet, pageIndex) => {
      result.push({
        key: `charts-${pageIndex}`,
        render: (page) => (
          <Slide title="مقایسه عملکرد شرکت‌ها" subtitle={chartPages.length > 1 ? `بخش ${toFa(pageIndex + 1)} از ${toFa(chartPages.length)}` : period} page={page} period={period}>
            <div className={`grid min-h-0 flex-1 gap-5 ${perSlide === 6 ? "grid-cols-3" : "grid-cols-2"}`} style={{ gridAutoRows: "1fr" }}>
              {itemSet.map((item) => <ChartCard key={item.key} item={item} rows={companyRows} total={holdingMap.get(item.key)} />)}
            </div>
          </Slide>
        ),
      });
    });

    const tableMetrics = visibleItems.filter((item) => companyRows.some((row) => row.item_key === item.key));
    const metricGroups = balancedChunks(tableMetrics, MAX_METRIC_COLUMNS);
    const rowPages = chunks(companies, COMPANY_ROWS_PER_SLIDE);
    if (!rowPages.length) rowPages.push([]);
    metricGroups.forEach((metrics, metricIndex) => {
      rowPages.forEach((groupSet, rowIndex) => {
        const parts = metricGroups.length * rowPages.length;
        const partNo = metricIndex * rowPages.length + rowIndex + 1;
        result.push({
          key: `companies-${metricIndex}-${rowIndex}`,
          render: (page) => (
            <Slide title="کارنامه شرکت‌ها" subtitle={parts > 1 ? `بخش ${toFa(partNo)} از ${toFa(parts)}` : period} page={page} period={period}>
              <CompanyTable groups={groupSet} metrics={metrics} holdingMap={holdingMap} showTotal={rowIndex === rowPages.length - 1} />
            </Slide>
          ),
        });
      });
    });

    const companyNames = new Map(companyRows.map((row) => [row.company_id, row.company]));
    const fileRows = sources.map((source) => {
      const used = (source.sheet_log ?? []).filter((sheet) => sheet.used);
      const companyId = report.files.find((file) => file.filename === source.filename)?.company_id;
      return {
        id: source.id,
        filename: source.filename,
        company: (companyId && companyNames.get(companyId)) || source.suggested_company || "—",
        sheets: used.length,
        rows: used.reduce((sum, sheet) => sum + (sheet.rows_total ?? 0), 0),
        ok: source.status === "parsed",
      };
    });
    const sourcePages = chunks(fileRows, SOURCE_ROWS_PER_SLIDE);
    sourcePages.forEach((fileSet, pageIndex) => {
      result.push({
        key: `sources-${pageIndex}`,
        render: (page) => (
          <Slide title="اسناد مأخذ گزارش" subtitle={sourcePages.length > 1 ? `بخش ${toFa(pageIndex + 1)} از ${toFa(sourcePages.length)}` : period} page={page} period={period}>
            <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white">
              <table className="w-full table-fixed border-collapse text-[16px]">
                <thead className="bg-[#252850] text-white">
                  <tr>
                    <th className="px-5 py-3 text-start font-bold">فایل</th>
                    <th className="w-[240px] px-3 py-3 text-start font-bold">شرکت</th>
                    <th className="w-[130px] px-3 py-3 text-start font-bold">شیت‌ها</th>
                    <th className="w-[130px] px-3 py-3 text-start font-bold">ردیف‌ها</th>
                    <th className="w-[150px] px-3 py-3 text-start font-bold">وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {fileSet.map((file) => (
                    <tr key={file.id} className="h-[48px] border-t border-slate-100 odd:bg-white even:bg-slate-50">
                      <td className="truncate px-5 font-medium text-slate-800" dir="auto">{file.filename}</td>
                      <td className="truncate px-3 text-slate-600">{file.company}</td>
                      <td className="px-3 tabular-nums">{toFa(file.sheets)}</td>
                      <td className="px-3 tabular-nums">{toFa(file.rows)}</td>
                      <td className={`px-3 font-bold ${file.ok ? "text-emerald-700" : "text-red-700"}`}>{file.ok ? "پردازش شد" : "ناموفق"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Slide>
        ),
      });
    });

    result.push({
      key: "closing",
      render: () => (
        <section className="presentation-slide-print">
          <div className="slide-canvas flex flex-col items-center justify-center bg-[#252850] text-center text-white">
            <div className="absolute inset-y-0 start-0 w-4 bg-[#fed836]" />
            <div className="rounded-[32px] bg-white p-6 shadow-2xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/volume-reports/jihad_nasr_kerman.png" alt="لوگوی جهاد نصر کرمان" loading="eager" decoding="sync" width={240} height={220} className="h-[220px] w-[240px] object-contain" />
            </div>
            <h2 className="mt-10 text-[52px] font-black">{report.title}</h2>
            <div className="mt-6 h-1.5 w-28 rounded-full bg-[#fed836]" />
            <p className="mt-6 text-[22px] text-white/70">{period} · {formatJalaliDate(report.period_end)}</p>
          </div>
        </section>
      ),
    });
    return result;
  }, [catalog, companyRows, holding, report, siteRows, sources]);

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
          <h1 className="mt-1 text-base font-bold text-[#252850]">{report.title}</h1>
          <p className="mt-1 text-[11px] text-slate-500">{toFa(slides.length)} اسلاید</p>
        </div>
        <button type="button" onClick={() => void printWhenImagesReady()} className="rounded-xl bg-[#252850] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1e2246]">
          ذخیره PDF
        </button>
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
