# ۰۱ — نمای کلی

## هدف محصول
پلتفرم **RAG سازمانی** برای «شرکت محور گستر نصر» (پیمانکار راه‌سازی/آسفالت/معدن):
- مدیریت سازمان: کاربر ← تیم ← پروژه، با نقش‌های سراسری و نقش داخل تیم.
- پایگاه دانش هر پروژه: اسناد (PDF/DOCX/PPTX/XLSX/TXT/تصویر) → متن → chunk → embedding → pgvector.
- چت با AI: شخصی (۱:۱، SSE) و گروهی پروژه (WebSocket، AI با `@bot` صدا زده می‌شود).
- AI یک **agent** با ابزار است، نه یک RAG ساده: خودش تصمیم می‌گیرد جست‌وجو کند، سند بخواند، حافظه بخواند/بنویسد یا از دیتابیس حسابداری بپرسد.
- اتصال به دیتابیس **حسابداری راهکاران** (Text-to-SQL ایمن، فقط‌خواندنی).

## Stack
| لایه | فناوری |
|---|---|
| API | FastAPI 0.115 (Python 3.12)، uvicorn، pydantic v2 / pydantic-settings |
| ORM / migration | SQLAlchemy 2.0 async (asyncpg)، Alembic |
| دیتابیس اصلی | PostgreSQL 16 + pgvector (ایندکس HNSW، cosine) |
| صف / pub-sub | Redis 7 — صف `RQ` برای ingestion، pub/sub برای WebSocket چت گروهی |
| LLM / Embedding | هر سرویس سازگار با OpenAI (`openai` SDK برای chat، `httpx` برای `/embeddings`)؛ پیش‌فرض embedding مدل `bge-m3` |
| OCR | همان LLM با مدل vision (`LLM_VISION_MODEL`) روی تصاویر |
| تجزیه‌ی فایل | pypdf، python-docx، python-pptx، openpyxl، Pillow، `pdftoppm` (poppler-utils) |
| chunking | tiktoken `cl100k_base` (با fallback شمارش کلمه) |
| دیتابیس حسابداری | SQL Server 2022 (Express) با `pymssql`؛ اعتبارسنجی SQL با `sqlglot` (dialect `tsql`) |
| Edge | Caddy 2 (TLS داخلی یا HTTP ساده)، reverse proxy برای `/api` و فرانت |
| تست | pytest + pytest-asyncio (Postgres واقعی) |

## سرویس‌های runtime
| سرویس | فرمان | نقش |
|---|---|---|
| `backend` | `uvicorn app.main:app --port 8000` | همه‌ی endpointها، SSE، WebSocket |
| `worker` (چند replica، پیش‌فرض ۳) | `python -m workers.ingestion_worker` | پردازش ingestion اسناد از صف RQ |
| `migrate` | `alembic upgrade head` | یک‌بار هنگام `up`، قبل از backend/worker |
| `postgres` | pgvector/pgvector:0.8.7-pg16 | دیتابیس اصلی |
| `redis` | redis:7.4 | صف + pub/sub |
| `mssql` | SQL Server 2022 | دیتابیس راهکاران (volume خارجی `rahkaran_mssql_data`) |
| `rahkaran-refresh` | `python sql/rahkaran/refresh.py` | job یک‌باره: ریستور آخرین `.bak` و اعمال لایه‌ی `ai` |
| `frontend` | Next.js | (فقط پروداکشن در compose) |
| `caddy` | Caddy | تنها سرویس با پورت منتشرشده در پروداکشن |

جزئیات در [ops/infra-and-deploy.md](ops/infra-and-deploy.md).

## نقشه‌ی کلی
```
 مرورگر/فرانت ──HTTPS──► Caddy ──/api──► backend (FastAPI)
                                    └──/──► frontend (Next.js)

 backend ──► Postgres+pgvector   (users, teams, projects, documents, chunks, chat, memory, hints, logs)
 backend ──► Redis               (enqueue ingestion job ; pub/sub برای WS ; publish از worker)
 backend ──► LLM API             (chat completions با stream + tools)
 backend ──► Embedding API       (/embeddings)
 backend ──► SQL Server `ai`.*   (فقط SELECT، فقط از ابزار ask_accounting_db و export)

 worker  ◄── Redis (RQ) ;  worker ──► Embedding API, LLM Vision (OCR), Postgres, دیسک (data/uploads)
 rahkaran-refresh ──► SQL Server (RESTORE از data/rahkaran-backups, apply.py)
```

## ساختار پوشه‌ها (سطح بالا)
```
Backend/
├── app/                 کد اپلیکیشن (core، features، providers، main.py)
├── workers/             نقطه‌ی ورود worker (RQ)
├── alembic/             env + ۷ migration
├── tests/               ۱۲۶ تست، روی Postgres واقعی
├── sql/rahkaran/        لایه‌ی معنایی `ai` (SQL، توضیحات، hints، نمونه‌سؤال‌ها، refresh/apply)
├── docs/rahkaran/       مستندات دامنه‌ی دیتابیس راهکاران (حجیم، بخشی تولید خودکار)
├── infra/caddy/         Dockerfile و Caddyfileها
├── data/uploads/        فایل‌های آپلودشده (+ فایل‌های `.reconstructed.*`) — gitignore
├── data/rahkaran-backups/  محل ریختن .bak شرکت — gitignore
├── Dockerfile, docker-compose{,.override,.prod}.yml
└── .agents/             همین مستندات
```
جزئیات فایل‌به‌فایل: [reference/modules.md](reference/modules.md).

## مفاهیم کلیدی (واژه‌نامه‌ی پروژه)
| اصطلاح | معنی |
|---|---|
| **Conversation** | یک گفتگو. `type=personal` (مال یک کاربر) یا `project_group` (مال یک پروژه). |
| **Message** | پیام در گفتگو؛ `sender_type=user/assistant`؛ فیلدهای JSONB: `sources` (استنادها) و `artifacts` (شواهد ساخت‌یافته‌ی ابزارها، مثل نتیجه‌ی SQL). |
| **Scope سند** | هر سند دقیقاً به یکی از «پروژه» یا «گفتگو» تعلق دارد (CHECK constraint). کتابخانه‌ی شخصی وجود ندارد. |
| **linked_project_id** | پروژه‌ای که یک چت شخصی «برای RAG» به آن وصل شده؛ دسترسی نمی‌دهد، فقط منبع جست‌وجو را تعیین می‌کند و عضویت هر بار دوباره چک می‌شود. |
| **UserContext** | شیء درخواست-محور: کاربر + `team_ids`/`led_team_ids`/`project_ids`؛ پایه‌ی همه‌ی چک‌های دسترسی. |
| **Agent / Tool** | `AgentEngine` حلقه‌ی tool-calling را اجرا می‌کند؛ هر `BaseTool` در `ToolRegistry` ثبت می‌شود. |
| **Artifact** | خروجی ساخت‌یافته‌ی ابزار برای UI (فعلاً فقط `sql_result`). |
| **Hint (schema hint)** | یک chunk دانش درباره‌ی دیتابیس راهکاران (view، مثال، اصطلاح، یادداشت، taxonomy) برای ساخت prompt تولید SQL. |
| **لایه‌ی `ai`** | schema با ۸۴ view روی دیتابیس راهکاران؛ تنها چیزی که کاربر SQL (reader) می‌تواند ببیند. |
| **حافظه‌ی پروژه (project memory)** | واقعیت‌ها/تصمیم‌هایی که agent به درخواست کاربر برای پروژه ذخیره می‌کند و بعداً با جست‌وجوی معنایی بازیابی می‌کند. |
| **`@bot`** | `AI_TRIGGER_TOKEN`؛ پیشوندی که در چت گروهی agent را فرا می‌خواند (case-insensitive). |

## زبان و محلی‌سازی
- کاربران فارسی‌زبانند؛ پرامپت‌های حوزه‌ی مالی و OCR فارسی‌اند. پاسخ‌های خطای API و پرامپت‌های عمومی انگلیسی‌اند.
- مبالغ حسابداری **ریال** است؛ نمایش به تومان/میلیارد تومان در لایه‌ی formatter و پرامپت انجام می‌شود.
- تاریخ‌های حسابداری شمسی؛ سال مالی از ۱ مهر تا ۳۱ شهریور (`fiscal_year 1404` = مهر ۱۴۰۴ تا شهریور ۱۴۰۵).
