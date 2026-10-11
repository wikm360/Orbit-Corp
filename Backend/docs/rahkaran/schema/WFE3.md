# Schema `WFE3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [Person](#person) | 2 | 7 | 🔴 استفاده‌نشده (seed) |  |

## Person

`WFE3.Person` — 2 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PersonID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| EmailAddress | nvarchar(200) | Y |  |  |
| InteractionType | int |  |  | `PersonInteractionType`: 1=پست الکترونیک |
| Code | nvarchar(50) | Y |  |  |
| ReplacedPersonRef | bigint | Y |  |  |

ارجاع‌شده توسط: `WFE3.SemiStatute`، `SYS3.ProcessInstanceTaskDelivery`، `WFE3.Assignment`، `PRC3.VerificationStep`
