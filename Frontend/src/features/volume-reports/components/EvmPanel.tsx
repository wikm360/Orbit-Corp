"use client";

import { useCallback, useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { billionInputToRial, formatBillionRial, formatRatio, rialToBillionInput } from "../lib/format";
import { toFa } from "../lib/jalali";
import type { EvmBasis, EvmCompany, EvmFigures, EvmProject, EvmResponse, PvMode } from "../types";
import { Button } from "@/shared/components/ui/Button";
import { Card, EmptyState, ErrorBox, LoadingBlock, fieldClass } from "./common";

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

function Row({ name, f, strong, note, pvCell, spi }: { name: string; f: EvmFigures; strong?: boolean; note?: string; pvCell?: React.ReactNode; spi?: string | null }) {
  return (
    <tr className={cn("border-t border-slate-100", strong && "bg-slate-50 font-semibold")} title={note}>
      <td className="px-3 py-2 text-slate-800">{name}</td>
      <td className="px-3 py-2 whitespace-nowrap">{pvCell ?? formatBillionRial(f.pv)}</td>
      <td className="px-3 py-2 whitespace-nowrap text-teal-800">{formatBillionRial(f.ev)}</td>
      <td className="px-3 py-2 whitespace-nowrap text-slate-500">{formatBillionRial(f.ev_net)}</td>
      <td className="px-3 py-2 whitespace-nowrap">{formatBillionRial(f.ac)}</td>
      <td className="px-3 py-2"><Ratio value={spi === undefined ? f.spi : spi} /></td>
      <td className="px-3 py-2"><Ratio value={f.cpi} /></td>
    </tr>
  );
}

const draftKey = (companyId: string, project: string | null) => `${companyId}|${project ?? ""}`;

/** SPI shown while typing: EV / the typed PV (display only; the saved value is recomputed by the server). */
function previewSpi(project: EvmProject, text: string | undefined): string | null | undefined {
  if (text === undefined) return undefined;
  const rial = billionInputToRial(text);
  if (!rial || !project.ev || Number(rial) <= 0) return null;
  return (Number(project.ev) / Number(rial)).toFixed(2);
}

function CompanyCard({ company, manual, draft, setDraft }: { company: EvmCompany; manual: boolean; draft: Record<string, string>; setDraft: (key: string, text: string) => void }) {
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
            {company.projects.map((p, i) => {
              const key = draftKey(company.company_id, p.project);
              const text = draft[key];
              const invalid = text !== undefined && billionInputToRial(text) === undefined;
              return (
                <Row
                  key={`${p.project}-${i}`} name={p.project ?? "—"} f={p} note={p.filename}
                  spi={manual ? previewSpi(p, text) : undefined}
                  pvCell={manual ? (
                    <input
                      inputMode="decimal" dir="ltr" value={text ?? ""} placeholder={rialToBillionInput(p.pv_auto ?? p.pv) || "—"}
                      aria-label={`PV ${p.project ?? ""} (میلیارد ریال)`} aria-invalid={invalid}
                      onChange={(e) => setDraft(key, e.target.value)}
                      className={cn(fieldClass, "w-32 py-1 text-xs", invalid && "border-red-400")}
                    />
                  ) : undefined}
                />
              );
            })}
            <Row name={`جمع ${company.company}`} f={company.total} strong note="جمع محاسبه‌شده از ردیف پروژه‌ها؛ SPI و CPI نسبت مجموع‌ها هستند" />
          </tbody>
        </table>
      </div>
      {!manual && company.projects.some((p) => p.pv_source && p.pv_source !== "file") && (
        <ul className="mt-2 space-y-0.5 text-[11px] text-indigo-700">
          {company.projects.filter((p) => p.pv_source && p.pv_source !== "file" && p.pv_source !== "manual").map((p, i) => (
            <li key={`${p.project}-${i}`}>
              PV «{p.project}»: {p.pv_source_label}{p.pv_share ? ` (${toFa(p.pv_share.replace("/", " از "))} روز ماه)` : ""}{p.pv_match === "fuzzy" ? " · تطبیق تقریبی نام پروژه؛ نام را کنترل کنید" : ""} — بقیه‌ی شاخص‌ها از فایل خود پروژه.
            </li>
          ))}
        </ul>
      )}
      {differs && reported && (
        <p className="mt-2 text-[11px] text-slate-500">
          جمع اعلام‌شده در خودِ فایل: SPI {formatRatio(reported.spi)} · CPI {formatRatio(reported.cpi)} · EV {formatBillionRial(reported.ev)} · AC {formatBillionRial(reported.ac)} (میلیارد ریال)
        </p>
      )}
    </Card>
  );
}

function BasisView({ data, manual, draft, setDraft }: { data: EvmBasis; manual: boolean; draft: Record<string, string>; setDraft: (key: string, text: string) => void }) {
  if (data.companies.length === 0) return <EmptyState title="جدول EVM در فایل‌ها پیدا نشد" hint="صفحه/شیت «گزارش مدیریت ارزش کسب شده (EVM)» باید در فایل باشد؛ اگر هست، گزارش را دوباره اجرا کنید." />;
  return (
    <div className="space-y-4">
      {data.holding && <Card><Summary total={data.holding} title={`مجموع همه‌ی شرکت‌ها — ${toFa(data.holding.projects)} پروژه`} /></Card>}
      {data.companies.map((c) => <CompanyCard key={c.company_id} company={c} manual={manual} draft={draft} setDraft={setDraft} />)}
      <p className="text-[11px] text-slate-400">ارقام به میلیارد ریال. EV: کارکرد · ev: کارکرد پس از کسر ضریب بالاسری · PV: کارکرد طبق برنامه · AC: هزینه‌ی واقعی · SPI = EV/PV · CPI = ev/AC. «—» یعنی در فایل داده‌ای برای محاسبه نبوده است.</p>
    </div>
  );
}

const MODES: { id: PvMode; label: string }[] = [{ id: "auto", label: "PV از پیش‌بینیِ هر پروژه" }, { id: "manual", label: "PV دستی" }];

/** PV / EV / AC / SPI / CPI per project and per company, as read from the EVM summary page of every file.
 *  PV comes from the forecasts automatically, or is typed per project ("دستی": blank = the file's own PV). */
export function EvmPanel({ reportId, refreshKey, editable }: { reportId: string; refreshKey: number; editable: boolean }) {
  const [data, setData] = useState<EvmResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [mode, setMode] = useState<PvMode>("auto");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [rereading, setRereading] = useState(false);

  const adopt = useCallback((next: EvmResponse) => {
    setData(next);
    setMode(next.pv_mode);
    const typed: Record<string, string> = {};
    for (const c of next.actual.companies) for (const p of c.projects) if (p.pv_manual) typed[draftKey(c.company_id, p.project)] = rialToBillionInput(p.pv_manual);
    setDraft(typed);
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try { adopt(await volumeReportApi.evm(reportId)); } catch (e) { setError(e); }
  }, [reportId, adopt]);
  useEffect(() => runSoon(() => { setData(null); void load(); }), [load, refreshKey]);

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  if (!data) return <LoadingBlock />;

  async function save() {
    if (!data) return;
    const values = [];
    for (const c of data.actual.companies) {
      for (const p of c.projects) {
        const rial = billionInputToRial(draft[draftKey(c.company_id, p.project)] ?? "");
        if (rial === undefined) { setSaveError("عدد وارد‌شده برای یک پروژه معتبر نیست."); return; }
        if (rial !== null && p.project) values.push({ company_id: c.company_id, project: p.project, pv: rial });
      }
    }
    setSaving(true);
    setSaveError(null);
    try { adopt(await volumeReportApi.setPv(reportId, mode, values)); } catch (e) { setSaveError(e instanceof Error ? e.message : "ذخیره ناموفق بود."); } finally { setSaving(false); }
  }

  async function reread() {
    setRereading(true);
    setSaveError(null);
    try { adopt(await volumeReportApi.reparseEvm(reportId)); } catch (e) { setSaveError(e instanceof Error ? e.message : "بازخوانی ناموفق بود."); } finally { setRereading(false); }
  }

  const manual = mode === "manual";
  const orphans = data.pv_manual_unmatched ?? [];
  return (
    <div className="space-y-4">
      {editable && data.actual.companies.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <div role="tablist" aria-label="منبع PV" className="inline-flex rounded-xl bg-slate-100 p-1">
            {MODES.map((m) => (
              <button key={m.id} role="tab" type="button" aria-selected={mode === m.id} onClick={() => setMode(m.id)}
                className={cn("rounded-lg px-4 py-1.5 text-sm", mode === m.id ? "bg-white font-medium text-teal-800 shadow-sm" : "text-slate-600")}>{m.label}</button>
            ))}
          </div>
          {manual && <span className="text-xs text-slate-500">PV هر پروژه را به میلیارد ریال بنویسید؛ عدد خاکستری پیشنهاد خودکار است و خانه‌ی خالی یعنی PV خودِ فایل پروژه.</span>}
          <Button size="sm" isLoading={saving} onClick={() => void save()} disabled={mode === data.pv_mode && !manual}>ذخیره</Button>
          <Button size="sm" variant="secondary" isLoading={rereading} onClick={() => void reread()}>بازخوانی از فایل‌ها</Button>
          {saveError && <span role="alert" className="text-xs text-red-600">{saveError}</span>}
        </div>
      )}
      {orphans.length > 0 && (
        <p role="status" className="rounded-xl bg-amber-50 px-4 py-2 text-xs text-amber-900">
          PVِ دستیِ این پروژه‌ها دیگر پروژه‌ی هم‌نامی در فایل‌ها ندارد و به‌کار نمی‌رود: {orphans.map((o) => o.project).join("، ")}
        </p>
      )}
      <BasisView data={data.actual} manual={manual && editable} draft={draft} setDraft={(key, text) => setDraft((d) => ({ ...d, [key]: text }))} />
    </div>
  );
}
