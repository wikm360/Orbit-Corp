/** Pure logic of the question cards: ordering, validation, building the answer payload. */

import type { AnswerPayload, Question, QuestionOption, RememberScope, ReviewGroup } from "../types";

export const FIXED_OPTION_KEYS = ["exclude", "unknown", "other"] as const;

export const byImpact = (questions: Question[]): Question[] =>
  [...questions].sort((a, b) => b.impact_score - a.impact_score || a.created_at.localeCompare(b.created_at));

/** Item options come first; the fixed escape hatches (حذف / نمی‌دانم / سایر) always last. */
export function orderedOptions(options: QuestionOption[]): QuestionOption[] {
  const fixed = (key: string) => (FIXED_OPTION_KEYS as readonly string[]).includes(key);
  return [...options.filter((o) => !fixed(o.key)), ...options.filter((o) => fixed(o.key))];
}

export function allowedScopes(question: Question): RememberScope[] {
  const scopes = question.spec.remember_scopes;
  return scopes && scopes.length ? scopes : ["global", "line"];
}
export const defaultScope = (question: Question): RememberScope => question.spec.default_remember ?? allowedScopes(question)[0] ?? "global";

export interface Draft { choice: string[]; number: string; text: string; scope: RememberScope }
export const emptyDraft = (question: Question): Draft => ({ choice: [], number: "", text: "", scope: defaultScope(question) });

/** Accepts Persian digits and the Persian decimal separator. Returns null for anything that is not a plain number. */
export function parseNumberInput(text: string): number | null {
  const normalized = text
    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[٫,]/g, ".")
    .trim();
  if (!/^\d+(\.\d+)?$/.test(normalized)) return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

/** Why the draft cannot be sent yet (Persian), or null when it can. */
export function validateDraft(question: Question, draft: Draft): string | null {
  const spec = question.spec;
  if (question.kind === "number") {
    const value = parseNumberInput(draft.number);
    if (value === null || value <= 0) return "یک عدد معتبر و بزرگ‌تر از صفر وارد کنید.";
    const { min, max } = spec.number ?? { min: 0, max: Number.POSITIVE_INFINITY };
    if (value < min || value > max) return `عدد باید بین ${min} و ${max} باشد.`;
    return null;
  }
  if (question.kind === "text") return draft.text.trim() ? null : "متن یادداشت را بنویسید.";
  if (question.kind === "multi_choice") {
    // The backend applies exactly one option to a group, so more than one is refused there.
    if (draft.choice.length !== 1) return "برای هر گروه فقط یک گزینه را انتخاب کنید.";
    return null;
  }
  if (question.kind === "confirm_group" && spec.system !== "layout") return draft.choice.length === 1 || draft.choice.length === 0 ? null : "فقط یک گزینه را انتخاب کنید.";
  return draft.choice.length === 1 ? null : "یک گزینه را انتخاب کنید.";
}

export function buildAnswer(question: Question, draft: Draft): AnswerPayload {
  const payload: AnswerPayload = { choice_keys: [], remember_scope: draft.scope };
  if (question.kind === "number") payload.number = parseNumberInput(draft.number);
  else if (question.kind === "text") payload.text = draft.text.trim();
  else payload.choice_keys = draft.choice;
  return payload;
}

/** Whether a "remember" selector makes sense: only for questions that change a classification. */
export const showsRemember = (question: Question): boolean =>
  !question.spec.system || question.spec.system === "no_conversion" || question.spec.system === "unit_mismatch"
    ? question.kind !== "text"
    : false;

export function groupsForQuestion(question: Question, groups: Map<string, ReviewGroup>): ReviewGroup[] {
  return question.group_keys.map((key) => groups.get(key)).filter((g): g is ReviewGroup => Boolean(g));
}

export const openCount = (questions: Question[]) => questions.filter((q) => q.status === "open").length;
