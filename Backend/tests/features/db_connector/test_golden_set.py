"""Guards for the accountant-style golden set and the knowledge it depends on (no SQL Server, no LLM, no Postgres).

The numbers in golden_expected.json come from a restored backup (see .agents/ops/accounting-golden-evaluation.md);
here we only check that the set is well-formed and that the hint corpus still teaches the things the golden cases probe.
"""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

import app.features.db_connector.hints as H
from app.features.db_connector.sql_validator import validate_sql

EXAMPLES = Path(__file__).resolve().parents[3] / "sql" / "rahkaran" / "examples"


def _load_golden():
    spec = importlib.util.spec_from_file_location("rahkaran_golden", EXAMPLES / "golden.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rahkaran_golden"] = mod
    spec.loader.exec_module(mod)
    return mod.GOLDEN


GOLDEN = _load_golden()
KINDS = {"scalar", "rows", "refusal", "ambiguous"}


def test_golden_cases_well_formed():
    ids = [c["id"] for c in GOLDEN]
    assert len(ids) == len(set(ids)) >= 20
    for c in GOLDEN:
        assert c["kind"] in KINDS
        assert c["question"].strip() and c["views"]
        if c["kind"] == "refusal":
            assert c["sql"] is None
        else:
            assert c["sql"] and c.get("value_col")


@pytest.mark.parametrize("case", [c for c in GOLDEN if c["sql"]], ids=lambda c: c["id"])
def test_golden_reference_sql_passes_validator(case):
    validate_sql(case["sql"])  # raises SqlValidationError when the reference itself would be rejected in production


def test_golden_expected_covers_every_case():
    expected = json.loads((EXAMPLES / "golden_expected.json").read_text(encoding="utf-8"))
    assert {c["id"] for c in GOLDEN} == set(expected)
    for c in GOLDEN:
        if c["sql"]:
            assert expected[c["id"]]["row_count"] >= 1, c["id"]


def test_golden_questions_are_not_few_shot_examples():
    """A golden question copied into the few-shot corpus would make the evaluation meaningless."""
    shots = {c["title"].strip() for c in H.load_corpus() if c["kind"] == "example"}
    leaked = [c["id"] for c in GOLDEN if c["question"].strip() in shots]
    assert not leaked, leaked


def _retrieve(question: str, k: int = 8):
    corpus = H.load_corpus()
    hints = [H.Hint(c["id"], c["kind"], c["title"], c["text"], c.get("views", []), c.get("keywords", [])) for c in corpus]
    index = H._index(hints)

    async def fake_load(_db):
        return hints, index

    async def fake_vec(_db, _q, _limit):
        return []

    orig = H._load_hints, H._vector_ranking
    H._load_hints, H._vector_ranking = fake_load, fake_vec
    try:
        return asyncio.run(H.retrieve_hints(None, question, top_k=k))
    finally:
        H._load_hints, H._vector_ranking = orig


def _views(got):
    return [k.split(":")[1] for k in got.keys if k.startswith("view:")]


def test_level6_question_retrieves_detail_view_first():
    got = _retrieve("هزینه قطعات خریداری‌شده برای یک کمپرسی در یک پروژه در سال ۱۴۰۴ چقدر بود؟")
    assert _views(got)[0] == "equipment_project_cost_year"
    assert any(k == "note:cost_levels" for k in got.keys)


def test_closed_year_breakdown_question_gets_the_warning_note():
    got = _retrieve("هزینه لاستیک ماشین‌آلات در سال ۱۴۰۲ به تفکیک دستگاه")
    assert "equipment_project_cost_year" in _views(got)
    assert "note:closed_year_breakdown" in got.keys


def test_invoice_items_question_gets_the_unavailable_note():
    got = _retrieve("چند عدد پنوماتیک زانویی در فاکتورهای قطعات خریده‌ایم؟")
    assert "note:invoice_items_missing" in got.keys


def test_petty_cash_question_retrieves_petty_cash_view():
    assert _views(_retrieve("مانده تنخواه یک دارنده چقدر است؟"))[0] == "petty_cash_balances"


def test_core_prompt_teaches_levels_and_limits():
    prompt = H.load_core_prompt()
    for needle in ("expense_item_name", "equipment_project_cost_year", "is_wip_transfer", "contract_name_norm", "is_party_account", "NO_SQL"):
        assert needle in prompt, needle


def test_corpus_documents_the_new_columns():
    text = " ".join(c["text"] for c in H.load_corpus() if c["kind"] == "view")
    for col in ("expense_item_name", "contract_name_norm", "equipment_plate", "is_wip_transfer", "is_party_account", "holder_name_norm"):
        assert col in text, col
