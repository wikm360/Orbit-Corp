# Runbook — کارهای روزمره و troubleshooting

همه‌ی دستورها داخل `Backend/` روی سرور. فرض: `alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'` (روی dev به‌جای `dc` از `docker compose` ساده استفاده کنید).
زمینه‌ی کامل: [infra-and-deploy.md](infra-and-deploy.md).

## آپدیت کد
```bash
git pull
dc up -d --build           # migrate خودکار اجرا می‌شود؛ backend/worker بازسازی می‌شوند
```
اگر `sql/rahkaran/hints/out/` عوض شده (یا `notes.py`/`questions.py` و `build_hints.py` دوباره اجرا شده): فایل‌ها را جایگزین کنید، `dc up -d --build backend worker`، سپس
`dc exec backend python -m app.features.db_connector.ingest`.

> migration `0008_chunk_lexical_search` جدول `document_chunks` را یک‌بار بازنویسی می‌کند (ستون generated + دو ایندکس GIN) و `search_text` را دسته‌ای backfill می‌کند؛ روی پایگاه بزرگ در ساعت کم‌تردد اجرا کنید. افزونه‌ی `pg_trgm` در image `pgvector/pgvector` هست و migration آن را می‌سازد (نیاز به دسترسی ساخت extension).

## آپدیت دیتابیس حسابداری (خروجی جدید شرکت)
1. `FULL_*.bak` / `DIFF_*.bak` جدید را در `data/rahkaran-backups/` بریزید (زیرپوشه‌ها مهم نیستند؛ قدیمی‌ها ماندنشان مشکلی ندارد).
2. `chmod -R a+rX data/rahkaran-backups`
3. `dc up -d` (یا `dc run --rm rahkaran-refresh`) و `dc logs rahkaran-refresh`.
گزینه‌ها: `dc run --rm rahkaran-refresh --dry-run` / `--force`. اگر خطا بدهد DB قبلی سالم می‌ماند. چند ثانیه قطعی هنگام swap. جزئیات: [../flows/accounting-data-refresh.md](../flows/accounting-data-refresh.md).
بعد از آپدیت داده لازم نیست hint ها دوباره ingest شوند مگر ساختار view ها عوض شده باشد.

## وضعیت و لاگ
```bash
dc ps
dc logs -f backend            # یا worker, caddy, frontend, mssql, rahkaran-refresh
dc logs worker | grep 'OCR orientation'   # مسیر تصمیم تشخیص جهت هر تصویر (OSD/مدل/نتیجه)
dc restart backend worker
dc up -d --build backend      # بازسازی فقط یک سرویس
```
نام کانتینر mssql در prod: `backend-mssql-1` (در dev: `rahkaran-mssql`).

## بک‌آپ
```bash
dc exec -T postgres pg_dump -U postgres org_rag | gzip > pg_$(date +%F).sql.gz   # کاربران/چت‌ها/اسناد(متادیتا)/hint
```
خارج از سرور نگه دارید. فایل‌های اسناد در volume `uploads_data` (`/app/data/uploads`) هستند و در `pg_dump` نیستند؛ جداگانه backup بگیرید. دیتابیس راهکاران از `.bak` شرکت قابل بازسازی است.

## دسترسی مستقیم به SQL Server در prod (نگهداری)
پورت میزبان ندارد. یا `dc exec mssql /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P …` یا برای پنجره‌ی نگهداری یک override موقت `127.0.0.1:14330:1433` (بعد از کار حذف شود). کانتینر prod: `backend-mssql-1`.

## تغییر مدل embedding (re-embed)
بردارهای مدل‌های مختلف قابل‌مقایسه نیستند؛ بعد از تغییر `EMBEDDING_MODEL` (یا `EMBEDDING_SEND_DIMENSIONS`) باید همه‌چیز دوباره embed شود:
```bash
# مسیر فایل روی chunkهای قدیمی (فقط metadata/search_text؛ بدون هزینه‌ی OCR/embedding؛ idempotent)
dc exec backend python -m app.features.documents.backfill_chunk_paths
dc exec backend python -m app.features.documents.reembed --dry-run      # فقط شمارش
dc exec backend python -m app.features.documents.reembed                # اسناد READY با embedding_model متفاوت + حافظه‌ی پروژه‌ها
dc exec backend python -m app.features.db_connector.ingest              # hint های SQL (با تغییر مدل خودکار دوباره embed می‌شوند)
```
هر سند جدا commit می‌شود؛ اجرای نیمه‌کاره را می‌شود دوباره زد. ابعاد خروجی باید با `EMBEDDING_DIMENSIONS` (ستون vector) یکی باشد (برای `text-embedding-3-large` با `EMBEDDING_SEND_DIMENSIONS=true` و `EMBEDDING_DIMENSIONS=1536`). در حین اجرا نتایج جست‌وجو ترکیبی از مدل قدیم و جدید است؛ در ساعت کم‌تردد اجرا کنید.

## ایجاد ادمین/کاربر
اولین `POST /auth/register` روی دیتابیس خالی super_admin می‌سازد. بقیه ثبت‌نام می‌کنند و super_admin نقش را با `PATCH /admin/users/{id}/role` تغییر می‌دهد. (بعد از بستن ثبت‌نام عمومی، endpoint ساخت کاربر وجود ندارد؛ ← known-issues.)

## ingest دستی hint ها
`dc exec backend python -m app.features.db_connector.ingest` (ترجیح بر endpoint admin).

## Migration دستی
`dc exec backend alembic upgrade head` (یا در dev: `alembic upgrade head`). قواعد: [../guides/add-migration.md](../guides/add-migration.md).

## مشکلات رایج
| علامت | علت / راه‌حل |
|---|---|
| `dc up` خطای `set POSTGRES_PASSWORD…` | متغیر در `.env` خالی است |
| `rahkaran-refresh`: `no FULL backup found` | فایل‌ها در `data/rahkaran-backups/` نیستند یا نام `..._FULL_YYYYMMDD_HHMMSS.bak` ندارند |
| refresh: خطای دسترسی فایل | `chmod -R a+rX data/rahkaran-backups` |
| refresh: `SQL Server not reachable` | mssql هنوز بالا نیامده (start_period ۹۰ثانیه)؛ ۱–۲ دقیقه بعد `dc run --rm rahkaran-refresh` |
| چت مالی «ابزار در دسترس نیست»/خطا | `RAHKARAN_DB_ENABLED=true`؟ پس از تغییر env backend را restart کردید؟ `dc logs backend`؛ ingest hint ها انجام شده؟ رمز reader درست؟ (اگر `schema_hints` خالی باشد به فایل jsonl برمی‌گردد؛ اگر `out/` هم نیست خطا) |
| پرسش مالی: «سیستم کوئری نساخت» | مدل `NO_SQL` داده؛ پرسش را دقیق‌تر (ماه/سال/نام مرکز هزینه) بنویسید؛ در `db_query_logs.error_message` (`unanswerable: …`) ببینید |
| رمز Postgres را عوض کردم و وصل نمی‌شود | رمز فقط روی volume خالی اعمال می‌شود؛ `ALTER USER` |
| مرورگر خطای گواهی | `root.crt` نصب نیست یا `SITE_ADDRESS` با آدرس مرورگر یکی نیست |
| سند همیشه `processing` | worker بالا نیست؟ (`dc ps`, `dc logs worker`)، Redis؟ job کشته‌شده (OOM/timeout ۶۰۰ث)؟ سند را FAILED کنید یا حذف/دوباره آپلود کنید |
| سند `failed` با 429/ECONNRESET | محدودیت embedding API؛ `POST …/documents/{id}/retry`؛ `WORKER_REPLICAS` را کم کنید |
| پاسخ‌های گروه نمی‌رسد | Redis؟ WS با `?token=` معتبر؟ در Caddy WebSocket پشتیبانی می‌شود (reverse_proxy پیش‌فرض) ولی لاگ proxy توکن را می‌بیند |
| بعد از restore داده، `ai` view ندارد | `rahkaran-refresh` خودکار apply می‌کند؛ دستی: `RAHKARAN_SA_PASSWORD=… python sql/rahkaran/apply.py` |
| `Permission denied` روی آپلود در dev | volume قدیمی با root ساخته شده؛ `chown 10001:10001` |

## اجرای محلی بدون Docker
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload            # API
python -m workers.ingestion_worker       # worker
```
برای OCR PDF اسکن‌شده `pdftoppm` (poppler-utils) نصب باشد.


## هزینه‌ی prompt و prefix cache
لاگ `[LLM:USAGE] model=… prompt=… cached=… completion=…` برای هر فراخوانی چت (استریم با `include_usage`). `cached` بزرگ‌تر از صفر یعنی prefix (ابزارها + system) از کش خوانده شده؛ روی gapgpt اندازه‌گیری شد: فراخوانی دوم به بعد ≈۹۹٪ prefix کش و هزینه‌ی ورودی ≈۱۰ برابر کمتر. ستون «توکن ورودی» پنل gapgpt برای درخواست‌های کش‌خورده `prompt+cached` نشان می‌دهد (دوبار شمرده)؛ معیار درست ستون هزینه است. هر چیز متغیر باید بعد از بخش ثابت prompt بیاید وگرنه کش می‌پرد.
