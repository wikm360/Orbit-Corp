"use client";

import { useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { cn } from "@/shared/lib/utils";

import { formatQuantityWithUnit } from "../lib/format";
import { toFa } from "../lib/jalali";
import {
  allowedScopes, buildAnswer, emptyDraft, formatRowNumbersLabel, isPdfFilename, locationsForQuestion,
  orderedOptions, showsRemember, validateDraft, type Draft,
} from "../lib/questions";
import { SITE_KIND_LABELS } from "../lib/status";
import type { AnswerPayload, Question, RememberScope, ReviewGroup } from "../types";
import { fieldClass } from "./common";

interface Props {
  question: Question;
  /** The rows the question is about (looked up by group key from the review groups). */
  groups: ReviewGroup[];
  busy?: boolean;
  onAnswer: (payload: AnswerPayload) => void;
  onSkip: () => void;
}

const SCOPE_LABELS: Record<RememberScope, string> = { global: "به خاطر بسپار: سراسری (همه‌ی گزارش‌ها)", line: "فقط همین ردیف" };

export function QuestionCard({ question, groups, busy = false, onAnswer, onSkip }: Props) {
  const [draft, setDraft] = useState<Draft>(() => emptyDraft(question));
  const [touched, setTouched] = useState(false);
  const spec = question.spec;
  const error = touched ? validateDraft(question, draft) : null;
  const scopes = allowedScopes(question);
  const options = orderedOptions(spec.options ?? []);
  const locations = locationsForQuestion(question, groups);
  const multiple = question.kind === "multi_choice";
  const choiceKind = ["choice", "multi_choice", "confirm_group"].includes(question.kind);

  function toggle(key: string) {
    setDraft((d) => ({ ...d, choice: multiple ? (d.choice.includes(key) ? d.choice.filter((k) => k !== key) : [...d.choice, key]) : [key] }));
  }

  function submit() {
    setTouched(true);
    if (validateDraft(question, draft) === null) onAnswer(buildAnswer(question, draft));
  }

  return (
    <article aria-label="سؤال" className="rounded-2xl border border-amber-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium leading-7 text-slate-900">{spec.prompt}</p>

      {locations.length > 0 && (
        <div
          aria-label="منبع در فایل‌ها"
          className="mt-2 rounded-xl border border-slate-200/80 bg-slate-50/90 px-3 py-2 text-xs text-slate-700"
        >
          <p className="mb-1 text-[11px] font-semibold text-slate-500">محل در فایل‌های گزارش:</p>
          <ul className="space-y-1">
            {locations.slice(0, 5).map((loc, idx) => {
              const rowLabel = formatRowNumbersLabel(loc.row_nos, loc.n_lines);
              return (
                <li key={`${loc.filename}-${loc.sheet ?? ""}-${loc.section ?? ""}-${idx}`} className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  {loc.filename && (
                    <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 font-medium text-slate-800">
                      <span className="text-slate-400">فایل:</span>
                      <span dir="auto">{loc.filename}</span>
                    </span>
                  )}
                  {loc.sheet && (
                    <span className="text-slate-700">
                      <span className="text-slate-400">{isPdfFilename(loc.filename) ? "صفحه:" : "شیت:"}</span>{" "}
                      <span className="font-medium">{loc.sheet}</span>
                    </span>
                  )}
                  {loc.section && (
                    <span className="text-slate-600">
                      <span className="text-slate-400">بخش:</span> {loc.section}
                    </span>
                  )}
                  {loc.site && (
                    <span className="text-slate-500">کارگاه {loc.site}</span>
                  )}
                  {rowLabel && (
                    <span className="text-slate-500">{rowLabel}</span>
                  )}
                </li>
              );
            })}
            {locations.length > 5 && <li className="text-slate-500">و {toFa(locations.length - 5)} محل دیگر</li>}
          </ul>
        </div>
      )}

      {groups.length > 0 && (
        <ul className="mt-2 space-y-1 rounded-xl bg-slate-50 p-3 text-xs text-slate-700" aria-label="ردیف‌های مربوط">
          {groups.slice(0, 5).map((g) => (
            <li key={g.group_key} className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium">{g.description}</span>
              <span className="text-slate-500">
                {toFa(g.n_lines)} ردیف · {formatQuantityWithUnit(g.total_quantity, g.unit, 2)} · {SITE_KIND_LABELS[g.site_kind]}
                {g.section_headings[0] ? ` · ${g.section_headings[0]}` : ""}
              </span>
            </li>
          ))}
          {groups.length > 5 && <li className="text-slate-500">و {toFa(groups.length - 5)} گروه دیگر</li>}
        </ul>
      )}

      {spec.system === "layout" && spec.validation && (
        <p className="mt-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-700">
          با این چیدمان {toFa(spec.validation.rows)} ردیف خوانده می‌شود ({toFa(spec.validation.nonzero_rows)} ردیف دارای حجم).
        </p>
      )}

      {choiceKind && (
        <fieldset className="mt-3 space-y-1.5">
          <legend className="sr-only">گزینه‌ها</legend>
          {multiple && <p className="text-xs text-slate-500">برای هر گروه فقط یک گزینه اعمال می‌شود.</p>}
          {question.kind === "confirm_group" && options.length === 0 && <p className="text-xs text-slate-500">پیشنهاد فعلی را تأیید کنید یا یکی از گزینه‌ها را بزنید.</p>}
          {options.map((option) => {
            const checked = draft.choice.includes(option.key);
            return (
              <label key={option.key} className={cn("flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors", checked ? "border-teal-500 bg-teal-50" : "border-slate-200 hover:bg-slate-50")}>
                <input type={multiple ? "checkbox" : "radio"} name={`q-${question.id}`} checked={checked} onChange={() => toggle(option.key)} className="accent-teal-600" />
                {option.label}
              </label>
            );
          })}
        </fieldset>
      )}

      {question.kind === "number" && spec.number && (
        <div className="mt-3">
          <label className="text-xs text-slate-600" htmlFor={`n-${question.id}`}>مقدار ({spec.number.unit})</label>
          <div className="mt-1 flex items-center gap-2">
            <input
              id={`n-${question.id}`} inputMode="decimal" dir="ltr" value={draft.number} placeholder="0.5"
              onChange={(e) => setDraft((d) => ({ ...d, number: e.target.value }))}
              className={cn(fieldClass, "max-w-[12rem] text-left")}
            />
            <span className="text-xs text-slate-500">{spec.number.unit} — بازه‌ی مجاز {toFa(spec.number.min)} تا {toFa(spec.number.max)}</span>
          </div>
        </div>
      )}

      {question.kind === "text" && (
        <textarea
          aria-label="یادداشت" rows={3} value={draft.text} onChange={(e) => setDraft((d) => ({ ...d, text: e.target.value }))}
          className={cn(fieldClass, "mt-3")} placeholder="یادداشت شما (تصمیم دسته‌بندی را مستقیم تغییر نمی‌دهد)"
        />
      )}

      {showsRemember(question) && scopes.length > 1 && (
        <fieldset className="mt-3 flex flex-wrap gap-4 text-xs text-slate-700">
          <legend className="sr-only">حافظه</legend>
          {scopes.map((scope) => (
            <label key={scope} className="flex cursor-pointer items-center gap-1.5">
              <input type="radio" name={`s-${question.id}`} checked={draft.scope === scope} onChange={() => setDraft((d) => ({ ...d, scope }))} className="accent-teal-600" />
              {SCOPE_LABELS[scope]}
            </label>
          ))}
        </fieldset>
      )}

      {error && <p role="alert" className="mt-2 text-xs text-red-600">{error}</p>}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" onClick={submit} isLoading={busy}>ثبت پاسخ</Button>
        <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={onSkip}>رد کردن</Button>
        <span className="ms-auto text-[11px] text-slate-400">اثر: {toFa(Math.round(question.impact_score * 1000) / 10)}٪</span>
      </div>
    </article>
  );
}
