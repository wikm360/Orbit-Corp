"""Run every golden reference SQL as the read-only user and (re)write golden_expected.json.
Env: RAHKARAN_AI_PASSWORD (+ RAHKARAN_AI_USER, RAHKARAN_HOST, RAHKARAN_PORT, RAHKARAN_DB). Rerun after each new backup: expected values move with the data."""
import datetime, decimal, json, os, sys
import pymssql
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden import GOLDEN


def jsonable(v):
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return str(v)[:10]
    return v


def main() -> int:
    conn = pymssql.connect(os.environ.get("RAHKARAN_HOST", "127.0.0.1"), user=os.environ.get("RAHKARAN_AI_USER", "rahkaran_ai_reader"),
                           password=os.environ["RAHKARAN_AI_PASSWORD"], database=os.environ.get("RAHKARAN_DB", "MehvarGostar"),
                           port=int(os.environ.get("RAHKARAN_PORT", "14330")), charset="UTF-8", login_timeout=30)
    cur = conn.cursor(as_dict=True)
    out, bad = {}, 0
    for c in GOLDEN:
        if c["sql"] is None:
            out[c["id"]] = {"kind": c["kind"], "rows": []}
            print(f"{c['id']} {c['kind']:9} -")
            continue
        try:
            cur.execute(c["sql"])
            rows = [{k: jsonable(v) for k, v in r.items()} for r in cur.fetchall()]
        except Exception as e:  # noqa: BLE001
            print(f"{c['id']} ERROR {str(e)[:160]}")
            bad += 1
            continue
        out[c["id"]] = {"kind": c["kind"], "value_col": c.get("value_col"), "row_count": len(rows), "rows": rows[:50]}
        first = rows[0] if rows else None
        print(f"{c['id']} {c['kind']:9} rows={len(rows):3} first={str(first)[:130]}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_expected.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("written", path, "errors:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
