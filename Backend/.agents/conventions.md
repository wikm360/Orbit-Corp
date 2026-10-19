# قواعد کدنویسی و کارهایی که نباید کرد

برای هر AI agent یا توسعه‌دهنده‌ای که روی `Backend/` کار می‌کند. همنوا با کد موجود بنویسید (تراکم کامنت، نام‌گذاری، سبک).

## سبک و الگو
- Python 3.12، type hints مدرن (`str | None`, `list[...]`)، `from __future__` فقط در جاهایی که قبلاً هست.
- هر feature: `models.py / schemas.py / service.py / router.py`. router باریک؛ منطق در service؛ service خودش `commit` می‌کند.
- SQLAlchemy 2.0 style: `Mapped[...]`, `mapped_column`, `select(...)`, `await db.execute(...)`. کلید UUID. Enum در DB با مقدار (`values_callable`).
- خطا: `from app.core.exceptions import …` (NotFound/Forbidden/BadRequest/Conflict/Unauthorized). پیام انگلیسی کوتاه.
- Async همه‌جا؛ کار sync سنگین (pymssql، parse فایل در worker) یا در thread یا در worker. اجرای blocking داخل handler async ممنوع.
- کامنت‌ها: توضیح *چرا* (قیود، تصمیم، تله) نه *چه*؛ انگلیسی در کد. پرامپت‌های حوزه‌ی مالی/OCR فارسی‌اند.
- تنظیمات جدید → فیلد در `Settings` + `.env.example` + [reference/configuration.md](reference/configuration.md).
- مدل جدید → ثبت در `core/model_registry.py` + migration جدید.
- ایمپورت متقابل مدل‌های featureها را حداقل کنید؛ از رشته در `relationship("TeamMembership")` استفاده شده.

## امنیت (قواعد سخت)
1. هر endpoint جدید **حتماً** dependency دسترسی دارد (`get_current_user_context` + `require_*`) و بررسی مالکیت منبع انجام می‌دهد (مثلاً `memory.project_id == project.id`).
2. دسترسی اسناد فقط از `accessible_documents_filter` / `_get_accessible_document`؛ هیچ query مستقیم روی `DocumentChunk` بدون این فیلتر ننویسید. `conversation_id` را هرگز `None` به فیلتر ندهید.
3. ابزار agent دسترسی را خودش از `context`/`conversation` بسنجد؛ به `document_id`/`project_id` ورودی مدل اعتماد نکنید.
4. هرگز SQL تولیدشده توسط مدل را بدون `validate_sql` اجرا نکنید؛ هرگز اتصال به SQL Server با کاربر غیر `rahkaran_ai_reader` در مسیر اپ نسازید؛ هرگز اجازه ندهید query به غیر از `ai.*` برسد.
5. secret در لاگ/پیام خطا/commit نگذارید. `.env*` و `*.bak` در git نیست و نباید باشد.
6. ورودی کاربر/داده‌ی DB که به prompt می‌رود داده است نه دستور؛ در متن ابزار دستور اجرایی از دل داده‌ها نسازید.
7. WebSocket و HTTP هر دو را در نظر بگیرید؛ قاعده‌ی دسترسی گفتگو در دو جا تکرار شده (`dependencies.require_conversation_access` و `router.conversation_websocket`).

## دیتابیس
- **migration اجراشده را هرگز ویرایش نکنید.** تغییر schema = فایل جدید (`000N_name.py`، `down_revision` درست). ← [guides/add-migration.md](guides/add-migration.md)
- ابعاد vector از `settings.embedding_dimensions` است؛ بدون برنامه‌ی مهاجرت تغییر ندهید.
- `created_at` با `server_default=func.now()`؛ ترتیب پیام `(created_at, id)`.
- برای cascade به `ondelete` در FK تکیه شده؛ ORM `cascade` فقط برای relationshipهای تعریف‌شده.

## agent / LLM
- پرامپت‌ها و رفتار ابزار را با تست‌های `_ScriptedLLMProvider` بپوشانید؛ از LLM واقعی در تست استفاده نکنید.
- ابزار جدید: توضیح `description` دقیق و کوتاه (مدل از آن تصمیم می‌گیرد)؛ خروجی متنی فشرده؛ خطای مورد انتظار را با استثنای `core.exceptions` بالا بدهید (registry به متن تبدیل می‌کند)؛ خروجی بزرگ را سقف بزنید.
- تغییر `MAX_STEPS`، سقف تاریخچه (۳۰)، یا فرمت `StreamEvent` روی `chat/service` و تست‌ها اثر دارد.

## تست
- هر رفتار جدید تست دارد؛ تست دسترسی منفی (403/404) برای هر قاعده‌ی دسترسی. ← [ops/testing.md](ops/testing.md)
- تست‌ها DB را در هر تست reset می‌کنند؛ به داده‌ی باقی‌مانده تکیه نکنید.

## git
- commit پیام‌ها کوتاه (سبک تاریخچه: `fixCaddyUp`, `1.72`)؛ فقط فایل‌های مرتبط را `git add` کنید (`Assets/`، `data/`، `.env*` نه).
- روی `main` push = deploy خودکار فرانت روی سرور (← [ops/infra-and-deploy.md](ops/infra-and-deploy.md)). قبل از push مطمئن شوید فرانت build می‌شود.

## کارهایی که نباید کرد (خلاصه)
- ❌ ویرایش migration اجراشده · ❌ `docker compose down -v` روی prod · ❌ `docker compose up` بدون `-f` روی prod
- ❌ باز کردن پورت DB/Redis به بیرون · ❌ `BIND_IP=0.0.0.0` · ❌ commit کردن `.env`/`.bak`
- ❌ query روی chunk بدون فیلتر دسترسی · ❌ اجرای SQL مدل بدون validator
- ❌ تغییر `EMBEDDING_DIMENSIONS` بدون migration/ایندکس مجدد · ❌ فراموش کردن `ingest` hint ها بعد از `build_hints`
- ❌ مستند را به‌روز نکردن (`.agents/`) بعد از تغییر رفتار
