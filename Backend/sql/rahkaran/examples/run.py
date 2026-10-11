"""Execute every example query as the read-only user, report time/rows/errors, and regenerate docs/rahkaran/QUESTIONS.md.
Env: RAHKARAN_AI_PASSWORD (+ optional RAHKARAN_AI_USER, RAHKARAN_HOST, RAHKARAN_PORT, RAHKARAN_DB)."""
import os, sys, time, datetime, decimal
import pymssql
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from questions import Q

GROUPS = {"finance": "مالی و دفتر کل", "contracts": "قراردادها و صورت‌وضعیت‌ها", "counterparties": "مشتریان، تأمین‌کنندگان و طرف‌حساب‌ها",
          "banks": "بانک، تنخواه، ضمانت‌نامه و تسهیلات", "payroll": "حقوق و دستمزد", "hr": "منابع انسانی", "assets": "دارایی ثابت و تجهیزات", "meta": "متا"}

def fmt(v):
    if isinstance(v, decimal.Decimal): return f"{v:,.0f}" if abs(v) >= 1000 else str(v.normalize())
    if isinstance(v, (datetime.date, datetime.datetime)): return str(v)[:10]
    return str(v)[:40]

conn = pymssql.connect(os.environ.get("RAHKARAN_HOST", "127.0.0.1"), user=os.environ.get("RAHKARAN_AI_USER", "rahkaran_ai_reader"),
                       password=os.environ["RAHKARAN_AI_PASSWORD"], database=os.environ.get("RAHKARAN_DB", "MehvarGostar"),
                       port=int(os.environ.get("RAHKARAN_PORT", "14330")), charset="UTF-8", login_timeout=30)
cur = conn.cursor(as_dict=True)
out, bad = [], 0
last_group = None
for group, question, sql in Q:
    t = time.time()
    try:
        cur.execute(sql); rows = cur.fetchall(); err = None
    except Exception as e:
        rows, err = [], str(e)[:200]; bad += 1
    dt = time.time() - t
    status = "ERR " + err if err else f"{len(rows)} rows"
    print(f"[{dt:5.1f}s] {status:14} {question}")
    if group != last_group:
        out.append(f"\n## {GROUPS[group]}\n"); last_group = group
    out.append(f"### {question}\n\n```sql\n{sql}\n```\n")
    if rows:
        keys = list(rows[0].keys())[:6]
        out.append("نمونه خروجی: " + " | ".join(f"{k}={fmt(rows[0][k])}" for k in keys) + f"  ({len(rows)} ردیف)\n")
    elif not err:
        out.append("نمونه خروجی: (بدون ردیف)\n")
head = ("# نمونه سؤال‌ها و SQL مرجع (لایه‌ی معنایی ai)\n\nپیش‌نویس مجموعه‌ی ارزیابی (golden set). هر SQL روی view های `ai` و با کاربر فقط‌خواندنی اجرا و بررسی شده است؛ "
        "مبالغ به ریال. خروجی‌ها نمونه‌ی ردیف اول از snapshot بک‌آپ 2026-10-05 هستند و با به‌روزرسانی داده تغییر می‌کنند. تولید خودکار با `sql/rahkaran/examples/run.py`.\n")
dst = os.environ.get("RAHKARAN_QUESTIONS_OUT")
if dst:
    open(dst, "w", encoding="utf-8").write(head + "\n".join(out))
print(f"{len(Q)} questions, {bad} errors")
