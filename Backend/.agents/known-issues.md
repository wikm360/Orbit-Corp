# محدودیت‌ها، بدهی فنی، وضعیت امنیتی و نقشه‌ی راه

> صحت‌سنجی شده از روی کد در commit `cef3aba`. برچسب‌ها: ✅ رفع‌شده · 🟡 نیمه‌رفع · 🔴 باز · ❓ نیاز به تأیید.
> این فایل جایگزین `docs/rahkaran/SECURITY_PLAN.md` و `PLAN.md` (حذف‌شده) است؛ بندهای آن‌ها با وضعیت امروز اینجا آمده‌اند.

## ۱. امنیت و دسترسی (به ترتیب اولویت)

### 🔴 بحرانی قبل از قرار گرفتن روی شبکه‌ی عمومی
| # | مورد | وضعیت امروز | اقدام |
|---|---|---|---|
| S1 | ثبت‌نام عمومی و ساخت کاربر | ✅ رفع‌شده: پرچم `ALLOW_PUBLIC_REGISTRATION` پیاده شد (ثبت‌نام کاربر اول آزاد است، بعدی‌ها مسدود). endpoint ادمین `POST /api/v1/admin/users` برای ساخت کاربر اضافه شد | — |
| S1-b | ابزار مالی برای همهٔ کاربران لاگین‌شده | ✅ رفع‌شده: ابزار `ask_accounting_db` در رجیستری ابزارها و در متد `execute` فقط برای مدیران (`is_admin: SUPER_ADMIN, ADMIN`) مجاز است؛ برای کاربران عادی به کلی فیلتر و مسدود شده است | — |
| S7 | در چت گروهی با `@bot` نتیجه‌ی مالی برای همه‌ی اعضا پخش می‌شود | 🔴 ابزار مالی در گروه هم فعال است | غیرفعال در گروه یا فقط برای کاربر مجاز؛ تصمیم محصول |
| S8 | بدون rate limit (login/register/chat) و بدون سقف هزینه LLM/DB برای هر کاربر | 🔴 | rate limit در اپ (مثلاً slowapi+Redis) یا Caddy plugin؛ سهمیه‌ی ساعتی برای ابزار مالی (مثلاً ۲۰/ساعت/کاربر)؛ semaphore هم‌زمانی |
| S6 | خروج داده به شخص ثالث: پرسش، SQL و **ردیف‌های نتیجه** (حقوق، کد ملی، شبا…) به `LLM_API_BASE_URL` (واسطه/ریسلر) می‌رود | 🔴 تصمیم سازمانی | تأیید رسمی شرکت؛ provider مستقیم/خودمیزبان؛ **ماسک PII** (کد ملی، شبا، شماره حساب، موبایل) و کاهش ردیف‌های ارسالی؛ حذف ستون‌های حساس از ورودی مدل |
| S5 | لاگ ترافیک بدنه‌ی پاسخ‌های مالی را می‌نویسد | 🟡 در prod compose خاموش (`REQUEST_LOGGING_ENABLED=false`) اما در کد مسیر حساس استثنا نشده | در کد: عدم لاگ بدنه‌ی `/chat` و `/accounting-db` حتی اگر روشن شد |
| S4 | `DEBUG=true` و `/docs` عمومی | ✅ رفع‌شده: در صورت `ENVIRONMENT=production` مستقیماً `docs_url/redoc_url/openapi_url=None` در FastAPI اعمال می‌شود | — |
| — | secrets برنامه از `.env` می‌آید و کل `.env` به کانتینرهای اپ می‌رسد | 🟡 secretهای زیرساخت blank می‌شوند ولی JWT/LLM/reader password هنوز در env | `Settings(secrets_dir="/run/secrets")` + Docker secrets برای `jwt_secret_key, llm_api_key, embedding_api_key, rahkaran_db_password` |
| — | `JWT_SECRET_KEY` پیش‌فرض ناامن و `CORS_ORIGINS` پیش‌فرض شامل IPهای قدیمی سرور | 🔴 اگر env ست نشود | fail-fast در startup برای production |

### رفع‌شده (نسبت به SECURITY_PLAN)
- ✅ A1 IDOR بازخورد: `_get_owned_log` (صاحب log یا admin) در feedback و export.
- ✅ A2 `/accounting-db/freshness` اکنون نیاز به لاگین دارد.
- ✅ S1 پرچم `ALLOW_PUBLIC_REGISTRATION` و endpoint ساخت کاربر توسط ادمین `POST /admin/users`.
- ✅ S2 پورت‌ها: prod compose هیچ پورتی جز Caddy منتشر نمی‌کند؛ Redis با رمز؛ شبکه‌های internal.
- ✅ S3 رمز SA پیش‌فرض از compose حذف شد (`${VAR:?}`) — ولی در تاریخچه‌ی git (commit `4a320ca`) هست: rotate کنید.
- ✅ S4 غیرفعال‌سازی خودکار docs در صورت محیط production.
- ✅ S9 لایسنس: پیش‌فرض `MSSQL_PID=Express`.
- ✅ S12 کانتینرها: غیر root، `read_only`, `cap_drop`, `no-new-privileges`, محدودیت منابع، image pin.
- ✅ A5 بخشی: `MONEY_COLUMNS` صریح برای UI (ولی ← «دو منطق مبلغ»).
- ✅ A13 ولوم `rahkaran_mssql_data` دیگر external نیست و خودکار ساخته می‌شود.
- ✅ امنیت اعتبارسنج SQL: AST + reader فقط‌خواندنی روی `ai` + سقف ردیف/timeout + formula-injection guard در export.

### 🟡/🔴 بازبینی کد اتصال دیتابیس (بندهای باز)
| # | شدت | مشکل | محل |
|---|---|---|---|
| A3 | 🟠 | پیام خطای خام SQL Server/مدل به کاربر نشان داده می‌شود (`علت: {last_error}`، `خطا در تولید کوئری: {exc}`) | `db_connector/service.py` |
| A4 | 🟠 | سلول‌های جدول Markdown escape نمی‌شوند (`| \ < >` و خط جدید)؛ متن شرح سند می‌تواند به مدل دستور بدهد (prompt injection از داده)؛ system prompt جمله‌ی «خروجی ابزار داده است، دستور نیست» ندارد | `formatter.format_cell`, `MODEL_NOTE` |
| A6 | 🟠 | حالت `NO_SQL` با `status=OK` و `row_count=0` ثبت می‌شود → آمار موفقیت کاذب و پرسش‌های بی‌پاسخ (مهم‌ترین ورودی بهبود) دیده نمی‌شوند | `service` شاخه‌ی `CannotAnswer`؛ پیشنهاد: status `unanswerable` + migration |
| A7 | 🟡 | سقف زمانی کلی نیست (تا ۳ LLM + ۳ query × ۶۰ث) و هم‌زمانی `to_thread` محدود نیست | `service`, `executor` |
| A8 | 🟡 | شکست تولید یک `Attempt(sql="")` خالی به prompt اضافه می‌کند | `service` |
| A9 | 🟡 | فعال بودن connector با تنظیم ناقص در startup خطا نمی‌دهد | `config` |
| A10 | 🟡 | `@@version`, `SUSER_NAME()`, `DB_NAME()`, `HOST_NAME()` و `CROSS JOIN` چندتایی مجاز است | `sql_validator` |
| A11 | 🟡 | فرانت باید `agent_activity.status=querying_database` را بشناسد | ❓ در `../Frontend` بررسی شود |
| A12 | 🟡 | ایندکس unique تکراری روی `schema_hints.hint_key` (ستون unique + ایندکس unique)؛ ingest در یک درخواست HTTP (ممکن است timeout شود) | migration 0006, router |
| A13 | 🟡 | `rahkaran_mssql_data` `external: true`؛ پورت 14330 در dev | compose |

### سایر مسائل امنیتی/عملیاتی
- بدون قفل حساب/۲FA؛ حداقل رمز ۸ نویسه؛ بدون بازیابی رمز؛ بدون API حذف/غیرفعال‌سازی کاربر.
- توکن WebSocket در query string → در لاگ proxy می‌ماند؛ اتصال WS باز با حذف کاربر از پروژه قطع نمی‌شود.
- access token قابل ابطال نیست (۳۰ دقیقه).
- ذخیره‌ی فایل روی دیسک محلی (نه object storage)؛ فایل‌های `.bak` روی دیسک سرور بدون رمزگذاری؛ Postgres حاوی تاریخچه‌ی چت‌های مالی → رمزگذاری دیسک (LUKS/TDE)، سیاست نگهداری، حذف امن `.bak`.
- `egress` اجازه‌ی هر مقصد اینترنتی را به backend/worker می‌دهد → allow-list برای host مدل.
- مخزن باید private باشد (نام‌ها/ارقام واقعی در `docs/rahkaran/*` و PDF قراردادها).
- ❓ قرارداد با فرانت برای SSE/WS و endpointهای جدید.
- ❓ `Frontend/src/shared/lib/apiClient.ts`: build با `NEXT_PUBLIC_API_URL=/api/v1` (نسبی) در مرورگر کار می‌کند، اما fallback سمت SSR `http://localhost:8000/api/v1` اگر server component مستقیم API را صدا بزند اشتباه است.
- بدون مانیتورینگ/هشدار (ورود ناموفق، پرسش‌های سنگین، 5xx).

### تصمیم‌هایی که هنوز از صاحب محصول لازم است
1. ثبت‌نام: کاملاً بسته (فقط ادمین) یا دعوت‌نامه؟ چه نقش/ایمیل‌هایی ابزار مالی را دارند؟ در گروه غیرفعال شود؟
2. ماسک PII: همه‌ی کد ملی/شبا/حساب/موبایل؟ نام کارکنان در خروجی حقوق نمایش داده شود؟
3. provider مدل: `gapgpt` (واسط) یا مستقیم/خودمیزبان؟ (تأیید شرکت)
4. SQL Server: Express یا Standard؟
5. دامنه و TLS: Let's Encrypt/CA سازمان یا `tls internal`؟
6. گیت‌هاب private؟ مستندات حاوی نام/ارقام واقعی بمانند؟

## ۲. مشکلات رفتاری/طراحی در کد
| مورد | توضیح | محل |
|---|---|---|
| گفتگوی شخصی ناشناخته | `POST /chat` با `conversation_id` نامعتبر/مال دیگری بی‌صدا گفتگوی جدید می‌سازد (نه 404) | `get_or_create_personal_conversation` |
| متن پیش از tool-call | delta گام‌های میانی stream می‌شود ولی ذخیره نمی‌شود | `agent/engine.py` |
| حافظه‌ی turn | فقط `content` تاریخچه (۳۰ پیام) بازپخش می‌شود؛ نتایج ابزار و artifact قبلی نه | `engine._build_messages` |
| صفحه‌ی بدون heading | سرفصل‌ها استخراج نمی‌شوند (ابزار outline حذف شد؛ `get_document_info` فقط تعداد صفحه/توکن می‌دهد) | parser |
| DOCX تک‌صفحه‌ای | شماره‌ی صفحه‌ی واقعی DOCX وجود ندارد؛ کل سند «صفحه ۱» است | `parser._parse_docx_pages` |
| سند گیرکرده | PROCESSING با مرگ worker خودکار FAILED نمی‌شود | ingestion |
| اعلان ingestion | `document_status` فقط برای اسناد گفتگو (نه پروژه) | `pipeline._notify_conversation` |
| `GET /projects/mine` | ادمینِ غیر-عضو پروژه‌ها را نمی‌بیند (ولی دسترسی دارد) | `projects.service.list_user_projects` |
| لیست گفتگوها | leader تیم که عضو پروژه نیست چت گروهی را در لیست نمی‌بیند (با id مستقیم دسترسی دارد) | `chat.service.list_user_conversations` |
| تنزل leader | leader می‌تواند leader دیگر را با `role=member` تنزل دهد | `access_control.router.add_team_member` |
| حافظه از چت | هر عضو پروژه می‌تواند حافظه بنویسد؛ مدیریت REST فقط manager | `memory_tools` vs `memory.router` |
| `recall` بدون آستانه | همیشه ۵ مورد برمی‌گرداند | `memory.service.recall` |
| `confidence_score` | ستون بلااستفاده | `ProjectMemory` |
| cache hint ها | per-process (۳۰۰ث)؛ ingest فقط cache همان process را ابطال می‌کند | `db_connector/hints.py` |
| دو منطق مبلغ | `formatter.is_money_column` (الگو) و `artifacts.column_kind` (صریح+الگو) ممکن است ناهمخوان باشند | db_connector |
| اتصال SQL Server | هر query اتصال جدید (بدون pool) و بدون محدودیت هم‌زمانی | `executor._connect` |
| `get_sql_llm_provider` | cache ندارد؛ هر تولید یک client جدید | `llm_provider.py` |
| ابعاد vector | از env در زمان migration؛ تغییرش مهاجرت دستی می‌خواهد | alembic 0001/0004/0006 |
| تنظیم‌پذیری | `ToolRegistry` در import ساخته می‌شود؛ تغییر `RAHKARAN_DB_ENABLED` بدون restart اثر نمی‌کند | `chat/service._agent_engine` |
| task پس‌زمینه‌ی گروه | `asyncio.create_task` بدون نگه‌داشتن ارجاع؛ با restart پاسخ از بین می‌رود | `post_group_message` |
| `created_at` پیام‌ها | زمان شروع transaction؛ ترتیب دقیق هم‌زمانی با `id` | models |
| ترتیب قاعده‌های core prompt | قاعده‌ی ۱۲ قبل از ۱۰ آمده (فقط ظاهر) | `notes.CORE_PROMPT` |

## ۳. محدودیت‌های عملکردی/محصولی
- **OCR: فیلتر ایمنی و کیفیت اسکن**: Gemini گاهی برای نامه‌های اداری (مهر/امضا) `content_filter` برمی‌گرداند؛ با retry (تا ۸ بار) اغلب حل می‌شود ولی تضمین نیست و سند تک‌صفحه‌ای در بدترین حالت FAILED می‌شود (retry دستی). تشخیص جهت پیش‌فرض `hybrid` است (Tesseract OSD + تأیید مدل)؛ OSD روی صفحه‌ی تقریباً فقط‌عددی (جدول) و صفحه‌ی کم‌متن گاهی «راست» می‌گوید و چرخش از دست می‌رود. image باید `tesseract-ocr`/`tesseract-ocr-osd` داشته باشد وگرنه به مدل برمی‌گردد. جزئیات: [ops/ocr-preprocessing-evaluation.md](ops/ocr-preprocessing-evaluation.md).
- **OCR هزینه/زمان دارد**: هر صفحه‌ی PDF با لایه‌ی خراب ~۲۰–۲۵ ثانیه و یک فراخوانی vision؛ PDFهای چندصدصفحه‌ای (و اسکن‌های حجیم تا ۱۹۰MB در پوشه‌ی eval) باید با `OCR_MAX_REPLACED_PAGES`/بودجه مدیریت شوند؛ بعد از سقف، صفحه‌ها با متن تعمیرشده (کیفیت پایین‌تر) ایندکس می‌شوند.
- پیش‌فرض‌های جست‌وجو (مدل `text-embedding-3-small`، آستانه‌ی ۰٫۳، بدون re-rank) هنوز بهترین ترکیب اندازه‌گیری‌شده نیستند؛ ترکیب پیشنهادی و دلیلش در [ops/retrieval-evaluation.md](ops/retrieval-evaluation.md) است (نیاز به re-embed و تصمیم شما).
- بازیابی اسناد hybrid است (برداری + Postgres full-text + trigram + RRF) ولی **re-rank، multi-query/HyDE، MMR، chunk همسایه** ندارد؛ full-text Postgres وزن IDF/BM25 ندارد (با شرط حداقل دو کلمه‌ی متمایز جبران شده) و stemmer فارسی ندارد (فقط نرمال‌سازی). کیفیت روی داده‌ی واقعی **اندازه‌گیری نشده** (eval set وجود ندارد).
- فرمت‌های قدیمی `.doc/.xls/.ppt` پشتیبانی نمی‌شوند؛ OCR وابسته به LLM vision و `LLM_API_KEY`؛ سقف ۵۰ تصویر در هر سند.
- حذف سند گفتگو، حذف گفتگو/پیام، حذف/ویرایش تیم و پروژه، حذف کاربر: API ندارد.
- تست WebSocket واقعی و تست SQL Server واقعی نیست.
- سقف ردیف: ۵۰۰ (واکشی)، ۶۰ (مدل)، ۱۰۰ (UI)، ۵۰۰۰ (export).
- داده‌ی مالی snapshot است (ماه‌های اخیر موقت)، نه زنده؛ به‌روزرسانی با ریختن `.bak`.
- بخشی از جداول راهکاران استفاده‌نشده‌اند (فروش/انبار/خرید/تولید) → پرسش‌های آن حوزه‌ها `NO_SQL` می‌گیرند.

## ۴. نقشه‌ی راه اتصال راهکاران (از PLAN.md)
| گام | وضعیت |
|---|---|
| ۰ ریستور و شناخت اولیه | ✅ |
| ۱ شناخت عمیق داده (glossaryها) | ✅ |
| ۲ لایه‌ی معنایی `ai` (۸۴ view، توضیحات، reader) | ✅ |
| ۳ hint ها (corpus، core prompt، ارزیابی واژگانی) | ✅ |
| ۴ کانکتور بک‌اند (hybrid retrieval، generator با تعمیر، validator، executor، formatter، log، feedback، export، artifacts) | ✅ |
| ۶ عملیاتی‌سازی (refresh خودکار بک‌آپ، data_freshness در پاسخ) | ✅ (`refresh.py`) |
| ۵ ارزیابی و بهبود — اجرای خودکار مجموعه‌ی سؤال‌ها (دقت/تأخیر/هزینه)، مقایسه‌ی ۲–۳ مدل، تحلیل خطا از `db_query_logs`، نمودار، UX | ⏳ بعد از ماه اول استفاده |
| ۷ سطح دسترسی — نگاشت نقش‌ها (مالی/منابع انسانی/مدیر) به گروه view، ماسک ستون‌های حساس (`national_id, sheba, account_number, mobile`, حقوق)، audit، تست prompt-injection | ⏳ آخرین گام؛ **فعلاً همه چیز برای همه‌ی کاربران لاگین باز است** |

## ۵. فهرست P0/P1/P2 پیشنهادی (از SECURITY_PLAN با وضعیت امروز)
- **P0**: بستن ثبت‌نام عمومی؛ allow-list و غیرفعال‌سازی ابزار مالی در گروه؛ docs غیرفعال در خود اپ؛ rate limit؛ rotate secretها.
- **P1**: ماسک PII؛ A3/A4/A6/A7/A8/A10؛ سهمیه‌ی کاربر؛ رمزگذاری دیسک/بک‌آپ و حذف امن `.bak`؛ تصمیم provider مدل.
- **P2**: قفل حساب/۲FA ادمین؛ محدودیت IP برای `/admin` و `/accounting-db/*`؛ مانیتورینگ و گزارش هفتگی از `db_query_logs`؛ تست نفوذ سبک (prompt injection از داده، دور زدن validator، brute-force، اسکن پورت).

## ۶. اختلاف‌های مستند قدیمی (`docs/BACKEND.md` حذف‌شده)
برای مرجع تاریخی: آن سند agent/tools، memory، db_connector، OCR، batch/retry، artifacts و migrationهای ۰۳–۰۷ را نداشت؛ می‌گفت «بدون OCR» و «embedding ۱۰۲۴ بعد»؛ می‌گفت CI backend را migrate/rebuild می‌کند (کد فعلی فقط فرانت را deploy می‌کند)؛ می‌گفت بازیابی در `chat.service` انجام می‌شود (اکنون ابزار `search_knowledge_base` است). همه‌ی این موارد در `.agents` اصلاح شده‌اند.

- `read_document_pages` بدون سقف تعداد صفحه/توکن است: مدل می‌تواند بازه‌ی بزرگ (مثلاً ۱–۱۴۴) بخواهد و context پر شود (فقط `read_entire_document` سقف ۳۰k توکن دارد). پرامپت/توضیح ابزارها مدل را از آن دور می‌کنند ولی سقف سخت نیست؛ پیشنهاد: سقف صفحه (~۸) و توکن (~۱۲k) + بودجه‌ی کل نتیجه‌ی ابزارها در هر turn.
