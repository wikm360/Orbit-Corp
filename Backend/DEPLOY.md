# راهنمای سریع پروداکشن (Orbit-Corp)

همه‌ی دستورها داخل `Backend/` روی سرور اجرا می‌شوند. اول یک بار این را بزنید (یا در `~/.bashrc` بگذارید):
```bash
cd /opt/orbit/Orbit-Corp/Backend
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
```
> هرگز `docker compose up` بدون `-f` نزنید (فایل dev را لود می‌کند). هرگز `dc down -v` نزنید (volume دیتابیس‌ها پاک می‌شود).

## چیزهایی که در گیت نیستند و دستی ریخته می‌شوند
| چه | کجا |
|---|---|
| `.env` (`chmod 600`، از `.env.example` ساخته می‌شود) | `Backend/.env` |
| `hints/out/` (۳ فایل: `core_prompt.md`, `hints.jsonl`, `hints_stats.json`) | `Backend/sql/rahkaran/hints/out/` |
| خروجی دیتابیس شرکت: جدیدترین `FULL_*.bak` و `DIFF_*.bak` | `Backend/data/rahkaran-backups/FULL/` و `.../DIFF/` |

## ۱) اولین راه‌اندازی
```bash
git clone git@github.com:wikm360/Orbit-Corp.git /opt/orbit/Orbit-Corp && cd /opt/orbit/Orbit-Corp/Backend
cp .env.example .env && chmod 600 .env && nano .env      # رمزهای جدید + کلیدهای LLM (به INFRA-CHANGES.md / پایین نگاه کنید)
# فایل‌های جدول بالا را بریزید، بعد:
chmod -R a+rX data/rahkaran-backups
dc up -d --build
dc logs rahkaran-refresh        # آخرش باید: "done - the new data is live"
dc ps                           # همه healthy (migrate و rahkaran-refresh exited عادی است)
dc exec backend python -m app.features.db_connector.ingest     # hint های RAG (یک بار)
```
بعد با تونل SSH/VPN وارد سایت شوید و **همان لحظه** ثبت‌نام کنید (کاربر اول ادمین است). سپس ثبت‌نام عمومی را ببندید (پایین).

مقادیر `.env` که حتماً باید درست باشند: `POSTGRES_PASSWORD`, `REDIS_PASSWORD` (hex: `openssl rand -hex 24`)، `RAHKARAN_SA_PASSWORD` (پیچیده)، `RAHKARAN_DB_PASSWORD` (رمز کاربر خواننده)، `JWT_SECRET_KEY`، `LLM_*`/`EMBEDDING_*`، `CORS_ORIGINS=https://<آدرس>`، `SITE_ADDRESS=<آدرس>`، `BIND_IP=127.0.0.1`، `ENVIRONMENT=production`، `DEBUG=false`.

## ۲) آپدیت کد
```bash
git pull
dc up -d --build
```
اگر پوشه‌ی `hints/out` عوض شده بود، جایگزینش کنید و دوباره ingest بزنید (دستور `ingest` بالا).

## ۳) آپدیت دیتابیس حسابداری (خروجی جدید شرکت)
1. فایل‌های جدید `FULL_*.bak` / `DIFF_*.bak` را در `data/rahkaran-backups/` بریزید (قدیمی‌ها می‌مانند یا پاک شوند، فرقی ندارد).
2. `chmod -R a+rX data/rahkaran-backups`
3. `dc up -d` (یا `dc run --rm rahkaran-refresh`) و نتیجه: `dc logs rahkaran-refresh`

خودش جدیدترین FULL + DIFF مرتبط را انتخاب می‌کند، در دیتابیس جانبی restore و `ai` را اعمال و تست می‌کند و بعد جایگزین می‌کند. اگر چیزی جدید نباشد می‌نویسد `already up to date`. گزینه‌ها: `dc run --rm rahkaran-refresh --dry-run` (فقط نشان بده)، `--force` (حتی اگر تازه باشد). اگر خطا بدهد، دیتابیس قبلی سالم می‌ماند.

## ۴) دستورهای روزمره
```bash
dc ps                              # وضعیت
dc logs -f backend                 # لاگ (یا worker, caddy, frontend, mssql)
dc restart backend worker          # ری‌استارت
dc up -d --build backend           # بیلد دوباره‌ی یک سرویس
```
بک‌آپ Postgres (چت‌ها، کاربران): `dc exec -T postgres pg_dump -U postgres org_rag | gzip > pg_$(date +%F).sql.gz` ← فایل را خارج از سرور نگه دارید.

## ۵) دسترسی و گواهی
- `BIND_IP=127.0.0.1` یعنی فقط روی خود سرور / تونل: `ssh -L 8443:127.0.0.1:443 user@server` و بعد `https://localhost:8443`. برای VPN، `BIND_IP` را روی IP رابط VPN بگذارید. هرگز `0.0.0.0`.
- گواهی داخلی Caddy: `dc cp caddy:/data/caddy/pki/authorities/local/root.crt .` و روی مرورگر/سیستم کاربران نصب کنید.
- `SITE_ADDRESS` باید همان نامی باشد که در مرورگر می‌زنید (اگر IP است، IP).

## ۵-ب) دسترسی کاربران شرکت از طریق IP عمومی + پورت (روتر/فایروال)
- مرورگر فقط به Caddy (پورت 443 سرور) وصل می‌شود؛ Caddy مسیر `/api` را به backend و بقیه را به فرانت می‌فرستد. مرورگر هرگز مستقیم با backend حرف نمی‌زند (آدرس API نسبی است: `/api/v1`).
- تنظیم `.env`: `BIND_IP=<IP شبکه‌ی داخلی همین سرور>` (نه 127.0.0.1، چون روتر باید برسد)، `PUBLIC_PORT=<همان پورتی که روتر به آن می‌فرستد، مثلاً 7496>`، `SITE_ADDRESS=<IP عمومی یا دامنه که کاربر می‌زند>` (بدون پورت)، `CORS_ORIGINS=https://<همان>:<پورت خارجی>` (آدرسی که کاربر در مرورگر می‌زند).
- روتر/فایروال شرکت: پورت خارجی ← `BIND_IP:PUBLIC_PORT` سرور (مثلاً 7496 ← 7496)، و **فقط IP(های) شرکت مجاز باشند** (منبع). این مهم‌ترین لایه‌ی امنیتی است.
- لایه‌ی دوم روی خود سرور (چون Docker قوانین ufw را دور می‌زند؛ بعد از `dc up` اعمال شود و پایدار شود با `iptables-persistent`):
  `sudo iptables -I DOCKER-USER -p tcp --dport 8443 ! -s <IP_شرکت>/32 -j DROP`
- گواهی: `tls internal` گواهی خودامضاست؛ یا `root.crt` را از طریق IT روی سیستم‌های شرکت نصب کنید (بخش ۵)، یا با دامنه‌ی داخلی و گواهی CA سازمان جایگزین کنید.
- **قبل از باز شدن پورت، ثبت‌نام عمومی را ببندید (بخش ۶).**

## ۶) بستن ثبت‌نام عمومی (بعد از ساخت ادمین)
در `infra/caddy/Caddyfile`، درست قبل از `handle /api/* {` اضافه کنید، بعد `dc up -d --build caddy`:
```
	@register path /api/v1/auth/register
	respond @register 403
```

## ۷) مشکلات رایج
| علامت | علت / راه‌حل |
|---|---|
| `dc up` خطای `set POSTGRES_PASSWORD...` | متغیر در `.env` خالی است. |
| `rahkaran-refresh`: `no FULL backup found` | فایل‌ها در `data/rahkaran-backups/` نیستند یا نام `..._FULL_YYYYMMDD_HHMMSS.bak` ندارند. |
| refresh: خطای دسترسی فایل | `chmod -R a+rX data/rahkaran-backups` |
| refresh: `SQL Server not reachable` | mssql هنوز بالا نیامده؛ ۱–۲ دقیقه بعد `dc run --rm rahkaran-refresh`. |
| چت مالی «ابزار در دسترس نیست» / خطا | `RAHKARAN_DB_ENABLED=true`؟ `dc logs backend`؛ ingest زده شده؟ |
| رمز Postgres را در `.env` عوض کردم و وصل نمی‌شود | رمز فقط بار اول روی volume خالی اعمال می‌شود: `dc exec postgres psql -U postgres -c "ALTER USER postgres PASSWORD '...'"`. |
| مرورگر خطای گواهی می‌دهد | root.crt را نصب نکرده‌اید یا `SITE_ADDRESS` با آدرس مرورگر یکی نیست. |

جزئیات فنی و تصمیم‌های امنیتی: `INFRA-CHANGES.md`.
