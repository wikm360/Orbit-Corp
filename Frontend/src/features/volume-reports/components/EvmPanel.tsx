"use client";

import { useCallback, useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatBillionRial, formatRatio } from "../lib/format";
import { toFa } from "../lib/jalali";
import type { EvmBasis, EvmCompany, EvmFigures, EvmResponse } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock } from "./common";

type Basis = "actual" | "planned";
const BASES: { id: Basis; label: string }[] = [{ id: "actual", label: "واقعی دوره" }, { id: "planned", label: "پیش‌بینی دوره‌ی بعد" }];

/** ≥ 1 on or ahead of plan/budget, 0.9–1 watch, below 0.9 behind. */
function ratioTone(value: string | null): string {
  if (value === null) return "text-slate-300";
  const n = Number.parseFloat(value);
  return n >= 1 ? "text-emerald-700" : n >= 0.9 ? "text-amber-700" : "text-red-600";
}

function Ratio({ value }: { value: string | null }) {
  return <span className={cn("font-semibold", ratioTone(value))} dir="ltr">{formatRatio(value)}</span>;
}

function Stat({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3" title={hint}>
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="mt-1 text-base text-slate-800">{children}</p>
    </div>
  );
}

function Summary({ total, title }: { total: EvmFigures; title: string }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium text-slate-600">{title}</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Stat label="SPI" hint="شاخص عملکرد برنامه زمان‌بندی = EV / PV"><Ratio value={total.spi} /></Stat>
        <Stat label="CPI" hint="شاخص عملکرد هزینه = ev / AC"><Ratio value={total.cpi} /></Stat>
        <Stat label="EV (میلیارد ریال)" hint="کارکرد">{formatBillionRial(total.ev)}</Stat>
        <Stat label="PV (میلیارد ریال)" hint="کارکرد طبق برنامه‌ی کارگاه">{formatBillionRial(total.pv)}</Stat>
        <Stat label="AC (میلیارد ریال)" hint="هزینه‌ی واقعی">{formatBillionRial(total.ac)}</Stat>
      </div>
    </div>
  );
}

const COLUMNS = ["پروژه", "PV", "EV", "ev", "AC", "SPI", "CPI"];

function Row({ name, f, strong, note }: { name: string; f: EvmFigures; strong?: boolean; note?: string }) {
  return (
    <tr className={cn("border-t border-slate-100", strong && "bg-slate-50 font-semibold")} title={note}>
      <td className="px-3 py-2 text-slate-800">{name}</td>
      <td className="px-3 py-2 whitespace-nowrap">{formatBillionRial(f.pv)}</td>
      <td className="px-3 py-2 whitespace-nowrap text-teal-800">{formatBillionRial(f.ev)}</td>
      <td className="px-3 py-2 whitespace-nowrap text-slate-500">{formatBillionRial(f.ev_net)}</td>
      <td className="px-3 py-2 whitespace-nowrap">{formatBillionRial(f.ac)}</td>
      <td className="px-3 py-2"><Ratio value={f.spi} /></td>
      <td className="px-3 py-2"><Ratio value={f.cpi} /></td>
    </tr>
  );
}

function CompanyCard({ company }: { company: EvmCompany }) {
  const reported = company.reported_total;
  const differs = reported && (reported.spi !== company.total.spi || reported.cpi !== company.total.cpi);
  return (
    <Card title={`${company.company} — ${toFa(company.projects.length)} پروژه`}>
      <div className="overflow-x-auto rounded-xl border border-slate-100">
        <table className="w-full min-w-[620px] text-xs">
          <thead className="bg-slate-50 text-slate-600">
            <tr>{COLUMNS.map((h) => <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {company.projects.map((p, i) => <Row key={`${p.project}-${i}`} name={p.project ?? "—"} f={p} note={p.filename} />)}
            <Row name={`جمع ${company.company}`} f={company.total} strong note="جمع محاسبه‌شده از ردیف پروژه‌ها؛ SPI و CPI نسبت مجموع‌ها هستند" />
          </tbody>
        </table>
      </div>
      {differs && reported && (
        <p className="mt-2 text-[11px] text-slate-500">
          جمع اعلام‌شده در خودِ فایل: SPI {formatRatio(reported.spi)} · CPI {formatRatio(reported.cpi)} · EV {formatBillionRial(reported.ev)} · AC {formatBillionRial(reported.ac)} (میلیارد ریال)
        </p>
      )}
    </Card>
  );
}

function BasisView({ data }: { data: EvmBasis }) {
  if (data.companies.length === 0) return <EmptyState title="جدول EVM در فایل‌ها پیدا نشد" hint="صفحه/شیت «گزارش مدیریت ارزش کسب شده (EVM)» باید در فایل باشد؛ اگر هست، گزارش را دوباره اجرا کنید." />;
  return (
    <div className="space-y-4">
      {data.holding && <Card><Summary total={data.holding} title={`مجموع همه‌ی شرکت‌ها — ${toFa(data.holding.projects)} پروژه`} /></Card>}
      {data.companies.map((c) => <CompanyCard key={c.company_id} company={c} />)}
      <p className="text-[11px] text-slate-400">ارقام به میلیارد ریال. EV: کارکرد · ev: کارکرد پس از کسر ضریب بالاسری · PV: کارکرد طبق برنامه · AC: هزینه‌ی واقعی · SPI = EV/PV · CPI = ev/AC. «—» یعنی در فایل داده‌ای برای محاسبه نبوده است.</p>
    </div>
  );
}

/** PV / EV / AC / SPI / CPI per project and per company, as read from the EVM summary page of every file. */
export function EvmPanel({ reportId, refreshKey }: { reportId: string; refreshKey: number }) {
  const [basis, setBasis] = useState<Basis>("actual");
  const [data, setData] = useState<EvmResponse | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setData(await volumeReportApi.evm(reportId)); } catch (e) { setError(e); }
  }, [reportId]);
  useEffect(() => runSoon(() => { setData(null); void load(); }), [load, refreshKey]);

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  if (!data) return <LoadingBlock />;
  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="مبنا" className="inline-flex rounded-xl bg-slate-100 p-1">
        {BASES.map((b) => (
          <button key={b.id} role="tab" type="button" aria-selected={basis === b.id} onClick={() => setBasis(b.id)}
            className={cn("rounded-lg px-4 py-1.5 text-sm", basis === b.id ? "bg-white font-medium text-teal-800 shadow-sm" : "text-slate-600")}>{b.label}</button>
        ))}
      </div>
      <BasisView data={data[basis]} />
    </div>
  );
}
