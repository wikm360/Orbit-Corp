# Schema `SLS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [CustomerSalesPortalUser](#customersalesportaluser) | 1 | 11 | 🔴 استفاده‌نشده (seed) |  |
| [HandheldPos](#handheldpos) | 16 | 2 | 🔴 استفاده‌نشده (seed) |  |
| [HandheldPrinter](#handheldprinter) | 22 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [SalesCommissionContext](#salescommissioncontext) | 7 | 7 | 🔴 استفاده‌نشده (seed) |  |
| [SalesEmployeeRole](#salesemployeerole) | 10 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [SalesPolicyExtraProperty](#salespolicyextraproperty) | 9 | 26 | 🔴 استفاده‌نشده (seed) |  |
| [ScriptTemplate](#scripttemplate) | 24 | 2 | 🔴 استفاده‌نشده (seed) |  |
| [SelfServiceUser](#selfserviceuser) | 1 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [TaxPayerCurrency](#taxpayercurrency) | 179 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [TaxPayerUnit](#taxpayerunit) | 101 | 4 | 🔴 استفاده‌نشده (seed) |  |

## CustomerSalesPortalUser

`SLS3.CustomerSalesPortalUser` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CustomerSalesPortalUserID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| FirstName | nvarchar(250) | Y |  |  |
| LastName | nvarchar(250) | Y |  |  |
| UserName | nvarchar(50) |  |  |  |
| Password | nvarchar(50) |  |  |  |
| Email | nvarchar(200) |  |  |  |
| IsAdmin | bit |  |  |  |
| IsSuperUser | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `SLS3.CustomerSalesPortalReceivedLoad`، `SLS3.CustomerSalesPortalSaleRequest`، `SLS3.CustomerSalesPortalShoppingCart`، `SLS3.CustomerSalesPortalUserGroupMember`، `SLS3.CustomerSalesPortalUserPermission`، `SLS3.CustomerSalesPortalUserReportPermission`

## HandheldPos

`SLS3.HandheldPos` — 16 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| HandheldPosID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |

ارجاع‌شده توسط: `SLS3.Broker`، `SLS3.MobileServiceUpdateSettings`

## HandheldPrinter

`SLS3.HandheldPrinter` — 22 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| HandheldPrinterID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| PrintFormat | nvarchar(128) |  |  |  |
| MultiPage | bit |  |  |  |
| MaxPageCount | int | Y |  |  |

ارجاع‌شده توسط: `SLS3.Broker`، `SLS3.HandheldPrintableDocument`

## SalesCommissionContext

`SLS3.SalesCommissionContext` — 7 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesCommissionContextID | bigint |  | PK |  |
| Key | nvarchar(256) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| FactorType | int |  |  |  |
| TargetType | int |  |  |  |
| VariablePrefix | nvarchar(15) |  |  |  |

ارجاع‌شده توسط: `SLS3.CommissionFactor`

## SalesEmployeeRole

`SLS3.SalesEmployeeRole` — 10 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesEmployeeRoleID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| IsInternal | bit |  |  |  |
| InternalRoleType | int | Y |  |  |

ارجاع‌شده توسط: `SLS3.SalesEmployeeRoleSalesDocument`، `SLS3.BrokerSalesEmployeeRole`، `SLS3.DocumentRelatedSalesEmployeeRole`

## SalesPolicyExtraProperty

`SLS3.SalesPolicyExtraProperty` — 9 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesPolicyExtraPropertyID | bigint |  | PK |  |
| BusinessPolicyRef | bigint |  | → GNR3.BusinessPolicy.BusinessPolicyID |  |
| DutyType | int |  |  |  |
| IsEffectiveOnFreeProductItems | bit |  |  |  |
| TransferPriceInPercentagePolicy | bit |  |  |  |
| IsContractBased | bit |  |  |  |
| FreeProductForEachBaseQuantityType | int |  |  | `FreeProductForEachBaseQuantityType`: 0= |
| ReductionLimitContainsDiscount | bit |  |  |  |
| ReductionLimitContainsMiscellaneous | bit |  |  |  |
| ReductionLimitContainsMiscellaneousFeeBased | bit |  |  |  |
| ReductionLimitContainsFreeProductDiscount | bit |  |  |  |
| UserCanSetFreeProductInDocument | bit |  |  |  |
| HasTolerance | bit |  |  |  |
| InclusiveFreeProduct | bit |  |  |  |
| UseAffectedItemUnitForInclusiveFreeProduct | bit |  |  |  |
| FreeProductAdaptationControl | bit |  |  |  |
| NonDefinitiveItemsPolicyOutputs | int | Y |  |  |
| WillNotIncludeInVoucher | bit |  |  |  |
| PricedFreeProduct | bit |  |  |  |
| PricedFreeProductCalculationMethod | int | Y |  | `PricedFreeProductCalculationMethod`:  |
| PricedFreeProductAcceptableAmountDifference | decimal(28,6) | Y |  |  |
| PolicyShouldBeSentToMobileAsText | bit |  |  |  |
| SelectRecommender | int | Y |  |  |
| NeedToConfirmFreeProduct | bit |  |  |  |
| ExitPartPolicyResultIsLimitedOnFreeProductItems | bit |  |  |  |

## ScriptTemplate

`SLS3.ScriptTemplate` — 24 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Key | nvarchar(256) | Y |  |  |
| Script | nvarchar(max) | Y |  |  |

## SelfServiceUser

`SLS3.SelfServiceUser` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SelfServiceUserID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| FirstName | nvarchar(250) | Y |  |  |
| LastName | nvarchar(250) | Y |  |  |
| UserName | nvarchar(50) |  |  |  |
| Password | nvarchar(50) |  |  |  |
| Email | nvarchar(200) |  |  |  |
| IsAdmin | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `SLS3.SelfServiceUserProfile`، `SLS3.SelfServiceSaleRequest`، `SLS3.SelfServiceSecurityPolicy`، `SLS3.SelfServiceUserGroupMember`، `SLS3.SelfServiceUserPermission`، `SLS3.ShoppingCartItem`

## TaxPayerCurrency

`SLS3.TaxPayerCurrency` — 179 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TaxPayerCurrencyID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Sign | nvarchar(10) |  |  |  |
| Title | nvarchar(100) |  |  |  |

## TaxPayerUnit

`SLS3.TaxPayerUnit` — 101 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TaxPayerUnitID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Name | nvarchar(50) |  |  |  |

ارجاع‌شده توسط: `SLS3.TaxPayerTransportationMap`، `SLS3.TaxPayerUnitMap`، `RMS3.TaxPayerOtherSurplusageMap`
