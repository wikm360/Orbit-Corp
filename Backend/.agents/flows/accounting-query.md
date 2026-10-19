# جریان: پرسش مالی از دیتابیس راهکاران (Text-to-SQL)

پیچیده‌ترین قابلیت پروژه. فایل‌ها: `features/db_connector/*` و `features/agent/tools/accounting_tools.py`؛ دادهٔ دانش: `sql/rahkaran/**`. دانش دامنه: [../../docs/rahkaran/README.md](../../docs/rahkaran/README.md).

## تصویر کلی
```
کاربر: «هزینه‌ی حقوق قرارداد X در ۱۴۰۴ چقدر بود؟»
   │ agent تصمیم می‌گیرد ابزار ask_accounting_db(question) را (یک‌بار) صدا بزند
   ▼
run_accounting_query(db, question, user_id, conversation_id)
  1) retrieve_hints   : BM25 + بردار (RRF) روی schema_hints → بلوک‌های دانش
  2) حلقه‌ی ≤ N بار (RAHKARAN_SQL_MAX_ATTEMPTS=3):
       generate  → LLM مدل SQL (core_prompt + hints + پرسش + تلاش‌های قبلی با خطا)
       extract_sql (یا NO_SQL → CannotAnswer)
       validate_sql → sqlglot AST (فقط یک SELECT روی ai.*)
       execute_query → SQL Server با کاربر فقط‌خواندنی، سقف ردیف/زمان
       اگر 0 ردیف و فیلتر متنی داشت → یک بار با «مقادیر واقعی ستون» دوباره
  3) compute_totals   : شمارش کل و جمع ستون‌های مبلغ اگر نتیجه ناقص دیده می‌شود
  4) DbQueryLog       : ثبت پرسش/SQL/وضعیت/زمان
  5) format + artifact: متن برای مدل (Markdown) + artifact برای UI
   ▼
مدل پاسخ کوتاه فارسی می‌نویسد؛ UI زیر پیام SQL و جدول کامل را از artifact نشان می‌دهد
```

## ابزار agent
`AskAccountingDbTool` (`agent/tools/accounting_tools.py`): پارامتر `question` (فارسی، خودبسنده). `include_sql_in_text=False` ← متن مدل SQL ندارد و با `MODEL_NOTE` شروع می‌شود (راهنمای نقل اعداد/عدم ساختن عدد). خروجی: `ToolExecutionResult(text, artifacts=[artifact])`.
فقط وقتی `RAHKARAN_DB_ENABLED=true` ثبت می‌شود. ⚠️ هیچ چک نقش/allow-list/سهمیه‌ای در ابزار یا registry نیست.

## ۱. بازیابی hint (`hints.py`)
**ورودی دانش** = `sql/rahkaran/hints/out/{hints.jsonl, core_prompt.md}` (در git نیست — ← [accounting-data-refresh.md](accounting-data-refresh.md)). `ingest_hints` آن را در `schema_hints` می‌ریزد.

`retrieve_hints(db, question, top_k=RAHKARAN_HINTS_TOP_K=8)`:
1. `_load_hints`: همه‌ی hintها (فقط ستون‌های متنی) + ساخت `Bm25Index`؛ **cache در حافظه‌ی process با TTL ۳۰۰ث**. اگر جدول خالی است از فایل jsonl می‌خواند (فقط واژگانی؛ warning).
2. رتبه‌ی واژگانی (`lexical.Bm25Index`): ۳۰ مورد برتر.
3. رتبه‌ی برداری: embedding پرسش (cache ۲۵۶ ورودی/۱ ساعت) و `cosine_distance` روی `schema_hints.embedding IS NOT NULL`، ۳۰ مورد. اگر embedding شکست خورد → فقط واژگانی (warning).
4. ادغام با **RRF** (`1/(60+rank+1)`).
5. انتخاب با سقف per-kind: `view:4, example:2, note:2, glossary:2, taxonomy:2` و کل ≤ top_k.
6. برای هر view انتخاب‌شده، سایر بخش‌های ستون‌های همان view (`view:<name>:<n>`) هم اضافه می‌شود.
7. سقف طول prompt ≈ ۲۲٬۰۰۰ نویسه (`_MAX_PROMPT_CHARS`).
خروجی: `RetrievedHints(keys, blocks)`.

`lexical.py`: BM25 خودکفا با توکن‌های کلمه + 4-gram نویسه (تحمل غلط املایی، نیم‌فاصله، «ي/ك» عربی، ارقام فارسی/عربی)؛ stopword فارسی؛ `boosts` (عنوان+کلمات کلیدی ×۲).

## ۲. تولید SQL (`generator.py`)
- `build_messages`: system = `core_prompt.md` + قواعد فرمت خروجی + «دانش بازیابی‌شده»؛ user = `پرسش: …`؛ برای هر تلاش قبلی جفت (assistant: ```sql…```، user: «این SQL خطا داد: … SQL اصلاح‌شده را بنویس»). اگر تلاش قبلی `raw` داشته باشد (مثلاً NO_SQL) همان پخش می‌شود.
- مدل: `get_sql_llm_provider()` (`LLM_SQL_MODEL` یا `LLM_MODEL`).
- `extract_sql`: اگر خروجی با `NO_SQL:` شروع شود → `CannotAnswer(reason)`؛ وگرنه بلوک ```sql (یا کل متن).
- قاعده‌ی خروجی: فقط یک `SELECT` T-SQL داخل بلوک sql.

## ۳. اعتبارسنج استاتیک (`sql_validator.py`) — لایه‌ی دفاعی اصلی
ترتیب بررسی (`validate_sql`):
1. خالی نبودن؛ طول ≤ ۸۰۰۰ نویسه.
2. حذف کامنت‌ها بدون آسیب به literal/identifier (`strip_comments`) و حذف `;` انتهایی.
3. literalها خالی می‌شوند (تا متن فارسی داخل LIKE باعث رد نشود)؛ `;` میانی → رد.
4. کلمات ممنوع (regex): `openrowset, opendatasource, openquery, openxml, xp_*, sp_*, fn_*, dbcc, waitfor, bulk, shutdown, exec, execute, declare, kill, backup, restore, reconfigure, grant, revoke, deny, option, tablesample`. (`option` ممنوع است چون hint را خود executor اضافه می‌کند.)
5. پیشوند سیستمی `sys. information_schema. master. msdb. tempdb. model.` ممنوع.
6. parse با `sqlglot` (dialect `tsql`)؛ باید دقیقاً **یک** statement از نوع `exp.Query` (SELECT/UNION/CTE) باشد؛ گره‌های `Insert/Update/Delete/Drop/Create/Alter/Merge/Truncate/Command/Use/Set/Into/Transaction/Commit/Rollback/Grant` ممنوع.
7. هر `Table` باید schema `ai` داشته باشد (یا نام یک CTE باشد)؛ cross-database و table-valued function ممنوع؛ حداقل یک view `ai.*`.
خطاها پیام انگلیسی قابل‌اقدام برای مدل هستند (`SqlValidationError`) و به‌عنوان بازخورد تعمیر برمی‌گردند.
شکاف‌های شناخته‌شده: `SELECT @@version/SUSER_NAME()/DB_NAME()` و سقف `CROSS JOIN` مسدود نیست (← known-issues).

## ۴. اجرا (`executor.py`)
- اتصال `pymssql` با کاربر `RAHKARAN_DB_USER` (فقط `SELECT` روی schema `ai`)، `login_timeout=15`, `timeout=RAHKARAN_DB_QUERY_TIMEOUT_SECONDS`(۶۰), `autocommit`.
- در thread (`asyncio.to_thread`) چون pymssql sync است. هر query اتصال جدید باز و می‌بندد (بدون pool).
- `SET ROWCOUNT (max_rows+1)` سپس `<sql>\nOPTION (USE HINT('DISABLE_OPTIMIZER_ROWGOAL'))` (جلوگیری از planهای فاجعه‌بار nested-loop برای `TOP n … ORDER BY`؛ trace flag 4138 هم در `apply.py` سراسری فعال می‌شود ولی با restart سرور از بین می‌رود). `max_rows` = `RAHKARAN_DB_MAX_ROWS`=۵۰۰؛ ردیف اضافه برای تشخیص `truncated`.
- مقادیر JSON-safe: Decimal→int/float، تاریخ→ISO، bytes→`<N bytes>`، UUID→str.
- خطاها → `DbExecutionError(message, timeout)` (متن خوانا از pymssql).
- `data_freshness()`: `SELECT item,value FROM ai.data_freshness` با cache ۶۰۰ث؛ هرگز استثنا نمی‌دهد.
هیچ semaphore/محدودیت هم‌زمانی روی اجرای SQL نیست.

## ۵. حلقه‌ی تعمیر (`service.run_accounting_query`)
- `CannotAnswer` در تلاش اول (اگر `max_attempts>1`): به‌جای تسلیم، یک `Attempt(raw="NO_SQL: …", error=_REFUSAL_CHALLENGE)` اضافه می‌شود تا مدل با پیش‌فرض‌های معقول (آخرین ماه/سال، همه‌ی ردیف‌ها) SQL بنویسد. اگر باز `NO_SQL` داد → log با **status=OK** و `error_message="unanswerable: …"` و متنی که به مدل می‌گوید صادقانه اعلام کند «کوئری ساخته نشد» (نه «داده نیست»).
- خطای تولید (استثنا) ← تلاش بعد؛ `SqlValidationError` ← `status=REJECTED` و تلاش بعد؛ `DbExecutionError` ← `status=ERROR` و تلاش بعد.
- **صفر ردیف**: اگر هنوز تلاش باقی است و فیلتر متنی (`=`, `LIKE`, `IN` با literal رشته‌ای روی ستون view های `ai.`) وجود دارد، `empty_result_feedback` تا ۳ ستون فیلتر را با `SELECT DISTINCT TOP 40` کاوش می‌کند و مقادیر واقعی را به مدل می‌دهد («احتمالاً مقدار فیلتر نیست، نه اینکه داده نباشد»). یک بار؛ اگر تلاش بعد هم نتیجه نداد همان اولین نتیجه‌ی خالی گزارش می‌شود (OK با ۰ ردیف).
- پایان بدون نتیجه: متن خطای عمومی فارسی با `علت` (⚠️ علت خام خطای SQL Server/مدل است) و شناسه‌ی پیگیری.

## ۶. جمع‌ها (`summary.py`)
مدل و UI فقط بخشی از ردیف‌ها را می‌بینند (`RAHKARAN_DB_ROWS_TO_MODEL`=۶۰ برای مدل؛ `RAHKARAN_ARTIFACT_MAX_ROWS`=۱۰۰ برای UI)، پس برای جلوگیری از ساخت عدد توسط مدل:
- اگر نتیجه کامل واکشی شده (`truncated=False`) و >۶۰ ردیف: `total_rows` و جمع ستون‌های مبلغ در پایتون محاسبه می‌شود.
- اگر `truncated`: `build_totals_sql` عبارت را (با حذف ORDER BY و حفظ CTE) داخل `SELECT COUNT(*), SUM(CAST(col AS DECIMAL(38,2))) FROM (…) q` می‌پیچد؛ برای UNION یا `TOP` ممکن نیست (`total_rows=None` یعنی «بیش از N»).
- ستون‌های مبلغ از `artifacts.column_kind` (حداکثر ۶ ستون).

## ۷. قالب‌بندی (`formatter.py`) و artifact (`artifacts.py`)
- `format_query_result` متن Markdown برای مدل: جدول (تا ۶۰ ردیف) با `format_cell`؛ هشدار `⚠️ مهم` با تعداد کل و جمع ستون‌ها وقتی ناقص است؛ فراداده‌ی اجرا (زمان، تعداد ردیف، `query_id`)؛ «وضعیت تازگی داده» از `data_freshness`. مبالغ ستون‌های «پولی» (`is_money_column` با الگوهای نام) به `ریال (… تومان / میلیون تومان / میلیارد تومان)` فرمت می‌شوند.
- `build_sql_result_artifact` → dict برای UI و ذخیره در `messages.artifacts`:
  ```json
  {"type":"sql_result","version":1,"query_id":"…","question":"…","sql":"…",
   "columns":[{"name":"…","kind":"money|ratio|number|date|text"}],
   "rows":[[…]],"row_count":N,"rows_fetched":M,"rows_shown":K,"total_exact":bool,
   "truncated":bool,"duration_ms":int,"executed_at":"ISO","data_as_of":{…},"currency":"IRR"}
  ```
  `column_kind` ترکیبی از: فهرست صریح `MONEY_COLUMNS` (تولید از `descriptions.py` ستون‌هایی که توضیحشان «(ریال)» دارد)، regexهای فارسی/انگلیسی (نسبت/درصد/تعداد/تاریخ/شناسه/سال‌ماه)، و توکن‌های مبلغ. ⚠️ دو منطق مبلغ‌شناسی موازی وجود دارد: `formatter.is_money_column` (برای متن مدل) و `artifacts.column_kind` (برای UI)؛ ممکن است اختلاف داشته باشند.
- `money_columns.py` را وقتی ستون ریالی جدیدی به view ها اضافه می‌شود بازتولید/ویرایش کنید.

## ۸. لاگ و بازخورد
هر اجرا یک `DbQueryLog` می‌سازد. endpointهای `/accounting-db/*` در [../reference/api-endpoints.md](../reference/api-endpoints.md).
- `POST /queries/{id}/feedback` `{feedback: -1|0|1, note?}` — فقط صاحب log یا admin (`_get_owned_log`).
- `GET /queries/{id}/export?format=xlsx|csv` — **SQL ذخیره‌شده دوباره اعتبارسنجی و اجرا می‌شود** تا سقف `RAHKARAN_EXPORT_MAX_ROWS`=۵۰۰۰. Excel: RTL، هدر رنگی، freeze؛ CSV با BOM. محافظ formula-injection: مقدار متنی که با `= + @ \t \r` شروع شود با `'` پیشوند می‌گیرد.
- admin: `GET /queries` (فیلتر status, صفحه‌بندی), `GET /queries/stats`, `POST /hints/ingest`.
- `GET /accounting-db/freshness`: هر کاربر لاگین‌شده.

## پیکربندی مرتبط
`RAHKARAN_DB_ENABLED, _HOST, _PORT, _NAME, _USER, _PASSWORD, _QUERY_TIMEOUT_SECONDS, _MAX_ROWS, _ROWS_TO_MODEL`, `RAHKARAN_SQL_MAX_ATTEMPTS`, `RAHKARAN_HINTS_TOP_K`, `RAHKARAN_ARTIFACT_MAX_ROWS`, `RAHKARAN_EXPORT_MAX_ROWS`, `LLM_SQL_MODEL` — ← [../reference/configuration.md](../reference/configuration.md).

## تست‌ها
`tests/features/db_connector/`: `test_sql_validator` (اعتبارسنج)، `test_generator`، `test_hints`، `test_lexical`، `test_summary`، `test_formatter`، `test_artifacts`، `test_service_and_executor`، `test_agent_accounting_tool`، `test_router` (۴۱ تست). SQL Server در تست‌ها stub می‌شود؛ هیچ تستی به SQL Server واقعی وصل نیست.
