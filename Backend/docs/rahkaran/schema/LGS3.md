# Schema `LGS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AccountGroupConfiguration](#accountgroupconfiguration) | 26 | 14 | 🔴 استفاده‌نشده (seed) |  |
| [DefaultPricingFactorsSharedMethod](#defaultpricingfactorssharedmethod) | 5 | 6 | 🔴 استفاده‌نشده (seed) |  |
| [InventoryVoucherSpecification](#inventoryvoucherspecification) | 47 | 53 | 🔴 استفاده‌نشده (seed) |  |
| [InventoryVoucherSpecificationDetailLedger](#inventoryvoucherspecificationdetailledger) | 2 | 7 | 🔴 استفاده‌نشده (seed) |  |
| [InventoryVoucherSpecificationDetailLedgerType](#inventoryvoucherspecificationdetailledgertype) | 2 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [PartNotice](#partnotice) | 17 | 18 | 🔴 استفاده‌نشده (seed) |  |
| [SerialSubscribingModule](#serialsubscribingmodule) | 2 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [TermOfDelivery](#termofdelivery) | 4 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [TransportationManagementPortalUser](#transportationmanagementportaluser) | 1 | 10 | 🔴 استفاده‌نشده (seed) |  |

## AccountGroupConfiguration

`LGS3.AccountGroupConfiguration` — 26 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountGroupConfigurationID | bigint |  | PK |  |
| AccountGroupName | nvarchar(250) |  |  |  |
| AccountGroupRef | bigint |  |  |  |
| IsParametric | bit |  |  |  |
| SelectedParameters | int | Y |  |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| DL4SourceType | int | Y |  |  |
| DL5SourceType | int | Y |  |  |
| DL6SourceType | int | Y |  |  |
| BusinessPolicyRef | bigint | Y | → GNR3.BusinessPolicy.BusinessPolicyID |  |
| PartGroupingRef | bigint | Y | → GNR3.EntityGrouping.EntityGroupingID |  |
| TrackingFactorRef | bigint | Y | → LGS3.TrackingFactorCharacteristic.TrackingFactorID |  |
| AccountGroupNameInSecondLanguage | nvarchar(250) | Y |  |  |

ارجاع‌شده توسط: `LGS3.AccountGroupConfigurationParameter`

## DefaultPricingFactorsSharedMethod

`LGS3.DefaultPricingFactorsSharedMethod` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DefaultPricingFactorsSharedMethodID | bigint |  | PK |  |
| PricingFactorType | int |  |  | `PricingFactorType`: 1=تخفیف، 2=سایر اضافات فاکتور خرید، 4=کرایه حمل، 32=پیش پرداخت، 256=سایر هزینه ها |
| IsPercent | bit |  |  |  |
| IsShare | bit |  |  |  |
| ShareType | int |  |  | `ShareType`: 0= |

## InventoryVoucherSpecification

`LGS3.InventoryVoucherSpecification` — 47 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InventoryVoucherSpecificationID | bigint |  | PK |  |
| Code | nvarchar(50) |  |  |  |
| Name | nvarchar(250) |  |  |  |
| Direction | int |  |  |  |
| IsReturn | bit |  |  |  |
| MaxRows | int |  |  |  |
| StockCaption | nvarchar(250) |  |  |  |
| Category | int |  |  |  |
| HasDelivererOrReceiver | bit |  |  |  |
| DelivererOrReceiverCaption | nvarchar(250) | Y |  |  |
| HasCounterpartStock | bit |  |  |  |
| CounterpartStockCaption | nvarchar(250) | Y |  |  |
| State | int |  |  | `State`: 1= فعال |
| PartTypes | int |  |  |  |
| TypeOfEffectOnStock | int |  |  |  |
| ValidReferences | bigint |  |  |  |
| DefaultReference | bigint | Y |  |  |
| ReferencedVoucherSpecificationRef | bigint | Y | → LGS3.InventoryVoucherSpecification.InventoryVoucherSpecificationID |  |
| HasReference | bit |  |  |  |
| Visible | bit |  |  |  |
| Editable | bit |  |  |  |
| IsWithoutReference | bit |  |  |  |
| PricingFactor | int |  |  |  |
| NeedsReturnableVoucherItem | bit |  |  |  |
| Additional1 | nvarchar(50) | Y |  |  |
| Additional2 | nvarchar(50) | Y |  |  |
| Additional3 | nvarchar(50) | Y |  |  |
| Additional4 | nvarchar(50) | Y |  |  |
| Additional5 | nvarchar(50) | Y |  |  |
| AdditionalItem1 | nvarchar(50) | Y |  |  |
| AdditionalItem2 | nvarchar(50) | Y |  |  |
| AdditionalItem3 | nvarchar(50) | Y |  |  |
| AdditionalItem4 | nvarchar(50) | Y |  |  |
| AdditionalItem5 | nvarchar(50) | Y |  |  |
| TrackingFactorDialogState | int |  |  | `TrackingFactorDialogState`: 2=پنجره عامل |
| ShowPartTechnicalSpecification | bit |  |  |  |
| ShowPartPropertiesComment | bit |  |  |  |
| ShowPhysicalRemaining | bit |  |  |  |
| ShowCommittableRemaining | bit |  |  |  |
| IsCorectiveVoucher | bit |  |  |  |
| IsAdditional1Required | bit |  |  |  |
| IsAdditional2Required | bit |  |  |  |
| IsAdditional3Required | bit |  |  |  |
| IsAdditional4Required | bit |  |  |  |
| IsAdditional5Required | bit |  |  |  |
| IsAdditionalItem1Required | bit |  |  |  |
| IsAdditionalItem2Required | bit |  |  |  |
| IsAdditionalItem3Required | bit |  |  |  |
| IsAdditionalItem4Required | bit |  |  |  |
| IsAdditionalItem5Required | bit |  |  |  |
| PurchaseType | int | Y |  | `PurchaseType`: 1=جزئی، 2=استعلامی |
| IsPriceDeviation | bit |  |  |  |

ارجاع‌شده توسط: `PAC3.DisassemblingConfirmationConsumedMaterial`، `SCR3.ProcurementDeliveryExtensionScrap`، `PAC3.RoutingProduct`، `PAC3.BomScrap`، `SCR3.ProcurementDirectDeliveryReceiptExtensionScrap`، `PAC3.RoutingComponentAssignment`، `PAC3.ProductionOrder`، `SCR3.SubcontractingOrder`، `LGS3.InventoryVoucherSpecificationDetailLedger`، `PAC3.MaterialWithdrawalDefaultValuesExtension`، `SCR3.ProcurmentOrderExtensionMaterial`، `SCR3.ProcurmentOrderExtensionScrap`، `SCR3.ProcurementDeliveryReturnExtensionScrap`، `LGS3.InventoryVoucherSpecification`، `LGS3.InventorySerialProfileVoucherSpecification`، `PAC3.RoutingScrapAssignment`، `PAC3.ProductionOrderScrap`، `SCR3.SubcontractingOrderMaterial`، `PAC3.ProductionOrderComponent`، `LGS3.HandheldBaseDataBagInventoryVoucherSpecification`، `LGS3.StocktakingPolicy`، `PAC3.BomItem`، `LGS3.InventoryVoucher`، `SCR3.SubcontractingOrderSideProduct`، `SCR3.ProcurementDeliveryExtensionMaterial` …

## InventoryVoucherSpecificationDetailLedger

`LGS3.InventoryVoucherSpecificationDetailLedger` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InventoryVoucherSpecificationDetailLedgerID | bigint |  | PK |  |
| InventoryVoucherSpecificationRef | bigint |  | → LGS3.InventoryVoucherSpecification.InventoryVoucherSpecificationID |  |
| Title | nvarchar(250) |  |  |  |
| Position | int |  |  |  |
| VisibleInItem | bit |  |  |  |
| RequiredOnSaving | bit |  |  |  |

ارجاع‌شده توسط: `LGS3.InventoryVoucherSpecificationDetailLedgerType`

## InventoryVoucherSpecificationDetailLedgerType

`LGS3.InventoryVoucherSpecificationDetailLedgerType` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InventoryVoucherSpecificationDetailLedgerTypeID | bigint |  | PK |  |
| InventoryVoucherSpecificationDetailLedgerRef | bigint |  | → LGS3.InventoryVoucherSpecificationDetailLedger.InventoryVoucherSpecificationDetailLedgerID |  |
| DetailLedgerType | bigint |  |  |  |
| IsDefault | bit |  |  |  |

## PartNotice

`LGS3.PartNotice` — 17 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PartNoticeID | bigint |  | PK |  |
| DefaultName | nvarchar(250) |  |  |  |
| Name | nvarchar(250) |  |  |  |
| Description | nvarchar(1024) |  |  |  |
| NoticeType | int |  |  |  |
| HasConfiguration | bit |  |  |  |
| UIControllerClassType | nvarchar(1024) | Y |  |  |
| ConfigurationData | xml | Y |  |  |
| BusinessControllerClassType | nvarchar(1024) |  |  |  |
| State | int |  |  | `State`: 1= فعال |
| HasEqualCondition | bit |  |  |  |
| DisplayUnitType | int |  |  | `PartNoticeDisplayUnitType`: 1=واحد اصلی |
| CreationDate | datetime |  |  |  |
| LastModificationDate | datetime |  |  |  |
| Creator | bigint |  |  |  |
| LastModifier | bigint |  |  |  |
| PlanningCodeStandardType | int | Y |  |  |

ارجاع‌شده توسط: `PRC3.PartNoticeTiming`، `PRC3.OrderingSuggestion`

## SerialSubscribingModule

`LGS3.SerialSubscribingModule` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SerialSubscribingModuleID | bigint |  | PK |  |
| Title | nvarchar(256) |  |  |  |
| TitleKey | nvarchar(256) |  |  |  |

ارجاع‌شده توسط: `LGS3.SerialProfileSubscribingModule`

## TermOfDelivery

`LGS3.TermOfDelivery` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TermOfDeliveryID | bigint |  | PK |  |
| Name | nvarchar(50) |  |  |  |
| IsMarine | bit |  |  |  |
| TermOfDeliveryType | int |  |  | `TermOfDeliveryType`: 1=FOB، 2=FCA، 3=CFR، 4=CPT |

## TransportationManagementPortalUser

`LGS3.TransportationManagementPortalUser` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TransportationManagementPortalUserID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| IsAdmin | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |
| FirstName | nvarchar(250) | Y |  |  |
| LastName | nvarchar(250) | Y |  |  |
| UserName | nvarchar(50) |  |  |  |
| Password | nvarchar(50) |  |  |  |
| Email | nvarchar(200) | Y |  |  |

ارجاع‌شده توسط: `LGS3.TransportationManagementPortalAssignment`، `LGS3.TransportationManagementPortalUserPermission`، `LGS3.TransportationManagementPortalDistribution`
