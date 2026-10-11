# Schema `RMS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AccountDeploymentSettingsAllowedPaymentType](#accountdeploymentsettingsallowedpaymenttype) | 5 | 8 | 🔴 استفاده‌نشده (seed) |  |
| [CustomerDefinitionTemplate](#customerdefinitiontemplate) | 1 | 18 | 🔴 استفاده‌نشده (seed) |  |
| [CustomerDefinitionTemplateItem](#customerdefinitiontemplateitem) | 12 | 7 | 🔴 استفاده‌نشده (seed) |  |
| [PerformanceSummaryPattern](#performancesummarypattern) | 1 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [PerformanceSummaryPatternOption](#performancesummarypatternoption) | 2 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [PerformanceSummaryPatternReceiptPayment](#performancesummarypatternreceiptpayment) | 2 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [PerformanceSummaryPatternSales](#performancesummarypatternsales) | 3 | 9 | 🔴 استفاده‌نشده (seed) |  |
| [PerformanceSummaryPatternSettlement](#performancesummarypatternsettlement) | 1 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [PriceListTemplate](#pricelisttemplate) | 1 | 15 | 🔴 استفاده‌نشده (seed) |  |
| [PriceListTemplateItemParameter](#pricelisttemplateitemparameter) | 1 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [ProductCouponProvider](#productcouponprovider) | 1 | 7 | 🔴 استفاده‌نشده (seed) |  |
| [RetailDocumentPaperType](#retaildocumentpapertype) | 7 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [RetailShopPolicy](#retailshoppolicy) | 5 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementMethod](#settlementmethod) | 9 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementMethodAttribute](#settlementmethodattribute) | 44 | 8 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementMethodGroup](#settlementmethodgroup) | 10 | 11 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementMethodGroupItem](#settlementmethodgroupitem) | 12 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementPolicy](#settlementpolicy) | 3 | 13 | 🔴 استفاده‌نشده (seed) |  |
| [SettlementPolicySettlementMethodGroup](#settlementpolicysettlementmethodgroup) | 6 | 15 | 🔴 استفاده‌نشده (seed) |  |
| [VirtualCardProvider](#virtualcardprovider) | 2 | 7 | 🔴 استفاده‌نشده (seed) |  |

## AccountDeploymentSettingsAllowedPaymentType

`RMS3.AccountDeploymentSettingsAllowedPaymentType` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountDeploymentSettingsAllowedPaymentTypeID | bigint |  | PK |  |
| SettlementNatureKey | nvarchar(50) |  |  |  |
| DefaultPaymentType | int | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

## CustomerDefinitionTemplate

`RMS3.CustomerDefinitionTemplate` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CustomerDefinitionTemplateID | bigint |  | PK |  |
| DefaultZoneBasedOnRetailShop | bit |  |  |  |
| DefaultCustomerGroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| DefaultCustomerGroupRef | bigint | Y | → GNR3.EntityGroup.EntityGroupID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| DefaultCustomerAutomaticLoyaltyMembership | bit |  |  |  |
| DefaultLoyaltyMemberPatternRef | bigint | Y |  |  |
| AuthenticateWithMobile | bit |  |  |  |
| DefaultFirstName | nvarchar(50) | Y |  |  |
| DefaultLastName | nvarchar(50) | Y |  |  |
| DefaultAddressTitle | nvarchar(50) | Y |  |  |
| FillFirstNameWithCellPhone | bit |  |  |  |
| FillLastNameWithCellPhone | bit |  |  |  |
| OfflineMatchingKeysJson | nvarchar(55) |  |  |  |

ارجاع‌شده توسط: `RMS3.CustomerDefinitionTemplateItem`، `RMS3.CustomerDefinitionTemplateSpecificSearchItem`

## CustomerDefinitionTemplateItem

`RMS3.CustomerDefinitionTemplateItem` — 12 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CustomerDefinitionTemplateItemID | bigint |  | PK |  |
| ColumnName | int |  |  |  |
| IsRequired | bit |  |  |  |
| DisplayOrder | int | Y |  |  |
| SearchOrder | int | Y |  |  |
| CustomerDefinitionTemplateRef | bigint |  | → RMS3.CustomerDefinitionTemplate.CustomerDefinitionTemplateID |  |

## PerformanceSummaryPattern

`RMS3.PerformanceSummaryPattern` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PerformanceSummaryPatternID | bigint |  | PK |  |
| Date | datetime |  |  |  |
| Number | nvarchar(50) |  |  |  |
| Status | int |  |  | `Status`: 2=غیر فعال |
| SystemDefined | bit |  |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `RMS3.AccountGroupConfiguration`، `RMS3.PerformanceSummaryPatternOption`، `RMS3.PerformanceSummaryPatternReceiptPayment`، `RMS3.PerformanceSummaryPatternSales`، `RMS3.PerformanceSummaryPatternSettlement`، `RMS3.PerformanceSummary`

## PerformanceSummaryPatternOption

`RMS3.PerformanceSummaryPatternOption` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PerformanceSummaryPatternOptionID | bigint |  | PK |  |
| PerformanceSummaryPatternRef | bigint |  | → RMS3.PerformanceSummaryPattern.PerformanceSummaryPatternID |  |
| OptionName | nvarchar(100) |  |  |  |

## PerformanceSummaryPatternReceiptPayment

`RMS3.PerformanceSummaryPatternReceiptPayment` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PerformanceSummaryPatternReceiptPaymentID | bigint |  | PK |  |
| PerformanceSummaryPatternRef | bigint |  | → RMS3.PerformanceSummaryPattern.PerformanceSummaryPatternID |  |
| CashierParam | bit |  |  |  |
| CustomerParam | bit |  |  |  |

ارجاع‌شده توسط: `RMS3.PerformanceSummaryReceiptPayment`

## PerformanceSummaryPatternSales

`RMS3.PerformanceSummaryPatternSales` — 3 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PerformanceSummaryPatternSalesID | bigint |  | PK |  |
| PerformanceSummaryPatternRef | bigint |  | → RMS3.PerformanceSummaryPattern.PerformanceSummaryPatternID |  |
| CashierParam | bit |  |  |  |
| CustomerParam | bit |  |  |  |
| ProductParam | bit |  |  |  |
| DocumentPatternParam | bit |  |  |  |
| PolicyParam | bit |  |  |  |
| SalesAreaParam | bit |  |  |  |

ارجاع‌شده توسط: `RMS3.PerformanceSummarySales`

## PerformanceSummaryPatternSettlement

`RMS3.PerformanceSummaryPatternSettlement` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PerformanceSummaryPatternSettlementID | bigint |  | PK |  |
| PerformanceSummaryPatternRef | bigint |  | → RMS3.PerformanceSummaryPattern.PerformanceSummaryPatternID |  |
| CashierParam | bit |  |  |  |

ارجاع‌شده توسط: `RMS3.PerformanceSummarySettlement`

## PriceListTemplate

`RMS3.PriceListTemplate` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PriceListTemplateID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| IsDefault | bit |  |  |  |
| ProductEntityGroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| CustomerEntityGroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| IsEnterpriseWide | bit |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| State | int |  |  |  |
| IsQuickPricingTemplate | bit |  |  |  |
| AutoCalculateFeeFromConsumerFee | bit |  |  |  |
| PricingWithSpecificAccess | bit |  |  |  |

ارجاع‌شده توسط: `RMS3.PriceListTemplateGroupParameter`، `RMS3.PriceListTemplateRetailShop`، `RMS3.PriceList`، `RMS3.PriceListTemplateItemParameter`

## PriceListTemplateItemParameter

`RMS3.PriceListTemplateItemParameter` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PriceListTemplateItemParameterID | bigint |  | PK |  |
| RetailPriceListParameter | int |  |  |  |
| PriceListTemplateRef | bigint |  | → RMS3.PriceListTemplate.PriceListTemplateID |  |
| Priority | int |  |  | `PriorityType`: 1=معمولی |

## ProductCouponProvider

`RMS3.ProductCouponProvider` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ProductCouponProviderID | bigint |  | PK |  |
| Name | nvarchar(500) |  |  |  |
| Title | nvarchar(500) |  |  |  |
| BaseUrl | nvarchar(500) | Y |  |  |
| UserName | nvarchar(500) | Y |  |  |
| Password | nvarchar(500) | Y |  |  |

ارجاع‌شده توسط: `RMS3.HeadOfficePerformanceSummaryPaymentItem`، `RMS3.ProductCouponTransaction`

## RetailDocumentPaperType

`RMS3.RetailDocumentPaperType` — 7 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RetailDocumentPaperTypeID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| Width | float |  |  |  |
| Height | float |  |  |  |
| IsRollPaper | bit |  |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `RMS3.RetailDocumentPrintLayout`

## RetailShopPolicy

`RMS3.RetailShopPolicy` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RetailShopPolicyID | bigint |  | PK |  |
| RetailShopRef | bigint | Y | → RMS3.RetailShop.RetailShopID |  |
| BusinessPolicyRef | bigint |  | → GNR3.BusinessPolicy.BusinessPolicyID |  |
| IsEnterpriseWide | bit |  |  |  |

## SettlementMethod

`RMS3.SettlementMethod` — 9 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementMethodID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| SettlementNatureKey | nvarchar(50) |  |  |  |
| SystemDefined | bit |  |  |  |
| IsInternal | bit |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `RMS3.SettlementMethodAttribute`، `RMS3.SettlementMethodGroupItem`، `RMS3.CustomerSettlementItem`، `RMS3.CustomerSettlementMediator`، `RMS3.RetailLoyaltyProgramCreditSettlementMethod`، `RMS3.RetailLoyaltyProgramPointSettlementMethod`، `RMS3.PerformanceSummaryReceiptPayment`

## SettlementMethodAttribute

`RMS3.SettlementMethodAttribute` — 44 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementMethodAttributeID | bigint |  | PK |  |
| AttributeKey | nvarchar(50) |  |  |  |
| Value | nvarchar(500) | Y |  |  |
| DisplayValue | nvarchar(500) | Y |  |  |
| SettlementMethodRef | bigint |  | → RMS3.SettlementMethod.SettlementMethodID |  |
| Category | int |  |  |  |
| IsVisible | bit |  |  |  |

## SettlementMethodGroup

`RMS3.SettlementMethodGroup` — 10 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementMethodGroupID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| SystemDefined | bit |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| TransactionType | int |  |  | `SettlementMethodGroupTransactionType`: 1=دریافت، 2=پرداخت، 3=دریافت و پرداخت |
| ReturnTransactionType | int |  |  | `SettlementMethodGroupReturnTransactionType`: 1=بازدریافت، 2=بازپرداخت، 3=بازپرداخت و بازدریافت، 4=هیچکدام |
| Type | int |  |  | `SettlementMethodGroupType`: 1=عادی |

ارجاع‌شده توسط: `RMS3.SettlementMethodGroupValidRange`، `RMS3.SettlementMethodGroupItem`، `RMS3.CustomerSettlementMediator`، `RMS3.SettlementPolicy`، `RMS3.SettlementPolicySettlementMethodGroup`

## SettlementMethodGroupItem

`RMS3.SettlementMethodGroupItem` — 12 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementMethodGroupItemID | bigint |  | PK |  |
| Priority | int |  |  | `PriorityType`: 1=معمولی، 2=فوری |
| SettlementMethodGroupRef | bigint |  | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |
| SettlementMethodRef | bigint |  | → RMS3.SettlementMethod.SettlementMethodID |  |

## SettlementPolicy

`RMS3.SettlementPolicy` — 3 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementPolicyID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| State | int |  |  | `State`: 1= فعال |
| ApplyToEntireOrganization | bit |  |  |  |
| IsDefault | bit |  |  |  |
| ApplicabilityType | int |  |  |  |
| MaxCreditPercent | decimal(28,6) |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| AdditionalPayAtReturnSettlementMethodGroupRef | bigint | Y | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |

ارجاع‌شده توسط: `RMS3.PriceChecker`، `RMS3.Invoice`، `RMS3.SettlementPolicyRetailShop`، `RMS3.CustomerSettlementMediator`، `RMS3.ReturnInvoice`، `RMS3.InvoiceItem`، `RMS3.ReturnInvoicePermit`، `RMS3.ScalePricing`، `RMS3.ReturnInvoicePermitItem`، `RMS3.ReturnInvoiceItem`، `RMS3.SalesOrder`، `RMS3.PriceListRetailProduct`، `RMS3.SettlementPolicySettlementMethodGroup`، `RMS3.SalesOrderItem`، `RMS3.RetailDocumentPatternItem`، `RMS3.PriceListGroupParameter`

## SettlementPolicySettlementMethodGroup

`RMS3.SettlementPolicySettlementMethodGroup` — 6 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementPolicySettlementMethodGroupID | bigint |  | PK |  |
| SettlementPolicyRef | bigint |  | → RMS3.SettlementPolicy.SettlementPolicyID |  |
| SettlementMethodGroupRef | bigint |  | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |
| PayAtReturnSettlementMethodGroupRef | bigint | Y | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |
| ReceiveAtReturnSettlementMethodGroupRef | bigint | Y | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |
| MinPercent | decimal(28,6) | Y |  |  |
| MaxPercent | decimal(28,6) | Y |  |  |
| MinAmount | decimal(28,6) | Y |  |  |
| MaxAmount | decimal(28,6) | Y |  |  |
| MorePaymentAllowed | bit |  |  |  |
| Priority | int |  |  | `PriorityType`: 1=معمولی، 2=فوری |
| EquivalentReturnSettlementMethodGroupRef | bigint | Y | → RMS3.SettlementMethodGroup.SettlementMethodGroupID |  |
| HasPriorityAtReturn | bit | Y |  |  |
| IsMinParameteric | bit |  |  |  |

## VirtualCardProvider

`RMS3.VirtualCardProvider` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VirtualCardProviderID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `RMS3.VirtualCardTransaction`، `RMS3.SituationDocumentVirtualCard`، `RMS3.VirtualCard`، `RMS3.OfflineVirtualCardTransaction`، `RMS3.OfflineVirtualCard`
