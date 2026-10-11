-- Meta views: data freshness, business glossary (Persian business term -> where to query) and catalogs of the ai views/columns with their descriptions.

-- ai.data_freshness: how current the snapshot is. Answers "تا چه تاریخی اطلاعات داریم؟".
CREATE OR ALTER VIEW ai.data_freshness AS
SELECT N'آخرین تاریخ سند حسابداری معتبر (شامل موقت)' AS item,
       (SELECT CONVERT(varchar(10), MAX(voucher_date), 23) FROM ai.vouchers WHERE is_valid_for_reports = 1 AND is_regular = 1) AS value
UNION ALL SELECT N'آخرین تاریخ سند بررسی‌شده/قطعی (بعد از آن اسناد موقت‌اند)',
       (SELECT CONVERT(varchar(10), MAX(voucher_date), 23) FROM ai.vouchers WHERE is_reviewed = 1 AND is_regular = 1)
UNION ALL SELECT N'تاریخ جلالی آخرین سند حسابداری معتبر',
       (SELECT c.jalali_date FROM ai.calendar c WHERE c.gregorian_date = (SELECT MAX(voucher_date) FROM ai.vouchers WHERE is_valid_for_reports = 1 AND is_regular = 1))
UNION ALL SELECT N'آخرین زمان ثبت/ویرایش سند (نشانه‌ی تاریخ بک‌آپ)',
       (SELECT CONVERT(varchar(19), MAX(LastModificationDate), 120) FROM FIN3.Voucher)
UNION ALL SELECT N'سال مالی جاری (آخرین سال با بیش از 100 سند)',
       (SELECT CAST(MAX(fiscal_year) AS varchar(10)) FROM ai.fiscal_years WHERE voucher_count > 100)
UNION ALL SELECT N'تعداد اسناد یادداشت (وضعیت 2، خارج از گزارش‌ها) در سال مالی جاری',
       (SELECT CAST(COUNT(*) AS varchar(10)) FROM ai.vouchers WHERE voucher_state_code = 2 AND fiscal_year = (SELECT MAX(fiscal_year) FROM ai.fiscal_years WHERE voucher_count > 100))
UNION ALL SELECT N'آخرین ماه محاسبه حقوق (YYYYMM جلالی)',
       (SELECT CAST(MAX(IssueYearMonth) AS varchar(10)) FROM HCM3.PayCalc)
UNION ALL SELECT N'آخرین تاریخ محاسبه استهلاک دارایی',
       (SELECT CONVERT(varchar(10), MAX(Date), 23) FROM FAM3.Depreciation)
UNION ALL SELECT N'آخرین ماه حضور و غیاب',
       (SELECT CAST(MAX(IssueYearMonth) AS varchar(10)) FROM HCM3.AttendanceCalc);
GO

-- ai.glossary: Persian business terms used at the company and where the data lives (view / column / account filter).
CREATE OR ALTER VIEW ai.glossary AS
SELECT term_fa, meaning_fa, where_to_query
FROM (VALUES
 (N'کارفرما / مشتری', N'سازمان یا شرکتی که برایش پروژه (پیمان) اجرا می‌کنیم؛ طرف‌حساب حساب‌های دریافتنی', N'ai.customer_balances ; ai.counterparty_balances (account_role = receivable_customer)'),
 (N'پیمان / قرارداد / پروژه اجرایی', N'هر قرارداد یک مرکز هزینه با کد 66xxxx است؛ شماره پیمان در عنوان آن و در توضیحات سند آمده', N'ai.cost_centers (is_contract = 1) ; ai.contract_financials ; ai.contract_financials_year'),
 (N'صورت‌وضعیت', N'سند ثبت درآمد پیمان برای کارفرما: درآمد پیمان‌ها + ارزش افزوده + کسر حسن انجام کار و بیمه', N'ai.contract_statements'),
 (N'حسن انجام کار / سپرده حسن انجام کار', N'درصدی (معمولاً ۱۰٪) از هر صورت‌وضعیت که کارفرما نگه می‌دارد (دریافتنی) یا ما از پیمانکاران نگه می‌داریم (پرداختنی)', N'ai.customer_balances.retention_receivable_balance ; ai.vendor_balances.retention_payable_balance'),
 (N'ضمانت‌نامه', N'ضمانت‌نامه‌های بانکی شرکت در مناقصه، پیش‌دریافت، حسن انجام کار/تعهدات که در حساب‌های انتظامی 911xxx نگهداری می‌شود', N'ai.guarantee_balances'),
 (N'درآمد', N'درآمد پیمان‌ها (SL 411010) و سایر درآمدها', N'ai.revenue_lines ; ai.income_summary_year'),
 (N'هزینه قراردادها / بهای تمام‌شده پروژه‌ها', N'هزینه‌های هر قرارداد طی سال در GL 1117 (کار در جریان ساخت) و در پایان سال در GL 5111 (بهای تمام‌شده)؛ جمع هر دو = هزینه قرارداد', N'ai.cost_lines (pnl_class IN project_cost_wip, project_cost_recognized) ; ai.contract_financials_year.contract_cost'),
 (N'سود و زیان / سودآوری', N'درآمد منهای هزینه‌ها (برآورد از دفتر کل)', N'ai.income_summary_year ; ai.contract_financials (margin)'),
 (N'تراز آزمایشی', N'گردش و مانده حساب‌ها در هر سال مالی', N'ai.trial_balance_sl_year ; ai.trial_balance_gl_year'),
 (N'ترازنامه', N'مانده حساب‌های دائم در پایان سال مالی', N'ai.balance_sheet_year ; ai.balance_sheet_check_year'),
 (N'مانده بانک / موجودی بانک', N'مانده حساب‌های بانکی شرکت (SL 111005) تجمعی تا آخرین سند', N'ai.bank_balances ; ai.bank_accounts ; ai.bank_movements'),
 (N'تنخواه', N'تنخواه‌گردان‌ها (SL 111003) به‌تفکیک دارنده', N'ai.petty_cash_balances'),
 (N'طلب از کارفرما / مطالبات', N'مانده بدهکار حساب‌های دریافتنی مشتریان', N'ai.customer_balances.receivable_balance'),
 (N'بدهی به تأمین‌کنندگان / پیمانکاران', N'مانده بستانکار حساب‌های پرداختنی', N'ai.vendor_balances'),
 (N'شرکت‌های گروه / نصر', N'شرکت‌های هم‌گروه (جهادنصر کرمان و …) در حساب‌های جدا (SL 111300 / 211000)', N'ai.group_company_balances'),
 (N'مالیات بر ارزش افزوده', N'ارزش افزوده ورودی (SL 111414) و خروجی/پرداختنی (SL 211212) با دوره مالیاتی (تفصیلی 99xxxx)', N'ai.vat_lines'),
 (N'تسهیلات بانکی / وام بانکی', N'وام‌های دریافتی از بانک‌ها (تفصیلی نوع تسهیلات؛ SL 211701/211702)', N'ai.facility_balances'),
 (N'سال مالی', N'از اول مهر تا آخر شهریور؛ سال مالی 1404 = 1404/07/01 تا 1405/06/31', N'ai.fiscal_years ; ai.calendar.fiscal_year'),
 (N'سند حسابداری', N'هر سند (Voucher) با چند ردیف؛ وضعیت‌های معتبر برای گزارش: موقت (1)، بررسی‌شده (4)، قطعی (32)؛ یادداشت (2) خارج از گزارش‌ها', N'ai.vouchers ; ai.ledger_lines (is_valid_for_reports = 1)'),
 (N'مرکز هزینه', N'واحد هزینه: قرارداد (66xxxx)، ماشین سنگین (41)، کامیون (42)، خودرو سبک (43)، تجهیزات ثابت (44)', N'ai.cost_centers'),
 (N'ماشین‌آلات / کامیون / خودرو', N'هر دستگاه یک مرکز هزینه است؛ هزینه‌های تعمیر، سوخت، استهلاک، اجاره روی آن ثبت می‌شود', N'ai.equipment_cost_year ; ai.assets'),
 (N'حقوق و دستمزد / حقوق خالص', N'خالص پرداختی ماهانه = جمع مزایا − جمع کسور', N'ai.payroll_monthly.net_pay ; ai.payroll_month_summary'),
 (N'هزینه کارفرما برای پرسنل', N'جمع مزایا + بیمه سهم کارفرما + بیمه بیکاری + بیمه تکمیلی سهم کارفرما', N'ai.payroll_monthly.employer_total_cost'),
 (N'بیمه تأمین اجتماعی', N'سهم کارگر ۷٪، سهم کارفرما ۲۰٪، بیمه بیکاری ۳٪ مأخذ بیمه', N'ai.payroll_monthly (employee_social_insurance, employer_social_insurance, unemployment_insurance)'),
 (N'بیمه تکمیلی', N'مبلغ ثابت ۱۱٬۰۰۰٬۰۰۰ ریال به‌ازای هر نفر تحت تکفل برای هر سهم', N'ai.payroll_monthly (employee_supplementary_insurance, employer_supplementary_insurance)'),
 (N'مالیات حقوق', N'مالیات ماهانه حقوق کارکنان', N'ai.payroll_monthly.income_tax'),
 (N'عیدی', N'پاداش سالانه (عیدی) و ذخیره ماهانه آن', N'ai.periodic_payments (calc_type = عیدی)'),
 (N'سنوات / بازخرید سنوات / ذخیره سنوات', N'مزایای پایان خدمت و ذخیره ماهانه آن', N'ai.periodic_payments (calc_type = بازخرید سنوات)'),
 (N'وام و مساعده کارکنان', N'مساعده شرکتی، خرید سهام (آرمان گهر، جهان فولاد)، وام صندوق، کسورات بیمه خودرو', N'ai.loans ; ai.loan_instalments'),
 (N'مرخصی', N'مانده مرخصی استحقاقی به دقیقه (۴۸۰ دقیقه = یک روز)', N'ai.leave_balances'),
 (N'پرسنل / کارکنان', N'وضعیت فعال = 2؛ همه فعال‌ها قراردادی‌اند', N'ai.employees ; ai.headcount_current'),
 (N'حکم کارگزینی', N'سند تغییر شرایط استخدامی/حقوقی؛ حکم مؤثر = آخرین حکم با وضعیت تایید پرداخت', N'ai.employee_statutes ; ai.employee_current_statutes ; ai.employee_current_pay_terms'),
 (N'دارایی ثابت', N'اموال و دارایی‌ها با شماره پلاک؛ وضعیت فعال = پلاک شده', N'ai.assets ; ai.asset_value_by_group'),
 (N'استهلاک', N'استهلاک ماهانه دارایی‌ها (خط مستقیم و نزولی)', N'ai.asset_depreciation ; ai.depreciation_summary_month'),
 (N'پلاک', N'شماره اموال (PlaqueNumber) هر دارایی', N'ai.assets.plaque_number'),
 (N'رسید تحصیل / خرید دارایی', N'سند ورود دارایی جدید', N'ai.asset_acquisitions'),
 (N'فروش دارایی', N'فروش اموال و ماشین‌آلات', N'ai.asset_sales'),
 (N'حذف دارایی', N'خروج دارایی از دفاتر (Elimination)', N'ai.asset_disposals'),
 (N'مبلغ', N'همه مبالغ به ریال هستند مگر اینکه صراحتاً روز/تعداد ذکر شده باشد', N'—'),
 (N'مانده بدهکار / بستانکار', N'net_debit = بدهکار − بستانکار؛ مثبت = بدهکار، منفی = بستانکار', N'ai.ledger_lines.net_debit ; ai.counterparty_balances.balance_net_debit')
) t(term_fa, meaning_fa, where_to_query);
GO

-- ai.view_catalog / ai.column_catalog: the semantic layer's own documentation (from the MS_Description extended properties written by descriptions.py).
CREATE OR ALTER VIEW ai.view_catalog AS
SELECT v.name AS view_name,
       CAST(ep.value AS nvarchar(max)) AS description,
       (SELECT COUNT(*) FROM sys.columns c WHERE c.object_id = v.object_id) AS column_count
FROM sys.views v
LEFT JOIN sys.extended_properties ep ON ep.class = 1 AND ep.major_id = v.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
WHERE v.schema_id = SCHEMA_ID('ai');
GO

CREATE OR ALTER VIEW ai.column_catalog AS
SELECT v.name AS view_name, c.column_id AS ordinal, c.name AS column_name,
       TYPE_NAME(c.user_type_id) + CASE WHEN TYPE_NAME(c.user_type_id) IN ('nvarchar','varchar') THEN '(' + CASE WHEN c.max_length = -1 THEN 'max' WHEN TYPE_NAME(c.user_type_id) = 'nvarchar' THEN CAST(c.max_length / 2 AS varchar(10)) ELSE CAST(c.max_length AS varchar(10)) END + ')'
                                        WHEN TYPE_NAME(c.user_type_id) = 'decimal' THEN '(' + CAST(c.precision AS varchar(5)) + ',' + CAST(c.scale AS varchar(5)) + ')' ELSE '' END AS data_type,
       CAST(ep.value AS nvarchar(max)) AS description
FROM sys.views v
JOIN sys.columns c ON c.object_id = v.object_id
LEFT JOIN sys.extended_properties ep ON ep.class = 1 AND ep.major_id = v.object_id AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
WHERE v.schema_id = SCHEMA_ID('ai');
GO
