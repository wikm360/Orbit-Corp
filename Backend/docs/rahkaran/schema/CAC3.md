# Schema `CAC3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [CalculationLogCatalog](#calculationlogcatalog) | 43 | 5 | 🔴 استفاده‌نشده (seed) |  |

## CalculationLogCatalog

`CAC3.CalculationLogCatalog` — 43 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| CalculationLogCatalogID | bigint |  | PK |  |
| Number | bigint |  |  |  |
| CatalogType | int |  |  |  |
| Editable | bit |  |  |  |

ارجاع‌شده توسط: `CAC3.CalculationStepLog`
