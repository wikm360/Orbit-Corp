# Schema `RLS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [Installation](#installation) | 3 | 13 | ⚫ نصب/مهاجرت |  |
| [InstallationLog](#installationlog) | 23,450 | 6 | ⚫ نصب/مهاجرت |  |
| [InstalledArtifact](#installedartifact) | 13,497 | 7 | ⚫ نصب/مهاجرت |  |
| [InstalledModule](#installedmodule) | 51 | 7 | ⚫ نصب/مهاجرت |  |
| [RahkaranInstallationJobStep](#rahkaraninstallationjobstep) | 5 | 15 | ⚫ نصب/مهاجرت |  |
| [TierStatus](#tierstatus) | 8 | 7 | ⚫ نصب/مهاجرت |  |

## Installation

`RLS3.Installation` — 3 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| PackageID | uniqueidentifier |  |  |  |
| PackageTitle | nvarchar(500) |  |  |  |
| SelectedModules | nvarchar(max) |  |  |  |
| MasterServerName | nvarchar(100) | Y |  |  |
| StartDate | datetime |  |  |  |
| FinishDate | datetime | Y |  |  |
| ProductVersion | decimal(28,6) |  |  |  |
| ReleaseNumber | int |  |  |  |
| SourceReleaseNumber | int | Y |  |  |
| Succeeded | bit |  |  |  |
| RuntimeParametersValues | nvarchar(max) | Y |  |  |
| HotFixNumber | int | Y |  |  |

ارجاع‌شده توسط: `RLS3.InstallationLog`، `RLS3.InstalledArtifact`، `RLS3.InstalledModule`، `RLS3.TierStatus`

## InstallationLog

`RLS3.InstallationLog` — 23,450 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| InstallationID | bigint |  | → RLS3.Installation.ID |  |
| TierName | nvarchar(100) | Y |  |  |
| Sevirity | int |  |  |  |
| Message | nvarchar(max) |  |  |  |
| Date | datetime |  |  |  |

## InstalledArtifact

`RLS3.InstalledArtifact` — 13,497 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| Name | nvarchar(1000) |  |  |  |
| Version | int |  |  |  |
| Crc | nvarchar(100) |  |  |  |
| InsertDate | datetime |  |  |  |
| LastModificationDate | datetime |  |  |  |
| InstallationID | bigint |  | → RLS3.Installation.ID |  |

## InstalledModule

`RLS3.InstalledModule` — 51 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| Name | nvarchar(100) |  |  |  |
| Title | nvarchar(100) |  |  |  |
| Version | int |  |  |  |
| InstallationID | bigint |  | → RLS3.Installation.ID |  |
| InsertDate | datetime |  |  |  |
| LastModificationDate | datetime |  |  |  |

## RahkaranInstallationJobStep

`RLS3.RahkaranInstallationJobStep` — 5 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RahkaranInstallationJobStepID | bigint |  | PK |  |
| StepName | nvarchar(50) |  |  |  |
| StepName_fa | nvarchar(100) |  |  |  |
| TargetMachineName | nvarchar(100) | Y |  |  |
| TargetComponentName | nvarchar(300) | Y |  |  |
| Status | int |  |  | `Status`: 1=فعال، 2=غیر فعال |
| StatusText | nvarchar(50) |  |  |  |
| ProductVersion | decimal(28,6) | Y |  |  |
| ReleaseNumber | int | Y |  |  |
| HotFixNumber | int | Y |  |  |
| StartTime | datetime2 | Y |  |  |
| EndTime | datetime2 | Y |  |  |
| SetupToolMachineName | nvarchar(100) |  |  |  |
| SetupToolPath | nvarchar(200) |  |  |  |
| VersionName | nvarchar(100) | Y |  |  |

## TierStatus

`RLS3.TierStatus` — 8 rows — ⚫ نصب/مهاجرت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| InstallationID | bigint |  | → RLS3.Installation.ID |  |
| TierName | nvarchar(100) |  |  |  |
| ServerName | nvarchar(100) |  |  |  |
| Status | int |  |  |  |
| Reason | nvarchar(max) | Y |  |  |
| LastStatusReportDate | datetime |  |  |  |
