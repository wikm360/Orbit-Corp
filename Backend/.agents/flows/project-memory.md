# جریان: حافظه‌ی پروژه (project memory)

فایل‌ها: `features/memory/{models,schemas,service,router}.py`, `features/agent/tools/memory_tools.py`.

## مفهوم
حقایق/تصمیم‌هایی که تیم از AI می‌خواهد «به یاد بسپارد» و در همه‌ی گفتگوهای همان پروژه (مشترک، نه per-conversation) با جست‌وجوی معنایی بازیابی می‌شوند.
دسته‌ها (`MemoryCategory`): `technical_decision`, `timeline`, `business_rule`, `convention`.

## نوشتن
- **از چت**: ابزار `remember_project_insight(fact, category)` — به‌صراحت در توضیح ابزار آمده «فقط وقتی کاربر خواسته». `memory_service.remember`: embedding از `fact_text` + ذخیره در `project_memories` با `created_by_user_id`.
- **از REST** (فقط manager): `POST /projects/{id}/memories`.
دسترسی ابزار: `project_id = resolve_retrieval_scope(...)`؛ اگر گفتگو به پروژه‌ای وصل نیست متن «This conversation isn't linked to any project.». ⚠️ هر عضو پروژه (حتی عضو ساده) می‌تواند از طریق چت حافظه بنویسد، در حالی که مدیریت REST فقط leader/admin است.

## خواندن
- **از چت**: `recall_project_insights(query, category?)` → `memory_service.recall`: embedding پرسش، `ORDER BY cosine_distance LIMIT 5` در همان پروژه (و دسته‌ی اختیاری). خروجی JSON `[{fact, category, is_verified}]`. **آستانه‌ی شباهت ندارد** (حتی نامرتبط‌ترین ۵ مورد را هم برمی‌گرداند اگر حافظه باشد).
- **REST**: `GET /projects/{id}/memories` (manager؛ مرتب نزولی بر `created_at`).

## ویرایش/حذف (manager)
- `PATCH /projects/{id}/memories/{mid}` — `fact_text`/`category`/`is_verified` اختیاری. تغییر `fact_text` **embedding را دوباره می‌سازد** (وگرنه جست‌وجو روی متن قدیمی match می‌کند).
- `DELETE …/{mid}` (204). بررسی `memory.project_id == project.id` (وگرنه 400).

## نکات
- `is_verified` را فقط manager تنظیم می‌کند؛ ابزار recall آن را به مدل نشان می‌دهد تا بداند چه چیزی تأییدشده است.
- `confidence_score` وجود دارد اما هیچ‌جا مقداردهی/مصرف نمی‌شود.
- هیچ dedup/محدودیت تعدادی وجود ندارد.
- تست‌ها: `tests/features/memory/test_memory.py`, `test_memory_router.py`.
