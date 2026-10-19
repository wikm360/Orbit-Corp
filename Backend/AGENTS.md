# Backend — راهنمای AI agent و توسعه‌دهندگان

مستندات کامل، به‌روز و فارسی (با اصطلاحات فنی انگلیسی) این پروژه در **[`.agents/`](.agents/README.md)** است. قبل از هر تغییر آن را بخوانید.

## حداقلِ لازم قبل از شروع
1. [`.agents/README.md`](.agents/README.md) — فهرست و «برای X کدام فایل را بخوانم».
2. [`.agents/03-access-control.md`](.agents/03-access-control.md) — مدل دسترسی؛ هر endpoint/ابزار جدید باید با آن سازگار باشد.
3. [`.agents/conventions.md`](.agents/conventions.md) — قواعد کد و کارهایی که نباید کرد.
4. [`.agents/known-issues.md`](.agents/known-issues.md) — مشکلات شناخته‌شده و وضعیت امنیتی.

## قواعد سخت (خلاصه)
- migration اجراشده را هرگز ویرایش نکنید؛ تغییر schema = migration جدید.
- هر query روی `DocumentChunk`/اسناد باید از `accessible_documents_filter` بگذرد.
- SQL تولیدشده توسط مدل فقط پس از `validate_sql` و فقط با کاربر فقط‌خواندنی روی schema `ai`.
- در پروداکشن هرگز `docker compose up` بدون `-f docker-compose.yml -f docker-compose.prod.yml` و هرگز `down -v`.
- `.env*`، `*.bak`، `data/` را commit نکنید.
- بعد از هر تغییر رفتار، `.agents/` را به‌روز کنید (کد درست است و مستند تابع آن).

## دستورهای متداول
```bash
docker compose up -d postgres redis && pytest        # تست (Postgres+pgvector لازم است)
alembic upgrade head                                  # migration
uvicorn app.main:app --reload                         # API
python -m workers.ingestion_worker                    # worker ingestion
```
فرانت‌اند: `../Frontend/AGENTS.md`.
