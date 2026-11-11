"use client";

import { formatBillionRial, formatRatio } from "../lib/format";
import { toFa } from "../lib/jalali";
import type { EvmCompany, EvmFigures } from "../types";

/** Per-company page of the management presentation, built on the company TOTAL only (so the layout never depends on how many
 *  projects the company has): figure tiles, SPI / CPI dials, PV · EV · ev · AC columns, an SPI×CPI map where every project is
 *  a dot, and a one-line reading. Palette = the deck's navy / gold on warm paper. */

const NAVY = "#252850";
const GOLD = "#fed836";
const GOLD_DARK = "#9b7a05";
const GOOD = "#2f7d5b";
const WATCH = "#b7791f";
const BAD = "#b4443c";
const MUTED = "#64748b";
const TRACK = "#e8e6df";

const num = (value: string | null | undefined): number | null => {
  if (value === null || value === undefined) return null;
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : null;
};

const toneColor = (value: number | null): string => (value === null ? "#cbd5e1" : value >= 1 ? GOOD : value >= 0.9 ? WATCH : BAD);

/** Whole-rial difference a − b as a decimal string (integer arithmetic, no floats); null when an operand is missing. */
function diffRial(a: string | null, b: string | null): string | null {
  if (a === null || b === null) return null;
  const left = /^(-?)(\d+)/.exec(a.trim());
  const right = /^(-?)(\d+)/.exec(b.trim());
  if (!left || !right) return null;
  const signed = (m: RegExpExecArray) => (m[1] ? -BigInt(m[2]!) : BigInt(m[2]!));
  return (signed(left) - signed(right)).toString();
}

function signedBillion(value: string | null): string {
  if (value === null) return "—";
  const text = formatBillionRial(value);
  return value.startsWith("-") || text === "—" || /^[۰٫]+$/.test(text) ? text : `+${text}`;
}

function Card({ title, note, children, className = "" }: { title: string; note?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`flex min-h-0 min-w-0 flex-col rounded-2xl border border-[#252850]/10 bg-white px-6 py-4 shadow-sm ${className}`}>
      <h3 className="mb-1 flex items-center gap-2.5 text-[18px] font-black text-[#252850]">
        <span className="h-5 w-1.5 rounded-full" style={{ backgroundColor: GOLD }} />
        {title}
        {note && <span className="ms-auto text-[12.5px] font-medium text-slate-400">{note}</span>}
      </h3>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </section>
  );
}

// ---- dials --------------------------------------------------------------------------------------------------------

const DIAL_MAX = 2;
function polar(cx: number, cy: number, r: number, ratio: number): [number, number] {
  const angle = Math.PI * (1 - Math.min(Math.max(ratio, 0), 1));
  return [cx + r * Math.cos(angle), cy - r * Math.sin(angle)];
}
function arc(cx: number, cy: number, r: number, from: number, to: number): string {
  const [x1, y1] = polar(cx, cy, r, from);
  const [x2, y2] = polar(cx, cy, r, to);
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

function Dial({ label, caption, value }: { label: string; caption: string; value: string | null }) {
  const v = num(value);
  const cx = 150, cy = 134, r = 108;
  const [tx1, ty1] = polar(cx, cy, r - 18, 1 / DIAL_MAX);
  const [tx2, ty2] = polar(cx, cy, r + 14, 1 / DIAL_MAX);
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center" dir="ltr">
      <svg viewBox="0 0 300 176" className="min-h-0 w-full flex-1" role="img" aria-label={`${label} ${value ?? "نامشخص"}`}>
        <path d={arc(cx, cy, r, 0, 1)} fill="none" stroke={TRACK} strokeWidth={20} strokeLinecap="round" />
        {v !== null && v > 0 && <path d={arc(cx, cy, r, 0, v / DIAL_MAX)} fill="none" stroke={toneColor(v)} strokeWidth={20} strokeLinecap="round" />}
        <line x1={tx1} y1={ty1} x2={tx2} y2={ty2} stroke={NAVY} strokeWidth={2.5} />
        <text x={tx2} y={ty2 - 7} textAnchor="middle" fontSize={13} fontWeight={700} fill={NAVY}>{toFa(1)}</text>
        <text x={cx} y={cy - 22} textAnchor="middle" fontSize={56} fontWeight={800} fill={v === null ? "#cbd5e1" : NAVY}>{formatRatio(value)}</text>
        <text x={cx} y={cy + 8} textAnchor="middle" fontSize={17} fontWeight={800} fill={GOLD_DARK}>{label}</text>
        <text x={cx - r} y={cy + 30} textAnchor="middle" fontSize={13} fill={MUTED}>{toFa(0)}</text>
        <text x={cx + r} y={cy + 30} textAnchor="middle" fontSize={13} fill={MUTED}>{toFa(2)}</text>
      </svg>
      <p className="text-[13.5px] font-medium text-slate-500" dir="rtl">{caption}</p>
    </div>
  );
}

// ---- columns: PV · EV · ev · AC -----------------------------------------------------------------------------------

function Columns({ t }: { t: EvmFigures }) {
  const series = [
    { label: "PV", sub: "برنامه", value: t.pv, color: "#c9ccdf" },
    { label: "EV", sub: "کارکرد", value: t.ev, color: NAVY },
    { label: "ev", sub: "کارکرد بدون بالاسری", value: t.ev_net, color: "#6c70a3" },
    { label: "AC", sub: "هزینه‌ی واقعی", value: t.ac, color: GOLD },
  ];
  const max = Math.max(1, ...series.map((s) => num(s.value) ?? 0));
  const W = 560, H = 520, base = 440, top = 50, slot = W / series.length, bw = 84;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="min-h-0 w-full flex-1" style={{ direction: "ltr" }} role="img" aria-label="PV EV ev AC">
      {[0.25, 0.5, 0.75, 1].map((g) => <line key={g} x1={10} x2={W - 10} y1={base - (base - top) * g} y2={base - (base - top) * g} stroke="#efede6" strokeWidth={1} />)}
      <line x1={10} x2={W - 10} y1={base} y2={base} stroke="#cfcbbf" strokeWidth={1.5} />
      {series.map((s, i) => {
        const v = num(s.value);
        const h = v === null ? 0 : Math.max(4, (v / max) * (base - top));
        const x = slot * i + (slot - bw) / 2;
        return (
          <g key={s.label}>
            {v !== null && <rect x={x} y={base - h} width={bw} height={h} rx={8} fill={s.color} />}
            <text x={x + bw / 2} y={(v === null ? base : base - h) - 10} textAnchor="middle" fontSize={22} fontWeight={800} fill={NAVY}>{formatBillionRial(s.value)}</text>
            <text x={x + bw / 2} y={base + 28} textAnchor="middle" fontSize={20} fontWeight={800} fill={NAVY}>{s.label}</text>
            <text x={x + bw / 2} y={base + 50} textAnchor="middle" fontSize={13} fill={MUTED}>{s.sub}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ---- SPI × CPI map ------------------------------------------------------------------------------------------------

function RatioMap({ company }: { company: EvmCompany }) {
  const W = 560, H = 520, L = 52, R = 14, T = 12, B = 44;
  const MAX = 2;
  const x = (v: number) => L + (Math.min(Math.max(v, 0), MAX) / MAX) * (W - L - R);
  const y = (v: number) => H - B - (Math.min(Math.max(v, 0), MAX) / MAX) * (H - T - B);
  const dots = company.projects.map((p) => ({ spi: num(p.spi), cpi: num(p.cpi) })).filter((d): d is { spi: number; cpi: number } => d.spi !== null && d.cpi !== null);
  const spi = num(company.total.spi), cpi = num(company.total.cpi);
  const mx = x(1), my = y(1);
  const quad = (qx: number, qy: number, qw: number, qh: number, fill: string) => <rect x={qx} y={qy} width={qw} height={qh} fill={fill} />;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="min-h-0 w-full flex-1" style={{ direction: "ltr" }} role="img" aria-label="SPI CPI">
      {quad(mx, T, W - R - mx, my - T, "rgba(47,125,91,0.12)")}
      {quad(L, T, mx - L, my - T, "rgba(183,121,31,0.10)")}
      {quad(mx, my, W - R - mx, H - B - my, "rgba(183,121,31,0.10)")}
      {quad(L, my, mx - L, H - B - my, "rgba(180,68,60,0.11)")}
      <line x1={mx} x2={mx} y1={T} y2={H - B} stroke={NAVY} strokeWidth={1.5} strokeDasharray="5 5" />
      <line x1={L} x2={W - R} y1={my} y2={my} stroke={NAVY} strokeWidth={1.5} strokeDasharray="5 5" />
      <rect x={L} y={T} width={W - L - R} height={H - T - B} fill="none" stroke="#d8d4c7" />
      <text x={(mx + W - R) / 2} y={T + 28} textAnchor="middle" fontSize={15} fontWeight={800} fill={GOOD}>پیشرو و کم‌هزینه</text>
      <text x={(L + mx) / 2} y={T + 28} textAnchor="middle" fontSize={15} fontWeight={800} fill={WATCH}>پیشرفت کند</text>
      <text x={(mx + W - R) / 2} y={H - B - 14} textAnchor="middle" fontSize={15} fontWeight={800} fill={WATCH}>هزینه‌ی بالا</text>
      <text x={(L + mx) / 2} y={H - B - 14} textAnchor="middle" fontSize={15} fontWeight={800} fill={BAD}>نیازمند توجه</text>
      {[0, 1, 2].map((tick) => (
        <g key={tick}>
          <text x={x(tick)} y={H - B + 20} textAnchor="middle" fontSize={13} fill={MUTED}>{toFa(tick)}</text>
          <text x={L - 10} y={y(tick) + 4} textAnchor="end" fontSize={13} fill={MUTED}>{toFa(tick)}</text>
        </g>
      ))}
      <text x={(L + W - R) / 2} y={H - 8} textAnchor="middle" fontSize={15} fontWeight={800} fill={NAVY}>SPI · برنامه زمانی ←</text>
      <text transform={`translate(14 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize={15} fontWeight={800} fill={NAVY}>CPI · هزینه ←</text>
      {dots.map((d, i) => <circle key={i} cx={x(d.spi)} cy={y(d.cpi)} r={9} fill={GOLD} fillOpacity={0.85} stroke={GOLD_DARK} strokeWidth={1.5} />)}
      {spi !== null && cpi !== null && (
        <g>
          <circle cx={x(spi)} cy={y(cpi)} r={17} fill={NAVY} stroke="#fff" strokeWidth={3} />
          <text x={x(spi)} y={y(cpi) + 5} textAnchor="middle" fontSize={13} fontWeight={800} fill="#fff">جمع</text>
        </g>
      )}
    </svg>
  );
}

// ---- reading ------------------------------------------------------------------------------------------------------

function verdict(spi: number | null, cpi: number | null): { title: string; text: string; color: string } | null {
  if (spi === null && cpi === null) return null;
  const ahead = spi !== null && spi >= 0.95;
  const cheap = cpi !== null && cpi >= 0.95;
  if (spi !== null && cpi !== null) {
    if (ahead && cheap) return { title: "عملکرد مطلوب", text: "پیشرفت مطابق برنامه و هزینه‌ها در محدوده‌ی کارکرد است.", color: GOOD };
    if (ahead) return { title: "پیشرفت خوب، هزینه‌ی بالا", text: "برنامه‌ی زمانی رعایت شده، اما هزینه‌ی واقعی از کارکرد بیشتر است.", color: WATCH };
    if (cheap) return { title: "هزینه تحت کنترل، پیشرفت کند", text: "هزینه‌ها مهار شده، اما کارکرد از برنامه عقب است.", color: WATCH };
    return { title: "نیازمند توجه", text: "کارکرد از برنامه عقب است و هزینه‌ی واقعی از کارکرد بیشتر شده است.", color: BAD };
  }
  return cpi !== null
    ? { title: cheap ? "هزینه تحت کنترل" : "فشار هزینه", text: "برنامه‌ی زمانی در فایل ثبت نشده؛ فقط شاخص هزینه قابل ارزیابی است.", color: cheap ? GOOD : BAD }
    : { title: ahead ? "مطابق برنامه" : "عقب از برنامه", text: "هزینه‌ی واقعی در فایل ثبت نشده؛ فقط شاخص زمانی قابل ارزیابی است.", color: ahead ? GOOD : BAD };
}

function Deviation({ label, value }: { label: string; value: string | null }) {
  const color = value === null ? MUTED : value.startsWith("-") ? BAD : GOOD;
  return (
    <div className="px-7">
      <p className="text-[13px] text-slate-500">{label}</p>
      <p className="text-[28px] font-black tabular-nums leading-tight" style={{ color }} dir="ltr">{signedBillion(value)}</p>
    </div>
  );
}

// ---- slide body ---------------------------------------------------------------------------------------------------

export function CompanyProfileBody({ evm }: { evm: EvmCompany | null }) {
  if (!evm) {
    return (
      <Card title="شاخص‌های ارزش کسب‌شده (EVM)" className="flex-1">
        <p className="m-auto text-[18px] text-slate-400">جدول EVM این شرکت در فایل‌های دوره پیدا نشد.</p>
      </Card>
    );
  }
  const t = evm.total;
  const read = verdict(num(t.spi), num(t.cpi));
  const sv = diffRial(t.ev, t.pv);
  const cv = diffRial(t.ev_net, t.ac);
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="grid min-h-0 flex-1 gap-4" style={{ gridTemplateColumns: "340px 1fr 1fr" }}>
        <Card title="شاخص‌های عملکرد">
          <div className="flex min-h-0 flex-1 flex-col justify-evenly">
            <Dial label="SPI" caption="برنامه زمانی · EV ÷ PV" value={t.spi} />
            <Dial label="CPI" caption="هزینه · ev ÷ AC" value={t.cpi} />
          </div>
        </Card>
        <Card title="برنامه، کارکرد و هزینه" note="میلیارد ریال">
          <Columns t={t} />
        </Card>
        <Card title="نقشه‌ی عملکرد" note={`هر نقطه‌ی طلایی یک پروژه · ${toFa(evm.projects.length)} پروژه`}>
          <RatioMap company={evm} />
        </Card>
      </div>

      <div className="flex shrink-0 items-center rounded-2xl border border-[#252850]/10 bg-white px-6 py-3.5 shadow-sm" style={{ borderInlineStart: `6px solid ${read?.color ?? "#cbd5e1"}` }}>
        <div className="min-w-0 flex-1">
          <p className="text-[21px] font-black" style={{ color: read?.color ?? NAVY }}>{read?.title ?? "خوانش مدیریتی"}</p>
          <p className="mt-0.5 text-[14px] leading-relaxed text-slate-600">{read?.text ?? "داده‌ی کافی برای ارزیابی در فایل ثبت نشده است."}</p>
        </div>
        <div className="flex shrink-0 divide-x divide-slate-200 divide-x-reverse">
          <Deviation label="انحراف زمانی (EV − PV)" value={sv} />
          <Deviation label="انحراف هزینه (ev − AC)" value={cv} />
        </div>
      </div>
    </div>
  );
}
