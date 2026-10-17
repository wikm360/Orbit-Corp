-- ai.vouchers: one row per accounting document (FIN3.Voucher) with totals, type, state, creator and Jalali dates.
CREATE OR ALTER VIEW ai.vouchers AS
SELECT v.VoucherID AS voucher_id,
       v.Number AS voucher_number,
       v.Sequence AS voucher_sequence,
       v.DailyNumber AS daily_number,
       v.FiscalYearRef AS fiscal_year_id,
       c.fiscal_year,
       CAST(v.Date AS date) AS voucher_date,
       c.jalali_date,
       c.jalali_year,
       c.jalali_month,
       c.jalali_month_name,
       c.jalali_ym,
       c.fiscal_month_no,
       v.VoucherTypeRef AS voucher_type_id,
       vt.Title AS voucher_type,
       vt.OwnerSystem AS source_system,
       v.State AS voucher_state_code,
       st.Value AS voucher_state,
       CASE WHEN v.State IN (1,4,32) THEN 1 ELSE 0 END AS is_valid_for_reports,
       CASE WHEN v.State IN (4,32) THEN 1 ELSE 0 END AS is_reviewed,
       CASE WHEN v.State = 32 THEN 1 ELSE 0 END AS is_final,
       CASE WHEN v.VoucherTypeRef IN (6,11) THEN 1 ELSE 0 END AS is_opening,
       CASE WHEN v.VoucherTypeRef IN (5,7) THEN 1 ELSE 0 END AS is_closing,
       CASE WHEN v.VoucherTypeRef IN (5,6,7,8,9,11) THEN 0 ELSE 1 END AS is_regular,
       v.Description AS description,
       v.AuxiliaryNumber AS auxiliary_number,
       ISNULL(t.total_debit, 0) AS total_debit,
       ISNULL(t.total_credit, 0) AS total_credit,
       ISNULL(t.line_count, 0) AS line_count,
       cr.Name AS created_by,
       CAST(v.CreationDate AS date) AS created_date,
       lm.Name AS last_modified_by,
       CAST(v.LastModificationDate AS date) AS last_modified_date,
       CAST(v.ReviewDate AS date) AS review_date,
       v.ReviewNumber AS review_number,
       v.IsReadonly AS is_readonly
FROM FIN3.Voucher v
JOIN FIN3.VoucherType vt ON vt.VoucherTypeID = v.VoucherTypeRef
JOIN ai.calendar c ON c.gregorian_date = CAST(v.Date AS date)
LEFT JOIN SYS3.Lookup st ON st.Type = 'VoucherState' AND st.Code = v.State
LEFT JOIN SYS3.[User] cr ON cr.UserID = v.Creator
LEFT JOIN SYS3.[User] lm ON lm.UserID = v.LastModifier
LEFT JOIN (SELECT i.VoucherRef, SUM(ISNULL(i.Debit,0)) AS total_debit, SUM(ISNULL(i.Credit,0)) AS total_credit, COUNT(*) AS line_count
           FROM FIN3.VoucherItem i GROUP BY i.VoucherRef) t ON t.VoucherRef = v.VoucherID;
GO

-- ai.ledger_lines: THE main fact view. One row per accounting document line (FIN3.VoucherItem, ~693K rows) joined with its document,
-- account hierarchy, Jalali/fiscal calendar and the resolved tafsili dimensions (counterparty, contract cost-center, equipment, cost-center, project,
-- bank account, facility, other detail). debit/credit are NULL-safe; net_debit = debit - credit.
-- ALWAYS filter on fiscal_year / voucher_date and is_valid_for_reports = 1 for financial answers. is_valid_for_reports = states 1 (temporary, i.e. entered but not
-- yet reviewed - the latest 1-2 months are in this state), 4 (reviewed) and 32 (final); state 2 (note/یادداشت) is excluded. Use is_reviewed = 1 for strictly reviewed data;
-- exclude is_opening / is_closing lines when you want period turnover (use is_regular = 1).
CREATE OR ALTER VIEW ai.ledger_lines AS
SELECT i.VoucherItemID AS line_id,
       v.VoucherID AS voucher_id,
       v.Number AS voucher_number,
       v.Sequence AS voucher_sequence,
       i.RowNumber AS line_no,
       v.FiscalYearRef AS fiscal_year_id,
       c.fiscal_year,
       CAST(v.Date AS date) AS voucher_date,
       c.jalali_date,
       c.jalali_year,
       c.jalali_month,
       c.jalali_month_name,
       c.jalali_ym,
       c.fiscal_month_no,
       c.fiscal_quarter,
       v.VoucherTypeRef AS voucher_type_id,
       vt.Title AS voucher_type,
       vt.OwnerSystem AS source_system,
       v.State AS voucher_state_code,
       st.Value AS voucher_state,
       CASE WHEN v.State IN (1,4,32) THEN 1 ELSE 0 END AS is_valid_for_reports,
       CASE WHEN v.State IN (4,32) THEN 1 ELSE 0 END AS is_reviewed,
       CASE WHEN v.State = 32 THEN 1 ELSE 0 END AS is_final,
       CASE WHEN v.VoucherTypeRef IN (6,11) THEN 1 ELSE 0 END AS is_opening,
       CASE WHEN v.VoucherTypeRef IN (5,7) THEN 1 ELSE 0 END AS is_closing,
       CASE WHEN v.VoucherTypeRef IN (5,6,7,8,9,11) THEN 0 ELSE 1 END AS is_regular,
       cr.Name AS created_by,
       v.Description AS voucher_description,
       i.Description AS line_description,
       a.group_code,
       a.group_title,
       a.gl_code,
       a.gl_title,
       a.sl_id,
       a.sl_code,
       a.sl_title,
       a.account_type,
       a.normal_balance,
       a.statement,
       a.financial_class,
       a.pnl_class,
       a.cost_nature_key,
       a.pnl_statement,
       a.detail_category,
       a.account_role,
       ISNULL(i.Debit, 0) AS debit,
       ISNULL(i.Credit, 0) AS credit,
       ISNULL(i.Debit, 0) - ISNULL(i.Credit, 0) AS net_debit,
       i.Quantity AS quantity,
       i.DLLevel4 AS dl4_code,
       i.DLLevel5 AS dl5_code,
       i.DLLevel6 AS dl6_code,
       CASE WHEN d4.DLTypeRef IN (1,2) THEN d4.Code WHEN d5.DLTypeRef IN (1,2) THEN d5.Code WHEN d6.DLTypeRef IN (1,2) THEN d6.Code END AS counterparty_dl_code,
       CASE WHEN d4.DLTypeRef IN (1,2) THEN RTRIM(d4.Title) WHEN d5.DLTypeRef IN (1,2) THEN RTRIM(d5.Title) WHEN d6.DLTypeRef IN (1,2) THEN RTRIM(d6.Title) END AS counterparty_name,
       CASE WHEN d4.DLTypeRef IN (1,2) THEN d4.ReferenceID WHEN d5.DLTypeRef IN (1,2) THEN d5.ReferenceID WHEN d6.DLTypeRef IN (1,2) THEN d6.ReferenceID END AS counterparty_party_id,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) = '66') THEN d4.Code WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) = '66') THEN d5.Code WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) = '66') THEN d6.Code END AS contract_dl_code,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) = '66') THEN RTRIM(d4.Title) WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) = '66') THEN RTRIM(d5.Title) WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) = '66') THEN RTRIM(d6.Title) END AS contract_name,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) = '66') THEN d4.ReferenceID WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) = '66') THEN d5.ReferenceID WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) = '66') THEN d6.ReferenceID END AS contract_cost_center_id,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) IN ('41','42','43','44')) THEN d4.Code WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) IN ('41','42','43','44')) THEN d5.Code WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) IN ('41','42','43','44')) THEN d6.Code END AS equipment_dl_code,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) IN ('41','42','43','44')) THEN RTRIM(d4.Title) WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) IN ('41','42','43','44')) THEN RTRIM(d5.Title) WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) IN ('41','42','43','44')) THEN RTRIM(d6.Title) END AS equipment_name,
       CASE WHEN (d4.DLTypeRef = 4 AND LEFT(d4.Code,2) IN ('41','42','43','44')) THEN d4.ReferenceID WHEN (d5.DLTypeRef = 4 AND LEFT(d5.Code,2) IN ('41','42','43','44')) THEN d5.ReferenceID WHEN (d6.DLTypeRef = 4 AND LEFT(d6.Code,2) IN ('41','42','43','44')) THEN d6.ReferenceID END AS equipment_cost_center_id,
       CASE WHEN d4.DLTypeRef = 4 THEN d4.Code WHEN d5.DLTypeRef = 4 THEN d5.Code WHEN d6.DLTypeRef = 4 THEN d6.Code END AS cost_center_dl_code,
       CASE WHEN d4.DLTypeRef = 4 THEN RTRIM(d4.Title) WHEN d5.DLTypeRef = 4 THEN RTRIM(d5.Title) WHEN d6.DLTypeRef = 4 THEN RTRIM(d6.Title) END AS cost_center_name,
       CASE WHEN d4.DLTypeRef = 4 THEN d4.ReferenceID WHEN d5.DLTypeRef = 4 THEN d5.ReferenceID WHEN d6.DLTypeRef = 4 THEN d6.ReferenceID END AS cost_center_id,
       CASE WHEN d4.DLTypeRef = 5 THEN d4.Code WHEN d5.DLTypeRef = 5 THEN d5.Code WHEN d6.DLTypeRef = 5 THEN d6.Code END AS project_dl_code,
       CASE WHEN d4.DLTypeRef = 5 THEN RTRIM(d4.Title) WHEN d5.DLTypeRef = 5 THEN RTRIM(d5.Title) WHEN d6.DLTypeRef = 5 THEN RTRIM(d6.Title) END AS project_name,
       CASE WHEN d4.DLTypeRef = 5 THEN d4.ReferenceID WHEN d5.DLTypeRef = 5 THEN d5.ReferenceID WHEN d6.DLTypeRef = 5 THEN d6.ReferenceID END AS project_id,
       CASE WHEN d4.DLTypeRef = 10 THEN d4.Code WHEN d5.DLTypeRef = 10 THEN d5.Code WHEN d6.DLTypeRef = 10 THEN d6.Code END AS bank_account_dl_code,
       CASE WHEN d4.DLTypeRef = 10 THEN RTRIM(d4.Title) WHEN d5.DLTypeRef = 10 THEN RTRIM(d5.Title) WHEN d6.DLTypeRef = 10 THEN RTRIM(d6.Title) END AS bank_account_name,
       CASE WHEN d4.DLTypeRef = 10 THEN d4.ReferenceID WHEN d5.DLTypeRef = 10 THEN d5.ReferenceID WHEN d6.DLTypeRef = 10 THEN d6.ReferenceID END AS bank_account_id,
       CASE WHEN d4.DLTypeRef = 13 THEN d4.Code WHEN d5.DLTypeRef = 13 THEN d5.Code WHEN d6.DLTypeRef = 13 THEN d6.Code END AS facility_dl_code,
       CASE WHEN d4.DLTypeRef = 13 THEN RTRIM(d4.Title) WHEN d5.DLTypeRef = 13 THEN RTRIM(d5.Title) WHEN d6.DLTypeRef = 13 THEN RTRIM(d6.Title) END AS facility_name,
       CASE WHEN d4.DLTypeRef = 27 THEN d4.Code WHEN d5.DLTypeRef = 27 THEN d5.Code WHEN d6.DLTypeRef = 27 THEN d6.Code END AS other_detail_dl_code,
       CASE WHEN d4.DLTypeRef = 27 THEN RTRIM(d4.Title) WHEN d5.DLTypeRef = 27 THEN RTRIM(d5.Title) WHEN d6.DLTypeRef = 27 THEN RTRIM(d6.Title) END AS other_detail_name,
       i.FollowUpNumber AS follow_up_number,
       CAST(i.FollowUpDate AS date) AS follow_up_date
FROM FIN3.VoucherItem i
JOIN FIN3.Voucher v ON v.VoucherID = i.VoucherRef
JOIN FIN3.VoucherType vt ON vt.VoucherTypeID = v.VoucherTypeRef
JOIN ai.calendar c ON c.gregorian_date = CAST(v.Date AS date)
JOIN ai.accounts a ON a.sl_id = i.SLRef
LEFT JOIN SYS3.Lookup st ON st.Type = 'VoucherState' AND st.Code = v.State
LEFT JOIN SYS3.[User] cr ON cr.UserID = v.Creator
LEFT JOIN FIN3.DL d4 ON d4.Code = i.DLLevel4
LEFT JOIN FIN3.DL d5 ON d5.Code = i.DLLevel5
LEFT JOIN FIN3.DL d6 ON d6.Code = i.DLLevel6;
GO
