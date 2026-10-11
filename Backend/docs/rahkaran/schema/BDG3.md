# Schema `BDG3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [BudgetEntityCategory](#budgetentitycategory) | 4 | 5 | 🔴 استفاده‌نشده (seed) |  |

## BudgetEntityCategory

`BDG3.BudgetEntityCategory` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BudgetEntityCategoryID | bigint |  | PK |  |
| Title | nvarchar(250) |  |  |  |
| DisplayOrder | tinyint |  |  |  |
| IconKey | nvarchar(50) | Y |  |  |

ارجاع‌شده توسط: `BDG3.BudgetEntityClassification`
