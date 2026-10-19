# راهنما: تغییر schema دیتابیس (Alembic)

> **هرگز migration اجراشده را ویرایش نکنید.** هر تغییر = فایل جدید.

## قدم‌ها
1. مدل را در `models.py` عوض کنید (و در `model_registry.py` ثبت کنید اگر جدید است).
2. فایل `alembic/versions/000N_<name>.py` بسازید. `revision = "000N_<name>"` و `down_revision` = آخرین (در زمان نگارش `0007_message_artifacts`).
   - autogenerate: `alembic revision --autogenerate -m "name"` (روی DB به‌روز) — **خروجی را حتماً بازبینی کنید** (enum، ایندکس HNSW، `server_default`).
3. `upgrade()` و `downgrade()` بنویسید (اگر برگشت‌ناپذیر است مثل 0002 در docstring بگویید).
4. تست: `pytest tests/test_migrations.py` (مقایسه‌ی `upgrade head` با `Base.metadata`).
5. `04-data-model.md` را به‌روز کنید.

## نکات Postgres/pgvector
- Enum جدید: `pg.ENUM(..., name=..., create_type=False)` و `.create(bind, checkfirst=True)`؛ افزودن مقدار به enum موجود: `ALTER TYPE … ADD VALUE IF NOT EXISTS` داخل `with op.get_context().autocommit_block():`.
- ستون vector: `Vector(settings.embedding_dimensions)`؛ ایندکس HNSW با `op.execute("CREATE INDEX … USING hnsw (embedding vector_cosine_ops)")`.
- ستون JSONB با default: `server_default=sa.text("'[]'::jsonb")` (الگو: 0007).
- CHECK constraint را با `drop_constraint` + `create_check_constraint` عوض کنید (الگو: 0003/0005).
- مهاجرت داده در همان migration (الگو: 0002 که پروژه‌ی «General» ساخت).

## تغییر ابعاد embedding
migration دستی: حذف ایندکس‌های HNSW، `ALTER COLUMN embedding TYPE vector(N)` (داده‌ی قدیمی باید پاک/دوباره ساخته شود)، ساخت دوباره‌ی ایندکس، تغییر env، سپس re-ingest اسناد (تنها راه: حذف chunk و retry یا آپلود دوباره)، حافظه‌ها (re-embed) و hint ها (`ingest`).

## اجرا
dev: `alembic upgrade head`. prod: سرویس `migrate` خودکار با `dc up -d --build`.
