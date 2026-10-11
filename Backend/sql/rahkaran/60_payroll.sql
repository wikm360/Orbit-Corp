-- Payroll views (HCM3 compensation). Amounts in Rials, payroll months are Jalali YYYYMM numbers.

-- ai.payroll_monthly: ONE row per employee per payroll month (HCM3.PayCalc) with the main compensation factors pivoted into columns (Rials; days where noted).
-- issue_year_month is the Jalali payroll month (YYYYMM, e.g. 140505 = Mordad 1405). Amounts sum all items of that payroll calculation
-- (items with an earlier apply month are arrears and are included; has_arrears_items flags them). The department / post / cost center are those
-- effective in that month. Identity: net_pay = total_benefits - total_deductions.
-- employer_total_cost = total_benefits + employer_social_insurance + unemployment_insurance + employer_supplementary_insurance (+ parents supplementary employer).
CREATE OR ALTER VIEW ai.payroll_monthly AS
SELECT p.PayCalcID AS pay_calc_id,
       p.EmployeeRef AS employee_id,
       e.Code AS employee_code,
       e.FullName AS employee_name,
       p.IssueYearMonth AS issue_year_month,
       p.IssueYearMonth / 100 AS jalali_year,
       p.IssueYearMonth % 100 AS jalali_month,
       CASE p.IssueYearMonth % 100 WHEN 1 THEN N'فروردین' WHEN 2 THEN N'اردیبهشت' WHEN 3 THEN N'خرداد' WHEN 4 THEN N'تیر' WHEN 5 THEN N'مرداد'
            WHEN 6 THEN N'شهریور' WHEN 7 THEN N'مهر' WHEN 8 THEN N'آبان' WHEN 9 THEN N'آذر' WHEN 10 THEN N'دی' WHEN 11 THEN N'بهمن' ELSE N'اسفند' END AS jalali_month_name,
       CASE WHEN p.IssueYearMonth % 100 >= 7 THEN p.IssueYearMonth / 100 ELSE p.IssueYearMonth / 100 - 1 END AS fiscal_year,
       st.department_name,
       st.post_title,
       st.job_title,
       st.employment_type,
       cc.DLCode AS cost_center_dl_code,
       RTRIM(ccd.Title) AS cost_center,
       SUM(CASE WHEN i.CompensationFactorRef = 37 THEN i.Value ELSE 0 END) AS effective_work_days,
       SUM(CASE WHEN i.CompensationFactorRef = 60 THEN i.Value ELSE 0 END) AS monthly_wage,
       SUM(CASE WHEN i.CompensationFactorRef = 59 THEN i.Value ELSE 0 END) AS daily_wage,
       SUM(CASE WHEN i.CompensationFactorRef = 38 THEN i.Value ELSE 0 END) AS base_pay,
       SUM(CASE WHEN i.CompensationFactorRef = 39 THEN i.Value ELSE 0 END) AS housing_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 40 THEN i.Value ELSE 0 END) AS child_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 139 THEN i.Value ELSE 0 END) AS seniority_pay,
       SUM(CASE WHEN i.CompensationFactorRef = 140 THEN i.Value ELSE 0 END) AS worker_bon,
       SUM(CASE WHEN i.CompensationFactorRef = 141 THEN i.Value ELSE 0 END) AS hard_work_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 162 THEN i.Value ELSE 0 END) AS transport_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 163 THEN i.Value ELSE 0 END) AS supervision_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 143 THEN i.Value ELSE 0 END) AS adjustment_difference,
       SUM(CASE WHEN i.CompensationFactorRef = 612 THEN i.Value ELSE 0 END) AS marital_allowance,
       SUM(CASE WHEN i.CompensationFactorRef = 164 THEN i.Value ELSE 0 END) AS mission_input,
       SUM(CASE WHEN i.CompensationFactorRef = 165 THEN i.Value ELSE 0 END) AS overtime_input,
       SUM(CASE WHEN i.CompensationFactorRef = 181 THEN i.Value ELSE 0 END) AS karaneh,
       SUM(CASE WHEN i.CompensationFactorRef = 243 THEN i.Value ELSE 0 END) AS bonus_reward,
       SUM(CASE WHEN i.CompensationFactorRef = 247 THEN i.Value ELSE 0 END) AS arrears_benefit,
       SUM(CASE WHEN i.CompensationFactorRef = 606 THEN i.Value ELSE 0 END) AS holiday_work_pay,
       SUM(CASE WHEN i.CompensationFactorRef = 607 THEN i.Value ELSE 0 END) AS shift_work_pay,
       SUM(CASE WHEN i.CompensationFactorRef = 604 THEN i.Value ELSE 0 END) AS suggestion_system_reward,
       SUM(CASE WHEN i.CompensationFactorRef = 61 THEN i.Value ELSE 0 END) AS total_benefits,
       SUM(CASE WHEN i.CompensationFactorRef = 62 THEN i.Value ELSE 0 END) AS total_deductions,
       SUM(CASE WHEN i.CompensationFactorRef = 63 THEN i.Value ELSE 0 END) AS net_pay,
       SUM(CASE WHEN i.CompensationFactorRef = 55 THEN i.Value ELSE 0 END) AS payable,
       SUM(CASE WHEN i.CompensationFactorRef = 43 THEN i.Value ELSE 0 END) AS insurable_earnings,
       SUM(CASE WHEN i.CompensationFactorRef = 44 THEN i.Value ELSE 0 END) AS insurance_ceiling,
       SUM(CASE WHEN i.CompensationFactorRef = 45 THEN i.Value ELSE 0 END) AS insurance_base,
       SUM(CASE WHEN i.CompensationFactorRef = 46 THEN i.Value ELSE 0 END) AS employee_social_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 64 THEN i.Value ELSE 0 END) AS employer_social_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 65 THEN i.Value ELSE 0 END) AS unemployment_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 72 THEN i.Value ELSE 0 END) AS employee_supplementary_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 73 THEN i.Value ELSE 0 END) AS employer_supplementary_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 609 THEN i.Value ELSE 0 END) AS parents_supplementary_insurance_employee,
       SUM(CASE WHEN i.CompensationFactorRef = 610 THEN i.Value ELSE 0 END) AS parents_supplementary_insurance_employer,
       SUM(CASE WHEN i.CompensationFactorRef = 167 THEN i.Value ELSE 0 END) AS employee_life_insurance,
       SUM(CASE WHEN i.CompensationFactorRef = 47 THEN i.Value ELSE 0 END) AS taxable_income,
       SUM(CASE WHEN i.CompensationFactorRef = 50 THEN i.Value ELSE 0 END) AS income_tax,
       SUM(CASE WHEN i.CompensationFactorRef = 52 THEN i.Value ELSE 0 END) AS loan_installments,
       SUM(CASE WHEN i.CompensationFactorRef = 597 THEN i.Value ELSE 0 END) AS company_advance_deduction,
       SUM(CASE WHEN i.CompensationFactorRef = 605 THEN i.Value ELSE 0 END) AS jahan_steel_shares_deduction,
       SUM(CASE WHEN i.CompensationFactorRef = 631 THEN i.Value ELSE 0 END) AS armangohar_shares_deduction,
       SUM(CASE WHEN i.CompensationFactorRef = 598 THEN i.Value ELSE 0 END) AS car_insurance_deduction,
       SUM(CASE WHEN i.CompensationFactorRef = 322 THEN i.Value ELSE 0 END) AS judicial_deductions,
       SUM(CASE WHEN i.CompensationFactorRef = 168 THEN i.Value ELSE 0 END) AS company_fund_membership,
       SUM(CASE WHEN i.CompensationFactorRef = 69 THEN i.Value ELSE 0 END) AS previous_month_debt,
       SUM(CASE WHEN i.CompensationFactorRef = 583 THEN i.Value ELSE 0 END) AS absent_days,
       SUM(CASE WHEN i.CompensationFactorRef = 584 THEN i.Value ELSE 0 END) AS sick_leave_days,
       SUM(CASE WHEN i.CompensationFactorRef IN (61,64,65,73,610) THEN i.Value ELSE 0 END) AS employer_total_cost,
       MAX(CASE WHEN i.ApplyYearMonth <> p.IssueYearMonth THEN 1 ELSE 0 END) AS has_arrears_items
FROM HCM3.PayCalc p
JOIN HCM3.Employee e ON e.EmployeeID = p.EmployeeRef
JOIN HCM3.PayCalcItem i ON i.PayCalcRef = p.PayCalcID
OUTER APPLY (SELECT TOP 1 CASE WHEN dp.Title LIKE N'%([ ]%[0-9])' THEN LTRIM(RTRIM(LEFT(dp.Title, CHARINDEX('(', dp.Title) - 1))) ELSE dp.Title END AS department_name,
                    po.Title AS post_title, jb.Title AS job_title, et.RawTitle AS employment_type
             FROM HCM3.EmployeeStatute s
             LEFT JOIN HCM3.Department dp ON dp.DepartmentID = s.DepartmentRef
             LEFT JOIN HCM3.Post po ON po.PostID = s.PostRef
             LEFT JOIN HCM3.Job jb ON jb.JobID = s.JobRef
             LEFT JOIN HCM3.EmploymentType et ON et.EmploymentTypeID = s.EmploymentTypeRef
             WHERE s.EmployeeRef = p.EmployeeRef AND s.Status = 10 AND s.ApplyYearMonth <= p.IssueYearMonth
             ORDER BY s.ApplyDate DESC, s.EmployeeStatuteID DESC) st
OUTER APPLY (SELECT TOP 1 r.DLCode FROM HCM3.EmployeeRelatedDL r
             WHERE r.EmployeeRef = p.EmployeeRef AND r.CompensationRelatedDLTypeRef = 1 AND r.EffectiveYearMonth <= p.IssueYearMonth
             ORDER BY r.EffectiveYearMonth DESC, r.EmployeeRelatedDLID DESC) cc
LEFT JOIN FIN3.DL ccd ON ccd.Code = cc.DLCode
GROUP BY p.PayCalcID, p.EmployeeRef, e.Code, e.FullName, p.IssueYearMonth, st.department_name, st.post_title, st.job_title, st.employment_type, cc.DLCode, ccd.Title;
GO

-- ai.payroll_factor_values: LONG form of payroll: one row per employee, payroll month, apply month and compensation factor (HCM3.PayCalcItem, ~3.4M rows).
-- Use it for any factor that is not a column of ai.payroll_monthly. ALWAYS filter on issue_year_month (or a range) - the table is large.
CREATE OR ALTER VIEW ai.payroll_factor_values AS
SELECT i.PayCalcItemID AS item_id,
       i.PayCalcRef AS pay_calc_id,
       i.EmployeeRef AS employee_id,
       e.FullName AS employee_name,
       i.IssueYearMonth AS issue_year_month,
       i.ApplyYearMonth AS apply_year_month,
       f.CompensationFactorID AS factor_id,
       f.Name AS factor_key,
       f.Title AS factor_title,
       cat.Value AS factor_category,
       i.Value AS value
FROM HCM3.PayCalcItem i
JOIN HCM3.Employee e ON e.EmployeeID = i.EmployeeRef
JOIN HCM3.CompensationFactor f ON f.CompensationFactorID = i.CompensationFactorRef
LEFT JOIN SYS3.Lookup cat ON cat.Type = 'CompensationFactorCategory' AND cat.Code = f.CategoryCode;
GO

-- ai.compensation_factors: dictionary of the 285 payroll factors with category, unit and whether it is ever non-zero (is_used).
CREATE OR ALTER VIEW ai.compensation_factors AS
SELECT f.CompensationFactorID AS factor_id, f.Name AS factor_key, f.Title AS factor_title,
       cat.Value AS factor_category, ct.Title AS calc_type,
       CASE f.AssignTypeCode WHEN 1 THEN N'محاسباتی' ELSE N'ورودی' END AS assign_type,
       mu.Value AS measurement_unit,
       CASE WHEN EXISTS (SELECT 1 FROM HCM3.PayCalcItem i WHERE i.CompensationFactorRef = f.CompensationFactorID AND i.Value <> 0)
              OR EXISTS (SELECT 1 FROM HCM3.PeriodicCalcItem i WHERE i.CompensationFactorRef = f.CompensationFactorID AND i.Value <> 0)
            THEN 1 ELSE 0 END AS is_used
FROM HCM3.CompensationFactor f
JOIN HCM3.CompensationCalcType ct ON ct.CompensationCalcTypeID = f.CompensationCalcTypeRef
LEFT JOIN SYS3.Lookup cat ON cat.Type = 'CompensationFactorCategory' AND cat.Code = f.CategoryCode
LEFT JOIN SYS3.Lookup mu ON mu.Type = 'CompensationMeasurementUnit' AND mu.Code = f.MeasurementUnitCode;
GO

-- ai.payroll_month_summary: company-wide totals per payroll month.
CREATE OR ALTER VIEW ai.payroll_month_summary AS
SELECT issue_year_month, MAX(jalali_year) AS jalali_year, MAX(jalali_month) AS jalali_month, MAX(jalali_month_name) AS jalali_month_name, MAX(fiscal_year) AS fiscal_year,
       COUNT(*) AS employee_count,
       SUM(total_benefits) AS total_benefits, SUM(total_deductions) AS total_deductions, SUM(net_pay) AS net_pay,
       SUM(employee_social_insurance) AS employee_social_insurance, SUM(employer_social_insurance) AS employer_social_insurance,
       SUM(unemployment_insurance) AS unemployment_insurance,
       SUM(employee_supplementary_insurance) AS employee_supplementary_insurance, SUM(employer_supplementary_insurance) AS employer_supplementary_insurance,
       SUM(income_tax) AS income_tax, SUM(loan_installments) AS loan_installments,
       SUM(employer_total_cost) AS employer_total_cost,
       SUM(effective_work_days) AS effective_work_days
FROM ai.payroll_monthly
GROUP BY issue_year_month;
GO

-- ai.payroll_by_cost_center_month / ai.payroll_by_department_month: payroll cost per month by contract/equipment cost center and by department.
CREATE OR ALTER VIEW ai.payroll_by_cost_center_month AS
SELECT issue_year_month, MAX(jalali_month_name) AS jalali_month_name, MAX(fiscal_year) AS fiscal_year, cost_center_dl_code, MAX(cost_center) AS cost_center,
       COUNT(*) AS employee_count, SUM(total_benefits) AS total_benefits, SUM(net_pay) AS net_pay,
       SUM(employer_total_cost) AS employer_total_cost, SUM(income_tax) AS income_tax, SUM(employee_social_insurance + employer_social_insurance + unemployment_insurance) AS social_insurance_total
FROM ai.payroll_monthly
GROUP BY issue_year_month, cost_center_dl_code;
GO

CREATE OR ALTER VIEW ai.payroll_by_department_month AS
SELECT issue_year_month, MAX(jalali_month_name) AS jalali_month_name, MAX(fiscal_year) AS fiscal_year, ISNULL(department_name, N'(بدون حکم)') AS department_name,
       COUNT(*) AS employee_count, SUM(total_benefits) AS total_benefits, SUM(net_pay) AS net_pay,
       SUM(employer_total_cost) AS employer_total_cost, SUM(income_tax) AS income_tax
FROM ai.payroll_monthly
GROUP BY issue_year_month, department_name;
GO

-- ai.payroll_year_summary: payroll per Jalali calendar year and per fiscal year (Mehr..Shahrivar) - quick totals.
CREATE OR ALTER VIEW ai.payroll_year_summary AS
SELECT fiscal_year, COUNT(DISTINCT issue_year_month) AS months, COUNT(DISTINCT employee_id) AS distinct_employees,
       SUM(total_benefits) AS total_benefits, SUM(total_deductions) AS total_deductions, SUM(net_pay) AS net_pay,
       SUM(employer_total_cost) AS employer_total_cost, SUM(income_tax) AS income_tax,
       SUM(employee_social_insurance) AS employee_social_insurance, SUM(employer_social_insurance) AS employer_social_insurance
FROM ai.payroll_monthly
GROUP BY fiscal_year;
GO

-- ai.periodic_calc_values: LONG form of the non-monthly calculations (عیدی، بازخرید مرخصی/سنوات، تسویه حساب، بازنشستگی، ذخایر): one row per employee, calculation
-- and factor. sub_type = 'ذخیره' (provision accrued monthly) or 'پرداخت' (actual payment).
CREATE OR ALTER VIEW ai.periodic_calc_values AS
SELECT i.PeriodicCalcItemID AS item_id, c.PeriodicCalcID AS periodic_calc_id, c.EmployeeRef AS employee_id, e.FullName AS employee_name,
       ct.Title AS calc_type, st.Value AS sub_type, c.IssueYearMonth AS issue_year_month,
       f.CompensationFactorID AS factor_id, f.Name AS factor_key, f.Title AS factor_title, i.Value AS value
FROM HCM3.PeriodicCalc c
JOIN HCM3.PeriodicCalcItem i ON i.PeriodicCalcRef = c.PeriodicCalcID
JOIN HCM3.Employee e ON e.EmployeeID = c.EmployeeRef
JOIN HCM3.CompensationCalcType ct ON ct.CompensationCalcTypeID = c.CompensationCalcTypeRef
JOIN HCM3.CompensationFactor f ON f.CompensationFactorID = i.CompensationFactorRef
LEFT JOIN SYS3.Lookup st ON st.Type = 'CompensationCalcSubType' AND st.Code = c.SubTypeCode;
GO

-- ai.periodic_payments: WIDE summary of the periodic calculations (one row per employee, calc type, sub type and month): Nowruz bonus (عیدی) and
-- severance / unused-leave buy-back (سنوات). net_reward = خالص عیدی; severance_result = نتیجه سنوات; *_provision = monthly accrued provisions.
CREATE OR ALTER VIEW ai.periodic_payments AS
SELECT c.PeriodicCalcID AS periodic_calc_id, c.EmployeeRef AS employee_id, e.FullName AS employee_name,
       ct.Title AS calc_type, st.Value AS sub_type, c.IssueYearMonth AS issue_year_month,
       SUM(CASE WHEN i.CompensationFactorRef = 100 THEN i.Value ELSE 0 END) AS reward_benefit,
       SUM(CASE WHEN i.CompensationFactorRef = 104 THEN i.Value ELSE 0 END) AS reward_tax,
       SUM(CASE WHEN i.CompensationFactorRef = 105 THEN i.Value ELSE 0 END) AS reward_payable,
       SUM(CASE WHEN i.CompensationFactorRef = 107 THEN i.Value ELSE 0 END) AS net_reward,
       SUM(CASE WHEN i.CompensationFactorRef = 110 THEN i.Value ELSE 0 END) AS reward_provision,
       SUM(CASE WHEN i.CompensationFactorRef = 15 THEN i.Value ELSE 0 END) AS severance_result,
       SUM(CASE WHEN i.CompensationFactorRef = 6 THEN i.Value ELSE 0 END) AS severance_provision_total,
       SUM(CASE WHEN i.CompensationFactorRef = 8 THEN i.Value ELSE 0 END) AS severance_provision_current,
       SUM(CASE WHEN i.CompensationFactorRef = 2 THEN i.Value ELSE 0 END) AS severance_days
FROM HCM3.PeriodicCalc c
JOIN HCM3.PeriodicCalcItem i ON i.PeriodicCalcRef = c.PeriodicCalcID
JOIN HCM3.Employee e ON e.EmployeeID = c.EmployeeRef
JOIN HCM3.CompensationCalcType ct ON ct.CompensationCalcTypeID = c.CompensationCalcTypeRef
LEFT JOIN SYS3.Lookup st ON st.Type = 'CompensationCalcSubType' AND st.Code = c.SubTypeCode
GROUP BY c.PeriodicCalcID, c.EmployeeRef, e.FullName, ct.Title, st.Value, c.IssueYearMonth;
GO

-- ai.payroll_accounting_vouchers: the accounting documents generated by payroll (salary, severance provision, Nowruz-bonus provision/payment) for each month.
CREATE OR ALTER VIEW ai.payroll_accounting_vouchers AS
SELECT hv.VoucherID AS hcm_voucher_id, spec.Title AS voucher_specification, hv.IssueYearMonth AS issue_year_month,
       hv.VoucherRef AS voucher_id, v.voucher_number, v.voucher_date, v.jalali_date, v.fiscal_year, v.voucher_state,
       v.total_debit, v.total_credit, v.line_count,
       (SELECT COUNT(*) FROM HCM3.VoucherEmployee ve WHERE ve.VoucherRef = hv.VoucherID) AS employee_count
FROM HCM3.Voucher hv
JOIN HCM3.VoucherSpecification spec ON spec.VoucherSpecificationID = hv.VoucherSpecificationRef
LEFT JOIN ai.vouchers v ON v.voucher_id = hv.VoucherRef;
GO

-- ai.attendance_monthly: monthly attendance summary per employee (only the monthly summary exists - no raw in/out punches; data ends at 1405/02).
-- Columns: normal_work_days (کارکرد عادی), absent_days (غیبت), sick_leave_days (مرخصی استعلاجی); other factors are in HCM3.AttendanceFactor.
CREATE OR ALTER VIEW ai.attendance_monthly AS
SELECT a.AttendanceCalcID AS attendance_calc_id, a.EmployeeRef AS employee_id, e.FullName AS employee_name, a.IssueYearMonth AS issue_year_month,
       CAST(a.FromDate AS date) AS from_date, CAST(a.ToDate AS date) AS to_date,
       SUM(CASE WHEN m.AttendanceFactorRef = 2 THEN m.Value ELSE 0 END) AS normal_work_days,
       SUM(CASE WHEN m.AttendanceFactorRef = 4 THEN m.Value ELSE 0 END) AS absent_days,
       SUM(CASE WHEN m.AttendanceFactorRef = 5 THEN m.Value ELSE 0 END) AS sick_leave_days,
       SUM(CASE WHEN m.AttendanceFactorRef = 6 THEN m.Value ELSE 0 END) AS suggestion_reward_points
FROM HCM3.AttendanceCalc a
JOIN HCM3.Employee e ON e.EmployeeID = a.EmployeeRef
LEFT JOIN HCM3.AttendanceCalcMonthlyItem m ON m.AttendanceCalcRef = a.AttendanceCalcID
GROUP BY a.AttendanceCalcID, a.EmployeeRef, e.FullName, a.IssueYearMonth, a.FromDate, a.ToDate;
GO
