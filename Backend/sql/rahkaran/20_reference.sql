-- Reference / master-data views: fiscal years, chart of accounts, tafsili (DL) accounts, parties, cost centers, projects, banks, users.

-- ai.fiscal_years: one row per fiscal year. fiscal_year is the real 4-digit label (the original GNR3.FiscalYear.Title is 2 digits for old years).
-- The company's fiscal year runs 1 Mehr .. 31 Shahrivar; fiscal_year 1404 = 1404/07/01 .. 1405/06/31.
CREATE OR ALTER VIEW ai.fiscal_years AS
SELECT fy.FiscalYearID AS fiscal_year_id,
       cs.fiscal_year AS fiscal_year,
       fy.Title AS original_title,
       CAST(lf.StartDate AS date) AS start_date,
       CAST(lf.EndDate AS date) AS end_date,
       cs.jalali_date AS start_jalali,
       ce.jalali_date AS end_jalali,
       lf.ClosingState AS closing_state_code,
       CASE lf.ClosingState WHEN 6 THEN N'بسته‌شده (بستن حساب‌ها و افتتاحیه سال بعد انجام شده)' WHEN 4 THEN N'جاری (باز)'
            WHEN 0 THEN N'شروع نشده' WHEN 2 THEN N'نخستین سال' ELSE N'نامشخص' END AS closing_state,
       (SELECT COUNT(*) FROM FIN3.Voucher v WHERE v.FiscalYearRef = fy.FiscalYearID) AS voucher_count,
       (SELECT MIN(CAST(v.Date AS date)) FROM FIN3.Voucher v WHERE v.FiscalYearRef = fy.FiscalYearID) AS first_voucher_date,
       (SELECT MAX(CAST(v.Date AS date)) FROM FIN3.Voucher v WHERE v.FiscalYearRef = fy.FiscalYearID) AS last_voucher_date
FROM GNR3.FiscalYear fy
JOIN GNR3.LedgerFiscalYear lf ON lf.FiscalYearRef = fy.FiscalYearID
JOIN ai.calendar cs ON cs.gregorian_date = CAST(lf.StartDate AS date)
JOIN ai.calendar ce ON ce.gregorian_date = CAST(lf.EndDate AS date);
GO

-- ai.accounts: chart of accounts, one row per SL (moin) with its GL (kol) and account group, plus derived classification.
CREATE OR ALTER VIEW ai.accounts AS
SELECT s.SLID AS sl_id,
       s.Code AS sl_code,
       RTRIM(s.Title) AS sl_title,
       g.GLID AS gl_id,
       g.Code AS gl_code,
       RTRIM(g.Title) AS gl_title,
       ag.AccountGroupID AS group_id,
       ag.Code AS group_code,
       RTRIM(ag.Title) AS group_title,
       CASE s.Type WHEN 1 THEN N'دائم' WHEN 2 THEN N'موقت' WHEN 3 THEN N'انتظامی' WHEN 4 THEN N'انتظامی قابل بستن' END AS account_type,
       CASE s.Nature WHEN 1 THEN N'مهم نیست' WHEN 2 THEN N'بدهکار' WHEN 3 THEN N'بستانکار' END AS normal_balance,
       CASE WHEN ag.Code IN ('11','12','21','22','31') THEN 'balance_sheet'
            WHEN ag.Code IN ('41','51','61','62') THEN 'income_statement'
            WHEN ag.Code = '81' THEN 'absorption' ELSE 'memorandum' END AS statement,
       CASE ag.Code WHEN '11' THEN N'دارایی جاری' WHEN '12' THEN N'دارایی غیرجاری' WHEN '21' THEN N'بدهی جاری' WHEN '22' THEN N'بدهی غیرجاری'
            WHEN '31' THEN N'حقوق صاحبان سهام' WHEN '41' THEN N'فروش و درآمد' WHEN '51' THEN N'بهای تمام‌شده' WHEN '61' THEN N'هزینه‌های فعالیت'
            WHEN '62' THEN N'سایر هزینه/درآمدهای غیرعملیاتی' WHEN '81' THEN N'جذب و انحرافات' WHEN '91' THEN N'حساب انتظامی' WHEN '92' THEN N'طرف‌حساب انتظامی' END AS financial_class,
       CASE
            WHEN g.Code = '1117' THEN 'project_cost_wip'            -- هزینه قراردادها در جریان (سال جاری؛ پایان سال به 5111 منتقل می‌شود)
            WHEN g.Code = '1118' THEN 'project_wip_accumulated'
            WHEN g.Code = '5111' THEN 'project_cost_recognized'     -- بهای تمام‌شده خدمات/پیمان شناسایی‌شده (پایان سال)
            WHEN g.Code = '5110' THEN 'cost_of_goods_sold'
            WHEN g.Code = '5112' THEN 'machinery_unit_cost'         -- هزینه واحد ماشین‌آلات (قبل از تسهیم)
            WHEN g.Code = '5114' THEN 'plant_unit_cost'
            WHEN g.Code = '4110' THEN 'contract_revenue'
            WHEN g.Code IN ('4113','4114','4115') THEN 'other_revenue'
            WHEN g.Code IN ('6110','6111','6112','6113','6114','6109') THEN 'operating_expense'
            WHEN g.Code = '6213' THEN 'admin_expense'
            WHEN g.Code = '6211' THEN 'financial_expense'
            WHEN g.Code IN ('6210','6212','6215','6217') THEN 'other_expense'
            WHEN ag.Code = '41' THEN 'other_revenue'
            WHEN ag.Code = '51' THEN 'cost_of_goods_sold'
            WHEN ag.Code = '61' THEN 'operating_expense'
            WHEN ag.Code = '62' THEN 'other_expense'
       END AS pnl_class,
       CASE WHEN g.Code IN ('1117','5111','5112','5114','6213') THEN RIGHT(s.Code, 2) END AS cost_nature_key,
       CASE
            WHEN s.Code = '111001' THEN 'cash'
            WHEN s.Code = '111003' THEN 'petty_cash'
            WHEN s.Code IN ('111005','111105') THEN 'bank'
            WHEN s.Code = '111300' THEN 'receivable_group_company'
            WHEN s.Code IN ('111301','111302') THEN 'receivable_customer'
            WHEN s.Code = '111303' THEN 'notes_receivable'
            WHEN s.Code = '111304' THEN 'retention_receivable'
            WHEN s.Code = '111307' THEN 'contracts_in_progress'
            WHEN s.Code IN ('111401','111420') THEN 'performance_deposit_receivable'
            WHEN s.Code IN ('111403','111404') THEN 'cash_deposit_guarantee_receivable'
            WHEN s.Code = '111402' THEN 'insurance_deposit_receivable'
            WHEN s.Code = '111405' THEN 'tax_prepaid'
            WHEN s.Code = '111410' THEN 'tax_withheld_by_employer'
            WHEN s.Code = '111414' THEN 'vat_input'
            WHEN s.Code IN ('111406','111415') THEN 'staff_receivable'
            WHEN s.Code = '111422' THEN 'other_receivable_parties'
            WHEN g.Code = '1119' THEN 'prepayment'
            WHEN g.Code = '1117' THEN 'project_cost_wip'
            WHEN g.Code = '1124' THEN 'assets_held_for_sale'
            WHEN s.Code = '121013' THEN 'fixed_asset_control'
            WHEN g.Code = '1210' THEN 'fixed_assets'
            WHEN g.Code = '1211' THEN 'accumulated_depreciation'
            WHEN s.Code = '211000' THEN 'payable_group_company'
            WHEN s.Code IN ('211001','211002','211238') THEN 'payable_vendor'
            WHEN s.Code = '211259' OR s.Code = '211004' THEN 'notes_payable'
            WHEN s.Code IN ('211250','211006') THEN 'net_salary_payable'
            WHEN s.Code IN ('211241','211005') THEN 'payroll_deductions_payable'
            WHEN s.Code IN ('211009','211207','211208') THEN 'retention_payable'
            WHEN s.Code = '211211' THEN 'insurance_deposit_payable'
            WHEN s.Code = '211212' THEN 'vat_output'
            WHEN s.Code = '211228' THEN 'vat_deposit'
            WHEN g.Code = '2114' THEN 'advance_received'
            WHEN s.Code = '211501' THEN 'income_tax_provision'
            WHEN g.Code = '2117' THEN 'bank_facility'
            WHEN s.Code = '211203' THEN 'bank_credit'
            WHEN s.Code = '221301' THEN 'severance_provision'
            WHEN g.Code = '3110' THEN 'share_capital'
            WHEN g.Code IN ('3113','3114') THEN 'retained_earnings'
            WHEN s.Code = '411010' THEN 'contract_revenue'
            WHEN g.Code = '9111' THEN 'memorandum_debit'
            WHEN g.Code = '9211' THEN 'memorandum_credit'
       END AS account_role,
       CASE WHEN g.Code = '9111' AND s.Code IN ('911101','911102','911103','911108') THEN 1
            WHEN g.Code = '9211' AND s.Code IN ('921101','921102','921103','921108') THEN 1 ELSE 0 END AS is_guarantee_account,
       s.State AS is_active,
       CASE WHEN EXISTS (SELECT 1 FROM FIN3.VoucherItem i WHERE i.SLRef = s.SLID) THEN 1 ELSE 0 END AS has_postings
FROM FIN3.SL s
JOIN FIN3.GL g ON g.GLID = s.GLRef
JOIN FIN3.AccountGroup ag ON ag.AccountGroupID = g.AccountGroupRef;
GO

-- ai.dl_accounts: tafsili (detail) accounts with type, a derived business category (from the DL code prefix) and the resolved reference entity.
CREATE OR ALTER VIEW ai.dl_accounts AS
SELECT d.DLID AS dl_id,
       d.Code AS dl_code,
       RTRIM(d.Title) AS dl_title,
       d.DLTypeRef AS dl_type_id,
       t.Title AS dl_type,
       CASE
            WHEN d.DLTypeRef = 1 AND LEFT(d.Code,2) = '24' THEN N'کارمند'
            WHEN d.DLTypeRef = 1 AND LEFT(d.Code,2) = '25' THEN N'شخص (کارمند یا پیمانکار/تأمین‌کننده)'
            WHEN d.DLTypeRef = 1 THEN N'شخص حقیقی (تأمین‌کننده/پیمانکار/راننده/فروشگاه)'
            WHEN d.DLTypeRef = 2 THEN N'شرکت/سازمان'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '41' THEN N'ماشین‌آلات سنگین'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '42' THEN N'کامیون/کمپرسی'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '43' THEN N'خودرو سبک'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '44' THEN N'تجهیزات ثابت (سنگ‌شکن/بچینگ)'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '49' THEN N'مرکز واسط استهلاک'
            WHEN d.DLTypeRef = 4 AND LEFT(d.Code,2) = '66' THEN N'قرارداد/پروژه اجرایی'
            WHEN d.DLTypeRef = 4 THEN N'مرکز هزینه (سایر)'
            WHEN d.DLTypeRef = 5 THEN N'پروژه'
            WHEN d.DLTypeRef = 10 THEN N'حساب بانکی'
            WHEN d.DLTypeRef = 13 THEN N'تسهیلات مالی (وام)'
            WHEN d.DLTypeRef = 27 AND LEFT(d.Code,2) = '99' THEN N'دوره مالیات بر ارزش افزوده / حساب واسط'
            WHEN d.DLTypeRef = 27 AND LEFT(d.Code,2) = '90' THEN N'سایر (قبض، مواد، کسورات، شماره قرارداد فرعی)'
            WHEN d.DLTypeRef = 27 THEN N'سایر (عمومی، واحد سازمانی، حساب‌های متفرقه)'
            ELSE t.Title END AS dl_category,
       d.ReferenceID AS reference_id,
       CASE WHEN d.DLTypeRef IN (1,2) THEN d.ReferenceID END AS party_id,
       CASE WHEN d.DLTypeRef = 4 THEN d.ReferenceID END AS cost_center_id,
       CASE WHEN d.DLTypeRef = 5 THEN d.ReferenceID END AS project_id,
       CASE WHEN d.DLTypeRef = 10 THEN d.ReferenceID END AS bank_account_id,
       d.State AS is_active,
       d.Description AS description
FROM FIN3.DL d
JOIN FIN3.DLType t ON t.DLTypeID = d.DLTypeRef;
GO

-- ai.parties: persons and companies (GNR3.Party) with main address and links to tafsili / employee.
CREATE OR ALTER VIEW ai.parties AS
SELECT p.PartyID AS party_id,
       CASE p.Type WHEN 0 THEN N'شخص حقیقی' WHEN 1 THEN N'شخص حقوقی' END AS party_type,
       p.FullName AS full_name,
       p.FirstName AS first_name,
       p.LastName AS last_name,
       p.CompanyName AS company_name,
       p.NationalID AS national_id,
       p.EconomicCode AS economic_code,
       p.RegistrationCode AS registration_code,
       p.IDNumber AS id_number,
       p.FatherName AS father_name,
       CAST(p.BirthDate AS date) AS birth_date,
       CASE p.Gender WHEN 1 THEN N'مرد' WHEN 2 THEN N'زن' END AS gender,
       p.Mobile AS mobile,
       p.Tel AS phone,
       p.Email AS email,
       ct.Value AS company_type,
       addr.address_text AS main_address,
       addr.city AS city,
       CASE WHEN EXISTS (SELECT 1 FROM HCM3.Employee e WHERE e.PartyRef = p.PartyID) THEN 1 ELSE 0 END AS is_employee,
       (SELECT MIN(e.EmployeeID) FROM HCM3.Employee e WHERE e.PartyRef = p.PartyID) AS employee_id,
       (SELECT STRING_AGG(d.Code, ',') FROM FIN3.DL d WHERE d.ReferenceID = p.PartyID AND d.DLTypeRef IN (1,2)) AS dl_codes,
       CAST(p.CreationDate AS date) AS created_date
FROM GNR3.Party p
LEFT JOIN SYS3.Lookup ct ON ct.Type = 'CompanyType' AND ct.Code = p.CompanyType
OUTER APPLY (
    SELECT TOP 1 a.Details AS address_text, rd.Name AS city
    FROM GNR3.PartyAddress pa
    JOIN GNR3.Address a ON a.AddressID = pa.AddressRef
    LEFT JOIN GNR3.RegionalDivision rd ON rd.RegionalDivisionID = a.RegionalDivisionRef
    WHERE pa.PartyRef = p.PartyID
    ORDER BY pa.IsMainAddress DESC, pa.PartyAddressID
) addr
WHERE p.PartyID > 0;
GO

-- ai.cost_centers: cost centers (GNR3.CostCenter) with the business category derived from the DL code prefix.
-- Every machine/vehicle is a cost center (41/42/43/44...) and every executive contract/project is a cost center with code 66xxxx.
CREATE OR ALTER VIEW ai.cost_centers AS
SELECT c.CostCenterID AS cost_center_id,
       RTRIM(c.Name) AS cost_center_name,
       LTRIM(RTRIM(c.Number)) AS cost_center_number,
       d.Code AS dl_code,
       CASE c.Type WHEN 1 THEN N'اداری' WHEN 2 THEN N'تولیدی' WHEN 3 THEN N'خدماتی' WHEN 4 THEN N'پیمانکار خارجی' END AS cost_center_type,
       CASE c.State WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS state,
       CASE
            WHEN LEFT(d.Code,2) = '41' THEN N'ماشین‌آلات سنگین'
            WHEN LEFT(d.Code,2) = '42' THEN N'کامیون/کمپرسی'
            WHEN LEFT(d.Code,2) = '43' THEN N'خودرو سبک'
            WHEN LEFT(d.Code,2) = '44' THEN N'تجهیزات ثابت (سنگ‌شکن/بچینگ)'
            WHEN LEFT(d.Code,2) = '49' THEN N'مرکز واسط استهلاک'
            WHEN LEFT(d.Code,2) = '66' THEN N'قرارداد/پروژه اجرایی'
            WHEN d.Code IS NULL THEN N'بدون تفصیلی'
            ELSE N'سایر' END AS category,
       CASE WHEN LEFT(d.Code,2) = '66' THEN 1 ELSE 0 END AS is_contract,
       CASE WHEN LEFT(d.Code,2) IN ('41','42','43','44') THEN 1 ELSE 0 END AS is_equipment
FROM GNR3.CostCenter c
LEFT JOIN FIN3.DL d ON d.DLTypeRef = 4 AND d.ReferenceID = c.CostCenterID;
GO

-- ai.projects: GNR3.Project with its tafsili code. Note: on expense lines the project dimension is mostly the generic projects
-- 661020 "عمومی(اداری)" and 661010 "عمومی"; the meaningful contract dimension is the cost center 66xxxx (see ai.cost_centers.is_contract).
CREATE OR ALTER VIEW ai.projects AS
SELECT pr.ProjectID AS project_id,
       RTRIM(pr.Name) AS project_name,
       LTRIM(RTRIM(pr.Number)) AS project_number,
       d.Code AS dl_code,
       CASE pr.State WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS state
FROM GNR3.Project pr
LEFT JOIN FIN3.DL d ON d.DLTypeRef = 5 AND d.ReferenceID = pr.ProjectID;
GO

-- ai.bank_accounts: the company's own bank accounts (RPA3.BankAccount) with bank, branch and the tafsili code used in the ledger.
CREATE OR ALTER VIEW ai.bank_accounts AS
SELECT b.BankAccountID AS bank_account_id,
       LTRIM(RTRIM(b.Number)) AS account_number,
       bk.Name AS bank_name,
       bb.Name AS branch_name,
       bb.Code AS branch_code,
       bt.Name AS account_type,
       b.InternationalNumber AS sheba,
       CASE b.State WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS state,
       d.Code AS dl_code,
       RTRIM(d.Title) AS dl_title,
       b.Description AS description
FROM RPA3.BankAccount b
JOIN RPA3.BankBranch bb ON bb.BankBranchID = b.BankBranchRef
JOIN RPA3.Bank bk ON bk.BankID = bb.BankRef
JOIN RPA3.BankAccountType bt ON bt.BankAccountTypeID = b.BankAccountTypeRef
LEFT JOIN FIN3.DL d ON d.DLTypeRef = 10 AND d.ReferenceID = b.BankAccountID;
GO

-- ai.users: Rahkaran application users (no credentials). Used to show who created / modified documents.
CREATE OR ALTER VIEW ai.users AS
SELECT u.UserID AS user_id,
       u.Name AS user_name,
       CASE u.Status WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS status,
       ISNULL(u.IsAdministrator, 0) AS is_administrator,
       u.PartyRef AS party_id,
       CAST(u.CreationDate AS date) AS created_date,
       CAST(u.LastModificationDate AS date) AS last_modified_date
FROM SYS3.[User] u;
GO
