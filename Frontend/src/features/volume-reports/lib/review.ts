/** Draft state of the bulk-confirm table: one editable decision per group. */

import type { ConfirmItem, RememberScope, ReviewGroup, Role } from "../types";

/** What the user picked for a group: a catalog item key, "duplicate", "unmatched" (= «سایر») or "" (nothing yet).
 *  There is no "remove from report": whatever is not counted is «سایر» and stays visible. */
export interface RowDraft { choice: string; role: Role; scope: RememberScope }

export const NO_CHOICE = "";

export function draftFromGroup(group: ReviewGroup): RowDraft {
  let choice = NO_CHOICE;
  if (group.disposition === "counted" && group.item_key) choice = group.item_key;
  else if (group.disposition === "excluded") choice = group.exclude_reason === "duplicate" ? "duplicate" : "unmatched"; // legacy removals read as «سایر»
  else if (group.disposition === "unmatched") choice = "unmatched";
  return { choice, role: group.role ?? "na", scope: "global" };
}

export function toConfirmItem(group: ReviewGroup, draft: RowDraft): ConfirmItem | null {
  if (draft.choice === NO_CHOICE) return null;
  const base = { group_key: group.group_key, role: draft.role, remember_scope: draft.scope };
  if (draft.choice === "duplicate") return { ...base, exclude_reason: "duplicate" };
  if (draft.choice === "unmatched") return { ...base, disposition: "unmatched" };
  return { ...base, item_key: draft.choice };
}

/** Confirms every selected row that has a decision; returns the payload plus how many selected rows had none. */
export function buildBulkPayload(groups: ReviewGroup[], drafts: Record<string, RowDraft>, selected: Set<string>) {
  const items: ConfirmItem[] = [];
  let skipped = 0;
  for (const group of groups) {
    if (!selected.has(group.group_key)) continue;
    const item = toConfirmItem(group, drafts[group.group_key] ?? draftFromGroup(group));
    if (item) items.push(item); else skipped += 1;
  }
  return { items, skipped };
}

/** Groups the agent proposed but nobody confirmed, plus groups still without any decision. */
export const pendingGroups = (groups: ReviewGroup[]): ReviewGroup[] => groups.filter((g) => !g.confirmed);

export const confidenceLabel = (c: number | null): string => (c === null ? "—" : `${Math.round(c * 100)}`);
