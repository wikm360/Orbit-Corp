"""Chat/agent tool `get_volume_report`: read-only access to PUBLISHED volume reports of the conversation's project.

Numbers come from the immutable snapshot (computed by code, never by a model); the tool never starts a run and never
shows drafts' figures. Scope always comes from `resolve_retrieval_scope`, not from the model's arguments."""

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.models import Report, ReportStatus, Snapshot

_GROUPS = ["holding", "company", "site", "item"]
_MAX_ROWS = 200


def _pick_report(reports: list[Report], period: str | None) -> Report | None:
    superseding = {r.supersedes_id for r in reports if r.supersedes_id}
    current = [r for r in reports if r.id not in superseding]  # an older version loses to its published successor
    if not current:
        return None
    wanted = (period or "latest").strip()
    if wanted != "latest":
        if ".." in wanted:
            start, _, end = wanted.partition("..")
            current = [r for r in current if r.period_start.isoformat() == start.strip() and r.period_end.isoformat() == end.strip()]
        else:
            needle = normalize_text(wanted)
            current = [r for r in current if needle and needle in normalize_text(r.period_label)]
    return max(current, key=lambda r: (r.period_end, r.version), default=None)


def _fmt(qty: Decimal, decimals: int) -> str:
    return f"{qty.quantize(Decimal(1).scaleb(-decimals)):,.{decimals}f}"


class GetVolumeReportTool(BaseTool):
    name = "get_volume_report"
    description = (
        "Weekly/monthly physical work-volume report (excavation, fill, subbase, base, asphalt, concrete, rebar, formwork, prime/tack coat, "
        "precast, pile drilling, pipe laying, mining load) of the linked project, per site, company or whole holding. Only PUBLISHED reports; figures "
        "are computed by the system - quote them exactly. Read-only: it cannot create or run a report."
    )
    parameters = {
        "type": "object",
        "properties": {
            "period": {"type": "string", "description": "'latest' (default), 'YYYY-MM-DD..YYYY-MM-DD' or the period label, e.g. 'شهریور 1405'"},
            "company": {"type": "string", "description": "Filter by company name (part of the name)"},
            "site": {"type": "string", "description": "Filter by site name (part of the name)"},
            "item": {"type": "string", "description": "Filter by item key (e.g. 'base') or Persian title"},
            "group_by": {"type": "string", "enum": _GROUPS, "description": "Default holding"},
        },
    }

    async def execute(self, *, db, context, conversation, period: str | None = None, company: str | None = None,
                      site: str | None = None, item: str | None = None, group_by: str = "holding", **_: Any) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        if project_id is None:
            return ToolExecutionResult(text="This conversation isn't linked to any project.")
        if group_by not in _GROUPS:
            group_by = "holding"
        reports = (await db.execute(select(Report).where(Report.project_id == project_id))).scalars().all()
        published = [r for r in reports if r.status == ReportStatus.PUBLISHED]
        report = _pick_report(published, period)
        if report is None:
            drafts = [f"{r.title} ({r.period_label}, {r.status.value})" for r in reports if r.status != ReportStatus.PUBLISHED][:10]
            hint = "; ".join(drafts) if drafts else "none"
            suffix = " for that period" if published and period and period != "latest" else ""
            return ToolExecutionResult(text=f"No published volume report{suffix}. Existing drafts: {hint}. "
                                            "Offer to prepare one in the Volume Reports section; do not estimate figures from raw files.")
        snapshot = (await db.execute(select(Snapshot).where(Snapshot.report_id == report.id))).scalar_one_or_none()
        if snapshot is None:
            return ToolExecutionResult(text="The published report has no snapshot.")
        payload = snapshot.payload
        catalog = {c["key"]: c for c in payload.get("catalog", [])}

        def match(text: str | None, needle: str | None) -> bool:
            return not needle or normalize_text(needle) in normalize_text(text or "")

        rows = [r for r in payload["results"]["site"]
                if match(r["company"], company) and match(r["site"], site)
                and (not item or item == r["item_key"] or match(r["item"], item))]
        grouped: dict[tuple, list] = {}
        for r in rows:
            label = {"holding": (), "company": (r["company"],), "site": (r["company"], r["site"]), "item": ()}[group_by]
            cell = grouped.setdefault((*label, r["item_key"]), [Decimal(0), r["unit"], 0, False])
            cell[0] += Decimal(r["qty"])
            cell[2] += r["n_lines"]
            cell[3] = cell[3] or r["has_unconfirmed"]
        order = {k: i for i, k in enumerate(catalog)}
        keys = sorted(grouped, key=lambda k: (k[:-1], order.get(k[-1], 99)))[:_MAX_ROWS]
        lead = {"holding": [], "company": ["شرکت"], "site": ["شرکت", "کارگاه"], "item": []}[group_by]
        columns = lead + ["آیتم", "مقدار"]  # units travel in `unit_by_row`
        out_rows, units, md = [], [], []
        for k in keys:
            qty, unit, _n, unconf = grouped[k]
            meta = catalog.get(k[-1], {"title_fa": k[-1], "decimals": 2})
            shown = _fmt(qty, meta["decimals"])
            out_rows.append([*k[:-1], meta["title_fa"], shown + ("*" if unconf else "")])
            units.append(unit)
            md.append("| " + " | ".join([*map(str, k[:-1]), meta["title_fa"], shown + ("*" if unconf else ""), unit]) + " |")
        gate = payload.get("warnings", {}).get("gate", [])
        notes = [f"گزارش منتشرشده: {report.title} — {report.period_label} (نسخه {report.version})"]
        if gate:
            notes.append("این گزارش با موارد باز منتشر شده است: " + ", ".join(f"{g['code']}={g['count']}" for g in gate))
        if any(grouped[k][3] for k in keys):
            notes.append("* شامل ردیف‌های تأییدنشده")
        if not keys:
            return ToolExecutionResult(text=f"The published report '{report.title}' ({report.period_label}) has no rows for these filters.")
        header = "| " + " | ".join(columns + ["واحد"]) + " |"
        text = "\n".join([notes[0], header, "|" + "---|" * (len(columns) + 1), *md, *[f"- {n}" for n in notes[1:]]])
        artifact = {"type": "volume_table", "version": 1, "report_id": str(report.id), "title": report.title, "period": report.period_label,
                    "columns": columns, "rows": out_rows, "unit_by_row": units, "notes": notes}
        return ToolExecutionResult(text=text, artifacts=[json.loads(json.dumps(artifact))])
