"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatQuantity, formatQuantityWithUnit, unitLabel } from "../lib/format";
import { toFa } from "../lib/jalali";
import { EFFECT_LABELS } from "../lib/status";
import type { CatalogItem, LineRow, ResultRow, ResultScope, ResultsResponse } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock, UnconfirmedMark } from "./common";
import { DrillDown, type DrillTarget } from "./DrillDown";
import { ResultsChart } from "./ResultsChart";

const SCOPES: { id: ResultScope; label: string }[] = [{ id: "holding", label: "هولدینگ" }, { id: "company", label: "شرکت" }, { id: "site", label: "کارگاه" }];

function ProblemTable({ title, hint, lines, tone }: { title: string; hint: string; lines: LineRow[]; tone: "amber" | "red" | "slate" }) {
  const [open, setOpen] = useState(tone !== "slate");
  if (!lines.length) return null;
  const border = { amber: "border-amber-300 bg-amber-50", red: "border-red-300 bg-red-50", slate: "border-slate-200 bg-slate-50" }[tone];
  return (
    <section className={cn("rounded-2xl border p-4", border)} aria-label={title}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between text-start">
        <span className="text-sm font-semibold text-slate-800">{title} <span className="font-normal text-slate-500">({toFa(lines.length)})</span></span>
        <span className="text-xs text-slate-500">{open ? "بستن" : "نمایش"}</span>
      </button>
      <p className="mt-1 text-xs text-slate-600">{hint}</p>
      {open && (
        <div className="mt-3 overflow-x-auto rounded-xl bg-white">
          <table className="w-full min-w-[640px] text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>{["شرح (نام اصلی)", "کارگاه", "مقدار و واحد اصلی", "وضعیت", "منبع"].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.line_id} className="border-t border-slate-100 align-top">
                  <td className="px-2 py-2">{l.description}</td>
                  <td className="px-2 py-2">{l.site}</td>
                  <td className="px-2 py-2 whitespace-nowrap">{formatQuantityWithUnit(l.quantity, l.unit_norm, 4)}</td>
                  <td className="px-2 py-2">{EFFECT_LABELS[l.effect]}{l.note && l.effect === "no_conversion" ? ` (${l.note})` : ""}</td>
                  <td className="px-2 py-2 text-slate-500">{l.filename} · {l.sheet.trim()} · ردیف {toFa(l.row_no)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** Results at holding / company / site level, the item cards, a chart, drill-down, and the "other" and "problem" lists. */
export function ResultsView({ reportId, catalog, refreshKey }: { reportId: string; catalog: CatalogItem[]; refreshKey: number }) {
  const [scope, setScope] = useState<ResultScope>("holding");
  const [data, setData] = useState<ResultsResponse | null>(null);
  const [siteRows, setSiteRows] = useState<ResultRow[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [drill, setDrill] = useState<DrillTarget | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [main, sites] = await Promise.all([
        volumeReportApi.results(reportId, scope, scope === "holding" ? ["other", "problems", "nonphysical"] : []),
        scope === "company" ? volumeReportApi.results(reportId, "site") : Promise.resolve(null),
      ]);
      // "Other"/"problem" lists always come from the holding query so they stay visible at every level.
      if (scope !== "holding" && !data?.other) {
        const holding = await volumeReportApi.results(reportId, "holding", ["other", "problems", "nonphysical"]);
        setData({ ...main, other: holding.other, problems: holding.problems, nonphysical: holding.nonphysical });
      } else {
        setData(scope === "holding" ? main : { ...main, other: data?.other, problems: data?.problems, nonphysical: data?.nonphysical });
      }
      setSiteRows(sites?.rows ?? []);
    } catch (e) {
      setError(e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, scope]);

  useEffect(() => runSoon(() => { setData(null); void load(); }), [load, refreshKey]);

  const entities = useMemo(() => {
    if (!data || scope === "holding") return [];
    const map = new Map<string, { key: string; label: string; sub?: string; rows: Map<string, ResultRow> }>();
    for (const row of data.rows) {
      const key = scope === "site" ? row.site_id! : row.company_id!;
      const entity = map.get(key) ?? { key, label: scope === "site" ? row.site! : row.company!, sub: scope === "site" ? row.company ?? undefined : undefined, rows: new Map() };
      entity.rows.set(row.item_key, row);
      map.set(key, entity);
    }
    return Array.from(map.values());
  }, [data, scope]);

  function openDrill(itemKey: string, title: string, entityKey?: string) {
    const meta = catalog.find((c) => c.key === itemKey);
    const itemKeys = meta?.is_rollup && meta.rollup_of.length ? meta.rollup_of : [itemKey];
    let siteIds: string[] | null = null;
    if (scope === "site" && entityKey) siteIds = [entityKey];
    if (scope === "company" && entityKey) siteIds = Array.from(new Set(siteRows.filter((r) => r.company_id === entityKey && itemKeys.includes(r.item_key)).map((r) => r.site_id!)));
    setDrill({ title, itemKeys, siteIds });
  }

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  if (!data) return <LoadingBlock />;

  const visibleItems = catalog.filter((c) => !c.is_rollup || c.key === "asphalt_total");
  const holdingMap = new Map(data.rows.map((r) => [r.item_key, r]));

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="سطح نمایش" className="inline-flex rounded-xl bg-slate-100 p-1">
        {SCOPES.map((s) => (
          <button key={s.id} role="tab" type="button" aria-selected={scope === s.id} onClick={() => setScope(s.id)}
            className={cn("rounded-lg px-4 py-1.5 text-sm", scope === s.id ? "bg-white font-medium text-teal-800 shadow-sm" : "text-slate-600")}>{s.label}</button>
        ))}
      </div>

      {data.rows.length === 0 ? (
        <EmptyState title="هنوز عددی شمرده نشده است" hint="گروه‌های بدون تصمیم را در تب «بازبینی» تأیید کنید." />
      ) : scope === "holding" ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="کارت آیتم‌ها">
          {visibleItems.map((item) => {
            const row = holdingMap.get(item.key);
            return (
              <button key={item.key} type="button" disabled={!row} onClick={() => row && openDrill(item.key, item.title_fa)}
                className={cn("rounded-2xl border bg-white p-4 text-start shadow-sm transition", row ? "border-black/[0.06] hover:border-teal-400 hover:shadow" : "border-dashed border-slate-200 opacity-60", item.key === "asphalt_total" && "ring-1 ring-teal-100")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">{item.title_fa}</span>
                  {row?.has_unconfirmed && <UnconfirmedMark />}
                </div>
                <div className="mt-2 text-xl font-semibold text-teal-800">{row ? formatQuantityWithUnit(row.qty, row.unit, item.decimals) : "—"}</div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {item.key === "asphalt_total" ? "بیندر + توپکا" : row ? `${toFa(row.n_lines)} ردیف · واحد ${unitLabel(item.output_unit)}` : "بدون ردیف"}
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="sticky start-0 bg-slate-50 px-3 py-2 text-start font-medium">{scope === "site" ? "کارگاه" : "شرکت"}</th>
                {visibleItems.map((i) => <th key={i.key} className="px-2 py-2 text-start font-medium">{i.title_fa}<div className="font-normal text-slate-400">{unitLabel(i.output_unit)}</div></th>)}
              </tr>
            </thead>
            <tbody>
              {entities.map((entity) => (
                <tr key={entity.key} className="border-t border-slate-100">
                  <th scope="row" className="sticky start-0 bg-white px-3 py-2 text-start font-medium">{entity.label}{entity.sub && <div className="font-normal text-slate-400">{entity.sub}</div>}</th>
                  {visibleItems.map((i) => {
                    const cell = entity.rows.get(i.key);
                    return (
                      <td key={i.key} className="px-2 py-2 whitespace-nowrap">
                        {cell ? (
                          <button type="button" onClick={() => openDrill(i.key, `${i.title_fa} — ${entity.label}`, entity.key)} className="text-teal-800 underline-offset-2 hover:underline">
                            {formatQuantity(cell.qty, i.decimals)}{cell.has_unconfirmed && <span aria-label="تأییدنشده" title="شامل ردیف‌های تأییدنشده" className="ms-1 text-amber-600">*</span>}
                          </button>
                        ) : <span className="text-slate-300">—</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.rows.length > 0 && <Card title="نمودار"><ResultsChart rows={data.rows} scope={scope} catalog={catalog} /></Card>}

      <ProblemTable tone="red" title="مشکل‌دار" hint="این ردیف‌ها شمرده نشدند: واحدشان با آیتم نمی‌خواند یا پارامتر تبدیل لازم است. هیچ‌کدام بی‌صدا حذف نشده‌اند." lines={data.problems ?? []} />
      <ProblemTable tone="amber" title="سایر / نامنطبق" hint="ردیف‌هایی که در هیچ‌یک از آیتم‌های گزارش نگنجیدند یا هنوز تصمیمی برایشان گرفته نشده؛ با نام و واحد اصلی." lines={data.other ?? []} />
      <ProblemTable tone="slate" title="بدون حجم فیزیکی" hint="واحد مقطوع، سری، درصد، عدد یا ساعت ماشین؛ شمرده نمی‌شوند ولی دیده می‌شوند." lines={data.nonphysical ?? []} />

      <DrillDown reportId={reportId} target={drill} onClose={() => setDrill(null)} />
    </div>
  );
}
