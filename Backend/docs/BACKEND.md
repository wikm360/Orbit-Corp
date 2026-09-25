# مستندات بک‌اند Orbit Corp (دستیار هوشمند سازمانی)

بک‌اند یک **دستیار هوشمند سازمانی مبتنی بر RAG** است: کاربران سازمان در تیم‌ها و پروژه‌ها سازمان‌دهی می‌شوند، اسناد پروژه‌ها آپلود و ایندکس می‌شوند، و کاربران می‌توانند با یک هوش مصنوعی گفتگو کنند که جواب‌هایش را از اسناد همان پروژه‌ها (با ذکر منبع) می‌سازد. علاوه بر گفتگوی شخصی با AI، هر پروژه یک **چت گروهی** هم دارد که اعضا در آن با هم حرف می‌زنند و هر وقت لازم شد AI را با `@bot` صدا می‌زنند.

- API: FastAPI (Python 3.12/3.13)، مسیر پایه `/api/v1`
- پایگاه داده: PostgreSQL + افزونه pgvector
- صف و پیام‌رسانی: Redis (صف پردازش اسناد با RQ، و pub/sub برای چت گروهی)
- مدل‌های هوش مصنوعی: هر سرویس سازگار با OpenAI (چت) و یک endpoint سازگار با `/v1/embeddings` (پیش‌فرض BGE-M3)

---

## ۱. معماری کلی

```
                      ┌──────────────┐
   مرورگر / فرانت ──► │  FastAPI API │◄──► PostgreSQL + pgvector
   (REST, SSE, WS)    │  (uvicorn)   │
                      └──┬────────┬──┘
                         │        │ pub/sub (چت گروهی)
              صف RQ      ▼        ▼
                      ┌──────────────┐
                      │    Redis     │
                      └──────┬───────┘
                             │ job
                      ┌──────▼───────┐        ┌────────────────────┐
                      │ Ingestion    │──────► │ Embedding API      │
                      │ Worker (RQ)  │        │ (BGE-M3, OpenAI-   │
                      └──────────────┘        │  compatible)       │
                                              └────────────────────┘
        API ──► LLM API (OpenAI-compatible، استریم پاسخ)
```

سه پردازش جدا اجرا می‌شود:
1. **API** (`app.main:app`): همه‌ی endpointها، SSE و WebSocket.
2. **Worker** (`python -m workers.ingestion_worker`): پردازش اسناد آپلودشده در پس‌زمینه.
3. **زیرساخت**: Postgres و Redis.

## ۲. ساختار پوشه‌ها

```
Backend/
├── app/
│   ├── main.py                 ساخت اپ، CORS، ثبت routerها، /health
│   ├── core/                   config, database, security (JWT/bcrypt),
│   │                           dependencies (کنترل دسترسی), exceptions
│   ├── features/
│   │   ├── auth/               ثبت‌نام، لاگین، refresh/logout، کاربر
│   │   ├── access_control/     تیم‌ها و عضویت تیم
│   │   ├── projects/           پروژه‌ها و عضویت پروژه
│   │   ├── documents/          آپلود/حذف سند + pipeline ایندکس (ingestion/)
│   │   ├── retrieval/          جست‌وجوی برداری با فیلتر دسترسی
│   │   ├── chat/               چت شخصی (SSE)، چت گروهی (WebSocket)، گفتگوها
│   │   └── admin/              مدیریت کاربران و اسناد (ادمین)
│   └── providers/              اینترفیس LLM و Embedding (قابل تعویض)
├── workers/ingestion_worker.py پردازشگر صف
├── alembic/versions/           0001_init، 0002_projects_chat_roles
├── tests/                      pytest (نیاز به Postgres واقعی)
└── data/uploads/               فایل‌های آپلودشده
```

هر feature ساختار ثابت دارد: `models.py`، `schemas.py`، `service.py` (منطق)، `router.py` (HTTP).

---

## ۳. نقش‌ها و دسترسی‌ها

دو نوع نقش وجود دارد:

**نقش سراسری کاربر** (`users.role`):

| نقش | توضیح |
|---|---|
| `super_admin` | بالاترین سطح. اولین کاربری که در سیستم ثبت‌نام کند خودکار این نقش را می‌گیرد. |
| `admin` | مدیر سازمان (CEO). به همه‌ی تیم‌ها، پروژه‌ها و گفتگوها دسترسی دارد. |
| `user` | کاربر عادی؛ فقط به چیزهایی که به آن‌ها اضافه شده. |

**نقش داخل تیم** (`team_memberships.role`): `leader` (مدیر تیم) یا `member`. یک نفر می‌تواند در تیم A لیدر و در تیم B عضو ساده باشد.

**ماتریس دسترسی:**

| کار | user (عضو) | leader همان تیم | admin | super_admin |
|---|:-:|:-:|:-:|:-:|
| ساخت تیم / دیدن همه‌ی تیم‌ها | ✗ | ✗ | ✓ | ✓ |
| تعیین leader برای تیم | ✗ | ✗ | ✓ | ✓ |
| افزودن/حذف عضو ساده‌ی تیم | ✗ | ✓ | ✓ | ✓ |
| ساخت پروژه در تیم | ✗ | ✓ | ✓ | ✓ |
| افزودن/حذف عضو پروژه (فقط از اعضای همان تیم) | ✗ | ✓ | ✓ | ✓ |
| آپلود/حذف سند پروژه | ✗ | ✓ | ✓ | ✓ |
| دیدن اسناد پروژه و چت گروهی آن | ✓ (اگر عضو پروژه باشد) | ✓ | ✓ | ✓ |
| دیدن چت شخصی دیگران | ✗ | ✗ | ✓ | ✓ |
| تغییر نقش سراسری کاربران | ✗ | ✗ | ✗ | ✓ |
| دیدن لیست کاربران / همه‌ی اسناد (`/admin`) | ✗ | ✗ | ✓ | ✓ |

قواعد مهم:
- دسترسی به پروژه فقط از راه **عضویت پروژه** است و عضو پروژه باید عضو **تیمِ آن پروژه** هم باشد.
- **با حذف کاربر از تیم، عضویت‌های پروژه‌ی همان تیم هم پاک می‌شود** و دسترسی‌اش به اسناد و چت گروهی پروژه قطع می‌شود.
- ادمین‌ها (`admin`/`super_admin`) همه‌جا دسترسی دارند؛ این یک تصمیم آگاهانه است (شامل چت‌های شخصی).

---

## ۴. مدل داده

| جدول | کاربرد | نکات |
|---|---|---|
| `users` | کاربران | ایمیل یکتا، رمز bcrypt، نقش سراسری |
| `refresh_tokens` | نشست‌های طولانی | فقط hash ذخیره می‌شود؛ `revoked_at` برای ابطال |
| `teams` | تیم‌ها | نام یکتا |
| `team_memberships` | عضویت + نقش در تیم | یکتا روی (user, team)؛ ستون `added_by` |
| `projects` | پروژه‌ها | متعلق به یک تیم؛ نام یکتا داخل تیم |
| `project_memberships` | دسترسی کاربر به پروژه | یکتا روی (project, user) |
| `conversations` | گفتگوها | `type` = `personal` یا `project_group` |
| `messages` | پیام‌ها | `sender_type` = `user`/`assistant`، `sources` (JSON منابع)، `reply_to_message_id` |
| `documents` | اسناد | فقط متعلق به **یکی** از پروژه یا گفتگو (CHECK constraint)؛ وضعیت `processing/ready/failed`؛ `content_hash` |
| `document_chunks` | تکه‌های سند + بردار embedding | ایندکس HNSW برای جست‌وجوی cosine |

---

## ۵. قابلیت‌ها و روال‌ها

### ۵.۱ احراز هویت
- **ثبت‌نام** `POST /auth/register`: اولین کاربر سیستم `super_admin` می‌شود (با قفل دیتابیس، پس دو ثبت‌نام هم‌زمان هر دو ادمین نمی‌شوند)؛ بقیه `user`.
- **لاگین** `POST /auth/login`: برمی‌گرداند `access_token` (JWT، پیش‌فرض ۳۰ دقیقه) + `refresh_token` (مبهم، پیش‌فرض ۳۰ روز) + اطلاعات کاربر.
- **تمدید** `POST /auth/refresh`: refresh token را می‌گیرد، **ابطالش می‌کند** و یک جفت توکن جدید می‌دهد (rotation). چون عمل اتمیک است، یک توکن هرگز دو بار قابل استفاده نیست؛ استفاده‌ی دوباره → 401.
- **خروج** `POST /auth/logout`: refresh token را باطل می‌کند (access token تا انقضای طبیعی‌اش معتبر می‌ماند).
- **پروفایل** `GET /auth/me`.
- همه‌ی endpointهای دیگر با هدر `Authorization: Bearer <access_token>` کار می‌کنند.

### ۵.۲ تیم‌ها و پروژه‌ها
- ادمین تیم می‌سازد و لیدر تعیین می‌کند؛ لیدر اعضای ساده‌ی تیم را مدیریت می‌کند و پروژه می‌سازد.
- سازنده‌ی پروژه خودکار عضو آن می‌شود.
- اعضای ساده‌ی تیم فقط پروژه‌هایی را می‌بینند که به آن‌ها اضافه شده‌اند؛ لیدر و ادمین همه‌ی پروژه‌های تیم را می‌بینند.

### ۵.۳ اسناد (پایگاه دانش پروژه)
فرمت‌های پشتیبانی‌شده: **PDF، DOCX، PPTX، XLSX، TXT** (فقط متن؛ بدون OCR).

روال آپلود (`POST /projects/{id}/documents`، فقط لیدر/ادمین):
1. اعتبارسنجی پسوند و حجم (پیش‌فرض حداکثر ۵۰ مگابایت).
2. محاسبه‌ی SHA-256 محتوا. اگر فایل هم‌محتوایی قبلاً آماده (READY) شده بود، **فایل دوباره ذخیره نمی‌شود**؛ و اگر با همان مدل embedding ایندکس شده بود، chunkهایش کپی می‌شود و سند بلافاصله READY است.
3. در غیر این‌صورت سند با وضعیت `processing` ثبت و یک job در صف Redis گذاشته می‌شود.
4. **Worker** این مراحل را اجرا می‌کند: `Parse` (استخراج متن) → `Chunk` (تکه‌های ۵۰۰ توکنی با هم‌پوشانی ۵۰) → `Embed` (بردار برای هر تکه) → `Persist` (ذخیره‌ی chunkها). موفق → `ready`؛ خطا → `failed` به‌همراه `error_message`.
5. حذف سند فایل فیزیکی را فقط وقتی پاک می‌کند که سند دیگری به آن اشاره نکند.

همچنین هر گفتگو می‌تواند اسناد **موقت خودش** را داشته باشد (`POST /chat/conversations/{id}/documents`) که فقط داخل همان گفتگو دیده می‌شوند.

### ۵.۴ چت شخصی با AI (SSE)
`POST /chat` با `{message, conversation_id?}`:
1. اگر `conversation_id` نباشد یا مال کاربر نباشد، گفتگوی شخصی جدیدی ساخته می‌شود (عنوان = ۸۰ نویسه‌ی اول پیام).
2. پیام کاربر ذخیره می‌شود.
3. **بازیابی**: پیام کاربر embed می‌شود و در اسناد قابل‌دسترس جست‌وجو می‌شود (اسناد خود گفتگو + اسناد پروژه‌ی «متصل‌شده» به گفتگو، در صورتی که کاربر هنوز عضو آن پروژه باشد). بهترین `top_k=5` تکه برمی‌گردد؛ اگر شباهت بهترین تکه زیر `0.3` باشد، بازیابی نادیده گرفته می‌شود و AI به‌صورت عمومی پاسخ می‌دهد.
4. پاسخ LLM به‌صورت **استریم SSE** می‌آید و بعد از پایان ذخیره می‌شود. حافظه‌ی گفتگو = ۳۰ پیام آخر.

رویدادهای SSE:

| event | داده |
|---|---|
| `start` | `{conversation_id}` |
| `delta` | `{content}` (تکه‌ی متن) |
| `done` | `{sources: [...], message_id}` |

هر منبع: `document_id, document_filename, chunk_index, snippet, score`.

فیلتر دسترسی **داخل خود query برداری** اعمال می‌شود (نه بعد از آن)، پس تکه‌ی سند غیرمجاز هرگز به LLM نمی‌رسد.

یک گفتگوی شخصی را می‌شود با `PATCH /chat/conversations/{id}` به یک پروژه‌ی عضو‌شده متصل یا جدا کرد تا از اسنادش استفاده کند.

### ۵.۵ چت گروهی پروژه (WebSocket)
- ساخت: `POST /chat/conversations` با `type=project_group` و `project_id`. همه‌ی اعضای پروژه، لیدر تیم و ادمین به آن دسترسی دارند.
- **ارسال پیام** از طریق REST: `POST /chat/conversations/{id}/messages` با `{content}` (تا هر پیام قبل از پخش ذخیره شود).
- **دریافت زنده** از طریق `WS /api/v1/chat/conversations/{id}/ws?token=<access_token>` (مرورگر نمی‌تواند هدر بفرستد، پس توکن در query است). سرور فقط رویداد می‌فرستد.
- اگر پیام با `@bot` شروع شود، AI در پس‌زمینه با اسناد پروژه پاسخ می‌دهد و پاسخ را به‌صورت استریم برای همه پخش می‌کند. در گروه، اسم فرستنده به هر پیام کاربر اضافه می‌شود تا AI بداند چه کسی حرف زده.
- پخش پیام از طریق Redis pub/sub است، پس اگر روزی چند instance از بک‌اند اجرا شود هم درست کار می‌کند.

رویدادهای WebSocket (JSON):

| event | داده |
|---|---|
| `message` | `{message: MessageRead}` (پیام کاربر یا پاسخ نهایی AI) |
| `assistant_start` | `{reply_to_message_id}` |
| `assistant_delta` | `{reply_to_message_id, delta}` |

**اتصال مجدد:** کلاینت بعد از reconnect باید `GET /chat/conversations/{id}/messages?after=<آخرین message id>` را بزند تا پیام‌های از دست‌رفته را بگیرد. ترتیب پیام‌ها با `(created_at, id)` است، پس پیام‌های هم‌زمان جا نمی‌افتند. سرور قبل از پذیرش اتصال به Redis subscribe می‌شود.

### ۵.۶ ادمین
- `GET /admin/users` لیست کاربران؛ `PATCH /admin/users/{id}/role` تغییر نقش (فقط super_admin)؛ `GET /admin/documents` همه‌ی اسناد.

---

## ۶. فهرست endpointها (پیشوند `/api/v1`)

| متد و مسیر | دسترسی | کار |
|---|---|---|
| `POST /auth/register` `login` `refresh` `logout` | عمومی | احراز هویت |
| `GET /auth/me` | لاگین | پروفایل |
| `POST /teams` , `GET /teams` | admin | ساخت / لیست همه‌ی تیم‌ها |
| `GET /teams/mine` | لاگین | تیم‌های من |
| `GET /teams/{id}/members` | عضو تیم / admin | اعضا |
| `POST /teams/{id}/members` | leader / admin | افزودن یا تغییر نقش عضو (leader فقط با admin) |
| `DELETE /teams/{id}/members/{user}` | leader / admin | حذف از تیم (+ قطع دسترسی پروژه‌ها) |
| `POST /teams/{id}/projects` | leader / admin | ساخت پروژه |
| `GET /teams/{id}/projects` | عضو تیم / admin | پروژه‌های قابل‌دیدن |
| `GET /projects/mine` , `GET /projects/{id}` | عضو پروژه | پروژه |
| `GET/POST/DELETE /projects/{id}/members[/{user}]` | عضو (GET) / leader (بقیه) | اعضای پروژه |
| `GET/POST /projects/{id}/documents` , `DELETE …/{doc}` | عضو (GET) / leader (بقیه) | اسناد پروژه |
| `POST /chat` | لاگین | چت شخصی (SSE) |
| `GET/POST /chat/conversations` , `GET/PATCH …/{id}` | طبق دسترسی گفتگو | مدیریت گفتگو |
| `GET/POST /chat/conversations/{id}/messages` | طبق دسترسی گفتگو | تاریخچه/catch-up و ارسال پیام گروهی |
| `POST /chat/conversations/{id}/documents` | طبق دسترسی گفتگو | سند موقت گفتگو |
| `WS /chat/conversations/{id}/ws?token=` | طبق دسترسی گفتگو | رویدادهای زنده |
| `GET /admin/users` , `PATCH /admin/users/{id}/role` , `GET /admin/documents` | admin / super_admin | مدیریت |
| `GET /health` | عمومی | سلامت سرویس |

خطاها: `400` درخواست نامعتبر، `401` احراز هویت، `403` دسترسی، `404` پیدا نشد، `409` تکراری.
مستندات تعاملی و کامل اسکیماها: `/docs` (Swagger) روی خود سرور.

---

## ۷. تنظیمات (متغیرهای محیطی)

نمونه‌ی کامل در `.env.example`. مهم‌ترین‌ها:

| متغیر | کاربرد |
|---|---|
| `DATABASE_URL`, `REDIS_URL` | اتصال به Postgres و Redis |
| `JWT_SECRET_KEY` | **حتماً در production عوض شود** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | عمر توکن‌ها (۳۰ دقیقه / ۳۰ روز) |
| `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | مدل چت (سازگار با OpenAI) |
| `LLM_DISABLE_THINKING`, `LLM_STRIP_CONTENT_TAGS` | حذف «فکر کردن» مدل‌های reasoning از خروجی |
| `EMBEDDING_API_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` | مدل embedding (پیش‌فرض bge-m3 با ۱۰۲۴ بعد) |
| `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS` | اندازه‌ی تکه‌ها |
| `RETRIEVAL_TOP_K`, `RETRIEVAL_SCORE_THRESHOLD` | تعداد نتیجه و آستانه‌ی شباهت |
| `AI_TRIGGER_TOKEN` | پیشوند صدا زدن AI در چت گروهی (`@bot`) |
| `MAX_UPLOAD_SIZE_MB`, `UPLOAD_DIR` | آپلود |
| `CORS_ORIGINS` | آدرس‌های مجاز فرانت |
| `REQUEST_LOGGING_ENABLED` | فعال/غیرفعال کردن لاگ ساخت‌یافتهٔ تمام درخواست‌ها و پاسخ‌های HTTP در CLI (پیش‌فرض `true`) |
| `REQUEST_LOG_BODY_LIMIT_BYTES` | سقف ثبت بدنهٔ هر درخواست/پاسخ؛ دادهٔ بیشتر به‌صورت truncated مشخص می‌شود (پیش‌فرض ۶۵۵۳۶ بایت) |

> تغییر `EMBEDDING_DIMENSIONS` بعد از ایندکس اسناد، ستون برداری را ناسازگار می‌کند و نیاز به migration و ایندکس مجدد دارد.

لاگ ترافیک با دو رویداد `HTTP_REQUEST` و `HTTP_RESPONSE` و یک `request_id` مشترک در خروجی backend نوشته می‌شود. متد، مسیر، query، headerها، status، زمان پاسخ و بدنهٔ JSON در آن موجود است؛ فیلدهای حساس مانند Authorization، cookie، password، secret و token به‌طور خودکار با `[REDACTED]` جایگزین می‌شوند. آپلودهای multipart به‌جای محتوای باینری با نام فیلدها، نام فایل و اندازه گزارش می‌شوند.

---

## ۸. اجرا، migration، تست، deploy

**اجرا با Docker Compose** (از ریشه‌ی پروژه):
```
docker compose up -d postgres redis
docker compose --profile app up -d --build backend worker
```
کانتینر backend هنگام استارت `alembic upgrade head` را اجرا می‌کند.

**Migration دستی:** `alembic upgrade head` (داخل `Backend/`).
- `0001_init`: ساختار اولیه (تیم و سند).
- `0002_projects_chat_roles`: پروژه‌ها، چت گروهی، `super_admin`، refresh token؛ داده‌های قبلی را نگه می‌دارد (اسناد هر تیم به یک پروژه‌ی «General» منتقل می‌شوند). برگشت‌ناپذیر است.
- **هیچ‌وقت migration اجراشده را ویرایش نکنید؛ برای هر تغییر schema یک فایل جدید بسازید.**

**تست:** `pytest` (Postgres با pgvector لازم است). تست‌ها روی دیتابیس جدا با نام `<db>_test` (یا `TEST_DATABASE_URL`) اجرا می‌شوند و روی دیتابیس دیگر از کار خودداری می‌کنند. LLM و embedding داخل تست‌ها stub هستند. تست‌ها شامل احراز هویت، refresh token، چت شخصی و گروهی، اسناد، تیم/پروژه/قطع دسترسی، ترتیب catch-up و تطابق migration با مدل‌هاست.

**Deploy:** GitHub Actions (`.github/workflows/deploy.yml`) بعد از push به `main`: `git pull` روی سرور، اجرای migration، ساخت مجدد backend و worker، سپس بیلد و ریستارت فرانت.

---

## ۹. محدودیت‌های فعلی و کارهای پیشنهادی

- **بدون OCR**: PDFهای اسکن‌شده و تصویر پردازش نمی‌شوند؛ فرمت‌های `.doc/.xls/.ppt` قدیمی هم پشتیبانی نمی‌شوند.
- **بازیابی فقط برداری** است (بدون BM25/hybrid و بدون re-ranking).
- **بدون rate limiting** و بدون قفل تلاش ناموفق لاگین.
- **بدون بازیابی رمز عبور**، ثبت‌نام عمومی باز است (هر کسی می‌تواند حساب `user` بسازد که تا اضافه نشود به چیزی دسترسی ندارد)، و API حذف/غیرفعال‌کردن کاربر وجود ندارد.
- **توکن WebSocket در query string** است (محدودیت مرورگر)؛ لاگ‌های reverse proxy را با احتیاط نگه دارید. اتصال WebSocket باز، با حذف کاربر از پروژه فوراً قطع نمی‌شود؛ فقط اتصال‌های جدید رد می‌شوند.
- ذخیره‌ی فایل روی دیسک محلی است (نه object storage).
- `created_at` پیام‌ها زمان شروع transaction دیتابیس است؛ ترتیب دقیق پیام‌های هم‌زمان با `id` مشخص می‌شود و لزوماً ترتیب واقعی commit نیست.
- تست WebSocket واقعی (با Redis) هنوز نوشته نشده است.
- **فرانت هنوز با قرارداد جدید هماهنگ نشده** (مسیرهای `/documents` و `/admin/teams` قدیمی، فیلد `sender_type`، نقش `super_admin`، refresh token، چت گروهی). Taha مسئول آن است.
