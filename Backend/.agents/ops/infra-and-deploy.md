# زیرساخت و Deploy

فایل‌ها: `Dockerfile`, `docker-compose.yml` (پایه/dev), `docker-compose.override.yml` (فقط dev، خودکار لود می‌شود), `docker-compose.prod.yml` (overlay پروداکشن), `infra/caddy/*`, `.dockerignore`, `.github/workflows/deploy.yml`.
دستورهای روزمره: [runbook.md](runbook.md).

## اجرای dev
```bash
cd Backend
cp .env.example .env     # مقادیر الزامی: POSTGRES_PASSWORD, RAHKARAN_SA_PASSWORD, RAHKARAN_DB_PASSWORD (+ LLM/EMBEDDING)
docker compose up -d     # postgres+redis → migrate → backend+worker(3) ; mssql ; rahkaran-refresh
```
- compose فایل `docker-compose.override.yml` را خودکار لود می‌کند: Redis روی `127.0.0.1:6379` و شبکه‌ی ثابت `10.77.0.0/24`.
- سرویس‌های dev publish روی localhost: backend `127.0.0.1:8000`, mssql `127.0.0.1:14330`.
- `rahkaran_mssql_data` یک volume **external** است؛ روی ماشین جدید ابتدا `docker volume create rahkaran_mssql_data`.
- `MSSQL_PID`: پیش‌فرض Express؛ برای توسعه می‌توان `Developer` گذاشت (**برای پروداکشن مجاز نیست**).
- مرتبه‌ی بالا آمدن: `postgres`+`redis` (healthcheck) → `migrate` (`alembic upgrade head`، `restart: "no"`) → `backend`+`worker` (depends_on `service_completed_successfully`).
- Postgres image: `pgvector/pgvector:0.8.7-pg16-bookworm`؛ Redis `7.4.11-alpine`؛ SQL Server `2022-CU27-ubuntu-22.04` (همان image که volume داده قبلاً با آن ساخته شده).

## Dockerfile (backend/worker/refresh)
`python:3.12.12-slim-bookworm`، `gcc` و `poppler-utils` (برای `pdftoppm`)، `pip install -r requirements.txt`، دانلود و bake کردن encoding tiktoken در `/opt/tiktoken` (`TIKTOKEN_CACHE_DIR`) تا با rootfs فقط‌خواندنی و بدون اینترنت کار کند، کاربر غیر root `app` (uid/gid 10001)، `/app/data/uploads` متعلق به آن. `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`. همان image برای سه نقش (backend, worker, rahkaran-refresh) با `command`/`entrypoint` متفاوت استفاده می‌شود.
`.dockerignore` شامل `docs/`, `Assets/`, `.env*` (به‌جز example), `*.bak`, `data/uploads/*`, `.venv`، و `eval/` (فایل‌های ارزیابی، ~۲٫۹GB)، `.agents`، `AGENTS.md`، `CLAUDE.md` هم خارج از image هستند؛ ولی **`sql/` و `sql/rahkaran/hints/out/` را حذف نمی‌کند** (لازم برای hint ها و refresh).

## overlay پروداکشن (`docker-compose.prod.yml`)
اجرا فقط با `-f` صریح (alias پیشنهادی `dc`):
```bash
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
```
> هرگز `docker compose up` بدون `-f` (فایل dev را لود می‌کند) و هرگز `dc down -v` (volume دیتابیس‌ها پاک می‌شود).

**شبکه‌ها**:
| شبکه | نوع | اعضا |
|---|---|---|
| `data` | internal | postgres, redis, mssql, migrate, backend, worker, rahkaran-refresh |
| `app` | internal | caddy, frontend, backend |
| `egress` | عادی (اینترنت خروجی) | backend, worker (برای LLM/Embedding API) |
| `edge` | عادی | caddy (تنها سرویس با پورت منتشرشده) |
دیتابیس‌ها هرگز به `egress` وصل نیستند.

**Secrets**: `postgres_password`, `redis_password`, `mssql_sa_password` به‌عنوان Docker secret (از env `.env`) در `/run/secrets`. Postgres از `POSTGRES_PASSWORD_FILE`، Redis با `--requirepass "$(cat …)"`، mssql با wrapper که `MSSQL_SA_PASSWORD` را از فایل می‌خواند. کانتینرهای اپ `POSTGRES_PASSWORD/REDIS_PASSWORD/RAHKARAN_SA_PASSWORD` را خالی می‌بینند. `REDIS_URL` با رمز: `redis://:${REDIS_PASSWORD}@redis:6379/0`.

**سخت‌سازی کانتینرها**: `read_only: true` + `tmpfs /tmp`, `cap_drop: [ALL]` (به‌جز موارد لازم: postgres: CHOWN/DAC_OVERRIDE/FOWNER/SETGID/SETUID؛ mssql و caddy: NET_BIND_SERVICE چون باینری‌ها file-capability دارند)، `no-new-privileges`, user `10001:10001`، محدودیت `mem_limit`/`pids_limit` (backend/worker 2g/512؛ postgres 2g؛ redis 512m؛ mssql 10g)، log rotation `json-file 10m×5`. Redis `read_only` ندارد (تزریق secret محیطی به rootfs فقط‌خواندنی ممکن نیست).

**سرویس‌های اپ**: `migrate`, `backend` (`expose 8000`، شبکه‌های app+data+egress)، `worker` (data+egress)، `rahkaran-refresh` (data؛ منتظر mssql healthy)، `frontend` (build از `../Frontend` با args `NEXT_PUBLIC_API_URL=/api/v1` و `NEXT_PUBLIC_AI_TRIGGER_TOKEN`)، `caddy`.
env مشترک اپ: `ENVIRONMENT=production`, `DEBUG=false`, `REQUEST_LOGGING_ENABLED=false`.

## Caddy (`infra/caddy/`)
- image `caddy:2.11.7-alpine`، کاربر غیر root؛ داخل کانتینر روی **8443** (HTTPS یا HTTP) و **8080** (healthcheck `/healthz`، منتشر نمی‌شود) گوش می‌دهد. compose: `${BIND_IP:-127.0.0.1}:${PUBLIC_PORT:-443}:8443`.
- `Caddyfile` (HTTPS): `https_port 8443`, `auto_https disable_redirects`, `admin off`, `default_sni` (کاربرانی که با IP بدون SNI می‌آیند هم گواهی بگیرند)؛ سایت `{$SITE_ADDRESS:localhost}` با `tls internal` (CA داخلی Caddy) + HSTS.
- `Caddyfile.http` (`CADDY_CONFIG=Caddyfile.http`): HTTP ساده، `auto_https off`. ⚠️ رمز/توکن/داده‌ی مالی بدون رمزگذاری؛ فقط با allow-list سخت IP قابل‌قبول؛ برخی قابلیت‌های مرورگر (clipboard) کار نمی‌کنند.
- `app.caddy` (مشترک): هدرهای امنیتی (`nosniff`, `Referrer-Policy: no-referrer`, CSP در حالت **Report-Only**, حذف `Server`)؛ `@blocked` برای `/docs /redoc /openapi.json` (و نسخه‌های زیر `/api`) → **404**؛ `handle /api/*`: `request_body max_size 60MB` و `reverse_proxy backend:8000 { flush_interval -1 }` (بدون buffer برای SSE، بدون فشرده‌سازی)؛ بقیه → `frontend:3000` با `encode zstd gzip`.
- مرورگر هرگز مستقیم با backend حرف نمی‌زند؛ آدرس API نسبی است (`/api/v1`).
- گواهی داخلی: `dc cp caddy:/data/caddy/pki/authorities/local/root.crt .` و نصب روی سیستم‌های کاربران (یا گواهی CA سازمان). `SITE_ADDRESS` باید دقیقاً همان نام/IP‌ای باشد که در مرورگر زده می‌شود (بدون پورت).

## اتصال از بیرون (پورت/روتر)
- `BIND_IP=127.0.0.1` یعنی فقط روی خود سرور/تونل: `ssh -L 8443:127.0.0.1:443 user@server` سپس `https://localhost:8443`. برای VPN، `BIND_IP` = IP رابط VPN. **هرگز `0.0.0.0`** (Docker قوانین ufw را دور می‌زند).
- دسترسی کاربران شرکت از اینترنت: `BIND_IP=<IP داخلی سرور>`, `PUBLIC_PORT=<پورت فوروارد روتر مثلاً 7496>`, `SITE_ADDRESS=<IP عمومی/دامنه>`, `CORS_ORIGINS=https://<همان>:<پورت خارجی>`. روتر/فایروال شرکت فقط IPهای شرکت را مجاز کند (مهم‌ترین لایه). لایه‌ی دوم روی سرور: `sudo iptables -I DOCKER-USER -p tcp --dport 8443 ! -s <IP_شرکت>/32 -j DROP` (پایدار با `iptables-persistent`).
- **قبل از باز شدن پورت ثبت‌نام عمومی را ببندید**: در `infra/caddy/Caddyfile`، قبل از `handle /api/* {` افزودن
  ```
  @register path /api/v1/auth/register
  respond @register 403
  ```
  و `dc up -d --build caddy`. (در `app.caddy` مشترک این بلوک پیش‌فرض نیست.)

## CI/CD (`.github/workflows/deploy.yml`)
روی هر push به `main`: SSH به سرور → یافتن checkout `wikm360/Orbit-Corp` → `git fetch` + `git reset --hard origin/main` → `cd Frontend && npm install && npm run build` → `systemctl restart front`.
⚠️ **backend/worker/migration/compose را deploy نمی‌کند**؛ فقط فرانت از طریق systemd. بک‌اند (Docker) باید روی سرور دستی با `git pull && dc up -d --build` به‌روز شود (طبق شواهد، ادغام این دو مسیر انجام نشده؛ merge شاخه‌ی infra-hardening، deploy را به compose سوییچ نکرده است). مستند قدیمی که می‌گفت CI migration و rebuild بک‌اند را انجام می‌دهد با کد فعلی ناسازگار است.

## اولین راه‌اندازی روی سرور
```bash
git clone git@github.com:wikm360/Orbit-Corp.git /opt/orbit/Orbit-Corp && cd /opt/orbit/Orbit-Corp/Backend
cp .env.example .env && chmod 600 .env && nano .env
# فایل‌هایی که در git نیستند و دستی ریخته می‌شوند: (جدول پایین)
chmod -R a+rX data/rahkaran-backups
dc up -d --build
dc logs rahkaran-refresh                    # باید: "done - the new data is live"
dc ps                                       # همه healthy (migrate و rahkaran-refresh = exited عادی)
dc exec backend python -m app.features.db_connector.ingest
```
سپس با تونل/VPN وارد شوید و **همان لحظه ثبت‌نام کنید** (اولین کاربر super_admin می‌شود)، بعد ثبت‌نام عمومی را ببندید.

| فایل | محل | چرا در git نیست |
|---|---|---|
| `.env` (chmod 600) | `Backend/.env` | secret |
| `FULL_*.bak` و `DIFF_*.bak` شرکت | `Backend/data/rahkaran-backups/FULL|DIFF/` | حجیم/محرمانه |

مقادیر `.env` که حتماً باید درست باشند: `POSTGRES_PASSWORD`, `REDIS_PASSWORD` (hex: `openssl rand -hex 24`؛ hex چون در `DATABASE_URL`/`REDIS_URL` جاسازی می‌شوند)، `RAHKARAN_SA_PASSWORD` (پیچیده: حرف بزرگ/کوچک/رقم/نماد ≥۸)، `RAHKARAN_DB_PASSWORD`, `JWT_SECRET_KEY`, `LLM_*`, `EMBEDDING_*`, `CORS_ORIGINS=https://<آدرس>`, `SITE_ADDRESS`, `BIND_IP=127.0.0.1`, `ENVIRONMENT=production`, `DEBUG=false`. رمز SA فقط در اولین init روی volume خالی اعمال می‌شود. رمز Postgres هم همین‌طور؛ برای تغییر بعدی: `dc exec postgres psql -U postgres -c "ALTER USER postgres PASSWORD '…'"`.

## تصمیم‌های امنیتی زیرساخت (چرا این‌طور است)
- فقط Caddy پورت منتشر می‌کند؛ دیتابیس‌ها روی شبکه‌ی internal بدون مسیر به بیرون.
- secrets دیتابیس‌ها فایل هستند نه env (docker inspect نشت نمی‌دهد).
- سخت‌سازی کانتینر و محدودیت منابع برای کاهش اثر نفوذ.
- `/docs` در خود اپ غیرفعال نیست (دفاع در عمق نیازمند کد؛ ← known-issues).
- لایسنس SQL Server: Express (رایگان و مجاز تولید، سقف ۱۰GB/DB؛ DB فعلی ~۵GB) — قبل از سوییچ مطمئن شوید DB ریستورشده ویژگی Enterprise-only ندارد (`SELECT * FROM sys.dm_db_persisted_sku_features`).
- رمز SA پیش‌فرض قدیمی قبلاً در تاریخچه‌ی git (commit `4a320ca`) بوده؛ همه‌ی secretهای واقعی باید rotate و تاریخچه با gitleaks/trufflehog بررسی شود.
- مخزن باید **private** بماند: `Backend/docs/rahkaran/*` و `assets/*.pdf` (قراردادها) حاوی نام و ارقام واقعی شرکت‌اند.
