# Schema `FAM3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AccountConfiguration](#accountconfiguration) | 86 | 40 | ⚪ تنظیمات/ثابت |  |
| [AccountConfigurationAssetDLType](#accountconfigurationassetdltype) | 73 | 21 | ⚪ تنظیمات/ثابت |  |
| [AccountConfigurationItem](#accountconfigurationitem) | 80 | 51 | ⚪ تنظیمات/ثابت |  |
| [AcquisitionReceipt](#acquisitionreceipt) | 857 | 27 | 🟢 تراکنشی فعال |  |
| [AcquisitionReceiptItem](#acquisitionreceiptitem) | 2,125 | 20 | 🟢 تراکنشی فعال |  |
| [AcquisitionReceiptItemInCalculationArea](#acquisitionreceiptitemincalculationarea) | 2,125 | 14 | ⚪ تنظیمات/ثابت |  |
| [Asset](#asset) | 7,327 | 19 | 🔵 اطلاعات پایه فعال | دارایی ثابت (۷۳۲۷) با PlaqueNumber (شماره پلاک). |
| [AssetClass](#assetclass) | 21 | 10 | 🔵 اطلاعات پایه فعال |  |
| [AssetExtraField](#assetextrafield) | 39 | 7 | 🔵 اطلاعات پایه فعال |  |
| [AssetExtraFieldValue](#assetextrafieldvalue) | 446 | 6 | 🔵 اطلاعات پایه فعال |  |
| [AssetGroup](#assetgroup) | 96 | 7 | 🔵 اطلاعات پایه فعال |  |
| [AssetGroupInCalculationArea](#assetgroupincalculationarea) | 96 | 8 | ⚪ تنظیمات/ثابت |  |
| [AssetInCalculationArea](#assetincalculationarea) | 7,327 | 7 | 🔵 اطلاعات پایه فعال |  |
| [AssetOperationSummary](#assetoperationsummary) | 9,918 | 37 | 🟢 تراکنشی فعال |  |
| [AssetTagTemplate](#assettagtemplate) | 1 | 12 | ⚪ تنظیمات/ثابت |  |
| [AssetTransaction](#assettransaction) | 123,584 | 21 | 🟢 تراکنشی فعال | تراکنش‌های دارایی؛ TransactionType: 1 تحصیل،2 استهلاک،5 فروش،8 حذف،17 انتقال،18 استقرار. |
| [CalculationArea](#calculationarea) | 1 | 12 | ⚪ تنظیمات/ثابت |  |
| [Collector](#collector) | 6 | 6 | 🔵 اطلاعات پایه فعال |  |
| [CostPart](#costpart) | 7,361 | 22 | 🔵 اطلاعات پایه فعال | جزء بهای دارایی و پارامترهای استهلاک؛ IsActive=1 جاری. |
| [CostPartDeploymentExtraInfo](#costpartdeploymentextrainfo) | 584 | 9 | ⚪ تنظیمات/ثابت |  |
| [CostPartTransaction](#costparttransaction) | 121,554 | 24 | 🟢 تراکنشی فعال | جزئیات مبلغی هر تراکنش (استهلاک ماهانه و انباشته). |
| [Depreciation](#depreciation) | 113,332 | 14 | 🟢 تراکنشی فعال | رویداد محاسبه‌ی استهلاک ماهانه. |
| [DepreciationMethod](#depreciationmethod) | 14 | 8 | 🔵 اطلاعات پایه فعال |  |
| [DocumentInCalculationArea](#documentincalculationarea) | 1,056 | 5 | ⚪ تنظیمات/ثابت |  |
| [Elimination](#elimination) | 51 | 21 | 🟢 تراکنشی فعال |  |
| [EliminationItem](#eliminationitem) | 1,980 | 9 | 🟢 تراکنشی فعال |  |
| [EliminationItemInCalculationArea](#eliminationitemincalculationarea) | 1,980 | 6 | ⚪ تنظیمات/ثابت |  |
| [ExitFromOrganization](#exitfromorganization) | 1 | 20 | 🟢 تراکنشی فعال |  |
| [ExitFromOrganizationItem](#exitfromorganizationitem) | 1 | 8 | ⚪ تنظیمات/ثابت |  |
| [ExitFromOrganizationItemInCalculationArea](#exitfromorganizationitemincalculationarea) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [ExpenditureClass](#expenditureclass) | 2 | 7 | ⚪ تنظیمات/ثابت |  |
| [FAMGLComparisonReport](#famglcomparisonreport) | 5 | 6 | ⚪ تنظیمات/ثابت |  |
| [FAMGLComparisonReportItem](#famglcomparisonreportitem) | 19 | 28 | ⚪ تنظیمات/ثابت |  |
| [InsuranceAccountConfiguration](#insuranceaccountconfiguration) | 5 | 39 | ⚪ تنظیمات/ثابت |  |
| [InternalTransfer](#internaltransfer) | 109 | 22 | 🟢 تراکنشی فعال |  |
| [InternalTransferItem](#internaltransferitem) | 823 | 14 | 🟢 تراکنشی فعال |  |
| [InternalTransferItemInCalculationArea](#internaltransferitemincalculationarea) | 823 | 5 | ⚪ تنظیمات/ثابت |  |
| [MaintenanceExpenditures](#maintenanceexpenditures) | 10 | 22 | 🟢 تراکنشی فعال |  |
| [MaintenanceExpendituresItem](#maintenanceexpendituresitem) | 34 | 19 | 🟢 تراکنشی فعال |  |
| [MaintenanceExpendituresItemInCalculationArea](#maintenanceexpendituresitemincalculationarea) | 34 | 7 | ⚪ تنظیمات/ثابت |  |
| [PurchasePriceElement](#purchasepriceelement) | 1 | 6 | ⚪ تنظیمات/ثابت |  |
| [PurchasePriceElementInCalculationArea](#purchasepriceelementincalculationarea) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [ReassignPlaqueNumber](#reassignplaquenumber) | 2,123 | 8 | ⚪ تنظیمات/ثابت |  |
| [Sales](#sales) | 26 | 33 | 🟢 تراکنشی فعال |  |
| [SalesItem](#salesitem) | 87 | 15 | 🟢 تراکنشی فعال |  |
| [SalesItemInCalculationArea](#salesitemincalculationarea) | 87 | 6 | ⚪ تنظیمات/ثابت |  |
| [SettlementPlace](#settlementplace) | 64 | 12 | 🔵 اطلاعات پایه فعال |  |
| [SmallDealsQuorum](#smalldealsquorum) | 1 | 6 | ⚪ تنظیمات/ثابت |  |
| [StandardCurrency](#standardcurrency) | 179 | 5 | ⚪ تنظیمات/ثابت |  |
| [StandardUnit](#standardunit) | 101 | 4 | ⚪ تنظیمات/ثابت |  |
| [VoucherDescription](#voucherdescription) | 2 | 7 | ⚪ تنظیمات/ثابت |  |

## AccountConfiguration

`FAM3.AccountConfiguration` — 86 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountConfigurationID | bigint |  | PK |  |
| CalculationAreaRef | bigint | Y | → FAM3.CalculationArea.CalculationAreaID |  |
| AccountGroupType | int |  |  |  |
| Parameter | int |  |  |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| DLLookup4 | int | Y |  |  |
| DLLookup5 | int | Y |  |  |
| DLLookup6 | int | Y |  |  |
| DLLookup7 | int | Y |  |  |
| DLLookup8 | int | Y |  |  |
| DLLookup9 | int | Y |  |  |
| DLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLookup10 | int | Y |  |  |
| DLLookup11 | int | Y |  |  |
| DLLookup12 | int | Y |  |  |
| DLLookup13 | int | Y |  |  |
| DLLookup14 | int | Y |  |  |
| DLLookup15 | int | Y |  |  |
| DLLookup16 | int | Y |  |  |
| DLLookup17 | int | Y |  |  |
| DLLookup18 | int | Y |  |  |
| DLLookup19 | int | Y |  |  |
| DLLookup20 | int | Y |  |  |
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

ارجاع‌شده توسط: `FAM3.AccountConfigurationItem`، `FAM3.AccountConfigurationAssetDLType`

## AccountConfigurationAssetDLType

`FAM3.AccountConfigurationAssetDLType` — 73 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountConfigurationAssetDLTypeID | bigint |  | PK |  |
| AccountConfigurationRef | bigint |  | → FAM3.AccountConfiguration.AccountConfigurationID |  |
| AccountConfigurationItemRef | bigint | Y | → FAM3.AccountConfigurationItem.AccountConfigurationItemID |  |
| AssetDLTypeRef4 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef5 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef6 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef7 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef8 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef9 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef10 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef11 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef12 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef13 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef14 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef15 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef16 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef17 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef18 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef19 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |
| AssetDLTypeRef20 | bigint | Y | → FAM3.AssetDLType.AssetDLTypeID |  |

## AccountConfigurationItem

`FAM3.AccountConfigurationItem` — 80 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountConfigurationItemID | bigint |  | PK |  |
| AccountConfigurationRef | bigint |  | → FAM3.AccountConfiguration.AccountConfigurationID |  |
| AssetGroupRef | bigint | Y | → FAM3.AssetGroup.AssetGroupID |  |
| AssetClassRef | bigint | Y | → FAM3.AssetClass.AssetClassID |  |
| CostCenterRef | bigint | Y | → GNR3.CostCenter.CostCenterID |  |
| ProjectRef | bigint | Y | → GNR3.Project.ProjectID |  |
| SettlementPlaceRef | bigint | Y | → FAM3.SettlementPlace.SettlementPlaceID |  |
| CollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |
| CurrencyType | int | Y |  | `CurrencyType`:  |
| SalePriceElementType | int | Y |  |  |
| PurchasePriceElementRef | bigint | Y | → FAM3.PurchasePriceElement.PurchasePriceElementID |  |
| AssetStateType | int | Y |  |  |
| StoreRef | bigint | Y | → LGS3.Store.StoreID |  |
| BranchRef | bigint | Y | → GNR3.Branch.BranchID |  |
| ExpenditureType | bigint | Y |  |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| DLLookup4 | int | Y |  |  |
| DLLookup5 | int | Y |  |  |
| DLLookup6 | int | Y |  |  |
| DLLookup7 | int | Y |  |  |
| DLLookup8 | int | Y |  |  |
| DLLookup9 | int | Y |  |  |
| DLLevel4 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel5 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel6 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel7 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel8 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLevel9 | nvarchar(64) | Y | → FIN3.DL.Code |  |
| DLLookup10 | int | Y |  |  |
| DLLookup11 | int | Y |  |  |
| DLLookup12 | int | Y |  |  |
| DLLookup13 | int | Y |  |  |
| DLLookup14 | int | Y |  |  |
| DLLookup15 | int | Y |  |  |
| DLLookup16 | int | Y |  |  |
| DLLookup17 | int | Y |  |  |
| DLLookup18 | int | Y |  |  |
| DLLookup19 | int | Y |  |  |
| DLLookup20 | int | Y |  |  |
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

ارجاع‌شده توسط: `FAM3.AccountConfigurationAssetDLType`

## AcquisitionReceipt

`FAM3.AcquisitionReceipt` — 857 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AcquisitionReceiptID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| State | int |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| Description_En | nvarchar(max) | Y |  |  |
| CurrencyRef | bigint | Y | → GNR3.Currency.CurrencyID |  |
| CurrencyExchangeRateRef | bigint | Y |  |  |
| CurrencyExchangeRate | decimal(28,6) | Y |  |  |
| AcquisitionType | int |  |  | `AcquisitionType`: 1=خرید |
| PartRef | bigint | Y | → LGS3.Part.PartID |  |
| SourceType | int | Y |  |  |
| SourceRef | bigint | Y |  |  |
| CounterPartRef | bigint | Y | → FIN3.DL.DLID |  |
| DealType | int |  |  |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| ReferenceNumber | nvarchar(64) | Y |  |  |
| ReferenceType | int | Y |  | `ReferenceType`:  |
| ReferenceRef | bigint | Y |  |  |
| RegisteredWithMobile | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AcquisitionReceiptItem`

## AcquisitionReceiptItem

`FAM3.AcquisitionReceiptItem` — 2,125 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AcquisitionReceiptItemID | bigint |  | PK |  |
| RowNumber | int |  |  |  |
| PlaqueNumber | nvarchar(64) | Y |  |  |
| Title | nvarchar(256) |  |  |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| SettlementPlaceRef | bigint |  | → FAM3.SettlementPlace.SettlementPlaceID |  |
| CostCenterRef | bigint |  | → GNR3.CostCenter.CostCenterID |  |
| CollectorRef | bigint |  | → FAM3.Collector.CollectorID |  |
| ProjectRef | bigint | Y | → GNR3.Project.ProjectID |  |
| PurchaseAmount | decimal(28,6) |  |  |  |
| OperationalCurrencyPurchaseAmount | decimal(28,6) |  |  |  |
| UtilizationDate | datetime |  |  |  |
| AcquisitionReceiptRef | bigint |  | → FAM3.AcquisitionReceipt.AcquisitionReceiptID |  |
| DelivererRef | bigint | Y | → GNR3.Party.PartyID |  |
| OldPlaqueNumber | nvarchar(64) | Y |  |  |
| GasState | int | Y |  |  |
| GasPermissionNumber | nvarchar(64) | Y |  |  |
| Title_En | nvarchar(256) | Y |  |  |

ارجاع‌شده توسط: `FAM3.GasAssetReformItem`، `FAM3.AcquisitionReceiptItemInCalculationArea`، `FAM3.AcquisitionReceiptItemPurchasePriceElement`

## AcquisitionReceiptItemInCalculationArea

`FAM3.AcquisitionReceiptItemInCalculationArea` — 2,125 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AcquisitionReceiptItemInCalculationAreaID | bigint |  | PK |  |
| AcquisitionReceiptItemRef | bigint |  | → FAM3.AcquisitionReceiptItem.AcquisitionReceiptItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| AssetGroupInCalculationAreaRef | bigint |  | → FAM3.AssetGroupInCalculationArea.AssetGroupInCalculationAreaID |  |
| DepreciationMethodRef | bigint | Y | → FAM3.DepreciationMethod.DepreciationMethodID |  |
| SalvageValue | decimal(28,6) |  |  |  |
| DepreciateInAcquisitionFiscalYear | bit |  |  |  |
| AccumulatedDepreciationValue | decimal(28,6) | Y |  |  |
| GasExpertPrice | decimal(28,6) | Y |  |  |
| Cost | decimal(28,6) | Y |  |  |
| NetPurchaseAmount | decimal(28,6) | Y |  |  |
| IncrementDecrement | decimal(28,6) | Y |  |  |

## Asset

`FAM3.Asset` — 7,327 rows — 🔵 اطلاعات پایه فعال

دارایی ثابت (۷۳۲۷) با PlaqueNumber (شماره پلاک).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetID | bigint |  | PK |  |
| PlaqueNumber | nvarchar(64) | Y |  |  |
| Title | nvarchar(256) |  |  |  |
| PartRef | bigint | Y | → LGS3.Part.PartID |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| AssetClassRef | bigint |  | → FAM3.AssetClass.AssetClassID |  |
| ProjectRef | bigint | Y | → GNR3.Project.ProjectID |  |
| CostCenterRef | bigint |  | → GNR3.CostCenter.CostCenterID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| SettlementPlaceRef | bigint |  | → FAM3.SettlementPlace.SettlementPlaceID |  |
| CollectorRef | bigint |  | → FAM3.Collector.CollectorID |  |
| UtilizationDate | datetime |  |  |  |
| OldPlaqueNumber | nvarchar(64) | Y |  |  |
| CounterPartRef | bigint | Y | → FIN3.DL.DLID |  |
| PhysicalLocation | int |  |  | `PhysicalLocationType`: 1=داخل سازمان |
| DelivererRef | bigint | Y | → GNR3.Party.PartyID |  |
| IsDeployment | bit |  |  |  |
| Title_En | nvarchar(256) | Y |  |  |

ارجاع‌شده توسط: `FAM3.AcquisitionReceiptItem`، `FAM3.RevaluationItem`، `FAM3.InsuranceItem`، `FAM3.AssetReformExtraFieldValue`، `FAM3.ExitPermitItem`، `FAM3.AssetExtraFieldValue`، `FAM3.AssetInventoryItem`، `FAM3.ExitFromOrganizationItem`، `FAM3.TemporaryExitItem`، `FAM3.AssetEquipment`، `FAM3.DonationItem`، `FAM3.GasAssetReformItem`، `FAM3.AssetBarcode`، `FAM3.AssetDLTypeValue`، `FAM3.ChangeRateItem`، `FAM3.ReassignPlaqueNumber`، `FAM3.MaintenanceExpendituresItem`، `FAM3.SendToStoreItem`، `FAM3.SalesItem`، `FAM3.ChangeCostItem`، `FAM3.PermissionRequestItem`، `FAM3.WithdrawalItem`، `FAM3.GasDeploymentItem`، `FAM3.CostPart`، `FAM3.EliminationItem` …

## AssetClass

`FAM3.AssetClass` — 21 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetClassID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| ParentRef | bigint | Y | → FAM3.AssetClass.AssetClassID |  |
| Left | int |  |  |  |
| Right | int |  |  |  |
| LedgerRef | bigint | Y | → GNR3.Ledger.LedgerID |  |
| IsGas | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AccountConfigurationItem`، `FAM3.Asset`، `FAM3.AssetClass`، `FAM3.AssetGroup`، `FAM3.AssetExtraField`

## AssetExtraField

`FAM3.AssetExtraField` — 39 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetExtraFieldID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_EN | nvarchar(128) | Y |  |  |
| AssetClassRef | bigint |  | → FAM3.AssetClass.AssetClassID |  |
| IsFixed | bit |  |  |  |
| DisketteColumnName | nvarchar(256) | Y |  |  |

ارجاع‌شده توسط: `FAM3.AssetReformExtraFieldValue`، `FAM3.AssetExtraFieldValue`، `FAM3.AssetExtraFieldGroup`

## AssetExtraFieldValue

`FAM3.AssetExtraFieldValue` — 446 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetExtraFieldValueID | bigint |  | PK |  |
| AssetExtraFieldRef | bigint |  | → FAM3.AssetExtraField.AssetExtraFieldID |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| Value | nvarchar(255) |  |  |  |
| IsReformed | bit |  |  |  |

## AssetGroup

`FAM3.AssetGroup` — 96 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetGroupID | bigint |  | PK |  |
| AssetClassRef | bigint |  | → FAM3.AssetClass.AssetClassID |  |
| Code | bigint |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| IsActive | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AcquisitionReceiptItem`، `FAM3.AccountConfigurationItem`، `FAM3.Asset`، `FAM3.AssetGroupPart`، `FAM3.Revaluation`، `FAM3.ChangeRateItem`، `FAM3.MaintenanceExpendituresItem`، `FAM3.AssetInventoryAddition`، `FAM3.AssetGroupInCalculationArea`، `FAM3.CostPart`، `FAM3.GasDeploymentItem`، `FAM3.AssetTransaction`، `FAM3.AssetExtraFieldGroup`، `FAM3.GasStandardCodeMapping`، `FAM3.InternalTransferItem`

## AssetGroupInCalculationArea

`FAM3.AssetGroupInCalculationArea` — 96 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetGroupInCalculationAreaID | bigint |  | PK |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| DepreciationMethodRef | bigint | Y | → FAM3.DepreciationMethod.DepreciationMethodID |  |
| SalvageValue | decimal(28,6) |  |  |  |
| MaxDepreciationBookValue | decimal(28,6) |  |  |  |
| IsDepreciable | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AcquisitionReceiptItemInCalculationArea`

## AssetInCalculationArea

`FAM3.AssetInCalculationArea` — 7,327 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetInCalculationAreaID | bigint |  | PK |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| State | int |  |  |  |
| DepreciationType | int |  |  | `DepreciationType`: 1=خیر، 2=بله |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| GasState | int | Y |  |  |

## AssetOperationSummary

`FAM3.AssetOperationSummary` — 9,918 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetOperationSummaryID | bigint |  | PK |  |
| UserRef | bigint |  |  |  |
| CostCenterRef | bigint |  |  |  |
| AssetGroupRef | bigint |  |  |  |
| ProjectRef | bigint | Y |  |  |
| BranchRef | bigint |  |  |  |
| SettlementPlaceRef | bigint |  |  |  |
| AssetRef | bigint |  |  |  |
| InitialCost | decimal(28,6) |  |  |  |
| AcquisitionReceiptCost | decimal(28,6) |  |  |  |
| MaintenanceCost | decimal(28,6) |  |  |  |
| ChangeCost | decimal(28,6) |  |  |  |
| RevaluationCost | decimal(28,6) |  |  |  |
| SalesCost | decimal(28,6) |  |  |  |
| EliminationCost | decimal(28,6) |  |  |  |
| DonationCost | decimal(28,6) |  |  |  |
| ExitFromOrganizationCost | decimal(28,6) |  |  |  |
| TransferInCost | decimal(28,6) |  |  |  |
| TransferOutCost | decimal(28,6) |  |  |  |
| InitialDepreciation | decimal(28,6) |  |  |  |
| AcquisitionReceiptDepreciation | decimal(28,6) |  |  |  |
| CalculatedDepreciation | decimal(28,6) |  |  |  |
| MaintenanceDepreciation | decimal(28,6) |  |  |  |
| ChangeCostDepreciationAdjustment | decimal(28,6) |  |  |  |
| ChangeRateDepreciationAdjustment | decimal(28,6) |  |  |  |
| TransferInDepreciation | decimal(28,6) |  |  |  |
| TransferOutDepreciation | decimal(28,6) |  |  |  |
| SalesDepreciation | decimal(28,6) |  |  |  |
| EliminationDepreciation | decimal(28,6) |  |  |  |
| DonationDepreciation | decimal(28,6) |  |  |  |
| ExitFromOrganizationDepreciation | decimal(28,6) |  |  |  |
| ScrapDepreciation | decimal(28,6) |  |  |  |
| FromOtherOrganizationDepreciation | decimal(28,6) |  |  |  |
| ChangeCostDepreciationAdjustmentPreviousFiscal | decimal(28,6) |  |  |  |
| RemainingRevaluationSurplus | decimal(28,6) |  |  |  |
| RevaluationSurplusDepreciation | decimal(28,6) |  |  |  |
| RevaluationSurplus | decimal(28,6) |  |  |  |

## AssetTagTemplate

`FAM3.AssetTagTemplate` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetTagTemplateID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| SystemicLatinName | nvarchar(50) | Y |  |  |
| IncludedTagFields | bigint |  |  |  |
| Settings | nvarchar(max) |  |  |  |
| ReportData | nvarchar(max) |  |  |  |
| State | int |  |  | `State`: 1= فعال |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

## AssetTransaction

`FAM3.AssetTransaction` — 123,584 rows — 🟢 تراکنشی فعال

تراکنش‌های دارایی؛ TransactionType: 1 تحصیل،2 استهلاک،5 فروش،8 حذف،17 انتقال،18 استقرار.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AssetTransactionID | bigint |  | PK |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AssetState | int |  |  | `AssetState`: -1=در انتظار پلاک گذاری، 1=پلاک شده، 2=فروش رفته، 7=اسقاط شده، 10=حذف شده، 18=خارج شده از سازمان |
| TransactionType | int |  |  |  |
| DocumentState | int |  |  | `DocumentState`: 1=ثبت موقت، 2=تایید شده، 5=سند صادر شده |
| DocumentDate | datetime |  |  |  |
| DocumentNumber | nvarchar(64) | Y |  |  |
| DocumentRef | bigint | Y |  |  |
| ProjectRef | bigint | Y | → GNR3.Project.ProjectID |  |
| CostCenterRef | bigint |  | → GNR3.CostCenter.CostCenterID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| CollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |
| SettlementPlaceRef | bigint |  | → FAM3.SettlementPlace.SettlementPlaceID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| CreationDate | datetime |  |  |  |
| PhysicalLocation | int |  |  | `PhysicalLocationType`: 1=داخل سازمان |
| DelivererRef | bigint | Y | → GNR3.Party.PartyID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| GasState | int | Y |  |  |

ارجاع‌شده توسط: `FAM3.RevaluationItemInCalculationArea`، `FAM3.ExitPermitItemInCalculationArea`، `FAM3.TemporaryExitItemInCalculationArea`، `FAM3.MaintenanceExpendituresItemInCalculationArea`، `FAM3.EliminationItemInCalculationArea`، `FAM3.DonationItemInCalculationArea`، `FAM3.GasAssetReformItemInCalculationArea`، `FAM3.ChangeRateItemInCalculationArea`، `FAM3.AcquisitionReceiptItemInCalculationArea`، `FAM3.SendToStoreItemInCalculationArea`، `FAM3.SalesItemInCalculationArea`، `FAM3.PermissionRequestItemInCalculationArea`، `FAM3.WithdrawalItemInCalculationArea`، `FAM3.ChangeCostItemInCalculationArea`، `FAM3.RetakeFromStoreItemInCalculationArea`، `FAM3.CostPartTransaction`، `FAM3.DefinitiveTransferItemInCalculationArea`، `FAM3.ScrapItemInCalculationArea`، `FAM3.AssetDepreciationItemInCalculationArea`، `FAM3.Depreciation`، `FAM3.ExitFromOrganizationItemInCalculationArea`، `FAM3.InternalTransferItemInCalculationArea`، `FAM3.AccidentItemInCalculationArea`

## CalculationArea

`FAM3.CalculationArea` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CalculationAreaID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| FiscalYearRef | bigint | Y | → GNR3.FiscalYear.FiscalYearID |  |
| FiscalYearStartDate | datetime | Y |  |  |
| VoucherLedgerRef | bigint | Y | → GNR3.Ledger.LedgerID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `FAM3.RevaluationItemInCalculationArea`، `FAM3.AccountConfiguration`، `FAM3.ExitPermitItemInCalculationArea`، `FAM3.TemporaryExitItemInCalculationArea`، `FAM3.SmallDealsQuorum`، `FAM3.MaintenanceExpendituresItemInCalculationArea`، `FAM3.EliminationItemInCalculationArea`، `FAM3.PurchasePriceElementInCalculationArea`، `FAM3.DonationItemInCalculationArea`، `FAM3.GasAssetReformItemInCalculationArea`، `FAM3.ChangeRateItemInCalculationArea`، `FAM3.SendToStoreItemInCalculationArea`، `FAM3.AcquisitionReceiptItemInCalculationArea`، `FAM3.AssetGroupInCalculationArea`، `FAM3.SalesItemInCalculationArea`، `FAM3.AcquisitionReceiptItemPurchasePriceElement`، `FAM3.PermissionRequestItemInCalculationArea`، `FAM3.WithdrawalItemInCalculationArea`، `FAM3.CostPart`، `FAM3.ChangeCostItemInCalculationArea`، `FAM3.RetakeFromStoreItemInCalculationArea`، `FAM3.AssetTransaction`، `FAM3.ScrapItemInCalculationArea`، `FAM3.AssetInCalculationArea`، `FAM3.DefinitiveTransferItemInCalculationArea` …

## Collector

`FAM3.Collector` — 6 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CollectorID | bigint |  | PK |  |
| Code | int |  |  |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| State | int |  |  | `State`: 1= فعال |
| IsDefault | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.InternalTransferItem`، `FAM3.AcquisitionReceiptItem`، `FAM3.CollectorItem`، `FAM3.InternalTransfer`، `FAM3.AssetInventoryItem`، `FAM3.Sales`، `FAM3.AccountConfigurationItem`، `FAM3.Asset`، `FAM3.CollectorDefaultCompany`، `FAM3.AssetInventoryAddition`، `FAM3.Elimination`، `FAM3.GasDeploymentItem`، `FAM3.RetakeFromStoreItem`، `FAM3.DefinitiveTransfer`، `FAM3.AssetTransaction`

## CostPart

`FAM3.CostPart` — 7,361 rows — 🔵 اطلاعات پایه فعال

جزء بهای دارایی و پارامترهای استهلاک؛ IsActive=1 جاری.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CostPartID | bigint |  | PK |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| CostType | int |  |  |  |
| Cost | decimal(28,6) |  |  |  |
| DepreciationCalculationStartDate | datetime |  |  |  |
| UsefulLife | decimal(28,6) | Y |  |  |
| DepreciationMethodRef | bigint | Y |  |  |
| DepreciationMethodType | int | Y |  |  |
| DepreciationRate | decimal(28,6) | Y |  |  |
| DepreciationState | int |  |  |  |
| UtilizationDate | datetime |  |  |  |
| SalvageValue | decimal(28,6) |  |  |  |
| IsActive | bit |  |  |  |
| ParentRef | bigint | Y | → FAM3.CostPart.CostPartID |  |
| RootRef | bigint | Y | → FAM3.CostPart.CostPartID |  |
| BaseBookValue | decimal(28,6) | Y |  |  |
| BaseUsefulLife | decimal(28,6) | Y |  |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| MajorDiscriminator | int | Y |  |  |
| SecondDiscriminator | int | Y |  |  |

ارجاع‌شده توسط: `FAM3.RevaluationItemInCalculationArea`، `FAM3.ChangeRateItemInCalculationArea`، `FAM3.CostPart`، `FAM3.ChangeCostItemInCalculationArea`، `FAM3.CostPartTransaction`، `FAM3.CostPartDeploymentExtraInfo`

## CostPartDeploymentExtraInfo

`FAM3.CostPartDeploymentExtraInfo` — 584 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CostPartDeploymentExtraInfoID | bigint |  | PK |  |
| CostPartRef | bigint |  | → FAM3.CostPart.CostPartID |  |
| LastChangeRateDate | datetime | Y |  |  |
| ChangeRateBaseAccumulatedDepreciation | decimal(28,6) | Y |  |  |
| RevaluationDepreciationMethodRef | bigint | Y | → FAM3.DepreciationMethod.DepreciationMethodID |  |
| RevaluationUsefulLife | decimal(28,6) | Y |  |  |
| ChangeRateUsefulLife | decimal(28,6) | Y |  |  |
| UsefulLife | decimal(28,6) | Y |  |  |

## CostPartTransaction

`FAM3.CostPartTransaction` — 121,554 rows — 🟢 تراکنشی فعال

جزئیات مبلغی هر تراکنش (استهلاک ماهانه و انباشته).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CostPartTransactionID | bigint |  | PK |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CostPartRef | bigint |  | → FAM3.CostPart.CostPartID |  |
| Cost | decimal(28,6) |  |  |  |
| DepreciationMethodRef | bigint | Y | → FAM3.DepreciationMethod.DepreciationMethodID |  |
| DepreciationValue | decimal(28,6) |  |  |  |
| AccumulatedDepreciationValue | decimal(28,6) |  |  |  |
| RevaluationSurplus | decimal(28,6) |  |  |  |
| AccumulatedRevaluationSurplus | decimal(28,6) |  |  |  |
| ImpairmentLoss | decimal(28,6) |  |  |  |
| AccumulatedImpairmentLoss | decimal(28,6) |  |  |  |
| RevaluationRevenue | decimal(28,6) |  |  |  |
| Date | datetime |  |  |  |
| EffectiveDate | datetime |  |  |  |
| CreationDate | datetime |  |  |  |
| ParentRef | bigint | Y | → FAM3.CostPartTransaction.CostPartTransactionID |  |
| Duration | int | Y |  |  |
| CalculationRate | int | Y |  |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| IsActive | bit |  |  |  |
| UsefulLife | decimal(28,6) | Y |  |  |
| DepreciationRate | decimal(28,6) | Y |  |  |
| BaseBookValue | decimal(28,6) | Y |  |  |

ارجاع‌شده توسط: `FAM3.CostPartTransaction`

## Depreciation

`FAM3.Depreciation` — 113,332 rows — 🟢 تراکنشی فعال

رویداد محاسبه‌ی استهلاک ماهانه.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DepreciationID | bigint |  | PK |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| Date | datetime |  |  |  |
| CalculationDate | datetime |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

## DepreciationMethod

`FAM3.DepreciationMethod` — 14 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DepreciationMethodID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) |  |  |  |
| MethodType | int |  |  |  |
| Rate | decimal(28,6) | Y |  |  |
| Usefullife | decimal(28,6) | Y |  |  |
| IsGas | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.RevaluationItemInCalculationArea`، `FAM3.MaintenanceExpendituresItemInCalculationArea`، `FAM3.ChangeRateItemInCalculationArea`، `FAM3.AssetGroupInCalculationArea`، `FAM3.AcquisitionReceiptItemInCalculationArea`، `FAM3.CostPartTransaction`، `FAM3.CostPartDeploymentExtraInfo`

## DocumentInCalculationArea

`FAM3.DocumentInCalculationArea` — 1,056 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DocumentInCalculationAreaID | bigint |  | PK |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| DocumentRef | bigint |  |  |  |
| AssetTransactionType | int |  |  | `AssetTransactionType`: 1=تحصیل، 5=فروش، 8=حذف، 11=مخارج پس از تحصیل، 17=انتقال داخلی، 19=خروج از سازمان |

## Elimination

`FAM3.Elimination` — 51 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EliminationID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| State | int |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Approver | bigint | Y | → SYS3.User.UserID |  |
| ApprovalDate | datetime | Y |  |  |
| ReferenceNumber | nvarchar(512) | Y |  |  |
| ReferenceRef | bigint | Y |  |  |
| ReferenceType | int | Y |  | `ReferenceType`:  |
| CollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |
| PermissionNumber | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `FAM3.EliminationItem`

## EliminationItem

`FAM3.EliminationItem` — 1,980 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EliminationItemID | bigint |  | PK |  |
| EliminationRef | bigint |  | → FAM3.Elimination.EliminationID |  |
| RowNumber | int |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| ExpenditureSide | decimal(28,6) | Y |  |  |
| GasState | int | Y |  |  |

ارجاع‌شده توسط: `FAM3.EliminationItemInCalculationArea`

## EliminationItemInCalculationArea

`FAM3.EliminationItemInCalculationArea` — 1,980 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EliminationItemInCalculationAreaID | bigint |  | PK |  |
| EliminationItemRef | bigint |  | → FAM3.EliminationItem.EliminationItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| Loss | decimal(28,6) |  |  |  |

## ExitFromOrganization

`FAM3.ExitFromOrganization` — 1 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ExitFromOrganizationID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| State | int |  |  |  |
| CounterPartRef | bigint | Y | → FIN3.DL.DLID |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Approver | bigint | Y | → SYS3.User.UserID |  |
| ApprovalDate | datetime | Y |  |  |
| ReferenceNumber | nvarchar(512) | Y |  |  |
| ReferenceRef | bigint | Y |  |  |
| ReferenceType | int | Y |  | `ReferenceType`:  |

ارجاع‌شده توسط: `FAM3.ExitFromOrganizationItem`

## ExitFromOrganizationItem

`FAM3.ExitFromOrganizationItem` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ExitFromOrganizationItemID | bigint |  | PK |  |
| ExitFromOrganizationRef | bigint |  | → FAM3.ExitFromOrganization.ExitFromOrganizationID |  |
| RowNumber | int |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AdditionSubtraction | decimal(28,6) |  |  |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) |  |  |  |

ارجاع‌شده توسط: `FAM3.ExitFromOrganizationItemInCalculationArea`، `FAM3.ExitFromOrganizationItemPriceElement`

## ExitFromOrganizationItemInCalculationArea

`FAM3.ExitFromOrganizationItemInCalculationArea` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ExitFromOrganizationItemInCalculationAreaID | bigint |  | PK |  |
| ExitFromOrganizationItemRef | bigint |  | → FAM3.ExitFromOrganizationItem.ExitFromOrganizationItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |

## ExpenditureClass

`FAM3.ExpenditureClass` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ExpenditureClassID | bigint |  | PK |  |
| Code | int |  |  |  |
| Type | int |  |  | `ExpenditureClassType`: 2=گسترش و الحاق، 3=افزایش قیمت |
| Title | nvarchar(512) |  |  |  |
| Title_En | nvarchar(512) | Y |  |  |
| State | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.MaintenanceExpendituresItem`

## FAMGLComparisonReport

`FAM3.FAMGLComparisonReport` — 5 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FAMGLComparisonReportID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| ToFiscalYearRef | bigint |  |  |  |
| ToDate | datetime |  |  |  |
| FAMGLComparisonAccountGroupType | int |  |  | `FAMGLComparisonAccountGroupType`: 1=بهای تمام شده |
| FAMGLComparisonType | int |  |  | `FAMGLComparisonType`: 1=پایان دوره |

ارجاع‌شده توسط: `FAM3.FAMGLComparisonReportItem`

## FAMGLComparisonReportItem

`FAM3.FAMGLComparisonReportItem` — 19 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FAMGLComparisonReportItemID | bigint |  | PK |  |
| FAMGLComparisonReportRef | bigint |  | → FAM3.FAMGLComparisonReport.FAMGLComparisonReportID |  |
| BranchRef | bigint | Y |  |  |
| AssetClassRef | bigint | Y |  |  |
| AssetGroupRef | bigint | Y |  |  |
| CostCenterRef | bigint | Y |  |  |
| ProjectRef | bigint | Y |  |  |
| SettlementPlaceRef | bigint | Y |  |  |
| SLRef | bigint |  |  |  |
| DL4Code | nvarchar(64) | Y |  |  |
| DL5Code | nvarchar(64) | Y |  |  |
| DL6Code | nvarchar(64) | Y |  |  |
| DL7Code | nvarchar(64) | Y |  |  |
| DL8Code | nvarchar(64) | Y |  |  |
| DL9Code | nvarchar(64) | Y |  |  |
| FAMAmount | decimal(28,6) | Y |  |  |
| GLAmount | decimal(28,6) | Y |  |  |
| DL10Code | nvarchar(64) | Y |  |  |
| DL11Code | nvarchar(64) | Y |  |  |
| DL12Code | nvarchar(64) | Y |  |  |
| DL13Code | nvarchar(64) | Y |  |  |
| DL14Code | nvarchar(64) | Y |  |  |
| DL15Code | nvarchar(64) | Y |  |  |
| DL16Code | nvarchar(64) | Y |  |  |
| DL17Code | nvarchar(64) | Y |  |  |
| DL18Code | nvarchar(64) | Y |  |  |
| DL19Code | nvarchar(64) | Y |  |  |
| DL20Code | nvarchar(64) | Y |  |  |

ارجاع‌شده توسط: `FAM3.FAMGLComparisonReportReason`

## InsuranceAccountConfiguration

`FAM3.InsuranceAccountConfiguration` — 5 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InsuranceAccountConfigurationID | bigint |  | PK |  |
| InsuranceAccountGroupType | int |  |  | `InsuranceAccountGroupType`: 1=پیش پرداخت، 2=هزینه بیمه، 3=رابط پرداخت، 4=مالیات پرداختنی، 5=عوارض پرداختنی |
| Parameter | int |  |  |  |
| SLRef | bigint | Y | → FIN3.SL.SLID |  |
| DLLookup4 | int | Y |  |  |
| DLLookup5 | int | Y |  |  |
| DLLookup6 | int | Y |  |  |
| DLLookup7 | int | Y |  |  |
| DLLookup8 | int | Y |  |  |
| DLLookup9 | int | Y |  |  |
| DLLookup10 | int | Y |  |  |
| DLLookup11 | int | Y |  |  |
| DLLookup12 | int | Y |  |  |
| DLLookup13 | int | Y |  |  |
| DLLookup14 | int | Y |  |  |
| DLLookup15 | int | Y |  |  |
| DLLookup16 | int | Y |  |  |
| DLLookup17 | int | Y |  |  |
| DLLookup18 | int | Y |  |  |
| DLLookup19 | int | Y |  |  |
| DLLookup20 | int | Y |  |  |
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

ارجاع‌شده توسط: `FAM3.InsuranceAccountConfigurationItem`

## InternalTransfer

`FAM3.InternalTransfer` — 109 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InternalTransferID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| DeliveredDate | datetime |  |  |  |
| State | int |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_EN | nvarchar(512) | Y |  |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| DestinationBranchRef | bigint |  |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Approver | bigint | Y | → SYS3.User.UserID |  |
| ApprovalDate | datetime | Y |  |  |
| Type | int |  |  | `InternalTransferType`: 1=انتقال داخلی |
| ReferenceRef | bigint | Y |  |  |
| ReferenceType | int | Y |  | `ReferenceType`:  |
| CollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |

ارجاع‌شده توسط: `FAM3.InternalTransferItem`

## InternalTransferItem

`FAM3.InternalTransferItem` — 823 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InternalTransferItemID | bigint |  | PK |  |
| InternalTransferRef | bigint |  | → FAM3.InternalTransfer.InternalTransferID |  |
| RowNumber | int |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AssetGroupRef | bigint | Y | → FAM3.AssetGroup.AssetGroupID |  |
| SettlementPlaceRef | bigint | Y |  |  |
| CostCenterRef | bigint | Y | → GNR3.CostCenter.CostCenterID |  |
| CollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |
| ProjectRef | bigint | Y | → GNR3.Project.ProjectID |  |
| Description | nvarchar(512) | Y |  |  |
| Description_EN | nvarchar(512) | Y |  |  |
| DelivererRef | bigint | Y | → GNR3.Party.PartyID |  |
| EquipmentHistoryRef | bigint | Y | → MMG3.EquipmentHistory.EquipmentHistoryID |  |

ارجاع‌شده توسط: `FAM3.InternalTransferItemInCalculationArea`

## InternalTransferItemInCalculationArea

`FAM3.InternalTransferItemInCalculationArea` — 823 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InternalTransferItemInCalculationAreaID | bigint |  | PK |  |
| InternalTransferItemRef | bigint |  | → FAM3.InternalTransferItem.InternalTransferItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |

## MaintenanceExpenditures

`FAM3.MaintenanceExpenditures` — 10 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MaintenanceExpendituresID | bigint |  | PK |  |
| SourceType | int | Y |  |  |
| SourceRef | bigint | Y |  |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| State | int |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| CurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| CurrencyExchangeRate | decimal(28,6) |  |  |  |
| CurrencyExchangeRateRef | bigint | Y | → GNR3.CurrencyExchangeRate.CurrencyExchangeRateID |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Approver | bigint | Y | → SYS3.User.UserID |  |
| ApprovalDate | datetime | Y |  |  |
| ReferenceNumber | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `FAM3.MaintenanceExpendituresItem`

## MaintenanceExpendituresItem

`FAM3.MaintenanceExpendituresItem` — 34 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MaintenanceExpendituresItemID | bigint |  | PK |  |
| MaintenanceExpendituresRef | bigint |  | → FAM3.MaintenanceExpenditures.MaintenanceExpendituresID |  |
| RowNumber | int |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| ExpenditureClassRef | bigint |  | → FAM3.ExpenditureClass.ExpenditureClassID |  |
| AssetGroupRef | bigint |  | → FAM3.AssetGroup.AssetGroupID |  |
| Amount | decimal(28,6) |  |  |  |
| OperationalCurrencyAmount | decimal(28,6) |  |  |  |
| IncrementDecrement | decimal(28,6) |  |  |  |
| NetPurchaseAmount | decimal(28,6) |  |  |  |
| Cost | decimal(28,6) |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| CounterPartRef | bigint | Y | → FIN3.DL.DLID |  |
| DealType | int |  |  |  |
| ItemOrService | int |  |  | `ItemOrService`: 1=کالا |
| MajorDiscriminator | int | Y |  |  |
| SecondDiscriminator | int | Y |  |  |

ارجاع‌شده توسط: `FAM3.MaintenanceExpendituresItemPriceElement`، `FAM3.MaintenanceExpendituresItemInCalculationArea`

## MaintenanceExpendituresItemInCalculationArea

`FAM3.MaintenanceExpendituresItemInCalculationArea` — 34 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MaintenanceExpendituresItemInCalculationAreaID | bigint |  | PK |  |
| MaintenanceExpendituresItemRef | bigint |  | → FAM3.MaintenanceExpendituresItem.MaintenanceExpendituresItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| DepreciationMethodRef | bigint | Y | → FAM3.DepreciationMethod.DepreciationMethodID |  |
| SalvageValue | decimal(28,6) |  |  |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |

## PurchasePriceElement

`FAM3.PurchasePriceElement` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PurchasePriceElementID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) |  |  |  |
| ElementType | int |  |  | `ElementType`: 1=واحد سازمانی |
| IsAffectingCost | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AccountConfigurationItem`، `FAM3.MaintenanceExpendituresItemPriceElement`، `FAM3.PurchasePriceElementInCalculationArea`، `FAM3.AcquisitionReceiptItemPurchasePriceElement`، `FAM3.ChangeCostItemPriceElement`

## PurchasePriceElementInCalculationArea

`FAM3.PurchasePriceElementInCalculationArea` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PurchasePriceElementInCalculationAreaID | bigint |  | PK |  |
| PurchasePriceElementRef | bigint |  | → FAM3.PurchasePriceElement.PurchasePriceElementID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| IsAffectingCost | bit |  |  |  |

## ReassignPlaqueNumber

`FAM3.ReassignPlaqueNumber` — 2,123 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReassignPlaqueNumberID | bigint |  | PK |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| CurrentPlaqueNumber | nvarchar(64) |  |  |  |
| NewPlaqueNumber | nvarchar(64) |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| Date | datetime |  |  |  |

## Sales

`FAM3.Sales` — 26 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Date | datetime |  |  |  |
| State | int |  |  |  |
| CounterPartRef | bigint |  | → FIN3.DL.DLID |  |
| DealType | int |  |  |  |
| CurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| CurrencyExchangeRate | decimal(28,6) | Y |  |  |
| CurrencyExchangeRateRef | bigint | Y |  |  |
| Description | nvarchar(512) |  |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| FiscalYearRef | bigint |  | → GNR3.FiscalYear.FiscalYearID |  |
| IsBatch | bit |  |  |  |
| BatchAmount | decimal(28,6) | Y |  |  |
| BatchAllocationType | int | Y |  | `BatchAllocationType`:  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| Approver | bigint | Y | → SYS3.User.UserID |  |
| ApprovalDate | datetime | Y |  |  |
| ReferenceNumber | nvarchar(512) | Y |  |  |
| ReferenceRef | bigint | Y |  |  |
| ReferenceType | int | Y |  | `ReferenceType`:  |
| GasSalesLicenseNumber | nvarchar(50) | Y |  |  |
| GasCollectorRef | bigint | Y | → FAM3.Collector.CollectorID |  |
| GasPurchaserOrganizationRef | bigint | Y | → FIN3.DL.DLID |  |
| GasBuyerPersonRef | bigint | Y | → FIN3.DL.DLID |  |
| GasSalesManagerRef | bigint | Y | → FIN3.DL.DLID |  |
| CivilPartnershipID | nvarchar(40) | Y |  |  |

ارجاع‌شده توسط: `FAM3.SalesPriceElement`، `FAM3.SalesItem`

## SalesItem

`FAM3.SalesItem` — 87 rows — 🟢 تراکنشی فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesItemID | bigint |  | PK |  |
| SalesRef | bigint |  | → FAM3.Sales.SalesID |  |
| RowNumber | int |  |  |  |
| AssetRef | bigint |  | → FAM3.Asset.AssetID |  |
| AdditionSubtraction | decimal(28,6) |  |  |  |
| NetSales | decimal(28,6) |  |  |  |
| SalesAmount | decimal(28,6) |  |  |  |
| OperationalCurrencySalesAmount | decimal(28,6) |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| GasDepositReceiptNumber | nvarchar(50) | Y |  |  |
| GasDepositReceiptDate | datetime | Y |  |  |
| GasDepositAmount | decimal(28,6) | Y |  |  |
| GasTreasuryAccountNumber | nvarchar(50) | Y |  |  |

ارجاع‌شده توسط: `FAM3.SalesItemSalesPriceElement`، `FAM3.SalesItemInCalculationArea`

## SalesItemInCalculationArea

`FAM3.SalesItemInCalculationArea` — 87 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SalesItemInCalculationAreaID | bigint |  | PK |  |
| SalesItemRef | bigint |  | → FAM3.SalesItem.SalesItemID |  |
| AssetTransactionRef | bigint |  | → FAM3.AssetTransaction.AssetTransactionID |  |
| CalculationAreaRef | bigint |  | → FAM3.CalculationArea.CalculationAreaID |  |
| SalesCostAndBenefit | decimal(28,6) |  |  |  |

## SettlementPlace

`FAM3.SettlementPlace` — 64 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SettlementPlaceID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| ParentRef | bigint | Y | → FAM3.SettlementPlace.SettlementPlaceID |  |
| Left | int |  |  |  |
| Right | int |  |  |  |
| IsStatic | bit |  |  |  |
| StaticSettlementPlaceType | int | Y |  |  |
| IsDefault | bit |  |  |  |
| IsActive | bit |  |  |  |

ارجاع‌شده توسط: `FAM3.AcquisitionReceiptItem`، `FAM3.CollectorItem`، `FAM3.AccountConfigurationItem`، `FAM3.AssetInventoryItem`، `FAM3.TemporaryExitItem`، `FAM3.Asset`، `FAM3.SettlementPlaceDefaultCompany`، `FAM3.AssetInventoryAddition`، `FAM3.SettlementPlace`، `FAM3.GasDeploymentItem`، `FAM3.RetakeFromStoreItem`، `FAM3.AssetTransaction`

## SmallDealsQuorum

`FAM3.SmallDealsQuorum` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SmallDealsQuorumID | bigint |  | PK |  |
| LedgerFiscalYearRef | bigint |  | → GNR3.LedgerFiscalYear.LedgerFiscalYearID |  |
| QuorumAmount | decimal(28,6) |  |  |  |
| PercentageAmount | decimal(28,6) |  |  |  |
| CalculationAreaRef | bigint | Y | → FAM3.CalculationArea.CalculationAreaID |  |

## StandardCurrency

`FAM3.StandardCurrency` — 179 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StandardCurrencyID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Sign | nvarchar(10) |  |  |  |
| Title | nvarchar(100) |  |  |  |

ارجاع‌شده توسط: `FAM3.StandardCurrencyMap`

## StandardUnit

`FAM3.StandardUnit` — 101 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StandardUnitID | bigint |  | PK |  |
| Code | bigint |  |  |  |
| Name | nvarchar(50) |  |  |  |

ارجاع‌شده توسط: `FAM3.StandardUnitMap`

## VoucherDescription

`FAM3.VoucherDescription` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| VoucherDescriptionID | bigint |  | PK |  |
| Description | nvarchar(512) |  |  |  |
| EntityCode | int | Y |  |  |
| Discriminator | nvarchar(125) | Y |  |  |
| AccountGroupType | int | Y |  |  |
| IsDebit | bit |  |  |  |
