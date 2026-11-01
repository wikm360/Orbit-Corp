"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/shared/components/ui/Modal";

import { runSoon } from "../lib/defer";
import { volumeReportApi } from "../api/volumeReportApi";
import { formatQuantity, formatQuantityWithUnit } from "../lib/format";
import { toFa } from "../lib/jalali";
import { EFFECT_LABELS } from "../lib/status";
import type { LineRow } from "../types";
import { ErrorBox, LoadingBlock, UnconfirmedMark } from "./common";

/** `itemKeys` has several entries for a rollup (asphalt total = binder + topka). */
export interface DrillTarget { title: string; itemKeys: string[]; siteIds: string[] | null }

/** Shows exactly which spreadsheet rows make up a number: file, sheet, row, description, original and converted quantity. */
export function DrillDown({ reportId, target, onClose }: { reportId: string; target: DrillTarget | null; onClose: () => void }) {
  const [lines, setLines] = useState<LineRow[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!target) return;
    let live = true;
    const sites: (string | undefined)[] = target.siteIds && target.siteIds.length ? target.siteIds : [undefined];
    const requests = target.itemKeys.flatMap((itemKey) => sites.map((siteId) => volumeReportApi.trace(reportId, itemKey, siteId)));
    const cancel = runSoon(() => {
      setLines(null);
      setError(null);
      Promise.all(requests)
        .then((parts) => { if (live) setLines(parts.flat()); })
        .catch((e) => { if (live) setError(e); });
    });
    return () => { live = false; cancel(); };
  }, [reportId, target]);

  return (
    <Modal isOpen={target !== null} onClose={onClose} title={target ? `ردیف‌های مؤثر: ${target.title}` : ""}>
      {error ? <ErrorBox error={error} /> : lines === null ? <LoadingBlock /> : lines.length === 0 ? <p className="py-6 text-center text-sm text-slate-500">ردیفی پیدا نشد.</p> : (
        <div className="max-h-[60vh] overflow-auto">
          <table className="w-full min-w-[640px] text-xs">
            <thead className="sticky top-0 bg-slate-50 text-slate-600">
              <tr>{["فایل", "شیت", "ردیف", "شرح", "مقدار اصلی", "مقدار گزارش"].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.line_id} className="border-t border-slate-100 align-top">
                  <td className="px-2 py-2">{l.filename}</td>
                  <td className="px-2 py-2">{l.sheet.trim()}</td>
                  <td className="px-2 py-2">{toFa(l.row_no)}</td>
                  <td className="px-2 py-2">{l.description} {l.unconfirmed && <UnconfirmedMark />}<div className="text-slate-400">{l.site}</div></td>
                  <td className="px-2 py-2 whitespace-nowrap">{formatQuantityWithUnit(l.quantity, l.unit_norm, 4)}</td>
                  <td className="px-2 py-2 whitespace-nowrap">{l.output_qty ? formatQuantityWithUnit(l.output_qty, l.output_unit, 2) : <span className="text-slate-400">{EFFECT_LABELS[l.effect]}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-slate-400">{formatQuantity(String(lines.length), 0)} ردیف</p>
        </div>
      )}
    </Modal>
  );
}
