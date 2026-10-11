# نمونه سؤال‌ها و SQL مرجع (لایه‌ی معنایی ai)

پیش‌نویس مجموعه‌ی ارزیابی (golden set). هر SQL روی view های `ai` و با کاربر فقط‌خواندنی اجرا و بررسی شده است؛ مبالغ به ریال. خروجی‌ها نمونه‌ی ردیف اول از snapshot بک‌آپ 2026-10-05 هستند و با به‌روزرسانی داده تغییر می‌کنند. تولید خودکار با `sql/rahkaran/examples/run.py`.

## مالی و دفتر کل

### درآمد و سود و زیان سال مالی ۱۴۰۴ چقدر است؟

```sql
SELECT * FROM ai.income_summary_year WHERE fiscal_year = 1404
```

نمونه خروجی: fiscal_year_id=117 | fiscal_year=1404 | contract_revenue=11,658,414,063,160 | other_revenue=1,345,375,070,991 | total_revenue=13,003,789,134,151 | contract_cost=10,632,832,514,881  (1 ردیف)

### روند درآمد و هزینه و سود در سال‌های مالی اخیر

```sql
SELECT fiscal_year, total_revenue, total_cost, profit_estimate FROM ai.income_summary_year ORDER BY fiscal_year DESC
```

نمونه خروجی: fiscal_year=1404 | total_revenue=13,003,789,134,151 | total_cost=11,938,020,113,939 | profit_estimate=1,065,769,020,212  (17 ردیف)

### درآمد پیمان‌ها در هر ماه سال مالی ۱۴۰۴

```sql
SELECT jalali_ym, jalali_month_name, SUM(amount) AS revenue FROM ai.revenue_lines WHERE fiscal_year = 1404 AND pnl_class = 'contract_revenue' GROUP BY jalali_ym, jalali_month_name ORDER BY jalali_ym
```

نمونه خروجی: jalali_ym=140407 | jalali_month_name=مهر | revenue=13,967,646,449  (11 ردیف)

### هزینه‌های ۱۴۰۴ به تفکیک ماهیت (حقوق، اجاره، سوخت، پیمانکار …)

```sql
SELECT cost_nature_key, nature_title, contract_cost, machinery_unit_cost, admin_expense, total_amount FROM ai.cost_by_nature_year WHERE fiscal_year = 1404 ORDER BY total_amount DESC
```

نمونه خروجی: cost_nature_key=04 | nature_title=حقوق و مزایای شغل | contract_cost=1,473,554,693,802 | machinery_unit_cost=0 | admin_expense=81,002,591,847 | total_amount=1,554,557,285,649  (54 ردیف)

### تراز آزمایشی معین‌ها در سال ۱۴۰۴ (فقط حساب‌های با گردش)

```sql
SELECT sl_code, sl_title, opening_net, period_debit, period_credit, closing_balance_net FROM ai.trial_balance_sl_year WHERE fiscal_year = 1404 AND (period_debit <> 0 OR period_credit <> 0) ORDER BY sl_code
```

نمونه خروجی: sl_code=111003 | sl_title=تنخواه گردانهای ریالی | opening_net=0 | period_debit=261,287,060,050 | period_credit=213,407,765,097 | closing_balance_net=47,879,294,953  (168 ردیف)

### ترازنامه پایان سال ۱۴۰۳ در سطح گروه حساب

```sql
SELECT group_code, group_title, SUM(balance_net) AS balance FROM ai.balance_sheet_year WHERE fiscal_year = 1403 GROUP BY group_code, group_title ORDER BY group_code
```

نمونه خروجی: group_code=11 | group_title=داراییهای جاری | balance=19,169,278,385,914  (5 ردیف)

### جمع دارایی‌ها، بدهی‌ها و حقوق صاحبان سهام در پایان هر سال

```sql
SELECT fiscal_year, total_assets, total_liabilities, total_equity_before_result, profit_for_year_unclosed FROM ai.balance_sheet_check_year ORDER BY fiscal_year DESC
```

نمونه خروجی: fiscal_year=1404 | total_assets=34,406,647,325,308 | total_liabilities=15,241,513,630,259 | total_equity_before_result=7,466,532,159,956 | profit_for_year_unclosed=11,698,601,535,093  (17 ردیف)

### اسناد حسابداری ثبت‌شده در مرداد ۱۴۰۵ (تعداد و جمع)

```sql
SELECT COUNT(*) AS voucher_count, SUM(total_debit) AS total_debit FROM ai.vouchers WHERE jalali_ym = 140505 AND is_valid_for_reports = 1 AND is_regular = 1
```

نمونه خروجی: voucher_count=1070 | total_debit=12,694,545,490,548  (1 ردیف)

### آخرین اسناد ثبت‌شده در سیستم

```sql
SELECT TOP 20 voucher_date, jalali_date, voucher_number, voucher_type, voucher_state, total_debit, description FROM ai.vouchers ORDER BY voucher_date DESC, voucher_id DESC
```

نمونه خروجی: voucher_date=2026-09-23 | jalali_date=1405/07/01 | voucher_number=3 | voucher_type=عمومی | voucher_state=یادداشت | total_debit=0  (20 ردیف)

### اسنادی که هنوز موقت هستند (بررسی نشده‌اند) به تفکیک ماه

```sql
SELECT jalali_ym, COUNT(*) AS vouchers, SUM(total_debit) AS total_debit FROM ai.vouchers WHERE voucher_state_code = 1 GROUP BY jalali_ym ORDER BY jalali_ym
```

نمونه خروجی: jalali_ym=140503 | vouchers=3 | total_debit=9,076,505,668  (4 ردیف)

### جستجوی اسناد با کلمه در توضیحات (مثلاً «بیمه»)

```sql
SELECT TOP 50 voucher_date, voucher_number, sl_title, debit, credit, line_description FROM ai.voucher_search WHERE line_description LIKE N'%بیمه%' ORDER BY voucher_date DESC
```

نمونه خروجی: voucher_date=2026-09-22 | voucher_number=11597 | sl_title=سپرده بیمه | debit=184,007,190 | credit=0 | line_description=بابت 5% سپرده بیمه صورت وضعیت شماره 15 ق  (50 ردیف)

### گردش ماهانه حساب موجودی بانکی در ۱۴۰۴

```sql
SELECT jalali_ym, jalali_month_name, total_debit AS money_in, total_credit AS money_out FROM ai.account_monthly_turnover WHERE fiscal_year = 1404 AND sl_code = '111005' ORDER BY jalali_ym
```

نمونه خروجی: jalali_ym=140407 | jalali_month_name=مهر | money_in=1,439,572,176,012 | money_out=1,787,810,119,066  (12 ردیف)

### مالیات بر ارزش افزوده پرداختنی/دریافتنی به تفکیک دوره

```sql
SELECT tax_period_or_detail, account_role, SUM(debit) AS debit, SUM(credit) AS credit FROM ai.vat_lines WHERE fiscal_year = 1404 GROUP BY tax_period_or_detail, account_role ORDER BY tax_period_or_detail
```

نمونه خروجی: tax_period_or_detail=None | account_role=vat_output | debit=15,711,340,944 | credit=0  (54 ردیف)


## قراردادها و صورت‌وضعیت‌ها

### قراردادها (پروژه‌ها) با بیشترین درآمد در سال ۱۴۰۴

```sql
SELECT TOP 10 contract_name, revenue, contract_cost, margin, margin_ratio FROM ai.contract_financials_year WHERE fiscal_year = 1404 ORDER BY revenue DESC
```

نمونه خروجی: contract_name=(15/1401/13729)عملیات تکمیل باند دوم سیر | revenue=2,897,484,636,039 | contract_cost=1,821,216,740,890 | margin=1,076,267,895,149 | margin_ratio=0.371449  (10 ردیف)

### سودآوری کل هر قرارداد (درآمد − هزینه) از ابتدا

```sql
SELECT TOP 20 contract_name, employer_name, total_revenue, total_contract_cost, total_margin, margin_ratio FROM ai.contract_financials ORDER BY total_revenue DESC
```

نمونه خروجی: contract_name=(15/1401/13729)عملیات تکمیل باند دوم سیر | employer_name=شرکت ساخت و توسعه زیر بناهای حمل و نقل ک | total_revenue=9,162,597,682,133 | total_contract_cost=6,286,341,569,963 | total_margin=2,876,256,112,170 | margin_ratio=0.313912  (20 ردیف)

### کدام قراردادها زیان‌ده هستند؟

```sql
SELECT contract_name, employer_name, total_revenue, total_contract_cost, total_margin FROM ai.contract_financials WHERE total_margin < 0 ORDER BY total_margin
```

نمونه خروجی: contract_name=احداث راه ارتباطی بین چاه هایCGW-1,CG-2  | employer_name=شرکت مهندسی و توسعه نفت | total_revenue=2,482,726,702,739 | total_contract_cost=3,380,506,255,721 | total_margin=-897,779,552,982  (10 ردیف)

### صورت‌وضعیت‌های یک کارفرما (مثلاً شهرداری کرمان)

```sql
SELECT voucher_date, jalali_date, contract_name, revenue_amount, vat_amount, retention_amount, description FROM ai.contract_statements WHERE employer_name LIKE N'%شهرداری کرمان%' ORDER BY voucher_date DESC
```

نمونه خروجی: voucher_date=2026-03-20 | jalali_date=1404/12/29 | contract_name=پل غیر همسطح شهید یونس زنگی ابادی(ق 6425 | revenue_amount=59,016,949,603 | vat_amount=0 | retention_amount=5,901,694,960  (13 ردیف)

### آخرین صورت‌وضعیت‌های ثبت‌شده در تمام قراردادها

```sql
SELECT TOP 20 voucher_date, jalali_date, contract_name, employer_name, revenue_amount FROM ai.contract_statements ORDER BY voucher_date DESC
```

نمونه خروجی: voucher_date=2026-09-22 | jalali_date=1405/06/31 | contract_name=(پیمان 18373) احداث قطعه اول راه دسترسی  | employer_name=سازمان توسعه و نوسازی معادن و صنایع معدن | revenue_amount=3,680,143,795  (20 ردیف)

### هزینه‌ی یک قرارداد به تفکیک ماهیت در سال ۱۴۰۴ (مثلاً سیرجان–قطروئیه)

```sql
SELECT cost_nature_key, sl_title, SUM(amount) AS amount FROM ai.cost_lines WHERE fiscal_year = 1404 AND contract_name LIKE N'%سیرجان-قطروئیه%' AND pnl_class IN ('project_cost_wip','project_cost_recognized') GROUP BY cost_nature_key, sl_title ORDER BY amount DESC
```

نمونه خروجی: cost_nature_key=04 | sl_title=حقوق و مزایای شغل | amount=248,676,455,146  (42 ردیف)

### حسن انجام کار نگهداشته‌شده توسط هر کارفرما

```sql
SELECT TOP 15 counterparty_name, retention_receivable_balance FROM ai.customer_balances ORDER BY retention_receivable_balance DESC
```

نمونه خروجی: counterparty_name=شرکت ساخت و توسعه زیر بناهای حمل و نقل ک | retention_receivable_balance=431,229,343,282  (15 ردیف)

### هزینه حقوق هر قرارداد در مرداد ۱۴۰۵

```sql
SELECT cost_center, employee_count, net_pay, employer_total_cost FROM ai.payroll_by_cost_center_month WHERE issue_year_month = 140505 ORDER BY employer_total_cost DESC
```

نمونه خروجی: cost_center=احداث باند دوم محور زرند - سیریز (قطعه ا | employee_count=115 | net_pay=65,746,713,745 | employer_total_cost=95,025,795,247  (8 ردیف)


## مشتریان، تأمین‌کنندگان و طرف‌حساب‌ها

### بیشترین مطالبات از کارفرماها

```sql
SELECT TOP 10 counterparty_name, receivable_balance, retention_receivable_balance, advance_received_balance, total_exposure FROM ai.customer_balances ORDER BY total_exposure DESC
```

نمونه خروجی: counterparty_name=شرکت ساخت و توسعه زیر بناهای حمل و نقل ک | receivable_balance=3,370,541,335,359 | retention_receivable_balance=431,229,343,282 | advance_received_balance=479,040,000,000 | total_exposure=3,322,730,678,641  (10 ردیف)

### مانده طلب از یک مشتری مشخص

```sql
SELECT * FROM ai.customer_balances WHERE counterparty_name LIKE N'%راه و شهرسازی استان کرمان%'
```

نمونه خروجی: counterparty_dl_code=320305 | counterparty_name=اداره کل راه و شهرسازی استان کرمان | party_id=None | receivable_balance=2,508,806,777,907 | retention_receivable_balance=410,686,176,942 | notes_receivable_balance=0  (1 ردیف)

### بیشترین بدهی به تأمین‌کنندگان و پیمانکاران

```sql
SELECT TOP 15 counterparty_name, payable_balance, notes_payable_balance, retention_payable_balance, prepayment_balance, net_payable FROM ai.vendor_balances ORDER BY net_payable DESC
```

نمونه خروجی: counterparty_name=اداره کل دارایی استان کرمان | payable_balance=1,827,828,831 | notes_payable_balance=1,568,794,064,740 | retention_payable_balance=0 | prepayment_balance=0 | net_payable=1,570,621,893,571  (15 ردیف)

### مانده با شرکت‌های گروه نصر

```sql
SELECT counterparty_name, receivable_balance, payable_balance, net_position FROM ai.group_company_balances ORDER BY ABS(net_position) DESC
```

نمونه خروجی: counterparty_name=جهادنصرکرمان | receivable_balance=1,384,867,534,370 | payable_balance=951,646,841,226 | net_position=433,220,693,144  (45 ردیف)

### گردش‌های یک طرف‌حساب (مثلاً جهادنصر کرمان) در سال ۱۴۰۴

```sql
SELECT voucher_date, voucher_number, sl_title, debit, credit, line_description FROM ai.ledger_lines WHERE counterparty_name LIKE N'%جهادنصر%' AND fiscal_year = 1404 AND is_valid_for_reports = 1 ORDER BY voucher_date
```

نمونه خروجی: voucher_date=2025-09-23 | voucher_number=1 | sl_title=حسابهای دریافتنی (شرکتهای گروه) | debit=10,392,426,719 | credit=0 | line_description=ثبت بابت سند افتتاحیه  (252 ردیف)

### پرداخت‌های انجام‌شده به یک شخص/شرکت از طریق بانک

```sql
SELECT TOP 50 m.voucher_date, m.dl_title AS bank_account, m.money_out, m.line_description FROM ai.bank_movements m WHERE m.money_out > 0 AND m.line_description LIKE N'%شمس الدینی%' ORDER BY m.voucher_date DESC
```

نمونه خروجی: voucher_date=2026-09-21 | bank_account=  رفاه-شعبه خیابان شفا حساب 333999319 | money_out=1,085,370,000 | line_description=پرداخت طی فیش 1783404 به حساب شبا IR73-0  (50 ردیف)


## بانک، تنخواه، ضمانت‌نامه و تسهیلات

### موجودی حساب‌های بانکی

```sql
SELECT dl_title, balance, last_activity_date FROM ai.bank_balances ORDER BY balance DESC
```

نمونه خروجی: dl_title=بانک شهر جهاد کرمان 4001006394975 | balance=82,225,168,813 | last_activity_date=2026-09-22  (63 ردیف)

### جمع موجودی بانکی کل شرکت

```sql
SELECT SUM(balance) AS total_bank_balance FROM ai.bank_balances WHERE sl_code = '111005'
```

نمونه خروجی: total_bank_balance=131,385,013,994  (1 ردیف)

### گردش بانکی هفته/ماه اخیر

```sql
SELECT TOP 100 voucher_date, jalali_date, dl_title, money_in, money_out, line_description FROM ai.bank_movements ORDER BY voucher_date DESC, line_id DESC
```

نمونه خروجی: voucher_date=2026-09-22 | jalali_date=1405/06/31 | dl_title=ملت بهمنیار 1805108991 | money_in=149,734,246 | money_out=0 | line_description=واریز به حساب توسط بانک ملت بابت سود علی  (100 ردیف)

### مانده تنخواه‌گردان‌ها

```sql
SELECT holder_name, balance, last_activity_date FROM ai.petty_cash_balances WHERE balance <> 0 ORDER BY balance DESC
```

نمونه خروجی: holder_name=مهدی بحرینی-هجیر الماسی باغ بهزادی | balance=9,496,617,565 | last_activity_date=2026-09-22  (13 ردیف)

### ضمانت‌نامه‌های حسن انجام تعهدات باز

```sql
SELECT counterparty_name, contract_name, reference_detail, balance_net_debit FROM ai.guarantee_balances WHERE sl_code = '911108' AND balance_net_debit > 0 ORDER BY balance_net_debit DESC
```

نمونه خروجی: counterparty_name=بانک شهر - شعبه جهاد | contract_name=None | reference_detail=None | balance_net_debit=13,000,000,000,000  (91 ردیف)

### جمع ضمانت‌نامه‌ها به تفکیک نوع

```sql
SELECT guarantee_type, SUM(balance_net_debit) AS outstanding FROM ai.guarantee_balances GROUP BY guarantee_type ORDER BY outstanding DESC
```

نمونه خروجی: guarantee_type=ضمانت نامه حسن انجام تعهدات | outstanding=28,228,297,856,439  (9 ردیف)

### تسهیلات (وام‌های بانکی) و مانده آن‌ها

```sql
SELECT facility_name, sl_title, balance_net_debit, last_date FROM ai.facility_balances WHERE balance_net_debit <> 0 ORDER BY ABS(balance_net_debit) DESC
```

نمونه خروجی: facility_name=تسهیلات بانک رفاه قرارداد 2-32898746-971 | sl_title=وامهای دریافتی از بانکها - فروش اقساطی | balance_net_debit=-46,585,067,642 | last_date=2026-09-01  (14 ردیف)


## حقوق و دستمزد

### جمع حقوق و هزینه کارفرما در هر ماه سال ۱۴۰۵

```sql
SELECT issue_year_month, jalali_month_name, employee_count, total_benefits, net_pay, employer_total_cost FROM ai.payroll_month_summary WHERE jalali_year = 1405 ORDER BY issue_year_month
```

نمونه خروجی: issue_year_month=140501 | jalali_month_name=فروردین | employee_count=564 | total_benefits=241,508,359,506 | net_pay=211,311,073,255 | employer_total_cost=299,570,233,448  (5 ردیف)

### کل پرداختی حقوق (خالص) در سال مالی ۱۴۰۴

```sql
SELECT * FROM ai.payroll_year_summary WHERE fiscal_year = 1404
```

نمونه خروجی: fiscal_year=1404 | months=11 | distinct_employees=662 | total_benefits=3,005,558,263,809 | total_deductions=372,198,011,347 | net_pay=2,633,360,252,462  (1 ردیف)

### چند نفر در مرداد ۱۴۰۵ حقوق گرفتند؟

```sql
SELECT employee_count, net_pay FROM ai.payroll_month_summary WHERE issue_year_month = 140505
```

نمونه خروجی: employee_count=517 | net_pay=277,308,332,290  (1 ردیف)

### بیشترین خالص پرداختی کارمندان در مرداد ۱۴۰۵

```sql
SELECT TOP 10 employee_name, department_name, net_pay, total_benefits, total_deductions FROM ai.payroll_monthly WHERE issue_year_month = 140505 ORDER BY net_pay DESC
```

نمونه خروجی: employee_name=جواد کریمی | department_name=مدیر عامل | net_pay=3,305,934,222 | total_benefits=3,658,169,789 | total_deductions=352,235,567  (10 ردیف)

### فیش حقوقی یک کارمند در یک ماه

```sql
SELECT * FROM ai.payroll_monthly WHERE employee_name LIKE N'%قاسم بروایه%' AND issue_year_month = 140505
```

نمونه خروجی: pay_calc_id=268276 | employee_id=2788 | employee_code=1402163 | employee_name=قاسم بروایه | issue_year_month=140505 | jalali_year=1405  (1 ردیف)

### حقوق به تفکیک واحد سازمانی در مرداد ۱۴۰۵

```sql
SELECT department_name, employee_count, net_pay, employer_total_cost FROM ai.payroll_by_department_month WHERE issue_year_month = 140505 ORDER BY employer_total_cost DESC
```

نمونه خروجی: department_name=وسائل نقلیه | employee_count=194 | net_pay=91,748,489,954 | employer_total_cost=135,055,806,821  (20 ردیف)

### بیمه تأمین اجتماعی (سهم کارگر و کارفرما) ماهانه در سال ۱۴۰۴

```sql
SELECT issue_year_month, employee_social_insurance, employer_social_insurance, unemployment_insurance FROM ai.payroll_month_summary WHERE fiscal_year = 1404 ORDER BY issue_year_month
```

نمونه خروجی: issue_year_month=140407 | employee_social_insurance=14,778,229,684 | employer_social_insurance=42,375,085,495 | unemployment_insurance=6,356,262,840  (11 ردیف)

### مالیات حقوق پرداختی در هر ماه

```sql
SELECT issue_year_month, income_tax FROM ai.payroll_month_summary WHERE jalali_year >= 1404 ORDER BY issue_year_month
```

نمونه خروجی: issue_year_month=140401 | income_tax=755,833,194  (17 ردیف)

### عیدی پرداخت‌شده و ذخیره‌ی عیدی ماهانه

```sql
SELECT issue_year_month, sub_type, COUNT(*) AS employees, SUM(net_reward) AS net_reward, SUM(reward_provision) AS provision FROM ai.periodic_payments WHERE calc_type = N'عیدی' AND issue_year_month >= 140400 GROUP BY issue_year_month, sub_type ORDER BY issue_year_month DESC
```

نمونه خروجی: issue_year_month=140505 | sub_type=ذخیره | employees=517 | net_reward=0 | provision=16,183,015,478  (16 ردیف)

### ذخیره‌ی سنوات (مزایای پایان خدمت) فعلی کل شرکت

```sql
SELECT SUM(severance_provision_total) AS total_provision FROM ai.periodic_payments WHERE calc_type = N'بازخرید سنوات' AND issue_year_month = (SELECT MAX(issue_year_month) FROM ai.periodic_payments WHERE calc_type = N'بازخرید سنوات')
```

نمونه خروجی: total_provision=69,313,090,522  (1 ردیف)

### وام‌ها و مساعده‌های باز کارکنان

```sql
SELECT loan_type, COUNT(*) AS loans, SUM(remainder) AS remainder FROM ai.loans WHERE remainder > 0 GROUP BY loan_type ORDER BY remainder DESC
```

نمونه خروجی: loan_type=سهام آرمان گهر نصر | loans=21 | remainder=31,900,000,000  (6 ردیف)

### اقساط وام یک کارمند

```sql
SELECT l.employee_name, l.loan_type, l.loan_amount, i.payment_year_month, i.amount FROM ai.loans l JOIN ai.loan_instalments i ON i.loan_id = l.loan_id WHERE l.employee_name LIKE N'%روح اله مظفری%' ORDER BY i.payment_year_month DESC
```

نمونه خروجی: employee_name=روح اله مظفری | loan_type=سهام جهان فولاد | loan_amount=299,997,500 | payment_year_month=140307 | amount=9,999,916  (35 ردیف)

### هزینه‌ی حقوق در سطح قرارداد در سال ۱۴۰۴

```sql
SELECT cost_center, SUM(employer_total_cost) AS cost FROM ai.payroll_by_cost_center_month WHERE fiscal_year = 1404 GROUP BY cost_center ORDER BY cost DESC
```

نمونه خروجی: cost_center=پروژه بارگیری و حمل باطله معدن 3 گل گهر( | cost=1,068,123,944,724  (10 ردیف)


## منابع انسانی

### تعداد کارکنان فعال به تفکیک واحد

```sql
SELECT department_name, SUM(employee_count) AS employees FROM ai.headcount_current GROUP BY department_name ORDER BY employees DESC
```

نمونه خروجی: department_name=وسائل نقلیه | employees=196  (20 ردیف)

### چند نفر کارمند فعال داریم؟

```sql
SELECT COUNT(*) AS active_employees FROM ai.employees WHERE is_active = 1
```

نمونه خروجی: active_employees=516  (1 ردیف)

### مشخصات یک کارمند

```sql
SELECT employee_code, full_name, status, department_name, post_title, job_title, employment_date_jalali, children_count, current_cost_center, insurance_number FROM ai.employees WHERE full_name LIKE N'%قاسم بروایه%'
```

نمونه خروجی: employee_code=1402163 | full_name=قاسم بروایه | status=فعال | department_name=وسائل نقلیه | post_title=راننده پایه یک | job_title=راننده خودروهای نیمه سنگین 1  (1 ردیف)

### کارکنانی که در سال ۱۴۰۴ استخدام شده‌اند

```sql
SELECT employee_code, full_name, department_name, post_title, employment_date_jalali FROM ai.employees WHERE employment_date >= '2025-09-23' AND employment_date <= '2026-09-22' ORDER BY employment_date
```

نمونه خروجی: employee_code=1404108 | full_name=محمد نباغ | department_name=پروژه | post_title=مسئول اجرائی کارگاه | employment_date_jalali=1404/07/01  (165 ردیف)

### میانگین حقوق پایه و شرایط مالی کارکنان فعال

```sql
SELECT COUNT(*) AS employees, AVG(base_pay) AS avg_base_pay, AVG(total_monthly_terms) AS avg_total_terms FROM ai.employee_current_pay_terms WHERE employee_status = N'فعال'
```

نمونه خروجی: employees=516 | avg_base_pay=188,650,127 | avg_total_terms=331,239,564  (1 ردیف)

### کارکنان یک قرارداد/مرکز هزینه

```sql
SELECT employee_code, full_name, department_name, post_title FROM ai.employees WHERE is_active = 1 AND current_cost_center LIKE N'%زرند - سیریز%'
```

نمونه خروجی: employee_code=189401 | full_name=نظر هاشم زهی چاه قنبر | department_name=نگهداری و تعمیرات | post_title=مکانیک ماشین آلات سنگین  (113 ردیف)

### مدرک تحصیلی کارکنان فعال

```sql
SELECT e.education_degree, COUNT(*) AS n FROM ai.employees e WHERE e.is_active = 1 GROUP BY e.education_degree ORDER BY n DESC
```

نمونه خروجی: education_degree=None | n=187  (7 ردیف)

### مانده مرخصی کارکنان با بیشترین مانده

```sql
SELECT TOP 10 employee_name, effective_year_month, value_minutes, days_equivalent FROM ai.leave_balances WHERE effective_year_month = (SELECT MAX(effective_year_month) FROM ai.leave_balances) ORDER BY value_minutes DESC
```

نمونه خروجی: employee_name=مهدی رضاخانی | effective_year_month=140501 | value_minutes=4320 | days_equivalent=9  (10 ردیف)


## دارایی ثابت و تجهیزات

### ارزش دفتری دارایی‌های ثابت فعال به تفکیک طبقه

```sql
SELECT asset_class, SUM(asset_count) AS assets, SUM(cost) AS cost, SUM(accumulated_depreciation) AS accumulated_depreciation, SUM(book_value) AS book_value FROM ai.asset_value_by_group WHERE status = N'پلاک شده' GROUP BY asset_class ORDER BY cost DESC
```

نمونه خروجی: asset_class=وسایط نقلیه | assets=156 | cost=4,080,601,475,653 | accumulated_depreciation=1,623,051,787,736 | book_value=2,457,549,687,917  (10 ردیف)

### گران‌ترین دارایی‌ها

```sql
SELECT TOP 15 plaque_number, asset_title, asset_group, cost, book_value, location_name FROM ai.assets WHERE is_active_asset = 1 ORDER BY cost DESC
```

نمونه خروجی: plaque_number=2100001 | asset_title= واگذاری 5 سهم از زمین شرف اباد = عطف 77 | asset_group=زمین | cost=500,000,000,000 | book_value=500,000,000,000 | location_name=پل غیر همسطح شهید یونس زنگی آبادی به شما  (15 ردیف)

### کامیون‌ها و خودروهای ما (فهرست دارایی‌های وسایط نقلیه)

```sql
SELECT plaque_number, asset_title, asset_group, utilization_date_jalali, cost, book_value, location_name FROM ai.assets WHERE is_active_asset = 1 AND asset_class = N'وسایط نقلیه' ORDER BY cost DESC
```

نمونه خروجی: plaque_number=401400083 | asset_title= یک دستگاه ( کامیون کمپرسی بی بن ) به رن | asset_group=کامیون ماده 149 | utilization_date_jalali=1405/03/31 | cost=70,801,000,000 | book_value=68,796,588,128  (156 ردیف)

### هزینه‌ی استهلاک ماهانه در سال ۱۴۰۴

```sql
SELECT jalali_ym, jalali_month_name, SUM(depreciation_amount) AS depreciation FROM ai.depreciation_summary_month WHERE fiscal_year = 1404 GROUP BY jalali_ym, jalali_month_name ORDER BY jalali_ym
```

نمونه خروجی: jalali_ym=140407 | jalali_month_name=مهر | depreciation=61,003,095,727  (12 ردیف)

### دارایی‌های خریداری‌شده در سال ۱۴۰۴

```sql
SELECT receipt_date, supplier_name, plaque_number, item_title, asset_group, purchase_amount FROM ai.asset_acquisitions WHERE fiscal_year = 1404 ORDER BY purchase_amount DESC
```

نمونه خروجی: receipt_date=2025-12-17 | supplier_name=سایر | plaque_number=302000005 | item_title=یک دستگاه ( کامیون میکسر آمیکو تیپ M2631 | asset_group=میکسر ماده 149 | purchase_amount=75,045,372,051  (290 ردیف)

### دارایی‌های فروخته‌شده و مبلغ فروش

```sql
SELECT sale_date, buyer_name, plaque_number, asset_title, sales_amount FROM ai.asset_sales ORDER BY sale_date DESC
```

نمونه خروجی: sale_date=2026-09-22 | buyer_name=سایر | plaque_number=401200016 | asset_title=وانت پیکان 1600 | sales_amount=3,153,153,153  (87 ردیف)

### هزینه‌ی تعمیر و نگهداری و سوخت یک دستگاه

```sql
SELECT fiscal_year, sl_title, SUM(amount) AS amount FROM ai.equipment_cost_year WHERE equipment_name LIKE N'%کوماتسو%' GROUP BY fiscal_year, sl_title ORDER BY fiscal_year DESC, amount DESC
```

نمونه خروجی: fiscal_year=1404 | sl_title=تعمیرونگهداری ماشین الات سنگین | amount=41,148,155,596  (132 ردیف)

### بیشترین هزینه‌ی عملیاتی دستگاه‌ها در ۱۴۰۴

```sql
SELECT TOP 15 equipment_name, equipment_category, SUM(amount) AS cost FROM ai.equipment_cost_year WHERE fiscal_year = 1404 GROUP BY equipment_name, equipment_category ORDER BY cost DESC
```

نمونه خروجی: equipment_name=لودر چرخ لاستیکی کوماتسو 470 شماره شاسی  | equipment_category=ماشین‌آلات سنگین | cost=39,972,717,675  (15 ردیف)

### آیا دفتر دارایی ثابت با دفتر کل مطابقت دارد؟

```sql
SELECT * FROM ai.asset_ledger_reconciliation
```

نمونه خروجی: item=بهای تمام‌شده دارایی‌های ثابت (فقط دارای | asset_module_amount=6,357,711,122,688 | ledger_amount=6,353,787,221,359 | difference=-3,923,901,329  (2 ردیف)


## متا

### داده‌ها تا چه تاریخی به‌روز است؟

```sql
SELECT * FROM ai.data_freshness
```

نمونه خروجی: item=آخرین تاریخ سند حسابداری معتبر (شامل موق | value=2026-09-22  (9 ردیف)

### فهرست سال‌های مالی

```sql
SELECT fiscal_year, start_jalali, end_jalali, closing_state, voucher_count FROM ai.fiscal_years ORDER BY fiscal_year DESC
```

نمونه خروجی: fiscal_year=1405 | start_jalali=1405/07/01 | end_jalali=1406/06/31 | closing_state=شروع نشده | voucher_count=3  (18 ردیف)

### تبدیل تاریخ: ۱۴۰۵/۰۴/۳۱ چه روزی میلادی است؟

```sql
SELECT gregorian_date, jalali_date, weekday_name FROM ai.calendar WHERE jalali_date = '1405/04/31'
```

نمونه خروجی: gregorian_date=2026-07-22 | jalali_date=1405/04/31 | weekday_name=چهارشنبه  (1 ردیف)
