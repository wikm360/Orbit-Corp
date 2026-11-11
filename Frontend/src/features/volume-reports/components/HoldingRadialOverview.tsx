"use client";

import { useMemo } from "react";

import { toFa } from "../lib/jalali";
import {
  SUMMARY_CANVAS_H,
  SUMMARY_CANVAS_W,
  computeOverviewRadarLayout,
  getCompanyColor,
  isExcludedFromOverviewRing,
  matchCompanyLogo,
} from "../lib/presentation";

export function CompanyMark({ name, size }: { name: string; size: number }) {
  const logo = matchCompanyLogo(name);
  if (logo) {
    // Plain <img>: next/image can defer or skip loading in print, which left the logos blank in the PDF.
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logo.src}
        alt={logo.label}
        loading="eager"
        decoding="sync"
        style={{ width: size * 1.25, height: size }}
        className="shrink-0 object-contain mix-blend-multiply"
      />
    );
  }
  return (
    <span
      style={{ width: size, height: size }}
      className="grid shrink-0 place-items-center rounded-xl bg-[#252850] text-sm font-bold text-[#fed836]"
    >
      {name.slice(0, 1)}
    </span>
  );
}

export interface HoldingCompanyOverviewItem {
  id: string;
  name: string;
  projectCount: number;
}

const RADAR_H = SUMMARY_CANVAS_H - 5;

/**
 * Slide 2 (`نمای کلی گزارش`) downward semi-circular Holding Arc/Radar view:
 * centers Mehvar Gostar Nasr as the mother card at top-center with subsidiary
 * company cards fanning downward along the semicircular radar orbit and top corner KPI cards.
 */
export function HoldingRadialOverview({
  companies,
  totalProjects,
}: {
  companies: HoldingCompanyOverviewItem[];
  totalProjects?: number;
}) {
  const layout = useMemo(() => {
    const inputs = companies
      .filter((company) => !isExcludedFromOverviewRing(company.name))
      .map((company, idx) => ({
        id: company.id,
        name: company.name,
        color: getCompanyColor(company.name, idx),
        projectCount: company.projectCount,
        sublabel: company.projectCount > 0 ? `${toFa(company.projectCount)} پروژه` : "عضو هلدینگ",
      }));
    return computeOverviewRadarLayout(inputs, SUMMARY_CANVAS_W, RADAR_H);
  }, [companies]);

  const resolvedProjectTotal =
    totalProjects ?? layout.nodes.reduce((sum, node) => sum + node.projectCount, 0);

  return (
    <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden" dir="ltr">
      <div
        className="relative shrink-0 overflow-hidden rounded-3xl border border-[#252850]/10 bg-white/60"
        style={{ width: layout.width, height: layout.height }}
      >
        {/* Radar Background Arcs & Radial Spokes SVG */}
        <svg
          width={layout.width}
          height={layout.height}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          className="pointer-events-none absolute inset-0 block"
        >
          {/* Ambient outer dashed orbit */}
          <path
            d={layout.outerArcPath}
            fill="none"
            stroke="#252850"
            strokeWidth={1.25}
            strokeDasharray="4 6"
            strokeOpacity={0.1}
          />
          {/* Primary subsidiary radar orbit */}
          <path
            d={layout.primaryArcPath}
            fill="none"
            stroke="#252850"
            strokeWidth={2}
            strokeDasharray="7 6"
            strokeOpacity={0.28}
          />
          {/* Inner technical orbit */}
          <path
            d={layout.innerArcPath}
            fill="none"
            stroke="#252850"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            strokeOpacity={0.14}
          />
          {/* Hub proximity gold dashed halo */}
          <path
            d={layout.hubArcPath}
            fill="none"
            stroke="#d97706"
            strokeWidth={1.5}
            strokeDasharray="4 5"
            strokeOpacity={0.32}
          />
          {/* Radial dashed spokes from mother card top edge to each subsidiary card */}
          {layout.nodes.map((node) => (
            <line
              key={`spoke-${node.id}`}
              x1={node.spokeX1}
              y1={node.spokeY1}
              x2={node.spokeX2}
              y2={node.spokeY2}
              stroke="#252850"
              strokeWidth={1.75}
              strokeDasharray="5 5"
              strokeOpacity={0.24}
            />
          ))}
        </svg>

        {/* Subsidiary Cards along the Semicircular Orbit */}
        {layout.nodes.map((node) => (
          <div
            key={`node-${node.id}`}
            style={{
              left: node.x,
              top: node.y,
              width: node.cardW,
              transform: "translate(-50%, -50%)",
            }}
            className="absolute z-10 overflow-hidden rounded-2xl border border-[#252850]/12 bg-white shadow-md"
          >
            <div className="h-1.5 w-full" style={{ backgroundColor: node.color }} />
            <div className="flex flex-col items-center px-3 py-2.5 text-center">
              <CompanyMark name={node.name} size={node.logoSizePx} />
              <p
                dir="rtl"
                className="mt-1.5 w-full font-black leading-[1.25] text-[#252850]"
                style={{ fontSize: `${node.nameFontPx}px` }}
              >
                {node.name}
              </p>
              <span
                dir="rtl"
                className={`mt-2 inline-block rounded-full border px-3 py-0.5 font-bold tabular-nums ${
                  node.projectCount > 0
                    ? "border-[#fed836]/70 bg-[#fed836]/25 text-[#252850]"
                    : "border-slate-200 bg-slate-100 text-slate-600"
                }`}
                style={{ fontSize: `${node.badgeFontPx}px` }}
              >
                {node.sublabel}
              </span>
            </div>
          </div>
        ))}

        {/* Mother Company Hub Card (Top Center) */}
        <div
          dir="rtl"
          className="absolute top-4 left-1/2 z-20 flex w-[310px] -translate-x-1/2 flex-col items-center overflow-hidden rounded-3xl border-2 border-[#252850]/20 bg-white shadow-xl"
        >
          <div className="h-2 w-full bg-[#fed836]" />
          <div className="flex flex-col items-center px-6 py-3.5 text-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/volume-reports/logo_mehvar.png"
              alt="لوگوی شرکت محور گستر نصر"
              loading="eager"
              decoding="sync"
              width={118}
              height={94}
              className="h-[88px] w-[114px] object-contain mix-blend-multiply"
            />
            <h3 className="mt-1 text-[18px] font-black leading-tight text-[#252850]">
              شرکت محور گستر نصر
            </h3>
            <span className="mt-0.5 text-[12px] font-semibold text-slate-500">
              هلدینگ تخصصی عمرانی
            </span>
          </div>
        </div>

        {/* Top-Right Corner KPI: Total Holding Projects */}
        <div
          dir="rtl"
          className="absolute top-5 right-7 z-20 flex min-w-[205px] items-center justify-between gap-4 overflow-hidden rounded-2xl border border-[#252850]/12 bg-white px-5 py-3.5 shadow-sm"
        >
          <div>
            <div className="text-[36px] font-black leading-none text-[#252850] tabular-nums">
              {toFa(resolvedProjectTotal)}
            </div>
            <div className="mt-1 text-[13px] font-bold text-slate-500">مجموع پروژه‌ها</div>
          </div>
          <span className="h-10 w-1.5 shrink-0 rounded-full bg-[#fed836]" />
        </div>

        {/* Top-Left Corner KPI: Active Subsidiaries Count */}
        <div
          dir="rtl"
          className="absolute top-5 left-7 z-20 flex min-w-[205px] items-center justify-between gap-4 overflow-hidden rounded-2xl border border-[#252850]/12 bg-white px-5 py-3.5 shadow-sm"
        >
          <span className="h-10 w-1.5 shrink-0 rounded-full bg-[#252850]" />
          <div className="text-end">
            <div className="text-[36px] font-black leading-none text-[#252850] tabular-nums">
              {toFa(layout.nodes.length)}
            </div>
            <div className="mt-1 text-[13px] font-bold text-slate-500">شرکت زیرمجموعه</div>
          </div>
        </div>
      </div>
    </div>
  );
}
