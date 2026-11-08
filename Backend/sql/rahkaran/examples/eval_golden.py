"""Evaluate the accounting Text-to-SQL stack on the golden set (examples/golden.py + golden_expected.json).

Two modes (run from Backend/ with the project's venv):

  python sql/rahkaran/examples/eval_golden.py retrieval [--k 8] [--out r.json]
      Local and free: lexical (BM25) hint retrieval using the project's own `retrieve_hints` selection logic (per-kind caps, view parts),
      WITHOUT Postgres / embeddings / LLM. Reports whether any expected view is in the retrieved set and at which rank.

  python sql/rahkaran/examples/eval_golden.py e2e [--ids g01,g02] [--out r.json]
      Real pipeline: `run_accounting_query` (needs Postgres for the log table, the hint table or the jsonl fallback, the LLM + embedding API,
      and RAHKARAN_DB_* env pointing at the restored SQL Server, e.g. RAHKARAN_DB_PORT=14331). SENDS THE QUESTION AND THE RESULT ROWS TO THE
      CONFIGURED EXTERNAL LLM PROVIDER - run it deliberately. Auto-scores scalar/rows cases against golden_expected.json; refusal/ambiguous
      cases are printed with the generated SQL and the reply for human review (marked "manual").

Scoring (e2e): scalar -> some numeric cell of the artifact matches the expected value within 0.5%;
               rows   -> the first-column keys of the expected rows are a subset of (>=80% of) the artifact's first-column keys, and when the
                         expected set has a value_col the sum over expected keys matches within 0.5%.
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))  # Backend/

from golden import GOLDEN  # noqa: E402


def _expected() -> dict:
    return json.loads((HERE / "golden_expected.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ retrieval
async def run_retrieval(k: int, ids: set[str] | None) -> list[dict]:
    import app.features.db_connector.hints as H

    corpus = H.load_corpus()
    hints = [H.Hint(c["id"], c["kind"], c["title"], c["text"], c.get("views", []), c.get("keywords", [])) for c in corpus]
    index = H._index(hints)

    async def fake_load(_db):
        return hints, index

    async def fake_vec(_db, _q, _limit):
        return []

    H._load_hints, H._vector_ranking = fake_load, fake_vec  # lexical only, no DB / network

    results = []
    for c in GOLDEN:
        if ids and c["id"] not in ids:
            continue
        got = await H.retrieve_hints(None, c["question"], top_k=k)
        view_keys = [key for key in got.keys if key.startswith("view:")]
        names = [key.split(":")[1] for key in view_keys]
        rank = next((i + 1 for i, n in enumerate(names) if n in c["views"]), None)
        results.append({"id": c["id"], "group": c["group"], "ok": rank is not None, "rank": rank, "views": names[:6], "expected": c["views"]})
    return results


# ------------------------------------------------------------------ end to end
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _close(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b), 1.0)


def score_artifact(case: dict, exp: dict, artifact: dict | None) -> tuple[str, str]:
    kind = case["kind"]
    if kind in ("refusal", "ambiguous"):
        return "manual", "review the reply"
    if not artifact or not artifact.get("rows"):
        return "FAIL", "no rows"
    rows = artifact["rows"]
    exp_rows = exp["rows"]
    col = case.get("value_col")
    if kind == "scalar":
        want = _num(exp_rows[0][col]) if exp_rows else None
        for r in rows[:50]:
            if any((n := _num(v)) is not None and want is not None and _close(n, want) for v in r):
                return "PASS", f"found {want:,.0f}"
        return "FAIL", f"expected {want} not in first rows ({str(rows[0])[:80]})"
    # rows
    keys_exp = [str(next(iter(r.values()))) for r in exp_rows]
    keys_got = {str(r[0]) for r in rows}
    hit = sum(1 for k in keys_exp if k in keys_got)
    if keys_exp and hit / len(keys_exp) < 0.8:
        return "FAIL", f"key overlap {hit}/{len(keys_exp)}"
    return "PASS", f"key overlap {hit}/{len(keys_exp)}"


async def run_e2e(ids: set[str] | None) -> list[dict]:
    from app.core.database import async_session_factory
    from app.features.db_connector.service import run_accounting_query

    exp_all = _expected()
    results = []
    async with async_session_factory() as db:
        for c in GOLDEN:
            if ids and c["id"] not in ids:
                continue
            ans = await run_accounting_query(db, question=c["question"], include_sql_in_text=True)
            art = ans.artifact
            status, detail = score_artifact(c, exp_all[c["id"]], art)
            results.append({"id": c["id"], "group": c["group"], "status": status, "detail": detail, "sql": (art or {}).get("sql"),
                            "query_status": str(ans.status), "reply": ans.text[:1500] if status == "manual" else None})
            print(f"{c['id']} {status:6} {detail}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["retrieval", "e2e"])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--ids", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    ids = {x for x in a.ids.split(",") if x} or None
    if a.mode == "retrieval":
        res = asyncio.run(run_retrieval(a.k, ids))
        for r in res:
            print(f"{r['id']} {r['group']:12} {'OK ' if r['ok'] else 'MISS'} rank={r['rank']}  got={r['views'][:4]}  want={r['expected']}")
        ok = sum(r["ok"] for r in res)
        top1 = sum(1 for r in res if r["rank"] == 1)
        print(f"\nretrieval: {ok}/{len(res)} cases have an expected view in top-{a.k}; {top1} at rank 1")
    else:
        res = asyncio.run(run_e2e(ids))
        sc = [r["status"] for r in res]
        print(f"\ne2e: PASS={sc.count('PASS')} FAIL={sc.count('FAIL')} manual={sc.count('manual')} of {len(res)}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
