# `.agents/` — مستندات مرجع بک‌اند Orbit Corp

این پوشه **منبع حقیقت مستندات بک‌اند** است؛ هم برای توسعه‌دهنده‌ی انسانی و هم برای هر AI agent که روی `Backend/` کار می‌کند.
متن‌ها فارسی است و نام کد، مسیر فایل و اصطلاحات فنی به انگلیسی آمده‌اند.

> صحت‌سنجی شده با کد در commit `cef3aba` (branch `main`، اکتبر ۲۰۲۶).
> هر جا چیزی از روی کد قابل تأیید نبود با عبارت **«نیاز به تأیید»** علامت خورده است.
> به فایل و نام تابع ارجاع داده شده، نه شماره‌ی خط (شماره‌ی خط زود کهنه می‌شود).

## پروژه در یک پاراگراف
بک‌اند یک **دستیار هوشمند سازمانی** است. کاربران در تیم‌ها و پروژه‌ها سازمان‌دهی می‌شوند؛ اسناد پروژه آپلود و ایندکس می‌شوند (RAG روی pgvector)؛
کاربر با یک **AI agent** چت می‌کند (چت شخصی با SSE یا چت گروهی پروژه با WebSocket و `@bot`). agent با **tool-calling** اسناد را جست‌وجو/مطالعه می‌کند،
حافظه‌ی مشترک پروژه را می‌خواند/می‌نویسد، و (اگر فعال باشد) با ابزار `ask_accounting_db` از **دیتابیس حسابداری راهکاران** (SQL Server، schema فقط‌خواندنی `ai`) با تولید T-SQL پاسخ مالی می‌دهد.

## ترتیب پیشنهادی مطالعه
1. [01-overview.md](01-overview.md) — تصویر کلی، سرویس‌ها، stack
2. [02-architecture.md](02-architecture.md) — ساختار کد و قراردادها
3. [03-access-control.md](03-access-control.md) — نقش‌ها و مدل دسترسی (مهم‌ترین قسمت برای تغییر ایمن)
4. [04-data-model.md](04-data-model.md) — جدول‌ها و migrationها
5. پوشه‌ی [flows/](flows/) — جریان‌های end-to-end
6. [known-issues.md](known-issues.md) — محدودیت‌ها، بدهی فنی، وضعیت امنیتی (قبل از هر تغییر بزرگ بخوانید)

## «می‌خواهم X را بفهمم/تغییر بدهم» → کدام فایل؟
| هدف | فایل |
|---|---|
| لاگین، JWT، refresh token | [flows/auth-and-tokens.md](flows/auth-and-tokens.md) |
| تیم، پروژه، عضویت، قطع دسترسی | [flows/teams-projects-membership.md](flows/teams-projects-membership.md) + [03](03-access-control.md) |
| آپلود سند، OCR، chunk، embedding، worker | [flows/document-ingestion.md](flows/document-ingestion.md) |
| حلقه‌ی agent و tool-calling | [flows/agent-turn.md](flows/agent-turn.md) + [reference/agent-tools.md](reference/agent-tools.md) |
| چت شخصی (SSE) | [flows/chat-personal-sse.md](flows/chat-personal-sse.md) |
| چت گروهی (WebSocket، `@bot`) | [flows/chat-group-ws.md](flows/chat-group-ws.md) |
| حافظه‌ی پروژه | [flows/project-memory.md](flows/project-memory.md) |
| پرسش مالی از دیتابیس راهکاران | [flows/accounting-query.md](flows/accounting-query.md) |
| آپدیت داده‌ی راهکاران، ساخت view/hint | [flows/accounting-data-refresh.md](flows/accounting-data-refresh.md) + [guides/extend-accounting-layer.md](guides/extend-accounting-layer.md) |
| کیفیت بازیابی اسناد، نتایج ارزیابی، اجرای دوباره‌ی ارزیابی | [ops/retrieval-evaluation.md](ops/retrieval-evaluation.md) + `../tools/retrieval_eval/` |
| لیست endpointها، رویدادهای SSE/WS، شکل artifact | [reference/api-endpoints.md](reference/api-endpoints.md) |
| متغیرهای env | [reference/configuration.md](reference/configuration.md) |
| نقشه‌ی فایل‌به‌فایل کد | [reference/modules.md](reference/modules.md) |
| Docker، Caddy، deploy، secrets | [ops/infra-and-deploy.md](ops/infra-and-deploy.md) |
| دستورهای روزمره و troubleshooting | [ops/runbook.md](ops/runbook.md) |
| اجرای تست و نوشتن تست | [ops/testing.md](ops/testing.md) |
| افزودن endpoint/feature | [guides/add-endpoint-or-feature.md](guides/add-endpoint-or-feature.md) |
| افزودن ابزار agent | [guides/add-agent-tool.md](guides/add-agent-tool.md) |
| تغییر schema دیتابیس | [guides/add-migration.md](guides/add-migration.md) |
| پشتیبانی از فرمت فایل جدید | [guides/add-file-format.md](guides/add-file-format.md) |
| چرا فلان چیز این‌طور ساخته شده | [decisions.md](decisions.md) |
| قواعد کدنویسی و کارهایی که نباید کرد | [conventions.md](conventions.md) |

## منابع بیرون از این پوشه (فقط لینک؛ تکرار نشده‌اند)
مستندات دامنه‌ی **دیتابیس راهکاران** که حجیم و بخشی تولید خودکار است در جای قبلی‌اش می‌ماند:
- [../docs/rahkaran/README.md](../docs/rahkaran/README.md) — شناخت دیتابیس (چه چیزی استفاده می‌شود)
- `../docs/rahkaran/GLOSSARY_*.md`، `enums.md`، `schema/*.md` (تولید خودکار)، `QUESTIONS.md` (تولید خودکار از `examples/run.py`)، `TAXONOMY_REVIEW.md`، `ACCOUNTANT_QUESTIONS.md`
- [../sql/rahkaran/README.md](../sql/rahkaran/README.md) — فهرست ۸۴ view لایه‌ی `ai`
- [../sql/rahkaran/hints/README.md](../sql/rahkaran/hints/README.md) — corpus هینت‌های Text-to-SQL

مستندات فرانت‌اند: `../Frontend/` (فایل‌های `AGENTS.md` / `CLAUDE.md` / `FRONTEND_PLAN.md` خودش). `.agents` فقط بک‌اند را پوشش می‌دهد؛ قرارداد API با فرانت در [reference/api-endpoints.md](reference/api-endpoints.md) است.

## قاعده‌ی نگهداری
- هر تغییری در رفتار کد باید همین‌جا هم به‌روز شود (در همان PR/commit).
- اگر مستندی با کد اختلاف دارد، **کد درست است**؛ مستند را اصلاح کنید.
- مستندات قدیمی که این پوشه پوشش داده حذف شده‌اند (`docs/BACKEND.md`، `DEPLOY.md`، `INFRA-CHANGES.md`، `docs/rahkaran/PLAN.md`، `docs/rahkaran/SECURITY_PLAN.md`)؛ محتوای مفید آن‌ها در `ops/`، `known-issues.md` و `decisions.md` منتقل شده است.
