# Schema `GNR3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [Address](#address) | 2,005 | 17 | 🔵 اطلاعات پایه فعال |  |
| [Branch](#branch) | 1 | 8 | 🔵 اطلاعات پایه فعال |  |
| [BusinessPolicy](#businesspolicy) | 19 | 22 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyCondition](#businesspolicycondition) | 19 | 12 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyConditionRow](#businesspolicyconditionrow) | 19 | 13 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyInputValue](#businesspolicyinputvalue) | 1 | 8 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyOutputValue](#businesspolicyoutputvalue) | 2 | 8 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyParameter](#businesspolicyparameter) | 77 | 19 | ⚪ تنظیمات/ثابت |  |
| [BusinessPolicyTargetEntity](#businesspolicytargetentity) | 112 | 5 | ⚪ تنظیمات/ثابت |  |
| [Company](#company) | 1 | 12 | 🔵 اطلاعات پایه فعال | یک شرکت: «شرکت محور گستر نصر». |
| [CompanyLedger](#companyledger) | 1 | 4 | ⚪ تنظیمات/ثابت |  |
| [CostCenter](#costcenter) | 511 | 7 | 🔵 اطلاعات پایه فعال | مراکز هزینه (۵۱۱: کارخانه آسفالت، پروژه‌ها، ماشین‌آلات...). Type: 1 اداری،2 تولیدی،3 خدماتی،4 پیمانکار. |
| [Currency](#currency) | 1 | 11 | 🔵 اطلاعات پایه فعال |  |
| [CurrencyExchangeRate](#currencyexchangerate) | 1 | 12 | ⚪ تنظیمات/ثابت |  |
| [DependantCustomerInformationSource](#dependantcustomerinformationsource) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [EntityGrouping](#entitygrouping) | 5 | 11 | ⚪ تنظیمات/ثابت |  |
| [EntitySegmentSetting](#entitysegmentsetting) | 55 | 7 | ⚪ تنظیمات/ثابت |  |
| [FiscalYear](#fiscalyear) | 18 | 5 | 🔵 اطلاعات پایه فعال | سال مالی؛ عنوان سال‌های قدیمی دو رقمی است (88..98) و سال‌های بعد 4 رقمی. تاریخ‌ها در LedgerFiscalYear. |
| [Ledger](#ledger) | 1 | 9 | 🔵 اطلاعات پایه فعال |  |
| [LedgerFiscalYear](#ledgerfiscalyear) | 18 | 10 | 🔵 اطلاعات پایه فعال | بازه‌ی تاریخ و وضعیت بستن هر سال مالی. |
| [MiddlewareInformation](#middlewareinformation) | 1 | 8 | ⚪ تنظیمات/ثابت |  |
| [Party](#party) | 11,815 | 49 | 🔵 اطلاعات پایه فعال | اشخاص حقیقی/حقوقی (Type 0 شخص،1 شرکت). حاوی کد ملی/موبایل — حساس. |
| [PartyAddress](#partyaddress) | 2,003 | 6 | 🔵 اطلاعات پایه فعال |  |
| [Project](#project) | 89 | 5 | 🔵 اطلاعات پایه فعال | پروژه‌ها (۸۹). |
| [RegionalDivision](#regionaldivision) | 342 | 12 | 🔵 اطلاعات پایه فعال |  |
| [SessionLock](#sessionlock) | 26 | 8 | 🟡 لاگ/کش/سیستمی |  |
| [TaxPayerSellerInformation](#taxpayersellerinformation) | 1 | 7 | ⚪ تنظیمات/ثابت |  |

## Address

`GNR3.Address` — 2,005 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AddressID | bigint |  | PK |  |
| Name | nvarchar(128) |  |  |  |
| Details | nvarchar(2048) |  |  |  |
| Details_EN | nvarchar(2048) | Y |  |  |
| ZipCode | nvarchar(32) | Y |  |  |
| Phone | nvarchar(64) |  |  |  |
| Fax | nvarchar(64) | Y |  |  |
| Email | nvarchar(64) | Y |  |  |
| WebPage | nvarchar(256) | Y |  |  |
| RegionalDivisionRef | bigint |  | → GNR3.RegionalDivision.RegionalDivisionID |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| Latitude | nvarchar(64) | Y |  |  |
| Longitude | nvarchar(64) | Y |  |  |

ارجاع‌شده توسط: `SLS3.CustomerAddress`، `LGS3.Plant`، `SLS3.OrderCustomAddress`، `SLS3.SalesOffice`، `SLS3.BrokerAddress`، `SLS3.Order`، `LGS3.TransportationManagementPortalDistribution`، `GNR3.PartyAddress`، `SLS3.OrderItem`

## Branch

`GNR3.Branch` — 1 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BranchID | bigint |  | PK |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| IsStatic | bit |  |  |  |
| CompanyRef | bigint |  | → GNR3.Company.CompanyID |  |
| TaxPayerSystemBranchCode | nvarchar(50) | Y |  |  |

ارجاع‌شده توسط: `HCM3.EmployeeInfo`، `FAM3.Donation`، `PRC3.AccountingVoucherTemplate`، `LGS3.EmptiesVoucher`، `FAM3.TemporaryExit`، `RPA3.CurrentShare`، `RPA3.Reconciliation`، `PRC3.Contract`، `FAM3.ExitPermit`، `RPA3.PayableCollateral`، `FCC3.PaymentInfo`، `FCC3.Tender`، `HCM3.EmployeeConditionItem`، `HCM3.NSVoucherTemplate`، `RPA3.ReceiptRequest`، `HCM3.AttendanceFactorProperty`، `RPA3.AcquisitionCost`، `RPA3.DepositDeployment`، `RPA3.PaymentOrder`، `HCM3.EmployeeBranchInfo`، `PRC3.PaymentInformation`، `RPA3.PaymentRequest`، `HCM3.CompensationComplementRequest`، `LGS3.StocktakingPeriod`، `RPA3.ReceivableCollateral` …

## BusinessPolicy

`GNR3.BusinessPolicy` — 19 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyID | bigint |  | PK |  |
| CompanyRef | bigint |  | → GNR3.Company.CompanyID |  |
| Name | nvarchar(256) |  |  |  |
| Type | nvarchar(256) |  |  |  |
| TargetBaseConcept | nvarchar(256) |  |  |  |
| TargetConcept | nvarchar(256) |  |  |  |
| IsInternal | bit |  |  |  |
| SupportsMultipleResults | bit |  |  |  |
| CalculationMethod | int | Y |  |  |
| Definitiveness | int |  |  |  |
| Enforcement | int |  |  |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime | Y |  |  |
| IsApplicableOnWholeDocument | bit |  |  |  |
| Status | int |  |  | `Status`: 1=فعال |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| EffectType | int | Y |  | `EffectType`: 1=میانگین، 2=ماکزیمم |
| MeasureTag | bit | Y |  |  |

ارجاع‌شده توسط: `PRC3.PurchaseRequestPolicyContextItem`، `SLS3.FreeProductReplacementProduct`، `GNR3.LoyaltyCreditTransaction`، `SLS3.ContractPolicy`، `SLS3.SalesPolicyTextualInterpretation`، `SLS3.NonDefinitiveBusinessPolicyUser`، `GNR3.BusinessPolicyMeasure`، `PRC3.QuotationPolicyContextItem`، `SLS3.SalesStatementPolicyResult`، `GNR3.BusinessPolicyEnforcementProcedureRow`، `PRC3.RefundPolicyContextItem`، `SLS3.SalesOfficePolicy`، `PRC3.PurchaseMiscCostPolicyResult`، `SLS3.PriceList`، `RMS3.BusinessPolicyDependency`، `GNR3.BusinessPolicyTargetEntity`، `XLS3.InvoiceItemPolicyResult`، `SLS3.OrderPolicyResult`، `SLS3.QuotationPolicyResult`، `GNR3.LoyaltyPointTransaction`، `DSD3.AssignmentItemChange`، `PRC3.BusinessPolicyExtraProperty`، `XLS3.ProformaPolicyResult`، `SLS3.SalesPolicyDocumentExtraProperty`، `SLS3.QuotationItemPolicyResult` …

## BusinessPolicyCondition

`GNR3.BusinessPolicyCondition` — 19 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyConditionID | bigint |  | PK |  |
| CompanyRef | bigint |  | → GNR3.Company.CompanyID |  |
| BusinessPolicyRef | bigint |  | → GNR3.BusinessPolicy.BusinessPolicyID |  |
| ConditionModel | int |  |  |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime | Y |  |  |
| Status | int |  |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `SLS3.FreeProductReplacementProduct`، `SLS3.SalesPolicyTextualInterpretation`، `SLS3.SalesStatementPolicyResult`، `PRC3.PurchaseMiscCostPolicyResult`، `XLS3.InvoiceItemPolicyResult`، `SLS3.OrderPolicyResult`، `SLS3.QuotationPolicyResult`، `DSD3.AssignmentItemChange`، `XLS3.ProformaPolicyResult`، `SLS3.QuotationItemPolicyResult`، `SLS3.InvoicePolicyResult`، `SLS3.ReturnPermitPolicyResult`، `IPR3.InsurancePolicyResult`، `SLS3.ReturnPermitItemPolicyResult`، `PRC3.PurchaseRequestPolicyResult`، `SLS3.SaleRequestPolicyResult`، `SLS3.InvoiceItemPolicyResult`، `IPR3.ImportLicencePolicyResult`، `RMS3.InvoicePolicyResult`، `PRC3.RefundPolicyResult`، `XLS3.ProformaItemPolicyResult`، `SLS3.SaleRequestItemPolicyResult`، `GNR3.BusinessPolicyConditionRow`، `RMS3.InvoiceItemPolicyResult`، `SLS3.ContractPolicyResult` …

## BusinessPolicyConditionRow

`GNR3.BusinessPolicyConditionRow` — 19 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyConditionRowID | bigint |  | PK |  |
| BusinessPolicyConditionRef | bigint |  | → GNR3.BusinessPolicyCondition.BusinessPolicyConditionID |  |
| Index | int | Y |  |  |
| Title | nvarchar(512) | Y |  |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime | Y |  |  |
| CreationDate | datetime |  |  |  |
| EndDateModifiedManually | bit | Y |  |  |
| LastModificationManualEndDate | datetime | Y |  |  |
| BusinessPolicyInputRef | bigint |  | → GNR3.BusinessPolicyInputValue.BusinessPolicyInputValueID |  |
| BusinessPolicyOutputRef | bigint | Y | → GNR3.BusinessPolicyOutputValue.BusinessPolicyOutputValueID |  |
| ForceToUnload | bit |  |  |  |

ارجاع‌شده توسط: `SLS3.FreeProductReplacementProduct`، `GNR3.LoyaltyCreditTransaction`، `SLS3.SalesPolicyTextualInterpretation`، `GNR3.LoyaltyCreditTransactionItem`، `PRC3.PurchaseMiscCostPolicyResult`، `XLS3.InvoiceItemPolicyResult`، `GNR3.LoyaltyPointTransaction`، `XLS3.ProformaPolicyResult`، `GNR3.LoyaltyPointTransactionItem`، `SLS3.SaleableWithoutRationingTrackingFactor`، `IPR3.InsurancePolicyResult`، `RMS3.InvoiceItem`، `PRC3.PurchaseRequestPolicyResult`، `IPR3.ImportLicencePolicyResult`، `RMS3.InvoicePolicyResult`، `PRC3.RefundPolicyResult`، `RMS3.InvoiceItemPolicyResult`، `DSD3.AssignmentItemPolicyResult`، `PRC3.OrderPolicyResult`، `IPR3.TransportDocumentPolicyResult`، `PRC3.PurchaseOrderPolicyResult`، `XLS3.OrderPolicyResult`، `RMS3.ReturnInvoiceItem`، `RMS3.ReturnInvoicePolicyResult`، `XLS3.SalesStatementPolicyResult` …

## BusinessPolicyInputValue

`GNR3.BusinessPolicyInputValue` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyInputValueID | bigint |  | PK |  |
| Value | nvarchar(max) |  |  |  |
| HashedValue | varchar(32) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `GNR3.BusinessPolicyConditionRow`

## BusinessPolicyOutputValue

`GNR3.BusinessPolicyOutputValue` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyOutputValueID | bigint |  | PK |  |
| Value | nvarchar(max) |  |  |  |
| HashedValue | varchar(32) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `GNR3.BusinessPolicyConditionRow`

## BusinessPolicyParameter

`GNR3.BusinessPolicyParameter` — 77 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyParameterID | bigint |  | PK |  |
| Name | nvarchar(100) |  |  |  |
| BaseConcept | nvarchar(256) |  |  |  |
| Concept | nvarchar(256) |  |  |  |
| ConceptProperty | nvarchar(40) |  |  |  |
| EntityGroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| AssignmentMethod | int |  |  |  |
| IsDefaultParameter | bit |  |  |  |
| DrillThroughProperty | nvarchar(100) | Y |  |  |
| DrillThroughFieldRef | bigint | Y |  |  |
| DrillThroughPrimitiveIndex | int | Y |  |  |
| DrillThroughPropertyDisplay | nvarchar(100) | Y |  |  |
| IsInternal | bit |  |  |  |
| IsComputational | bit |  |  |  |
| ComputationType | int | Y |  | `BusinessPolicyParameterComputationType`:  |
| GroupingLevel | int | Y |  |  |
| DrillThroughProviderProperty | nvarchar(100) | Y |  |  |
| ProviderFullName | nvarchar(200) | Y |  |  |

ارجاع‌شده توسط: `SLS3.PriceListParametersItem`، `SLS3.RationingSetting`، `SLS3.RationingParallelSegmentation`، `GNR3.BusinessPolicyParameterAssociation`

## BusinessPolicyTargetEntity

`GNR3.BusinessPolicyTargetEntity` — 112 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessPolicyTargetEntityID | bigint |  | PK |  |
| BusinessPolicyRef | bigint |  | → GNR3.BusinessPolicy.BusinessPolicyID |  |
| ComponentName | nvarchar(300) |  |  |  |
| EntityName | nvarchar(512) |  |  |  |

## Company

`GNR3.Company` — 1 rows — 🔵 اطلاعات پایه فعال

یک شرکت: «شرکت محور گستر نصر».

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompanyID | bigint |  | PK |  |
| IsEnterprise | bit |  |  |  |
| Code | nvarchar(64) |  |  |  |
| Name | nvarchar(128) |  |  |  |
| Name_EN | nvarchar(128) | Y |  |  |
| CurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| Status | int |  |  | `Status`: 1=فعال |
| IsCompanyGroup | bit |  |  |  |
| MainOrgCode | nvarchar(50) | Y |  |  |
| MainOrgID | nvarchar(11) | Y |  |  |

ارجاع‌شده توسط: `SLS3.BrokerServiceCutsAndCosts`، `PRC3.CompanyAdminUser`، `GNR3.BusinessPolicyEnforcementProcedure`، `GNR3.CorporateStructureNode`، `GNR3.EntitySegmentAssignment`، `SLS3.Product`، `LGS3.Service`، `SLS3.PaymentAgreement`، `SLS3.OneTimeCustomer`، `SLS3.Broker`، `SLS3.Agent`، `SLS3.ProductPack`، `FSR3.BookletComparitiveReportingPeriodPresentation`، `GNR3.Branch`، `SLS3.Quotation`، `GNR3.BusinessPolicyCondition`، `LGS3.Plant`، `FAM3.CollectorDefaultCompany`، `LGS3.Carrier`، `SLS3.SaleRequest`، `FSR3.ModularTopicInfo`، `FAM3.SettlementPlaceDefaultCompany`، `FSR3.CalculationInformation`، `GNR3.CompanyLedger`، `SLS3.Contract` …

## CompanyLedger

`GNR3.CompanyLedger` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CompanyLedgerID | bigint |  | PK |  |
| CompanyRef | bigint |  | → GNR3.Company.CompanyID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |

## CostCenter

`GNR3.CostCenter` — 511 rows — 🔵 اطلاعات پایه فعال

مراکز هزینه (۵۱۱: کارخانه آسفالت، پروژه‌ها، ماشین‌آلات...). Type: 1 اداری،2 تولیدی،3 خدماتی،4 پیمانکار.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CostCenterID | bigint |  | PK |  |
| Name | nvarchar(256) |  |  |  |
| Number | nvarchar(50) |  |  |  |
| Type | int |  |  | `CostCenterType`: 1=اداری، 2=تولیدی، 3=خدماتی |
| State | int |  |  | `CostCenterState`: 1=فعال، 2=غیرفعال |
| Name_En | nvarchar(256) | Y |  |  |

ارجاع‌شده توسط: `FAM3.InternalTransferItem`، `FAM3.AcquisitionReceiptItem`، `RMS3.RetailDepartment`، `FAM3.AccountConfigurationItem`، `RPA3.PaymentRequest`، `MMG3.EquipmentHistory`، `PRC3.PreOrder`، `FAM3.AssetInventoryItem`، `STM3.ProductStoreConfig`، `SCR3.ProcurementDeliveryReturnExtension`، `FAM3.Asset`، `SCR3.ProcurmentSupplierExtension`، `CAC3.DirectInputMaterial`، `FAM3.InsuranceAccountConfigurationItem`، `CMMS3.WorkOrderEquipment`، `PRC3.AccountGroupLedgerParameterValue`، `MMG3.Equipment`، `MMG3.WorkCenter`، `CAC3.CostCenterDeliveryItem`، `RMS3.RetailInteriorSectionShop`، `CMMS3.InspectionEquipment`، `LGS3.PriceListItem`، `FAM3.AssetInventoryAddition`، `CAC3.BeginningMaterial`، `SLS3.SalesOffice` …

## Currency

`GNR3.Currency` — 1 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CurrencyID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Unit | int |  |  |  |
| Precision | int |  |  |  |
| FractionTitle | nvarchar(128) | Y |  |  |
| FractionTitle_En | nvarchar(128) | Y |  |  |
| RoundingMethod | int |  |  | `CurrencyRoundingMethod`: 3=گرد کردن اتوماتیک |
| Symbol | nvarchar(8) | Y |  |  |
| Abbreviation | nchar(3) |  |  |  |

ارجاع‌شده توسط: `PRC3.PaymentInformation`، `RMS3.SettlementItem`، `FCC3.PaymentInfoItem`، `RPA3.TransferRestorePayableCheque`، `PRC3.PurchaseRequestAmendmentItem`، `RMS3.EPayment`، `SLS3.PriceList`، `RPA3.PaymentOrder`، `IPR3.Clearance`، `RMS3.SettlementSummary`، `SLS3.SalesStatementWageResult`، `RPA3.ReceivableCollateral`، `FAM3.MaintenanceExpenditures`، `PRC3.Refund`، `RPA3.PaymentRequest`، `SCM3.CatalogItem`، `SLS3.SalesOfficeCurrency`، `RMS3.EReceiptTransaction`، `RMS3.CustomerSettlementItem`، `DSD3.TourReceiptMoneyInfo`، `PRC3.PaymentInformationItem`، `RPA3.TransferPayableCheque`، `RMS3.ReturnInvoice`، `RMS3.Cheque`، `FSR3.NatureAdjustmentItem` …

## CurrencyExchangeRate

`GNR3.CurrencyExchangeRate` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CurrencyExchangeRateID | bigint |  | PK |  |
| BaseCurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| CurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| Date | datetime |  |  |  |
| Rate | decimal(28,6) |  |  |  |
| CreationDate | datetime |  |  |  |
| ReverseCalculation | bit |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |

ارجاع‌شده توسط: `PRC3.Refund`، `RPA3.ReceivableNote`، `IPR3.Clearance`، `IPR3.TransportDocument`، `XLS3.Invoice`، `FSR3.AdjustmentVoucherItem`، `SLS3.Quotation`، `FAM3.MaintenanceExpendituresItemPriceElement`، `PRC3.Quotation`، `RPA3.InterestAmountChange`، `XLS3.Order`، `FAM3.SalesPriceElement`، `FCC3.ContractPayCommitment`، `IPR3.Insurance`، `RPA3.TransferCashMoney`، `SLS3.SaleRequest`، `FAM3.SalesItemSalesPriceElement`، `SLS3.Contract`، `PRC3.Invoice`، `LGS3.PricingFactor`، `FIN3.ConversionDocument`، `IPR3.LetterOfCredit`، `IPR3.ImportLicence`، `RPA3.PaymentRestoreReceivableNote`، `RPA3.ReceiptReturnReceivableNote` …

## DependantCustomerInformationSource

`GNR3.DependantCustomerInformationSource` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DependantCustomerInformationSourceID | bigint |  | PK |  |
| GroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| DefaultPostalCodeSource | int |  |  |  |
| DefaultBranchCodeSource | int |  |  |  |

ارجاع‌شده توسط: `GNR3.DependantCustomerInformationSourceItem`

## EntityGrouping

`GNR3.EntityGrouping` — 5 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntityGroupingID | bigint |  | PK |  |
| Name | nvarchar(100) |  |  |  |
| ComponentName | nvarchar(100) |  |  |  |
| EntityName | nvarchar(100) |  |  |  |
| SubtypeKey | nvarchar(100) | Y |  |  |
| SubtypeTitle | nvarchar(100) | Y |  |  |
| IsDisjoint | bit |  |  |  |
| IsInternal | bit |  |  |  |
| IntermediateGroupMembershipEnabled | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `CMMS3.DamageReasonGroupMember`، `RMS3.SettlementMethodGroupValidRange`، `LGS3.PartGroupMember`، `PDS3.CustomerCreditPolicy`، `SLS3.SalesAreaGroupMember`، `SLS3.CalculationBaseTableStructure`، `PDS3.UserCreditLimit`، `SLS3.ForcedProductPlan`، `LGS3.TransportationManagementPortalConfiguration`، `SLS3.ProductGroupMember`، `GNR3.CurrencyGroupMember`، `SYS3.UserGroupMember`، `PRC3.AccountGroupLedger`، `GNR3.BusinessPolicyParameter`، `SLS3.RationingExceptionItem`، `SLS3.BrokerGroupMember`، `GNR3.EntityGroup`، `PRC3.PurchaseItemGroupMembers`، `RMS3.CustomerDefinitionTemplate`، `PDS3.RemainingUntilProductExpiration`، `CMMS3.ProblemGroupMember`، `FIN3.SLGroupMember`، `FIN3.AccountGroupGroupMember`، `SLS3.SelfServiceProductGroupImage`، `SLS3.SelfServiceProductSpecificationConfig` …

## EntitySegmentSetting

`GNR3.EntitySegmentSetting` — 55 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntitySegmentSettingID | bigint |  | PK |  |
| EntityCode | int |  |  |  |
| Discriminator | bigint | Y |  |  |
| IsShared | bit |  |  |  |
| IsCompanyBase | bit |  |  |  |
| IsLedgerBase | bit |  |  |  |

ارجاع‌شده توسط: `GNR3.EntitySegmentAssignment`

## FiscalYear

`GNR3.FiscalYear` — 18 rows — 🔵 اطلاعات پایه فعال

سال مالی؛ عنوان سال‌های قدیمی دو رقمی است (88..98) و سال‌های بعد 4 رقمی. تاریخ‌ها در LedgerFiscalYear.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FiscalYearID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `RPA3.Deposit`، `PRC3.TechnicalInquiry`، `XLS3.Proforma`، `FAM3.TemporaryExit`، `BDG3.BudgetingBatchAmending`، `FAM3.Donation`، `RPA3.CurrentShare`، `XLS3.InvoicePermit`، `PRC3.PurchaseRequestAmendment`، `BDG3.BudgetEntity`، `LGS3.TransportationManagementPortalAssignment`، `RPA3.Reconciliation`، `PRC3.PaymentInformation`، `FAM3.ExitPermit`، `PRC3.Contract`، `RPA3.DepositDeployment`، `RPA3.PaymentOrder`، `CAC3.BeginningWorkInProcess`، `FAM3.MaintenanceExpenditures`، `LGS3.StocktakingPeriod`، `RPA3.DurationChange`، `FAM3.InternalTransfer`، `PRC3.Refund`، `FAM3.ExitFromOrganization`، `PRC3.Order` …

## Ledger

`GNR3.Ledger` — 1 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LedgerID | bigint |  | PK |  |
| Code | int |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| IsLeading | bit |  |  |  |
| IsFinancial | bit |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| State | bit |  |  |  |

ارجاع‌شده توسط: `FIN3.VATBaseInformation`، `QCM3.QualityInspectionResultItem`، `FAM3.TemporaryExit`، `RPA3.CurrentShare`، `BDG3.BudgetingBatchAmending`، `FAM3.Donation`، `RPA3.CollateralType`، `RPA3.Reconciliation`، `BDG3.BudgetEntity`، `RPA3.ContractType`، `FAM3.ExitPermit`، `PRC3.Contract`، `RPA3.PayableCollateral`، `RPA3.DepositDeployment`، `RPA3.AcquisitionCost`، `LGS3.StocktakingPeriod`، `RPA3.PaymentOrder`، `FAM3.MaintenanceExpenditures`، `GNR3.EntitySegmentAssignment`، `FAM3.InternalTransfer`، `FAM3.ExitFromOrganization`، `RPA3.ReceivableCollateral`، `RPA3.DurationChange`، `FCC3.ContractHeader`، `FSR3.CollectiveInformation` …

## LedgerFiscalYear

`GNR3.LedgerFiscalYear` — 18 rows — 🔵 اطلاعات پایه فعال

بازه‌ی تاریخ و وضعیت بستن هر سال مالی.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LedgerFiscalYearID | bigint |  | PK |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime |  |  |  |
| IsGregorian | bit |  |  |  |
| ClosingState | int |  |  |  |
| CapitalSupplementaryPeriodEndDate | datetime | Y |  |  |
| CurrentSupplementaryPeriodEndDate | datetime | Y |  |  |

ارجاع‌شده توسط: `LGS3.FinalizationQuantitativeHistory`، `LGS3.Cardex`، `FAM3.SmallDealsQuorum`، `LGS3.FinalVerificationHistory`

## MiddlewareInformation

`GNR3.MiddlewareInformation` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MiddlewareInformationID | bigint |  | PK |  |
| State | int |  |  | `State`: 1= فعال |
| LastReceiveDateTime | datetime | Y |  |  |
| MiddlewareVersion | nvarchar(100) |  |  |  |
| ComputerName | nvarchar(500) |  |  |  |
| MiddlewarePath | nvarchar(max) |  |  |  |
| IPAddresses | nvarchar(max) |  |  |  |

## Party

`GNR3.Party` — 11,815 rows — 🔵 اطلاعات پایه فعال

اشخاص حقیقی/حقوقی (Type 0 شخص،1 شرکت). حاوی کد ملی/موبایل — حساس.

> ⚠️ **حساس**: کد ملی، موبایل، شناسنامه

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PartyID | bigint |  | PK |  |
| Title | int | Y |  | `PartyTitle`: 1=خانم، 2=آقا، 3=-، 4=890500، 5=SG، 6=آقای، 7=اقای غفار دهقانی، 8=بانک، 9=بانک، 10=بیمه تامین اجتماعی سیرجان، 11=بیمه(ابراهیم)، 12=بیمه(حسین) |
| FirstName | nvarchar(50) | Y |  |  |
| LastName | nvarchar(50) | Y |  |  |
| FullName | nvarchar(101) | Y |  |  |
| Alias | nvarchar(50) | Y |  |  |
| NationalID | nvarchar(20) | Y |  |  |
| Gender | int | Y |  | `Gender`: 1=زن، 2=مرد |
| Nationality | nvarchar(20) | Y |  |  |
| Allegiance | nvarchar(20) | Y |  |  |
| Religion | int | Y |  |  |
| Subreligion | int | Y |  |  |
| Mobile | nvarchar(20) | Y |  |  |
| Email | nvarchar(50) | Y |  |  |
| IDNumber | nvarchar(20) | Y |  |  |
| IDSerial | nvarchar(20) | Y |  |  |
| FatherName | nvarchar(50) | Y |  |  |
| BirthPlaceRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| BirthDate | datetime | Y |  |  |
| IssuanceDate | datetime | Y |  |  |
| IssuancePlaceRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| CompanyCode | nvarchar(20) | Y |  |  |
| Abbreviation | nchar(10) | Y |  |  |
| EconomicCode | nvarchar(20) | Y |  |  |
| RegistrationCode | nvarchar(20) | Y |  |  |
| CompanyType | int | Y |  | `CompanyType`: 1=سهامی خاص |
| ActivityType | nvarchar(50) | Y |  |  |
| Website | nvarchar(30) | Y |  |  |
| ReferenceCompany | nvarchar(50) | Y |  |  |
| Group | nvarchar(50) | Y |  |  |
| CompanyName | nvarchar(100) | Y |  |  |
| Number | nvarchar(50) | Y |  |  |
| Type | int |  |  | `PartyType`: 0=شخص، 1=شرکت |
| FirstName_EN | nvarchar(50) | Y |  |  |
| LastName_EN | nvarchar(50) | Y |  |  |
| CompanyName_EN | nvarchar(100) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |
| Tel | nvarchar(20) | Y |  |  |
| MaritalStatus | int | Y |  | `MaritalStatus`: 1=مجرد، 2=متأهل |
| EducationDegree | int | Y |  | `EducationDegree`: 1=بیسواد، 2=بیسواد و کم سواد، 3=دکترا یا مدرک معادل، 6=فوق دیپلم، 7=فوق لیسانس، 8=لیسانس، 9=نامعلوم |
| MarriageDate | datetime | Y |  |  |
| VATCertificateValidityDate | datetime | Y |  |  |
| FidaRegistration | nvarchar(20) | Y |  |  |
| IsPharmaceuticalSupplier | bit |  |  |  |
| FullName_EN | nvarchar(101) | Y |  |  |

ارجاع‌شده توسط: `LGS3.Transporter`، `HCM3.Institute`، `QAM3.FMEATeamMember`، `FAM3.GasDeploymentItem`، `LGS3.Custom`، `RMS3.RetailInteriorSection`، `CAC3.Contractor`، `LGS3.ShippingOrder`، `XLS3.CollectionNotice`، `LGS3.MaterialClassProposal`، `SLS3.Customer`، `LGS3.UnloadingOrder`، `RPA3.OnlineMoneyTransferItem`، `SLS3.SalesStatement`، `FAM3.AssetTransaction`، `CMMS3.ServiceOperationSubcontract`، `GNR3.Company`، `DSD3.TourProductConflict`، `RPA3.SalesTerminal`، `FIN3.VATParty`، `GNR3.PartyAddress`، `CMMS3.WorkOrderOperation`، `FIN3.Account`، `LGS3.HandheldVoucher`، `MMG3.WorkCenterCapacityPersonnel` …

## PartyAddress

`GNR3.PartyAddress` — 2,003 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PartyAddressID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| AddressRef | bigint |  | → GNR3.Address.AddressID |  |
| IsMainAddress | bit |  |  |  |
| GLNCode | varchar(13) | Y |  |  |

ارجاع‌شده توسط: `LGS3.CustomAddress`، `SCM3.OrderExtension`، `FIN3.VATBaseInformation`

## Project

`GNR3.Project` — 89 rows — 🔵 اطلاعات پایه فعال

پروژه‌ها (۸۹).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ProjectID | bigint |  | PK |  |
| Name | nvarchar(256) |  |  |  |
| Number | nvarchar(50) |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `FAM3.InternalTransferItem`، `FAM3.AcquisitionReceiptItem`، `FAM3.AccountConfigurationItem`، `MMG3.EquipmentHistory`، `CMMS3.Inspection`، `CMMS3.MaintenanceProject`، `FAM3.AssetInventoryItem`، `FAM3.Asset`، `FAM3.InsuranceAccountConfigurationItem`، `CMMS3.WorkOrderEquipment`، `PRC3.AccountGroupLedgerParameterValue`، `MMG3.Equipment`، `CMMS3.WorkOrder`، `CMMS3.InspectionEquipment`، `LGS3.PriceListItem`، `FAM3.AssetInventoryAddition`، `FAM3.AssetTransaction`، `FAM3.RetakeFromStoreItem`، `LGS3.AccountGroupConfigurationParameter`

## RegionalDivision

`GNR3.RegionalDivision` — 342 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RegionalDivisionID | bigint |  | PK |  |
| Name | nvarchar(128) |  |  |  |
| Title_EN | nvarchar(128) | Y |  |  |
| ParentRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| Type | int |  |  | `RegionalDivisionType`: 2=استان، 3=شهر، 4=شهرستان، 5=منطقه |
| Code | nvarchar(64) | Y |  |  |
| Abbreviation | nvarchar(32) | Y |  |  |
| LocalCode | nvarchar(32) | Y |  |  |
| FinanceCode | nvarchar(32) | Y |  |  |
| Version | varbinary(50) |  |  |  |
| Left | int |  |  |  |
| Right | int |  |  |  |

ارجاع‌شده توسط: `XLS3.PriceReferenceItem`، `GNR3.RegionalDivision`، `RPA3.BankBranch`، `XLS3.Proforma`، `FIN3.VatContractCollectiveInformation`، `HCM3.EmployeeRelativeChangeRequest`، `RMS3.Cheque`، `SLS3.OneTimeCustomer`، `FIN3.SeasonalZoneMap`، `IPR3.TransportDocument`، `RPA3.ReceivableNote`، `SLS3.PriceListResultRow`، `SLS3.SalesOfficeRegionalDivision`، `IPR3.Insurance`، `RMS3.BankReceipt`، `FIN3.VATCollectiveInformation`، `SLS3.SalesTerritoryRegion`، `HCM3.MissionDocument`، `HCM3.Post`، `HCM3.Department`، `IPR3.CommercialOrder`، `HCM3.EmployeeRelative`، `HCM3.MissionType`، `HCM3.BatchMissionDocument`، `GNR3.Party` …

## SessionLock

`GNR3.SessionLock` — 26 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SessionLockID | bigint |  | PK |  |
| SessionKey | nvarchar(50) |  |  |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| BranchRef | bigint | Y |  |  |

## TaxPayerSellerInformation

`GNR3.TaxPayerSellerInformation` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TaxPayerSellerInformationID | bigint |  | PK |  |
| PartyType | int |  |  |  |
| NationalID | nvarchar(16) | Y |  |  |
| NationalCode | nvarchar(16) | Y |  |  |
| EconomicID | nvarchar(16) | Y |  |  |
| CivilParticipationID | nvarchar(16) | Y |  |  |
