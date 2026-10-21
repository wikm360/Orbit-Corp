# مرجع پیکربندی (متغیرهای محیطی)

منبع: `app/core/config.py` (`Settings`, pydantic-settings؛ نام env = نام فیلد به حروف بزرگ، `extra="ignore"`، فایل `.env` در cwd). نمونه: `.env.example`. `get_settings()` با `lru_cache` است → **تغییر env نیازمند restart process است**. برخی مقادیر در زمان import خوانده می‌شوند (`engine`, `Queue`, `ToolRegistry`).

## App
| env | پیش‌فرض | توضیح |
|---|---|---|
| `APP_NAME` | Organization RAG Assistant | عنوان FastAPI |
| `ENVIRONMENT` | development | فعلاً فقط برچسب (کدی به آن شاخه نمی‌زند) |
| `DEBUG` | true | `FastAPI(debug=…)` و `echo` SQLAlchemy ← **در پروداکشن false** (در غیر این صورت traceback و لاگ SQL) |
| `API_PREFIX` | /api/v1 | |
| `REQUEST_LOGGING_ENABLED` | true | middleware لاگ ترافیک (در prod compose: false) |
| `REQUEST_LOG_BODY_LIMIT_BYTES` | 65536 | سقف ضبط بدنه |
| `CORS_ORIGINS` | لیست localhost + چند IP | CSV یا JSON array؛ در پروداکشن فقط origin واقعی https. (پیش‌فرض کد شامل IPهای قدیمی سرور است؛ حتماً با env override کنید) |

## Database / Redis
| env | پیش‌فرض | توضیح |
|---|---|---|
| `DATABASE_URL` | postgresql+asyncpg://postgres:postgres@localhost:5432/org_rag | در compose بازنویسی می‌شود |
| `REDIS_URL` | redis://localhost:6379/0 | در prod با رمز |
| `INGESTION_QUEUE_NAME` | ingestion | نام صف RQ |
Engine: `pool_pre_ping=True`, `pool_recycle=1800`, `echo=settings.debug`.

## Auth
`JWT_SECRET_KEY` (پیش‌فرض ناامن، **باید عوض شود**) · `JWT_ALGORITHM`=HS256 · `ACCESS_TOKEN_EXPIRE_MINUTES`=30 · `REFRESH_TOKEN_EXPIRE_DAYS`=30.

## ذخیره‌سازی و آپلود
`UPLOAD_DIR`=`./data/uploads` (در Docker `/app/data/uploads`، volume `uploads_data`، owner uid 10001) · `MAX_UPLOAD_SIZE_MB`=50 · `MAX_BATCH_UPLOAD_FILES`=20.

## Embedding
| env | پیش‌فرض | |
|---|---|---|
| `EMBEDDING_API_BASE_URL` | https://api.example.com/v1 | endpoint سازگار با `/embeddings` |
| `EMBEDDING_API_KEY` | "" | |
| `EMBEDDING_MODEL` | bge-m3 | ذخیره در `documents.embedding_model`؛ تغییر آن باعث می‌شود dedup از کپی chunk استفاده نکند و دوباره embed شود |
| `EMBEDDING_SEND_DIMENSIONS` | false (true = فیلد `dimensions` هم در درخواست فرستاده شود؛ برای `text-embedding-3-large` روی ستون ۱۵۳۶ لازم است) |
| `EMBEDDING_DIMENSIONS` | 1536 | ⚠️ ابعاد ستون‌های vector از همین مقدار در زمان migration ساخته می‌شود؛ تغییر بعد از ایندکس = ناسازگار |

## LLM
| env | پیش‌فرض | |
|---|---|---|
| `LLM_API_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | OpenAI / "" / gpt-4o | مدل چت agent (باید tool-calling و stream داشته باشد) |
| `LLM_DISABLE_THINKING` | false | `extra_body.enable_thinking=false` برای مدل‌های reasoning (Qwen3…)؛ برای OpenAI خاموش بماند |
| `LLM_STRIP_CONTENT_TAGS` | [] | نام تگ‌هایی (بدون <>) که بلوکشان از stream حذف شود (`thought`) |
| `LLM_VISION_MODEL` | None→`LLM_MODEL` | مدل OCR تصاویر و صفحات. پیشنهاد: `gemini-3.5-flash-lite` (روی کثیف‌ترین اسکن شرکت ۵۷/۵۸ عدد درست در ~۱۲ثانیه در برابر ۲۳/۵۸ برای gpt-4.1-mini؛ جدول در ops/retrieval-evaluation.md). مدل reasoning نگذارید |
| `LLM_SQL_MODEL` | None→`LLM_MODEL` | مدل نوشتن SQL |
OCR و SQL از همان `LLM_API_BASE_URL`/`LLM_API_KEY` استفاده می‌کنند (provider جدا برای هر کدام وجود ندارد).

## Ingestion / chunk / retrieval
| env | پیش‌فرض |
|---|---|
| `OCR_ENABLED` | true |
| `OCR_MAX_IMAGES_PER_DOC` | 50 |
| `OCR_MIN_IMAGE_DIMENSION` | 60 (px؛ تصاویر کوچک‌تر نادیده) |
| `OCR_REPLACE_BAD_TEXT_LAYER` | true (صفحه‌ی PDF با لایه‌ی متنی خراب با OCR صفحه جایگزین شود) |
| `OCR_MAX_REPLACED_PAGES` | 300 (هر صفحه یک فراخوانی vision = هزینه/زمان) |
| `OCR_CONCURRENCY` | 12 (صفحه‌ی هم‌زمان در یک سند؛ بار واقعی = `WORKER_REPLICAS` × این عدد؛ با 429 کمش کنید) |
| `PDF_RENDER_DPI` | 200 (رزولوشن رندر صفحات PDF با pdftoppm برای OCR شفاف ارقام و جداول) |
| `OCR_MAX_IMAGE_DIMENSION` | 2560 (سقف ابعاد تصویر برای حفظ وضوح سلول‌های جدول و اعشار) |
| `OCR_JPEG_QUALITY` | 95 (کیفیت تصویر بهینه‌شده برای حذف نویز فشرده‌سازی اطراف اعداد) |
| `EMBEDDING_CONCURRENCY` | 4 (دسته‌ی ۶۴تایی embedding هم‌زمان در یک سند؛ بار واقعی = `WORKER_REPLICAS` × این عدد؛ با 429 کمش کنید) |
| `OCR_MAX_TOKENS` | 6000 (سقف خروجی هر فراخوانی vision؛ قبلاً ثابت ۲۰۴۸ بود و صفحه‌ی جدول متراکم را (~۲٫۵–۳k توکن) می‌برید. مدل reasoning نگذارید: بودجه را صرف تفکر می‌کند و متنی برنمی‌گرداند) |
| `PDF_PARSE_WORKERS` | 4 (process برای parse صفحات یک PDF؛ decode تصاویر اسکن CPU-bound است؛ ۱ = تک‌process؛ فقط برای PDFهای ≥۸ صفحه؛ بار واقعی CPU = `WORKER_REPLICAS` × این عدد) |
| `INGESTION_JOB_TIMEOUT_SECONDS` | 3600 (timeout job RQ برای یک سند) |
| `CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS` | 500 / 50 |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_SCORE_THRESHOLD` | 5 / 0.3 (آستانه‌ی cosine؛ chunk پیداشده‌ی واژگانی از آن معاف است) |
| `SEARCH_PAGE_EXPANSION_MAX_TOKENS` | 6000 (بودجه‌ی متن صفحه‌ی کامل در هر `search_knowledge_base`؛ ۰ = گسترش خاموش و فقط chunk) |
| `RETRIEVAL_HYBRID_ENABLED` | true (false = فقط برداری، مثل قبل) |
| `RETRIEVAL_CANDIDATES` | 30 (کاندیدا از هر رتبه‌بندی پیش از ادغام) |
| `RETRIEVAL_RRF_K` | 60 |
| `RETRIEVAL_LEXICAL_MIN_TERM_HITS` | 2 (حداقل کلمه‌ی متمایز پرسش در chunk برای match واژگانی) |
| `RETRIEVAL_TRIGRAM_ENABLED` | true |
| `RETRIEVAL_TRIGRAM_MAX_TERMS` | 3 (فقط پرسش کوتاه) |
| `RETRIEVAL_TRIGRAM_THRESHOLD` | 0.65 (`word_similarity`) |
| `RETRIEVAL_RERANK_ENABLED` | false (true = LLM re-rank کاندیدای hybrid؛ یک فراخوانی LLM در هر جست‌وجو؛ ← ops/retrieval-evaluation.md) |
| `LLM_RERANK_MODEL` | None → `LLM_MODEL` (پیشنهاد: مدل کوچک و سریع مثل `gpt-4.1-mini`) |
| `RETRIEVAL_RERANK_CANDIDATES` | 20 (کاندیدای ارسالی به re-ranker) |
| `RETRIEVAL_RERANK_PASSAGE_CHARS` | 600 (حداکثر نویسه‌ی هر کاندیدا در prompt) |
| `RETRIEVAL_RERANK_TIMEOUT_SECONDS` | 30 (بعد از آن بدون re-rank برمی‌گردد) |

## چت
`AI_TRIGGER_TOKEN`=`@bot` (پیشوند صدا زدن AI در گروه؛ در build فرانت هم باید یکی باشد — `NEXT_PUBLIC_AI_TRIGGER_TOKEN`).

## دیتابیس راهکاران (connector)
| env | پیش‌فرض | |
|---|---|---|
| `RAHKARAN_DB_ENABLED` | false | **سوییچ اصلی**: ثبت ابزار `ask_accounting_db` + بند system prompt |
| `RAHKARAN_DB_HOST` / `_PORT` / `_NAME` | mssql / 1433 / MehvarGostar | |
| `RAHKARAN_DB_USER` / `_PASSWORD` | rahkaran_ai_reader / "" | |
| `RAHKARAN_DB_QUERY_TIMEOUT_SECONDS` | 60 | |
| `RAHKARAN_DB_MAX_ROWS` | 500 | سقف سخت ردیف از SQL Server (`SET ROWCOUNT`) |
| `RAHKARAN_DB_ROWS_TO_MODEL` | 60 | ردیف‌هایی که مدل می‌بیند |
| `RAHKARAN_SQL_MAX_ATTEMPTS` | 3 | تلاش تولید/تعمیر SQL |
| `RAHKARAN_HINTS_TOP_K` | 8 | |
| `RAHKARAN_ARTIFACT_MAX_ROWS` | 100 | ردیف ذخیره‌شده در پیام برای UI |
| `RAHKARAN_EXPORT_MAX_ROWS` | 5000 | سقف export Excel/CSV |
هیچ اعتبارسنجی در startup وجود ندارد (فعال با رمز خالی تا اولین پرسش خطا نمی‌دهد).

## فقط Docker/compose (توسط خود اپ خوانده نمی‌شود)
`POSTGRES_USER, POSTGRES_PASSWORD (الزامی), POSTGRES_DB` · `REDIS_PASSWORD` (prod الزامی) · `RAHKARAN_SA_PASSWORD` (الزامی، قوی) · `MSSQL_PID` (Express پیش‌فرض؛ Developer فقط توسعه) · `RAHKARAN_BACKUP_DIR` (پیش‌فرض `./data/rahkaran-backups`) · `WORKER_REPLICAS` (3) · `BIND_IP` (127.0.0.1) · `PUBLIC_PORT` (443) · `SITE_ADDRESS` (localhost) · `CADDY_CONFIG` (`Caddyfile` یا `Caddyfile.http`).
در prod compose: `RAHKARAN_SA_PASSWORD`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` برای کانتینرهای اپ **خالی** می‌شوند.
`.env.example` پیش‌فرض‌های `ENVIRONMENT=production`, `DEBUG=false`, `REQUEST_LOGGING_ENABLED=false` را در انتهای بلوک docker هم دارد.

## فقط تست / ابزار
`TEST_DATABASE_URL` (اگر نبود `<DB>_test` روی همان سرور) · برای `sql/rahkaran/*`: `RAHKARAN_SA_PASSWORD, RAHKARAN_AI_PASSWORD, RAHKARAN_AI_USER, RAHKARAN_HOST, RAHKARAN_PORT(14330 محلی), RAHKARAN_DB, RAHKARAN_SKIP_TF4138, RAHKARAN_BACKUP_LOCAL_DIR, RAHKARAN_BACKUP_SQL_DIR, RAHKARAN_SET_READ_ONLY, RAHKARAN_QUESTIONS_OUT`.

## فایل‌های env موجود در پوشه
`.env` (توسعه)، `.env.example` (نمونه، در git)، `.env.production` و `.env.production.bak-*` (نسخه‌های پروداکشن؛ **حاوی secret واقعی، در git نیستند**؛ `.gitignore` همه‌ی `.env*` به‌جز `.env.example` را نادیده می‌گیرد).
