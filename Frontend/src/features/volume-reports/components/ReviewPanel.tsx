"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatQuantityWithUnit } from "../lib/format";
import { toFa } from "../lib/jalali";
import { byImpact, formatSourceLocationText } from "../lib/questions";
import {
  buildBulkPayload, confidenceLabel, draftFromGroup, pendingGroups, type RowDraft,
} from "../lib/review";
import { ROLE_LABELS, SITE_KIND_LABELS } from "../lib/status";
import type { AnswerPayload, CatalogItem, Question, RememberScope, ReviewGroup, Role } from "../types";
import { Card, EmptyState, ErrorBox, fieldClass, LoadingBlock } from "./common";
import { QuestionCard } from "./QuestionCard";

interface Props {
  reportId: string;
  catalog: CatalogItem[];
  editable: boolean;
  /** Called after any change that can alter results/status (answer, skip, confirm). */
  onChanged: () => void;
  /** Starts the next agent pass (POST /continue). */
  onContinue: () => Promise<void>;
  canContinue: boolean;
}

export function ReviewPanel({ reportId, catalog, editable, onChanged, onContinue, canContinue }: Props) {
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [groups, setGroups] = useState<ReviewGroup[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [answered, setAnswered] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, RowDraft>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [q, g] = await Promise.all([volumeReportApi.questions(reportId, "open"), volumeReportApi.groups(reportId, "all")]);
      setQuestions(byImpact(q));
      setGroups(g);
    } catch (e) {
      setError(e);
    }
  }, [reportId]);
  useEffect(() => runSoon(() => void load()), [load]);

  const groupMap = useMemo(() => new Map((groups ?? []).map((g) => [g.group_key, g])), [groups]);
  const pending = useMemo(() => pendingGroups(groups ?? []), [groups]);
  const items = catalog.filter((c) => !c.is_rollup);

  async function afterChange(message?: string) {
    setNotice(message ?? null);
    await load();
    onChanged();
  }

  async function answer(question: Question, payload: AnswerPayload) {
    setBusyId(question.id);
    try {
      await volumeReportApi.answer(reportId, question.id, payload);
      setAnswered((n) => n + 1);
      await afterChange("پاسخ ثبت شد.");
    } catch (e) {
      setNotice(friendlyErrorMessage(e, "ثبت پاسخ ناموفق بود."));
    } finally {
      setBusyId(null);
    }
  }

  async function skip(question: Question) {
    setBusyId(question.id);
    try {
      await volumeReportApi.skip(reportId, question.id);
      setAnswered((n) => n + 1);
      await afterChange("سؤال رد شد؛ ردیف‌هایش در «سایر/نامنطبق» دیده می‌شوند.");
    } catch (e) {
      setNotice(friendlyErrorMessage(e, "رد کردن ناموفق بود."));
    } finally {
      setBusyId(null);
    }
  }

  const draftOf = (g: ReviewGroup) => drafts[g.group_key] ?? draftFromGroup(g);
  const setDraft = (g: ReviewGroup, patch: Partial<RowDraft>) => setDrafts((d) => ({ ...d, [g.group_key]: { ...draftOf(g), ...patch } }));
  const toggle = (key: string) => setSelected((s) => { const next = new Set(s); if (next.has(key)) next.delete(key); else next.add(key); return next; });

  async function confirmSelected(keys: Set<string>) {
    const { items: payload, skipped } = buildBulkPayload(pending, drafts, keys);
    if (!payload.length) { setNotice("برای ردیف‌های انتخابی هنوز آیتم یا «سایر» مشخص نشده است."); return; }
    setBulkBusy(true);
    try {
      await volumeReportApi.confirm(reportId, payload);
      setSelected(new Set());
      await afterChange(`${toFa(payload.length)} گروه تأیید شد${skipped ? `؛ ${toFa(skipped)} گروه بدون تصمیم ماند` : ""}.`);
    } catch (e) {
      setNotice(friendlyErrorMessage(e, "تأیید گروهی ناموفق بود."));
    } finally {
      setBulkBusy(false);
    }
  }

  async function runContinue() {
    setBulkBusy(true);
    try {
      await onContinue();
      setAnswered(0);
    } catch (e) {
      setNotice(friendlyErrorMessage(e, "شروع دور بعد ناموفق بود."));
    } finally {
      setBulkBusy(false);
    }
  }

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  if (!questions || !groups) return <LoadingBlock />;

  const agentProposals = new Set(pending.filter((g) => g.disposition && g.disposition !== "needs_input").map((g) => g.group_key));

  return (
    <div className="space-y-5">
      {notice && <p role="status" className="rounded-xl bg-teal-50 px-4 py-2 text-sm text-teal-800">{notice}</p>}

      <Card
        title={<>سؤال‌ها {questions.length > 0 && <span className="text-amber-600">({toFa(questions.length)})</span>}</>}
        actions={canContinue && editable ? (
          <Button size="sm" variant={answered > 0 ? "primary" : "secondary"} isLoading={bulkBusy} onClick={() => void runContinue()}>
            ادامه — دور بعد بررسی هوشمند
          </Button>
        ) : undefined}
      >
        {questions.length === 0 ? <EmptyState title="سؤال بازی نیست" hint="اگر هنوز گروه بدون تصمیم دارید، «ادامه» یک دور دیگر بررسی هوشمند اجرا می‌کند." /> : (
          <div className="space-y-3">
            {questions.map((q) => (
              <QuestionCard key={q.id} question={q} busy={busyId === q.id || !editable}
                groups={q.group_keys.map((k) => groupMap.get(k)).filter((g): g is ReviewGroup => Boolean(g))}
                onAnswer={(payload) => void answer(q, payload)} onSkip={() => void skip(q)} />
            ))}
          </div>
        )}
      </Card>

      <Card
        title={<>تأیید گروهی {pending.length > 0 && <span className="text-slate-500">({toFa(pending.length)} گروه تأییدنشده)</span>}</>}
        actions={editable && pending.length > 0 ? (
          <>
            <Button size="sm" variant="secondary" disabled={!selected.size} isLoading={bulkBusy} onClick={() => void confirmSelected(selected)}>تأیید انتخاب‌شده ({toFa(selected.size)})</Button>
            <Button size="sm" isLoading={bulkBusy} disabled={!agentProposals.size} onClick={() => void confirmSelected(agentProposals)}>تأیید همه‌ی پیشنهادها</Button>
          </>
        ) : undefined}
      >
        {pending.length === 0 ? <EmptyState title="همه‌ی گروه‌ها تأیید شده‌اند" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-xs">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="w-8 px-2 py-2"><input type="checkbox" aria-label="انتخاب همه" checked={selected.size === pending.length} onChange={(e) => setSelected(e.target.checked ? new Set(pending.map((g) => g.group_key)) : new Set())} className="accent-teal-600" /></th>
                  {["شرح", "واحد", "نوع کارگاه", "آیتم پیشنهادی", "نقش", "اطمینان ٪", "حافظه"].map((h) => <th key={h} className="px-2 py-2 text-start font-medium">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {pending.map((g) => {
                  const d = draftOf(g);
                  return (
                    <tr key={g.group_key} className="border-t border-slate-100 align-top">
                      <td className="px-2 py-2"><input type="checkbox" aria-label={`انتخاب ${g.description}`} checked={selected.has(g.group_key)} onChange={() => toggle(g.group_key)} className="accent-teal-600" /></td>
                      <td className="px-2 py-2">
                        <div className="font-medium text-slate-800">{g.description}</div>
                        <div className="text-slate-400">{toFa(g.n_lines)} ردیف · {formatQuantityWithUnit(g.total_quantity, g.unit, 2)}{g.section_headings[0] ? ` · ${g.section_headings[0]}` : ""}</div>
                        {g.locations && g.locations.length > 0 && (
                          <div className="mt-0.5 text-[11px] text-slate-500">
                            {g.locations.slice(0, 2).map((loc) => formatSourceLocationText(loc)).join(" | ")}
                            {g.locations.length > 2 ? ` (+${toFa(g.locations.length - 2)})` : ""}
                          </div>
                        )}
                      </td>
                      <td className="px-2 py-2 whitespace-nowrap">{g.unit}</td>
                      <td className="px-2 py-2 whitespace-nowrap">{SITE_KIND_LABELS[g.site_kind]}</td>
                      <td className="px-2 py-2">
                        <select aria-label="آیتم" value={d.choice} disabled={!editable} onChange={(e) => setDraft(g, { choice: e.target.value })} className={fieldClass}>
                          <option value="">— انتخاب کنید —</option>
                          {items.map((i) => <option key={i.key} value={i.key}>{i.title_fa}</option>)}
                          <option value="duplicate">تکراری (دوباره‌شماری)</option>
                          <option value="unmatched">سایر (نامنطبق)</option>
                        </select>
                      </td>
                      <td className="px-2 py-2">
                        <select aria-label="نقش" value={d.role} disabled={!editable} onChange={(e) => setDraft(g, { role: e.target.value as Role })} className={fieldClass}>
                          {(Object.keys(ROLE_LABELS) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                        </select>
                      </td>
                      <td className="px-2 py-2 whitespace-nowrap">{toFa(confidenceLabel(g.confidence))}</td>
                      <td className="px-2 py-2">
                        <select aria-label="حافظه" value={d.scope} disabled={!editable} onChange={(e) => setDraft(g, { scope: e.target.value as RememberScope })} className={fieldClass}>
                          <option value="global">سراسری</option>
                          <option value="line">فقط همین گزارش</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
