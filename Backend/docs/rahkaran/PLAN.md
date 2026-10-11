# نقشه‌ی راه: اتصال راهکاران به پلتفرم RAG (گام‌به‌گام)

وضعیت (اکتبر 2026): گام‌های ۰ تا ۲ انجام شده‌اند؛ گام ۳ (hint های RAG) آماده‌ی شروع است. دسترسی بر اساس نقش فعلاً **آخرین گام** است (همه چیز باز).
معماری هدف: ابزار Agent با نام `ask_accounting_db` که داخلش schema-RAG + تولید T-SQL + اعتبارسنجی + اجرا + بازنویسی خودکار خطا انجام می‌شود، **فقط روی schema `ai`**.

## گام ۰ — ریستور و شناخت اولیه ✅
کانتینر SQL Server، ریستور FULL+DIFF، مستند [README.md](README.md) و [schema/](schema/).

## گام ۱ — شناخت عمیق داده ✅
[GLOSSARY_ACCOUNTS.md](GLOSSARY_ACCOUNTS.md)، [GLOSSARY_DIMENSIONS.md](GLOSSARY_DIMENSIONS.md)، [GLOSSARY_PAYROLL.md](GLOSSARY_PAYROLL.md)، [GLOSSARY_ENUMS.md](GLOSSARY_ENUMS.md). یافته‌های کلیدی: قرارداد = مرکز هزینه 66xxxx؛ انتقال 1117→5111 در پایان سال؛ تسهیم استهلاک 5112 پایان سال؛ فرمول‌های حقوق؛ الگوی تفصیلی هر معین.

## گام ۲ — لایه‌ی معنایی (view ها) ✅
[../../sql/rahkaran/](../../sql/rahkaran/README.md): schema `ai` با ۸۴ view (مرجع، دفتر کل، گزارش‌های مالی، قراردادها، طرف‌حساب‌ها، بانک/ضمانت‌نامه/تسهیلات، منابع انسانی، حقوق، دارایی ثابت، متا)، توضیح فارسی برای ۱۰۰٪ view ها و ستون‌ها (`ai.view_catalog`، `ai.column_catalog`)، فرهنگ اصطلاحات (`ai.glossary`)، کاربر فقط‌خواندنی با دسترسی فقط به `ai`، و ۶۷ سؤال نمونه با SQL تست‌شده ([QUESTIONS.md](QUESTIONS.md)). صحت با تطبیق مجموع‌ها با جدول‌های خام کنترل شد (درآمد، مانده‌ی مطالبات، بانک، دارایی، حقوق).

## گام ۳ — هینت‌های schema برای RAG ✅
[../../sql/rahkaran/hints/](../../sql/rahkaran/hints/README.md): پرامپت ثابت (۱۰ قاعده)، ۹۰ chunk از view ها (توضیح + کاربرد + فیلتر + اشتباهات + کلمات کلیدی + ستون‌ها)، ۶۷ نمونه‌ی سؤال→SQL، ۴۰ اصطلاح، ۱۷ یادداشت مفهومی؛ خروجی `out/hints.jsonl` (≈ 35 هزار توکن) آماده‌ی embed. ارزیابی واژگانی بازیابی (بدون API): ≈ ۹۶٪ روی سؤال‌های نمونه (leave-one-out بدون نشت) و ۱۰۰٪ روی ۵۰ سؤال بازنویسی‌شده (تنظیم‌شده، خوش‌بینانه). embedding و ذخیره در pgvector در گام ۴ انجام می‌شود (نیازمند تغییر کد/migration).

## گام ۴ — اتصال در بک‌آپ‌اند (اولین تغییر کد) ✅
1. `config.py`: تنظیمات اتصال SQL Server (`rahkaran_ai_reader`)، سقف ردیف/زمان، مدل SQL جدا (`llm_sql_model`)؛ سرویس `mssql` در `docker-compose.yml` با volume داده‌های ریستورشده؛ درایور `pymssql` و `sqlglot` در `requirements.txt`.
2. ماژول `features/db_connector`: بازیابی ترکیبی schema hints (برداری pgvector + واژگانی BM25 با RRF)، تولیدکننده‌ی SQL با حلقه تصحیح خودکار، **اعتبارسنج استاتیک SQL** با `sqlglot` (فقط یک `SELECT`، فقط view های `ai`، بدون `;` چندگانه/`INTO`/`EXEC`/`OPTION` دستی)، اجرا با افزودن `OPTION (USE HINT('DISABLE_OPTIMIZER_ROWGOAL'))` و timeout، قالب‌بندی نتیجه (تبدیل ریال به تومان/میلیارد، جدول مارک‌داون، تاریخ شمسی، متادیتا و تازگی داده‌ها).
3. جدول‌های `schema_hints` و `db_query_logs` با مایگریشن Alembic شماره `0006_accounting_db_connector`؛ اسکریپت Ingestion خودکار و idempotent از `out/hints.jsonl` با embedding فعلی پروژه (`text-embedding-3-small`).
4. ابزار `ask_accounting_db(question)` در `ToolRegistry` با پشتیبانی از `querying_database` در رویدادهای زنده Agent.
5. لاگ جامع پرسش‌ها در `db_query_logs` (متن پرسش، کلید hint ها، SQL، وضعیت، تعداد ردیف، زمان اجرا)؛ API های فیدبک کاربر (👍/👎 و یادداشت)، لیست تاریخچه کوئری‌ها، متغیرهای آماری داشبورد (`/api/v1/accounting-db/*`) و endpoint بازنشانی Ingest.
6. مجموعه تست‌های جامع واحد و یکپارچه در `tests/features/db_connector/` (۳۷ تست موفق، ۱۰۰٪ پاس شدن کل ۱۱۲ تست پروژه).

## گام ۵ — ارزیابی و بهبود (بعد از ماه اول استفاده)
مبنا: لاگ پرسش‌های واقعی؛ پرسش‌های ناموفق/پرتکرار → نمونه‌ی جدید در QUESTIONS، hint یا view جدید.
اجرای خودکار مجموعه‌ی سؤال‌ها (دقت/تاخیر/هزینه)، مقایسه‌ی ۲–۳ مدل، تحلیل خطا → بهبود hint/view/few-shot؛ تجربه‌ی کاربر: نمایش SQL و جدول، خروجی Excel، پیام خطا، نمودار.

## گام ۶ — عملیاتی‌سازی
ورود خودکار بک‌آپ (کار شما): ریستور روی کانتینر موقت → `sql/rahkaran/apply.py` → تست دود (`examples/run.py`) → سوییچ اتمیک؛ نمایش «تاریخ آخرین بک‌آپ» (`ai.data_freshness`) به کاربر؛ لاگ سؤال/SQL.

## گام ۷ — سطح دسترسی (بعد از کامل‌شدن ویژگی)
نگاشت نقش‌ها (مالی / منابع انسانی / مدیر) به گروه‌های view، ماسک ستون‌های حساس (`national_id`, `sheba`, `account_number`, `mobile`, حقوق)، audit، تست prompt injection.
