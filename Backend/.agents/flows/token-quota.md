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

## هزینه‌ی دلاری (migration `0026`، فقط پایش؛ هنوز چیزی با هزینه بسته نمی‌شود)
- `record_usage` هزینه‌ی هر فراخوانی را به **micro-USD** (توکن × قیمت هر میلیون = micro-USD) حساب و در `llm_usage.cost_micro_usd` ذخیره می‌کند (snapshot؛ تغییر قیمت تاریخچه را عوض نمی‌کند). `billed_to` فعلاً همیشه `user` است (برای استخر راه‌اندازی در آینده).
- قیمت‌ها در جدول `model_prices` (کلید = نام دقیق مدل همان‌طور که gateway گزارش می‌دهد؛ پیشوند vendor و حروف بزرگ/کوچک نادیده گرفته می‌شود) و cache ۶۰ثانیه‌ای در `usage/pricing.py`. مدل ناشناخته = گران‌ترین قیمت جدول (نه صفر) + هشدار لاگ؛ جدول خالی = ۰. جمع به بالا رُند می‌شود. migration سه قیمت جاری را seed و تاریخچه‌ی هم‌نام را back-fill کرد.
- endpoint: `GET /admin/model-prices` (admin+)، `PUT|DELETE /admin/model-prices/{model}` (**فقط super_admin**)، `GET /admin/usage/cost-summary?days=` (admin+؛ جمع و تفکیک هدف/مدل/کاربر)، و `GET /admin/users/{id}/token-usage` اکنون `cost_usd`، `by_model` و `cost_usd` هر هدف را هم دارد.

## سقف دلاری (migration `0027`؛ `usage/quota.py`)
- **سه پنجره** برای هر کاربر: ۵ ساعت و ۷ روز **شناور**، و **ماه شمسی** (از ۰۰:۰۰ اول ماه شمسی به وقت تهران؛ تبدیل تاریخ در همان فایل پیاده شده، بدون وابستگی). مصرف = جمع `llm_usage.cost_micro_usd` (چت، SQL، rerank، گزارش حجم، **OCR و embedding هم**) با `billed_to='user'`، از `max(شروع پنجره, users.token_period_start)`؛ پس «ریست» هر سه پنجره را از نو شروع می‌کند. طول پنجره‌ها در کد ثابت است؛ **همه‌ی عددها در DB** و فقط با super_admin قابل تغییر.
- **پلن هر نقش** `quota_plans` (`user`: ۰٫۴۵/۱٫۵/۴٫۵$، `admin`: ۱٫۵/۵/۱۵$ — seed اولیه) و **override هر کاربر** (`users.quota_five_hour/weekly/monthly_override`، `quota_unlimited`؛ NULL = از پلن). super_admin هرگز محدود نمی‌شود و override برایش 400 است. ترتیب سقف‌ها: ۵ساعت ≤ هفته ≤ ماه.
- **سوئیچ `quota_config.enforced`** (پیش‌فرض **false = shadow**: هزینه ثبت و نمایش داده می‌شود ولی چیزی با هزینه بسته نمی‌شود). با true: `enforce_quota(user)` قبل از چت شخصی، Run/Continue گزارش حجم، **آپلود سند** (پروژه/گفتگو، تک و batch) و بین گام‌های agent → ۴۲۹ `token_quota_exceeded` با هدر `X-Quota-Window` (`five_hour|weekly|monthly`) و `X-Quota-Resets-At` (برای پنجره‌ی شناور تقریبی). چک آپلود فقط ورودی است: سندِ شروع‌شده کامل پردازش می‌شود (حداکثر یک سند سرریز). سقف توکنی قدیمی (`token_limit`) هنوز جداگانه اعمال می‌شود.
- **endpoint**: خواندن (admin+): `GET /admin/quota` (پلن‌ها، enforced، مرز ماه جاری)، `GET /admin/users/{id}/quota`، `GET /auth/me/quota` (خود کاربر). نوشتن (**فقط super_admin**): `PUT /admin/quota/enforced {enforced}`، `PUT /admin/quota/plans/{user|admin} {five_hour_usd,weekly_usd,monthly_usd}`، `PUT /admin/users/{id}/quota {five_hour_usd?,weekly_usd?,monthly_usd?,unlimited}` (null = پلن)، و endpointهای قدیمی token-limit (set/extend/reset) که از این‌جا **فقط super_admin** است (قبلاً admin برای `user` هم می‌توانست).
## استخر راه‌اندازی، سقف کل سازمان، هزینه‌ی صفحه‌ای (migration `0028`)
- **استخر راه‌اندازی** (`quota_config.setup_pool_enabled/setup_pool_micro`، پیش‌فرض خاموش): تا وقتی روشن است، OCR و embedding **سندهای پروژه** با `billed_to='org_setup'` ثبت می‌شود (روی نام آپلودکننده، برای ردیابی) و از سهمیه‌ی شخصی او کم **نمی‌شود**. سندهای گفتگو همیشه از سهمیه‌ی کاربر. مانده = بودجه − جمع همه‌ی ردیف‌های `org_setup` (**همه‌ی زمان‌ها**؛ برای تمدید بودجه را بالا ببرید). فقط super_admin: `PUT /admin/quota/setup-pool {enabled?, budget_usd?}`.
- **رد شدن آپلود:** `enforce_upload_quota(user, project_upload=True)` در آپلود پروژه (تک/batch/آرشیو) و retry (تک/گروهی): با استخر روشن و `enforced` فعال و مانده ≤ ۰ → ۴۲۹ با `detail="setup_pool_exhausted"`؛ در غیر این‌صورت بدون چک سهمیه‌ی شخصی (فقط سقف سازمان). super_admin می‌گذرد. اگر `enforced` خاموش باشد (shadow) چیزی رد نمی‌شود ولی هزینه به استخر می‌رود. سندِ صف‌شده‌ای که نوبتش بعد از تمام‌شدن استخر برسد (`run_ingestion_pipeline`) بدون هزینه `failed` می‌شود (پیام فارسی؛ پس از تمدید retry) تا صف طولانی استخر را سرریز نکند. سند در حال پردازش تا آخر کامل می‌شود.
- **سقف کل سازمان** (`org_monthly_cap_micro`، NULL = ندارد): مجموع هزینه‌ی همه‌ی کاربران + استخر در ماه شمسی؛ با رسیدن به آن (و `enforced` روشن) همه جز super_admin — حتی کاربران `unlimited` — ۴۲۹ با `X-Quota-Window: org_monthly` می‌گیرند. `PUT /admin/quota/org-cap {monthly_cap_usd|null}`. `GET /admin/quota` مانده‌ی استخر و مصرف/درصد سقف را نشان می‌دهد (هشدار ۸۰٪ فقط نمایشی است؛ اعلان خودکار نیست).
- **Mistral OCR** (تحلیل جدول دو مرحله‌ای): هر فراخوانی موفق یک ردیف `llm_usage` با `pages=1` و هزینه‌ی صفحه‌ای (`model_prices.per_page_usd`، با `PUT /admin/model-prices/mistral-ocr-latest {per_page_usd}`) می‌شود. **قیمتی seed نشده**: تا وقتی تنظیم نشود هزینه ۰ ثبت و یک‌بار هشدار لاگ می‌شود (حدس نمی‌زنیم).
- هنوز **نیست**: اعلان خودکار هشدار سقف (فقط نمایش در پنل).

## صفحه‌ی «مصرف من» (`/profile`)
هر کاربر لاگین‌شده (همه‌ی نقش‌ها؛ لینک از بلوک کاربر در سایدبار): سه پنجره با مصرف/سقف/باقی‌مانده/زمان آزادشدن از `GET /auth/me/quota`، و از `GET /auth/me/usage?days=` (فقط داده‌ی خود کاربر): مصرف ماه شمسی به تفکیک هدف، مبلغی که استخر راه‌اندازی برای آپلودهای او داده (`billed_to='org_setup'`؛ جدا از مصرف شخصی) و هزینه‌ی روزانه (روز به وقت تهران). اطلاعاتی از دیگران نمی‌دهد. فایل‌ها: `features/profile/screens/ProfileScreen.tsx`، `app/(main)/profile/page.tsx`.

## فرانت (سقف دلاری)
`features/admin/components/QuotaAdminPanel.tsx` (پلن نقش‌ها، سوئیچ اعمال، استخر، سقف سازمان، قیمت مدل‌ها، هزینه‌ی ۳۰ روز؛ ویرایش فقط super_admin و برای admin فقط‌خواندنی) و `UserQuotaControls.tsx` (سه پنجره‌ی هر کاربر + استثنا/نامحدود/بازگشت به پلن) داخل AdminScreen؛ `TokenQuotaBanner` از `GET /auth/me/quota` (تنگ‌ترین پنجره، ≥۸۰٪ یا تمام‌شده؛ فقط وقتی `enforced`) و در غیر این صورت سقف توکنی قدیمی؛ `ApiError.headers` و `friendlyErrorMessage` پیام ۴۲۹ را با نام پنجره و زمان آزادشدن (`X-Quota-Window`/`X-Quota-Resets-At`) و `setup_pool_exhausted` نشان می‌دهند.
