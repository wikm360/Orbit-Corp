# Schema `SCM3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [DownloadSettings](#downloadsettings) | 8 | 6 | 🔴 استفاده‌نشده (seed) |  |
| [UploadSettings](#uploadsettings) | 11 | 6 | 🔴 استفاده‌نشده (seed) |  |

## DownloadSettings

`SCM3.DownloadSettings` — 8 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DownloadSettingsID | bigint |  | PK |  |
| DocumentType | int |  |  |  |
| Enabled | bit |  |  |  |
| LastTimestamp | datetime | Y |  |  |
| Url | nvarchar(200) |  |  |  |

## UploadSettings

`SCM3.UploadSettings` — 11 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| UploadSettingsID | bigint |  | PK |  |
| DocumentType | int |  |  |  |
| Enabled | bit |  |  |  |
| LastTimestamp | datetime | Y |  |  |
| Url | nvarchar(200) |  |  |  |
