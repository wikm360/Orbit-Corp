# نحوهٔ deploy روی سرور (Production)

راهنمای کامل راه‌اندازی، آپدیت و نگهداری بک‌اند Orbit Corp روی سرور با Docker Compose. توسعه روی سیستم خودتان: [DEVELOPMENT.md](DEVELOPMENT.md).
پشت‌صحنه و دلیل تصمیم‌ها: [.agents/ops/infra-and-deploy.md](.agents/ops/infra-and-deploy.md) و [.agents/ops/runbook.md](.agents/ops/runbook.md).

> همهٔ دستورها داخل پوشهٔ `Backend/` روی سرور اجرا می‌شوند.
> با تنظیم `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml` در `.env`، دستور استاندارد `docker compose` به طور خودکار فایل پروداکشن را لود می‌کند و نیازی به هیچ alias یا فلگ اضافی نیست.
> **هرگز** `down -v` نزنید (volumeهای دیتابیس پاک می‌شوند).

---

## ۰. آنچه روی سرور اجرا می‌شود

```
اینترنت/شبکه ──► Caddy (تنها پورت منتشرشده) ──/api──► backend (FastAPI) ──► postgres (pgvector) · redis · mssql (راهکاران)
                                              └──/──► frontend (Next.js)          ▲
                                                       worker × N (ingestion) ────┘ ──► LLM/Embedding API (اینترنت خروجی)
```
سرویس‌ها: `postgres`، `redis`، `mssql`، `migrate` (یک‌بار)، `backend`، `worker` (چند replica)، `rahkaran-refresh` (یک‌بار)، `frontend`، `caddy`.
دیتابیس‌ها فقط در شبکهٔ داخلی‌اند؛ فقط backend و worker به اینترنت خروجی (برای LLM/Embedding) دسترسی دارند.

## ۱. پیش‌نیازها

| مورد | حداقل / توضیح |
|---|---|
| سیستم‌عامل | Linux (Ubuntu/Debian)، دسترسی SSH با کلید |
| نرم‌افزار | Docker Engine + **Docker Compose v2** (`docker compose`)، `git`، `openssl` |
| منابع | CPU ≥ ۴ هسته، RAM ≥ **۱۶ GB** (SQL Server تا ۱۰GB، postgres ۲GB، backend/worker هرکدام تا ۲GB)، دیسک ≥ ۱۰۰ GB SSD (دو نسخه از دیتابیس راهکاران هنگام refresh + `.bak`ها + اسناد) |
| شبکه | خروجی HTTPS به `LLM_API_BASE_URL` و `EMBEDDING_API_BASE_URL`؛ ورودی فقط روی پورت Caddy |
| داده | فایل‌های `FULL_*.bak` و `DIFF_*.bak` خروجی راهکاران (برای قابلیت مالی) |
| کلیدها | کلید API مدل چت و embedding |

## ۲. اولین راه‌اندازی

### ۲.۱ دریافت کد
```bash
sudo mkdir -p /opt/orbit && sudo chown $USER /opt/orbit
git clone git@github.com:wikm360/Orbit-Corp.git /opt/orbit/Orbit-Corp
cd /opt/orbit/Orbit-Corp/Backend
```

### ۲.۲ ساخت `.env`
```bash
cp .env.example .env && chmod 600 .env
openssl rand -hex 24      # برای هر رمز یک‌بار بزنید (hex چون رمزها داخل URL قرار می‌گیرند)
nano .env
```
مقادیر **الزامی** (بقیه پیش‌فرض دارند؛ فهرست کامل: [.agents/reference/configuration.md](.agents/reference/configuration.md)):

| متغیر | مقدار |
|---|---|
| `COMPOSE_FILE` | `docker-compose.yml:docker-compose.prod.yml` (اتصال خودکار فایل پروداکشن) |
| `ALLOW_PUBLIC_REGISTRATION` | `true` برای ثبت‌نام اولین کاربر (super_admin)؛ سپس `false` |
| `ENVIRONMENT` / `DEBUG` | `production` / `false` |
| `POSTGRES_PASSWORD` | رمز hex جدید (فقط بار اول روی volume خالی اعمال می‌شود) |
| `REDIS_PASSWORD` | رمز hex جدید |
| `RAHKARAN_SA_PASSWORD` | رمز قوی SQL Server: حرف بزرگ+کوچک+عدد+نماد، ≥ ۸ نویسه (فقط بار اول اعمال می‌شود) |
| `RAHKARAN_DB_PASSWORD` | رمز کاربر فقط‌خواندنی `rahkaran_ai_reader` |
| `RAHKARAN_DB_ENABLED` | `true` برای فعال شدن ابزار مالی |
| `JWT_SECRET_KEY` | رشتهٔ تصادفی طولانی (`openssl rand -hex 48`) — **حتماً عوض شود** |
| `LLM_API_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | مدل چت (سازگار با OpenAI، با tool-calling و stream) |
| `EMBEDDING_API_BASE_URL` / `EMBEDDING_API_KEY` / `EMBEDDING_MODEL` / `EMBEDDING_DIMENSIONS` | مدل embedding؛ ابعاد باید با ستون vector دیتابیس یکی باشد (پیش‌فرض ۱۵۳۶) |
| `CORS_ORIGINS` | آدرسی که کاربر در مرورگر می‌زند، مثلاً `https://10.0.0.5:7496` |
| `SITE_ADDRESS` | همان نام/IP بدون پورت (گواهی Caddy برای همین صادر می‌شود) |
| `BIND_IP` / `PUBLIC_PORT` | آدرس و پورتی که Caddy روی میزبان گوش می‌دهد (← بخش ۴) |
| `CADDY_CONFIG` | `Caddyfile` (HTTPS، توصیه‌شده) یا `Caddyfile.http` (HTTP ساده، ناامن) |
| `WORKER_REPLICAS` | تعداد workerهای ingestion (پیش‌فرض ۳) |

توصیه‌های اختیاری (اندازه‌گیری‌شده؛ [.agents/ops/retrieval-evaluation.md](.agents/ops/retrieval-evaluation.md)):
```
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_SEND_DIMENSIONS=true       # با EMBEDDING_DIMENSIONS=1536
RETRIEVAL_SCORE_THRESHOLD=0.4
RETRIEVAL_RERANK_ENABLED=true
LLM_RERANK_MODEL=gpt-4.1-mini
LLM_VISION_MODEL=gemini-3.5-flash-lite  # OCR: دقیق‌ترین و سریع‌ترین در اندازه‌گیری روی اسکن‌های فارسی (ops/retrieval-evaluation.md)؛ مدل reasoning نگذارید؛ OCR_CONCURRENCY پیش‌فرض ۱۲
```
مدل embedding را **قبل از اولین ingest** تعیین کنید؛ بعداً تغییرش نیاز به re-embed دارد (بخش ۶.۴).

### ۲.۳ فایل‌هایی که در git نیستند
| چه | کجا |
|---|---|
| `.env` | `Backend/.env` (`chmod 600`) |
| خروجی راهکاران: `FULL_*.bak` و `DIFF_*.bak` (هر زیرپوشه؛ نام باید شامل `_FULL_YYYYMMDD_HHMMSS.bak` یا `_DIFF_…` باشد) | `Backend/data/rahkaran-backups/` |
```bash
mkdir -p data/rahkaran-backups   # فایل‌ها را بریزید
chmod -R a+rX data/rahkaran-backups
```
(فایل‌های hint ‏`sql/rahkaran/hints/out/` داخل git هستند و با `git pull` می‌آیند.)

### ۲.۴ build و اجرا
```bash
docker compose up -d --build
docker compose ps                      # همه healthy؛ migrate و rahkaran-refresh با وضعیت exited عادی است
docker compose logs migrate            # باید به alembic upgrade head برسد
docker compose logs rahkaran-refresh   # آخرش: "done - the new data is live" (چند دقیقه طول می‌کشد)
```
اولین build چند دقیقه است. اگر `rahkaran-refresh` خطا داد: [بخش ۸](#۸-مشکلات-رایج).

### ۲.۵ hint های Text-to-SQL (خودکار)
هینت‌های پایگاه داده به صورت کاملاً خودکار در startup بک‌اند همگام‌سازی و بارگذاری می‌شوند (نیازی به اجرای دستور دستی نیست). اگر به هر دلیلی خواستید دستی آن را فراخوانی کنید:
```bash
docker compose exec backend python -m app.features.db_connector.ingest
```

### ۲.۶ اولین ادمین و بستن ثبت‌نام عمومی
۱. با تونل/VPN (بخش ۴) یا آدرس سایت وارد شوید و ثبت‌نام کنید: اولین کاربر خودکار `super_admin` می‌شود.
۲. در فایل `.env`، ثبت‌نام عمومی را ببندید:
```bash
ALLOW_PUBLIC_REGISTRATION=false
```
سپس با `docker compose up -d backend` آن را اعمال کنید. از این پس تلاش برای ثبت‌نام عمومی خطای ۴۰۳ دریافت می‌کند.
۳. ساخت کاربران بعدی: ادمین‌ها می‌توانند مستقیماً از طریق API (`POST /api/v1/admin/users`) یا پنل کاربری کاربر جدید ایجاد کنند:
```json
{
  "email": "user@example.com",
  "password": "ChangeMe-12345",
  "full_name": "نام کاربر",
  "role": "user"
}
```
سپس super_admin نقش را در پنل/`PATCH /api/v1/admin/users/{id}/role` در صورت نیاز تنظیم می‌کند، و leader تیم کاربر را به تیم/پروژه اضافه می‌کند.

## ۳. فرانت‌اند و CI

- **در compose:** سرویس `frontend` (Next.js) با build-arg `NEXT_PUBLIC_API_URL=/api/v1` ساخته می‌شود و Caddy مسیر `/` را به آن می‌دهد؛ با `docker compose up -d --build` همراه بک‌اند بالا می‌آید.
- **GitHub Actions** (`.github/workflows/deploy.yml`): با هر push به `main` به سرور SSH می‌زند، `git reset --hard origin/main`، سپس `cd Frontend && npm install && npm run build` و `systemctl restart front`. **بک‌اند/migration/compose را deploy نمی‌کند.** این مسیر مربوط به اجرای فرانت با systemd است و با سرویس `frontend` در compose موازی/تکراری است؛ یکی را انتخاب کنید (در حالت compose، سرویس `front` را stop کنید تا پورت/منابع دوبار مصرف نشود). نیازمند secretهای repo: `SERVER_HOST`، `SERVER_USER`، `SERVER_SSH_KEY`.
- پس بعد از هر push که کد بک‌اند را عوض می‌کند، روی سرور خودتان `git pull && docker compose up -d --build` را بزنید (بخش ۶.۱).

## ۴. دسترسی کاربران

| حالت | تنظیمات |
|---|---|
| **تونل SSH** (ساده و امن) | `BIND_IP=127.0.0.1`؛ از سیستم خودتان `ssh -L 8443:127.0.0.1:443 user@server` و باز کردن `https://localhost:8443` (`SITE_ADDRESS=localhost`) |
| **VPN** (WireGuard…) | `BIND_IP=<IP رابط VPN>` |
| **IP عمومی/روتر شرکت** | `BIND_IP=<IP داخلی سرور>`، `PUBLIC_PORT=<پورت فوروارد روتر مثلاً 7496>`، `SITE_ADDRESS=<IP/دامنه>`، `CORS_ORIGINS=https://<همان>:<پورت خارجی>` |
هرگز `BIND_IP=0.0.0.0` (Docker قوانین ufw را دور می‌زند).

برای حالت IP عمومی:
- روتر/فایروال شرکت: پورت خارجی → `BIND_IP:PUBLIC_PORT` و **فقط IPهای شرکت** مجاز باشند (مهم‌ترین لایه).
- لایهٔ دوم روی سرور (بعد از هر `docker compose up` بررسی و با `iptables-persistent` پایدار شود):
  ```bash
  sudo iptables -I DOCKER-USER -p tcp --dport 8443 ! -s <IP_شرکت>/32 -j DROP
  ```
- **قبل از باز شدن پورت، ثبت‌نام عمومی را ببندید (۲.۶).**

### گواهی HTTPS
`tls internal` گواهی خودامضا (CA داخلی Caddy) می‌سازد. برای نصب روی سیستم کاربران:
```bash
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt .
```
و root.crt را از طریق IT روی مرورگر/سیستم کاربران نصب کنید؛ یا با دامنهٔ داخلی و گواهی CA سازمان جایگزین کنید.
HTTP ساده (`CADDY_CONFIG=Caddyfile.http`) رمز، توکن و داده‌های مالی را بدون رمزگذاری می‌فرستد؛ فقط با allow-list سخت IP قابل‌قبول است.

## ۵. چک‌لیست قبل از دسترسی کاربران

- [ ] همهٔ secretها عوض شده‌اند (`POSTGRES_*`، `REDIS_PASSWORD`، `RAHKARAN_*`، `JWT_SECRET_KEY`) و `.env` با `chmod 600` است.
- [ ] `ENVIRONMENT=production`، `DEBUG=false` (و `REQUEST_LOGGING_ENABLED` در prod خودکار false است).
- [ ] ثبت‌نام عمومی بسته است (`ALLOW_PUBLIC_REGISTRATION=false`)؛ ادمین ساخته شده.
- [ ] `CORS_ORIGINS` فقط origin واقعی https.
- [ ] پورت فقط از IPهای مجاز باز است؛ `BIND_IP` درست است.
- [ ] گواهی روی سیستم کاربران نصب است (یا HTTP با allow-list).
- [ ] provider مدل (LLM/Embedding) با تأیید شرکت انتخاب شده؛ بدانید پرسش، SQL و **ردیف‌های نتیجهٔ مالی** به آن می‌رود (ماسک PII هنوز وجود ندارد).
- [ ] ابزار مالی برای همهٔ کاربران لاگین‌شده (حتی در چت گروهی) باز است؛ اگر مطلوب نیست `RAHKARAN_DB_ENABLED=false` ([known-issues](.agents/known-issues.md)).
- [ ] SQL Server روی `Express` است (برای تولید مجاز؛ سقف ۱۰GB برای هر دیتابیس).
- [ ] backup گرفته می‌شود (بخش ۷) و مخزن git private است.

## ۶. آپدیت

### ۶.۱ کد
```bash
cd /opt/orbit/Orbit-Corp/Backend
git pull
docker compose up -d --build        # migrate خودکار اجرا می‌شود؛ backend/worker/frontend بازسازی می‌شوند
docker compose ps && docker compose logs --tail=50 migrate backend
```
قبل از آپدیت‌هایی که migration دارند، backup بگیرید (بخش ۷). Migration (مثل `0008`) ممکن است جدول بزرگ را بازنویسی کند؛ در ساعت کم‌تردد اجرا کنید. **migration اجراشده را هرگز ویرایش نکنید**؛ برخی (مثل `0002`) برگشت‌ناپذیرند.

### ۶.۲ دیتابیس حسابداری (خروجی جدید شرکت)
```bash
cp /path/FULL_*.bak /path/DIFF_*.bak data/rahkaran-backups/
chmod -R a+rX data/rahkaran-backups
docker compose up -d                                       # یا: docker compose run --rm rahkaran-refresh
docker compose logs rahkaran-refresh
```
خودکار جدیدترین FULL و DIFF هم‌زنجیره را انتخاب، در دیتابیس جانبی restore، لایهٔ `ai` را اعمال و تست می‌کند و بعد با چند ثانیه قطعی جایگزین می‌کند؛ در صورت خطا دیتابیس قبلی سالم می‌ماند. گزینه‌ها: `docker compose run --rm rahkaran-refresh --dry-run` / `--force`. اگر ساختار view ها عوض نشده، ingest مجدد hint لازم نیست.

### ۶.۳ تغییر `.env`
```bash
nano .env
docker compose up -d backend worker      # تنظیمات فقط با restart اعمال می‌شوند
```
(رمز postgres/redis/mssql بعد از اولین راه‌اندازی با تغییر `.env` عوض نمی‌شود؛ برای Postgres: `docker compose exec postgres psql -U postgres -c "ALTER USER postgres PASSWORD '...'"`.)

### ۶.۴ تغییر مدل embedding
```bash
nano .env                                                    # EMBEDDING_MODEL / DIMENSIONS / SEND_DIMENSIONS
docker compose up -d backend worker
docker compose exec backend python -m app.features.documents.reembed --dry-run
docker compose exec backend python -m app.features.documents.reembed     # اسناد READY و حافظهٔ پروژه‌ها
docker compose exec backend python -m app.features.db_connector.ingest   # hint ها
```
تا پایان re-embed نتایج جست‌وجو ترکیبی از دو مدل است؛ در ساعت کم‌تردد انجام دهید.

### ۶.۵ بازگشت (rollback)
```bash
git log --oneline -5 && git checkout <commit-قبلی> && docker compose up -d --build
```
اگر migration جدیدی اجرا شده بود، کد قدیمی ممکن است با schema ناسازگار باشد؛ در صورت نیاز از backup Postgres برگردانید.

## ۷. backup و بازیابی

```bash
# Postgres: کاربران، گفتگوها، اسناد (متادیتا و chunk)، حافظه، hint ها، لاگ پرسش‌ها
docker compose exec -T postgres pg_dump -U postgres org_rag | gzip > pg_$(date +%F).sql.gz

# فایل‌های آپلودشده (volume uploads_data)
docker run --rm -v backend_uploads_data:/d -v "$PWD":/b alpine tar czf /b/uploads_$(date +%F).tgz -C /d .
```
هر دو را **خارج از سرور** نگه دارید (و در صورت امکان رمزگذاری). دیتابیس راهکاران از `.bak` شرکت قابل بازسازی است. اسم volume با `docker volume ls` تأیید شود (پیشوند `backend_` از `name: backend` در compose می‌آید).
بازیابی Postgres: `gunzip -c pg_X.sql.gz | docker compose exec -T postgres psql -U postgres org_rag` روی دیتابیس خالی (پس از `docker compose stop backend worker`).

## ۸. مشکلات رایج

| علامت | علت / راه‌حل |
|---|---|
| `docker compose up` خطای `set POSTGRES_PASSWORD…` | متغیر الزامی در `.env` خالی است |
| `rahkaran-refresh`: `no FULL backup found` | فایل‌ها در `data/rahkaran-backups/` نیستند یا نام استاندارد ندارند |
| refresh: خطای دسترسی | `chmod -R a+rX data/rahkaran-backups` |
| refresh: `SQL Server not reachable` | mssql هنوز بالا نیامده (تا ۹۰ثانیه)؛ چند دقیقه بعد `docker compose run --rm rahkaran-refresh` |
| چت مالی خطا می‌دهد | `RAHKARAN_DB_ENABLED=true`؟ backend بعد از تغییر env restart شده؟ ingest hint ها؟ رمز reader درست؟ `docker compose logs backend` |
| مرورگر خطای گواهی | root.crt نصب نیست یا `SITE_ADDRESS` با آدرس مرورگر یکی نیست |
| سند `processing` می‌ماند | `docker compose ps`/`docker compose logs worker`؛ Redis؛ job کشته‌شده (حافظه/timeout) ← حذف و دوباره آپلود |
| سند `failed` (429/قطع) | محدودیت API؛ `POST /projects/{id}/documents/{doc}/retry`؛ `WORKER_REPLICAS` یا `OCR_CONCURRENCY` را کم کنید |
| رمز Postgres تغییر کرد و وصل نمی‌شود | رمز فقط روی volume خالی اعمال می‌شود (`ALTER USER`) |
| `Permission denied` روی آپلود | volume قدیمی با root ساخته شده: `chown -R 10001:10001` روی volume |
| پاسخ‌های گروه نمی‌رسد | Redis؛ توکن WS معتبر؛ Caddy |
| دیسک پر شد | `docker system df`؛ فایل‌های `.bak` قدیمی؛ لاگ‌ها rotate می‌شوند (۱۰MB×۵) |

## ۹. دستورهای روزمره
```bash
docker compose ps                              # وضعیت
docker compose logs -f backend                 # یا worker, caddy, frontend, mssql, postgres
docker compose restart backend worker
docker compose up -d --build backend           # بازسازی یک سرویس
docker compose exec backend alembic current    # نسخهٔ migration
docker compose exec postgres psql -U postgres org_rag
```
سلامت: `curl -s http://127.0.0.1:8000/health` فقط از داخل شبکهٔ docker (`docker compose exec backend python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health').read())"`)؛ نام کانتینر mssql در prod: `backend-mssql-1`.
