-- Finance report views built on ai.ledger_lines. All of them use documents with is_valid_for_reports = 1 (states 1 temporary, 4 reviewed, 32 final;
-- state 2 notes are excluded) unless stated otherwise. Amounts are in Rials.
--
-- Voucher-type buckets used everywhere:
--   opening  = voucher types 6, 11      (افتتاحیه)
--   closing  = voucher types 5, 7       (بستن حساب‌ها / اختتامیه)
--   adjust   = voucher types 8, 9       (تعدیل ماهیت ابتدا/انتهای دوره)
--   regular  = everything else          (is_regular = 1)

-- ai.trial_balance_sl_year: per fiscal year and SL: opening balance, period turnover (regular documents) and closing balance.
-- closing_balance_net = opening_net + period_net + adjust_net  (i.e. the balance BEFORE the year-end closing entries; for temporary
-- income/expense accounts it equals the result of the year). Positive = debit balance, negative = credit balance.
CREATE OR ALTER VIEW ai.trial_balance_sl_year AS
SELECT l.fiscal_year_id, l.fiscal_year,
       l.group_code, l.group_title, l.gl_code, l.gl_title, l.sl_code, l.sl_title,
       l.account_type, l.statement, l.account_role,
       SUM(CASE WHEN l.is_opening = 1 THEN l.debit ELSE 0 END) AS opening_debit,
       SUM(CASE WHEN l.is_opening = 1 THEN l.credit ELSE 0 END) AS opening_credit,
       SUM(CASE WHEN l.is_opening = 1 THEN l.net_debit ELSE 0 END) AS opening_net,
       SUM(CASE WHEN l.is_regular = 1 THEN l.debit ELSE 0 END) AS period_debit,
       SUM(CASE WHEN l.is_regular = 1 THEN l.credit ELSE 0 END) AS period_credit,
       SUM(CASE WHEN l.is_regular = 1 THEN l.net_debit ELSE 0 END) AS period_net,
       SUM(CASE WHEN l.voucher_type_id IN (8,9) THEN l.net_debit ELSE 0 END) AS adjust_net,
       SUM(CASE WHEN l.is_closing = 1 THEN l.net_debit ELSE 0 END) AS closing_entries_net,
       SUM(CASE WHEN l.is_closing = 0 THEN l.net_debit ELSE 0 END) AS closing_balance_net
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1
GROUP BY l.fiscal_year_id, l.fiscal_year, l.group_code, l.group_title, l.gl_code, l.gl_title, l.sl_code, l.sl_title,
         l.account_type, l.statement, l.account_role;
GO

-- ai.trial_balance_gl_year: same as ai.trial_balance_sl_year but at GL (kol) level.
CREATE OR ALTER VIEW ai.trial_balance_gl_year AS
SELECT fiscal_year_id, fiscal_year, group_code, group_title, gl_code, gl_title, account_type, statement,
       SUM(opening_debit) AS opening_debit, SUM(opening_credit) AS opening_credit, SUM(opening_net) AS opening_net,
       SUM(period_debit) AS period_debit, SUM(period_credit) AS period_credit, SUM(period_net) AS period_net,
       SUM(adjust_net) AS adjust_net, SUM(closing_entries_net) AS closing_entries_net, SUM(closing_balance_net) AS closing_balance_net
FROM ai.trial_balance_sl_year
GROUP BY fiscal_year_id, fiscal_year, group_code, group_title, gl_code, gl_title, account_type, statement;
GO

-- ai.balance_sheet_year: end-of-year balances of balance-sheet accounts at GL level (before year-end closing entries).
-- For the current open year the profit/loss accounts are not closed yet, so the sheet only balances together with
-- ai.income_summary_year (see ai.balance_sheet_check_year).
CREATE OR ALTER VIEW ai.balance_sheet_year AS
SELECT fiscal_year_id, fiscal_year, group_code, group_title, gl_code, gl_title,
       closing_balance_net AS balance_net,
       CASE WHEN closing_balance_net > 0 THEN closing_balance_net ELSE 0 END AS debit_balance,
       CASE WHEN closing_balance_net < 0 THEN -closing_balance_net ELSE 0 END AS credit_balance
FROM ai.trial_balance_gl_year
WHERE statement = 'balance_sheet' AND closing_balance_net <> 0;
GO

-- ai.balance_sheet_check_year: per fiscal year: sum of balance-sheet balances, sum of the unclosed income/expense accounts and memorandum accounts.
-- balance_sheet_net + pnl_net should be 0 (debits = credits).
CREATE OR ALTER VIEW ai.balance_sheet_check_year AS
SELECT fiscal_year_id, fiscal_year,
       SUM(CASE WHEN statement = 'balance_sheet' THEN closing_balance_net ELSE 0 END) AS balance_sheet_net,
       SUM(CASE WHEN statement = 'income_statement' THEN closing_balance_net ELSE 0 END) AS pnl_net,
       SUM(CASE WHEN statement NOT IN ('balance_sheet','income_statement') THEN closing_balance_net ELSE 0 END) AS memorandum_and_other_net,
       SUM(CASE WHEN group_code IN ('11','12') THEN closing_balance_net ELSE 0 END) AS total_assets,
       -SUM(CASE WHEN group_code IN ('21','22') THEN closing_balance_net ELSE 0 END) AS total_liabilities,
       -SUM(CASE WHEN group_code = '31' THEN closing_balance_net ELSE 0 END) AS total_equity_before_result,
       -SUM(CASE WHEN statement = 'income_statement' THEN closing_balance_net ELSE 0 END) AS profit_for_year_unclosed
FROM ai.trial_balance_gl_year
GROUP BY fiscal_year_id, fiscal_year;
GO

-- ai.account_monthly_turnover: monthly debit/credit turnover per SL (regular documents only). Good for trends.
CREATE OR ALTER VIEW ai.account_monthly_turnover AS
SELECT l.fiscal_year, l.jalali_year, l.jalali_month, l.jalali_month_name, l.jalali_ym, l.fiscal_month_no,
       l.group_code, l.gl_code, l.gl_title, l.sl_code, l.sl_title, l.account_role, l.pnl_class,
       SUM(l.debit) AS total_debit, SUM(l.credit) AS total_credit, SUM(l.net_debit) AS net_debit,
       COUNT(*) AS line_count
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.is_regular = 1
GROUP BY l.fiscal_year, l.jalali_year, l.jalali_month, l.jalali_month_name, l.jalali_ym, l.fiscal_month_no,
         l.group_code, l.gl_code, l.gl_title, l.sl_code, l.sl_title, l.account_role, l.pnl_class;
GO

-- ai.pnl_by_account_year: income and cost accounts per fiscal year and SL (regular documents). kind = 'revenue' or 'cost'; amount is
-- positive in the account's natural direction (revenue = credit - debit, cost = debit - credit).
-- Costs of contracts live in GL 1117 (کار در جریان ساخت) during the year and are moved to GL 5111 (بهای تمام‌شده) by a year-end voucher
-- (pnl_class project_cost_wip -> project_cost_recognized), so for ANY year total contract cost = project_cost_wip + project_cost_recognized.
CREATE OR ALTER VIEW ai.pnl_by_account_year AS
SELECT l.fiscal_year_id, l.fiscal_year, l.pnl_class,
       CASE WHEN l.pnl_class IN ('contract_revenue','other_revenue') THEN 'revenue' ELSE 'cost' END AS kind,
       l.group_code, l.gl_code, l.gl_title, l.sl_code, l.sl_title, l.cost_nature_key,
       SUM(l.debit) AS total_debit, SUM(l.credit) AS total_credit,
       SUM(CASE WHEN l.pnl_class IN ('contract_revenue','other_revenue') THEN l.credit - l.debit ELSE l.debit - l.credit END) AS amount
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.is_regular = 1 AND l.pnl_class IS NOT NULL
GROUP BY l.fiscal_year_id, l.fiscal_year, l.pnl_class, l.group_code, l.gl_code, l.gl_title, l.sl_code, l.sl_title, l.cost_nature_key;
GO

-- ai.income_summary_year: one row per fiscal year: revenue, the cost classes and the resulting operating result (before nothing else).
-- profit_estimate = total_revenue - total_cost. It is an ESTIMATE from the ledger: machinery_unit_cost (GL 5112) is re-allocated to contracts only at
-- year end, and tax expense is inside admin_expense.
CREATE OR ALTER VIEW ai.income_summary_year AS
SELECT fiscal_year_id, fiscal_year,
       SUM(CASE WHEN pnl_class = 'contract_revenue' THEN amount ELSE 0 END) AS contract_revenue,
       SUM(CASE WHEN pnl_class = 'other_revenue' THEN amount ELSE 0 END) AS other_revenue,
       SUM(CASE WHEN kind = 'revenue' THEN amount ELSE 0 END) AS total_revenue,
       SUM(CASE WHEN pnl_class IN ('project_cost_wip','project_cost_recognized') THEN amount ELSE 0 END) AS contract_cost,
       SUM(CASE WHEN pnl_class = 'machinery_unit_cost' THEN amount ELSE 0 END) AS machinery_unit_cost,
       SUM(CASE WHEN pnl_class = 'plant_unit_cost' THEN amount ELSE 0 END) AS plant_unit_cost,
       SUM(CASE WHEN pnl_class = 'cost_of_goods_sold' THEN amount ELSE 0 END) AS cost_of_goods_sold,
       SUM(CASE WHEN pnl_class = 'operating_expense' THEN amount ELSE 0 END) AS operating_expense,
       SUM(CASE WHEN pnl_class = 'admin_expense' THEN amount ELSE 0 END) AS admin_expense,
       SUM(CASE WHEN pnl_class = 'financial_expense' THEN amount ELSE 0 END) AS financial_expense,
       SUM(CASE WHEN pnl_class = 'other_expense' THEN amount ELSE 0 END) AS other_expense,
       SUM(CASE WHEN kind = 'cost' THEN amount ELSE 0 END) AS total_cost,
       SUM(CASE WHEN kind = 'revenue' THEN amount ELSE -amount END) AS profit_estimate
FROM ai.pnl_by_account_year
GROUP BY fiscal_year_id, fiscal_year;
GO

-- ai.revenue_lines / ai.cost_lines: the revenue and cost lines of the ledger (regular, valid states 1/4/32) with all dimensions. Use for drill-downs
-- by contract, equipment, cost nature, counterparty, month ...
CREATE OR ALTER VIEW ai.revenue_lines AS
SELECT line_id, voucher_id, voucher_number, fiscal_year, voucher_date, jalali_date, jalali_ym, jalali_month_name, fiscal_month_no,
       pnl_class, gl_code, gl_title, sl_code, sl_title, credit - debit AS amount, debit, credit,
       contract_dl_code, contract_name, cost_center_dl_code, cost_center_name, project_dl_code, project_name,
       counterparty_dl_code, counterparty_name, other_detail_name, voucher_description, line_description
FROM ai.ledger_lines
WHERE is_valid_for_reports = 1 AND is_regular = 1 AND pnl_class IN ('contract_revenue','other_revenue');
GO

CREATE OR ALTER VIEW ai.cost_lines AS
SELECT line_id, voucher_id, voucher_number, fiscal_year, voucher_date, jalali_date, jalali_ym, jalali_month_name, fiscal_month_no,
       pnl_class, gl_code, gl_title, sl_code, sl_title, cost_nature_key, debit - credit AS amount, debit, credit,
       contract_dl_code, contract_name, equipment_dl_code, equipment_name, cost_center_dl_code, cost_center_name,
       project_dl_code, project_name, counterparty_dl_code, counterparty_name, other_detail_name,
       source_system, voucher_description, line_description
FROM ai.ledger_lines
WHERE is_valid_for_reports = 1 AND is_regular = 1
  AND pnl_class IN ('project_cost_wip','project_cost_recognized','machinery_unit_cost','plant_unit_cost','cost_of_goods_sold',
                    'operating_expense','admin_expense','financial_expense','other_expense');
GO

-- ai.cost_by_nature_year: contract/operating cost per fiscal year by cost nature (حقوق، اجاره، سوخت، پیمانکار …) merging the mirrored
-- accounts 1117xx / 5111xx / 5112xx / 5114xx / 6213xx by their 2-digit suffix (cost_nature_key). nature_title comes from the 1117xx account.
CREATE OR ALTER VIEW ai.cost_by_nature_year AS
SELECT c.fiscal_year, c.cost_nature_key,
       ISNULL(a.sl_title, N'(بدون معین 1117 متناظر)') AS nature_title,
       SUM(CASE WHEN c.pnl_class IN ('project_cost_wip','project_cost_recognized') THEN c.amount ELSE 0 END) AS contract_cost,
       SUM(CASE WHEN c.pnl_class = 'machinery_unit_cost' THEN c.amount ELSE 0 END) AS machinery_unit_cost,
       SUM(CASE WHEN c.pnl_class = 'plant_unit_cost' THEN c.amount ELSE 0 END) AS plant_unit_cost,
       SUM(CASE WHEN c.pnl_class = 'admin_expense' THEN c.amount ELSE 0 END) AS admin_expense,
       SUM(c.amount) AS total_amount
FROM ai.cost_lines c
LEFT JOIN ai.accounts a ON a.gl_code = '1117' AND a.cost_nature_key = c.cost_nature_key
WHERE c.cost_nature_key IS NOT NULL
GROUP BY c.fiscal_year, c.cost_nature_key, a.sl_title;
GO

-- ai.contract_financials_year: per fiscal year and contract (cost center 66xxxx): contract revenue, contract cost, margin, and the movement and
-- running (cumulative) balance of receivable / retention (حسن انجام کار دریافتنی) / advances received for that contract.
-- Balances are cumulative over all years up to and including fiscal_year (valid states 1/4/32 documents).
CREATE OR ALTER VIEW ai.contract_financials_year AS
WITH base AS (
    SELECT l.fiscal_year_id, l.fiscal_year, l.contract_dl_code,
           SUM(CASE WHEN l.is_regular = 1 AND l.account_role = 'contract_revenue' THEN l.credit - l.debit ELSE 0 END) AS revenue,
           SUM(CASE WHEN l.is_regular = 1 AND l.pnl_class IN ('project_cost_wip','project_cost_recognized') THEN l.net_debit ELSE 0 END) AS contract_cost,
           SUM(CASE WHEN l.account_role = 'receivable_customer' THEN l.net_debit ELSE 0 END) AS receivable_change,
           SUM(CASE WHEN l.account_role = 'retention_receivable' THEN l.net_debit ELSE 0 END) AS retention_receivable_change,
           SUM(CASE WHEN l.account_role = 'advance_received' THEN l.credit - l.debit ELSE 0 END) AS advance_received_change,
           COUNT(DISTINCT CASE WHEN l.is_regular = 1 AND l.account_role = 'contract_revenue' AND l.credit > 0 THEN l.voucher_id END) AS revenue_voucher_count,
           MIN(CASE WHEN l.account_role = 'contract_revenue' THEN l.voucher_date END) AS first_revenue_date,
           MAX(CASE WHEN l.account_role = 'contract_revenue' THEN l.voucher_date END) AS last_revenue_date
    FROM ai.ledger_lines l
    WHERE l.is_valid_for_reports = 1 AND l.contract_dl_code IS NOT NULL
    GROUP BY l.fiscal_year_id, l.fiscal_year, l.contract_dl_code
)
SELECT b.fiscal_year_id, b.fiscal_year, b.contract_dl_code, cc.cost_center_id, cc.cost_center_name AS contract_name, cc.state AS contract_state,
       b.revenue, b.contract_cost, b.revenue - b.contract_cost AS margin,
       CASE WHEN b.revenue <> 0 THEN (b.revenue - b.contract_cost) / b.revenue END AS margin_ratio,
       b.revenue_voucher_count, b.first_revenue_date, b.last_revenue_date,
       b.receivable_change, b.retention_receivable_change, b.advance_received_change,
       SUM(b.receivable_change) OVER (PARTITION BY b.contract_dl_code ORDER BY b.fiscal_year_id ROWS UNBOUNDED PRECEDING) AS receivable_balance,
       SUM(b.retention_receivable_change) OVER (PARTITION BY b.contract_dl_code ORDER BY b.fiscal_year_id ROWS UNBOUNDED PRECEDING) AS retention_receivable_balance,
       SUM(b.advance_received_change) OVER (PARTITION BY b.contract_dl_code ORDER BY b.fiscal_year_id ROWS UNBOUNDED PRECEDING) AS advance_received_balance
FROM base b
LEFT JOIN ai.cost_centers cc ON cc.dl_code = b.contract_dl_code;
GO

-- ai.contract_financials: all-time totals per contract with the employer (the customer with the largest receivable activity) and latest balances.
CREATE OR ALTER VIEW ai.contract_financials AS
WITH employer AS (
    SELECT contract_dl_code, counterparty_dl_code, counterparty_name,
           ROW_NUMBER() OVER (PARTITION BY contract_dl_code ORDER BY SUM(debit) DESC) AS rn
    FROM ai.ledger_lines
    WHERE is_valid_for_reports = 1 AND account_role = 'receivable_customer' AND contract_dl_code IS NOT NULL AND counterparty_dl_code IS NOT NULL
    GROUP BY contract_dl_code, counterparty_dl_code, counterparty_name
)
SELECT y.contract_dl_code, MAX(y.cost_center_id) AS cost_center_id, MAX(y.contract_name) AS contract_name, MAX(y.contract_state) AS contract_state,
       e.counterparty_dl_code AS employer_dl_code, e.counterparty_name AS employer_name,
       SUM(y.revenue) AS total_revenue, SUM(y.contract_cost) AS total_contract_cost, SUM(y.revenue) - SUM(y.contract_cost) AS total_margin,
       CASE WHEN SUM(y.revenue) <> 0 THEN (SUM(y.revenue) - SUM(y.contract_cost)) / SUM(y.revenue) END AS margin_ratio,
       SUM(y.revenue_voucher_count) AS revenue_voucher_count,
       MIN(y.first_revenue_date) AS first_revenue_date, MAX(y.last_revenue_date) AS last_revenue_date,
       SUM(y.receivable_change) AS receivable_balance,
       SUM(y.retention_receivable_change) AS retention_receivable_balance,
       SUM(y.advance_received_change) AS advance_received_balance,
       MIN(y.fiscal_year) AS first_fiscal_year, MAX(y.fiscal_year) AS last_fiscal_year
FROM ai.contract_financials_year y
LEFT JOIN employer e ON e.contract_dl_code = y.contract_dl_code AND e.rn = 1
GROUP BY y.contract_dl_code, e.counterparty_dl_code, e.counterparty_name;
GO

-- ai.contract_statements: one row per (voucher, contract) for contract revenue documents (صورت‌وضعیت کارفرما): revenue, VAT, receivable,
-- retention (حسن انجام کار) and insurance deposit amounts of that document. The statement number / contract number are only in the description.
CREATE OR ALTER VIEW ai.contract_statements AS
SELECT l.voucher_id, l.voucher_number, l.fiscal_year, l.voucher_date, l.jalali_date, l.contract_dl_code, MAX(l.contract_name) AS contract_name,
       SUM(CASE WHEN l.account_role = 'contract_revenue' THEN l.credit - l.debit ELSE 0 END) AS revenue_amount,
       SUM(CASE WHEN l.account_role = 'receivable_customer' THEN l.net_debit ELSE 0 END) AS receivable_amount,
       SUM(CASE WHEN l.account_role = 'vat_output' THEN l.credit - l.debit ELSE 0 END) AS vat_amount,
       SUM(CASE WHEN l.account_role = 'retention_receivable' THEN l.net_debit ELSE 0 END) AS retention_amount,
       SUM(CASE WHEN l.account_role = 'insurance_deposit_receivable' THEN l.net_debit ELSE 0 END) AS insurance_deposit_amount,
       MAX(CASE WHEN l.account_role = 'receivable_customer' THEN l.counterparty_name END) AS employer_name,
       MAX(l.voucher_description) AS description
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.is_regular = 1 AND l.contract_dl_code IS NOT NULL
  AND l.voucher_id IN (SELECT x.voucher_id FROM ai.ledger_lines x WHERE x.account_role = 'contract_revenue' AND x.credit > 0)
GROUP BY l.voucher_id, l.voucher_number, l.fiscal_year, l.voucher_date, l.jalali_date, l.contract_dl_code
HAVING SUM(CASE WHEN l.account_role = 'contract_revenue' THEN l.credit - l.debit ELSE 0 END) <> 0;
GO

-- ai.counterparty_balances: cumulative balance (all history, valid states 1/4/32, incl. opening/closing entries which cancel) per counterparty (person/company
-- tafsili) and balance-sheet SL. balance_net_debit > 0 = debit (they owe us / we paid in advance), < 0 = credit (we owe them).
CREATE OR ALTER VIEW ai.counterparty_balances AS
SELECT l.counterparty_dl_code, MAX(l.counterparty_name) AS counterparty_name, MAX(l.counterparty_party_id) AS party_id,
       l.gl_code, l.sl_code, MAX(l.sl_title) AS sl_title, MAX(l.account_role) AS account_role,
       SUM(l.debit) AS total_debit, SUM(l.credit) AS total_credit, SUM(l.net_debit) AS balance_net_debit,
       CASE WHEN SUM(l.net_debit) > 0 THEN N'بدهکار' WHEN SUM(l.net_debit) < 0 THEN N'بستانکار' ELSE N'صفر' END AS balance_side,
       MIN(l.voucher_date) AS first_activity_date, MAX(l.voucher_date) AS last_activity_date,
       COUNT(DISTINCT l.voucher_id) AS voucher_count
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.counterparty_dl_code IS NOT NULL AND l.statement = 'balance_sheet'
GROUP BY l.counterparty_dl_code, l.gl_code, l.sl_code;
GO

-- ai.customer_balances: per customer (employer) the receivable position. total_exposure = receivable + retention + notes - advances.
-- Positive = the customer owes the company.
CREATE OR ALTER VIEW ai.customer_balances AS
SELECT counterparty_dl_code, MAX(counterparty_name) AS counterparty_name, MAX(party_id) AS party_id,
       SUM(CASE WHEN account_role = 'receivable_customer' THEN balance_net_debit ELSE 0 END) AS receivable_balance,
       SUM(CASE WHEN account_role = 'retention_receivable' THEN balance_net_debit ELSE 0 END) AS retention_receivable_balance,
       SUM(CASE WHEN account_role = 'notes_receivable' THEN balance_net_debit ELSE 0 END) AS notes_receivable_balance,
       -SUM(CASE WHEN account_role = 'advance_received' THEN balance_net_debit ELSE 0 END) AS advance_received_balance,
       SUM(CASE WHEN account_role IN ('receivable_customer','retention_receivable','notes_receivable') THEN balance_net_debit
                WHEN account_role = 'advance_received' THEN balance_net_debit ELSE 0 END) AS total_exposure,
       MAX(last_activity_date) AS last_activity_date
FROM ai.counterparty_balances
WHERE account_role IN ('receivable_customer','retention_receivable','notes_receivable','advance_received')
GROUP BY counterparty_dl_code;
GO

-- ai.vendor_balances: per vendor/contractor the payable position. net_payable = payable + notes + retention payable - prepayments (positive = the company owes them).
CREATE OR ALTER VIEW ai.vendor_balances AS
SELECT counterparty_dl_code, MAX(counterparty_name) AS counterparty_name, MAX(party_id) AS party_id,
       -SUM(CASE WHEN account_role = 'payable_vendor' THEN balance_net_debit ELSE 0 END) AS payable_balance,
       -SUM(CASE WHEN account_role = 'notes_payable' THEN balance_net_debit ELSE 0 END) AS notes_payable_balance,
       -SUM(CASE WHEN account_role = 'retention_payable' THEN balance_net_debit ELSE 0 END) AS retention_payable_balance,
       SUM(CASE WHEN account_role = 'prepayment' THEN balance_net_debit ELSE 0 END) AS prepayment_balance,
       -SUM(CASE WHEN account_role IN ('payable_vendor','notes_payable','retention_payable','prepayment') THEN balance_net_debit ELSE 0 END) AS net_payable,
       MAX(last_activity_date) AS last_activity_date
FROM ai.counterparty_balances
WHERE account_role IN ('payable_vendor','notes_payable','retention_payable','prepayment')
GROUP BY counterparty_dl_code;
GO

-- ai.group_company_balances: balances with the Nasr group companies (SL 111300 receivable, SL 211000 payable). net_position > 0 = the group company owes us.
CREATE OR ALTER VIEW ai.group_company_balances AS
SELECT counterparty_dl_code, MAX(counterparty_name) AS counterparty_name,
       SUM(CASE WHEN account_role = 'receivable_group_company' THEN balance_net_debit ELSE 0 END) AS receivable_balance,
       -SUM(CASE WHEN account_role = 'payable_group_company' THEN balance_net_debit ELSE 0 END) AS payable_balance,
       SUM(CASE WHEN account_role IN ('receivable_group_company','payable_group_company') THEN balance_net_debit ELSE 0 END) AS net_position,
       MAX(last_activity_date) AS last_activity_date
FROM ai.counterparty_balances
WHERE account_role IN ('receivable_group_company','payable_group_company')
GROUP BY counterparty_dl_code;
GO

-- ai.guarantee_balances: bank guarantees and securities kept in memorandum accounts (SL 9111xx), per guarantee type, beneficiary/issuer, contract
-- and reference. balance_net_debit > 0 = outstanding.
CREATE OR ALTER VIEW ai.guarantee_balances AS
SELECT l.sl_code, MAX(l.sl_title) AS guarantee_type,
       l.counterparty_dl_code, MAX(l.counterparty_name) AS counterparty_name,
       l.contract_dl_code, MAX(l.contract_name) AS contract_name,
       l.other_detail_dl_code, MAX(l.other_detail_name) AS reference_detail,
       SUM(l.debit) AS total_issued, SUM(l.credit) AS total_released, SUM(l.net_debit) AS balance_net_debit,
       MIN(l.voucher_date) AS first_date, MAX(l.voucher_date) AS last_date
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.gl_code = '9111'
GROUP BY l.sl_code, l.counterparty_dl_code, l.contract_dl_code, l.other_detail_dl_code;
GO

-- ai.bank_balances: balance per bank account tafsili (SL 111005 bank balances and 111105 short-term deposits), cumulative, valid states 1/4/32.
CREATE OR ALTER VIEW ai.bank_balances AS
SELECT COALESCE(l.bank_account_dl_code, l.counterparty_dl_code) AS dl_code,
       MAX(COALESCE(l.bank_account_name, l.counterparty_name)) AS dl_title,
       CASE WHEN MAX(l.bank_account_dl_code) IS NOT NULL THEN N'حساب بانکی' ELSE N'بانک به‌عنوان شرکت/ثبت قدیمی' END AS dl_kind,
       MAX(l.bank_account_id) AS bank_account_id,
       l.sl_code, SUM(l.debit) AS total_debit, SUM(l.credit) AS total_credit, SUM(l.net_debit) AS balance,
       MAX(l.voucher_date) AS last_activity_date
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.account_role = 'bank'
GROUP BY COALESCE(l.bank_account_dl_code, l.counterparty_dl_code), l.sl_code;
GO

-- ai.bank_movements: every debit/credit on a bank SL (money in = debit, money out = credit) with the bank account and the document description.
-- Written directly on the base tables (not on ai.ledger_lines) so that "latest movements" queries stay fast.
CREATE OR ALTER VIEW ai.bank_movements AS
SELECT i.VoucherItemID AS line_id, v.VoucherID AS voucher_id, v.Number AS voucher_number, c.fiscal_year, CAST(v.Date AS date) AS voucher_date,
       c.jalali_date, c.jalali_ym, a.sl_code,
       COALESCE(CASE WHEN d4.DLTypeRef = 10 THEN d4.Code END, CASE WHEN d5.DLTypeRef = 10 THEN d5.Code END, i.DLLevel4) AS dl_code,
       COALESCE(CASE WHEN d4.DLTypeRef = 10 THEN RTRIM(d4.Title) END, CASE WHEN d5.DLTypeRef = 10 THEN RTRIM(d5.Title) END, RTRIM(d4.Title)) AS dl_title,
       COALESCE(CASE WHEN d4.DLTypeRef = 10 THEN d4.ReferenceID END, CASE WHEN d5.DLTypeRef = 10 THEN d5.ReferenceID END) AS bank_account_id,
       ISNULL(i.Debit, 0) AS money_in, ISNULL(i.Credit, 0) AS money_out, ISNULL(i.Debit, 0) - ISNULL(i.Credit, 0) AS net_debit,
       vt.OwnerSystem AS source_system, v.Description AS voucher_description, i.Description AS line_description
FROM FIN3.VoucherItem i
JOIN ai.accounts a ON a.sl_id = i.SLRef AND a.account_role = 'bank'
JOIN FIN3.Voucher v ON v.VoucherID = i.VoucherRef
JOIN FIN3.VoucherType vt ON vt.VoucherTypeID = v.VoucherTypeRef
JOIN ai.calendar c ON c.gregorian_date = CAST(v.Date AS date)
LEFT JOIN FIN3.DL d4 ON d4.Code = i.DLLevel4
LEFT JOIN FIN3.DL d5 ON d5.Code = i.DLLevel5
WHERE v.State IN (1,4,32) AND v.VoucherTypeRef NOT IN (5,6,7,8,9,11);
GO

-- ai.voucher_search: light-weight text search over document lines (no dimension joins): find documents by words in the voucher or line description.
-- Use it to locate vouchers (then join ai.ledger_lines / ai.vouchers on voucher_id for details). Search the header first (ai.vouchers.description) when possible.
CREATE OR ALTER VIEW ai.voucher_search AS
SELECT i.VoucherItemID AS line_id, v.VoucherID AS voucher_id, v.Number AS voucher_number, CAST(v.Date AS date) AS voucher_date, c.jalali_date, c.fiscal_year,
       v.State AS voucher_state_code, s.Code AS sl_code, RTRIM(s.Title) AS sl_title,
       ISNULL(i.Debit, 0) AS debit, ISNULL(i.Credit, 0) AS credit, v.Description AS voucher_description, i.Description AS line_description
FROM FIN3.VoucherItem i
JOIN FIN3.Voucher v ON v.VoucherID = i.VoucherRef
JOIN FIN3.SL s ON s.SLID = i.SLRef
JOIN ai.calendar c ON c.gregorian_date = CAST(v.Date AS date)
WHERE v.State IN (1,4,32);
GO

-- ai.vat_lines: VAT lines (input = SL 111414, output = SL 211212, deposit = SL 211228) with the tax period (other_detail like "دوره دوم سال 1405").
CREATE OR ALTER VIEW ai.vat_lines AS
SELECT line_id, voucher_id, voucher_number, fiscal_year, voucher_date, jalali_date, account_role, sl_code, sl_title,
       debit, credit, net_debit, other_detail_dl_code AS tax_period_dl_code, other_detail_name AS tax_period_or_detail,
       counterparty_dl_code, counterparty_name, contract_dl_code, contract_name, voucher_description, line_description
FROM ai.ledger_lines
WHERE is_valid_for_reports = 1 AND is_regular = 1 AND account_role IN ('vat_input','vat_output','vat_deposit');
GO

-- ai.facility_balances: bank loans/facilities (tafsili type 13): principal and interest SLs per facility; balance_net_debit < 0 = outstanding debt.
CREATE OR ALTER VIEW ai.facility_balances AS
SELECT l.facility_dl_code, MAX(l.facility_name) AS facility_name, l.sl_code, MAX(l.sl_title) AS sl_title,
       SUM(l.debit) AS total_debit, SUM(l.credit) AS total_credit, SUM(l.net_debit) AS balance_net_debit,
       MIN(l.voucher_date) AS first_date, MAX(l.voucher_date) AS last_date
FROM ai.ledger_lines l
WHERE l.is_valid_for_reports = 1 AND l.facility_dl_code IS NOT NULL
GROUP BY l.facility_dl_code, l.sl_code;
GO

-- ai.equipment_cost_year: operating cost per machine/vehicle (cost centers 41/42/43/44) per fiscal year and cost nature (repairs, fuel, depreciation ...).
CREATE OR ALTER VIEW ai.equipment_cost_year AS
SELECT c.fiscal_year, c.equipment_dl_code, MAX(c.equipment_name) AS equipment_name, e.category AS equipment_category,
       c.sl_code, MAX(c.sl_title) AS sl_title, c.cost_nature_key, c.pnl_class,
       SUM(c.amount) AS amount, COUNT(*) AS line_count
FROM ai.cost_lines c
LEFT JOIN ai.cost_centers e ON e.dl_code = c.equipment_dl_code
WHERE c.equipment_dl_code IS NOT NULL
GROUP BY c.fiscal_year, c.equipment_dl_code, e.category, c.sl_code, c.cost_nature_key, c.pnl_class;
GO

-- ai.petty_cash_balances: petty-cash (تنخواه) balance per holder (SL 111003).
CREATE OR ALTER VIEW ai.petty_cash_balances AS
SELECT counterparty_dl_code, MAX(counterparty_name) AS holder_name, SUM(debit) AS total_debit, SUM(credit) AS total_credit,
       SUM(net_debit) AS balance, MAX(voucher_date) AS last_activity_date
FROM ai.ledger_lines
WHERE is_valid_for_reports = 1 AND account_role = 'petty_cash'
GROUP BY counterparty_dl_code;
GO

-- ai.voucher_sources: which module form produced an accounting document (depreciation, acquisition receipt, sales, elimination ...), via FIN3.VoucherReference.
CREATE OR ALTER VIEW ai.voucher_sources AS
SELECT r.VoucherRef AS voucher_id,
       r.OriginalEntityCode AS entity_code,
       RIGHT(el.EntityName, CHARINDEX(',', REVERSE(el.EntityName)) - 1) AS source_entity,
       COUNT(*) AS reference_count,
       MAX(r.Description) AS description
FROM FIN3.VoucherReference r
LEFT JOIN SYS3.EntityLookup el ON el.Code = r.OriginalEntityCode
GROUP BY r.VoucherRef, r.OriginalEntityCode, el.EntityName;
GO
