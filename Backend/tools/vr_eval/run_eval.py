"""Manual evaluation of the volume-report agent against a human-labelled golden set (NOT part of CI: uses the real LLM).

Workflow (from Backend/, with the app environment):
  1. python -m tools.vr_eval.run_eval build  --golden golden.json --out eval.xlsx
        -> a synthetic income workbook with the golden rows (quantities are dummies; classification never sees them)
  2. Upload eval.xlsx into a scratch project, create a report and run it (twice for repeatability) with the real model,
     WITHOUT answering questions (so the agent's own proposals are measured).
  3. python -m tools.vr_eval.run_eval score --golden golden.json --report REPORT_ID [--report SECOND_REPORT_ID]

Golden file: {"rows": [{"description", "unit", "site_kind", "item_key" | null, "role", "exclude_reason" | null}, ...]}
`item_key=null` means the row must be excluded. Keep the real golden set out of git (it carries company text);
`golden.example.json` only shows the shape. Paste the score output into .agents/ops/vr-evaluation.md.

Metrics: accuracy (item + exclusion), question rate (rows left to humans), silent errors (wrong AND counted AND unconfirmed
-- the dangerous kind), repeatability between two reports, tokens.
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import func, select

from app.core import model_registry  # noqa: F401
from app.core.database import async_session_factory
from app.features.volume_report.agent.index import GroupIndex
from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.units import normalize_unit
from app.features.volume_report.models import AgentRun, Item, Report


def build(golden: list[dict], out: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "درآمد پروژه ارزیابی"
    ws["B2"] = "گزارش درآمد پروژه ارزیابی در ماه شهریور 1405"
    for col, label in {2: "فعالیت", 5: "واحد", 6: "حجم"}.items():
        ws.cell(4, col, label)
    for i, row in enumerate(golden, start=5):
        ws.cell(i, 2, row["description"])
        ws.cell(i, 5, row["unit"])
        ws.cell(i, 6, 100 + i)
    wb.save(out)


async def _outcome(report_id: uuid.UUID) -> tuple[dict, dict]:
    """{normalized description|unit: (item_key | 'excluded' | 'open', confirmed)} and token usage."""
    async with async_session_factory() as db:
        report = await db.get(Report, report_id)
        index = await GroupIndex.load(db, report)
        keys = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
        result = {}
        for g in index.groups:
            c = g.classification
            if c is None or c.disposition.value == "needs_input":
                value = "open"
            elif c.disposition.value == "counted":
                value = keys.get(c.item_id, "open")
            else:
                value = c.disposition.value if c.disposition.value != "excluded" else "excluded"
            result[f"{normalize_text(g.description)}|{g.unit}"] = (value, bool(c and c.confirmed))
        tokens = (await db.execute(select(func.coalesce(func.sum(AgentRun.prompt_tokens), 0), func.coalesce(func.sum(AgentRun.completion_tokens), 0))
                                   .where(AgentRun.report_id == report_id))).one()
        return result, {"prompt": int(tokens[0]), "completion": int(tokens[1])}


def score(golden: list[dict], outcomes: list[dict], usage: list[dict]) -> str:
    first = outcomes[0]
    total = correct = asked = silent = 0
    for row in golden:
        key = f"{normalize_text(row['description'])}|{normalize_unit(row['unit']).unit_norm}"
        want = row["item_key"] or "excluded"
        got, confirmed = first.get(key, ("missing", False))
        total += 1
        if got == "open":
            asked += 1
        elif got == want or (want == "excluded" and got in ("excluded", "nonphysical")):
            correct += 1
        elif not confirmed:
            silent += 1
    lines = [
        f"rows={total} accuracy={correct / total:.1%} question_rate={asked / total:.1%} silent_errors={silent}",
        f"tokens(run1) prompt={usage[0]['prompt']} completion={usage[0]['completion']}",
    ]
    if len(outcomes) > 1:
        same = sum(1 for k, v in first.items() if outcomes[1].get(k, (None,))[0] == v[0])
        lines.append(f"repeatability={same / max(len(first), 1):.1%} over {len(first)} groups")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--golden", required=True)
    b.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--golden", required=True)
    s.add_argument("--report", action="append", required=True, type=uuid.UUID)
    args = parser.parse_args()
    golden = json.loads(Path(args.golden).read_text())["rows"]
    if args.cmd == "build":
        build(golden, Path(args.out))
        print(f"wrote {args.out} with {len(golden)} rows")
        return

    async def _run():
        pairs = [await _outcome(r) for r in args.report]
        print(score(golden, [p[0] for p in pairs], [p[1] for p in pairs]))

    asyncio.run(_run())


if __name__ == "__main__":
    main()
