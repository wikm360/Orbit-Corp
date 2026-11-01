"use client";

import Link from "next/link";

import { unitLabel } from "../lib/format";
import { toFa } from "../lib/jalali";
import type { VolumeTableArtifact } from "../types";

/**
 * Chat rendering of the `volume_table` artifact: an RTL table whose last column is the unit of each row (units differ per
 * item, so they travel in `unit_by_row`). Figures arrive formatted by the server's catalog decimals as strings; we only
 * localise the digits (never re-compute).
 */
export function VolumeTableCard({ artifact }: { artifact: VolumeTableArtifact }) {
  const toPersian = (text: string) => toFa(text.replace(/,/g, "٬").replace(/\./g, "٫"));
  return (
    <figure dir="rtl" className="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-white text-start shadow-sm">
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
        <span className="text-sm font-semibold text-slate-800">{artifact.title}</span>
        <span className="flex items-center gap-3 text-xs text-slate-500">
          {artifact.period}
          <Link href={`/volume-reports/${artifact.report_id}`} className="text-teal-700 hover:underline">باز کردن گزارش</Link>
        </span>
      </figcaption>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[320px] text-xs">
          <thead className="bg-white text-slate-600">
            <tr>
              {artifact.columns.map((c) => <th key={c} scope="col" className="px-3 py-2 text-start font-medium">{c}</th>)}
              <th scope="col" className="px-3 py-2 text-start font-medium">واحد</th>
            </tr>
          </thead>
          <tbody>
            {artifact.rows.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                {row.map((cell, j) => {
                  const numeric = j === row.length - 1;
                  return <td key={j} className={numeric ? "whitespace-nowrap px-3 py-2 font-medium text-teal-800" : "px-3 py-2"}>{numeric ? toPersian(cell) : cell}</td>;
                })}
                <td className="whitespace-nowrap px-3 py-2 text-slate-500">{unitLabel(artifact.unit_by_row[i])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {artifact.notes.length > 0 && (
        <ul className="space-y-0.5 border-t border-slate-100 px-4 py-2 text-[11px] text-slate-500">
          {artifact.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}
    </figure>
  );
}
