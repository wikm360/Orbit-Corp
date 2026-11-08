"""Golden set (جزئی/حسابدار-محور): Persian question -> reference T-SQL + what a correct answer must look like.

Source of the cases: the conversation with the company accountant (invoice -> moein -> project (DL level 4) -> machine (level 5) ->
expense item (level 6: قطعات/فیلتر/لاستیک/تعمیر/سوخت-روغن), petty cash, closed-year WIP transfer) + the audit of the Oct-2026 backup.
Reference SQL is written to be correct *independently of* the semantic views that are being improved: where a view cannot answer
(closed fiscal years, level-6 names) it goes to ai.ledger_lines + ai.dl_accounts directly.

Fields per case (dict):
  id, group, question, sql (reference; None when the correct behaviour is "say it is not available")
  kind      : 'scalar'   -> one number, compare `value_col` of the first row
              'rows'     -> compare the set of first-column keys (and `value_col` sums when given)
              'refusal'  -> no SQL can answer; a correct reply must say the data does not exist
              'ambiguous'-> several entities match; a correct reply must list/flag the candidates (min_candidates) or state the assumption
  value_col : name of the numeric column in the reference result
  views     : any of these views in the top-k retrieved hints counts as "retrieval OK" (eval_golden.py --mode retrieval)
  note      : why the case exists (which failure mode of the current approach it probes)
All amounts are Rials. FY = fiscal year (Mehr..Shahrivar): 1404 = 1404/07/01..1405/06/31.
Closing/transfer vouchers of WIP (1117xx -> 5111xx) are excluded with CLOSING; the description differs per year, hence the loose LIKE.
"""

CLOSING = "voucher_description LIKE N'%کار%جریان%بهای تمام%'"

# level-6 expense item of a ledger line (works for every fiscal year, unlike the net-based cost views)
_L6 = "LEFT JOIN ai.dl_accounts d6 ON d6.dl_code = l.dl6_code"
_BASE = f"l.is_valid_for_reports = 1 AND l.is_regular = 1 AND NOT ({CLOSING.replace('voucher_description', 'l.voucher_description')})"

GOLDEN = [
    # ---------------- سطح ۶: قطعات / لاستیک / فیلتر ... ----------------
    dict(id="g01", group="level6", kind="scalar", value_col="amount",
         question="در سال ۱۴۰۴ برای پروژه راور-دیهوک چقدر قطعات برای ماشین‌آلات سنگین خریدیم؟",
         sql=f"SELECT SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code = '111780' "
             f"AND l.contract_dl_code = '661278' AND d6.dl_title = N'قطعات'",
         views=["cost_lines", "equipment_project_cost_year"], note="کاربر «راور دیهوک» می‌گوید؛ در داده «راور-دیهوک»؛ قطعات = سطح ۶ نه معین"),
    dict(id="g02", group="level6", kind="scalar", value_col="amount",
         question="هزینه قطعات کمپرسی بنز پلاک 818ع14 در پروژه راور دیهوک در ۱۴۰۴ چقدر بود؟",
         sql=f"SELECT SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code = '111780' "
             f"AND l.contract_dl_code = '661278' AND l.equipment_dl_code = '422222' AND d6.dl_title = N'قطعات'",
         views=["cost_lines", "equipment_project_cost_year"], note="سناریوی سخت حسابدار: معین ← پروژه ← دستگاه ← سطح ۶. equipment_cost_year محور پروژه ندارد"),
    dict(id="g03", group="level6", kind="rows", value_col="amount",
         question="هزینه تعمیر ماشین‌آلات سنگین پروژه راور-دیهوک در ۱۴۰۴ را به تفکیک نوع (قطعات، لاستیک، فیلتر، …) بده",
         sql=f"SELECT d6.dl_title AS item, SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} WHERE {_BASE} AND l.fiscal_year = 1404 "
             f"AND l.sl_code = '111780' AND l.contract_dl_code = '661278' GROUP BY d6.dl_title ORDER BY amount DESC",
         views=["cost_lines", "equipment_project_cost_year"], note="تفکیک سطح ۶ در یک پروژه"),
    dict(id="g04", group="level6", kind="scalar", value_col="amount",
         question="هزینه لاستیک ماشین‌آلات سنگین و کامیون‌ها در سال مالی ۱۴۰۳ چقدر بود؟",
         sql=f"SELECT SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} WHERE {_BASE} AND l.fiscal_year = 1403 "
             f"AND l.sl_code = '111780' AND d6.dl_title LIKE N'%لاستیک%'",
         views=["cost_lines", "equipment_project_cost_year", "equipment_cost_year"], note="سال بسته: جمع خالص 1117 صفر است؛ معین 511007 «لاستیک» بدون تراکنش است"),
    dict(id="g05", group="level6", kind="rows", value_col="amount",
         question="پنج دستگاه با بیشترین هزینه قطعات در سال ۱۴۰۴ کدامند؟",
         sql=f"SELECT TOP 5 l.equipment_dl_code AS code, MAX(l.equipment_name) AS name, SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} "
             f"WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code IN ('111780','111781') AND d6.dl_title = N'قطعات' AND l.equipment_dl_code IS NOT NULL "
             f"GROUP BY l.equipment_dl_code ORDER BY amount DESC",
         views=["cost_lines", "equipment_project_cost_year", "equipment_cost_year"], note="رتبه‌بندی دستگاه بر اساس سطح ۶"),
    dict(id="g06", group="level6", kind="rows", value_col="amount",
         question="هزینه تعمیر و نگهداری ماشین‌آلات سنگین در سال ۱۴۰۲ به تفکیک دستگاه، ۵ تای اول",
         sql=f"SELECT TOP 5 l.equipment_dl_code AS code, MAX(l.equipment_name) AS name, SUM(l.net_debit) AS amount FROM ai.ledger_lines l "
             f"WHERE {_BASE} AND l.fiscal_year = 1402 AND l.sl_code = '111780' AND l.equipment_dl_code IS NOT NULL GROUP BY l.equipment_dl_code ORDER BY amount DESC",
         views=["equipment_project_cost_year", "equipment_cost_year", "cost_lines"], note="سال بسته: equipment_cost_year برای 1401..1403 صفر است"),
    dict(id="g07", group="level6", kind="rows", value_col="amount",
         question="هزینه سوخت گازوئیل در سال ۱۴۰۴ به تفکیک پروژه",
         sql=f"SELECT l.contract_dl_code AS code, MAX(l.contract_name) AS name, SUM(l.net_debit) AS amount FROM ai.ledger_lines l {_L6} "
             f"WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code = '111755' AND d6.dl_title LIKE N'%گازوئیل%' GROUP BY l.contract_dl_code ORDER BY amount DESC",
         views=["cost_lines", "equipment_project_cost_year"], note="سطح ۶ سوخت (گازوئیل/بنزین/مازوت)"),
    dict(id="g08", group="level6", kind="rows", value_col="machines",
         question="در پروژه راور-دیهوک در ۱۴۰۴ برای چند دستگاه قطعات خریداری شده است؟",
         sql=f"SELECT COUNT(DISTINCT l.equipment_dl_code) AS machines FROM ai.ledger_lines l {_L6} WHERE {_BASE} AND l.fiscal_year = 1404 "
             f"AND l.sl_code IN ('111780','111781') AND l.contract_dl_code = '661278' AND d6.dl_title = N'قطعات'",
         views=["cost_lines", "equipment_project_cost_year"], note="شمارش دستگاه (نه ردیف)؛ سؤال محدود به سنگین نیست، پس سنگین+سبک (111780+111781)"),
    dict(id="g09", group="level6", kind="scalar", value_col="amount",
         question="هزینه تعمیر کمپرسی ولوو پلاک 911ع69 در سال ۱۴۰۴ چقدر است؟",
         sql=f"SELECT SUM(l.net_debit) AS amount FROM ai.ledger_lines l WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code = '111780' AND l.equipment_dl_code = '422334'",
         views=["cost_lines", "equipment_project_cost_year", "equipment_cost_year"], note="نام دستگاه فاصله‌ی دوتایی دارد («ولوو      پلاک»)"),
    dict(id="g10", group="level6", kind="rows", value_col="amount",
         question="هزینه تعمیر ماشین‌آلات سنگین را برای سال‌های ۱۴۰۲ و ۱۴۰۳ و ۱۴۰۴ مقایسه کن",
         sql=f"SELECT l.fiscal_year AS year, SUM(l.net_debit) AS amount FROM ai.ledger_lines l WHERE {_BASE} AND l.fiscal_year IN (1402,1403,1404) AND l.sl_code = '111780' "
             f"GROUP BY l.fiscal_year ORDER BY l.fiscal_year",
         views=["cost_by_nature_year", "pnl_by_category_year", "equipment_project_cost_year", "cost_lines"], note="مقایسه‌ی سال بسته با سال جاری باید مبنای یکسان داشته باشد"),

    # ---------------- پروژه / قرارداد ----------------
    dict(id="g11", group="contract", kind="scalar", value_col="amount",
         question="هزینه کل پروژه تکمیل زیرسازی و آسفالت محور کرمان-دیهوک (راور) در سال ۱۴۰۴ چقدر است؟",
         sql="SELECT contract_cost AS amount FROM ai.contract_financials_year WHERE fiscal_year = 1404 AND contract_dl_code = '661278'",
         views=["contract_financials_year", "contract_financials"], note="جمع قرارداد درست است؛ باید با نام «راور دیهوک» پیدا شود"),
    dict(id="g12", group="contract", kind="scalar", value_col="amount",
         question="هزینه کل دفتر مرکزی در سال ۱۴۰۴",
         sql="SELECT SUM(amount) AS amount FROM ai.cost_lines WHERE fiscal_year = 1404 AND contract_dl_code = '661070'",
         views=["cost_lines", "contract_financials_year"], note="«دفتر مرکزی» = مرکز هزینه 661070 (نه department_name)"),
    dict(id="g13", group="contract", kind="rows", value_col="amount",
         question="هزینه ماهانه تعمیر ماشین‌آلات سنگین پروژه راور-دیهوک در ۱۴۰۴",
         sql=f"SELECT l.jalali_ym AS ym, SUM(l.net_debit) AS amount FROM ai.ledger_lines l WHERE {_BASE} AND l.fiscal_year = 1404 AND l.sl_code = '111780' "
             f"AND l.contract_dl_code = '661278' GROUP BY l.jalali_ym ORDER BY l.jalali_ym",
         views=["cost_lines", "equipment_project_cost_year"], note="روند ماهانه + اسناد موقت ماه‌های آخر"),
    dict(id="g14", group="contract", kind="rows", value_col="amount",
         question="سه پروژه با بیشترین هزینه قطعات و تعمیر ماشین‌آلات در سال ۱۴۰۴",
         sql=f"SELECT TOP 3 l.contract_dl_code AS code, MAX(l.contract_name) AS name, SUM(l.net_debit) AS amount FROM ai.ledger_lines l WHERE {_BASE} AND l.fiscal_year = 1404 "
             f"AND l.sl_code IN ('111780','111781') GROUP BY l.contract_dl_code ORDER BY amount DESC",
         views=["cost_lines", "equipment_project_cost_year", "contract_financials_year"], note="رتبه‌بندی پروژه‌ها بر اساس نوع هزینه"),

    # ---------------- تنخواه ----------------
    dict(id="g15", group="petty_cash", kind="scalar", value_col="balance",
         question="مانده تنخواه عبدالرضا طاهری چقدر است و بدهکار است یا بستانکار؟",
         sql="SELECT balance FROM ai.petty_cash_balances WHERE counterparty_dl_code = '251785'",
         views=["petty_cash_balances"], note="مانده منفی = شرکت به دارنده بدهکار است (از جیب خودش خرج کرده)"),
    dict(id="g16", group="petty_cash", kind="ambiguous", value_col="balance", min_candidates=2,
         question="مانده تنخواه رحیم سلطانی چقدر است؟",
         sql="SELECT counterparty_dl_code AS code, holder_name AS name, balance FROM ai.petty_cash_balances WHERE holder_name LIKE N'%رحیم سلطانی%'",
         views=["petty_cash_balances"], note="دو تنخواه‌دار؛ نام ترکیبی «مدیر - دارنده»؛ و «رحیم سلطانی نژاد» تأمین‌کننده است نه تنخواه‌دار"),
    dict(id="g17", group="petty_cash", kind="rows", value_col="balance",
         question="کدام تنخواه‌داران بستانکار هستند، یعنی شرکت به آن‌ها بدهکار است؟",
         sql="SELECT counterparty_dl_code AS code, holder_name AS name, balance FROM ai.petty_cash_balances WHERE balance < 0 ORDER BY balance",
         views=["petty_cash_balances"], note="جهت علامت"),
    dict(id="g18", group="petty_cash", kind="scalar", value_col="balance",
         question="جمع مانده همه‌ی تنخواه‌ها چقدر است؟",
         sql="SELECT SUM(balance) AS balance FROM ai.petty_cash_balances",
         views=["petty_cash_balances"], note="جمع الجبری بدهکار/بستانکار"),

    # ---------------- طرف‌حساب ----------------
    dict(id="g19", group="counterparty", kind="scalar", value_col="net_payable",
         question="چقدر به یوسف سیاه نوریان (حمل و نقل امین) بدهکاریم؟",
         sql="SELECT net_payable FROM ai.vendor_balances WHERE counterparty_dl_code = '201914'",
         views=["vendor_balances", "counterparty_balances"], note="counterparty_balances شامل ردیف هزینه‌ی 1117 هم هست؛ جمع بی‌فیلتر برای این شخص ۱۴۳ میلیارد بدهکار می‌دهد در حالی که واقعاً ۳۸.۹ میلیارد بستانکار است"),
    dict(id="g20", group="counterparty", kind="rows", value_col="receivable_balance",
         question="۵ کارفرمای دارای بیشترین مطالبات",
         sql="SELECT TOP 5 counterparty_dl_code AS code, counterparty_name AS name, receivable_balance FROM ai.customer_balances ORDER BY receivable_balance DESC",
         views=["customer_balances"], note="کنترل: سؤال کلی که قبلاً خوب جواب می‌داد نباید خراب شود"),

    # ---------------- حقوق / کلی (regression) ----------------
    dict(id="g21", group="regression", kind="scalar", value_col="amount",
         question="هزینه حقوق (دسته‌ی حقوق) در سال ۱۴۰۴ چقدر است؟",
         sql="SELECT SUM(amount) AS amount FROM ai.pnl_by_category_year WHERE fiscal_year = 1404 AND detail_category = N'حقوق'",
         views=["pnl_by_category_year", "cost_by_nature_year"], note="regression: سؤال کلی"),
    dict(id="g22", group="regression", kind="scalar", value_col="amount",
         question="درآمد پیمان‌ها در سال مالی ۱۴۰۴",
         sql="SELECT SUM(amount) AS amount FROM ai.revenue_lines WHERE fiscal_year = 1404 AND pnl_class = 'contract_revenue'",
         views=["revenue_lines", "income_summary_year"], note="regression"),
    dict(id="g23", group="regression", kind="scalar", value_col="amount",
         question="هزینه سوخت در ۱۴۰۴ چقدر بود؟",
         sql="SELECT SUM(amount) AS amount FROM ai.pnl_by_category_year WHERE fiscal_year = 1404 AND detail_category = N'سوخت'",
         views=["pnl_by_category_year", "cost_by_nature_year"], note="regression: دسته‌ی کلی"),

    # ---------------- داده‌ای که وجود ندارد / مبهم ----------------
    dict(id="g24", group="unavailable", kind="refusal", sql=None,
         question="در فاکتورهای قطعات پروژه راور چند عدد پنوماتیک زانویی ۱/۴ خریده‌ایم؟",
         views=["cost_lines", "voucher_search"], note="ریز اقلام فاکتور (کالا/تعداد) در دیتابیس نیست؛ فقط مبلغ هر فقره"),
    dict(id="g25", group="unavailable", kind="refusal", sql=None,
         question="قیمت واحد و تعداد فیلتر روغن خریداری‌شده برای لودرها چقدر بوده؟",
         views=["cost_lines"], note="انبار/خرید استفاده نمی‌شود؛ مقدار و قیمت واحد ثبت نشده"),
    dict(id="g26", group="ambiguous", kind="ambiguous", value_col="amount", min_candidates=5,
         question="هزینه تعمیر کمپرسی بنز در ۱۴۰۴ چقدر بود؟",
         sql=f"SELECT l.equipment_dl_code AS code, MAX(l.equipment_name) AS name, SUM(l.net_debit) AS amount FROM ai.ledger_lines l WHERE {_BASE} AND l.fiscal_year = 1404 "
             f"AND l.sl_code = '111780' AND l.equipment_name LIKE N'%کمپرسی%بنز%' GROUP BY l.equipment_dl_code ORDER BY amount DESC",
         views=["cost_lines", "equipment_project_cost_year", "equipment_cost_year"], note="«کمپرسی بنز» = ۱۴ دستگاه؛ پاسخ درست یا تفکیک دستگاه‌ها یا اعلام فرض"),
]

BY_ID = {c["id"]: c for c in GOLDEN}
