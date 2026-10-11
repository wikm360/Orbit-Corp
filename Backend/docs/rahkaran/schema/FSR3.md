# Schema `FSR3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [DetailSetting](#detailsetting) | 5 | 10 | ⚪ تنظیمات/ثابت |  |
| [GeneralSetting](#generalsetting) | 1 | 12 | ⚪ تنظیمات/ثابت |  |
| [ReportingStyle](#reportingstyle) | 38 | 11 | ⚪ تنظیمات/ثابت |  |
| [ReportTypeSetting](#reporttypesetting) | 2 | 7 | ⚪ تنظیمات/ثابت |  |
| [Structure](#structure) | 1 | 6 | ⚪ تنظیمات/ثابت |  |

## DetailSetting

`FSR3.DetailSetting` — 5 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DetailSettingID | bigint |  | PK |  |
| ReportType | int |  |  | `ReportType`: 1=گزارش، 2=یادداشت |
| ItemType | int |  |  | `DetailSettingItemType`: 1=ترازنامه، 2=سود و زیان، 3=سود و زیان جامع، 4=گردش وجوه نقد، 5=یادداشت |
| ReportTitle | nvarchar(128) |  |  |  |
| ReportingPeriodFormat | nvarchar(128) |  |  |  |
| Orientation | int |  |  | `Orientation`: 1=عمودی، 2=افقی |
| SeperateAmountByTotalType | bit |  |  |  |
| SeperateAmountByColumnType | bit |  |  |  |
| SeperateTitleByColumnType | bit |  |  |  |

## GeneralSetting

`FSR3.GeneralSetting` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| GeneralSettingID | bigint |  | PK |  |
| FixedEndingExpression | nvarchar(256) | Y |  |  |
| ShowNoteColumn | bit |  |  |  |
| HeaderTextAlign | int |  |  |  |
| ReportTextAlign | int |  |  |  |
| FixedEndingExpressionTextAlign | int |  |  |  |
| HeaderDescriptionTextAlign | int |  |  |  |
| FooterDescriptionTextAlign | int |  |  |  |
| NoteTitleTextAlign | int |  |  |  |
| ShowNotesOnSeperatedPages | bit |  |  |  |
| ApplyNoteGrouping | bit |  |  |  |

## ReportingStyle

`FSR3.ReportingStyle` — 38 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportingStyleID | bigint |  | PK |  |
| CategoryType | int |  |  | `ReportingStyleCategoryType`: 1=اطلاعات سربرگ، 2=اطلاعات سرجمع، 3=اطلاعات عمومی |
| ReportType | int | Y |  | `ReportType`: 1=گزارش، 2=یادداشت |
| ItemType | int |  |  |  |
| FontName | nvarchar(64) |  |  |  |
| FontSize | int |  |  |  |
| FontColor | nvarchar(64) |  |  |  |
| BackGroundColor | nvarchar(64) | Y |  |  |
| IsBold | bit |  |  |  |
| IsItalic | bit |  |  |  |

## ReportTypeSetting

`FSR3.ReportTypeSetting` — 2 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportTypeSettingID | bigint |  | PK |  |
| ReportType | int |  |  | `ReportType`: 1=گزارش، 2=یادداشت |
| OperationalCurrencyAmountFormat | int | Y |  |  |
| AmountFormat | int | Y |  | `AmountFormat`: 1000000=میلیون |
| ShowAmountFormat | bit |  |  |  |
| ShowCompanyName | bit |  |  |  |

## Structure

`FSR3.Structure` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StructureID | bigint |  | PK |  |
| Code | int |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |

ارجاع‌شده توسط: `FSR3.CalculationInformation`، `FSR3.ReportStructure`، `FSR3.BookletStatementOrder`
