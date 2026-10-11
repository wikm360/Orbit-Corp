# Schema `CNV3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [CompensationFactorMapping](#compensationfactormapping) | 118 | 5 | ⚫ نصب/مهاجرت |  |
| [CurrencyMap](#currencymap) | 172 | 5 | ⚫ نصب/مهاجرت |  |
| [DLTypeMap](#dltypemap) | 17 | 4 | ⚫ نصب/مهاجرت |  |
| [Log](#log) | 21,857 | 5 | 🟡 لاگ/کش/سیستمی |  |
| [RegionalDivisionMap](#regionaldivisionmap) | 198 | 3 | ⚫ نصب/مهاجرت |  |
| [StaticAttendanceFactorMapping](#staticattendancefactormapping) | 5 | 4 | ⚫ نصب/مهاجرت |  |
| [StaticCompensationFactorMapping](#staticcompensationfactormapping) | 85 | 4 | ⚫ نصب/مهاجرت |  |
| [VoucherTypeMap](#vouchertypemap) | 26 | 7 | ⚫ نصب/مهاجرت |  |

## CompensationFactorMapping

`CNV3.CompensationFactorMapping` — 118 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RahkaranID | bigint |  |  |  |
| RahkaranName | varchar(255) |  |  |  |
| RahkaranTitle | nvarchar(400) |  |  |  |
| RahkaranIsFinancialStatute | bit |  |  |  |
| DelphiName | varchar(15) | Y |  |  |

## CurrencyMap

`CNV3.CurrencyMap` — 172 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Abbreviation | char(3) |  | PK |  |
| Title | nvarchar(128) | Y |  |  |
| Title_En | nvarchar(128) | Y |  |  |
| Symbol | nvarchar(8) | Y |  |  |
| Delphi_Serial | int | Y |  |  |

## DLTypeMap

`CNV3.DLTypeMap` — 17 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DLTypeMapID | bigint |  | PK |  |
| Delphi_DLType | int |  |  |  |
| G3_DLTypeID | bigint |  |  |  |
| Manual | bit |  |  |  |

## Log

`CNV3.Log` — 21,857 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LogID | bigint |  | PK |  |
| Date | datetime |  |  |  |
| FileName | nvarchar(200) |  |  |  |
| Type | char(1) |  |  |  |
| Message | nvarchar(500) |  |  |  |

## RegionalDivisionMap

`CNV3.RegionalDivisionMap` — 198 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Delphi_Serial | int |  | PK |  |
| Title | nvarchar(50) |  |  |  |
| Type | int |  |  |  |

## StaticAttendanceFactorMapping

`CNV3.StaticAttendanceFactorMapping` — 5 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RahkaranName | varchar(255) |  |  |  |
| RahkaranTitle | nvarchar(400) | Y |  |  |
| RahkaranDescription | nvarchar(max) | Y |  |  |
| DelphiName | varchar(15) |  |  |  |

## StaticCompensationFactorMapping

`CNV3.StaticCompensationFactorMapping` — 85 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RahkaranName | varchar(255) |  |  |  |
| RahkaranTitle | nvarchar(400) | Y |  |  |
| RahkaranDescription | nvarchar(max) | Y |  |  |
| DelphiName | varchar(15) |  |  |  |

## VoucherTypeMap

`CNV3.VoucherTypeMap` — 26 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Delphi_SystemRef | varchar(5) |  | PK |  |
| Delphi_Code | int |  | PK |  |
| Delphi_Title | nvarchar(50) |  |  |  |
| G3_OwnerSystem | nvarchar(3) | Y |  |  |
| G3_Code | int | Y |  |  |
| G3_Title | nvarchar(128) |  |  |  |
| Manual | bit |  |  |  |
