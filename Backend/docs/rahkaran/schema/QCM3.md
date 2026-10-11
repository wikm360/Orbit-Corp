# Schema `QCM3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [InspectionDocumentRules](#inspectiondocumentrules) | 6 | 6 | 🔴 استفاده‌نشده (seed) |  |
| [InspectionDocumentRulesEvaluation](#inspectiondocumentrulesevaluation) | 24 | 7 | 🔴 استفاده‌نشده (seed) |  |
| [InventoryInspectionDocumentRules](#inventoryinspectiondocumentrules) | 6 | 9 | 🔴 استفاده‌نشده (seed) |  |
| [LogicalOperatorMapping](#logicaloperatormapping) | 1 | 3 | 🔴 استفاده‌نشده (seed) |  |
| [LogicalOperatorMappingOperator](#logicaloperatormappingoperator) | 5 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [StandardSamplingTable](#standardsamplingtable) | 348 | 11 | 🔴 استفاده‌نشده (seed) |  |

## InspectionDocumentRules

`QCM3.InspectionDocumentRules` — 6 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InspectionDocumentRulesID | bigint |  | PK |  |
| AbilityToSpecifySampleValue | bit | Y |  |  |
| AbilityToSpecifyValue | bit | Y |  |  |
| InspectionDocumentType | tinyint |  |  | `InspectionDocumentType`: 1=بازرسی اقلام ورودی، 2=بازرسی حین تولید، 3=بازرسی نهایی تولید، 4=بازرسی مجدد، 5=بازرسی متفرقه، 6=بازرسی پایداری |
| AutoFillAcceptedValue | bit | Y |  |  |

ارجاع‌شده توسط: `QCM3.InventoryInspectionDocumentRules`، `QCM3.InspectionDocumentRulesEvaluation`

## InspectionDocumentRulesEvaluation

`QCM3.InspectionDocumentRulesEvaluation` — 24 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InspectionDocumentRulesEvaluationID | bigint |  | PK |  |
| Title | nvarchar(256) |  |  |  |
| Range | tinyint |  |  | `InspectionDocumentRulesEvaluationRange`: 3=نقطه بازرسی، 4=سند بازرسی/عملیات/نقطه بازرسی |
| Evaluation | tinyint |  |  |  |
| State | tinyint |  |  | `State`: 1= فعال |
| InspectionDocumentRulesRef | bigint |  | → QCM3.InspectionDocumentRules.InspectionDocumentRulesID |  |

ارجاع‌شده توسط: `QCM3.InspectionLot`، `QCM3.InspectionPointValue`، `QCM3.InspectionLotOperation`

## InventoryInspectionDocumentRules

`QCM3.InventoryInspectionDocumentRules` — 6 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| InventoryInspectionDocumentRulesID | bigint |  | PK |  |
| AutoReceiptPermitForDamageAmount | bit | Y |  |  |
| AutoReceiptPermitForConfirmedAmount | bit | Y |  |  |
| AutoIssuePermitForDamageAmount | bit | Y |  |  |
| AutoPartRequestForSampleConsumption | bit | Y |  |  |
| PartRequestType | tinyint | Y |  | `PartRequestType`:  |
| AutoReserveForLotSize | bit | Y |  |  |
| InspectionDocumentRulesRef | bigint |  | → QCM3.InspectionDocumentRules.InspectionDocumentRulesID |  |

## LogicalOperatorMapping

`QCM3.LogicalOperatorMapping` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LogicalOperatorMappingID | bigint |  | PK |  |
| Description | nvarchar(1024) | Y |  |  |

ارجاع‌شده توسط: `QCM3.LogicalOperatorMappingOperator`

## LogicalOperatorMappingOperator

`QCM3.LogicalOperatorMappingOperator` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LogicalOperatorMappingOperatorID | bigint |  | PK |  |
| LogicalOperatorMappingRef | bigint |  | → QCM3.LogicalOperatorMapping.LogicalOperatorMappingID |  |
| Operator | int |  |  |  |

ارجاع‌شده توسط: `QCM3.LogicalOperatorMappingOperatorNotation`

## StandardSamplingTable

`QCM3.StandardSamplingTable` — 348 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StandardSamplingTableID | bigint |  | PK |  |
| StandardType | int |  |  |  |
| VerificationLevel | int |  |  |  |
| LowerLotSize | int | Y |  |  |
| UpperLotSize | int | Y |  |  |
| SamplingPlan | int |  |  | `SamplingPlan`: 1=یکباره، 2=چند باره مستقل |
| CodeLetter | int |  |  | `CodeLetter`: 1=A، 2=B، 3=C، 4=D، 5=E |
| SampleSize | int |  |  |  |
| KValue | decimal(3,2) | Y |  |  |
| FValue | decimal(4,3) | Y |  |  |
