"use client";

import { useEffect, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatJalaliDateTime, toFa } from "../lib/jalali";
import { ROLE_LABELS, SITE_KIND_LABELS } from "../lib/status";
import { UNIT_LABELS } from "../lib/format";
import type { Company, Conversion, DecisionRow, LexiconEntry, SettingsItem, Site, SiteKind } from "../types";
import { Card, EmptyState, ErrorBox, fieldClass, LoadingBlock, Tabs } from "./common";

type Section = "items" | "lexicon" | "conversions" | "sites" | "decisions";

function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    const cancel = runSoon(() => {
      setError(null);
      fn().then((d) => { if (live) setData(d); }).catch((e) => { if (live) setError(e); });
    });
    return () => { live = false; cancel(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, reload: () => setTick((t) => t + 1) };
}

function omit<T>(record: Record<string, T>, key: string): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([k]) => k !== key));
}

function Notice({ message }: { message: string | null }) {
  return message ? <p role="status" className="rounded-xl bg-slate-100 px-3 py-2 text-xs text-slate-700">{message}</p> : null;
}

const UNIT_OPTIONS = Object.keys(UNIT_LABELS).filter((u) => !["lump", "series", "pct", "ea", "other", "hr"].includes(u));
const DIMENSION_BY_UNIT: Record<string, string> = { m3: "volume", m2: "area", m: "length", kg: "mass", t: "mass", m2cm: "area_thickness", m3km: "volume_distance" };

function ItemsSection({ editable }: { editable: boolean }) {
  const { data, error, reload } = useLoad(() => volumeReportApi.settings.items(), []);
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, Partial<SettingsItem>>>({});
  const [adding, setAdding] = useState({ key: "", title_fa: "", output_unit: "m3", decimals: 2 });

  async function save(item: SettingsItem) {
    const patch = { ...item, ...draft[item.key] };
    try {
      await volumeReportApi.settings.updateItem({ ...patch, dimension: DIMENSION_BY_UNIT[patch.output_unit] ?? patch.dimension });
      setDraft((d) => omit(d, item.key));
      setNotice("ذخیره شد؛ در اجرای بعدی اعمال می‌شود."); reload();
    } catch (e) { setNotice(friendlyErrorMessage(e, "ذخیره ناموفق بود.")); }
  }
  async function create() {
    try {
      await volumeReportApi.settings.createItem({
        key: adding.key, title_fa: adding.title_fa, description_fa: "", dimension: DIMENSION_BY_UNIT[adding.output_unit]!, output_unit: adding.output_unit,
        decimals: adding.decimals, sort_order: (data?.length ?? 0) + 1, is_rollup: false, rollup_of: [], mining_only: false, is_active: true,
      } as never);
      setAdding({ key: "", title_fa: "", output_unit: "m3", decimals: 2 }); setNotice("آیتم افزوده شد."); reload();
    } catch (e) { setNotice(friendlyErrorMessage(e, "افزودن ناموفق بود.")); }
  }

  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <LoadingBlock />;
  return (
    <div className="space-y-3">
      <Notice message={notice} />
      <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white">
        <table className="w-full min-w-[720px] text-xs">
          <thead className="bg-slate-50 text-slate-600"><tr>{["کلید", "عنوان", "واحد خروجی", "اعشار", "فعال", ""].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {data.map((item) => {
              const d = { ...item, ...draft[item.key] };
              const locked = !editable || item.is_rollup;
              return (
                <tr key={item.key} className="border-t border-slate-100">
                  <td className="px-2 py-2 font-mono text-[11px]" dir="ltr">{item.key}</td>
                  <td className="px-2 py-2"><input aria-label="عنوان" disabled={!editable} value={d.title_fa} onChange={(e) => setDraft((x) => ({ ...x, [item.key]: { ...x[item.key], title_fa: e.target.value } }))} className={fieldClass} /></td>
                  <td className="px-2 py-2">
                    <select aria-label="واحد خروجی" disabled={locked} value={d.output_unit} onChange={(e) => setDraft((x) => ({ ...x, [item.key]: { ...x[item.key], output_unit: e.target.value } }))} className={fieldClass}>
                      {UNIT_OPTIONS.filter((u) => DIMENSION_BY_UNIT[u] === item.dimension).map((u) => <option key={u} value={u}>{UNIT_LABELS[u]}</option>)}
                    </select>
                  </td>
                  <td className="px-2 py-2"><input aria-label="اعشار" type="number" min={0} max={6} disabled={!editable} value={d.decimals} onChange={(e) => setDraft((x) => ({ ...x, [item.key]: { ...x[item.key], decimals: Number(e.target.value) } }))} className={`${fieldClass} w-20`} /></td>
                  <td className="px-2 py-2"><input aria-label="فعال" type="checkbox" disabled={!editable} checked={d.is_active} onChange={(e) => setDraft((x) => ({ ...x, [item.key]: { ...x[item.key], is_active: e.target.checked } }))} className="accent-teal-600" /></td>
                  <td className="px-2 py-2">{editable && draft[item.key] && <Button size="sm" onClick={() => void save(item)}>ذخیره</Button>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {editable && (
        <Card title="افزودن آیتم">
          <div className="grid gap-2 md:grid-cols-5">
            <input aria-label="کلید انگلیسی" dir="ltr" placeholder="gabion" value={adding.key} onChange={(e) => setAdding({ ...adding, key: e.target.value })} className={fieldClass} />
            <input aria-label="عنوان فارسی" placeholder="گابیون" value={adding.title_fa} onChange={(e) => setAdding({ ...adding, title_fa: e.target.value })} className={fieldClass} />
            <select aria-label="واحد" value={adding.output_unit} onChange={(e) => setAdding({ ...adding, output_unit: e.target.value })} className={fieldClass}>{UNIT_OPTIONS.map((u) => <option key={u} value={u}>{UNIT_LABELS[u]}</option>)}</select>
            <input aria-label="اعشار" type="number" min={0} max={6} value={adding.decimals} onChange={(e) => setAdding({ ...adding, decimals: Number(e.target.value) })} className={fieldClass} />
            <Button onClick={() => void create()} disabled={!adding.key || !adding.title_fa}>افزودن</Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function LexiconSection({ editable }: { editable: boolean }) {
  const { data, error, reload } = useLoad(() => volumeReportApi.settings.lexicon(), []);
  const [notice, setNotice] = useState<string | null>(null);
  const [phrases, setPhrases] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState({ token: "", kind: "item_hint" as LexiconEntry["kind"], phrases: "" });
  const split = (text: string) => text.split(/[،,\n]/).map((p) => p.trim()).filter(Boolean);

  async function save(entry: LexiconEntry) {
    try { await volumeReportApi.settings.updateLexicon({ token: entry.token, kind: entry.kind, is_active: entry.is_active, phrases: split(phrases[entry.token] ?? entry.phrases.join("، ")) }); setNotice("ذخیره شد."); setPhrases((p) => omit(p, entry.token)); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "ذخیره ناموفق بود.")); }
  }
  async function add() {
    try { await volumeReportApi.settings.createLexicon({ token: adding.token, kind: adding.kind, is_active: true, phrases: split(adding.phrases) }); setAdding({ token: "", kind: "item_hint", phrases: "" }); setNotice("توکن افزوده شد."); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "افزودن ناموفق بود.")); }
  }
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <LoadingBlock />;
  const KINDS: Record<LexiconEntry["kind"], string> = { item_hint: "نشانه‌ی آیتم", role: "نقش", hard_exclusion: "حذف قطعی", noise: "نویز" };
  return (
    <div className="space-y-3">
      <Notice message={notice} />
      <p className="text-xs text-slate-500">عبارت‌ها را با «،» جدا کنید. «حذف قطعی» ردیف را بدون پرسش از گزارش خارج می‌کند؛ تغییرات از اجرای بعدی اعمال می‌شود.</p>
      <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white">
        <table className="w-full min-w-[640px] text-xs">
          <thead className="bg-slate-50 text-slate-600"><tr>{["توکن", "نوع", "عبارت‌ها", ""].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {data.map((e) => (
              <tr key={e.token} className="border-t border-slate-100">
                <td className="px-2 py-2 font-mono text-[11px]" dir="ltr">{e.token}</td>
                <td className="px-2 py-2 whitespace-nowrap">{KINDS[e.kind]}</td>
                <td className="px-2 py-2"><textarea aria-label={`عبارت‌های ${e.token}`} rows={2} disabled={!editable} value={phrases[e.token] ?? e.phrases.join("، ")} onChange={(ev) => setPhrases((p) => ({ ...p, [e.token]: ev.target.value }))} className={fieldClass} /></td>
                <td className="px-2 py-2">{editable && phrases[e.token] !== undefined && <Button size="sm" onClick={() => void save(e)}>ذخیره</Button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editable && (
        <Card title="افزودن توکن">
          <div className="grid gap-2 md:grid-cols-4">
            <input aria-label="توکن" dir="ltr" placeholder="GABION" value={adding.token} onChange={(e) => setAdding({ ...adding, token: e.target.value.toUpperCase() })} className={fieldClass} />
            <select aria-label="نوع" value={adding.kind} onChange={(e) => setAdding({ ...adding, kind: e.target.value as LexiconEntry["kind"] })} className={fieldClass}>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
            <input aria-label="عبارت‌ها" placeholder="گابیون، سبد سنگی" value={adding.phrases} onChange={(e) => setAdding({ ...adding, phrases: e.target.value })} className={fieldClass} />
            <Button onClick={() => void add()} disabled={!adding.token || !adding.phrases.trim()}>افزودن</Button>
          </div>
        </Card>
      )}
    </div>
  );
}

const PARAMS = [
  { key: "density_t_per_m3", label: "چگالی", unit: "t/m3" },
  { key: "thickness_m", label: "ضخامت", unit: "m" },
  { key: "cross_section_m2", label: "سطح مقطع", unit: "m2" },
] as const;

function ConversionsSection({ editable }: { editable: boolean }) {
  const { data, error, reload } = useLoad(async () => ({ conversions: await volumeReportApi.settings.conversions(), items: await volumeReportApi.settings.items() }), []);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({ key: "density_t_per_m3", item_key: "", value: "" });

  async function save() {
    const param = PARAMS.find((p) => p.key === form.key)!;
    const value = Number(form.value.replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d))).replace("٫", "."));
    if (!Number.isFinite(value) || value <= 0) { setNotice("مقدار باید عددی بزرگ‌تر از صفر باشد."); return; }
    try { await volumeReportApi.settings.saveConversion({ key: form.key, item_key: form.item_key || null, value, unit: param.unit }); setForm({ ...form, value: "" }); setNotice("ذخیره شد؛ با «محاسبه‌ی مجدد» در گزارش‌ها اعمال می‌شود."); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "ذخیره ناموفق بود.")); }
  }
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <LoadingBlock />;
  const title = (key: string | null) => (key ? data.items.find((i) => i.key === key)?.title_fa ?? key : "سراسری");
  return (
    <div className="space-y-3">
      <Notice message={notice} />
      <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white">
        <table className="w-full min-w-[480px] text-xs">
          <thead className="bg-slate-50 text-slate-600"><tr>{["پارامتر", "آیتم", "مقدار", "واحد"].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {data.conversions.length === 0 && <tr><td colSpan={4} className="px-2 py-6 text-center text-slate-400">پارامتری ثبت نشده است.</td></tr>}
            {data.conversions.map((c: Conversion) => (
              <tr key={c.id} className="border-t border-slate-100">
                <td className="px-2 py-2">{PARAMS.find((p) => p.key === c.key)?.label ?? c.key}</td>
                <td className="px-2 py-2">{title(c.item_key)}{c.site_id ? " (کارگاه خاص)" : ""}</td>
                <td className="px-2 py-2" dir="ltr">{toFa(Number(c.value))}</td>
                <td className="px-2 py-2" dir="ltr">{c.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editable && (
        <Card title="ثبت یا ویرایش پارامتر">
          <div className="grid gap-2 md:grid-cols-4">
            <select aria-label="پارامتر" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} className={fieldClass}>{PARAMS.map((p) => <option key={p.key} value={p.key}>{p.label} ({p.unit})</option>)}</select>
            <select aria-label="آیتم" value={form.item_key} onChange={(e) => setForm({ ...form, item_key: e.target.value })} className={fieldClass}>
              <option value="">سراسری</option>{data.items.filter((i) => !i.is_rollup).map((i) => <option key={i.key} value={i.key}>{i.title_fa}</option>)}
            </select>
            <input aria-label="مقدار" dir="ltr" inputMode="decimal" placeholder="2.35" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} className={fieldClass} />
            <Button onClick={() => void save()} disabled={!form.value}>ذخیره</Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function SitesSection({ editable }: { editable: boolean }) {
  const { data, error, reload } = useLoad(async () => ({ companies: await volumeReportApi.settings.companies(), sites: await volumeReportApi.settings.sites() }), []);
  const [notice, setNotice] = useState<string | null>(null);
  const [newCompany, setNewCompany] = useState("");

  async function setKind(site: Site, kind: SiteKind) {
    try { await volumeReportApi.settings.updateSite(site.id, { kind }); setNotice("نوع کارگاه تأیید شد؛ گزارش‌های قبلی را دوباره اجرا کنید."); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "ذخیره ناموفق بود.")); }
  }
  async function addCompany() {
    try { await volumeReportApi.settings.createCompany(newCompany.trim()); setNewCompany(""); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "افزودن ناموفق بود.")); }
  }
  async function toggleCompany(c: Company) {
    try { await volumeReportApi.settings.updateCompany(c.id, { name: c.name, aliases: c.aliases, is_active: !c.is_active }); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "ذخیره ناموفق بود.")); }
  }
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return <LoadingBlock />;
  return (
    <div className="space-y-4">
      <Notice message={notice} />
      <Card title="شرکت‌ها">
        <ul className="divide-y divide-slate-100 text-sm">
          {data.companies.map((c) => (
            <li key={c.id} className="flex items-center justify-between py-2">
              <span className={c.is_active ? "" : "text-slate-400 line-through"}>{c.name}</span>
              {editable && <Button size="sm" variant="ghost" onClick={() => void toggleCompany(c)}>{c.is_active ? "غیرفعال" : "فعال‌سازی"}</Button>}
            </li>
          ))}
          {data.companies.length === 0 && <li className="py-3 text-center text-xs text-slate-400">شرکتی ثبت نشده است.</li>}
        </ul>
        {editable && <div className="mt-3 flex gap-2"><input aria-label="نام شرکت" value={newCompany} onChange={(e) => setNewCompany(e.target.value)} placeholder="نام شرکت جدید" className={fieldClass} /><Button disabled={!newCompany.trim()} onClick={() => void addCompany()}>افزودن</Button></div>}
      </Card>
      <Card title="کارگاه‌ها و نوع آن‌ها">
        {data.sites.length === 0 ? <EmptyState title="کارگاهی هنوز شناسایی نشده است" hint="پس از اولین اجرا، کارگاه‌ها از روی عنوان شیت‌ها ساخته می‌شوند." /> : (
          <ul className="divide-y divide-slate-100 text-sm">
            {data.sites.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{s.name}<span className="ms-2 text-xs text-slate-400">{data.companies.find((c) => c.id === s.company_id)?.name}</span></span>
                <span className="flex items-center gap-2">
                  {!s.kind_confirmed && <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">تأییدنشده</span>}
                  <select aria-label={`نوع ${s.name}`} disabled={!editable} value={s.kind} onChange={(e) => void setKind(s, e.target.value as SiteKind)} className={`${fieldClass} w-32`}>
                    {(Object.keys(SITE_KIND_LABELS) as SiteKind[]).map((k) => <option key={k} value={k}>{SITE_KIND_LABELS[k]}</option>)}
                  </select>
                  {editable && !s.kind_confirmed && <Button size="sm" variant="secondary" onClick={() => void setKind(s, s.kind)}>تأیید</Button>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function DecisionsSection() {
  const [query, setQuery] = useState("");
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const { data, error, reload } = useLoad(() => volumeReportApi.settings.decisions(query || undefined, includeRevoked), [query, includeRevoked]);
  const [notice, setNotice] = useState<string | null>(null);
  const { data: items } = useLoad(() => volumeReportApi.catalog(), []);

  async function revoke(d: DecisionRow) {
    if (!window.confirm("این تصمیم لغو شود؟ از اجرای بعدی دیگر خودکار اعمال نمی‌شود.")) return;
    try { await volumeReportApi.settings.revokeDecision(d.id); setNotice("تصمیم لغو شد."); reload(); }
    catch (e) { setNotice(friendlyErrorMessage(e, "لغو ناموفق بود.")); }
  }
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  return (
    <div className="space-y-3">
      <Notice message={notice} />
      <div className="flex flex-wrap items-center gap-3">
        <input aria-label="جست‌وجو" placeholder="جست‌وجو در شرح…" value={query} onChange={(e) => setQuery(e.target.value)} className={`${fieldClass} max-w-xs`} />
        <label className="flex items-center gap-1.5 text-xs text-slate-600"><input type="checkbox" checked={includeRevoked} onChange={(e) => setIncludeRevoked(e.target.checked)} className="accent-teal-600" /> نمایش لغوشده‌ها</label>
      </div>
      {!data ? <LoadingBlock /> : data.length === 0 ? <EmptyState title="تصمیمی در حافظه نیست" hint="با تأیید «سراسری» در بازبینی، تصمیم‌ها اینجا جمع می‌شوند." /> : (
        <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white">
          <table className="w-full min-w-[760px] text-xs">
            <thead className="bg-slate-50 text-slate-600"><tr>{["شرح", "واحد", "کارگاه", "تصمیم", "نقش", "استفاده", "تأیید", ""].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id} className={`border-t border-slate-100 ${d.revoked_at ? "opacity-50" : ""}`}>
                  <td className="px-2 py-2">{d.description}</td>
                  <td className="px-2 py-2" dir="ltr">{d.unit}</td>
                  <td className="px-2 py-2">{SITE_KIND_LABELS[d.site_kind]}</td>
                  <td className="px-2 py-2">{d.item_key ? (items?.find((i) => i.key === d.item_key)?.title_fa ?? d.item_key) : d.disposition === "excluded" ? "حذف" : d.disposition}</td>
                  <td className="px-2 py-2">{ROLE_LABELS[d.role]}</td>
                  <td className="px-2 py-2">{toFa(d.hits)}</td>
                  <td className="px-2 py-2 whitespace-nowrap">{formatJalaliDateTime(d.confirmed_at)}</td>
                  <td className="px-2 py-2">{d.revoked_at ? <span className="text-slate-500">لغو شده</span> : <Button size="sm" variant="ghost" className="text-red-600" onClick={() => void revoke(d)}>لغو</Button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Global settings. Everyone may read the catalog/parameters/sites; writing (and the decision memory) is for admins and team leaders. */
export function SettingsPanel({ canEdit }: { canEdit: boolean }) {
  const [section, setSection] = useState<Section>("items");
  const tabs: { id: Section; label: string }[] = [
    { id: "items", label: "کاتالوگ آیتم‌ها" }, { id: "lexicon", label: "واژگان" }, { id: "conversions", label: "پارامترهای تبدیل" }, { id: "sites", label: "کارگاه‌ها و شرکت‌ها" },
    ...(canEdit ? [{ id: "decisions" as const, label: "حافظه‌ی تصمیم‌ها" }] : []),
  ];
  return (
    <div className="space-y-4">
      {!canEdit && <p className="rounded-xl bg-slate-100 px-4 py-2 text-xs text-slate-600">ویرایش تنظیمات فقط برای مدیر یا سرپرست تیم ممکن است؛ شما فقط می‌توانید آن‌ها را ببینید.</p>}
      <Tabs<Section> tabs={tabs} value={section} onChange={setSection} />
      {section === "items" && <ItemsSection editable={canEdit} />}
      {section === "lexicon" && <LexiconSection editable={canEdit} />}
      {section === "conversions" && <ConversionsSection editable={canEdit} />}
      {section === "sites" && <SitesSection editable={canEdit} />}
      {section === "decisions" && canEdit && <DecisionsSection />}
    </div>
  );
}
