# Schema `HCM3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AttendanceCalc](#attendancecalc) | 60,501 | 17 | 🟢 تراکنشی فعال | محاسبه‌ی حضور و غیاب ماهانه؛ تردد خام وجود ندارد. |
| [AttendanceCalcMonthlyItem](#attendancecalcmonthlyitem) | 62,169 | 7 | 🟢 تراکنشی فعال |  |
| [AttendanceCalculatedYearMonthDay](#attendancecalculatedyearmonthday) | 5,933 | 8 | ⚪ تنظیمات/ثابت |  |
| [AttendanceFactor](#attendancefactor) | 4 | 16 | ⚪ تنظیمات/ثابت |  |
| [AttendanceFactorProperty](#attendancefactorproperty) | 12 | 14 | ⚪ تنظیمات/ثابت |  |
| [AttendanceStatus](#attendancestatus) | 2 | 11 | ⚪ تنظیمات/ثابت |  |
| [AttendanceViewConfiguration](#attendanceviewconfiguration) | 11 | 10 | ⚪ تنظیمات/ثابت |  |
| [AuditLog](#auditlog) | 27,470 | 7 | 🟡 لاگ/کش/سیستمی |  |
| [BatchEmployeeStatute](#batchemployeestatute) | 22 | 31 | 🟢 تراکنشی فعال |  |
| [BatchEmployeeStatuteEmployee](#batchemployeestatuteemployee) | 2,480 | 10 | 🟢 تراکنشی فعال |  |
| [BatchEmployeeStatuteFactor](#batchemployeestatutefactor) | 374 | 12 | 🟢 تراکنشی فعال |  |
| [CalculationBaseTable](#calculationbasetable) | 3 | 5 | ⚪ تنظیمات/ثابت |  |
| [CalculationBaseTableItem](#calculationbasetableitem) | 46 | 23 | ⚪ تنظیمات/ثابت |  |
| [CalculationBaseTableStructure](#calculationbasetablestructure) | 8 | 54 | ⚪ تنظیمات/ثابت |  |
| [CompensationCalcType](#compensationcalctype) | 6 | 12 | 🔵 اطلاعات پایه فعال |  |
| [CompensationCalcTypeItem](#compensationcalctypeitem) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [CompensationFactor](#compensationfactor) | 285 | 15 | 🔵 اطلاعات پایه فعال | تعریف عوامل حقوق/مزایا/کسورات (Name لاتین، Title فارسی). |
| [CompensationFactorProperty](#compensationfactorproperty) | 1,887 | 13 | 🔵 اطلاعات پایه فعال |  |
| [CompensationRelatedDLType](#compensationrelateddltype) | 2 | 9 | ⚪ تنظیمات/ثابت |  |
| [CompensationTax](#compensationtax) | 42,644 | 39 | 🟢 تراکنشی فعال | محاسبه‌ی مالیات حقوق. |
| [Department](#department) | 58 | 21 | 🔵 اطلاعات پایه فعال | واحد سازمانی (۵۸). |
| [Employee](#employee) | 2,211 | 30 | 🔵 اطلاعات پایه فعال | کارمند (۲۲۱۱ سابقه؛ Status 2 فعال). حساس. |
| [EmployeeEducation](#employeeeducation) | 1,918 | 21 | 🔵 اطلاعات پایه فعال |  |
| [EmployeeLocalSyncData](#employeelocalsyncdata) | 1,522 | 4 | 🟡 لاگ/کش/سیستمی |  |
| [EmployeeMarriage](#employeemarriage) | 2,216 | 9 | 🔵 اطلاعات پایه فعال |  |
| [EmployeePaymentLocation](#employeepaymentlocation) | 2,738 | 18 | 🔵 اطلاعات پایه فعال |  |
| [EmployeePriorPeriod](#employeepriorperiod) | 37,024 | 12 | 🟢 تراکنشی فعال |  |
| [EmployeeRelatedDL](#employeerelateddl) | 4,980 | 11 | 🔵 اطلاعات پایه فعال |  |
| [EmployeeRelatedOrganization](#employeerelatedorganization) | 8,460 | 21 | 🔵 اطلاعات پایه فعال |  |
| [EmployeeRelative](#employeerelative) | 3,621 | 34 | 🔵 اطلاعات پایه فعال |  |
| [EmployeeRelativeInsurance](#employeerelativeinsurance) | 459 | 12 | ⚪ تنظیمات/ثابت |  |
| [EmployeeStatute](#employeestatute) | 20,483 | 46 | 🟢 تراکنشی فعال | حکم کارگزینی (پست/واحد/شغل/نوع استخدام). Status 10 = نهایی. |
| [EmployeeStatuteFactor](#employeestatutefactor) | 263,296 | 12 | 🟢 تراکنشی فعال |  |
| [EmployeeStatuteStateHistory](#employeestatutestatehistory) | 17,371 | 7 | 🟡 لاگ/کش/سیستمی |  |
| [EmployeeSupplementary](#employeesupplementary) | 1,255 | 9 | ⚪ تنظیمات/ثابت |  |
| [EmployeeWarriorRecord](#employeewarriorrecord) | 10 | 28 | ⚪ تنظیمات/ثابت |  |
| [EmploymentType](#employmenttype) | 3 | 10 | 🔵 اطلاعات پایه فعال |  |
| [EmploymentTypeItem](#employmenttypeitem) | 35 | 10 | ⚪ تنظیمات/ثابت |  |
| [EmpStatuteConvertMapping](#empstatuteconvertmapping) | 22,264 | 3 | 🟡 لاگ/کش/سیستمی |  |
| [FactorViewSetting](#factorviewsetting) | 55 | 13 | ⚪ تنظیمات/ثابت |  |
| [FactorViewSettingAttendance](#factorviewsettingattendance) | 11 | 5 | ⚪ تنظیمات/ثابت |  |
| [FactorViewSettingCompensation](#factorviewsettingcompensation) | 1,629 | 5 | ⚪ تنظیمات/ثابت |  |
| [FactorViewSettingType](#factorviewsettingtype) | 18 | 15 | ⚪ تنظیمات/ثابت |  |
| [FileStructure](#filestructure) | 24 | 13 | ⚪ تنظیمات/ثابت |  |
| [FileStructureField](#filestructurefield) | 544 | 19 | ⚪ تنظیمات/ثابت |  |
| [FinancialStatute](#financialstatute) | 17,548 | 14 | 🟢 تراکنشی فعال |  |
| [Formula](#formula) | 1,152 | 10 | ⚪ تنظیمات/ثابت | فرمول‌های محاسبه (کد C#/متن) برای عوامل. |
| [FormulaContext](#formulacontext) | 50 | 4 | ⚪ تنظیمات/ثابت |  |
| [FormulaContextObject](#formulacontextobject) | 8 | 8 | ⚪ تنظیمات/ثابت |  |
| [HcmTag](#hcmtag) | 7 | 2 | ⚪ تنظیمات/ثابت |  |
| [InputFileStructure](#inputfilestructure) | 15 | 22 | ⚪ تنظیمات/ثابت |  |
| [InputFileStructureField](#inputfilestructurefield) | 29 | 10 | ⚪ تنظیمات/ثابت |  |
| [Job](#job) | 790 | 18 | 🔵 اطلاعات پایه فعال |  |
| [LeaveRemainder](#leaveremainder) | 1,975 | 17 | 🟢 تراکنشی فعال |  |
| [LeaveType](#leavetype) | 1 | 20 | 🔵 اطلاعات پایه فعال |  |
| [LeaveTypeProperty](#leavetypeproperty) | 2 | 34 | ⚪ تنظیمات/ثابت |  |
| [LoanAdjustment](#loanadjustment) | 11 | 12 | 🟢 تراکنشی فعال |  |
| [LoanInstalment](#loaninstalment) | 10,736 | 7 | 🟢 تراکنشی فعال |  |
| [LoanPayment](#loanpayment) | 5,758 | 24 | 🟢 تراکنشی فعال | وام/مساعده‌ی پرداختی به کارکنان؛ LoanInstalment اقساط. |
| [LoanType](#loantype) | 10 | 11 | 🔵 اطلاعات پایه فعال |  |
| [LocalSyncDataPartition](#localsyncdatapartition) | 14 | 5 | ⚪ تنظیمات/ثابت |  |
| [MajorJobClass](#majorjobclass) | 2 | 8 | ⚪ تنظیمات/ثابت |  |
| [Mapping](#mapping) | 10 | 10 | ⚪ تنظیمات/ثابت |  |
| [MappingInput](#mappinginput) | 399 | 16 | ⚪ تنظیمات/ثابت |  |
| [MappingOutput](#mappingoutput) | 679 | 12 | ⚪ تنظیمات/ثابت |  |
| [MappingStructure](#mappingstructure) | 26 | 9 | ⚪ تنظیمات/ثابت |  |
| [MappingStructureInput](#mappingstructureinput) | 62 | 13 | ⚪ تنظیمات/ثابت |  |
| [MappingStructureOutput](#mappingstructureoutput) | 30 | 12 | ⚪ تنظیمات/ثابت |  |
| [MonthlyFactorData](#monthlyfactordata) | 78,222 | 9 | 🟢 تراکنشی فعال |  |
| [MonthlyFactorDataCompensationItem](#monthlyfactordatacompensationitem) | 248,358 | 14 | 🟢 تراکنشی فعال |  |
| [Organization](#organization) | 3 | 11 | 🔵 اطلاعات پایه فعال |  |
| [OrganizationBranch](#organizationbranch) | 32 | 13 | 🔵 اطلاعات پایه فعال |  |
| [OrganizationCompensationFactor](#organizationcompensationfactor) | 52 | 8 | ⚪ تنظیمات/ثابت |  |
| [PayCalc](#paycalc) | 82,446 | 8 | 🟢 تراکنشی فعال | محاسبه‌ی حقوق ماهانه هر کارمند؛ IssueYearMonth جلالی (YYYYMM). |
| [PayCalcItem](#paycalcitem) | 3,453,700 | 9 | 🟢 تراکنشی فعال | مقادیر عوامل حقوقی هر محاسبه؛ CompensationFactorRef=63 خالص پرداختی، 55 قابل پرداخت، 62 جمع کسور، 61 جمع مزایا. حساس. |
| [PeriodicCalc](#periodiccalc) | 73,819 | 10 | 🟢 تراکنشی فعال | محاسبات دوره‌ای (عیدی، بازخرید...) به‌تفکیک CompensationCalcType. |
| [PeriodicCalcItem](#periodiccalcitem) | 790,606 | 8 | 🟢 تراکنشی فعال |  |
| [Post](#post) | 359 | 28 | 🔵 اطلاعات پایه فعال |  |
| [PostJob](#postjob) | 264 | 8 | 🔵 اطلاعات پایه فعال |  |
| [ReportSetting](#reportsetting) | 2 | 10 | ⚪ تنظیمات/ثابت |  |
| [ReportSettingCompensationFactor](#reportsettingcompensationfactor) | 26 | 6 | ⚪ تنظیمات/ثابت |  |
| [ReportSettingItem](#reportsettingitem) | 26 | 9 | ⚪ تنظیمات/ثابت |  |
| [RfidDeviceSdk](#rfiddevicesdk) | 10 | 10 | ⚪ تنظیمات/ثابت |  |
| [RfidLocalLogicalResource](#rfidlocallogicalresource) | 14 | 5 | ⚪ تنظیمات/ثابت |  |
| [SelfServiceLinkAccess](#selfservicelinkaccess) | 3 | 77 | ⚪ تنظیمات/ثابت |  |
| [SettlementViewSettingInputValue](#settlementviewsettinginputvalue) | 1 | 9 | ⚪ تنظیمات/ثابت |  |
| [StatuteFactor](#statutefactor) | 27 | 14 | 🔵 اطلاعات پایه فعال |  |
| [StatuteFactorDisplayOrder](#statutefactordisplayorder) | 51 | 5 | ⚪ تنظیمات/ثابت |  |
| [StatuteFactorProperty](#statutefactorproperty) | 94 | 12 | ⚪ تنظیمات/ثابت |  |
| [StatuteType](#statutetype) | 13 | 17 | 🔵 اطلاعات پایه فعال |  |
| [StatuteTypeFactor](#statutetypefactor) | 676 | 10 | ⚪ تنظیمات/ثابت |  |
| [StatuteTypeParameter](#statutetypeparameter) | 157 | 11 | ⚪ تنظیمات/ثابت |  |
| [StrategicObjectiveType](#strategicobjectivetype) | 2 | 9 | ⚪ تنظیمات/ثابت |  |
| [TaxTable](#taxtable) | 37 | 10 | 🔵 اطلاعات پایه فعال |  |
| [TaxTableItem](#taxtableitem) | 183 | 10 | 🔵 اطلاعات پایه فعال |  |
| [Voucher](#voucher) | 272 | 18 | 🟢 تراکنشی فعال | ارتباط محاسبه‌ی حقوق با سند حسابداری (VoucherRef → FIN3.Voucher). |
| [VoucherEmployee](#voucheremployee) | 106,737 | 8 | 🟢 تراکنشی فعال |  |
| [VoucherSpecification](#voucherspecification) | 48 | 12 | 🔵 اطلاعات پایه فعال |  |
| [VoucherSpecificationCalcType](#voucherspecificationcalctype) | 48 | 4 | ⚪ تنظیمات/ثابت |  |
| [VoucherSpecificationSL](#voucherspecificationsl) | 877 | 46 | 🔵 اطلاعات پایه فعال |  |
| [VoucherSpecificationSLFactor](#voucherspecificationslfactor) | 3,416 | 10 | ⚪ تنظیمات/ثابت |  |
| [VoucherSpecificationSLLoan](#voucherspecificationslloan) | 96 | 8 | ⚪ تنظیمات/ثابت |  |
| [VoucherSpecificationSLRelatedDL](#voucherspecificationslrelateddl) | 112,904 | 10 | ⚪ تنظیمات/ثابت |  |

## AttendanceCalc

`HCM3.AttendanceCalc` — 60,501 rows — 🟢 تراکنشی فعال

محاسبه‌ی حضور و غیاب ماهانه؛ تردد خام وجود ندارد.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceCalcID | bigint |  | PK |  |
| IssueYearMonth | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| FromDate | datetime |  |  |  |
| ToDate | datetime |  |  |  |
| AttendanceCalculationCalendarRef | bigint | Y | → HCM3.AttendanceCalculationCalendar.AttendanceCalculationCalendarID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| CalcType | int |  |  |  |
| LastAttendanceDateTime | datetime | Y |  |  |
| LastAttendanceEntrance | bit | Y |  |  |
| LastAttendanceRef | bigint | Y |  |  |
| EndDateTime | datetime | Y |  |  |
| FirstincompleteDate | datetime | Y |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceCalcDailyItem`، `HCM3.AttendanceCalcApplyInfo`، `HCM3.AttendanceCalcMonthlyItem`

## AttendanceCalcMonthlyItem

`HCM3.AttendanceCalcMonthlyItem` — 62,169 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceCalcMonthlyItemID | bigint |  | PK |  |
| AttendanceCalcRef | bigint |  | → HCM3.AttendanceCalc.AttendanceCalcID |  |
| AttendanceFactorRef | bigint |  | → HCM3.AttendanceFactor.AttendanceFactorID |  |
| AttendanceFactorPropertyRef | bigint |  | → HCM3.AttendanceFactorProperty.AttendanceFactorPropertyID |  |
| ApplyYearMonth | int |  |  |  |
| Value | decimal(28,6) |  |  |  |

## AttendanceCalculatedYearMonthDay

`HCM3.AttendanceCalculatedYearMonthDay` — 5,933 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceCalculatedYearMonthDayID | bigint |  | PK |  |
| YearMonth | int |  |  |  |
| Date | datetime |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## AttendanceFactor

`HCM3.AttendanceFactor` — 4 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceFactorID | bigint |  | PK |  |
| Name | varchar(255) |  |  |  |
| Title | nvarchar(400) |  |  |  |
| ScaleCode | int |  |  | `AttendanceFactorScale`: 2=ماهانه |
| AssignTypeCode | int |  |  | `AttendanceFactorAssignType`: 1=محاسباتی |
| MeasurementUnitCode | int |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| EmploymentTypeVisible | bit |  |  |  |
| WorkingGroupVisible | bit |  |  |  |
| WorkLocationVisible | bit |  |  |  |
| BranchVisible | bit |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceFactorProperty`، `HCM3.AttendancePermissionRequestStructure`، `HCM3.ReportConfigurationUserFactor`، `HCM3.ReportConfigurationFactor`، `HCM3.AttendanceMonthlyInputFactorData`، `HCM3.AttendanceFixedFactorData`، `HCM3.ReportSettingAttendanceFactor`، `HCM3.AttendanceDataFactorViewSetting`، `HCM3.AttendanceCalcDailyItem`، `HCM3.FactorViewSettingAttendance`، `HCM3.AttendanceCalcPropertyInfo`، `HCM3.AttendanceDailyInputFactorData`، `HCM3.AttendanceViewConfigurationFactor`، `HCM3.AttendanceDailyFixedFactorData`، `HCM3.AttendanceViewConfigurationUserFactor`، `HCM3.AttendanceCalcMonthlyItem`

## AttendanceFactorProperty

`HCM3.AttendanceFactorProperty` — 12 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceFactorPropertyID | bigint |  | PK |  |
| AttendanceFactorRef | bigint |  | → HCM3.AttendanceFactor.AttendanceFactorID |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| WorkingGroupRef | bigint | Y | → HCM3.WorkingGroup.WorkingGroupID |  |
| WorkLocationCode | int | Y |  | `WorkLocation`:  |
| BranchRef | bigint | Y | → GNR3.Branch.BranchID |  |
| ApplyYearMonth | int |  |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceMonthlyInputFactorData`، `HCM3.AttendanceFixedFactorData`، `HCM3.AttendanceCalcDailyItem`، `HCM3.AttendanceCalcPropertyInfo`، `HCM3.AttendanceDailyInputFactorData`، `HCM3.AttendanceDailyFixedFactorData`، `HCM3.AttendanceCalcMonthlyItem`

## AttendanceStatus

`HCM3.AttendanceStatus` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceStatusID | bigint |  | PK |  |
| Title | nvarchar(200) |  |  |  |
| EffectiveOnAttendanceCalc | bit |  |  |  |
| TypeCode | int |  |  | `AttendanceStatusType`: 1=تردد |
| ViewInSelfService | bit |  |  |  |
| Color | nchar(7) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendancePermissionType`، `HCM3.AttendanceDataCorrectionRequest`، `HCM3.AttendanceData`، `HCM3.MissionTypeAttendanceStatus`، `HCM3.LeaveTypeAttendanceStatus`، `HCM3.LeaveRequestAttendanceStatus`

## AttendanceViewConfiguration

`HCM3.AttendanceViewConfiguration` — 11 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AttendanceViewConfigurationID | bigint |  | PK |  |
| Title | nvarchar(400) |  |  |  |
| AssignTypeFilters | int |  |  |  |
| AssignTypeViews | int |  |  |  |
| UserLevel | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceViewConfigurationUserWorkingDayInfo`، `HCM3.AttendanceViewConfigurationFactor`، `HCM3.AttendanceViewConfigurationUserFactor`

## AuditLog

`HCM3.AuditLog` — 27,470 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AuditLogID | bigint |  | PK |  |
| EntityId | bigint |  |  |  |
| EntityType | varchar(200) |  |  |  |
| EmployeeId | bigint |  |  |  |
| ActionType | tinyint |  |  |  |
| IssueDate | datetime |  |  |  |
| EffectiveDate | datetime | Y |  |  |

## BatchEmployeeStatute

`HCM3.BatchEmployeeStatute` — 22 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BatchEmployeeStatuteID | bigint |  | PK |  |
| Title | nvarchar(200) |  |  |  |
| Number | nvarchar(200) | Y |  |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| EmploymentDate | datetime | Y |  |  |
| StatuteTypeRef | bigint |  | → HCM3.StatuteType.StatuteTypeID |  |
| IssueDate | datetime |  |  |  |
| ApplyDate | datetime |  |  |  |
| ExpiryDate | datetime | Y |  |  |
| OrganizationalStructureRef | bigint | Y | → HCM3.OrganizationalStructure.OrganizationalStructureID |  |
| PostRef | bigint | Y | → HCM3.Post.PostID |  |
| DepartmentRef | bigint | Y | → HCM3.Department.DepartmentID |  |
| JobRef | bigint | Y | → HCM3.Job.JobID |  |
| WorkLocationCode | int | Y |  | `WorkLocation`: 20=سیرجان_قطروئیه، 28=ماشین آلات سیرجان |
| RankCode | int | Y |  | `Rank`:  |
| BaseCode | int | Y |  | `Base`:  |
| Description | nvarchar(max) | Y |  |  |
| ConfirmDate | datetime | Y |  |  |
| ConfirmerRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| PaymentConfirmDate | datetime | Y |  |  |
| PaymentConfirmerRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| RetirementDate | datetime | Y |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |
| Extra3Code | int | Y |  |  |
| Extra4Code | int | Y |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeStatute`، `HCM3.BatchEmployeeStatuteFactor`، `HCM3.BatchEmployeeStatuteEmployee`

## BatchEmployeeStatuteEmployee

`HCM3.BatchEmployeeStatuteEmployee` — 2,480 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BatchEmployeeStatuteEmployeeID | bigint |  | PK |  |
| BatchEmployeeStatuteRef | bigint |  | → HCM3.BatchEmployeeStatute.BatchEmployeeStatuteID |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| StatusMessage | nvarchar(400) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| PromotionProcessRef | bigint | Y |  |  |

## BatchEmployeeStatuteFactor

`HCM3.BatchEmployeeStatuteFactor` — 374 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BatchEmployeeStatuteFactorID | bigint |  | PK |  |
| BatchEmployeeStatuteRef | bigint |  | → HCM3.BatchEmployeeStatute.BatchEmployeeStatuteID |  |
| StatuteFactorRef | bigint |  | → HCM3.StatuteFactor.StatuteFactorID |  |
| AssignmentMethodCode | int |  |  |  |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| SpecifiedValue | decimal(28,6) | Y |  |  |
| Percent | float | Y |  |  |

## CalculationBaseTable

`HCM3.CalculationBaseTable` — 3 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CalculationBaseTableID | bigint |  | PK |  |
| CalculationBaseTableStructureRef | bigint |  | → HCM3.CalculationBaseTableStructure.CalculationBaseTableStructureID |  |
| Title | nvarchar(100) |  |  |  |
| ActivationDate | datetime | Y |  |  |

ارجاع‌شده توسط: `HCM3.CalculationBaseTableItem`

## CalculationBaseTableItem

`HCM3.CalculationBaseTableItem` — 46 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CalculationBaseTableItemID | bigint |  | PK |  |
| CalculationBaseTableRef | bigint |  | → HCM3.CalculationBaseTable.CalculationBaseTableID |  |
| Key1 | decimal(28,6) |  |  |  |
| Key2 | decimal(28,6) | Y |  |  |
| Key3 | decimal(28,6) | Y |  |  |
| Value1 | decimal(28,6) |  |  |  |
| Value2 | decimal(28,6) | Y |  |  |
| Value3 | decimal(28,6) | Y |  |  |
| Key4 | decimal(28,6) | Y |  |  |
| Key5 | decimal(28,6) | Y |  |  |
| Key6 | decimal(28,6) | Y |  |  |
| Key7 | decimal(28,6) | Y |  |  |
| Key8 | decimal(28,6) | Y |  |  |
| Key9 | decimal(28,6) | Y |  |  |
| Key10 | decimal(28,6) | Y |  |  |
| Value4 | decimal(28,6) | Y |  |  |
| Value5 | decimal(28,6) | Y |  |  |
| Value6 | decimal(28,6) | Y |  |  |
| Value7 | decimal(28,6) | Y |  |  |
| Value8 | decimal(28,6) | Y |  |  |
| Value9 | decimal(28,6) | Y |  |  |
| Value10 | decimal(28,6) | Y |  |  |

## CalculationBaseTableStructure

`HCM3.CalculationBaseTableStructure` — 8 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CalculationBaseTableStructureID | bigint |  | PK |  |
| Title | nvarchar(100) |  |  |  |
| Name | nvarchar(255) |  |  |  |
| EntityCode1 | nvarchar(100) | Y |  |  |
| EntityCode2 | nvarchar(100) | Y |  |  |
| EntityCode3 | nvarchar(100) | Y |  |  |
| LookupCode1 | nvarchar(100) | Y |  |  |
| LookupCode2 | nvarchar(100) | Y |  |  |
| LookupCode3 | nvarchar(100) | Y |  |  |
| InputTitle1 | nvarchar(255) | Y |  |  |
| InputTitle2 | nvarchar(255) | Y |  |  |
| InputTitle3 | nvarchar(255) | Y |  |  |
| ValueTitle1 | nvarchar(255) |  |  |  |
| ValueTitle2 | nvarchar(255) | Y |  |  |
| ValueTitle3 | nvarchar(255) | Y |  |  |
| EntityTitleField1 | varchar(255) | Y |  |  |
| EntityTitleField2 | varchar(255) | Y |  |  |
| EntityTitleField3 | varchar(255) | Y |  |  |
| EntityCode4 | nvarchar(100) | Y |  |  |
| EntityCode5 | nvarchar(100) | Y |  |  |
| EntityCode6 | nvarchar(100) | Y |  |  |
| EntityCode7 | nvarchar(100) | Y |  |  |
| EntityCode8 | nvarchar(100) | Y |  |  |
| EntityCode9 | nvarchar(100) | Y |  |  |
| EntityCode10 | nvarchar(100) | Y |  |  |
| EntityTitleField4 | varchar(255) | Y |  |  |
| EntityTitleField5 | varchar(255) | Y |  |  |
| EntityTitleField6 | varchar(255) | Y |  |  |
| EntityTitleField7 | varchar(255) | Y |  |  |
| EntityTitleField8 | varchar(255) | Y |  |  |
| EntityTitleField9 | varchar(255) | Y |  |  |
| EntityTitleField10 | varchar(255) | Y |  |  |
| LookupCode4 | nvarchar(100) | Y |  |  |
| LookupCode5 | nvarchar(100) | Y |  |  |
| LookupCode6 | nvarchar(100) | Y |  |  |
| LookupCode7 | nvarchar(100) | Y |  |  |
| LookupCode8 | nvarchar(100) | Y |  |  |
| LookupCode9 | nvarchar(100) | Y |  |  |
| LookupCode10 | nvarchar(100) | Y |  |  |
| InputTitle4 | nvarchar(255) | Y |  |  |
| InputTitle5 | nvarchar(255) | Y |  |  |
| InputTitle6 | nvarchar(255) | Y |  |  |
| InputTitle7 | nvarchar(255) | Y |  |  |
| InputTitle8 | nvarchar(255) | Y |  |  |
| InputTitle9 | nvarchar(255) | Y |  |  |
| InputTitle10 | nvarchar(255) | Y |  |  |
| ValueTitle4 | nvarchar(100) | Y |  |  |
| ValueTitle5 | nvarchar(100) | Y |  |  |
| ValueTitle6 | nvarchar(100) | Y |  |  |
| ValueTitle7 | nvarchar(100) | Y |  |  |
| ValueTitle8 | nvarchar(100) | Y |  |  |
| ValueTitle9 | nvarchar(100) | Y |  |  |
| ValueTitle10 | nvarchar(100) | Y |  |  |

ارجاع‌شده توسط: `HCM3.CalculationBaseTable`

## CompensationCalcType

`HCM3.CompensationCalcType` — 6 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationCalcTypeID | bigint |  | PK |  |
| Title | nvarchar(400) |  |  |  |
| GroupCode | int |  |  |  |
| SequenceCode | int | Y |  |  |
| PreventIssueStatute | bit |  |  |  |
| PreventAttendanceCalc | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Type | int |  |  |  |

ارجاع‌شده توسط: `HCM3.UserDefinedCalc`، `HCM3.CompensationPaymentRequestType`، `HCM3.FactorViewSetting`، `HCM3.CompensationFactor`، `HCM3.CompensationTax`، `HCM3.FinancialStatute`، `HCM3.RetirementUserDefinedCalc`، `HCM3.PeriodicCalc`، `HCM3.VoucherSpecificationCalcType`، `HCM3.MonthlyFactorData`، `HCM3.CompensationInsurance`، `HCM3.CompensationCalcTypeItem`

## CompensationCalcTypeItem

`HCM3.CompensationCalcTypeItem` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationCalcTypeItemID | bigint |  | PK |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| DeferredConditionType | int |  |  |  |

## CompensationFactor

`HCM3.CompensationFactor` — 285 rows — 🔵 اطلاعات پایه فعال

تعریف عوامل حقوق/مزایا/کسورات (Name لاتین، Title فارسی).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationFactorID | bigint |  | PK |  |
| Name | varchar(255) |  |  |  |
| Title | nvarchar(400) |  |  |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| CategoryCode | int |  |  | `CompensationFactorCategory`: 1=مزایا، 2=کسور، 3=تعهدات کارفرما، 4=حکم مالی، 5=سایر، 6=مطالبات، 7=بدهی ها، 8=بدون طبقه |
| AssignTypeCode | int |  |  | `CompensationFactorAssignType`: 1=محاسباتی، 2=ورودی |
| MeasurementUnitCode | int |  |  |  |
| FinalResult | bit |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| IsTreasury | bit |  |  |  |

ارجاع‌شده توسط: `HCM3.ReportSettingCompensationFactor`، `HCM3.CompensationFactorProperty`، `HCM3.PayCalcItem`، `HCM3.OrganizationCompensationFactor`، `HCM3.CompensationPaymentRequestTypeItem`، `HCM3.ReportConfigurationUserFactor`، `HCM3.FinancialStatute`، `HCM3.ReportConfigurationFactor`، `HCM3.SettlementCalcItem`، `HCM3.UserDefinedCalcItem`، `HCM3.RetirementUserDefinedCalcItem`، `HCM3.PeriodicCalcItem`، `HCM3.RetirementCalcItem`، `HCM3.EmployeePaymentLocation`، `HCM3.FileStructureBank`، `HCM3.VoucherSpecificationSLFactor`، `HCM3.FactorViewSettingCompensation`، `HCM3.TransferVoucherSpecificationSLFactor`، `HCM3.MonthlyFactorDataCompensationItem`

## CompensationFactorProperty

`HCM3.CompensationFactorProperty` — 1,887 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationFactorPropertyID | bigint |  | PK |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| EmploymentTypeRef | bigint |  | → HCM3.EmploymentType.EmploymentTypeID |  |
| IssueYearMonth | int |  |  |  |
| ApplyYearMonth | int |  |  |  |
| Attributes | int |  |  |  |
| Status | int |  |  |  |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.PayCalcItem`، `HCM3.UserDefinedCalcItem`، `HCM3.SettlementCalcItem`، `HCM3.RetirementUserDefinedCalcItem`، `HCM3.PeriodicCalcItem`، `HCM3.RetirementCalcItem`، `HCM3.MonthlyFactorDataCompensationItem`

## CompensationRelatedDLType

`HCM3.CompensationRelatedDLType` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationRelatedDLTypeID | bigint |  | PK |  |
| DLTypeRef | bigint |  | → FIN3.DLType.DLTypeID |  |
| Mandatory | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| ShowInEmployeeFilter | bit |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeRelatedDL`

## CompensationTax

`HCM3.CompensationTax` — 42,644 rows — 🟢 تراکنشی فعال

محاسبه‌ی مالیات حقوق.

> ⚠️ **حساس**: مالیات حقوق افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompensationTaxID | bigint |  | PK |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| IssueYearMonth | int |  |  |  |
| ApplyYearMonth | int |  |  |  |
| CurrentIncomeContinuousCash | decimal(28,0) |  |  |  |
| CurrentIncomeContinuousNonCash | decimal(28,0) |  |  |  |
| CurrentIncomeDiscontinuousNonCash | decimal(28,0) |  |  |  |
| CurrentIncomeDiscontinuousCash | decimal(28,0) |  |  |  |
| YearlyIncomeContinuousCash | decimal(28,0) |  |  |  |
| YearlyIncomeContinuousNonCash | decimal(28,0) |  |  |  |
| YearlyIncomeDiscontinuousNonCash | decimal(28,0) |  |  |  |
| YearlyIncomeDiscontinuousCash | decimal(28,0) |  |  |  |
| YearlyIncome | decimal(28,0) |  |  |  |
| YearlyTax | decimal(28,0) |  |  |  |
| YearlyIncomeContinuousNonCashAfterExemption9113 | decimal(28,0) |  |  |  |
| YearlyIncomeNonCash | decimal(28,0) |  |  |  |
| YearlyIncomeContinuousCashAndNonCash | decimal(28,0) |  |  |  |
| YearlyTaxForContinuousCashAndNonCash | decimal(28,0) |  |  |  |
| DiscontinuousPaymentTax | decimal(28,0) |  |  |  |
| ContinuousPaymentTax | decimal(28,0) |  |  |  |
| TotalTax | decimal(28,0) |  |  |  |
| MonthlyTax | decimal(28,0) |  |  |  |
| Tax | decimal(28,0) |  |  |  |
| TaxPaidSurplus | decimal(28,0) |  |  |  |
| CurrentTaxSurplus | decimal(28,0) |  |  |  |
| TotalAttendanceMonths | decimal(28,0) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| IsTreasury | bit |  |  |  |
| TaxDiscount | decimal(28,0) |  |  |  |
| Exemption9113Reminder | decimal(28,0) |  |  |  |
| SpecialTax | decimal(28,0) |  |  |  |
| CurrentIncomeSpecial | decimal(28,0) |  |  |  |
| IncomeSpecial | decimal(28,0) |  |  |  |
| SpecialTaxExemption | decimal(28,0) |  |  |  |

## Department

`HCM3.Department` — 58 rows — 🔵 اطلاعات پایه فعال

واحد سازمانی (۵۸).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DepartmentID | bigint |  | PK |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(200) |  |  |  |
| AbbrSign | nvarchar(50) | Y |  |  |
| BusinessDomainCode | int | Y |  |  |
| DepartmentTypeCode | int | Y |  | `DepartmentType`:  |
| RegionalDivisionRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| Description | nvarchar(max) | Y |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| StatusChangeDate | datetime | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| UniqueCode | nvarchar(100) | Y |  |  |
| AbbrName | nvarchar(50) | Y |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |
| Extra3Code | int | Y |  |  |
| SecondLanguageTitle | nvarchar(200) | Y |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeWorkChangeRequest`، `HCM3.PeriodEvaluationStepType`، `HCM3.EmployeeStatute`، `HCM3.EmployeeConditionItem`، `HCM3.EmployeeStatuteTempPost`، `HCM3.MissionDocument`، `HCM3.MandatoryDistributionStructureItem`، `HCM3.EmployeeWorkRecord`، `ECM.Correspondent`، `ECM.Letter`، `HCM3.BatchMissionDocument`، `HCM3.CorrectiveEmployeeStatute`، `HCM3.OrganizationalStructure`، `HCM3.BatchEmployeeStatute`، `HCM3.BatchCorrectiveEmployeeStatute`، `HCM3.EmployeeInfo`

## Employee

`HCM3.Employee` — 2,211 rows — 🔵 اطلاعات پایه فعال

کارمند (۲۲۱۱ سابقه؛ Status 2 فعال). حساس.

> ⚠️ **حساس**: کد ملی/نظام وظیفه/فایل پیوست

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| Code | nvarchar(100) |  |  |  |
| WorkIDNumber | nvarchar(100) | Y |  |  |
| EmploymentNumber | nvarchar(100) | Y |  |  |
| MilitaryServiceStatusCode | int | Y |  | `MilitaryServiceStatus`: 1=انجام داده، 2=معاف، 3=غیبت، 4=در حال انجام |
| MilitaryUnitCode | int | Y |  | `MilitaryUnit`: 1=ارتش، 2=سپاه، 3=کمیته انقلاب اسلامی، 4=مدیریت وظیفه عمومی، 5=نیروی انتظامی، 6=وزارت دفاع |
| MilitaryBranchCode | int | Y |  | `MilitaryBranch`: 1=اداری، 2=خدماتی، 3=پشتیبانی |
| ExemptionTypeCode | int | Y |  | `ExemptionType`: 18=پایان خدمت، 19=معاف کفالت، 95=معافیت تحصیلی، 97=پزشکی، 98=معافیت رهبری، 134=(Unkown)، 135=موارد خاص، 136=جریمه مشمولان غایب |
| MilitaryStartDate | datetime | Y |  |  |
| MilitaryEndDate | datetime | Y |  |  |
| MilitaryDuration | int | Y |  |  |
| MilitaryEducationDegreeCode | int | Y |  |  |
| MilitaryAttachment | varbinary(max) | Y |  |  |
| MilitaryAttachmentFileName | nvarchar(512) | Y |  |  |
| Status | int |  |  | `EmployeeStatus`: 1=جدید، 2=فعال، 3=غیر فعال، 4=معلق |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| DeathDate | datetime | Y |  |  |
| DeathAnnouncingDate | datetime | Y |  |  |
| MailAttachmentPassword | nvarchar(max) | Y |  |  |
| MonthLengthType | int | Y |  | `MonthLengthType`:  |
| FirstName | nvarchar(50) |  |  |  |
| LastName | nvarchar(50) |  |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |
| FullName | nvarchar(101) |  |  |  |

ارجاع‌شده توسط: `HCM3.LeaveRemainder`، `HCM3.EmployeeRfidCard`، `HCM3.EmployeeAppraiserItem`، `HCM3.RfidEmployeePhone`، `HCM3.EmployeeStatute`، `HCM3.EmployeeFace`، `HCM3.EmployeeEmploymentNumber`، `HCM3.UserDefinedCalc`، `HCM3.NegativeRemainderRequest`، `HCM3.EmployeeTraining`، `HCM3.EmployeeContractInfo`، `HCM3.AppraisalQuestionnaire`، `HCM3.EmployeeSupplementary`، `HCM3.EmployeeRelatedOrganization`، `HCM3.PromotionProcess`، `HCM3.EmployeeBranchInfo`، `HCM3.EmployeeConditionItem`، `HCM3.EmployeeCompetency`، `HCM3.PayCalcItem`، `HCM3.CompensationComplementRequestEmployee`، `HCM3.ChangeEmploymentDate`، `HCM3.AttendanceDataCorrectionRequest`، `HCM3.EmployeeGroupEmployee`، `HCM3.CorrectiveEmployeeStatuteStateHistory`، `HCM3.PayCalc` …

## EmployeeEducation

`HCM3.EmployeeEducation` — 1,918 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeEducationID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| DegreeCode | int |  |  |  |
| DisciplineCode | int |  |  |  |
| MajorCode | int | Y |  |  |
| StartDate | datetime | Y |  |  |
| EndDate | datetime | Y |  |  |
| GPA | nvarchar(10) | Y |  |  |
| CenterCode | int |  |  |  |
| NeedLevelCode | int |  |  |  |
| QualityCode | int |  |  |  |
| EffectiveDate | datetime |  |  |  |
| FileName | nvarchar(512) | Y |  |  |
| FileContents | varbinary(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |

## EmployeeLocalSyncData

`HCM3.EmployeeLocalSyncData` — 1,522 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeLocalSyncDataID | bigint |  | PK |  |
| EmployeeID | bigint |  |  |  |
| LocalSyncDataPartitionRef | bigint | Y | → HCM3.LocalSyncDataPartition.LocalSyncDataPartitionID |  |

## EmployeeMarriage

`HCM3.EmployeeMarriage` — 2,216 rows — 🔵 اطلاعات پایه فعال

> ⚠️ **حساس**: اطلاعات خانواده

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeMarriageID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| StatusCode | int |  |  |  |
| EffectiveDate | datetime |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## EmployeePaymentLocation

`HCM3.EmployeePaymentLocation` — 2,738 rows — 🔵 اطلاعات پایه فعال

> ⚠️ **حساس**: شماره حساب/شبا

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeePaymentLocationID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| TypeCode | int |  |  |  |
| BankRef | bigint | Y | → RPA3.Bank.BankID |  |
| CashRef | bigint | Y | → RPA3.Cash.CashID |  |
| BankBranchRef | bigint | Y | → RPA3.BankBranch.BankBranchID |  |
| BankAccountTypeRef | bigint | Y | → RPA3.BankAccountType.BankAccountTypeID |  |
| CompensationFactorRef | bigint | Y | → HCM3.CompensationFactor.CompensationFactorID |  |
| AccountNumber | nvarchar(50) | Y |  |  |
| EffectiveYearMonth | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Sheba | nvarchar(26) | Y |  |  |
| IsRetirement | bit |  |  |  |
| PartyBankAccountRef | bigint | Y | → RPA3.PartyBankAccount.PartyBankAccountID |  |

## EmployeePriorPeriod

`HCM3.EmployeePriorPeriod` — 37,024 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeePriorPeriodID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CompensationCalcSubTypeCode | int |  |  | `CompensationCalcSubType`: 1=ذخیره |
| DeploymentAmount | decimal(28,6) |  |  |  |
| CalcYearMonth | int |  |  |  |
| BaseCalcYearMonth | int |  |  |  |
| IsManual | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## EmployeeRelatedDL

`HCM3.EmployeeRelatedDL` — 4,980 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeRelatedDLID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CompensationRelatedDLTypeRef | bigint |  | → HCM3.CompensationRelatedDLType.CompensationRelatedDLTypeID |  |
| DLCode | nvarchar(64) | Y | → FIN3.DL.Code |  |
| EffectiveDate | datetime |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| EffectiveYearMonth | int |  |  |  |

## EmployeeRelatedOrganization

`HCM3.EmployeeRelatedOrganization` — 8,460 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeRelatedOrganizationID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| OrganizationBranchRef | bigint |  | → HCM3.OrganizationBranch.OrganizationBranchID |  |
| InsuranceContractCode | int | Y |  |  |
| TaxGroupCode | int | Y |  | `TaxGroup`: 1=100%، 2=50%، 3=10%، 4=بازنشسته وظیفه و مستمری بگیر، 9=جانبازان انقلاب اسلامی |
| TaxCalculationTypeCode | int | Y |  | `TaxCalculationType`: 1=تعدیل ماهیانه |
| Code | nvarchar(200) | Y |  |  |
| IssueYearMonth | int |  |  |  |
| EffectiveYearMonth | int |  |  |  |
| ExpiryYearMonth | int | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| IsInsurance | bit |  |  |  |
| OrganizationRef | bigint |  | → HCM3.Organization.OrganizationID |  |
| InsuranceType | int | Y |  | `InsuranceType`: 1=وارداتی |
| IssueDate | datetime |  |  |  |
| EffectiveDate | datetime |  |  |  |
| ExpiryDate | datetime | Y |  |  |

## EmployeeRelative

`HCM3.EmployeeRelative` — 3,621 rows — 🔵 اطلاعات پایه فعال

> ⚠️ **حساس**: اطلاعات خانواده

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeRelativeID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| FirstName | nvarchar(100) |  |  |  |
| LastName | nvarchar(100) | Y |  |  |
| FatherName | nvarchar(100) | Y |  |  |
| RelationCode | int |  |  |  |
| NationalID | varchar(20) |  |  |  |
| IDNumber | varchar(20) | Y |  |  |
| BirthDate | datetime |  |  |  |
| RegionalDivisionRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| DegreeCode | int | Y |  |  |
| EducationStateCode | int | Y |  | `EducationState`:  |
| PhysicalStateCode | int | Y |  | `PhysicalState`: 1=سالم |
| MaritalStatusCode | int | Y |  | `MaritalStatus`: 1=مجرد، 2=متأهل |
| Job | nvarchar(100) | Y |  |  |
| Address | nvarchar(150) | Y |  |  |
| IsFourthChild | bit |  |  |  |
| IncludeInSonshipPay | bit |  |  |  |
| ExpiryDate | datetime | Y |  |  |
| FileName | nvarchar(512) | Y |  |  |
| FileContents | varbinary(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| EffectiveDate | datetime |  |  |  |
| AnnouncingDate | datetime | Y |  |  |
| EmployeeRelativeExtra1Code | int | Y |  |  |
| DutySalaryShare | decimal(10,2) | Y |  |  |
| AllegianceCode | int |  |  | `Allegiance`: 1=ایرانی |
| RelativeType | int |  |  |  |
| ParentEmployeeRef | bigint | Y | → HCM3.Employee.EmployeeID |  |

ارجاع‌شده توسط: `HCM3.EmployeeRelativeInsurance`

## EmployeeRelativeInsurance

`HCM3.EmployeeRelativeInsurance` — 459 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeRelativeInsuranceID | bigint |  | PK |  |
| EmployeeRelativeRef | bigint |  | → HCM3.EmployeeRelative.EmployeeRelativeID |  |
| OrganizationRef | bigint |  | → HCM3.Organization.OrganizationID |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime | Y |  |  |
| InsuranceNumber | nvarchar(50) | Y |  |  |
| IsSurety | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## EmployeeStatute

`HCM3.EmployeeStatute` — 20,483 rows — 🟢 تراکنشی فعال

حکم کارگزینی (پست/واحد/شغل/نوع استخدام). Status 10 = نهایی.

> ⚠️ **حساس**: احکام حقوقی افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeStatuteID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| EmploymentDate | datetime | Y |  |  |
| StatuteTypeRef | bigint | Y | → HCM3.StatuteType.StatuteTypeID |  |
| Number | nvarchar(200) | Y |  |  |
| IssueDate | datetime | Y |  |  |
| ApplyDate | datetime | Y |  |  |
| ExpiryDate | datetime | Y |  |  |
| OrganizationalStructureRef | bigint | Y | → HCM3.OrganizationalStructure.OrganizationalStructureID |  |
| PostRef | bigint | Y | → HCM3.Post.PostID |  |
| DepartmentRef | bigint | Y | → HCM3.Department.DepartmentID |  |
| JobRef | bigint | Y | → HCM3.Job.JobID |  |
| WorkLocationCode | int | Y |  | `WorkLocation`: 1=کارخانه آسفالت بم، 2=کارخانه آسفالت عامریه، 3=کارگاه بم-زاهدان-میرجاوه، 4=کارگاه بم - شورگز، 5=کارگاه رستم  آباد-بزمان - ایرانشهر، 6=بم-ریگان-فهرج، 7=بهسازی گل گهر سیرجان، 8=بیمه، 9=پات ، 10=پروژه800متری، 11=پل زیرگذرحسین آبادسیرجان، 12=خرامه - نیریز |
| RankCode | int | Y |  | `Rank`:  |
| BaseCode | int | Y |  | `Base`: 1=1، 2=2، 3=3 |
| Description | nvarchar(max) | Y |  |  |
| Status | int |  |  | `EmployeeStatuteStatus`: 1=ذخیره، 5=تایید کارگزینی، 10=تایید پرداخت |
| ConfirmDate | datetime | Y |  |  |
| ConfirmYearMonth | int | Y |  |  |
| ConfirmerRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| PaymentConfirmDate | datetime | Y |  |  |
| PaymentConfirmerRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| BatchEmployeeStatuteRef | bigint | Y | → HCM3.BatchEmployeeStatute.BatchEmployeeStatuteID |  |
| CorrectiveEmployeeStatuteRef | bigint | Y |  |  |
| EmployeeStatuteRequestRef | bigint | Y | → HCM3.EmployeeStatuteRequest.EmployeeStatuteRequestID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| RetirementDate | datetime | Y |  |  |
| OfficialEmploymentDate | datetime | Y |  |  |
| BonusGroup | int | Y |  | `BonusGroup`:  |
| EstablishmentDocument | int | Y |  | `EstablishmentDocument`:  |
| WorkYears | int | Y |  |  |
| AfterIssueStatusCode | int | Y |  | `EmployeeStatuteAfterIssueStatus`: 1=فعال، 2=غیرفعال، 3=معلق |
| IssueTimeCode | int | Y |  | `EmployeeStatuteIssueTime`: 1=در حین استخدام، 2=در شروع استخدام، 3=در پایان استخدام |
| ApplyConfirmDateSequence | decimal(25,7) |  |  |  |
| ApplyIssueDateSequence | decimal(25,7) |  |  |  |
| ApplyYearMonth | int | Y |  |  |
| IssueYearMonth | int | Y |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |
| Extra3Code | int | Y |  |  |
| Extra4Code | int | Y |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeStatuteFactor`، `HCM3.SettlementCalc`، `HCM3.EmployeeStatuteTempPost`، `HCM3.EmployeeStatuteStateHistory`، `ECM.Correspondent`، `HCM3.EmployeeRetirementFormStatute`

## EmployeeStatuteFactor

`HCM3.EmployeeStatuteFactor` — 263,296 rows — 🟢 تراکنشی فعال

> ⚠️ **حساس**: احکام حقوقی افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeStatuteFactorID | bigint |  | PK |  |
| EmployeeStatuteRef | bigint |  | → HCM3.EmployeeStatute.EmployeeStatuteID |  |
| StatuteFactorPropertyRef | bigint |  | → HCM3.StatuteFactorProperty.StatuteFactorPropertyID |  |
| CalcValue | decimal(28,6) |  |  |  |
| EditedValue | decimal(28,6) | Y |  |  |
| Value | decimal(28,6) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| StatuteFactorRef | bigint |  | → HCM3.StatuteFactor.StatuteFactorID |  |

## EmployeeStatuteStateHistory

`HCM3.EmployeeStatuteStateHistory` — 17,371 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeStatuteStateHistoryID | bigint |  | PK |  |
| EmployeeStatuteRef | bigint |  | → HCM3.EmployeeStatute.EmployeeStatuteID |  |
| AuditorRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| ChangeDate | datetime |  |  |  |
| StatusCode | int |  |  |  |
| Description | nvarchar(500) | Y |  |  |

## EmployeeSupplementary

`HCM3.EmployeeSupplementary` — 1,255 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeSupplementaryID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| Photo | varbinary(max) | Y |  |  |
| Signature | varbinary(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## EmployeeWarriorRecord

`HCM3.EmployeeWarriorRecord` — 10 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmployeeWarriorRecordID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| StatusCode | int | Y |  |  |
| WarPlace | nvarchar(400) | Y |  |  |
| StartDate | datetime | Y |  |  |
| EndDate | datetime | Y |  |  |
| Duration | int | Y |  |  |
| EncouragementGroup | int | Y |  |  |
| ActivityLevelCode | int | Y |  |  |
| EffectiveDate | datetime |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| FileName | nvarchar(512) | Y |  |  |
| FileContents | varbinary(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| WarriorGroupCode | int | Y |  | `WarriorGroup`: 2=جانباز |
| MartyrRelationCode | int | Y |  |  |
| MartyrRelationGradeCode | int | Y |  | `MartyrRelationGrade`:  |
| SacrificePercent | decimal(10,2) | Y |  |  |
| SacrificeExemptionAmount | int | Y |  |  |
| SacrificeLeaveAmountInMonth | int | Y |  |  |
| SacrificeLeaveAmountInYear | int | Y |  |  |
| SacrificeOverworkAmount | int | Y |  |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeRetirementFormWarriorRecord`

## EmploymentType

`HCM3.EmploymentType` — 3 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmploymentTypeID | bigint |  | PK |  |
| RawTitle | nvarchar(400) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Nature | int | Y |  |  |
| WageSystemTypeCode | int | Y |  | `WageSystemType`:  |
| Title | nvarchar(500) |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeStatute`، `HCM3.EmployeeWorkChangeRequest`، `HCM3.PeriodEvaluationStepType`، `HCM3.StatuteTypeFactor`، `HCM3.AttendanceFactorProperty`، `HCM3.EmployeeConditionItem`، `HCM3.EmployeeStatuteReportPattern`، `HCM3.CompensationFactorProperty`، `HCM3.ChangeEmploymentDate`، `HCM3.EmploymentTypeItem`، `HCM3.MissionFactorProperty`، `HCM3.StatuteFactorProperty`، `HCM3.EmployeeWorkRecord`، `HCM3.VoucherSpecificationSLFactor`، `HCM3.LeaveTypeProperty`، `HCM3.StatuteFactorDisplayOrder`، `HCM3.CorrectiveEmployeeStatute`، `HCM3.BatchEmployeeStatute`، `HCM3.CompensationCalcTypeItem`، `HCM3.BatchCorrectiveEmployeeStatute`، `HCM3.EmployeeInfo`

## EmploymentTypeItem

`HCM3.EmploymentTypeItem` — 35 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmploymentTypeItemID | bigint |  | PK |  |
| EmploymentTypeRef | bigint |  | → HCM3.EmploymentType.EmploymentTypeID |  |
| EffectiveYearMonth | int |  |  |  |
| CalendarMonthTypeCode | int |  |  | `CalendarMonthType`: 1=ماه استاندارد |
| WorkMinutes | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## EmpStatuteConvertMapping

`HCM3.EmpStatuteConvertMapping` — 22,264 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EmpStatuteConvertMappingID | bigint |  |  |  |
| RahkaranEmpStatuteID | bigint | Y |  |  |
| DelphiEmpStatuteID | bigint | Y |  |  |

## FactorViewSetting

`HCM3.FactorViewSetting` — 55 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FactorViewSettingID | bigint |  | PK |  |
| FactorViewSettingTypeRef | bigint |  | → HCM3.FactorViewSettingType.FactorViewSettingTypeID |  |
| FactorTypeRef | bigint | Y | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| UserRef | bigint | Y | → SYS3.User.UserID |  |
| Title | nvarchar(250) |  |  |  |
| IsUserLevel | bit |  |  |  |
| IsDefault | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| Definition | nvarchar(max) | Y |  |  |

ارجاع‌شده توسط: `HCM3.SettlementViewSettingInputValue`، `HCM3.FactorViewSettingCompensation`، `HCM3.FactorViewSettingAttendance`

## FactorViewSettingAttendance

`HCM3.FactorViewSettingAttendance` — 11 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FactorViewSettingAttendanceID | bigint |  | PK |  |
| FactorViewSettingRef | bigint |  | → HCM3.FactorViewSetting.FactorViewSettingID |  |
| AttendanceFactorRef | bigint |  | → HCM3.AttendanceFactor.AttendanceFactorID |  |
| Order | int |  |  |  |

## FactorViewSettingCompensation

`HCM3.FactorViewSettingCompensation` — 1,629 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FactorViewSettingCompensationID | bigint |  | PK |  |
| FactorViewSettingRef | bigint |  | → HCM3.FactorViewSetting.FactorViewSettingID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| Order | int |  |  |  |

## FactorViewSettingType

`HCM3.FactorViewSettingType` — 18 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FactorViewSettingTypeID | bigint |  | PK |  |
| Title | nvarchar(250) |  |  |  |
| LevelType | int |  |  |  |
| HasCompensationFactor | bit |  |  |  |
| HasAttendanceFactor | bit |  |  |  |
| HasAllTypeOfCompFactor | bit |  |  |  |
| CalcGroups | int |  |  |  |
| AssignTypes | int |  |  |  |
| Categories | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| CalcType | int |  |  |  |

ارجاع‌شده توسط: `HCM3.FactorViewSetting`

## FileStructure

`HCM3.FileStructure` — 24 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FileStructureID | bigint |  | PK |  |
| Name | varchar(255) |  |  |  |
| Type | varchar(100) |  |  |  |
| Title | nvarchar(200) |  |  |  |
| FileName | nvarchar(200) |  |  |  |
| FieldSeparator | nvarchar(10) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| EncodingType | tinyint |  |  | `EncodingType`: 1=Unicode، 2=UTF8 |
| SubType | int | Y |  |  |

ارجاع‌شده توسط: `HCM3.FileStructureField`، `HCM3.FileCalc`، `HCM3.FileStructureBank`، `HCM3.FileStructureRetirementLoan`، `HCM3.FileStructureRetirement`

## FileStructureField

`HCM3.FileStructureField` — 544 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FileStructureFieldID | bigint |  | PK |  |
| FileStructureRef | bigint |  | → HCM3.FileStructure.FileStructureID |  |
| Name | nvarchar(200) |  |  |  |
| Title | nvarchar(200) |  |  |  |
| DataTypeCode | int |  |  | `FileStructureFieldDataType`: 1=عدد، 2=رشته، 3=تاریخ |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| Order | int |  |  |  |
| LocationCode | int |  |  | `FileStructureFieldLocation`: 1=سرفصل، 2=بدنه، 3=پاورقی |
| AssignTypeCode | int |  |  | `FileStructureFieldAssignType`: 1=محاسباتی، 2=ورودی |
| ZeroFilter | bit |  |  |  |
| DefaultValue | nvarchar(200) | Y |  |  |
| Length | int | Y |  |  |
| Summary | bit |  |  |  |
| Included | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## FinancialStatute

`HCM3.FinancialStatute` — 17,548 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FinancialStatuteID | bigint |  | PK |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| IssueYearMonth | int |  |  |  |
| ApplyYearMonth | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| Value | decimal(28,6) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| IssueDate | datetime |  |  |  |
| ApplyDate | datetime |  |  |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |

## Formula

`HCM3.Formula` — 1,152 rows — ⚪ تنظیمات/ثابت

فرمول‌های محاسبه (کد C#/متن) برای عوامل.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FormulaID | bigint |  | PK |  |
| FormulaBody | nvarchar(max) |  |  |  |
| UIObject | varbinary(max) | Y |  |  |
| ModuleName | varchar(100) | Y |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceFactorProperty`، `HCM3.CompensationFactorProperty`، `HCM3.BatchEmployeeStatuteFactor`، `HCM3.TrainingFactorProperty`، `HCM3.FileStructureField`، `HCM3.PromotionStructureFactor`، `HCM3.MissionFactorProperty`، `HCM3.PerformancePeriodFactorProperty`، `SLS3.CommissionFactorItem`، `HCM3.StatuteFactorProperty`، `HCM3.AppraisalFormItem`، `HCM3.LeaveTypeProperty`، `STM3.FormulaFactorProperty`، `HCM3.AppraisalFormTemplateItem`، `HCM3.TrainingAssessmentFactorProperty`، `HCM3.AppraisalPatternItem`

## FormulaContext

`HCM3.FormulaContext` — 50 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FormulaContextID | bigint |  | PK |  |
| Key | nvarchar(100) |  |  |  |
| XmlObject | xml |  |  |  |

## FormulaContextObject

`HCM3.FormulaContextObject` — 8 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FormulaContextObjectID | bigint |  | PK |  |
| Key | nvarchar(100) |  |  |  |
| AssemblyObject | varbinary(max) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

## HcmTag

`HCM3.HcmTag` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Key | varchar(500) |  |  |  |
| Value | nvarchar(max) |  |  |  |

## InputFileStructure

`HCM3.InputFileStructure` — 15 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InputFileStructureID | bigint |  | PK |  |
| Title | nvarchar(200) |  |  |  |
| Type | varchar(100) |  |  |  |
| DefaultName | nvarchar(200) | Y |  |  |
| FieldSplitter | char(1) | Y |  |  |
| TimeSplitter | char(1) | Y |  |  |
| CodeColumnIndex | int | Y |  |  |
| CodeStartColumnIndex | int | Y |  |  |
| CodeColumnLength | int | Y |  |  |
| DateStartColumnIndex | int | Y |  |  |
| DateColumnIndex | int | Y |  |  |
| CodeCount | int |  |  |  |
| CodeSplitter | char(1) | Y |  |  |
| ConsiderFirstRow | bit | Y |  |  |
| EntityID | bigint | Y |  |  |
| FileFormatCode | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| KeyColumnType | int |  |  | `KeyColumnType`: 1=کد پرسنلی |

ارجاع‌شده توسط: `HCM3.InputFileStructureField`

## InputFileStructureField

`HCM3.InputFileStructureField` — 29 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InputFileStructureFieldID | bigint |  | PK |  |
| InputFileStructureRef | bigint |  | → HCM3.InputFileStructure.InputFileStructureID |  |
| Key | bigint |  |  |  |
| KeyColumnIndex | int | Y |  |  |
| KeyStartColumnIndex | int | Y |  |  |
| KeyColumnLength | int | Y |  |  |
| DayColumnLength | int | Y |  |  |
| HourColumnLength | int | Y |  |  |
| MinuteColumnLength | int | Y |  |  |

## Job

`HCM3.Job` — 790 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| JobID | bigint |  | PK |  |
| ParentRef | bigint | Y | → HCM3.Job.JobID |  |
| NextJobRef | bigint | Y | → HCM3.Job.JobID |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(400) |  |  |  |
| ClassCode | int |  |  | `JobClass`: 1=رسته شغلی پیش فرض - عمومی |
| JobRankNumber | int | Y |  |  |
| GroupCode | int | Y |  | `JobGroup`: 1=1، 2=10، 3=11، 4=12، 5=13، 6=14، 7=15، 8=16، 9=17، 10=18، 11=19، 12=2 |
| Senior | bit | Y |  |  |
| InsuranceCode | nvarchar(50) | Y |  |  |
| Description | nvarchar(max) | Y |  |  |
| ExtraDescription | nvarchar(max) | Y |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeWorkChangeRequest`، `HCM3.EmployeeStatute`، `HCM3.JobQualification`، `HCM3.JobDuty`، `HCM3.JobCompetency`، `HCM3.PostJob`، `HCM3.Job`، `HCM3.EmployeeWorkRecord`، `HCM3.CorrectiveEmployeeStatute`، `HCM3.JobCourse`، `HCM3.BatchEmployeeStatute`، `HCM3.BatchCorrectiveEmployeeStatute`، `HCM3.EmployeeInfo`

## LeaveRemainder

`HCM3.LeaveRemainder` — 1,975 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LeaveRemainderID | bigint |  | PK |  |
| TypeCode | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| LeaveTypeRef | bigint |  | → HCM3.LeaveType.LeaveTypeID |  |
| LeaveTypePropertyRef | bigint | Y |  |  |
| EffectiveYearMonth | int |  |  |  |
| Value | int |  |  |  |
| IsTemporary | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| IsDeployedRemaining | bit |  |  |  |
| Description | nvarchar(500) | Y |  |  |
| IsInactive | bit |  |  |  |
| EffectiveDate | datetime |  |  |  |

## LeaveType

`HCM3.LeaveType` — 1 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LeaveTypeID | bigint |  | PK |  |
| Code | nvarchar(20) | Y |  |  |
| Title | nvarchar(400) |  |  |  |
| CategoryCode | int |  |  |  |
| MeasurementUnitCode | int |  |  |  |
| ScaleCode | int |  |  |  |
| Redeemable | bit |  |  |  |
| DefaultInRequest | bit |  |  |  |
| HasSecondConfirmation | bit |  |  |  |
| SecondConfirmMaxDays | int |  |  |  |
| HasThirdConfirmation | bit |  |  |  |
| ThirdConfirmerRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| VisibleInSelfService | bit |  |  |  |
| DelegationRequired | bit |  |  |  |
| EmploymentTypeVisible | bit |  |  |  |
| WorkingGroupVisible | bit |  |  |  |
| WorkLocationVisible | bit |  |  |  |
| BranchVisible | bit |  |  |  |
| Status | int |  |  | `Status`: 1=فعال |

ارجاع‌شده توسط: `HCM3.LeaveTypePostExclude`، `HCM3.LeaveRemainder`، `HCM3.NegativeRemainderRequest`، `HCM3.LeaveTypeProperty`، `HCM3.LeaveRemainderHistory`، `HCM3.LeaveRequest`، `HCM3.LeaveTypeAttendanceStatus`

## LeaveTypeProperty

`HCM3.LeaveTypeProperty` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LeaveTypePropertyID | bigint |  | PK |  |
| LeaveTypeRef | bigint |  | → HCM3.LeaveType.LeaveTypeID |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| WorkingGroupRef | bigint | Y | → HCM3.WorkingGroup.WorkingGroupID |  |
| WorkLocationCode | int | Y |  | `WorkLocation`:  |
| BranchRef | bigint | Y | → GNR3.Branch.BranchID |  |
| ApplyYearMonth | int |  |  |  |
| EntitlementDays | int |  |  |  |
| EntitlementHours | int |  |  |  |
| EntitlementMinutes | int |  |  |  |
| MaxAnnualTransferDays | int |  |  |  |
| MaxAnnualTransferHours | int |  |  |  |
| MaxAnnualTransferMinutes | int |  |  |  |
| MaxMonthlyTransferDays | int |  |  |  |
| MaxMonthlyTransferHours | int |  |  |  |
| MaxMonthlyTransferMinutes | int |  |  |  |
| ConsiderEmployeeSacrificeStatus | bit |  |  |  |
| MaxHourlyDurationInYearOrMonthDays | int | Y |  |  |
| MaxHourlyDurationInYearOrMonthHours | int | Y |  |  |
| MaxHourlyDurationInYearOrMonthMinutes | int | Y |  |  |
| MaxHourlyDurationInDay | int | Y |  |  |
| MaxHourlyCountInMonth | int | Y |  |  |
| Status | bit |  |  |  |
| HasFormula | bit |  |  |  |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| EntitlementAssignMethodCode | int |  |  |  |
| LeaveInsertionTypeCode | int |  |  |  |
| NegativeRemainType | int |  |  | `NegativeRemainType`: 4=نامحدود |
| MaxNegativeDay | int |  |  |  |
| MaxNegativeHour | int |  |  |  |
| MaxNegativeMinute | int |  |  |  |
| AccomulateAnnualRemains | bit |  |  |  |
| AutomaticCalculable | bit |  |  |  |

ارجاع‌شده توسط: `HCM3.LeaveRequest`

## LoanAdjustment

`HCM3.LoanAdjustment` — 11 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LoanAdjustmentID | bigint |  | PK |  |
| LoanPaymentRef | bigint |  | → HCM3.LoanPayment.LoanPaymentID |  |
| Percent | float |  |  |  |
| Amount | decimal(28,6) |  |  |  |
| Duration | int |  |  |  |
| EffectiveYearMonth | int |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## LoanInstalment

`HCM3.LoanInstalment` — 10,736 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LoanInstalmentID | bigint |  | PK |  |
| LoanPaymentRef | bigint |  | → HCM3.LoanPayment.LoanPaymentID |  |
| PaymentYearMonth | int |  |  |  |
| Amount | decimal(28,6) |  |  |  |
| PaymentMethodCode | int |  |  | `LoanInstalmentPaymentMethod`: 0=سیستمی، 1=دستی |
| Description | nvarchar(max) | Y |  |  |

## LoanPayment

`HCM3.LoanPayment` — 5,758 rows — 🟢 تراکنشی فعال

وام/مساعده‌ی پرداختی به کارکنان؛ LoanInstalment اقساط.

> ⚠️ **حساس**: وام افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LoanPaymentID | bigint |  | PK |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| LoanTypeRef | bigint |  | → HCM3.LoanType.LoanTypeID |  |
| LoanAmount | decimal(28,6) |  |  |  |
| InstalmentQuantity | int |  |  |  |
| InstalmentAmount | decimal(28,6) |  |  |  |
| ExtraAmount | decimal(28,6) |  |  |  |
| ExtraPaymentMethodCode | int | Y |  |  |
| DeploymentRemainder | decimal(28,6) |  |  |  |
| Remainder | decimal(28,6) |  |  |  |
| LoanNumber | nvarchar(50) | Y |  |  |
| ConfirmerEmployeeRef | bigint | Y | → HCM3.Employee.EmployeeID |  |
| ConfirmationDate | datetime | Y |  |  |
| VerificationDate | datetime | Y |  |  |
| ConfirmedPaymentDate | datetime | Y |  |  |
| PaymentDate | datetime |  |  |  |
| InstalmentDueYearMonth | int |  |  |  |
| Status | int |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.LoanSuretyDocument`، `HCM3.LoanSurety`، `HCM3.LoanAdjustment`، `HCM3.LoanInstalment`

## LoanType

`HCM3.LoanType` — 10 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LoanTypeID | bigint |  | PK |  |
| Title | nvarchar(400) |  |  |  |
| MaxAmount | decimal(28,6) |  |  |  |
| InstallmentAmount | decimal(28,6) |  |  |  |
| Cumulative | bit |  |  |  |
| VisibleInForm | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.LoanTypeDL`، `HCM3.RetirementReceiptReportSettingLoanType`، `HCM3.LoanPayment`، `HCM3.FileStructureRetirementLoan`، `HCM3.TransferVoucherSpecificationSLLoan`، `HCM3.VoucherSpecificationSLLoan`

## LocalSyncDataPartition

`HCM3.LocalSyncDataPartition` — 14 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LocalSyncDataPartitionID | bigint |  | PK |  |
| StartEntityID | bigint |  |  |  |
| EndEntityID | bigint |  |  |  |
| EntityName | varchar(50) |  |  |  |

ارجاع‌شده توسط: `HCM3.LocalSyncSiteStatus`، `HCM3.EmployeeLocalSyncData`

## MajorJobClass

`HCM3.MajorJobClass` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MajorJobClassID | bigint |  | PK |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(400) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MajorJobClassItem`

## Mapping

`HCM3.Mapping` — 10 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingID | bigint |  | PK |  |
| Title | nvarchar(255) |  |  |  |
| MappingStructureRef | bigint |  | → HCM3.MappingStructure.MappingStructureID |  |
| Status | bit |  |  |  |
| ActivationDate | datetime | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MappingOutput`، `HCM3.MappingInput`

## MappingInput

`HCM3.MappingInput` — 399 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingInputID | bigint |  | PK |  |
| MappingRef | bigint |  | → HCM3.Mapping.MappingID |  |
| MappingStructureInputRef | bigint |  | → HCM3.MappingStructureInput.MappingStructureInputID |  |
| RowNumber | bigint |  |  |  |
| FromValue | nvarchar(255) |  |  |  |
| ToValue | nvarchar(255) | Y |  |  |
| Order | int |  |  |  |
| Type | int |  |  |  |
| InputMethod | int | Y |  |  |
| TransformedFromValue | int | Y |  |  |
| TransformedToValue | int | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## MappingOutput

`HCM3.MappingOutput` — 679 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingOutputID | bigint |  | PK |  |
| MappingRef | bigint |  | → HCM3.Mapping.MappingID |  |
| MappingStructureOutputRef | bigint |  | → HCM3.MappingStructureOutput.MappingStructureOutputID |  |
| RowNumber | bigint |  |  |  |
| Value | nvarchar(255) |  |  |  |
| Order | int |  |  |  |
| Type | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## MappingStructure

`HCM3.MappingStructure` — 26 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingStructureID | bigint |  | PK |  |
| Title | nvarchar(255) |  |  |  |
| Name | nvarchar(255) |  |  |  |
| BySystem | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MappingStructureOutput`، `HCM3.MappingStructureInput`، `HCM3.Mapping`

## MappingStructureInput

`HCM3.MappingStructureInput` — 62 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingStructureInputID | bigint |  | PK |  |
| MappingStructureRef | bigint |  | → HCM3.MappingStructure.MappingStructureID |  |
| Title | nvarchar(255) |  |  |  |
| Type | int |  |  |  |
| InputMethod | int | Y |  |  |
| FieldType | nvarchar(30) | Y |  |  |
| EntityField | nvarchar(255) | Y |  |  |
| Order | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MappingInput`

## MappingStructureOutput

`HCM3.MappingStructureOutput` — 30 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MappingStructureOutputID | bigint |  | PK |  |
| MappingStructureRef | bigint |  | → HCM3.MappingStructure.MappingStructureID |  |
| Title | nvarchar(255) |  |  |  |
| Type | int |  |  | `MappingStructureOutputType`: 1=موجودیت، 2=کد و شرحی، 3=عدد، 4=رشته |
| FieldType | nvarchar(30) | Y |  |  |
| EntityField | nvarchar(255) | Y |  |  |
| Order | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MappingOutput`

## MonthlyFactorData

`HCM3.MonthlyFactorData` — 78,222 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MonthlyFactorDataID | bigint |  | PK |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| IssueYearMonth | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.MonthlyFactorDataCompensationItem`، `HCM3.WGSalaryReceipt`، `HCM3.PYSalaryReceipt`

## MonthlyFactorDataCompensationItem

`HCM3.MonthlyFactorDataCompensationItem` — 248,358 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MonthlyFactorDataCompensationItemID | bigint |  | PK |  |
| MonthlyFactorDataRef | bigint |  | → HCM3.MonthlyFactorData.MonthlyFactorDataID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| CompensationFactorPropertyRef | bigint |  | → HCM3.CompensationFactorProperty.CompensationFactorPropertyID |  |
| ApplyYearMonth | int |  |  |  |
| Value | decimal(28,6) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| IssueYearMonth | int |  |  |  |
| EmployeeRef | bigint |  |  |  |
| CompensationCalcTypeRef | bigint |  |  |  |

## Organization

`HCM3.Organization` — 3 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| OrganizationID | bigint |  | PK |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(200) |  |  |  |
| TypeCode | int |  |  | `OrganizationType`: 1=بیمه تامین اجتماعی، 2=مالیات |
| MandatoryEmployeeRelatedCode | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Nature | int |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeInfo`، `HCM3.EmployeeWorkChangeRequest`، `HCM3.EmployeeRelatedOrganization`، `HCM3.EmployeeRelativeInsurance`، `HCM3.OrganizationCompensationFactor`، `HCM3.OrganizationBranch`، `HCM3.EmployeeWorkRecord`، `HCM3.CompensationInsurance`

## OrganizationBranch

`HCM3.OrganizationBranch` — 32 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| OrganizationBranchID | bigint |  | PK |  |
| OrganizationRef | bigint |  | → HCM3.Organization.OrganizationID |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| Code | nvarchar(100) | Y |  |  |
| IsDefault | bit |  |  |  |
| ContainsEmployerExemption | bit |  |  |  |
| ExemptionQuantity | int | Y |  |  |
| IsInsuranceContractCodeAware | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeInfo`، `HCM3.EmployeeRelatedOrganization`، `HCM3.EmployerExemptionException`

## OrganizationCompensationFactor

`HCM3.OrganizationCompensationFactor` — 52 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| OrganizationCompensationFactorID | bigint |  | PK |  |
| OrganizationRef | bigint |  | → HCM3.Organization.OrganizationID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## PayCalc

`HCM3.PayCalc` — 82,446 rows — 🟢 تراکنشی فعال

محاسبه‌ی حقوق ماهانه هر کارمند؛ IssueYearMonth جلالی (YYYYMM).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PayCalcID | bigint |  | PK |  |
| IssueYearMonth | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.PayCalcItem`

## PayCalcItem

`HCM3.PayCalcItem` — 3,453,700 rows — 🟢 تراکنشی فعال

مقادیر عوامل حقوقی هر محاسبه؛ CompensationFactorRef=63 خالص پرداختی، 55 قابل پرداخت، 62 جمع کسور، 61 جمع مزایا. حساس.

> ⚠️ **حساس**: حقوق افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PayCalcItemID | bigint |  | PK |  |
| PayCalcRef | bigint |  | → HCM3.PayCalc.PayCalcID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| CompensationFactorPropertyRef | bigint |  | → HCM3.CompensationFactorProperty.CompensationFactorPropertyID |  |
| ApplyYearMonth | int |  |  |  |
| Value | decimal(28,6) |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| IssueYearMonth | int |  |  |  |

## PeriodicCalc

`HCM3.PeriodicCalc` — 73,819 rows — 🟢 تراکنشی فعال

محاسبات دوره‌ای (عیدی، بازخرید...) به‌تفکیک CompensationCalcType.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PeriodicCalcID | bigint |  | PK |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |
| SubTypeCode | int |  |  |  |
| IssueYearMonth | int |  |  |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.PeriodicCalcItem`

## PeriodicCalcItem

`HCM3.PeriodicCalcItem` — 790,606 rows — 🟢 تراکنشی فعال

> ⚠️ **حساس**: حقوق افراد

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PeriodicCalcItemID | bigint |  | PK |  |
| PeriodicCalcRef | bigint |  | → HCM3.PeriodicCalc.PeriodicCalcID |  |
| CompensationFactorPropertyRef | bigint |  | → HCM3.CompensationFactorProperty.CompensationFactorPropertyID |  |
| Value | decimal(28,6) |  |  |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| EmployeeRef | bigint |  |  |  |
| IssueYearMonth | int |  |  |  |

## Post

`HCM3.Post` — 359 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PostID | bigint |  | PK |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(400) |  |  |  |
| LevelCode | int | Y |  | `PostLevel`:  |
| ManagementLevelCode | int | Y |  | `ManagementLevel`: 1=عادی |
| TypeCode | int | Y |  | `PostType`: 1=اصلی |
| OccupationStatusCode | int | Y |  | `PostOccupationStatus`:  |
| RegionalDivisionTypeCode | int | Y |  | `RegionalDivisionType`:  |
| Capacity | int | Y |  |  |
| MaxOccupationDuration | int | Y |  |  |
| Qualification | nvarchar(max) | Y |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| StatusChangeDate | datetime | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| UniqueCode | nvarchar(100) | Y |  |  |
| RegionalDivisionRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| Extra1Code | int | Y |  |  |
| Extra2Code | int | Y |  |  |
| AbbrName | nvarchar(50) | Y |  |  |
| FormalName | nvarchar(400) | Y |  |  |
| Extra3Code | int | Y |  |  |
| Extra4Code | int | Y |  |  |
| Extra5Code | int | Y |  |  |
| SecondLanguageTitle | nvarchar(200) | Y |  |  |

ارجاع‌شده توسط: `HCM3.LeaveTypePostExclude`، `HCM3.EmployeeRetirementForm30`، `HCM3.EmployeeWorkChangeRequest`، `HCM3.PeriodEvaluationStepType`، `HCM3.EmployeeStatute`، `HCM3.EmployeeConditionItem`، `HCM3.PostJob`، `HCM3.EmployeeStatuteTempPost`، `HCM3.MandatoryDistributionStructureItem`، `HCM3.EmployeeWorkRecord`، `ECM.Correspondent`، `ECM.Letter`، `HCM3.PostDuty`، `HCM3.PostCompetency`، `HCM3.PostAuthority`، `HCM3.CorrectiveEmployeeStatute`، `HCM3.PostCourse`، `HCM3.OrganizationalStructure`، `HCM3.BatchEmployeeStatute`، `HCM3.PostQualification`، `HCM3.BatchCorrectiveEmployeeStatute`، `HCM3.EmployeeInfo`

## PostJob

`HCM3.PostJob` — 264 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PostJobID | bigint |  | PK |  |
| PostRef | bigint |  | → HCM3.Post.PostID |  |
| JobRef | bigint |  | → HCM3.Job.JobID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## ReportSetting

`HCM3.ReportSetting` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportSettingID | bigint |  | PK |  |
| Title | nvarchar(255) |  |  |  |
| IsDefault | bit |  |  |  |
| Type | int |  |  | `ReportSettingType`: 1=حقوق |
| ReportType | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |

ارجاع‌شده توسط: `HCM3.ReportSettingItem`، `HCM3.RetirementReceiptReportSetting`، `HCM3.TreasuryReportSetting`، `HCM3.Tabsare21ReportSetting`، `HCM3.RetirementReportSetting`، `HCM3.Retirement123FormReportSetting`، `HCM3.EmployeeRetirementForm`

## ReportSettingCompensationFactor

`HCM3.ReportSettingCompensationFactor` — 26 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportSettingCompensationFactorID | bigint |  | PK |  |
| ReportSettingItemRef | bigint |  | → HCM3.ReportSettingItem.ReportSettingItemID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| DisplayTitle | nvarchar(400) | Y |  |  |
| Order | int |  |  |  |

## ReportSettingItem

`HCM3.ReportSettingItem` — 26 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportSettingItemID | bigint |  | PK |  |
| ReportSettingRef | bigint |  | → HCM3.ReportSetting.ReportSettingID |  |
| Title | nvarchar(500) |  |  |  |
| Name | nvarchar(500) | Y |  |  |
| Nature | int |  |  |  |
| Extra | int | Y |  |  |
| Order | int |  |  |  |
| FactorType | int |  |  |  |

ارجاع‌شده توسط: `HCM3.ReportSettingCompensationFactor`، `HCM3.ReportSettingStatuteFactor`، `HCM3.ReportSettingAttendanceFactor`

## RfidDeviceSdk

`HCM3.RfidDeviceSdk` — 10 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RfidDeviceSdkID | bigint |  | PK |  |
| Key | nvarchar(250) | Y |  |  |
| Title | nvarchar(500) | Y |  |  |
| DefaultPort | nvarchar(5) | Y |  |  |
| IsIndexMandatory | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.RfidDevice`

## RfidLocalLogicalResource

`HCM3.RfidLocalLogicalResource` — 14 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RfidLocalLogicalResourceID | bigint |  | PK |  |
| Key | nvarchar(500) |  |  |  |
| Name | nvarchar(500) |  |  |  |
| ParentRef | bigint | Y | → HCM3.RfidLocalLogicalResource.RfidLocalLogicalResourceID |  |

ارجاع‌شده توسط: `HCM3.RfidLocalSecurityPolicy`، `HCM3.RfidLocalLogicalResource`

## SelfServiceLinkAccess

`HCM3.SelfServiceLinkAccess` — 3 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SelfServiceLinkAccessID | bigint |  | PK |  |
| ActorRef | bigint |  |  |  |
| ActorTypeCode | int |  |  |  |
| RevertToParent | bit |  |  |  |
| ChangeAddress | bit |  |  |  |
| EmployeeInfoChangeRequest | bit |  |  |  |
| EmployeeStatute | bit |  |  |  |
| LeaveRequest | bit |  |  |  |
| LeaveCardex | bit |  |  |  |
| MissionDocument | bit |  |  |  |
| AttendanceDataCorrectionRequest | bit |  |  |  |
| AttendancePermissionRequest | bit |  |  |  |
| AttendancePermission | bit |  |  |  |
| WorkingGroupChangeRequest | bit |  |  |  |
| AttendanceStatus | bit |  |  |  |
| ReviewAttendanceCalc | bit |  |  |  |
| SalaryReceipt | bit |  |  |  |
| PeriodicCalcReceipt | bit |  |  |  |
| UserDefinedCalcReceipt | bit |  |  |  |
| ReviewCompensation | bit |  |  |  |
| CourseRequest | bit |  |  |  |
| TrainingRecords | bit |  |  |  |
| DailyCalc | bit |  |  |  |
| ReportExplorer | bit |  |  |  |
| AppraisalForm | bit |  |  |  |
| EmployeeAppraisalWorkbookReport | bit |  |  |  |
| TrainingAppraisalForm | bit |  |  |  |
| ManagerBatchOperation | bit |  |  |  |
| ManagerEmployeeInfoChangeRequest | bit |  |  |  |
| ManagerEmployeeStatute | bit |  |  |  |
| ManagerLeaveRequest | bit |  |  |  |
| ManagerLeaveCardex | bit |  |  |  |
| ManagerMissionDocument | bit |  |  |  |
| ManagerAttendanceDataCorrectionRequest | bit |  |  |  |
| ManagerAttendancePermissionRequest | bit |  |  |  |
| BatchAttendancePermission | bit |  |  |  |
| ManagerAttendancePermission | bit |  |  |  |
| ManagerWorkingGroupChangeRequest | bit |  |  |  |
| ManagerAttendanceStatus | bit |  |  |  |
| ManagerReviewAttendanceCalc | bit |  |  |  |
| ManagerSalaryReceipt | bit |  |  |  |
| ManagerPeriodicCalcReceipt | bit |  |  |  |
| ManagerUserDefinedCalcReceipt | bit |  |  |  |
| ManagerReviewCompensation | bit |  |  |  |
| ManagerCourseRequest | bit |  |  |  |
| ManagerTrainingRecords | bit |  |  |  |
| ManagerEmployeeAppraisalWorkbookReport | bit |  |  |  |
| ManagerAppraisalForm | bit |  |  |  |
| ManagerTrainingAppraisalForm | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| ManagerBatchAttendanceStatus | bit |  |  |  |
| WorkingGroupOrganizing | bit |  |  |  |
| WorkingGroupOrganizingHistory | bit |  |  |  |
| AttendanceEventsList | bit |  |  |  |
| DailyAttendanceDataManagement | bit |  |  |  |
| DailyAttendanceDataCalculation | bit |  |  |  |
| CourseRegistration | bit |  |  |  |
| TrainingCalendar | bit |  |  |  |
| ManagerWorkingGroupOrganizing | bit |  |  |  |
| ManagerWorkingGroupOrganizingHistory | bit |  |  |  |
| ManagerDailyAttendanceDataManagement | bit |  |  |  |
| ManagerDailyAttendanceDataCalculation | bit |  |  |  |
| ManagerCourseRegistration | bit |  |  |  |
| ManagerTrainingCalendar | bit |  |  |  |
| PerformanceAgreement | bit |  |  |  |
| AppraisalQuestionnaire | bit |  |  |  |
| MyPerformanceProfile | bit |  |  |  |
| ManagerPerformanceDashboard | bit |  |  |  |
| ManagerPerformanceAgreement | bit |  |  |  |
| ManagerAppraisalReview | bit |  |  |  |
| ManagerAppraisalQuestionnaire | bit |  |  |  |
| ManagerViewAppraisalQuestionnaire | bit |  |  |  |
| NewsList | bit |  |  |  |

## SettlementViewSettingInputValue

`HCM3.SettlementViewSettingInputValue` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementViewSettingInputValueID | bigint |  | PK |  |
| FactorViewSettingRef | bigint |  | → HCM3.FactorViewSetting.FactorViewSettingID |  |
| ReportDescription | nvarchar(500) | Y |  |  |
| ShebaOrAccountNumber | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |

## StatuteFactor

`HCM3.StatuteFactor` — 27 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteFactorID | bigint |  | PK |  |
| Name | varchar(255) |  |  |  |
| Title | nvarchar(400) |  |  |  |
| PeriodCode | int |  |  | `StatuteFactorPeriod`: 1=ماهانه |
| TypeCode | int |  |  | `StatuteFactorType`: 1=اصلی، 2=فرعی |
| Description | nvarchar(max) | Y |  |  |
| VisibleInStatute | bit |  |  |  |
| VisibleInEmployee | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| RelatedStatuteTypeCode | int |  |  | `StatuteFactorRelatedStatuteType`: 1=حین خدمت |

ارجاع‌شده توسط: `HCM3.StatuteTypeFactor`، `HCM3.EmployeeStatuteFactor`، `HCM3.BatchEmployeeStatuteFactor`، `HCM3.EmployeeStatuteReportPatternFactor`، `HCM3.CorrectiveEmployeeStatuteFactor`، `HCM3.BatchCorrectiveEmployeeStatuteFactor`، `HCM3.ReportSettingStatuteFactor`، `HCM3.StatuteFactorProperty`، `HCM3.StatuteFactorDisplayOrder`

## StatuteFactorDisplayOrder

`HCM3.StatuteFactorDisplayOrder` — 51 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteFactorDisplayOrderID | bigint |  | PK |  |
| StatuteFactorRef | bigint |  | → HCM3.StatuteFactor.StatuteFactorID |  |
| EmploymentTypeRef | bigint |  | → HCM3.EmploymentType.EmploymentTypeID |  |
| DisplayOrder | int |  |  |  |

## StatuteFactorProperty

`HCM3.StatuteFactorProperty` — 94 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteFactorPropertyID | bigint |  | PK |  |
| StatuteFactorRef | bigint |  | → HCM3.StatuteFactor.StatuteFactorID |  |
| EmploymentTypeRef | bigint |  | → HCM3.EmploymentType.EmploymentTypeID |  |
| IssueYearMonth | int |  |  |  |
| ApplyYearMonth | int |  |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| FormulaRef | bigint | Y | → HCM3.Formula.FormulaID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeStatuteFactor`

## StatuteType

`HCM3.StatuteType` — 13 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteTypeID | bigint |  | PK |  |
| Code | nvarchar(100) | Y |  |  |
| Title | nvarchar(400) |  |  |  |
| IssueTimeCode | int |  |  |  |
| AfterIssueStatusCode | int |  |  |  |
| PostSelectionTypeCode | int |  |  |  |
| DefaultDescription | nvarchar(max) | Y |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| TempPostSelectionTypeCode | int |  |  |  |
| RelatedStatuteTypeCode | int |  |  |  |
| StartStatuteTypeRef | bigint | Y | → HCM3.StatuteType.StatuteTypeID |  |
| CorrectiveStatuteDisplayTitle | nvarchar(400) | Y |  |  |

ارجاع‌شده توسط: `HCM3.StatuteTypeParameter`، `HCM3.EmployeeStatute`، `HCM3.StatuteTypeFactor`، `HCM3.PromotionStructure`، `HCM3.StatuteType`، `HCM3.EmployeeStatuteRequest`، `HCM3.Retirement123FormReportSettingStatuteType`، `HCM3.CorrectiveEmployeeStatute`، `HCM3.BatchEmployeeStatute`، `HCM3.BatchCorrectiveEmployeeStatute`، `HCM3.EmployeeInfo`

## StatuteTypeFactor

`HCM3.StatuteTypeFactor` — 676 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteTypeFactorID | bigint |  | PK |  |
| StatuteTypeRef | bigint |  | → HCM3.StatuteType.StatuteTypeID |  |
| EmploymentTypeRef | bigint |  | → HCM3.EmploymentType.EmploymentTypeID |  |
| StatuteFactorRef | bigint |  | → HCM3.StatuteFactor.StatuteFactorID |  |
| Editable | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## StatuteTypeParameter

`HCM3.StatuteTypeParameter` — 157 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StatuteTypeParameterID | bigint |  | PK |  |
| StatuteTypeRef | bigint |  | → HCM3.StatuteType.StatuteTypeID |  |
| TypeCode | int |  |  |  |
| Editable | bit |  |  |  |
| SetMethodCode | int |  |  | `StatuteTypeParameterSetMethod`: 2=مقدار حکم قبلی |
| Required | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## StrategicObjectiveType

`HCM3.StrategicObjectiveType` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StrategicObjectiveTypeID | bigint |  | PK |  |
| Title | nvarchar(400) |  |  |  |
| Number | nvarchar(400) |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Systemic | bit | Y |  |  |

ارجاع‌شده توسط: `HCM3.StrategicObjectiveItem`

## TaxTable

`HCM3.TaxTable` — 37 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TaxTableID | bigint |  | PK |  |
| Title | nvarchar(400) |  |  |  |
| EffectiveYearMonth | int |  |  |  |
| TaxGroupCode | int |  |  | `TaxGroup`: 1=100%، 2=50% |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| TaxType | int |  |  | `TaxType`: 1=حقوق |

ارجاع‌شده توسط: `HCM3.TaxTableItem`

## TaxTableItem

`HCM3.TaxTableItem` — 183 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TaxTableItemID | bigint |  | PK |  |
| TaxTableRef | bigint |  | → HCM3.TaxTable.TaxTableID |  |
| FromValue | decimal(28,6) |  |  |  |
| ToValue | decimal(28,6) |  |  |  |
| Coefficient | float |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## Voucher

`HCM3.Voucher` — 272 rows — 🟢 تراکنشی فعال

ارتباط محاسبه‌ی حقوق با سند حسابداری (VoucherRef → FIN3.Voucher).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherID | bigint |  | PK |  |
| VoucherSpecificationRef | bigint |  | → HCM3.VoucherSpecification.VoucherSpecificationID |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| VoucherDate | datetime |  |  |  |
| IssueYearMonth | int |  |  |  |
| Number | nvarchar(100) | Y |  |  |
| Description | nvarchar(max) | Y |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| ExportingMethodCode | int |  |  |  |
| HasSharing | bit |  |  |  |
| VoucherInsuranceBranchesTitle | nvarchar(max) | Y |  |  |
| VoucherBranchesTitle | nvarchar(max) | Y |  |  |
| VoucherInsuranceContractsCode | nvarchar(max) | Y |  |  |

ارجاع‌شده توسط: `HCM3.VoucherInsuranceBranch`، `HCM3.VoucherBranch`، `HCM3.VoucherEmployee`

## VoucherEmployee

`HCM3.VoucherEmployee` — 106,737 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherEmployeeID | bigint |  | PK |  |
| VoucherRef | bigint |  | → HCM3.Voucher.VoucherID |  |
| EmployeeRef | bigint |  | → HCM3.Employee.EmployeeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## VoucherSpecification

`HCM3.VoucherSpecification` — 48 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationID | bigint |  | PK |  |
| Code | int |  |  |  |
| Title | nvarchar(255) |  |  |  |
| CompensationCalcSubTypeCode | int | Y |  | `CompensationCalcSubType`: 1=ذخیره، 2=پرداخت |
| IsDefault | bit |  |  |  |
| AllowFixedDLs | bit |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Status | int |  |  |  |

ارجاع‌شده توسط: `HCM3.Voucher`، `HCM3.VoucherSpecificationCalcType`، `HCM3.VoucherSpecificationSL`

## VoucherSpecificationCalcType

`HCM3.VoucherSpecificationCalcType` — 48 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationCalcTypeID | bigint |  | PK |  |
| VoucherSpecificationRef | bigint |  | → HCM3.VoucherSpecification.VoucherSpecificationID |  |
| CompensationCalcTypeRef | bigint |  | → HCM3.CompensationCalcType.CompensationCalcTypeID |  |

## VoucherSpecificationSL

`HCM3.VoucherSpecificationSL` — 877 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationSLID | bigint |  | PK |  |
| VoucherSpecificationRef | bigint |  | → HCM3.VoucherSpecification.VoucherSpecificationID |  |
| SLRef | bigint |  | → FIN3.SL.SLID |  |
| Description | nvarchar(255) |  |  |  |
| NatureCode | int |  |  | `VoucherSpecificationSLNature`: 1=بدهکار، 2=بستانکار |
| DLTypeRef4 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef5 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef6 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef7 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef8 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef9 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLCode4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Order | int |  |  |  |
| DLTypeRef10 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef11 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef12 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef13 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef14 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef15 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef16 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef17 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef18 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef19 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef20 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLCode10 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode11 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode12 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode13 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode14 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode15 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode16 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode17 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode18 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode19 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLCode20 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| RelatedDLStatus | int |  |  | `VoucherSpecificationSLRelatedDLStatus`: 2=خارج شده |

ارجاع‌شده توسط: `HCM3.VoucherSpecificationSLRelatedDL`، `HCM3.VoucherSpecificationSLFactor`، `HCM3.VoucherSpecificationSLLoan`، `HCM3.CompensationPaymentRequest`

## VoucherSpecificationSLFactor

`HCM3.VoucherSpecificationSLFactor` — 3,416 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationSLFactorID | bigint |  | PK |  |
| VoucherSpecificationSLRef | bigint |  | → HCM3.VoucherSpecificationSL.VoucherSpecificationSLID |  |
| CompensationFactorRef | bigint |  | → HCM3.CompensationFactor.CompensationFactorID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| EmploymentTypeRef | bigint | Y | → HCM3.EmploymentType.EmploymentTypeID |  |
| ExportingMethodCode | int |  |  |  |

## VoucherSpecificationSLLoan

`HCM3.VoucherSpecificationSLLoan` — 96 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationSLLoanID | bigint |  | PK |  |
| VoucherSpecificationSLRef | bigint |  | → HCM3.VoucherSpecificationSL.VoucherSpecificationSLID |  |
| LoanTypeRef | bigint |  | → HCM3.LoanType.LoanTypeID |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |

## VoucherSpecificationSLRelatedDL

`HCM3.VoucherSpecificationSLRelatedDL` — 112,904 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherSpecificationSLRelatedDLID | bigint |  | PK |  |
| VoucherSpecificationSLRef | bigint |  | → HCM3.VoucherSpecificationSL.VoucherSpecificationSLID |  |
| DLRef | bigint |  |  |  |
| DLCode | nvarchar(64) |  | → FIN3.DL.Code |  |
| Status | int |  |  | `Status`: 2=غیر فعال |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
