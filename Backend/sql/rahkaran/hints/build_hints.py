"""Build the Text-to-SQL hint corpus for the Rahkaran semantic layer (step 3).

Reads the catalogs from the database (ai.view_catalog / ai.column_catalog / ai.glossary, as the read-only user), the example questions
(../examples/questions.py) and the hand-written knowledge (notes.py), and writes to ./out:
  hints.jsonl      one JSON chunk per line: {id, kind, title, text, views, keywords}  -> to be embedded + stored for retrieval (step 4)
  core_prompt.md   the short always-on system prompt
  hints_stats.json counts per kind
Env: RAHKARAN_AI_PASSWORD (+ RAHKARAN_AI_USER, RAHKARAN_HOST, RAHKARAN_PORT, RAHKARAN_DB).
"""
import json, os, re, sys
import pymssql

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "examples"))
from notes import CORE_PROMPT, VIEW_HINTS, DOMAIN_NOTES
from questions import Q

COLS_PER_CHUNK = 28
SKIP_VIEWS = {"column_catalog", "view_catalog"}  # meta helper, not useful as a retrieval target


def connect():
    return pymssql.connect(os.environ.get("RAHKARAN_HOST", "127.0.0.1"), user=os.environ.get("RAHKARAN_AI_USER", "rahkaran_ai_reader"),
                           password=os.environ["RAHKARAN_AI_PASSWORD"], database=os.environ.get("RAHKARAN_DB", "MehvarGostar"),
                           port=int(os.environ.get("RAHKARAN_PORT", "14330")), charset="UTF-8", login_timeout=30)


def _group_title(t):
    return re.sub(r"\s+", " ", re.sub(r"[0-9]+$", "", t.replace("ي", "ی").replace("ك", "ک"))).strip()


def taxonomy_chunks(cur):
    """One chunk per accountant category (detail_category) listing its moin accounts grouped by title, plus an index chunk of the hierarchy.
    Source: ai.account_taxonomy joined with ai.accounts (only accounts that exist in this database)."""
    cur.execute("SELECT t.pnl_statement, t.detail_category, a.sl_code, RTRIM(a.sl_title) AS sl_title, a.has_postings "
                "FROM ai.account_taxonomy t JOIN ai.accounts a ON a.sl_code = t.sl_code WHERE t.detail_category IS NOT NULL ORDER BY a.sl_code")
    rows = cur.fetchall()
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["detail_category"], {}).setdefault(r["pnl_statement"], []).append(r)
    chunks, index = [], {}
    for cat, stmts in sorted(by_cat.items()):
        body, kws = [], [cat]
        for stmt, accs in sorted(stmts.items()):
            index.setdefault(stmt, []).append(cat)
            titles = {}
            for a in accs:
                titles.setdefault(_group_title(a["sl_title"]), []).append(a["sl_code"])
            body.append(f"سرفصل «{stmt}»:\n" + "\n".join(f"- {t}: " + "، ".join(codes) for t, codes in titles.items()))
            kws += [stmt] + list(titles)[:25]
        text = (f"طبقه‌بندی حسابدار - دسته: {cat}\n"
                f"فیلتر کلی: detail_category = N'{cat}' (در ai.pnl_by_category_year یا ledger_lines/cost_lines)؛ فیلتر جزئی: sl_code IN (...) یا sl_title LIKE N'%...%'.\n"
                "معین‌ها (عنوان: کدها؛ 1117xx طی سال پروژه‌ها، 5111xx/5112xx بعد از پایان سال، 6213xx اداری):\n" + "\n".join(body))
        chunks.append(dict(id=f"taxonomy:{len(chunks) + 1:03d}", kind="taxonomy", title=f"دسته‌ی {cat}", text=text,
                           views=["pnl_by_category_year", "account_taxonomy"], keywords=kws))
    idx = "\n".join(f"- {stmt}: " + "، ".join(cats) for stmt, cats in sorted(index.items()))
    chunks.append(dict(id="taxonomy:000", kind="taxonomy", title="فهرست دسته‌های حسابدار",
                       text="طبقه‌بندی حسابدار: سرفصل صورت سود و زیان ← دسته‌ی تحلیلی (detail_category) ← معین. دسته‌ها:\n" + idx,
                       views=["pnl_by_category_year", "account_taxonomy"], keywords=["دسته‌ها", "طبقه‌بندی", "سرفصل", "انواع هزینه"]))
    return chunks


def main():
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    cur = connect().cursor(as_dict=True)
    cur.execute("SELECT view_name, description, column_count FROM ai.view_catalog ORDER BY view_name")
    views = {r["view_name"]: r for r in cur.fetchall()}
    cur.execute("SELECT view_name, ordinal, column_name, data_type, description FROM ai.column_catalog ORDER BY view_name, ordinal")
    cols = {}
    for r in cur.fetchall():
        cols.setdefault(r["view_name"], []).append(r)
    cur.execute("SELECT term_fa, meaning_fa, where_to_query FROM ai.glossary")
    glossary = cur.fetchall()

    examples_by_view = {}
    for group, question, sql in Q:
        for v in set(re.findall(r"ai\.(\w+)", sql)):
            examples_by_view.setdefault(v, []).append((question, sql))

    chunks = []

    # ---- view chunks (description + hints + columns [+ examples]) ----
    for name, info in views.items():
        if name in SKIP_VIEWS:
            continue
        h = VIEW_HINTS.get(name, {})
        c = cols.get(name, [])
        head = [f"view: ai.{name}", f"توضیح: {info['description']}"]
        if h.get("use"): head.append(f"کاربرد: {h['use']}")
        if h.get("filters"): head.append(f"فیلترهای معمول: {h['filters']}")
        if h.get("pitfalls"): head.append(f"نکات و اشتباهات رایج: {h['pitfalls']}")
        if h.get("keywords"): head.append("کلمات کلیدی: " + "، ".join(h["keywords"]))
        parts = [c[i:i + COLS_PER_CHUNK] for i in range(0, len(c), COLS_PER_CHUNK)] or [[]]
        for pi, part in enumerate(parts):
            lines = [f"- {x['column_name']} ({x['data_type']}): {x['description']}" for x in part]
            title = f"ai.{name}" + (f" (ستون‌ها {pi + 1}/{len(parts)})" if len(parts) > 1 else "")
            text = "\n".join((head if pi == 0 else head[:2]) + ["ستون‌ها:"] + lines)
            if pi == 0 and name in examples_by_view:
                ex = examples_by_view[name][:2]
                text += "\nنمونه پرسش‌ها: " + " | ".join(q for q, _ in ex)
            chunks.append(dict(id=f"view:{name}:{pi + 1}", kind="view", title=title, text=text, views=[name],
                               keywords=h.get("keywords", [])))

    # ---- example chunks (question -> SQL) ----
    for i, (group, question, sql) in enumerate(Q, 1):
        used = sorted(set(re.findall(r"ai\.(\w+)", sql)))
        text = f"سؤال: {question}\nview ها: " + "، ".join("ai." + v for v in used) + f"\nSQL:\n{sql}"
        chunks.append(dict(id=f"example:{i:03d}", kind="example", title=question, text=text, views=used, keywords=[group]))

    # ---- glossary chunks ----
    for i, g in enumerate(glossary, 1):
        used = sorted(set(re.findall(r"ai\.(\w+)", g["where_to_query"])))
        text = f"اصطلاح: {g['term_fa']}\nمعنی: {g['meaning_fa']}\nمحل داده: {g['where_to_query']}"
        chunks.append(dict(id=f"glossary:{i:03d}", kind="glossary", title=g["term_fa"], text=text, views=used, keywords=[]))

    # ---- domain notes ----
    for nid, title, text, kws in DOMAIN_NOTES:
        used = sorted(set(re.findall(r"ai\.(\w+)", text)))
        chunks.append(dict(id=f"note:{nid}", kind="note", title=title, text=f"{title}\n{text}\nکلمات کلیدی: " + "، ".join(kws), views=used, keywords=kws))

    chunks += taxonomy_chunks(cur)

    with open(os.path.join(out_dir, "hints.jsonl"), "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    open(os.path.join(out_dir, "core_prompt.md"), "w", encoding="utf-8").write(CORE_PROMPT)
    stats = {}
    for ch in chunks:
        stats[ch["kind"]] = stats.get(ch["kind"], 0) + 1
    stats["total_chars"] = sum(len(c["text"]) for c in chunks)
    stats["max_chunk_chars"] = max(len(c["text"]) for c in chunks)
    json.dump(stats, open(os.path.join(out_dir, "hints_stats.json"), "w"), ensure_ascii=False, indent=1)
    print(stats)
    missing = [v for v in views if v not in SKIP_VIEWS and v not in VIEW_HINTS]
    print("views without hand-written hints (auto only):", missing)


if __name__ == "__main__":
    main()
