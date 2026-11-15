"""Structural checks of the ai.ledger_lines materialization (needs no SQL Server).

The heavy source query lives in the hidden schema ai_src; 35_ledger_materialize.sql copies it into ai.ledger_lines_mat and re-exposes it as the
view ai.ledger_lines, so every downstream view / hint / description keeps working unchanged.
"""
import glob
import os
import re

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sql", "rahkaran")


def _read(name: str) -> str:
    with open(os.path.join(SQL_DIR, name), encoding="utf-8") as f:
        return f.read()


def test_source_query_moved_to_hidden_schema():
    assert "CREATE OR ALTER VIEW ai_src.ledger_lines AS" in _read("30_ledger.sql")
    assert not re.search(r"CREATE OR ALTER VIEW ai\.ledger_lines\b", _read("30_ledger.sql"))
    assert "ai_src" in _read("00_schema.sql")


def test_materialize_step_runs_after_source_and_before_dependents():
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SQL_DIR, "[0-9][0-9]_*.sql")))
    assert files.index("30_ledger.sql") < files.index("35_ledger_materialize.sql") < files.index("40_finance_reports.sql")


def test_materialize_builds_table_verifies_and_exposes_view():
    sql = _read("35_ledger_materialize.sql")
    assert "SELECT * INTO ai.ledger_lines_mat FROM ai_src.ledger_lines" in sql
    assert "CREATE UNIQUE CLUSTERED INDEX" in sql and "DATA_COMPRESSION = PAGE" in sql
    assert "THROW" in sql  # copy != source must abort the refresh before the swap
    # the public object stays a VIEW (descriptions/catalogs are built from sys.views)
    assert re.search(r"CREATE OR ALTER VIEW ai\.ledger_lines AS\s+SELECT \* FROM ai\.ledger_lines_mat", sql)
    # the view must be created after the table exists
    assert sql.index("SELECT * INTO") < sql.index("CREATE OR ALTER VIEW ai.ledger_lines")


def test_batches_split_like_apply_py():
    # apply.py splits on lines holding only GO; CREATE VIEW must be the first statement of its batch
    sql = _read("35_ledger_materialize.sql")
    batches = [b.strip() for b in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if b.strip()]
    view_batches = [b for b in batches if "CREATE OR ALTER VIEW" in b]
    assert len(view_batches) == 1
    assert re.sub(r"(?m)^--.*$", "", view_batches[0]).strip().startswith("CREATE OR ALTER VIEW")
