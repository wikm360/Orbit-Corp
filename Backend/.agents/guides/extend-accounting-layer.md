# راهنما: گسترش لایه‌ی حسابداری (view جدید، hint، نمونه‌سؤال)

زمینه: [../flows/accounting-data-refresh.md](../flows/accounting-data-refresh.md) و [../flows/accounting-query.md](../flows/accounting-query.md). دانش دامنه: `../../docs/rahkaran/`.

## افزودن یا تغییر view
1. در فایل `sql/rahkaran/NN_*.sql` مناسب (ledger=30، گزارش مالی=40، HR=50، حقوق=60، دارایی=70، متا=80…) view را بنویسید؛ idempotent (`CREATE OR ALTER VIEW ai.<name>`). از **نام‌گذاری استاندارد** ستون‌ها استفاده کنید (همان نام = همان معنی در همه‌ی view ها).
2. در `sql/rahkaran/descriptions.py`:
   - توضیح view در `VIEWS`
   - توضیح ستون‌های جدید در `COLS_TEXT` (یا `OVERRIDES` برای نام عمومی با معنی متفاوت). ستون ریالی باید «(ریال)» در توضیح داشته باشد.
3. اگر ستون ریالی اضافه شد، `app/features/db_connector/money_columns.py::MONEY_COLUMNS` را به‌روز کنید (طبق کامنت فایل: تولید از descriptions).
4. در `sql/rahkaran/hints/notes.py::VIEW_HINTS[view]` اضافه کنید: `keywords` (کلمات فارسی که کاربر می‌گوید)، `use`، `filters`، `pitfalls`. بدون آن، hint فقط از catalog خودکار ساخته می‌شود (build لیست «views without hand-written hints» را چاپ می‌کند).
5. اعمال: `RAHKARAN_SA_PASSWORD=… python sql/rahkaran/apply.py NN descr` (روی DB محلی؛ در prod با refresh/ریستور اعمال می‌شود).
6. `RAHKARAN_AI_PASSWORD=… python sql/rahkaran/hints/build_hints.py` → `out/`.
7. `ingest` (CLI) و بازبینی با `eval_retrieval.py`.
8. همیشه view جدید را با reader تست کنید (`examples/run.py`) و فقط ستون‌های لازم را در معرض بگذارید؛ ستون حساس (کد ملی، شبا، حساب، موبایل) را در view قرار ندهید یا مشخص برچسب بزنید (ماسک هنوز پیاده نیست).

## مفهوم یا دام جدید
`DOMAIN_NOTES` در notes.py: `(id, title, text, keywords)` — مثلاً قاعده‌ی سال مالی، تفاوت قرارداد/پروژه، علامت بدهکار/بستانکار. کوتاه و خاص بنویسید (بزرگ‌ترین chunk ~۲٫۶K نویسه).

## سؤال نمونه (few-shot)
`sql/rahkaran/examples/questions.py`: ردیف `(group, "سؤال فارسی", "SQL")` با `group ∈ finance, contracts, counterparties, banks, payroll, hr, assets, meta`. SQL باید روی reader بدون خطا و با نتیجه‌ی منطقی اجرا شود (`examples/run.py`). **سؤال‌هایی که مدل غلط جواب داد ارزشمندترین نمونه‌ها هستند** (از `db_query_logs` با feedback −1 یا status ≠ ok). سپس `QUESTIONS.md` را با `RAHKARAN_QUESTIONS_OUT=docs/rahkaran/QUESTIONS.md python sql/rahkaran/examples/run.py` بازتولید کنید.

## قاعده‌ی ثابت prompt
تغییر `CORE_PROMPT` در notes.py → `build_hints.py` → `core_prompt.md` → (بدون ingest؛ `load_core_prompt()` هر بار فایل را می‌خواند، پس بعد از کپی فایل روی سرور و restart/جایگزینی مؤثر است). هر قاعده را کوتاه نگه دارید (~۱۲۰۰ توکن).

## تغییر فایل طبقه‌بندی حسابدار
Excel را در `docs/rahkaran/data/` جایگزین کنید → `python docs/rahkaran/tools/gen_taxonomy.py` (نیاز `RAHKARAN_SA_PASSWORD`؛ `15_taxonomy.sql` را می‌سازد) → `apply.py 15 20 30 40 descr` → `build_hints.py` → ingest. موارد مبهم در `docs/rahkaran/TAXONOMY_REVIEW.md` برای حسابدار.

## چک‌لیست
- [ ] SQL view + descriptions + MONEY_COLUMNS + VIEW_HINTS
- [ ] apply + smoke با reader
- [ ] build_hints + ingest + eval
- [ ] نمونه‌سؤال و QUESTIONS.md
- [ ] [../../sql/rahkaran/README.md](../../sql/rahkaran/README.md) (فهرست view ها) به‌روز
- [ ] تست‌های `tests/features/db_connector` سبز
