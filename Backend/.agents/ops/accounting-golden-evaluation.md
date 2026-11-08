# ارزیابی Text-to-SQL مالی با golden set (حسابدار-محور)

> وضعیت: بازیابی و end-to-end (مدل `qwen3.8-flash` از gapgpt) با لایه‌ی جدید اجرا شده؛ **e2e روی کد/لایه‌ی قدیمی کامل نشد** (اجرا قطع شد)، پس مقایسه‌ی قبل/بعد فقط برای بازیابی است. e2e داده‌ی مالی و ردیف‌های نتیجه را به LLM بیرونی می‌فرستد؛ عمداً دستی.

## چرا
در سؤال‌های کلی مدل خوب بود ولی در سؤال‌های جزئی («قطعات کمپرسی X در پروژه Y»، «لاستیک سال گذشته»، «تنخواه فلانی») جواب غلط می‌داد. ریشه‌ها در [../known-issues.md](../known-issues.md) و [../flows/accounting-data-refresh.md](../flows/accounting-data-refresh.md) (بخش «ریز هزینه‌ی ماشین‌آلات و سطح ۶») آمده است. golden set همین‌ها را قابل اندازه‌گیری می‌کند.

## فایل‌ها (`sql/rahkaran/examples/`)
| فایل | نقش |
|---|---|
| `golden.py` | ۲۶ مورد: `id, group, question, sql (مرجع), kind (scalar/rows/refusal/ambiguous), views (viewهای قابل‌قبول), note` |
| `golden_expected.py` | همه‌ی SQL های مرجع را با reader اجرا و `golden_expected.json` را می‌نویسد (بعد از هر بک‌آپ جدید دوباره؛ اعداد با داده عوض می‌شوند) |
| `eval_golden.py retrieval` | محلی/رایگان: همان `retrieve_hints` پروژه با BM25 (بدون Postgres/embedding/LLM). آیا view درست در top-k هست و در چه رتبه‌ای |
| `eval_golden.py e2e` | `run_accounting_query` واقعی (نیاز Postgres، LLM، `RAHKARAN_DB_*` به SQL Server ریستور‌شده). امتیاز خودکار scalar/rows؛ refusal/ambiguous = بازبینی دستی |

SQL مرجع عمداً به `ai.ledger_lines` + `ai.dl_accounts` می‌رود (نه view های در حال بهبود) تا مستقل از آن‌ها درست باشد؛ روی هر ردیف مبنای «بدون اسناد انتقال پایان سال» (`CLOSING`).

## روش
1. ریستور بک‌آپ و اعمال لایه: `docker compose` معمولی، یا کانتینر جدا (در بررسی اول از `rahkaran-audit-mssql` روی پورت 14331 استفاده شد) و `RAHKARAN_SA_PASSWORD=… RAHKARAN_PORT=… python sql/rahkaran/apply.py`.
2. `RAHKARAN_AI_PASSWORD=… RAHKARAN_PORT=… python sql/rahkaran/examples/golden_expected.py`
3. `python sql/rahkaran/examples/eval_golden.py retrieval [--k 8] [--out r.json]`
4. (دستی) `RAHKARAN_DB_PORT=… python sql/rahkaran/examples/eval_golden.py e2e [--ids g01,g02] --out e2e.json`
5. **قاعده‌ی عدم آلودگی**: سؤال golden یا نام‌های اختصاصی آن (پروژه/دستگاه/شخص) در few-shot و note ها نیاید.

## نتایج
| تاریخ | حالت | نتیجه |
|---|---|---|
| 2026-11-07 (قبل از تغییر) | retrieval k=8 | view مورد انتظار در top-8: **21/26**؛ رتبه ۱: **16**. موارد g01 g03 g07 (سطح ۶) و g14 و g25 miss؛ رتبه ۱ برای سؤال سطح ۶ همیشه `equipment_cost_year` (بدون محور پروژه و برای سال بسته صفر) |
| 2026-11-07 (بعد از لایه جدید + hint) | retrieval k=8 | **25/26**؛ رتبه ۱: **23**. تنها miss: g25 (سؤال «قیمت واحد و تعداد فیلتر» که عمداً refusal است؛ note `invoice_items_missing` بازیابی می‌شود) |
| 2026-11-07 (لایه جدید) | e2e، `qwen3.8-flash` | ۲۶ مورد: **20 PASS، 2 FAIL، 4 بازبینی دستی**. هر دو FAIL (g04، g08) ایراد تعریف golden بود، نه مدل (سؤال محدود به «سنگین» نبود/مبهم بود)؛ مرجع اصلاح و آن دو دوباره اجرا شدند: هر دو PASS ⇒ **22/22 خودکار PASS** (اصلاح بعد از دیدن نتیجه انجام شد، پس خوش‌بینانه است). دستی: g16 (هر دو تنخواه‌دار برگشت، تأمین‌کننده هم‌نام نیامد)، g24 و g25 (NO_SQL صادقانه)، g26 (به تفکیک دستگاه، ۹ ردیف) |
| قبل از تغییر | e2e | کامل نشد (اجرا قطع شد)؛ اندازه‌گیری نشده |

یافته‌های e2e: (۱) مدل در همه‌ی موارد سطح ۶ مستقیم سراغ `equipment_project_cost_year` و `expense_item_name` رفت. (۲) پیام `unanswerable` در `service.py` به مدل می‌گوید «از کاربر بخواه پرسش را دقیق‌تر بنویسد»، که برای داده‌ای که اصلاً ثبت نشده (ریز اقلام فاکتور) گمراه‌کننده است؛ اصلاح نشده. (۳) g20: مدل به‌جای `receivable_balance` از `total_exposure` رتبه‌بندی کرد (۴ از ۵ مشترک) که معقول است.

نکته: «OK» در بازیابی فقط یعنی view درست در prompt هست، نه اینکه مدل SQL درست بنویسد. معیار نهایی e2e است (هدف: ≥۸۰٪ PASS در scalar/rows، پاسخ صادقانه در refusal، فهرست/اعلام فرض در ambiguous).

## بررسی صحت لایه‌ی داده (همان تاریخ، FULL 2026-10-02 + DIFF 2026-10-05)
- چهار مرجع golden (g01 g02 g04 g09) با `equipment_project_cost_year` دقیقاً برابر شدند (بر حسب ریال: 36535626086، 1738728636، 245716518467، 11087565710).
- جمع view جدید = `contract_financials_year.contract_cost` برای ۱۳۹۷–۱۴۰۴ (جز ۱۴۰۱ با ≈۲٫۴ میلیارد ریال بیشتر).
- `equipment_cost_year` برای 111780: ۱۴۰۱ تا ۱۴۰۳ حدود ۵۷٫۰ و ۶۴٫۳ و ۸۴٫۲ میلیارد تومان (قبلاً صفر).
