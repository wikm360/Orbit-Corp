# Schema `FIN3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AccountGroup](#accountgroup) | 12 | 10 | 🔵 اطلاعات پایه فعال | گروه حساب (11 دارایی جاری ... 91/92 انتظامی). |
| [AccountingDepartment](#accountingdepartment) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [AccountMapping](#accountmapping) | 616 | 18 | ⚪ تنظیمات/ثابت |  |
| [AccountType](#accounttype) | 1 | 7 | ⚪ تنظیمات/ثابت |  |
| [AgingReceivableSetting](#agingreceivablesetting) | 38 | 19 | ⚪ تنظیمات/ثابت |  |
| [Analyse](#analyse) | 1 | 7 | ⚪ تنظیمات/ثابت |  |
| [ClosingVoucherClosableSL](#closingvoucherclosablesl) | 1,455 | 42 | ⚪ تنظیمات/ثابت |  |
| [ClosingVoucherCounterPartSL](#closingvouchercounterpartsl) | 7 | 25 | ⚪ تنظیمات/ثابت |  |
| [ClosingVoucherPattern](#closingvoucherpattern) | 7 | 11 | ⚪ تنظیمات/ثابت |  |
| [ClosingVoucherReferences](#closingvoucherreferences) | 6 | 7 | ⚪ تنظیمات/ثابت |  |
| [COAGrouping](#coagrouping) | 1 | 7 | ⚪ تنظیمات/ثابت |  |
| [CodingStandard](#codingstandard) | 10 | 7 | ⚪ تنظیمات/ثابت | استاندارد کدینگ سنا/سناما؛ جدول‌های CodingStandard* تنظیمات ثابت‌اند. |
| [CodingStandardDlSlType](#codingstandarddlsltype) | 6,713 | 4 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardEntity](#codingstandardentity) | 368 | 11 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardEntityCode](#codingstandardentitycode) | 8,660 | 9 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardReportFieldInfo](#codingstandardreportfieldinfo) | 1,026 | 18 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardReportInfo](#codingstandardreportinfo) | 144 | 9 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardXMLDataInfo](#codingstandardxmldatainfo) | 1,176 | 8 | ⚪ تنظیمات/ثابت |  |
| [CodingStandardXMLInfo](#codingstandardxmlinfo) | 336 | 11 | ⚪ تنظیمات/ثابت |  |
| [DebitCreditStatement](#debitcreditstatement) | 531 | 16 | 🔵 اطلاعات پایه فعال | صورت‌ریز بدهکار/بستانکار مورد استفاده برای مغایرت‌گیری/تطبیق طرف‌حساب. |
| [DebitCreditStatementItem](#debitcreditstatementitem) | 872 | 16 | 🔵 اطلاعات پایه فعال |  |
| [DeletedVoucher](#deletedvoucher) | 1,757 | 15 | 🟡 لاگ/کش/سیستمی | لاگ سندهای حذف‌شده. |
| [DL](#dl) | 8,154 | 14 | 🔵 اطلاعات پایه فعال | حساب تفصیلی (طرف‌حساب‌ها/مراکز هزینه/پروژه/حساب بانکی). Code یکتاست و از DLLevelN ارجاع می‌شود؛ ReferenceID به Party/CostCenter/Project/BankAccount. |
| [DLGrouping](#dlgrouping) | 2 | 6 | ⚪ تنظیمات/ثابت |  |
| [DLGroupingDetail](#dlgroupingdetail) | 3 | 4 | ⚪ تنظیمات/ثابت |  |
| [DLType](#dltype) | 35 | 12 | 🔵 اطلاعات پایه فعال | نوع تفصیلی: 1 شخص،2 شرکت،4 مرکز هزینه،5 پروژه،10 حساب بانکی،13 تسهیلات،27 سایر. |
| [DLTypeRelation](#dltyperelation) | 1,479 | 6 | 🔵 اطلاعات پایه فعال | هر معین در هر سطح (Level) چه نوع تفصیلی می‌پذیرد. |
| [GL](#gl) | 73 | 11 | 🔵 اطلاعات پایه فعال | حساب کل (۷۳). FIN3.SL معین (۶ رقمی؛ ۴ رقم اول = کد کل). |
| [GLVoucher](#glvoucher) | 214 | 15 | 🔵 اطلاعات پایه فعال | اسناد سطح کل (تجمیعی) با GLVoucherItem و GLVoucherReference. |
| [GLVoucherItem](#glvoucheritem) | 4,324 | 9 | 🔵 اطلاعات پایه فعال |  |
| [GLVoucherReference](#glvoucherreference) | 72,928 | 4 | 🟡 لاگ/کش/سیستمی |  |
| [LookupMap](#lookupmap) | 5 | 5 | ⚪ تنظیمات/ثابت |  |
| [PeriodicOppositNatureAccounts](#periodicoppositnatureaccounts) | 2,101 | 78 | 🟡 لاگ/کش/سیستمی | کش گزارش حساب‌های خلاف ماهیت. |
| [PeriodNature](#periodnature) | 3 | 5 | ⚪ تنظیمات/ثابت |  |
| [SeasonalReportMergePattern](#seasonalreportmergepattern) | 1 | 9 | ⚪ تنظیمات/ثابت |  |
| [SeasonalReportMergePatternItem](#seasonalreportmergepatternitem) | 2 | 7 | ⚪ تنظیمات/ثابت |  |
| [SeasonalZone](#seasonalzone) | 7,453 | 6 | ⚪ تنظیمات/ثابت | فهرست ثابت شهر/استان/کشور (اظهارنامه فصلی). |
| [SL](#sl) | 618 | 22 | 🔵 اطلاعات پایه فعال | حساب معین (۶۱۸). |
| [SLDefaultVat](#sldefaultvat) | 1 | 7 | ⚪ تنظیمات/ثابت |  |
| [SLDLFlow](#sldlflow) | 6,389 | 12 | 🟡 لاگ/کش/سیستمی | کش گردش حساب‌ها (صورت‌حساب تفصیلی) برای گزارش. |
| [SLStandardDesc](#slstandarddesc) | 453 | 5 | ⚪ تنظیمات/ثابت |  |
| [StandardVoucherTypeEntity](#standardvouchertypeentity) | 20 | 4 | ⚪ تنظیمات/ثابت |  |
| [VATParty](#vatparty) | 873 | 9 | 🔵 اطلاعات پایه فعال | اشخاص مشمول ارزش افزوده. |
| [Voucher](#voucher) | 95,741 | 26 | 🟢 تراکنشی فعال | سرفصل سند حسابداری. State: 1 موقت،4 بررسی‌شده،32 قطعی. تاریخ میلادی. |
| [VoucherHistory](#voucherhistory) | 1 | 11 | 🟡 لاگ/کش/سیستمی |  |
| [VoucherItem](#voucheritem) | 693,272 | 73 | 🟢 تراکنشی فعال | ردیف‌های سند (بدهکار/بستانکار). Debit/Credit nullable. تفصیلی‌ها در DLLevel4..20. |
| [VoucherItemOffline](#voucheritemoffline) | 693,050 | 77 | 🟡 لاگ/کش/سیستمی | کپی denormalized و عقب‌مانده‌ی VoucherItem (۲۲۲ ردیف جدید را ندارد). برای گزارش استفاده نشود. |
| [VoucherLock](#voucherlock) | 7,224 | 5 | 🟡 لاگ/کش/سیستمی |  |
| [VoucherReference](#voucherreference) | 114,254 | 10 | 🟡 لاگ/کش/سیستمی | ارتباط سند با سند/فرم مبدأ (مثلاً استهلاک، حقوق) با کد entity. |
| [VoucherReviewRecord](#voucherreviewrecord) | 37,351 | 8 | 🟡 لاگ/کش/سیستمی |  |
| [VoucherType](#vouchertype) | 46 | 8 | 🔵 اطلاعات پایه فعال | نوع سند (عمومی، افتتاحیه، اختتامیه، بستن حساب‌ها، اسناد خودکار FAM/HCM). |

## AccountGroup

`FIN3.AccountGroup` — 12 rows — 🔵 اطلاعات پایه فعال

گروه حساب (11 دارایی جاری ... 91/92 انتظامی).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountGroupID | bigint |  | PK |  |
| LedgerRef | bigint |  |  |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| State | bit |  |  |  |
| Nature | int |  |  |  |
| Type | int |  |  |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `FSR3.AdjustmentVoucherItem`، `FIN3.VoucherItem`، `FIN3.AccountGroupGroupMember`، `FIN3.GL`

## AccountingDepartment

`FIN3.AccountingDepartment` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountingDepartmentID | bigint |  | PK |  |
| Code | int | Y |  |  |
| Name | nvarchar(100) |  |  |  |
| IsStatic | bit | Y |  |  |

## AccountMapping

`FIN3.AccountMapping` — 616 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountMappingID | bigint |  | PK |  |
| LeadingSLRef | bigint | Y |  |  |
| Level | int | Y |  |  |
| IsTemporary | bit |  |  |  |
| LeadingDLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| LeadingDLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| LeadingDLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| LeadingDLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| LeadingDLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| LeadingDLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondarySLRef | bigint | Y | → FIN3.SL.SLID |  |
| SecondaryDLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondaryDLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondaryDLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondaryDLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondaryDLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| SecondaryDLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |

ارجاع‌شده توسط: `FIN3.AccountMappingItem`

## AccountType

`FIN3.AccountType` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountTypeID | bigint |  | PK |  |
| Number | nvarchar(50) |  |  |  |
| Name | nvarchar(100) |  |  |  |
| CategoryType | int |  |  |  |
| IsCreditable | bit |  |  |  |
| IsStatic | bit |  |  |  |

ارجاع‌شده توسط: `SLS3.SalesTypeItem`، `FIN3.Account`

## AgingReceivableSetting

`FIN3.AgingReceivableSetting` — 38 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AgingReceivableSettingID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| FromFiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| ToFiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| CurrencyFeature | int |  |  |  |
| ReportType | int |  |  | `ReportType`: 1=گزارش، 2=یادداشت |
| PeriodTitle | nvarchar(128) |  |  |  |
| PercentageperPeriod | decimal(5,2) |  |  |  |
| FromDate | datetime |  |  |  |
| ToDate | datetime |  |  |  |
| VoucherTypeIds | nvarchar(512) | Y |  |  |
| BranchIds | nvarchar(512) | Y |  |  |
| GLIds | nvarchar(512) | Y |  |  |
| NoneNatureChecked | bit |  |  |  |
| FirstPercentage | decimal(5,2) |  |  |  |
| FromMonth | nvarchar(10) | Y |  |  |
| ToMonth | nvarchar(10) | Y |  |  |
| LedgerRef | bigint |  |  |  |

## Analyse

`FIN3.Analyse` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AnalyseID | bigint |  | PK |  |
| DebitVoucherItemRef | bigint |  | → FIN3.VoucherItem.VoucherItemID |  |
| CreditVoucherItemRef | bigint |  | → FIN3.VoucherItem.VoucherItemID |  |
| Amount | decimal(28,6) |  |  |  |
| Type | int |  |  | `AnalyseType`: 1=حساب |
| AccountSpecification | int |  |  | `AccountSpecification`: 1=غیر ارزی |

## ClosingVoucherClosableSL

`FIN3.ClosingVoucherClosableSL` — 1,455 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ClosingVoucherClosableSLID | bigint |  | PK |  |
| ClosingVoucherCounterPartSLRef | bigint |  | → FIN3.ClosingVoucherCounterPartSL.ClosingVoucherCounterPartSLID |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| SLCode | nvarchar(64) | Y |  |  |
| DLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel10 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel11 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel12 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel13 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel14 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel15 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel16 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel17 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel18 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel19 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel20 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLTypeRef4 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef5 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef6 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef7 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef8 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef9 | bigint | Y | → FIN3.DLType.DLTypeID |  |
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
| FilledDLLevelNumber | int |  |  |  |
| IncludeFilter | bit |  |  |  |
| PeriodNatureType | int | Y |  | `PeriodNatureType`:  |

## ClosingVoucherCounterPartSL

`FIN3.ClosingVoucherCounterPartSL` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ClosingVoucherCounterPartSLID | bigint |  | PK |  |
| Percentage | decimal(28,6) | Y |  |  |
| ClosingVoucherPatternRef | bigint |  | → FIN3.ClosingVoucherPattern.ClosingVoucherPatternID |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| SLCode | nvarchar(64) | Y |  |  |
| DLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel10 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel11 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel12 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel13 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel14 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel15 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel16 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel17 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel18 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel19 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel20 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| GroupingVoucherOrder | int | Y |  |  |
| PeriodNatureType | int | Y |  | `PeriodNatureType`:  |

ارجاع‌شده توسط: `FIN3.ClosingVoucherClosableSL`

## ClosingVoucherPattern

`FIN3.ClosingVoucherPattern` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ClosingVoucherPatternID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| Code | int |  |  |  |
| Type | int |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| State | bit |  |  |  |
| IssueVoucherSeparately | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.ClosingVoucherReferences`، `FIN3.ClosingVoucherCounterPartSL`

## ClosingVoucherReferences

`FIN3.ClosingVoucherReferences` — 6 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ClosingVoucherReferencesID | bigint |  | PK |  |
| ClosingVoucherPatternRef | bigint |  | → FIN3.ClosingVoucherPattern.ClosingVoucherPatternID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |
| ToDate | datetime |  |  |  |
| VoucherDate | datetime |  |  |  |

## COAGrouping

`FIN3.COAGrouping` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| COAGroupingID | bigint |  | PK |  |
| ParentRef | bigint | Y | → FIN3.COAGrouping.COAGroupingID |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| IsAssigned | bit |  |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |

ارجاع‌شده توسط: `FIN3.COAGrouping`، `FIN3.COAGroupingSL`

## CodingStandard

`FIN3.CodingStandard` — 10 rows — ⚪ تنظیمات/ثابت

استاندارد کدینگ سنا/سناما؛ جدول‌های CodingStandard* تنظیمات ثابت‌اند.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardID | bigint |  | PK |  |
| StandardTitle | nvarchar(250) |  |  |  |
| StandardTitleEn | nvarchar(250) |  |  |  |
| ProtocolTitle | nvarchar(250) | Y |  |  |
| ProtocolVersion | nvarchar(250) |  |  |  |
| IsStatic | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.StandardVoucherTypeMapping`، `FIN3.CodingStandardXMLInfo`، `FIN3.CodingStandardReportInfo`، `FIN3.CodingStandardFormula`، `FIN3.CodingStandardExtraField`، `FIN3.CodingStandardEntity`

## CodingStandardDlSlType

`FIN3.CodingStandardDlSlType` — 6,713 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardDLID | bigint |  | PK |  |
| ProtocolVersionStr | nvarchar(10) |  |  |  |
| SLType | nvarchar(50) |  |  |  |
| DLType | nvarchar(50) |  |  |  |

## CodingStandardEntity

`FIN3.CodingStandardEntity` — 368 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardEntityID | bigint |  | PK |  |
| CodingStandardRef | bigint |  | → FIN3.CodingStandard.CodingStandardID |  |
| RowNumber | int |  |  |  |
| Title | nvarchar(250) |  |  |  |
| TitleEN | nvarchar(250) |  |  |  |
| EntityName | nvarchar(250) | Y |  |  |
| EntityKey | nvarchar(250) | Y |  |  |
| IsStatic | bit |  |  |  |
| MapingIsAvailableForLeaf | bit |  |  |  |
| DetailReference | int |  |  | `CodingStandardEntityDetailReference`: 1=موجودیت سیستمی، 2=موجودیت استاندارد |

ارجاع‌شده توسط: `FIN3.CodingStandardEntityCode`

## CodingStandardEntityCode

`FIN3.CodingStandardEntityCode` — 8,660 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardEntityCodeID | bigint |  | PK |  |
| Name | nvarchar(250) |  |  |  |
| Code | nvarchar(100) |  |  |  |
| CodingStandardEntityRef | bigint |  | → FIN3.CodingStandardEntity.CodingStandardEntityID |  |
| ParentRef | bigint | Y | → FIN3.CodingStandardEntityCode.CodingStandardEntityCodeID |  |
| Left | int |  |  |  |
| Right | int |  |  |  |
| IsStatic | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.CodingStandardFormulaItem`، `FIN3.CodingStandardFormulaItemFilter`، `FIN3.CodingStandardEntityCode`، `FIN3.CodingStandardEntityCodeMapping`

## CodingStandardReportFieldInfo

`FIN3.CodingStandardReportFieldInfo` — 1,026 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardReportFieldInfoID | bigint |  | PK |  |
| FieldCode | nvarchar(128) |  |  |  |
| FieldTitleEN | nvarchar(250) |  |  |  |
| FieldTitle | nvarchar(250) |  |  |  |
| Nature | nvarchar(250) | Y |  |  |
| ViewOrder | int |  |  |  |
| MappField | int |  |  |  |
| DataType | nvarchar(50) |  |  |  |
| CodingStandardReportInfoRef | bigint |  | → FIN3.CodingStandardReportInfo.CodingStandardReportInfoID |  |
| IsAggregate | int |  |  |  |
| Attachment | bit | Y |  |  |
| Data_Type | int |  |  |  |
| Size | int |  |  |  |
| Precision | int |  |  |  |
| Scale | int |  |  |  |
| OriginalField | nvarchar(250) | Y |  |  |
| ContentType | int |  |  |  |

ارجاع‌شده توسط: `FIN3.CodingStandardReportFieldInfoAttachment`

## CodingStandardReportInfo

`FIN3.CodingStandardReportInfo` — 144 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardReportInfoID | bigint |  | PK |  |
| PartTitle | nvarchar(250) |  |  |  |
| PartTitle_En | nvarchar(250) |  |  |  |
| CodingStandardRef | bigint |  | → FIN3.CodingStandard.CodingStandardID |  |
| ObjectName | nvarchar(250) | Y |  |  |
| ReferenceData | varchar(5) | Y |  |  |
| Attachment | bit | Y |  |  |
| OrderView | int |  |  |  |

ارجاع‌شده توسط: `FIN3.CodingStandardReportFieldInfo`

## CodingStandardXMLDataInfo

`FIN3.CodingStandardXMLDataInfo` — 1,176 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardXMLDataInfoID | bigint |  | PK |  |
| CodingStandardXMLInfoRef | bigint |  | → FIN3.CodingStandardXMLInfo.CodingStandardXMLInfoID |  |
| AttributeName | nvarchar(100) |  |  |  |
| ReportFieldInfoRef | nvarchar(500) |  |  |  |
| ShowWithoutValue | bit |  |  |  |
| AttributeOrder | int |  |  |  |
| EmptyValue | nvarchar(50) | Y |  |  |

## CodingStandardXMLInfo

`FIN3.CodingStandardXMLInfo` — 336 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CodingStandardXMLInfoID | bigint |  | PK |  |
| CodingStandardRef | bigint |  | → FIN3.CodingStandard.CodingStandardID |  |
| XmlElementType | nvarchar(10) |  |  |  |
| XmlElementTitle | nvarchar(100) |  |  |  |
| XmlElementParent | bigint | Y |  |  |
| XmlElementKey | nvarchar(100) | Y |  |  |
| XmlOrder | int |  |  |  |
| ReferenceData | nvarchar(100) |  |  |  |
| ReportInfoRef | nvarchar(500) |  |  |  |
| IsAggregate | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.CodingStandardXMLDataInfo`

## DebitCreditStatement

`FIN3.DebitCreditStatement` — 531 rows — 🔵 اطلاعات پایه فعال

صورت‌ریز بدهکار/بستانکار مورد استفاده برای مغایرت‌گیری/تطبیق طرف‌حساب.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DebitCreditStatementID | bigint |  | PK |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| MainNumber | int |  |  |  |
| Number | nvarchar(64) |  |  |  |
| DLRef | nvarchar(64) |  | → FIN3.DL.Code |  |
| Date | datetime |  |  |  |
| Type | int |  |  |  |
| State | int |  |  | `DebitCreditStatementState`: 1=ایجاد شده، 2=ارسال شده، 3=ابطال شده |
| Description | nvarchar(512) | Y |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Confirmer | bigint |  | → SYS3.User.UserID |  |

ارجاع‌شده توسط: `FIN3.DebitCreditStatementItem`

## DebitCreditStatementItem

`FIN3.DebitCreditStatementItem` — 872 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DebitCreditStatementItemID | bigint |  | PK |  |
| DebitCreditStatementRef | bigint |  | → FIN3.DebitCreditStatement.DebitCreditStatementID |  |
| VoucherItemRef | bigint |  |  |  |
| VoucherRef | bigint |  |  |  |
| VoucherDate | datetime |  |  |  |
| VoucherNumber | int | Y |  |  |
| VoucherSequence | int |  |  |  |
| VoucherItemRowNumber | int |  |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| TargetCurrencyDebit | decimal(28,6) | Y |  |  |
| TargetCurrencyCredit | decimal(28,6) | Y |  |  |
| TargetCurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |

## DeletedVoucher

`FIN3.DeletedVoucher` — 1,757 rows — 🟡 لاگ/کش/سیستمی

لاگ سندهای حذف‌شده.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DeletedVoucherID | bigint |  | PK |  |
| ReferenceNumber | bigint | Y |  |  |
| VoucherNumber | int |  |  |  |
| VoucherSequence | int |  |  |  |
| VoucherDailyNumber | int |  |  |  |
| FiscalYearRef | bigint |  |  |  |
| LedgerRef | bigint |  |  |  |
| BranchRef | bigint |  |  |  |
| VoucherDate | datetime |  |  |  |
| VoucherCreator | bigint |  | → SYS3.User.UserID |  |
| Deleter | bigint |  | → SYS3.User.UserID |  |
| DateOfRemoval | datetime |  |  |  |
| VoucherTypeRef | bigint | Y |  |  |
| IsSequenceNumberUsed | bit |  |  |  |

## DL

`FIN3.DL` — 8,154 rows — 🔵 اطلاعات پایه فعال

حساب تفصیلی (طرف‌حساب‌ها/مراکز هزینه/پروژه/حساب بانکی). Code یکتاست و از DLLevelN ارجاع می‌شود؛ ReferenceID به Party/CostCenter/Project/BankAccount.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLID | bigint |  | PK |  |
| DLTypeRef | bigint |  | → FIN3.DLType.DLTypeID |  |
| ReferenceID | bigint | Y |  |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(512) |  |  |  |
| Title_En | nvarchar(512) | Y |  |  |
| CurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| EntityCode | int | Y |  |  |
| Discriminator | nvarchar(64) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| State | bit |  |  |  |
| ClassificationNumber | nvarchar(64) | Y |  |  |
| ParentDLRef | bigint | Y |  |  |

ارجاع‌شده توسط: `RPA3.PayableCollateral`، `PRC3.EntityDLLevelInfo`، `PRC3.PaymentInformation`، `BDG3.PaymentTypeSL`، `RPA3.DepositDeploymentItem`، `BDG3.BudgetEntityItem`، `RPA3.PaymentOrder`، `RPA3.TransferPayableCheque`، `FAM3.ExitFromOrganization`، `RPA3.ReceivableCollateral`، `RPA3.PaymentRequest`، `FCC3.ContractHeader`، `RPA3.PaymentRequestItem`، `FCC3.ContractAmount`، `FAM3.Sales`، `RPA3.GuaranteeToNormal`، `RPA3.PaymentOrderPayableNote`، `BDG3.PaymentInformationItem`، `FAM3.TemporaryExitItem`، `RPA3.ReceivableNote`، `RPA3.PaymentOrderRestoreReceivableNote`، `FAM3.Asset`، `FCC3.ContractPayCommitment`، `LGS3.PricingFactor`، `RPA3.GuaranteeToPayableNote` …

## DLGrouping

`FIN3.DLGrouping` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLGroupingID | bigint |  | PK |  |
| ParentRef | bigint | Y | → FIN3.DLGrouping.DLGroupingID |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| IsAssigned | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.DLGrouping`، `FIN3.DLGroupingDetail`

## DLGroupingDetail

`FIN3.DLGroupingDetail` — 3 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLGroupingDetailID | bigint |  | PK |  |
| DLGroupingRef | bigint |  | → FIN3.DLGrouping.DLGroupingID |  |
| DLRef | nvarchar(64) |  | → FIN3.DL.Code |  |

## DLType

`FIN3.DLType` — 35 rows — 🔵 اطلاعات پایه فعال

نوع تفصیلی: 1 شخص،2 شرکت،4 مرکز هزینه،5 پروژه،10 حساب بانکی،13 تسهیلات،27 سایر.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLTypeID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| DefaultCode | nvarchar(64) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| IsStatic | bit |  |  |  |
| EntityCode | int | Y |  |  |
| Discriminator | nvarchar(64) | Y |  |  |
| ParentDLTypeRef | bigint | Y | → FIN3.DLType.DLTypeID |  |
| IsParentRequired | bit |  |  |  |
| ClassificationNumberLength | int |  |  |  |

ارجاع‌شده توسط: `FIN3.VoucherItem`، `HCM3.TransferVoucherSpecificationSL`، `HCM3.OilVoucherTemplateItem`، `FSR3.PriorYearAdjustmentItem`، `FSR3.NatureAdjustmentItem`، `FSR3.MatrixAccountNoteItemImportanceInfo`، `FSR3.WriteOffPatternAccount`، `FSR3.PriorYearAdjustmentCollectiveInformation`، `FSR3.AccountNoteItem`، `FSR3.TopicToSLRelationDL`، `HCM3.CompensationRelatedDLType`، `FSR3.AdjustmentVoucherItem`، `BDG3.AmountControlDefinitionEntityDLType`، `FSR3.MatrixAccountNoteItem`، `FIN3.DLTypeRelation`، `FIN3.DLType`، `HCM3.OilVoucherItem`، `BDG3.RegularReportTemplateItem`، `FSR3.WriteOffStatementItem`، `FSR3.PriorYearAdjustmentAccount`، `HCM3.DefaultTrainingVoucherItem`، `FSR3.AccountNoteStructureImportanceInfo`، `BDG3.FilterDLType`، `CAC3.CostCenterConversionSLVoucherItem`، `FSR3.AccountNoteImportanceInfo` …

## DLTypeRelation

`FIN3.DLTypeRelation` — 1,479 rows — 🔵 اطلاعات پایه فعال

هر معین در هر سطح (Level) چه نوع تفصیلی می‌پذیرد.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLTypeRelationID | bigint |  | PK |  |
| SLRef | bigint |  | → FIN3.SL.SLID |  |
| Level | int |  |  |  |
| DLTypeRef | bigint |  | → FIN3.DLType.DLTypeID |  |
| HasNatureControl | bit |  |  |  |

## GL

`FIN3.GL` — 73 rows — 🔵 اطلاعات پایه فعال

حساب کل (۷۳). FIN3.SL معین (۶ رقمی؛ ۴ رقم اول = کد کل).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| GLID | bigint |  | PK |  |
| LedgerRef | bigint |  |  |  |
| AccountGroupRef | bigint |  | → FIN3.AccountGroup.AccountGroupID |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Nature | int |  |  |  |
| Type | int |  |  |  |
| State | bit |  |  |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `FSR3.CollectiveInformation`، `FSR3.MatrixNoteStructureItemImportanceInfo`، `FIN3.VoucherItem`، `FSR3.MatrixAccountNoteItemImportanceInfo`، `FSR3.PriorYearAdjustmentCollectiveInformation`، `FSR3.TopicToSLRelation`، `FSR3.AccountNoteItem`، `FSR3.MatrixAccountNoteItem`، `FSR3.AdjustmentVoucherItem`، `FSR3.AccountNoteStructureImportanceInfo`، `FSR3.AccountNoteImportanceInfo`، `FIN3.SL`، `FIN3.GLVoucherItem`، `FSR3.ReportTopicToSLRelation`، `FIN3.GLGroupMember`

## GLVoucher

`FIN3.GLVoucher` — 214 rows — 🔵 اطلاعات پایه فعال

اسناد سطح کل (تجمیعی) با GLVoucherItem و GLVoucherReference.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| GLVoucherID | bigint |  | PK |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| Number | int |  |  |  |
| Date | datetime |  |  |  |
| Description | nvarchar(4000) | Y |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| IsTemporary | bit |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `FIN3.GLVoucherItem`، `FIN3.GLVoucherReference`

## GLVoucherItem

`FIN3.GLVoucherItem` — 4,324 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| GLVoucherItemID | bigint |  | PK |  |
| GLVoucherRef | bigint |  | → FIN3.GLVoucher.GLVoucherID |  |
| GLRef | bigint |  | → FIN3.GL.GLID |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Date | datetime |  |  |  |

## GLVoucherReference

`FIN3.GLVoucherReference` — 72,928 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| GLVoucherReferenceID | bigint |  | PK |  |
| GLVoucherRef | bigint |  | → FIN3.GLVoucher.GLVoucherID |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |

## LookupMap

`FIN3.LookupMap` — 5 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LookupMapID | bigint |  | PK |  |
| LookupRef | bigint |  |  |  |
| StandardCode | bigint |  |  |  |
| StandardTitle | nvarchar(250) |  |  |  |

## PeriodicOppositNatureAccounts

`FIN3.PeriodicOppositNatureAccounts` — 2,101 rows — 🟡 لاگ/کش/سیستمی

کش گزارش حساب‌های خلاف ماهیت.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PeriodicOppositNatureAccountsID | bigint |  | PK |  |
| BranchRef | bigint |  |  |  |
| BranchCode | nvarchar(64) |  |  |  |
| BranchTitle | nvarchar(128) |  |  |  |
| BranchTitle_En | nvarchar(128) | Y |  |  |
| VoucherItemID | bigint |  |  |  |
| VoucherNumber | int |  |  |  |
| VoucherSequence | int |  |  |  |
| VoucherDate | datetime |  |  |  |
| RowNumber | int |  |  |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| Nature | int |  |  |  |
| NewNature | int |  |  |  |
| RunningValue | decimal(28,6) |  |  |  |
| SLRef | bigint |  |  |  |
| SLTitle | nvarchar(128) |  |  |  |
| SLTitle_En | nvarchar(128) | Y |  |  |
| SLCode | nvarchar(64) |  |  |  |
| DLLevel4Title | nvarchar(128) | Y |  |  |
| DLLevel4Title_En | nvarchar(128) | Y |  |  |
| DLLevel4Code | nvarchar(64) | Y |  |  |
| DLLevel5Title | nvarchar(128) | Y |  |  |
| DLLevel5Title_En | nvarchar(128) | Y |  |  |
| DLLevel5Code | nvarchar(64) | Y |  |  |
| DLLevel6Title | nvarchar(128) | Y |  |  |
| DLLevel6Title_En | nvarchar(128) | Y |  |  |
| DLLevel6Code | nvarchar(64) | Y |  |  |
| DLLevel7Title | nvarchar(128) | Y |  |  |
| DLLevel7Title_En | nvarchar(128) | Y |  |  |
| DLLevel7Code | nvarchar(64) | Y |  |  |
| DLLevel8Title | nvarchar(128) | Y |  |  |
| DLLevel8Title_En | nvarchar(128) | Y |  |  |
| DLLevel8Code | nvarchar(64) | Y |  |  |
| DLLevel9Title | nvarchar(128) | Y |  |  |
| DLLevel9Title_En | nvarchar(128) | Y |  |  |
| DLLevel9Code | nvarchar(64) | Y |  |  |
| DLLevel10Title | nvarchar(128) | Y |  |  |
| DLLevel10Title_En | nvarchar(128) | Y |  |  |
| DLLevel10Code | nvarchar(64) | Y |  |  |
| DLLevel11Title | nvarchar(128) | Y |  |  |
| DLLevel11Title_En | nvarchar(128) | Y |  |  |
| DLLevel11Code | nvarchar(64) | Y |  |  |
| DLLevel12Title | nvarchar(128) | Y |  |  |
| DLLevel12Title_En | nvarchar(128) | Y |  |  |
| DLLevel12Code | nvarchar(64) | Y |  |  |
| DLLevel13Title | nvarchar(128) | Y |  |  |
| DLLevel13Title_En | nvarchar(128) | Y |  |  |
| DLLevel13Code | nvarchar(64) | Y |  |  |
| DLLevel14Title | nvarchar(128) | Y |  |  |
| DLLevel14Title_En | nvarchar(128) | Y |  |  |
| DLLevel14Code | nvarchar(64) | Y |  |  |
| DLLevel15Title | nvarchar(128) | Y |  |  |
| DLLevel15Title_En | nvarchar(128) | Y |  |  |
| DLLevel15Code | nvarchar(64) | Y |  |  |
| DLLevel16Title | nvarchar(128) | Y |  |  |
| DLLevel16Title_En | nvarchar(128) | Y |  |  |
| DLLevel16Code | nvarchar(64) | Y |  |  |
| DLLevel17Title | nvarchar(128) | Y |  |  |
| DLLevel17Title_En | nvarchar(128) | Y |  |  |
| DLLevel17Code | nvarchar(64) | Y |  |  |
| DLLevel18Title | nvarchar(128) | Y |  |  |
| DLLevel18Title_En | nvarchar(128) | Y |  |  |
| DLLevel18Code | nvarchar(64) | Y |  |  |
| DLLevel19Title | nvarchar(128) | Y |  |  |
| DLLevel19Title_En | nvarchar(128) | Y |  |  |
| DLLevel19Code | nvarchar(64) | Y |  |  |
| DLLevel20Title | nvarchar(128) | Y |  |  |
| DLLevel20Title_En | nvarchar(128) | Y |  |  |
| DLLevel20Code | nvarchar(64) | Y |  |  |
| BaseCurrencyRef | bigint | Y |  |  |
| BaseCurrencyTitle | nvarchar(128) | Y |  |  |
| BaseCurrencyTitle_En | nvarchar(128) | Y |  |  |
| UserRef | bigint |  |  |  |
| VoucherDailyNumber | int |  |  |  |

## PeriodNature

`FIN3.PeriodNature` — 3 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PeriodNatureID | bigint |  | PK |  |
| Type | int |  |  | `PeriodNatureType`: 1=جاری، 2=سنواتی، 3=متمم |
| Title | nvarchar(250) |  |  |  |
| Title_En | nvarchar(50) | Y |  |  |

## SeasonalReportMergePattern

`FIN3.SeasonalReportMergePattern` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SeasonalReportMergePatternID | bigint |  | PK |  |
| Title | nvarchar(100) | Y |  |  |
| Number | nvarchar(50) |  |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `FIN3.SeasonalReportMergePatternItem`، `FIN3.TaxYear`

## SeasonalReportMergePatternItem

`FIN3.SeasonalReportMergePatternItem` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SeasonalReportMergePatternItemID | bigint |  | PK |  |
| SeasonalReportMergePatternRef | bigint |  | → FIN3.SeasonalReportMergePattern.SeasonalReportMergePatternID |  |
| ProviderType | int |  |  |  |
| Args | nvarchar(200) | Y |  |  |
| TaggingAgentKey | nvarchar(50) |  |  |  |
| PartyType | int |  |  |  |

## SeasonalZone

`FIN3.SeasonalZone` — 7,453 rows — ⚪ تنظیمات/ثابت

فهرست ثابت شهر/استان/کشور (اظهارنامه فصلی).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SeasonalZoneID | bigint |  | PK |  |
| CityCode | bigint |  |  |  |
| CityName | nvarchar(50) |  |  |  |
| ProvinceCode | bigint |  |  |  |
| ProviceName | nvarchar(50) |  |  |  |

ارجاع‌شده توسط: `FIN3.VATBaseInformation`، `FIN3.SeasonalZoneMap`

## SL

`FIN3.SL` — 618 rows — 🔵 اطلاعات پایه فعال

حساب معین (۶۱۸).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SLID | bigint |  | PK |  |
| GLRef | bigint |  | → FIN3.GL.GLID |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Nature | int |  |  |  |
| IsTraceable | bit |  |  |  |
| IsMultiCurrency | bit |  |  |  |
| HasCurrencyConversion | bit |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| DefaultCurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| State | bit |  |  |  |
| Type | int |  |  | `SLType`: 1=دائم، 2=موقت، 3=انتظامی |
| VATSLType | int | Y |  | `VATSLType`: 2=معین مالیات پذیر |
| TaxAccountType | int | Y |  | `TaxAccountType`:  |
| IsQuantifiable | bit |  |  |  |
| FundCategory | int | Y |  | `FundCategory`:  |
| ZeroBalance | int |  |  |  |
| AccountClass | int |  |  | `AccountClass`: 1=مالی |
| NatureControl | int |  |  | `NatureControl`: 1=بدون کنترل |
| LedgerRef | bigint |  |  |  |

ارجاع‌شده توسط: `FSR3.CollectiveInformation`، `RPA3.DraftVoucherItem`، `RPA3.CollateralType`، `FIN3.AutomaticVoucherPatternSourceSL`، `RPA3.ContractType`، `FAM3.AccountConfigurationItem`، `RPA3.VoucherReconciliationAllItem`، `BDG3.PaymentTypeSL`، `RPA3.BankAccountReconciliationSl`، `FAM3.AccountConfiguration`، `FSR3.PriorYearAdjustmentItem`، `FSR3.NatureAdjustmentItem`، `FSR3.MatrixNoteStructureItemImportanceInfo`، `FAM3.InsuranceAccountConfiguration`، `FSR3.WriteOffPatternAccount`، `HCM3.TransferVoucherSpecificationSL`، `RPA3.PayableCollateralAccountingInformation`، `BDG3.BudgetEntityItem`، `HCM3.OilVoucherTemplateItem`، `RPA3.RpaGLComparisonReportDeployment`، `FIN3.ClosingVoucherClosableSL`، `FSR3.MatrixAccountNoteItemImportanceInfo`، `PRC3.AccountGroupLedger`، `BDG3.SLFormulaItem`، `FSR3.PriorYearAdjustmentCollectiveInformation` …

## SLDefaultVat

`FIN3.SLDefaultVat` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SLDefaultVatID | bigint |  | PK |  |
| SLRef | bigint |  | → FIN3.SL.SLID |  |
| TaxStateType | int | Y |  |  |
| TransactionType | int | Y |  | `TransactionType`:  |
| PurchaseOrSale | int | Y |  | `PurchaseOrSale`:  |
| ItemOrServiceOrWithholdingTax | int | Y |  | `ItemOrServiceOrWithholdingTax`:  |

## SLDLFlow

`FIN3.SLDLFlow` — 6,389 rows — 🟡 لاگ/کش/سیستمی

کش گردش حساب‌ها (صورت‌حساب تفصیلی) برای گزارش.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SLDLFlowID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| Sequence | int |  |  |  |
| Number | int | Y |  |  |
| Date | datetime |  |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| Balance | decimal(28,6) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| VoucherRef | bigint |  |  |  |

## SLStandardDesc

`FIN3.SLStandardDesc` — 453 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SLStandardDescID | bigint |  | PK |  |
| SLRef | bigint |  | → FIN3.SL.SLID |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) | Y |  |  |

## StandardVoucherTypeEntity

`FIN3.StandardVoucherTypeEntity` — 20 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StandardVoucherTypeEntityID | bigint |  | PK |  |
| Code | nvarchar(100) |  |  |  |
| Title | nvarchar(250) |  |  |  |

ارجاع‌شده توسط: `FIN3.StandardVoucherTypeMappingItem`

## VATParty

`FIN3.VATParty` — 873 rows — 🔵 اطلاعات پایه فعال

اشخاص مشمول ارزش افزوده.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VATPartyID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| VATCategory | int |  |  |  |
| VATPartyType | int |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `FIN3.VATCollectiveInformation`

## Voucher

`FIN3.Voucher` — 95,741 rows — 🟢 تراکنشی فعال

سرفصل سند حسابداری. State: 1 موقت،4 بررسی‌شده،32 قطعی. تاریخ میلادی.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherID | bigint |  | PK |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| Number | int | Y |  |  |
| Sequence | int |  |  |  |
| DailyNumber | int |  |  |  |
| AuxiliaryNumber | nvarchar(16) | Y |  |  |
| Date | datetime |  |  |  |
| VoucherTypeRef | bigint |  | → FIN3.VoucherType.VoucherTypeID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| State | int |  |  | `VoucherState`: 1=موقت، 2=یادداشت، 4=بررسی شده، 32=قطعی شده |
| IsTemporary | bit |  |  |  |
| IsCurrencyBased | bit |  |  |  |
| IsExternal | bit |  |  |  |
| ReferenceNumber | bigint | Y |  |  |
| ShowCurrencyFields | bit |  |  |  |
| IsReadonly | bit |  |  |  |
| ReviewNumber | int | Y |  |  |
| ReviewDate | datetime | Y |  |  |

ارجاع‌شده توسط: `FIN3.VoucherItem`، `FIN3.VatContractCollectiveInformation`، `FSR3.PriorYearAdjustmentItem`، `IPR3.Clearance`، `PRC3.Refund`، `IPR3.TransportDocument`، `HCM3.Voucher`، `HCM3.TransferVoucher`، `FIN3.ClosingVoucherInfo`، `IPR3.Insurance`، `FIN3.ClosingVoucherReferences`، `PRC3.Invoice`، `HCM3.OilVoucherReference`، `FSR3.PriorYearAdjustment`، `FIN3.ConversionDocument`، `IPR3.ImportLicence`، `CAC3.AccountingVoucher`، `FIN3.DraftVoucher`، `HCM3.TrainingVoucher`، `FIN3.VoucherReference`، `IPR3.CommercialOrder`، `SLS3.CommissionVoucher`، `HCM3.NSVoucherReference`، `PRC3.PurchaseMiscCost`، `FIN3.GLVoucherReference` …

## VoucherHistory

`FIN3.VoucherHistory` — 1 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherHistoryID | bigint |  | PK |  |
| ReferenceNumber | bigint |  |  |  |
| ReferenceType | int |  |  | `ReferenceType`: 1=سند بازرسی |
| PropertyType | int |  |  |  |
| OriginPropertyValue | nvarchar(512) | Y |  |  |
| PropertyValue | nvarchar(512) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

## VoucherItem

`FIN3.VoucherItem` — 693,272 rows — 🟢 تراکنشی فعال

ردیف‌های سند (بدهکار/بستانکار). Debit/Credit nullable. تفصیلی‌ها در DLLevel4..20.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherItemID | bigint |  | PK |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| RowNumber | int |  |  |  |
| AccountGroupRef | bigint |  | → FIN3.AccountGroup.AccountGroupID |  |
| GLRef | bigint |  | → FIN3.GL.GLID |  |
| SLRef | bigint |  | → FIN3.SL.SLID |  |
| SLCode | nvarchar(64) |  |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| CurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| BaseCurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| TargetCurrencyRef | bigint | Y |  |  |
| TargetCurrencyDebit | decimal(28,6) | Y |  |  |
| TargetCurrencyCredit | decimal(28,6) | Y |  |  |
| IsCurrencyBased | bit |  |  |  |
| OperationalCurrencyExchangeRateRef | bigint | Y | → GNR3.CurrencyExchangeRate.CurrencyExchangeRateID |  |
| OperationalCurrencyExchangeRate | decimal(28,6) | Y |  |  |
| BaseCurrencyExchangeRateRef | bigint | Y | → GNR3.CurrencyExchangeRate.CurrencyExchangeRateID |  |
| BaseCurrencyExchangeRate | decimal(28,6) | Y |  |  |
| CurrencyDebit | decimal(28,6) | Y |  |  |
| CurrencyCredit | decimal(28,6) | Y |  |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| FollowUpNumber | nvarchar(64) | Y |  |  |
| FollowUpDate | datetime | Y |  |  |
| Quantity | decimal(28,6) | Y |  |  |
| DLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel10 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel11 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel12 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel13 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel14 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel15 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel16 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel17 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel18 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel19 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel20 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLTypeRef4 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef5 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef6 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef7 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef8 | bigint | Y | → FIN3.DLType.DLTypeID |  |
| DLTypeRef9 | bigint | Y | → FIN3.DLType.DLTypeID |  |
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
| TaxAccountType | int | Y |  | `TaxAccountType`:  |
| TaxStateType | int | Y |  |  |
| TransactionType | int | Y |  | `TransactionType`:  |
| PurchaseOrSale | int | Y |  | `PurchaseOrSale`:  |
| ItemOrService | int | Y |  | `ItemOrService`:  |
| PartyRef | bigint | Y | → GNR3.Party.PartyID |  |
| TaxAmount | decimal(28,6) | Y |  |  |
| TollAmount | decimal(28,6) | Y |  |  |
| PeriodNature | int | Y |  | `PeriodNatureType`:  |
| IsTaxPrepaymentUnrefundable | bit |  |  |  |
| IsTollPrepaymentUnrefundable | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.Analyse`، `FSR3.PriorYearAdjustmentItem`، `LGS3.ItemPrice`، `RPA3.VoucherReconciliationItem`

## VoucherItemOffline

`FIN3.VoucherItemOffline` — 693,050 rows — 🟡 لاگ/کش/سیستمی

کپی denormalized و عقب‌مانده‌ی VoucherItem (۲۲۲ ردیف جدید را ندارد). برای گزارش استفاده نشود.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherItemID | bigint |  |  |  |
| RowNumber | int |  |  |  |
| VoucherRef | bigint |  |  |  |
| BranchRef | bigint |  |  |  |
| AccountGroupRef | bigint |  |  |  |
| GLRef | bigint |  |  |  |
| SLRef | bigint |  |  |  |
| SLCode | nvarchar(64) |  |  |  |
| Debit | decimal(28,6) | Y |  |  |
| Credit | decimal(28,6) | Y |  |  |
| CurrencyRef | bigint | Y |  |  |
| BaseCurrencyRef | bigint | Y |  |  |
| CurrencyDebit | decimal(28,6) | Y |  |  |
| CurrencyCredit | decimal(28,6) | Y |  |  |
| FollowUpNumber | nvarchar(64) | Y |  |  |
| FollowUpDate | datetime | Y |  |  |
| DLLevel4 | nvarchar(64) | Y |  |  |
| DLLevel5 | nvarchar(64) | Y |  |  |
| DLLevel6 | nvarchar(64) | Y |  |  |
| DLLevel7 | nvarchar(64) | Y |  |  |
| DLLevel8 | nvarchar(64) | Y |  |  |
| DLLevel9 | nvarchar(64) | Y |  |  |
| DLTypeRef4 | bigint | Y |  |  |
| DLTypeRef5 | bigint | Y |  |  |
| DLTypeRef6 | bigint | Y |  |  |
| DLTypeRef7 | bigint | Y |  |  |
| DLTypeRef8 | bigint | Y |  |  |
| DLTypeRef9 | bigint | Y |  |  |
| TaxAccountType | int | Y |  | `TaxAccountType`:  |
| TaxStateType | int | Y |  |  |
| TransactionType | int | Y |  | `TransactionType`:  |
| PurchaseOrSale | int | Y |  | `PurchaseOrSale`:  |
| ItemOrService | int | Y |  | `ItemOrService`:  |
| IsCurrencyBased | bit |  |  |  |
| Quantity | decimal(28,6) | Y |  |  |
| PartyRef | bigint | Y |  |  |
| Date | datetime |  |  |  |
| VoucherTypeRef | bigint |  |  |  |
| AuxiliaryNumber | nvarchar(16) | Y |  |  |
| FiscalYearRef | bigint |  |  |  |
| LedgerRef | bigint |  |  |  |
| Number | int | Y |  |  |
| Sequence | int |  |  |  |
| IsTraceable | bit |  |  |  |
| IsQuantifiable | bit |  |  |  |
| IsMultiCurrency | bit |  |  |  |
| SLType | int |  |  | `SLType`: 1=دائم، 2=موقت، 3=انتظامی |
| TargetCurrencyCredit | decimal(28,6) | Y |  |  |
| TargetCurrencyDebit | decimal(28,6) | Y |  |  |
| TargetCurrencyRef | bigint | Y |  |  |
| VoucherCreator | bigint |  |  |  |
| DailyNumber | int |  |  |  |
| VoucherState | int |  |  | `VoucherState`: 1=موقت، 4=بررسی شده، 32=قطعی شده |
| VoucherSequence | int |  |  |  |
| IsExternal | bit |  |  |  |
| DLLevel10 | nvarchar(64) | Y |  |  |
| DLLevel11 | nvarchar(64) | Y |  |  |
| DLLevel12 | nvarchar(64) | Y |  |  |
| DLLevel13 | nvarchar(64) | Y |  |  |
| DLLevel14 | nvarchar(64) | Y |  |  |
| DLLevel15 | nvarchar(64) | Y |  |  |
| DLLevel16 | nvarchar(64) | Y |  |  |
| DLLevel17 | nvarchar(64) | Y |  |  |
| DLLevel18 | nvarchar(64) | Y |  |  |
| DLLevel19 | nvarchar(64) | Y |  |  |
| DLLevel20 | nvarchar(64) | Y |  |  |
| DLTypeRef10 | bigint | Y |  |  |
| DLTypeRef11 | bigint | Y |  |  |
| DLTypeRef12 | bigint | Y |  |  |
| DLTypeRef13 | bigint | Y |  |  |
| DLTypeRef14 | bigint | Y |  |  |
| DLTypeRef15 | bigint | Y |  |  |
| DLTypeRef16 | bigint | Y |  |  |
| DLTypeRef17 | bigint | Y |  |  |
| DLTypeRef18 | bigint | Y |  |  |
| DLTypeRef19 | bigint | Y |  |  |
| DLTypeRef20 | bigint | Y |  |  |

## VoucherLock

`FIN3.VoucherLock` — 7,224 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherLockID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| VoucherRef | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

## VoucherReference

`FIN3.VoucherReference` — 114,254 rows — 🟡 لاگ/کش/سیستمی

ارتباط سند با سند/فرم مبدأ (مثلاً استهلاک، حقوق) با کد entity.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherReferenceID | bigint |  | PK |  |
| OriginalEntityCode | int |  |  |  |
| OriginalReferenceID | bigint |  |  |  |
| MasterEntityCode | int |  |  |  |
| MasterReferenceID | bigint |  |  |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |
| ReferenceNumber | nvarchar(128) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| Descriminator | int | Y |  |  |

## VoucherReviewRecord

`FIN3.VoucherReviewRecord` — 37,351 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherReviewRecordID | bigint |  | PK |  |
| VoucherRef | bigint |  | → FIN3.Voucher.VoucherID |  |
| Date | datetime |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| State | int |  |  |  |
| Action | int |  |  |  |
| Reviewer | bigint |  | → SYS3.User.UserID |  |

## VoucherType

`FIN3.VoucherType` — 46 rows — 🔵 اطلاعات پایه فعال

نوع سند (عمومی، افتتاحیه، اختتامیه، بستن حساب‌ها، اسناد خودکار FAM/HCM).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherTypeID | bigint |  | PK |  |
| Code | int | Y |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| IsStatic | bit |  |  |  |
| OwnerSystem | nvarchar(3) | Y |  |  |

ارجاع‌شده توسط: `FIN3.StandardVoucherTypeMappingItem`، `FSR3.AdjustmentVoucher`، `FIN3.Voucher`، `FIN3.AccountingVoucherTemplate`
