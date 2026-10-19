# جریان: داده‌ی راهکاران، لایه‌ی `ai`، hintها و refresh

این فایل **چرخه‌ی عمر داده‌ی حسابداری** را توضیح می‌دهد (از `.bak` شرکت تا hint در Postgres). نحوه‌ی پرسش‌وپاسخ: [accounting-query.md](accounting-query.md). افزودن view/hint: [../guides/extend-accounting-layer.md](../guides/extend-accounting-layer.md).

## اجزا
```
data/rahkaran-backups/ (FULL_*.bak, DIFF_*.bak)         ← شرکت می‌ریزد (gitignore)
        │  rahkaran-refresh (sql/rahkaran/refresh.py)
        ▼
SQL Server (mssql) : MehvarGostar  (READ_ONLY)  ←  schema `ai` (84 view) + کاربر rahkaran_ai_reader
        │  python sql/rahkaran/hints/build_hints.py  (خواندن catalogها + examples + notes)
        ▼
sql/rahkaran/hints/out/{hints.jsonl, core_prompt.md, hints_stats.json}   (gitignore! دستی روی سرور)
        │  python -m app.features.db_connector.ingest   (یا POST /accounting-db/hints/ingest)
        ▼
Postgres.schema_hints (embedding + متن)  ← مصرف: db_connector/hints.retrieve_hints
```

## دیتابیس مبدأ
دیتابیس «MehvarGostar» (راهکاران نسل ۳، SQL Server 2022، ~۵GB، collation `Persian_100_CI_AI`) متعلق به «شرکت محور گستر نصر». ۳۴۹۴ جدول که فقط ~۳۹۳ جدول داده دارد؛ فقط **FIN3 (مالی)، HCM3 (منابع انسانی/حقوق)، FAM3 (دارایی ثابت)** + RPA3/GNR3 استفاده واقعی دارند. جزئیات در [../../docs/rahkaran/README.md](../../docs/rahkaran/README.md) و `schema/*.md`، glossaryها (`GLOSSARY_ACCOUNTS/DIMENSIONS/PAYROLL/ENUMS`).

## لایه‌ی `ai` (`sql/rahkaran/*.sql`)
فایل‌ها به ترتیب شماره اجرا می‌شوند (batch با خط `GO`): `00_schema, 10_calendar_lookup, 15_taxonomy, 20_reference, 30_ledger, 40_finance_reports, 50_hr, 60_payroll, 70_assets, 80_meta`. سپس `descriptions.py` توضیح فارسی هر view/ستون را به‌صورت `MS_Description` می‌نویسد (و پوشش را چاپ می‌کند)، و کاربر خواننده ساخته می‌شود.
- ۸۴ view با نام‌های `snake_case` انگلیسی؛ **نام ستون یکسان = معنی یکسان در همه‌ی view ها** (`fiscal_year`, `jalali_ym`, `net_debit`, `contract_dl_code`).
- فهرست کامل view ها با توضیح: [../../sql/rahkaran/README.md](../../sql/rahkaran/README.md).
- طبقه‌بندی حسابدار (`15_taxonomy.sql`، view `ai.account_taxonomy` از فایل Excel حسابدار `docs/rahkaran/data/mehvargostar_code.xlsx` با `docs/rahkaran/tools/gen_taxonomy.py`): سرفصل سود و زیان ← `detail_category` ← معین؛ معین‌های آینه‌ای با تطبیق پسوند/شباهت عنوان `taxonomy_source='derived'` می‌گیرند؛ موارد مبهم در `TAXONOMY_REVIEW.md` برای حسابدار.
- کاربر `rahkaran_ai_reader` (ساخته‌شده در `apply.py` وقتی `RAHKARAN_AI_PASSWORD` ست باشد): `GRANT SELECT ON SCHEMA::ai`. view ها owner=`dbo` هستند و **ownership chaining** اجازه می‌دهد جدول‌های خام FIN3/HCM3 را بخوانند بدون دسترسی مستقیم. جدول خام برای reader بسته است.

### `apply.py`
`python sql/rahkaran/apply.py [prefix…]` (مثلاً `30 40`، یا `descr` فقط برای توضیحات). Env: `RAHKARAN_SA_PASSWORD` (الزامی)، `RAHKARAN_HOST/PORT/DB`، `RAHKARAN_AI_PASSWORD/USER`، `RAHKARAN_SKIP_TF4138=1`.
- idempotent؛ اگر DB `READ_ONLY` است موقتاً `READ_WRITE` می‌کند و برمی‌گرداند.
- `DBCC TRACEON (4138, -1)` (غیرفعال‌سازی row-goal) را سراسری روشن می‌کند؛ با restart SQL Server از بین می‌رود، به همین دلیل executor هم hint را در هر query می‌گذارد.
- **باید بعد از هر ریستور جدید دوباره اجرا شود** (view ها و `ai.calendar_data` با ریستور از بین می‌روند) — `refresh.py` این را خودکار انجام می‌دهد.

## refresh خودکار (`sql/rahkaran/refresh.py` ← سرویس `rahkaran-refresh`)
job یک‌باره؛ روی هر `docker compose up` اجرا می‌شود و idempotent است.
1. `scan()` در `RAHKARAN_BACKUP_LOCAL_DIR` (`/backups`) به‌دنبال `*_FULL_YYYYMMDD_HHMMSS.bak` / `*_DIFF_…` (هر زیرپوشه). نبود FULL = «nothing to do».
2. `choose()`: جدیدترین FULL؛ و جدیدترین DIFF **متعلق به همان FULL** (مقایسه‌ی `DifferentialBaseLSN` DIFF با `CheckpointLSN` FULL با `RESTORE HEADERONLY`). فایل‌های `.trn` نادیده.
3. جدول نشانگر `master.dbo.rahkaran_restore_state` (id=1, signature=`name:size` فایل‌ها). اگر signature برابر و DB ONLINE است و `--force` نیست → «already up to date».
4. `--dry-run` فقط گزارش می‌دهد.
5. بازیابی در دیتابیس جانبی `<DB>_new` با `MOVE` فایل‌های logical به `/var/opt/mssql/data/<DB>_<stamp>_<i>.mdf|ldf` (FULL با NORECOVERY سپس DIFF با RECOVERY).
6. `apply.py` روی `<DB>_new` (subprocess، env `RAHKARAN_DB=<DB>_new`) + smoke test: `COUNT(*) FROM ai.view_catalog` و `TOP 1 FROM ai.data_freshness`.
7. هر شکست قبل از swap → `<DB>_new` حذف و **DB زنده دست‌نخورده**.
8. swap (تنها لحظه‌ی قطعی چند ثانیه‌ای): DB فعلی (اگر READ_ONLY → ابتدا READ_WRITE) SINGLE_USER و rename به `<DB>_old`؛ `<DB>_new` → `<DB>`; MULTI_USER؛ در صورت `RAHKARAN_SET_READ_ONLY=1` (پیش‌فرض) READ_ONLY؛ حذف `_old`. شکست swap → rollback به نام قبلی.
9. به‌روزرسانی signature؛ پیام `done - the new data is live`.
نیاز: فضای دیسک برای دو نسخه هم‌زمان؛ FULL و DIFF از یک زنجیره‌ی backup. روی SQL Server Express محدودیت ۱۰GB هر DB (DB فعلی ~۵GB). آزمایش‌شده با FULL 2026-10-02 + DIFF 2026-10-05 (~۱۰ثانیه روی SSD).
در compose: سرویس با تصویر backend ساخته می‌شود (entrypoint `python sql/rahkaran/refresh.py`)؛ env: `RAHKARAN_SA_PASSWORD`, `RAHKARAN_AI_PASSWORD`(=`RAHKARAN_DB_PASSWORD`), `RAHKARAN_HOST=mssql`, `RAHKARAN_PORT=1433`, `RAHKARAN_DB`. پوشه‌ی بک‌آپ `${RAHKARAN_BACKUP_DIR:-./data/rahkaran-backups}` در هر دو کانتینر `mssql` و refresh به‌صورت read-only روی `/backups` mount است؛ فایل‌ها باید برای همه خواندنی باشند (`chmod -R a+rX`).

## ساخت hint ها (`sql/rahkaran/hints/`)
- `notes.py`: دانش دست‌نویس — `CORE_PROMPT` (قواعد همیشه‌فعال)، `VIEW_HINTS[view]={keywords,use,filters,pitfalls}`، `DOMAIN_NOTES=[(id,title,text,keywords)]`.
- `../examples/questions.py`: `Q=[(group, سؤال فارسی, SQL)]` — ۶۷+ سؤال نمونه (few-shot و مجموعه‌ی ارزیابی).
- `build_hints.py` (با `RAHKARAN_AI_PASSWORD`، خواندن از `ai.view_catalog/column_catalog/glossary/account_taxonomy`): تولید `out/hints.jsonl` (هر خط `{id,kind,title,text,views,keywords}`)، `core_prompt.md`، `hints_stats.json`. انواع: `view` (هر view تا ۲۸ ستون در هر chunk + توضیح + نمونه پرسش‌ها)، `example`، `glossary`، `note`، `taxonomy` (یک chunk برای هر دسته‌ی تحلیلی + chunk فهرست `taxonomy:000`).
- `eval_retrieval.py [k]` / `eval_set.py`: ارزیابی واژگانی (BM25) بازیابی؛ ~۹۶٪ روی نمونه‌ها در k=6 (leave-one-out)، ۵۰ سؤال بازنویسی‌شده ۱۰۰٪ ولی خوش‌بینانه (کلیدواژه‌ها بعد از دیدن خطا تنظیم شده‌اند). بعد از جمع‌آوری سؤال‌های واقعی باید جایگزین شود.
- `examples/run.py`: همه‌ی نمونه‌ها را با reader اجرا، زمان/خطا چاپ می‌کند و در صورت `RAHKARAN_QUESTIONS_OUT` فایل `docs/rahkaran/QUESTIONS.md` را بازتولید می‌کند.

### ingest در Postgres (`hints.ingest_hints`, CLI: `python -m app.features.db_connector.ingest`)
- upsert بر اساس `hint_key`؛ `content_hash = sha256(model+title+text)`؛ بدون تغییر و با embedding موجود = `unchanged`.
- تغییرکرده/جدید در دسته‌های ۳۲تایی embed می‌شود؛ اگر embedding API در دسترس نباشد chunk **بدون بردار** ذخیره می‌شود (بازیابی واژگانی کار می‌کند) و `stored_without_embedding` شمرده می‌شود.
- hintهایی که دیگر در corpus نیستند حذف می‌شوند؛ cache حافظه‌ی process با `invalidate_cache()` ابطال می‌شود (⚠️ **فقط در همان process**؛ بقیه‌ی instance ها تا ۳۰۰ث قدیمی می‌مانند).
- `POST /accounting-db/hints/ingest` (admin) همین کار را داخل یک درخواست HTTP انجام می‌دهد (ممکن است timeout شود؛ CLI ترجیح دارد).
- `out/` در git نیست (الگوی `out/` در `.gitignore`) و در `.dockerignore` نیست؛ باید قبل از build روی سرور موجود باشد تا داخل image بیاید، و بعد از هر تغییر `ingest` دوباره زده شود.

## چرخه‌ی کامل پس از تغییر دانش
| تغییر | دستورها |
|---|---|
| backup جدید شرکت | فایل‌ها را در `data/rahkaran-backups/` بریزید → `dc up -d` (یا `run --rm rahkaran-refresh`) |
| view/ستون جدید یا ویرایش `*.sql` | `apply.py [prefix…] descr` → `build_hints.py` → ingest |
| ویرایش `notes.py`/`questions.py`/`descriptions.py` | `build_hints.py` → ingest |
| ویرایش فایل Excel حسابدار | `gen_taxonomy.py` → `apply.py 15 20 30 40 descr` → `build_hints.py` → ingest |

## حساسیت داده
`ai.parties`, `ai.employees`, `ai.employee_bank_accounts` شامل کد ملی/شبا/موبایل/حقوق‌اند و هیچ ماسکی روی خروجی اعمال نمی‌شود؛ نتیجه‌ی query (ردیف‌ها) به LLM provider خارجی فرستاده می‌شود. ← [../known-issues.md](../known-issues.md).
