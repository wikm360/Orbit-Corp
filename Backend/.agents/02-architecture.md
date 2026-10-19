# ۰۲ — معماری و ساختار کد

## ساختار `app/`
```
app/
├── main.py                 ساخت FastAPI، CORS، middleware لاگ، ثبت routerها، GET /health
├── core/
│   ├── config.py           Settings (pydantic-settings، از env و .env) + get_settings() با lru_cache
│   ├── database.py         async engine، async_session_factory، Base، get_db()
│   ├── dependencies.py     UserContext + همه‌ی dependencyهای احراز هویت/دسترسی
│   ├── security.py         bcrypt، JWT access token، refresh token مبهم + hash
│   ├── exceptions.py       NotFound/Forbidden/Unauthorized/Conflict/BadRequest (HTTPException)
│   ├── model_registry.py   import همه‌ی models برای ثبت روی Base.metadata
│   └── request_logging.py  middleware ASGI لاگ ساخت‌یافته‌ی درخواست/پاسخ (با redact)
├── providers/
│   ├── llm_provider.py     LLMProvider (ABC) + OpenAICompatibleLLMProvider (stream + tools)
│   └── embedding_provider.py  EmbeddingProvider (ABC) + BGEM3EmbeddingProvider (با retry)
└── features/
    ├── auth/  access_control/  projects/  admin/
    ├── documents/ (+ ingestion/)  retrieval/  memory/
    ├── chat/  agent/ (+ tools/)
    └── db_connector/
```

## قرارداد هر feature
پوشه‌ی `app/features/<name>/` معمولاً این فایل‌ها را دارد:
| فایل | مسئولیت |
|---|---|
| `models.py` | مدل‌های SQLAlchemy (ارث از `Base`) |
| `schemas.py` | مدل‌های pydantic برای ورودی/خروجی API (بعضی featureها schema را داخل `router.py` دارند: `access_control`, `projects`) |
| `service.py` | منطق کسب‌وکار؛ توابع async که `db: AsyncSession` می‌گیرند و خودشان `commit` می‌کنند |
| `router.py` | `APIRouter`؛ فقط dependency + فراخوانی service + تبدیل به response |

قواعد رایج:
- **service commit می‌کند** (نه router و نه dependency). `get_db` فقط session می‌دهد.
- UUID همه‌جا کلید اصلی (`PG_UUID(as_uuid=True)`)؛ `created_at` با `server_default=func.now()`.
- Enumها در دیتابیس با `values_callable` روی **مقدار** (`"super_admin"`) ذخیره می‌شوند، نه نام عضو.
- featureها مدل‌های هم را مستقیم import نمی‌کنند مگر لازم؛ `model_registry.py` برای رزولوشن relationshipهای رشته‌ای است و باید هر مدل جدید در آن ثبت شود.
- خطاهای دامنه با استثناهای `app.core.exceptions` بالا می‌آیند (FastAPI آن‌ها را به HTTP تبدیل می‌کند). داخل ابزارهای agent این استثناها گرفته و به متن تبدیل می‌شوند.

## جهت وابستگی‌ها (تقریبی)
```
router ─► service ─► models
core.dependencies ─► access_control.service, projects.service, auth.models
chat.service ─► agent.engine ─► agent.tools.* ─► documents.service, retrieval, memory, projects, db_connector
documents.ingestion.pipeline ─► chat.ws.publish_event (برای اعلان به گفتگو)
db_connector.service ─► hints, generator, sql_validator, executor, summary, formatter, artifacts
```
نکته‌ی دور وابستگی: `core/dependencies.py` از featureها import می‌کند (access_control، projects)؛ و `agent/engine.py` از `core.dependencies.UserContext` استفاده می‌کند. این به‌دلیل جایگاه `UserContext` است؛ import circular را با ترتیب import و عدم import مدل‌های هم‌دیگر در سطح ماژول مدیریت کرده‌اند.

## راه‌اندازی اپ (`app/main.py`)
1. `model_registry` import می‌شود (ثبت همه‌ی مدل‌ها).
2. `FastAPI(title=app_name, debug=settings.debug)` — **docs/openapi در خود اپ غیرفعال نمی‌شود**؛ فقط Caddy در پروداکشن آن‌ها را 404 می‌کند.
3. `CORSMiddleware` با `settings.cors_origins` (`allow_credentials=True`، همه‌ی method/headerها).
4. اگر `request_logging_enabled`: `configure_request_logger()` و `RequestResponseLoggingMiddleware` (جزئیات پایین).
5. روترها با پیشوند `settings.api_prefix` (`/api/v1`) ثبت می‌شوند به ترتیب: auth, teams (access_control), projects, documents, memory, chat, accounting-db (db_connector), admin.
6. `GET /health` (خارج از `/api/v1`) → `{"status":"ok"}`.
در این مرحله هیچ job پس‌زمینه‌ای (startup event) تعریف نشده است.

## Provider ها (تعویض‌پذیری مدل)
- `LLMProvider.stream_chat(messages, tools=None)` → `AsyncIterator[StreamEvent]` که یا `{"type":"content","delta":...}` است یا یک `{"type":"tool_calls","calls":[...]}` نهایی. یک turn هرگز بعد از `tool_calls` محتوای بیشتری نمی‌دهد.
- `OpenAICompatibleLLMProvider`:
  - tool call‌ها را از تکه‌های stream (کلید `index`) تجمیع می‌کند و در پایان با `finish_reason == "tool_calls"` تحویل می‌دهد.
  - `disable_thinking` → `extra_body={"enable_thinking": False}` (برای مدل‌های reasoning مثل Qwen3؛ برای OpenAI واقعی خاموش بماند).
  - `_strip_tag_blocks`: بلوک‌های `<tag>…</tag>` (مثل `<thought>`) از خروجی stream حذف می‌شود (`LLM_STRIP_CONTENT_TAGS`)؛ اگر تگ بسته نشد متن نگه‌داشته‌شده در پایان flush می‌شود.
  - retry شفاف: اگر اتصال قبل از تحویل اولین توکن قطع شود تا ۳ بار با backoff (۱.۵ثانیه × attempt)؛ بعد از شروع تحویل، خطا بالا می‌آید.
- `get_llm_provider()` با `lru_cache`؛ `get_sql_llm_provider()` و `get_rerank_llm_provider()` (مدل `LLM_RERANK_MODEL`) **cache ندارند** و `llm_sql_model or llm_model` را با همان base_url/key می‌سازد.
- `EmbeddingProvider.embed(texts)` → بردارها به همان ترتیب ورودی. `BGEM3EmbeddingProvider` به `POST {base}/embeddings` می‌زند؛ روی 429/5xx و خطاهای transport تا ۵ بار retry با backoff نمایی (۱،۲،۴،۸ ثانیه؛ سقف ۳۰؛ `Retry-After` عددی رعایت می‌شود)؛ timeout هر درخواست ۶۰ثانیه. با `EMBEDDING_SEND_DIMENSIONS=true` فیلد `dimensions` هم فرستاده می‌شود (برای `text-embedding-3-large` روی ستون ۱۵۳۶).
- تست‌ها این providerها را stub می‌کنند (`tests/conftest.py`)؛ هیچ تستی به شبکه نمی‌رود.

## لاگ ترافیک (`core/request_logging.py`)
- middleware خالص ASGI (فقط `http`؛ WebSocket عبور می‌کند). برای هر درخواست `request_id` (uuid4) می‌سازد و دو خط لاگ می‌نویسد: `HTTP_REQUEST` و `HTTP_RESPONSE` (یا `HTTP_ERROR` با traceback کوتاه)، logger با نام `orbit.traffic` روی stdout.
- بدنه‌ی درخواست را کامل buffer می‌کند و با `replay_receive` دوباره به اپ می‌دهد؛ بدنه‌ی پاسخ را chunk به chunk ضبط می‌کند (برای SSE هم کار می‌کند) تا سقف `REQUEST_LOG_BODY_LIMIT_BYTES` (۶۴KB).
- redact: کلید/هدر/query که یکی از `authorization, cookie, password, passwd, secret, token, api_key, apikey` را داشته باشد → `[REDACTED]`. JSON بازگشتی redact می‌شود؛ متن غیر JSON با regex best-effort؛ multipart فقط نام فیلد/فایل/اندازه؛ باینری فقط اندازه.
- هدر `x-request-id` به پاسخ افزوده می‌شود.
- ⚠️ **بدنه‌ی پاسخ‌ها (از جمله جواب‌های مالی در SSE) در لاگ می‌آید.** در پروداکشن `REQUEST_LOGGING_ENABLED=false` است (compose prod). آدرس WebSocket با `?token=` از طریق middleware عبور نمی‌کند ولی در لاگ reverse proxy می‌ماند.

## الگوهای هم‌زمانی مهم
- **session جدا برای کارهای detached**: SSE چت و پاسخ AI در چت گروهی خودشان `async_session_factory()` باز می‌کنند چون session درخواست قبل از شروع body استریم (FastAPI < 0.118) یا بعد از پایان request بسته است. `UserContext` در این حالت از request به task منتقل می‌شود (فقط فیلدهای scalar).
- **صف event با task پس‌زمینه** در SSE: engine در یک `asyncio.Task` اجرا می‌شود و فقط آن task با `db` کار می‌کند؛ حلقه‌ی generator صف event را (poll ۰٫۰۸ثانیه) تخلیه و به SSE تبدیل می‌کند.
- **کدهای sync داخل async**: اجرای SQL Server (`pymssql`) با `asyncio.to_thread`. worker هر job را با `asyncio.run` اجرا می‌کند (RQ برای هر job یک process فرزند fork می‌کند، پس event loop/engine مشترک بین jobها نیست؛ نیاز به تأیید برای حالت‌های غیراستاندارد).
- **Redis در دو شکل**: `chat/ws.py` یک کلاینت async بلندمدت برای پروسه‌ی API دارد؛ `publish_event()` برای worker هر بار کلاینت موقت می‌سازد و می‌بندد. `documents/service.py` یک کلاینت sync (`redis.Redis`) و `Queue` در **زمان import** می‌سازد.
