# راه‌اندازی محیط توسعه (روی سیستم خودتان)

راهنمای اجرای بک‌اند، worker، دیتابیس‌ها و فرانت روی لپ‌تاپ/دسکتاپ برای توسعه و تست. deploy روی سرور: [DEPLOY.md](DEPLOY.md). مستندات فنی: [.agents/README.md](.agents/README.md).

> همهٔ دستورها داخل `Backend/` هستند مگر ذکر شده. در dev از `docker compose` ساده استفاده می‌شود (فایل `docker-compose.override.yml` خودکار لود می‌شود).

## ۱. پیش‌نیازها

| مورد | توضیح |
|---|---|
| Docker + Docker Compose v2 | برای Postgres، Redis، SQL Server (و اختیاری خود اپ) |
| Python 3.12+ | فقط اگر اپ را بیرون از Docker اجرا می‌کنید (image از 3.12 استفاده می‌کند) |
| Node 20 + npm | برای فرانت (`../Frontend`) |
| `poppler-utils` | برای OCR صفحات PDF اسکن‌شده/خراب (`sudo apt install poppler-utils`)؛ بدون آن رندر صفحه کار نمی‌کند |
| دسترسی اینترنت | کلید و endpoint مدل چت و embedding؛ دانلود اولیهٔ encoding کتابخانهٔ `tiktoken` |
| RAM | اگر SQL Server را بالا می‌آورید ≥ ۱۶GB (کانتینر تا ۸GB حافظه می‌گیرد) |

## ۲. دو روش اجرا

| | روش A — همه‌چیز در Docker | روش B — زیرساخت در Docker، اپ روی سیستم (برای دیباگ) |
|---|---|---|
| backend / worker | کانتینر | `uvicorn --reload` و `python -m workers…` در venv |
| تغییر کد | `docker compose up -d --build backend worker` | فوری (hot reload) |
| مناسب برای | تست نزدیک به production | توسعهٔ روزمره، breakpoint، pytest |

### مشترک: ساخت `.env`
```bash
cp .env.example .env
```
مقادیر حداقلی که **همیشه** باید پر باشند (compose حتی برای `up postgres redis` همهٔ فایل را interpolate می‌کند و اگر خالی باشند خطا می‌دهد):
```
POSTGRES_PASSWORD=dev-postgres          # هر رشته‌ای برای dev
RAHKARAN_SA_PASSWORD=Dev-Passw0rd!      # پیچیده: بزرگ+کوچک+عدد+نماد، ≥8
RAHKARAN_DB_PASSWORD=dev-reader
```
و برای عملکرد AI:
```
LLM_API_BASE_URL=...   LLM_API_KEY=...   LLM_MODEL=...
EMBEDDING_API_BASE_URL=...   EMBEDDING_API_KEY=...   EMBEDDING_MODEL=...   EMBEDDING_DIMENSIONS=1536
JWT_SECRET_KEY=dev-secret
```
- `DATABASE_URL` و `REDIS_URL` در روش A توسط compose روی شبکهٔ داخلی بازنویسی می‌شوند؛ در روش B باید به `localhost` اشاره کنند (پیش‌فرض‌های `.env.example`).
- `RAHKARAN_DB_ENABLED=false` (پیش‌فرض) تا وقتی دیتابیس راهکاران را راه نینداخته‌اید.
- `.env` در git نیست؛ commit نکنید.

### روش A — همه‌چیز در Docker
```bash
docker compose up -d --build         # postgres, redis, migrate, backend, worker×3, mssql, rahkaran-refresh
docker compose ps
docker compose logs -f backend worker
```
- API روی `http://127.0.0.1:8000` (Swagger: `/docs`)، Redis روی `127.0.0.1:6379`، SQL Server روی `127.0.0.1:14330`. Postgres **پورت میزبان ندارد**.
- در dev یک worker کافی است: `WORKER_REPLICAS=1` در `.env`.
- اگر mssql/راهکاران را نمی‌خواهید: `docker compose up -d --build postgres redis migrate backend worker`.
- برای اولین بار volume راهکاران را بسازید: `docker volume create rahkaran_mssql_data`.

### روش B — زیرساخت در Docker، اپ روی سیستم
Postgres پورت میزبان ندارد؛ یک فایل محلی (در git نیست؛ نامش را نگه دارید یا در `.git/info/exclude` بگذارید) بسازید:
```yaml
# docker-compose.local.yml
services:
  postgres:
    ports: ["127.0.0.1:5432:5432"]
```
```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.local.yml up -d postgres redis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload                 # terminal 1: API روی :8000
python -m workers.ingestion_worker            # terminal 2: worker ingestion
```
`DATABASE_URL=postgresql+asyncpg://postgres:<POSTGRES_PASSWORD>@localhost:5432/org_rag` و `REDIS_URL=redis://localhost:6379/0` باید در `.env` باشند.
(نکته: `docker-compose.override.yml` Redis را روی `127.0.0.1:6379` باز می‌کند.)

## ۳. فرانت‌اند
```bash
cd ../Frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1' > .env.local   # اگر ندارید
npm run dev                                                           # http://localhost:3000
```
`CORS_ORIGINS` بک‌اند به‌طور پیش‌فرض `http://localhost:3000` را دارد. توکن فراخوانی AI (`@bot`) با `AI_TRIGGER_TOKEN` (بک‌اند) و `NEXT_PUBLIC_AI_TRIGGER_TOKEN` (فرانت) باید یکی باشد. تست‌های فرانت: `npm test`.

## ۴. اولین استفاده
1. `http://localhost:3000` → ثبت‌نام. **اولین کاربر `super_admin` می‌شود.**
2. در پنل: تیم بسازید، یک نفر را leader کنید، پروژه بسازید، عضو اضافه کنید، سند آپلود کنید (PDF/DOCX/PPTX/XLSX/TXT/تصویر).
3. سند ابتدا `processing` است؛ با بالا بودن worker و Redis به `ready` می‌رسد (`docker compose logs -f worker`).
4. چت کنید؛ در چت گروهی با `@bot` سؤال بپرسید.

## ۵. دیتابیس راهکاران (اختیاری؛ فقط برای قابلیت مالی)

۱. فایل‌های `FULL_*.bak` و `DIFF_*.bak` را در `data/rahkaran-backups/` بگذارید (`chmod -R a+rX data/rahkaran-backups`).
۲. `.env`: `RAHKARAN_DB_ENABLED=true`، `RAHKARAN_DB_HOST=mssql` (روش A) یا `127.0.0.1` با `RAHKARAN_DB_PORT=14330` (روش B)، و رمزها.
۳. ریستور و اعمال لایهٔ `ai` (خودکار، idempotent):
```bash
docker compose up -d mssql
docker compose run --rm rahkaran-refresh          # --dry-run / --force هم دارد
```
۴. hint ها (فایل‌های `sql/rahkaran/hints/out/` داخل git هستند):
```bash
docker compose exec backend python -m app.features.db_connector.ingest        # روش A
python -m app.features.db_connector.ingest                                    # روش B
```
۵. backend را restart کنید (ابزار `ask_accounting_db` هنگام استارت ثبت می‌شود).

توسعهٔ view ها/hintها: [.agents/guides/extend-accounting-layer.md](.agents/guides/extend-accounting-layer.md) (`sql/rahkaran/apply.py`، `hints/build_hints.py`).

## ۶. تست
```bash
# Postgres با pgvector + pg_trgm و Redis لازم است
docker compose up -d postgres redis
pytest                       # DB تست جدا: <نام DB>_test؛ روی DB دیگر خودداری می‌کند
pytest tests/features/retrieval -q
pytest -k refresh_tokens
```
- روش B: پورت Postgres را با `docker-compose.local.yml` باز کنید (بالا).
- روش A (Postgres بدون پورت): `TEST_DATABASE_URL=postgresql+asyncpg://postgres:<رمز>@<IP کانتینر postgres>:5432/org_rag_test` (IP را با `docker inspect backend-postgres-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'` بگیرید) و `REDIS_URL=redis://127.0.0.1:6379/0`.
- هیچ تستی به LLM/Embedding/SQL Server واقعی وصل نمی‌شود (stub). جزئیات: [.agents/ops/testing.md](.agents/ops/testing.md).
- ارزیابی کیفیت جست‌وجو روی فایل‌های واقعی: [tools/retrieval_eval/README.md](tools/retrieval_eval/README.md).

## ۷. کار با دیتابیس و migration
```bash
alembic upgrade head                       # اعمال
alembic revision --autogenerate -m "name"  # ساخت migration جدید (حتماً بازبینی کنید)
alembic current
docker compose exec postgres psql -U postgres org_rag
```
**migration اجراشده را ویرایش نکنید.** راهنما: [.agents/guides/add-migration.md](.agents/guides/add-migration.md). ابعاد ستون‌های vector از `EMBEDDING_DIMENSIONS` در زمان migration ساخته می‌شوند؛ بعد از تغییر مدل/ابعاد: `python -m app.features.documents.reembed`.

## ۸. ریست و پاک‌سازی
| می‌خواهم | دستور |
|---|---|
| توقف همه | `docker compose down` (volumeها می‌مانند) |
| پاک‌کردن دیتابیس Postgres و Redis (دادهٔ dev) | `docker compose down` سپس `docker volume rm backend_postgres_data backend_redis_data` |
| پاک‌کردن فایل‌های آپلود | `docker volume rm backend_uploads_data` (روش A) یا حذف `data/uploads/*` (روش B) |
| دیتابیس راهکاران | **حذف نکنید**: `rahkaran_mssql_data` volume خارجی است و ریستور دوباره زمان‌بر است |
`down -v` همهٔ volumeهای داخل compose را پاک می‌کند؛ در dev قابل‌قبول است، ولی در production هرگز.

## ۹. نکته‌ها و تفاوت با production
| | dev | production |
|---|---|---|
| compose | `docker-compose.yml` + override (خودکار) | `-f docker-compose.yml -f docker-compose.prod.yml` |
| پورت‌ها | backend 8000، redis 6379، mssql 14330 روی `127.0.0.1` | فقط Caddy |
| secrets | env از `.env` | Docker secrets برای postgres/redis/mssql |
| `DEBUG` | `true` (traceback و لاگ SQL) | `false` |
| لاگ ترافیک | روشن (`REQUEST_LOGGING_ENABLED=true`؛ شامل بدنهٔ پاسخ‌ها) | خاموش |
| کانتینرها | معمولی | غیر root، read-only، محدودیت منابع |
| TLS/proxy | ندارد | Caddy |
- لاگ ترافیک در dev بدنهٔ پاسخ‌ها (از جمله نتایج مالی) را چاپ می‌کند؛ اگر داده‌ی واقعی دارید `REQUEST_LOGGING_ENABLED=false` بگذارید.
- تغییر `.env` فقط با restart اعمال می‌شود (`get_settings()` cache دارد).
- OCR و re-rank هزینهٔ API دارند؛ برای dev می‌توانید `OCR_ENABLED=false` بگذارید.
- قبل از push: `pytest` و (اگر فرانت را تغییر دادید) `npm run build`. push روی `main` فرانت را روی سرور deploy می‌کند ([DEPLOY.md](DEPLOY.md) بخش ۳).
- قواعد کدنویسی و کارهایی که نباید کرد: [.agents/conventions.md](.agents/conventions.md).
