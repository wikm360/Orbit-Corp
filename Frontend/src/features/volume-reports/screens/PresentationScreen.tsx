"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { ErrorBox, LoadingBlock } from "../components/common";
import { runSoon } from "../lib/defer";
import { formatJalaliDate, toFa } from "../lib/jalali";
import { formatQuantity, formatQuantityWithUnit } from "../lib/format";
import { EFFECT_LABELS } from "../lib/status";
import type { CatalogItem, LineRow, ReportDetail, ResultRow, ResultsResponse, SourceInfo } from "../types";

const NAVY = "#252850";
const READY_STATUSES = new Set(["awaiting_user", "needs_review", "ready", "published"]);
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

function groupRows(rows: ResultRow[], scope: "company" | "site") {
  const groups = new Map<string, { id: string; name: string; company?: string; rows: Map<string, ResultRow> }>();
  for (const row of rows) {
    const id = scope === "company" ? row.company_id : row.site_id;
    if (!id) continue;
    const group = groups.get(id) ?? {
      id,
      name: scope === "company" ? row.company ?? "بدون نام" : row.site ?? "بدون نام",
      company: scope === "site" ? row.company ?? undefined : undefined,
      rows: new Map<string, ResultRow>(),
    };
    group.rows.set(row.item_key, row);
    groups.set(id, group);
  }
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name, "fa"));
}

function matchLogo(name: string) {
  const normalized = name.toLocaleLowerCase("fa");
  return LOGOS.find((logo) => logo.match.some((part) => normalized.includes(part)));
}

function Slide({ title, eyebrow, children, className = "" }: { title: string; eyebrow?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`presentation-slide-print relative flex flex-col overflow-hidden rounded-3xl bg-[#f7f7f5] p-8 text-slate-900 shadow-xl md:p-12 ${className}`}>
      <div className="mb-6 flex shrink-0 items-end justify-between gap-6 border-b border-[#252850]/10 pb-4">
        <div>
          {eyebrow && <p className="mb-1 text-[11px] font-semibold tracking-widest text-[#9b7a05]">{eyebrow}</p>}
          <h2 className="text-2xl font-bold text-[#252850] md:text-3xl">{title}</h2>
        </div>
        <span className="h-1 w-16 shrink-0 rounded-full bg-[#fed836]" />
      </div>
      <div className="min-h-0 flex-1">{children}</div>
      <div className="mt-4 flex shrink-0 items-center justify-between border-t border-[#252850]/10 pt-3 text-[10px] text-slate-500">
        <span>گزارش مدیریتی احجام عملیات اجرایی</span>
        <span>جهاد نصر کرمان</span>
      </div>
    </section>
  );
}

function EmptyValue() {
  return <span className="text-slate-300">—</span>;
}

function MetricTable({
  groups,
  metrics,
  scope,
}: {
  groups: ReturnType<typeof groupRows>;
  metrics: CatalogItem[];
  scope: "company" | "site";
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white">
      <table className="w-full table-fixed border-collapse text-[11px]">
        <thead className="bg-[#252850] text-white">
          <tr>
            <th className="w-[22%] px-3 py-3 text-start font-semibold">{scope === "company" ? "شرکت تابعه" : "کارگاه / پروژه"}</th>
            {scope === "site" && <th className="w-[15%] px-2 py-3 text-start font-medium">شرکت مجری</th>}
            {metrics.map((item) => (
              <th key={item.key} className="px-2 py-3 text-start font-medium">
                {item.title_fa}<span className="mt-1 block text-[9px] text-white/60">{item.output_unit}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.id} className="border-t border-slate-100 odd:bg-white even:bg-slate-50/70">
              <th scope="row" className="px-3 py-3 text-start font-semibold text-slate-800">{group.name}</th>
              {scope === "site" && <td className="px-2 py-3 text-slate-500">{group.company ?? "—"}</td>}
              {metrics.map((item) => {
                const row = group.rows.get(item.key);
                return <td key={item.key} className="px-2 py-3 font-medium tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : <EmptyValue />}</td>;
              })}
            </tr>
          ))}
          {groups.length === 0 && <tr><td colSpan={metrics.length + (scope === "site" ? 2 : 1)} className="px-3 py-8 text-center text-slate-400">داده‌ای برای نمایش ثبت نشده است.</td></tr>}
        </tbody>
      </table>
      <p className="border-t border-slate-100 px-3 py-2 text-[9px] text-slate-400">مقادیر با واحد آیتم درج شده‌اند؛ خط تیره یعنی برای آن مورد حجمی ثبت نشده است.</p>
    </div>
  );
}

function ChartBars({ rows, item }: { rows: ResultRow[]; item: CatalogItem }) {
  const companies = groupRows(rows.filter((row) => row.item_key === item.key), "company");
  const maxValue = Math.max(0, ...companies.map((company) => Number.parseFloat(company.rows.get(item.key)?.qty ?? "0")));
  return (
    <div className="space-y-4 rounded-2xl border border-[#252850]/10 bg-white p-5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h3 className="font-bold text-[#252850]">{item.title_fa}</h3>
          <p className="mt-1 text-[10px] text-slate-500">مقایسه بر اساس مقدار ثبت‌شده · {item.output_unit}</p>
        </div>
        <span className="text-[10px] font-semibold text-slate-500">{item.output_unit}</span>
      </div>
      {companies.length ? companies.map((company, index) => {
        const row = company.rows.get(item.key);
        const value = Number.parseFloat(row?.qty ?? "0");
        const width = maxValue > 0 ? Math.max(value > 0 ? 1 : 0, (value / maxValue) * 100) : 0;
        return (
          <div key={company.id} className="grid grid-cols-[minmax(90px,150px)_1fr_auto] items-center gap-3 text-[10px]">
            <span className="truncate font-medium text-slate-700">{company.name}</span>
            <div className="h-3 overflow-hidden rounded-full bg-[#e7e8f0]">
              <div className="h-full rounded-full" style={{ width: `${width}%`, backgroundColor: index === 0 ? NAVY : "#8d90b5" }} />
            </div>
            <span className="min-w-[82px] text-end font-semibold tabular-nums text-[#252850]">{formatQuantityWithUnit(row?.qty, row?.unit, item.decimals)}</span>
          </div>
        );
      }) : <p className="py-6 text-center text-sm text-slate-400">برای این آیتم داده‌ای ثبت نشده است.</p>}
    </div>
  );
}

function sourceRows(sources: SourceInfo[]) {
  return sources.flatMap((source) => {
    const sheets = source.sheet_log ?? [];
    if (!sheets.length) return [{ filename: source.filename, sheet: "—", kind: source.status, used: false, rows: null as number | null, warnings: source.warnings.length }];
    return sheets.map((sheet, index) => ({
      filename: source.filename,
      sheet: sheet.sheet,
      kind: sheet.kind,
      used: sheet.used,
      rows: sheet.rows_total ?? null,
      warnings: source.warnings.filter((warning) => warning.sheet === sheet.sheet || (!warning.sheet && index === 0)).length,
    }));
  });
}

function lineCountLabel(rows: LineRow[]) {
  const perEffect = new Map<string, number>();
  for (const row of rows) perEffect.set(row.effect, (perEffect.get(row.effect) ?? 0) + 1);
  const capped = Array.from(perEffect.values()).some((count) => count >= 1000);
  return `${toFa(rows.length)}${capped ? "+" : ""}`;
}

export function PresentationScreen({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [holding, setHolding] = useState<ResultsResponse | null>(null);
  const [companyRows, setCompanyRows] = useState<ResultRow[]>([]);
  const [siteRows, setSiteRows] = useState<ResultRow[]>([]);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, items, holdingResult, companyResult, siteResult, sourceFiles] = await Promise.all([
        volumeReportApi.get(reportId),
        volumeReportApi.catalog(),
        volumeReportApi.results(reportId, "holding", ["other", "problems", "nonphysical"]),
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

  const slides = useMemo(() => {
    if (!report || !holding) return [];
    const allItems = catalog.filter((item) => !item.is_rollup || item.key === "asphalt_total");
    const itemByKey = new Map(catalog.map((item) => [item.key, item]));
    const holdingMap = new Map(holding.rows.map((row) => [row.item_key, row]));
    const companies = groupRows(companyRows, "company");
    const sites = groupRows(siteRows, "site");
    const totalWarnings = sources.reduce((sum, source) => sum + source.warnings.length, 0);
    const unconfirmedItems = holding.rows.filter((row) => row.has_unconfirmed).length;
    const qualityLines = [
      { title: "نیازمند تبدیل / ناسازگاری واحد", rows: holding.problems ?? [] },
      { title: "سایر / نامنطبق / نیازمند تصمیم", rows: holding.other ?? [] },
      { title: "فاقد حجم فیزیکی", rows: holding.nonphysical ?? [] },
    ];
    const sourceSheetRows = sourceRows(sources);
    if (!sourceSheetRows.length) {
      sourceSheetRows.push({ filename: "—", sheet: "—", kind: "—", used: false, rows: null, warnings: 0 });
    }
    const result: ReactNode[] = [];

    result.push(
      <section key="cover" className="presentation-slide-print relative flex overflow-hidden rounded-3xl bg-[#252850] text-white shadow-xl">
        <div className="absolute inset-y-0 start-0 w-3 bg-[#fed836]" />
        <div className="flex min-w-0 flex-1 flex-col justify-center p-10 md:p-16">
          <p className="mb-5 text-sm font-semibold tracking-wide text-[#fed836]">گزارش مدیریتی دوره‌ای</p>
          <h1 className="max-w-3xl text-4xl font-black leading-[1.5] md:text-6xl">{report.title}</h1>
          <p className="mt-4 text-lg text-white/75">عملکرد تجمیعی احجام عملیات اجرایی</p>
          <div className="mt-10 flex flex-wrap gap-x-8 gap-y-3 text-sm text-white/75">
            <span>{report.period_label}</span>
            <span>{formatJalaliDate(report.period_start)} تا {formatJalaliDate(report.period_end)}</span>
            <span>نسخه {toFa(report.version)}</span>
          </div>
          <div className="mt-12 h-1 w-28 rounded-full bg-[#fed836]" />
          <p className="mt-4 text-xs text-white/55">تهیه‌شده برای شرکت جهاد نصر کرمان</p>
        </div>
        <div className="hidden w-[34%] items-center justify-center p-10 md:flex">
          <div className="rounded-[2rem] bg-white p-6 shadow-2xl">
            <Image src="/volume-reports/jihad_nasr_kerman.png" alt="لوگوی جهاد نصر کرمان" width={300} height={275} unoptimized loading="eager" className="h-64 w-64 object-contain" />
          </div>
        </div>
        <div className="absolute bottom-8 end-10 text-[10px] text-white/50">Orbit Corp · Volume Report</div>
      </section>,
    );

    const preferredKeys = ["excavation", "fill", "asphalt_total", "concrete"];
    const headlineItems = preferredKeys
      .map((key) => itemByKey.get(key))
      .filter((item): item is CatalogItem => Boolean(item && holdingMap.has(item.key)))
      .slice(0, 4);
    const overviewCards = [
      { label: "شرکت‌های دارای عملکرد", value: toFa(companies.length), note: "بر اساس نتایج ثبت‌شده" },
      { label: "کارگاه‌های دارای عملکرد", value: toFa(sites.length), note: "کارگاه‌های دارای حداقل یک آیتم" },
      { label: "فایل‌های مأخذ", value: toFa(report.files.length), note: "فایل‌های پیوست‌شده به گزارش" },
      { label: "آیتم‌های کاتالوگ", value: toFa(allItems.length), note: "آیتم‌های فعال در ساختار گزارش" },
    ];

    result.push(
      <Slide key="overview" title="گستره گزارش در یک نگاه" eyebrow="نمای کلی">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {overviewCards.map((card) => (
            <div key={card.label} className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-[#252850]/5">
              <p className="text-[11px] text-slate-500">{card.label}</p>
              <p className="mt-2 text-3xl font-black tabular-nums text-[#252850]">{card.value}</p>
              <p className="mt-1 text-[9px] text-slate-400">{card.note}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 grid grid-cols-3 gap-3">
          {companies.slice(0, 6).map((company) => {
            const logo = matchLogo(company.name);
            return (
              <div key={company.id} className="flex min-h-20 items-center gap-3 rounded-xl border border-slate-100 bg-white px-3 py-2">
                {logo ? <Image src={logo.src} alt={logo.label} width={52} height={42} unoptimized loading="eager" className="h-10 w-12 shrink-0 object-contain" /> : <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#252850] text-sm font-bold text-[#fed836]">{company.name.slice(0, 1)}</span>}
                <span className="text-xs font-semibold text-slate-700">{company.name}</span>
              </div>
            );
          })}
        </div>
        {companies.length > 6 && <p className="mt-2 text-[10px] text-slate-400">و {toFa(companies.length - 6)} شرکت دیگر در جداول تفصیلی آمده‌اند.</p>}
      </Slide>,
    );

    result.push(
      <Slide key="summary" title="خلاصه مدیریتی دوره" eyebrow={report.period_label}>
        <div className="grid grid-cols-2 gap-4">
          {headlineItems.length ? headlineItems.map((item) => {
            const row = holdingMap.get(item.key)!;
            return (
              <div key={item.key} className="rounded-2xl bg-[#252850] p-5 text-white">
                <p className="text-xs text-white/70">{item.title_fa}</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-[#fed836]">{formatQuantityWithUnit(row.qty, row.unit, item.decimals)}</p>
                <p className="mt-2 text-[10px] text-white/60">{toFa(row.n_lines)} ردیف تشکیل‌دهنده{row.has_unconfirmed ? " · شامل موارد تأییدنشده" : ""}</p>
              </div>
            );
          }) : <div className="col-span-2 rounded-2xl bg-white p-6 text-sm text-slate-500">برای این دوره هنوز مقدار قابل‌جمع‌بندی ثبت نشده است.</div>}
        </div>
        <div className="mt-5 rounded-2xl border-s-4 border-[#fed836] bg-white px-5 py-4">
          <p className="text-xs font-bold text-[#252850]">وضعیت گزارش</p>
          <p className="mt-1 text-sm leading-7 text-slate-600">
            {report.status === "published" ? "این نسخه منتشر شده و برای ارائه آماده است." : "این گزارش هنوز منتشر نشده است؛ موارد نیازمند بازبینی در بخش کنترل کیفیت مشخص شده‌اند."}
            {" "}تعداد شرکت‌های دارای عملکرد {toFa(companies.length)} و تعداد کارگاه‌های دارای عملکرد {toFa(sites.length)} است.
          </p>
        </div>
      </Slide>,
    );

    const chartItems = preferredKeys
      .map((key) => itemByKey.get(key))
      .filter((item): item is CatalogItem => Boolean(item && companyRows.some((row) => row.item_key === item.key)))
      .slice(0, 3);
    if (chartItems.length) {
      result.push(
        <Slide key="charts" title="مقایسه عملکرد شرکت‌ها" eyebrow="تحلیل بصری">
          <div className="grid grid-cols-1 gap-4">
            {chartItems.map((item) => <ChartBars key={item.key} rows={companyRows} item={item} />)}
          </div>
          <p className="mt-3 text-[9px] text-slate-400">طول میله‌ها برای مقایسه نسبی شرکت‌ها در همان آیتم است؛ اعداد دقیق در جدول‌ها درج شده‌اند.</p>
        </Slide>,
      );
    }

    const companyMetrics = chunks(allItems, 5);
    for (let metricIndex = 0; metricIndex < companyMetrics.length; metricIndex += 1) {
      const metricSet = companyMetrics[metricIndex]!;
      for (let entityIndex = 0; entityIndex < Math.max(1, Math.ceil(companies.length / 9)); entityIndex += 1) {
        const companySet = companies.slice(entityIndex * 9, entityIndex * 9 + 9);
        result.push(
          <Slide
            key={`companies-${metricIndex}-${entityIndex}`}
            title={companyMetrics.length > 1 ? `کارنامه شرکت‌ها · ${metricSet[0]?.title_fa ?? ""} تا ${metricSet[metricSet.length - 1]?.title_fa ?? ""}` : "کارنامه تفکیکی شرکت‌ها"}
            eyebrow="جدول مقایسه‌ای"
          >
            <MetricTable groups={companySet} metrics={metricSet} scope="company" />
          </Slide>,
        );
      }
    }

    const siteMetrics = chunks(allItems, 5);
    for (let metricIndex = 0; metricIndex < siteMetrics.length; metricIndex += 1) {
      const metricSet = siteMetrics[metricIndex]!;
      for (let entityIndex = 0; entityIndex < Math.max(1, Math.ceil(sites.length / 9)); entityIndex += 1) {
        const siteSet = sites.slice(entityIndex * 9, entityIndex * 9 + 9);
        result.push(
          <Slide
            key={`sites-${metricIndex}-${entityIndex}`}
            title={siteMetrics.length > 1 ? `کارنامه کارگاه‌ها · ${metricSet[0]?.title_fa ?? ""} تا ${metricSet[metricSet.length - 1]?.title_fa ?? ""}` : "کارنامه تفکیکی کارگاه‌ها"}
            eyebrow="جزئیات پروژه"
          >
            <MetricTable groups={siteSet} metrics={metricSet} scope="site" />
          </Slide>,
        );
      }
    }

    for (const [pageIndex, itemSet] of chunks(allItems, 8).entries()) {
      result.push(
        <Slide key={`items-${pageIndex}`} title="ریز احجام به تفکیک آیتم" eyebrow="جمع هولدینگ">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {itemSet.map((item) => {
              const row = holdingMap.get(item.key);
              return (
                <div key={item.key} className="min-h-28 rounded-2xl border border-[#252850]/10 bg-white p-4">
                  <p className="text-xs font-semibold text-slate-700">{item.title_fa}</p>
                  <p className="mt-3 text-xl font-black tabular-nums text-[#252850]">{row ? formatQuantity(row.qty, item.decimals) : "—"}</p>
                  <div className="mt-1 flex justify-between text-[9px] text-slate-400">
                    <span>{item.output_unit}</span>
                    <span>{row ? `${toFa(row.n_lines)} ردیف` : "بدون ردیف"}</span>
                  </div>
                  {row?.has_unconfirmed && <p className="mt-2 text-[9px] font-medium text-amber-700">دارای مقدار تأییدنشده</p>}
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-[9px] text-slate-400">مقادیر از نتایج تجمیعی گزارش خوانده شده‌اند؛ آیتم «آسفالت (جمع)» جمع بیندر و توپکا است.</p>
        </Slide>,
      );
    }

    result.push(
      <Slide key="quality" title="کنترل کیفیت و شفافیت داده" eyebrow="هیچ موردی بی‌صدا حذف نمی‌شود">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { title: "آیتم‌های دارای ردیف تأییدنشده", value: toFa(unconfirmedItems), color: "text-amber-700" },
            { title: "هشدارهای فایل‌های مأخذ", value: toFa(totalWarnings), color: "text-[#252850]" },
            { title: "فایل‌های پردازش‌شده", value: toFa(sources.filter((source) => source.status === "parsed").length), color: "text-emerald-700" },
            { title: "موارد مانع انتشار", value: toFa(report.issues.length), color: "text-red-700" },
          ].map((card) => (
            <div key={card.title} className="rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-[10px] text-slate-500">{card.title}</p>
              <p className={`mt-2 text-3xl font-black tabular-nums ${card.color}`}>{card.value}</p>
            </div>
          ))}
        </div>
        {report.issues.length > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <h3 className="text-xs font-bold text-amber-900">موارد نیازمند رسیدگی</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {report.issues.map((issue) => <span key={issue.code} className="rounded-lg bg-white px-3 py-2 text-[10px] text-amber-900">{issue.code} · {toFa(issue.count)}</span>)}
            </div>
          </div>
        )}
        <div className="mt-4 space-y-2">
          {qualityLines.map((category) => (
            <div key={category.title} className="flex items-center justify-between rounded-xl bg-white px-4 py-3">
              <span className="text-xs font-medium text-slate-700">{category.title}</span>
              <span className="text-sm font-bold tabular-nums text-[#252850]">{lineCountLabel(category.rows)}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[9px] leading-5 text-slate-500">ردیف‌های خارج از محاسبه و موارد نیازمند بررسی در اسلایدهای بعدی با شرح و مأخذ نمایش داده شده‌اند. عدد دارای «+» یعنی سقف نمایش API برای همان گروه رسیده است.</p>
      </Slide>,
    );

    for (const category of qualityLines) {
      const rowPages = chunks(category.rows, 7);
      for (const [pageIndex, lineSet] of rowPages.entries()) {
        result.push(
          <Slide key={`quality-lines-${category.title}-${pageIndex}`} title={category.title} eyebrow={`جزئیات کنترل کیفیت · ${lineCountLabel(category.rows)} ردیف`}>
            <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white">
              <table className="w-full table-fixed border-collapse text-[9px]">
                <thead className="bg-[#252850] text-white">
                  <tr>
                    <th className="w-[25%] px-2 py-2 text-start">شرح ردیف</th>
                    <th className="w-[16%] px-2 py-2 text-start">شرکت / کارگاه</th>
                    <th className="w-[14%] px-2 py-2 text-start">مقدار اصلی</th>
                    <th className="w-[32%] px-2 py-2 text-start">فایل · شیت · ردیف</th>
                    <th className="px-2 py-2 text-start">وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {lineSet.map((line) => (
                    <tr key={line.line_id} className="border-t border-slate-100 align-top">
                      <td className="px-2 py-2 leading-5">{line.description || "—"}</td>
                      <td className="px-2 py-2">{line.company} · {line.site}</td>
                      <td className="px-2 py-2 whitespace-nowrap">{formatQuantityWithUnit(line.quantity, line.unit_norm, 4)}</td>
                      <td className="px-2 py-2 text-slate-500">{line.filename} · {line.sheet.trim()} · {toFa(line.row_no)}</td>
                      <td className="px-2 py-2">{EFFECT_LABELS[line.effect]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {lineCountLabel(category.rows).endsWith("+") && pageIndex === rowPages.length - 1 && <p className="mt-2 text-[9px] text-amber-700">برای دست‌کم یکی از وضعیت‌های این گروه، نمایش به سقف ۱٬۰۰۰ ردیف API رسیده است؛ شمار اعلام‌شده حداقل است.</p>}
          </Slide>,
        );
      }
    }

    for (const [pageIndex, sheetSet] of chunks(sourceSheetRows, 8).entries()) {
      result.push(
        <Slide key={`sources-${pageIndex}`} title="شناسنامه اسناد و شیت‌های مأخذ" eyebrow="ردیابی منبع داده">
          <div className="overflow-hidden rounded-2xl border border-[#252850]/10 bg-white">
            <table className="w-full table-fixed border-collapse text-[10px]">
              <thead className="bg-[#252850] text-white">
                <tr>
                  <th className="w-[34%] px-3 py-3 text-start">فایل ورودی</th>
                  <th className="w-[23%] px-3 py-3 text-start">شیت</th>
                  <th className="w-[13%] px-2 py-3 text-start">نوع</th>
                  <th className="w-[11%] px-2 py-3 text-start">ردیف‌ها</th>
                  <th className="w-[9%] px-2 py-3 text-start">هشدار</th>
                  <th className="px-2 py-3 text-start">وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {sheetSet.map((entry, index) => (
                  <tr key={`${entry.filename}-${entry.sheet}-${index}`} className="border-t border-slate-100 odd:bg-white even:bg-slate-50/70">
                    <td className="break-all px-3 py-3 font-medium text-slate-700">{entry.filename}</td>
                    <td className="px-3 py-3">{entry.sheet}</td>
                    <td className="px-2 py-3">{entry.kind}</td>
                    <td className="px-2 py-3 tabular-nums">{entry.rows === null ? "—" : toFa(entry.rows)}</td>
                    <td className="px-2 py-3 tabular-nums">{toFa(entry.warnings)}</td>
                    <td className={`px-2 py-3 font-semibold ${entry.used ? "text-emerald-700" : "text-slate-400"}`}>{entry.used ? "استفاده شد" : "صرفاً ثبت شد"}</td>
                  </tr>
                ))}
                {sheetSet.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-400">فایلی برای این گزارش ثبت نشده است.</td></tr>}
              </tbody>
            </table>
          </div>
        </Slide>,
      );
    }

    result.push(
      <section key="closing" className="presentation-slide-print relative flex flex-col justify-center overflow-hidden rounded-3xl bg-[#252850] p-12 text-white shadow-xl md:p-16">
        <div className="absolute inset-y-0 start-0 w-3 bg-[#fed836]" />
        <p className="text-sm font-semibold tracking-widest text-[#fed836]">جمع‌بندی</p>
        <h2 className="mt-4 max-w-4xl text-4xl font-black leading-[1.6] md:text-5xl">گزارش احجام دوره‌ی {report.period_label}</h2>
        <p className="mt-5 max-w-3xl text-base leading-8 text-white/75">
          جمع‌بندی مقادیر، مقایسه شرکت‌ها و کارگاه‌ها، ریز آیتم‌ها و وضعیت مأخذ در اسلایدهای پیشین ارائه شد.
          {report.status === "published" ? " این نسخه منتشر شده است." : " وضعیت انتشار و موارد باز گزارش در بخش کنترل کیفیت آمده است."}
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <span className="rounded-xl bg-white/10 px-4 py-3 text-sm">شرکت‌های دارای عملکرد: {toFa(companies.length)}</span>
          <span className="rounded-xl bg-white/10 px-4 py-3 text-sm">کارگاه‌های دارای عملکرد: {toFa(sites.length)}</span>
          <span className="rounded-xl bg-white/10 px-4 py-3 text-sm">فایل‌های مأخذ: {toFa(report.files.length)}</span>
        </div>
        <div className="absolute bottom-8 end-10 text-xs text-white/50">شرکت جهاد نصر کرمان · {formatJalaliDate(report.period_end)}</div>
      </section>,
    );
    return result;
  }, [catalog, companyRows, holding, report, siteRows, sources]);

  if (error) return <div className="p-6"><ErrorBox error={error} onRetry={() => void load()} /></div>;
  if (!report || !holding) return <LoadingBlock />;

  if (!READY_STATUSES.has(report.status)) {
    return (
      <div className="mx-auto max-w-2xl p-8 text-center">
        <p className="text-lg font-semibold text-slate-800">ارائه هنوز آماده نیست</p>
        <p className="mt-2 text-sm text-slate-500">ابتدا پردازش گزارش را کامل کنید؛ سپس می‌توانید نسخه‌ی PDF را بسازید.</p>
        <Link href={`/volume-reports/${reportId}`} className="mt-5 inline-flex rounded-xl bg-[#252850] px-4 py-2 text-sm text-white">بازگشت به گزارش</Link>
      </div>
    );
  }

  return (
    <div className="presentation-page min-h-full bg-[#edf0f3] p-3 md:p-6" dir="rtl" lang="fa">
      <div className="no-print mx-auto mb-4 flex max-w-[1600px] flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm">
        <div>
          <Link href={`/volume-reports/${reportId}`} className="text-xs text-slate-500 hover:text-[#252850]">بازگشت به گزارش</Link>
          <h1 className="mt-1 text-base font-bold text-[#252850]">پیش‌نمایش پرزنتیشن · {report.title}</h1>
          <p className="mt-1 text-[11px] text-slate-500">{toFa(slides.length)} اسلاید · نسبت ۱۶:۹ · برای خروجی، مقصد چاپگر را روی Save as PDF بگذارید.</p>
        </div>
        <button type="button" onClick={() => window.print()} className="rounded-xl bg-[#252850] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1e2246]">
          ذخیره PDF
        </button>
      </div>
      <div className="print-only-container mx-auto flex max-w-[1600px] flex-col gap-5">
        {slides.map((slide, index) => (
          <div key={index} className="relative">
            {slide}
            <span className="no-print absolute bottom-3 start-4 rounded-md bg-black/50 px-2 py-1 text-[10px] text-white">{toFa(index + 1)} / {toFa(slides.length)}</span>
            <span className="print-slide-number absolute bottom-4 start-8 hidden text-[9px] text-slate-400">{toFa(index + 1)} / {toFa(slides.length)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
