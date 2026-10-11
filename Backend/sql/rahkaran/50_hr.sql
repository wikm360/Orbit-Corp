-- Human-resources views (HCM3). Contain personal data (national id, bank account, family) and salary terms.

-- ai.departments / ai.posts / ai.jobs: organisation master data. Department titles often end with a code like "(   79)", removed here.
CREATE OR ALTER VIEW ai.departments AS
SELECT d.DepartmentID AS department_id,
       d.Code AS department_code,
       LTRIM(RTRIM(CASE WHEN d.Title LIKE N'%([ ]%[0-9])' THEN LEFT(d.Title, CHARINDEX('(', d.Title) - 1) ELSE d.Title END)) AS department_name,
       d.Title AS original_title,
       rd.Name AS region_name,
       d.Status AS status_code,
       CASE d.Status WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS status
FROM HCM3.Department d
LEFT JOIN GNR3.RegionalDivision rd ON rd.RegionalDivisionID = d.RegionalDivisionRef;
GO

CREATE OR ALTER VIEW ai.posts AS
SELECT p.PostID AS post_id, p.Code AS post_code, p.Title AS post_title, p.Capacity AS capacity,
       p.ManagementLevelCode AS management_level_code,
       CASE p.Status WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS status
FROM HCM3.Post p;
GO

CREATE OR ALTER VIEW ai.jobs AS
SELECT j.JobID AS job_id, j.Code AS job_code, j.Title AS job_title,
       jc.Value AS job_class, jg.Value AS job_group,
       LTRIM(RTRIM(j.InsuranceCode)) AS insurance_job_code,
       CASE j.Status WHEN 1 THEN N'فعال' ELSE N'غیرفعال' END AS status
FROM HCM3.Job j
LEFT JOIN SYS3.Lookup jc ON jc.Type = 'JobClass' AND jc.Code = j.ClassCode
LEFT JOIN SYS3.Lookup jg ON jg.Type = 'JobGroup' AND jg.Code = j.GroupCode;
GO

-- ai.employee_statutes: every payroll "حکم" (statute document) of every employee: hiring, salary changes, insurance-branch changes, deactivation ...
-- Status 10 = approved for payment (the effective ones). The effective statute at a date is the latest status-10 statute with apply_date <= date.
CREATE OR ALTER VIEW ai.employee_statutes AS
SELECT s.EmployeeStatuteID AS statute_id,
       s.EmployeeRef AS employee_id,
       e.Code AS employee_code,
       e.FullName AS employee_name,
       st.Title AS statute_type,
       s.Number AS statute_number,
       s.Status AS status_code,
       ss.Value AS status,
       et.RawTitle AS employment_type,
       CASE WHEN dp.Title LIKE N'%([ ]%[0-9])' THEN LTRIM(RTRIM(LEFT(dp.Title, CHARINDEX('(', dp.Title) - 1))) ELSE dp.Title END AS department_name,
       po.Title AS post_title,
       jb.Title AS job_title,
       CAST(s.EmploymentDate AS date) AS employment_date,
       CAST(s.IssueDate AS date) AS issue_date,
       CAST(s.ApplyDate AS date) AS apply_date,
       ca.jalali_date AS apply_date_jalali,
       CAST(s.ExpiryDate AS date) AS expiry_date,
       CAST(s.ConfirmDate AS date) AS confirm_date,
       s.ApplyYearMonth AS apply_year_month,
       s.IssueYearMonth AS issue_year_month,
       ai.Value AS employee_status_after_issue,
       CAST(s.RetirementDate AS date) AS retirement_date,
       s.Description AS description
FROM HCM3.EmployeeStatute s
JOIN HCM3.Employee e ON e.EmployeeID = s.EmployeeRef
LEFT JOIN HCM3.StatuteType st ON st.StatuteTypeID = s.StatuteTypeRef
LEFT JOIN HCM3.EmploymentType et ON et.EmploymentTypeID = s.EmploymentTypeRef
LEFT JOIN HCM3.Department dp ON dp.DepartmentID = s.DepartmentRef
LEFT JOIN HCM3.Post po ON po.PostID = s.PostRef
LEFT JOIN HCM3.Job jb ON jb.JobID = s.JobRef
LEFT JOIN SYS3.Lookup ss ON ss.Type = 'EmployeeStatuteStatus' AND ss.Code = s.Status
LEFT JOIN SYS3.Lookup ai ON ai.Type = 'EmployeeStatuteAfterIssueStatus' AND ai.Code = s.AfterIssueStatusCode
LEFT JOIN ai.calendar ca ON ca.gregorian_date = CAST(s.ApplyDate AS date);
GO

-- ai.employee_current_statutes: ONE row per employee = the latest approved (status 10) statute (current department/post/job/employment type).
CREATE OR ALTER VIEW ai.employee_current_statutes AS
SELECT x.employee_id, x.statute_id, x.statute_type, x.employment_type, x.department_name, x.post_title, x.job_title,
       x.apply_date, x.apply_date_jalali, x.employment_date, x.employee_status_after_issue
FROM (
    SELECT s.employee_id, s.statute_id, s.statute_type, s.employment_type, s.department_name, s.post_title, s.job_title,
           s.apply_date, s.apply_date_jalali, s.employment_date, s.employee_status_after_issue,
           ROW_NUMBER() OVER (PARTITION BY s.employee_id ORDER BY s.apply_date DESC, s.statute_id DESC) AS rn
    FROM ai.employee_statutes s
    WHERE s.status_code = 10
) x
WHERE x.rn = 1;
GO

-- ai.employee_statute_factors: the monetary/point terms of each statute (base pay, housing, children allowance ...). value is in Rials per month
-- for the monetary factors (factor_kind = 'مبلغ'), or a score/count for the others.
CREATE OR ALTER VIEW ai.employee_statute_factors AS
SELECT f.EmployeeStatuteRef AS statute_id,
       s.EmployeeRef AS employee_id,
       sf.StatuteFactorID AS factor_id,
       sf.Name AS factor_key,
       RTRIM(sf.Title) AS factor_title,
       CASE sf.TypeCode WHEN 1 THEN N'مبلغ' ELSE N'امتیاز/تعداد/شرط' END AS factor_kind,
       f.Value AS value,
       f.CalcValue AS calculated_value,
       f.EditedValue AS edited_value,
       CAST(s.ApplyDate AS date) AS apply_date,
       s.Status AS statute_status_code
FROM HCM3.EmployeeStatuteFactor f
JOIN HCM3.EmployeeStatute s ON s.EmployeeStatuteID = f.EmployeeStatuteRef
JOIN HCM3.StatuteFactor sf ON sf.StatuteFactorID = f.StatuteFactorRef;
GO

-- ai.employees: one row per employee (HCM3.Employee) with personal data and the CURRENT statute, cost-center/contract assignment and insurance.
-- current_cost_center is the contract/equipment cost center the employee's payroll cost is charged to (latest EmployeeRelatedDL of type 1).
CREATE OR ALTER VIEW ai.employees AS
SELECT e.EmployeeID AS employee_id,
       e.Code AS employee_code,
       e.PartyRef AS party_id,
       e.FullName AS full_name,
       e.FirstName AS first_name,
       e.LastName AS last_name,
       p.NationalID AS national_id,
       p.IDNumber AS id_number,
       p.FatherName AS father_name,
       CAST(p.BirthDate AS date) AS birth_date,
       bj.jalali_date AS birth_date_jalali,
       DATEDIFF(YEAR, p.BirthDate, GETDATE()) AS approx_age,
       CASE p.Gender WHEN 1 THEN N'مرد' WHEN 2 THEN N'زن' END AS gender,
       ms.Value AS marital_status,
       ed.Value AS education_degree,
       p.Mobile AS mobile,
       p.Tel AS phone,
       p.Email AS email,
       e.Status AS status_code,
       es.Value AS status,
       CASE WHEN e.Status = 2 THEN 1 ELSE 0 END AS is_active,
       cs.employment_type,
       cs.department_name,
       cs.post_title,
       cs.job_title,
       cs.statute_type AS last_statute_type,
       cs.apply_date AS last_statute_apply_date,
       fs.first_employment_date AS employment_date,
       fj.jalali_date AS employment_date_jalali,
       DATEDIFF(MONTH, fs.first_employment_date, GETDATE()) / 12.0 AS approx_service_years,
       ch.children_count,
       cc.DLCode AS current_cost_center_dl_code,
       RTRIM(ccd.Title) AS current_cost_center,
       cc.EffectiveYearMonth AS cost_center_effective_ym,
       pj.DLCode AS current_project_dl_code,
       RTRIM(pjd.Title) AS current_project,
       ins.Code AS insurance_number,
       ins.org_branch_code AS insurance_branch_code,
       ins.org_title AS insurance_organization,
       CASE WHEN e.MilitaryServiceStatusCode IS NULL THEN NULL ELSE ml.Value END AS military_service_status,
       CAST(e.CreationDate AS date) AS record_created_date
FROM HCM3.Employee e
JOIN GNR3.Party p ON p.PartyID = e.PartyRef
LEFT JOIN ai.employee_current_statutes cs ON cs.employee_id = e.EmployeeID
LEFT JOIN SYS3.Lookup es ON es.Type = 'EmployeeStatus' AND es.Code = e.Status
LEFT JOIN SYS3.Lookup ms ON ms.Type = 'PersonMaritalStatus' AND ms.Code = p.MaritalStatus
LEFT JOIN SYS3.Lookup ed ON ed.Type = 'PersonEducationDegree' AND ed.Code = p.EducationDegree
LEFT JOIN SYS3.Lookup ml ON ml.Type = 'MilitaryServiceStatus' AND ml.Code = e.MilitaryServiceStatusCode
LEFT JOIN ai.calendar bj ON bj.gregorian_date = CAST(p.BirthDate AS date)
OUTER APPLY (SELECT MIN(CAST(s.EmploymentDate AS date)) AS first_employment_date FROM HCM3.EmployeeStatute s WHERE s.EmployeeRef = e.EmployeeID AND s.EmploymentDate IS NOT NULL) fs
LEFT JOIN ai.calendar fj ON fj.gregorian_date = fs.first_employment_date
OUTER APPLY (SELECT COUNT(*) AS children_count FROM HCM3.EmployeeRelative r WHERE r.EmployeeRef = e.EmployeeID AND r.RelationCode IN (7,8,9) AND r.ExpiryDate IS NULL) ch
OUTER APPLY (SELECT TOP 1 r.DLCode, r.EffectiveYearMonth FROM HCM3.EmployeeRelatedDL r WHERE r.EmployeeRef = e.EmployeeID AND r.CompensationRelatedDLTypeRef = 1 ORDER BY r.EffectiveYearMonth DESC, r.EmployeeRelatedDLID DESC) cc
LEFT JOIN FIN3.DL ccd ON ccd.Code = cc.DLCode
OUTER APPLY (SELECT TOP 1 r.DLCode FROM HCM3.EmployeeRelatedDL r WHERE r.EmployeeRef = e.EmployeeID AND r.CompensationRelatedDLTypeRef = 2 ORDER BY r.EffectiveYearMonth DESC, r.EmployeeRelatedDLID DESC) pj
LEFT JOIN FIN3.DL pjd ON pjd.Code = pj.DLCode
OUTER APPLY (SELECT TOP 1 o.Code, ob.Code AS org_branch_code, og.Title AS org_title
             FROM HCM3.EmployeeRelatedOrganization o
             JOIN HCM3.OrganizationBranch ob ON ob.OrganizationBranchID = o.OrganizationBranchRef
             JOIN HCM3.Organization og ON og.OrganizationID = ob.OrganizationRef
             WHERE o.EmployeeRef = e.EmployeeID AND o.IsInsurance = 1 AND o.ExpiryYearMonth IS NULL
             ORDER BY o.EffectiveYearMonth DESC, o.EmployeeRelatedOrganizationID DESC) ins;
GO

-- ai.employee_current_pay_terms: ONE row per employee: the monetary terms of the CURRENT statute pivoted into columns (Rials per month).
CREATE OR ALTER VIEW ai.employee_current_pay_terms AS
SELECT c.employee_id, e.employee_code, e.full_name, e.status AS employee_status, e.department_name, c.statute_id, c.apply_date,
       SUM(CASE WHEN f.factor_key = 'Basepay' THEN f.value ELSE 0 END) AS base_pay,
       SUM(CASE WHEN f.factor_key = 'HousePay' THEN f.value ELSE 0 END) AS housing_allowance,
       SUM(CASE WHEN f.factor_key = 'Childpay' THEN f.value ELSE 0 END) AS child_allowance,
       SUM(CASE WHEN f.factor_key = 'YearExpPay' THEN f.value ELSE 0 END) AS seniority_pay,
       SUM(CASE WHEN f.factor_key = 'Bonpay' THEN f.value ELSE 0 END) AS worker_bon,
       SUM(CASE WHEN f.factor_key = 'HardWorkPay' THEN f.value ELSE 0 END) AS hard_work_allowance,
       SUM(CASE WHEN f.factor_key = 'ayabzahab' THEN f.value ELSE 0 END) AS transport_allowance,
       SUM(CASE WHEN f.factor_key = 'ManagePAy' THEN f.value ELSE 0 END) AS supervision_allowance,
       SUM(CASE WHEN f.factor_key = 'UF4' THEN f.value ELSE 0 END) AS marital_allowance,
       SUM(CASE WHEN f.factor_key = 'WorkRolePay' THEN f.value ELSE 0 END) AS adjustment_difference,
       SUM(CASE WHEN f.factor_key = 'mozdeartabe' THEN f.value ELSE 0 END) AS rank_pay,
       SUM(CASE WHEN f.factor_key = 'JabzPay' THEN f.value ELSE 0 END) AS absorption_allowance,
       SUM(CASE WHEN f.factor_kind = N'مبلغ' AND f.factor_key NOT IN ('GrubPay') THEN f.value ELSE 0 END) AS total_monthly_terms
FROM ai.employee_current_statutes c
JOIN ai.employees e ON e.employee_id = c.employee_id
JOIN ai.employee_statute_factors f ON f.statute_id = c.statute_id
GROUP BY c.employee_id, e.employee_code, e.full_name, e.status, e.department_name, c.statute_id, c.apply_date;
GO

-- ai.employee_cost_center_history: which contract / equipment cost center and project each employee's payroll cost was charged to, over time.
CREATE OR ALTER VIEW ai.employee_cost_center_history AS
SELECT r.EmployeeRef AS employee_id, e.FullName AS employee_name,
       CASE r.CompensationRelatedDLTypeRef WHEN 1 THEN N'مرکز هزینه' WHEN 2 THEN N'پروژه' END AS assignment_kind,
       r.DLCode AS dl_code, RTRIM(d.Title) AS dl_title,
       r.EffectiveYearMonth AS effective_year_month, CAST(r.EffectiveDate AS date) AS effective_date
FROM HCM3.EmployeeRelatedDL r
JOIN HCM3.Employee e ON e.EmployeeID = r.EmployeeRef
LEFT JOIN FIN3.DL d ON d.Code = r.DLCode;
GO

-- ai.employee_relatives: family members registered for employees (children, spouse, parents) - used for allowances and supplementary insurance.
CREATE OR ALTER VIEW ai.employee_relatives AS
SELECT r.EmployeeRelativeID AS relative_id, r.EmployeeRef AS employee_id, e.FullName AS employee_name,
       r.FirstName AS first_name, r.LastName AS last_name, rel.Value AS relation,
       r.NationalID AS national_id, CAST(r.BirthDate AS date) AS birth_date, mst.Value AS marital_status,
       r.Job AS job, CAST(r.ExpiryDate AS date) AS expiry_date,
       CASE WHEN r.ExpiryDate IS NULL THEN 1 ELSE 0 END AS is_active,
       r.IncludeInSonshipPay AS included_in_child_allowance
FROM HCM3.EmployeeRelative r
JOIN HCM3.Employee e ON e.EmployeeID = r.EmployeeRef
LEFT JOIN SYS3.Lookup rel ON rel.Type = 'EmployeeRelation' AND rel.Code = r.RelationCode
LEFT JOIN SYS3.Lookup mst ON mst.Type = 'MaritalStatus' AND mst.Code = r.MaritalStatusCode;
GO

-- ai.employee_education: education records.
CREATE OR ALTER VIEW ai.employee_education AS
SELECT ed.EmployeeEducationID AS education_id, ed.EmployeeRef AS employee_id, e.FullName AS employee_name,
       dg.Value AS degree, ds.Value AS discipline, mj.Value AS major, ec.Value AS education_center, ed.GPA AS gpa,
       CAST(ed.EndDate AS date) AS graduation_date
FROM HCM3.EmployeeEducation ed
JOIN HCM3.Employee e ON e.EmployeeID = ed.EmployeeRef
LEFT JOIN SYS3.Lookup dg ON dg.Type = 'EducationDegree' AND dg.Code = ed.DegreeCode
LEFT JOIN SYS3.Lookup ds ON ds.Type = 'EducationDiscipline' AND ds.Code = ed.DisciplineCode
LEFT JOIN SYS3.Lookup mj ON mj.Type = 'EducationMajor' AND mj.Code = ed.MajorCode
LEFT JOIN SYS3.Lookup ec ON ec.Type = 'EducationCenter' AND ec.Code = ed.CenterCode;
GO

-- ai.employee_bank_accounts: where each employee's salary is paid (bank, account, sheba) and since when.
CREATE OR ALTER VIEW ai.employee_bank_accounts AS
SELECT pl.EmployeePaymentLocationID AS payment_location_id, pl.EmployeeRef AS employee_id, e.FullName AS employee_name,
       bk.Name AS bank_name, bb.Name AS branch_name, pl.AccountNumber AS account_number, pl.Sheba AS sheba,
       pl.EffectiveYearMonth AS effective_year_month,
       CASE WHEN pl.EmployeePaymentLocationID = (SELECT TOP 1 p2.EmployeePaymentLocationID FROM HCM3.EmployeePaymentLocation p2
                                                 WHERE p2.EmployeeRef = pl.EmployeeRef ORDER BY p2.EffectiveYearMonth DESC, p2.EmployeePaymentLocationID DESC)
            THEN 1 ELSE 0 END AS is_latest
FROM HCM3.EmployeePaymentLocation pl
JOIN HCM3.Employee e ON e.EmployeeID = pl.EmployeeRef
LEFT JOIN RPA3.Bank bk ON bk.BankID = pl.BankRef
LEFT JOIN RPA3.BankBranch bb ON bb.BankBranchID = pl.BankBranchRef;
GO

-- ai.employee_insurance: social-security / supplementary insurance registrations over time (insurance number, branch, tax group).
CREATE OR ALTER VIEW ai.employee_insurance AS
SELECT o.EmployeeRelatedOrganizationID AS registration_id, o.EmployeeRef AS employee_id, e.FullName AS employee_name,
       og.Title AS organization, ob.Code AS organization_branch_code, o.Code AS insurance_number,
       o.IsInsurance AS is_insurance, tg.Value AS tax_group,
       o.EffectiveYearMonth AS effective_year_month, o.ExpiryYearMonth AS expiry_year_month,
       CASE WHEN o.ExpiryYearMonth IS NULL THEN 1 ELSE 0 END AS is_current
FROM HCM3.EmployeeRelatedOrganization o
JOIN HCM3.Employee e ON e.EmployeeID = o.EmployeeRef
JOIN HCM3.OrganizationBranch ob ON ob.OrganizationBranchID = o.OrganizationBranchRef
JOIN HCM3.Organization og ON og.OrganizationID = ob.OrganizationRef
LEFT JOIN SYS3.Lookup tg ON tg.Type = 'TaxGroup' AND tg.Code = o.TaxGroupCode;
GO

-- ai.loans: loans / advances / share purchases deducted from salary (HCM3.LoanPayment). remainder > 0 means not fully repaid.
CREATE OR ALTER VIEW ai.loans AS
SELECT lp.LoanPaymentID AS loan_id, lp.EmployeeRef AS employee_id, e.FullName AS employee_name, lt.Title AS loan_type,
       lp.LoanNumber AS loan_number, lp.LoanAmount AS loan_amount, lp.InstalmentQuantity AS instalment_count,
       lp.InstalmentAmount AS instalment_amount, lp.Remainder AS remainder, lp.DeploymentRemainder AS opening_remainder,
       CAST(lp.ConfirmationDate AS date) AS confirmation_date, CAST(lp.PaymentDate AS date) AS payment_date,
       lps.Value AS settlement_status
FROM HCM3.LoanPayment lp
JOIN HCM3.Employee e ON e.EmployeeID = lp.EmployeeRef
JOIN HCM3.LoanType lt ON lt.LoanTypeID = lp.LoanTypeRef
LEFT JOIN SYS3.Lookup lps ON lps.Type = 'LoanPaymentState' AND lps.Code = lp.Status;
GO

-- ai.loan_instalments: scheduled/deducted instalments per loan and Jalali month (payment_year_month like 140505).
CREATE OR ALTER VIEW ai.loan_instalments AS
SELECT li.LoanInstalmentID AS instalment_id, li.LoanPaymentRef AS loan_id, l.employee_id, l.employee_name, l.loan_type,
       li.PaymentYearMonth AS payment_year_month, li.Amount AS amount, pm.Value AS payment_method
FROM HCM3.LoanInstalment li
JOIN ai.loans l ON l.loan_id = li.LoanPaymentRef
LEFT JOIN SYS3.Lookup pm ON pm.Type = 'LoanInstalmentPaymentMethod' AND pm.Code = li.PaymentMethodCode;
GO

-- ai.leave_balances: leave balances (only entitlement leave "مرخصی استحقاقی" exists). value_minutes is stored in minutes; days_equivalent assumes a
-- 480-minute working day (approximation). Negative = leave taken in excess of entitlement.
CREATE OR ALTER VIEW ai.leave_balances AS
SELECT lr.LeaveRemainderID AS leave_balance_id, lr.EmployeeRef AS employee_id, e.FullName AS employee_name, lt.Title AS leave_type,
       lr.EffectiveYearMonth AS effective_year_month, lr.Value AS value_minutes, CAST(lr.Value / 480.0 AS decimal(18,2)) AS days_equivalent,
       lr.IsTemporary AS is_temporary
FROM HCM3.LeaveRemainder lr
JOIN HCM3.Employee e ON e.EmployeeID = lr.EmployeeRef
JOIN HCM3.LeaveType lt ON lt.LeaveTypeID = lr.LeaveTypeRef;
GO

-- ai.headcount_current: current headcount of ACTIVE employees (status 2) by department and employment type.
CREATE OR ALTER VIEW ai.headcount_current AS
SELECT ISNULL(department_name, N'(بدون حکم)') AS department_name, ISNULL(employment_type, N'(نامشخص)') AS employment_type,
       COUNT(*) AS employee_count,
       SUM(CASE WHEN gender = N'زن' THEN 1 ELSE 0 END) AS female_count
FROM ai.employees
WHERE is_active = 1
GROUP BY department_name, employment_type;
GO
