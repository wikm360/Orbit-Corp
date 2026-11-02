# سقف مصرف توکن هر کاربر (`app/features/usage/`)

## اندازه‌گیری (ambient، بدون تغییر امضای توابع)
- ورودی هر مسیر `usage_scope(user_id, purpose)` باز می‌کند (contextvar): `AgentEngine.run_agent_loop` (purpose `chat`، چت شخصی و پاسخ گروهی به نام فرستنده‌ی پیام)، `pipeline.run_report` (`vr_agent`، به نام کسی که Run/Continue زد؛ `user_id` سومین آرگومان job در RQ است و برای jobهای قدیمی `None`)، `run_ingestion_pipeline` (`ocr`، به نام `uploaded_by`).
- `usage_purpose("sql"|"rerank")` برچسب را داخل همان scope عوض می‌کند (تولید SQL مالی، rerank).
- provider بعد از هر فراخوانی `record_usage` را صدا می‌زند (`llm_provider._meter`، `embedding_provider`، `ocr._meter_vision`). بیرون از scope هیچ‌چیز ثبت نمی‌شود. `record_usage` هرگز exception نمی‌دهد و در session کوتاه جدا commit می‌کند (مصرف نوبت‌های شکست‌خورده هم ثبت می‌شود).
- هر فراخوانی یک ردیف `llm_usage`؛ فقط مصرفِ `counts_toward_quota` با `UPDATE users SET tokens_used = tokens_used + n` اتمیک جمع می‌شود. **`ocr` و `embedding` فقط ثبت می‌شوند و هرگز محدود نمی‌شوند** (قطع وسط ingestion سند را نیمه‌کاره می‌گذارد). توکن = prompt + completion (بدون تخفیف cache؛ `cached_tokens` جدا ثبت می‌شود).
- اگر gateway در پاسخ `usage` ندهد، چیزی ثبت نمی‌شود (کد `include_usage` را می‌فرستد).

## اعمال (نرم)
`ensure_quota(user)` / `is_exhausted` (super_admin هرگز؛ `token_limit` NULL = نامحدود؛ `used >= limit` = تمام). قبل از شروع چت شخصی و Run/Continue گزارش حجم (429، `token_quota_exceeded`)؛ چت گروهی: `_post_quota_notice`. حین کار: `quota_exhausted(user_id)` (خواندن تازه از DB) بین گام‌های موتور (پیام ثابت `_QUOTA_TEXT` بدون فراخوانی اضافه) و بین گام‌های agent گزارش حجم (activity warn + `agent_incomplete`).

## مدیریت
`service.set_limit/extend_limit/reset_usage/usage_report`؛ endpointها در `admin/router.py` (جدول بالا در [03-access-control.md](../03-access-control.md)). ریست فقط `token_period_start` را جلو می‌برد؛ گزارش دوره‌ی جاری از `llm_usage.created_at >= token_period_start` ساخته می‌شود.

## فرانت
`features/admin/components/TokenQuotaControls.tsx` (نوار مصرف، تعیین/تمدید/ریست/حذف، جزئیات مصرف) داخل AdminScreen؛ `features/chat/components/TokenQuotaBanner.tsx` (هشدار ۸۰٪ / تمام‌شدن، با `/auth/me`)؛ `errorMessages.ts` پیام ۴۲۹ سقف را جدا نشان می‌دهد.
