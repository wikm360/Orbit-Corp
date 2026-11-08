/** Pure builders for the ECharts options (kept separate from the component so they can be tested without a DOM). */

import { formatQuantity, toChartNumber, unitLabel } from "./format";
import type { CatalogItem, ResultRow } from "../types";

export interface ChartInput { rows: ResultRow[]; unit: string; scope: "holding" | "company" | "site"; catalog: CatalogItem[] }

/** Units that actually occur in the rows, in catalog order of first appearance. */
export function unitsPresent(rows: ResultRow[], catalog: CatalogItem[]): string[] {
  const order = new Map(catalog.map((c, i) => [c.key, i]));
  const sorted = [...rows].sort((a, b) => (order.get(a.item_key) ?? 99) - (order.get(b.item_key) ?? 99));
  return Array.from(new Set(sorted.map((r) => r.unit)));
}

const entityLabel = (r: ResultRow, scope: ChartInput["scope"]) => (scope === "site" ? `${r.site ?? ""}` : scope === "company" ? r.company ?? "" : "هلدینگ");

/** Bar chart for one unit: x = items with that unit; one series per company/site (a single series for the holding). */
export function buildBarOption({ rows, unit, scope, catalog }: ChartInput) {
  const items = catalog.filter((c) => rows.some((r) => r.item_key === c.key && r.unit === unit));
  const entities = Array.from(new Set(rows.filter((r) => r.unit === unit).map((r) => entityLabel(r, scope))));
  const decimals = new Map(catalog.map((c) => [c.key, c.decimals]));
  const series = entities.map((entity) => ({
    name: entity,
    type: "bar" as const,
    barMaxWidth: 36,
    data: items.map((item) => {
      const row = rows.find((r) => r.item_key === item.key && r.unit === unit && entityLabel(r, scope) === entity);
      return row ? toChartNumber(row.qty) : 0; // drawing only; labels below come from the exact strings
    }),
  }));
  return {
    animation: false,
    textStyle: { fontFamily: "inherit" },
    grid: { left: 16, right: 16, top: entities.length > 1 ? 48 : 24, bottom: 8, containLabel: true },
    legend: entities.length > 1 ? { top: 0, type: "scroll" as const } : undefined,
    tooltip: {
      trigger: "axis" as const,
      axisPointer: { type: "shadow" as const },
      valueFormatter: (value: number) => `${formatQuantity(String(value), decimals.get(items[0]?.key ?? "") ?? 2)} ${unitLabel(unit)}`,
    },
    xAxis: { type: "category" as const, data: items.map((i) => i.title_fa), axisLabel: { interval: 0, rotate: items.length > 5 ? 25 : 0 } },
    yAxis: { type: "value" as const, name: unitLabel(unit), axisLabel: { formatter: (v: number) => formatQuantity(String(v), 0) } },
    series,
    color: ["#0f766e", "#163b48", "#f59e0b", "#6366f1", "#e11d48", "#0891b2", "#84cc16"],
  };
}
