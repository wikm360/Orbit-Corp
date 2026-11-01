"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { buildBarOption, unitsPresent } from "../lib/chart";
import { unitLabel } from "../lib/format";
import type { CatalogItem, ResultRow, ResultScope } from "../types";

/** ECharts is loaded on demand (and tree-shaken to the bar chart) so it never weighs on the other screens. */
export function ResultsChart({ rows, scope, catalog }: { rows: ResultRow[]; scope: ResultScope; catalog: CatalogItem[] }) {
  const units = useMemo(() => unitsPresent(rows.filter((r) => r.item_key !== "asphalt_total"), catalog), [rows, catalog]);
  const [unit, setUnit] = useState<string | null>(null);
  const activeUnit = unit && units.includes(unit) ? unit : units[0] ?? null;
  const element = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!activeUnit || !element.current) return;
    let disposed = false;
    let chart: { setOption: (o: unknown, notMerge?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
    const host = element.current;
    const observer = new ResizeObserver(() => chart?.resize());
    (async () => {
      try {
        const [core, charts, components, renderers] = await Promise.all([
          import("echarts/core"), import("echarts/charts"), import("echarts/components"), import("echarts/renderers"),
        ]);
        if (disposed) return;
        core.use([charts.BarChart, components.GridComponent, components.TooltipComponent, components.LegendComponent, renderers.CanvasRenderer]);
        chart = core.init(host, undefined, { renderer: "canvas" });
        chart.setOption(buildBarOption({ rows, unit: activeUnit, scope, catalog }), true);
        observer.observe(host);
      } catch {
        if (!disposed) setFailed(true);
      }
    })();
    return () => { disposed = true; observer.disconnect(); chart?.dispose(); };
  }, [rows, scope, catalog, activeUnit]);

  if (!units.length) return null;
  return (
    <div>
      <div role="tablist" aria-label="واحد نمودار" className="mb-2 flex flex-wrap gap-1.5">
        {units.map((u) => (
          <button key={u} role="tab" type="button" aria-selected={u === activeUnit} onClick={() => setUnit(u)}
            className={cn("rounded-lg border px-2.5 py-1 text-xs", u === activeUnit ? "border-teal-500 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-600 hover:bg-slate-50")}>
            {unitLabel(u)}
          </button>
        ))}
      </div>
      {failed ? <p className="py-6 text-center text-xs text-slate-500">نمودار بارگذاری نشد؛ جدول بالا کامل است.</p> : <div ref={element} role="img" aria-label="نمودار حجم عملیات" className="h-72 w-full" />}
    </div>
  );
}
