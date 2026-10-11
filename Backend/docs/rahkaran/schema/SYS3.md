# Schema `SYS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [BusinessRuleActionExecutionLog](#businessruleactionexecutionlog) | 57,913 | 8 | 🟡 لاگ/کش/سیستمی |  |
| [ConfigurationGroup](#configurationgroup) | 2,925 | 4 | ⚪ تنظیمات/ثابت |  |
| [ConfigurationValue](#configurationvalue) | 3,658 | 8 | ⚪ تنظیمات/ثابت |  |
| [DashboardCategory](#dashboardcategory) | 7 | 8 | ⚪ تنظیمات/ثابت |  |
| [DataTransferMethod](#datatransfermethod) | 17 | 15 | ⚪ تنظیمات/ثابت |  |
| [DBSignature](#dbsignature) | 1 | 2 | ⚪ تنظیمات/ثابت |  |
| [DynamicReport](#dynamicreport) | 18 | 14 | 🔵 اطلاعات پایه فعال | گزارش‌های ساخته‌شده توسط کاربران (بیمه، مالیات، وام، لیست حقوق...) — نشان‌دهنده‌ی نیاز واقعی واحد حقوق. |
| [EntityEvent](#entityevent) | 17 | 4 | ⚪ تنظیمات/ثابت |  |
| [EntityGeneralNotification](#entitygeneralnotification) | 22 | 9 | ⚪ تنظیمات/ثابت |  |
| [EntityLookup](#entitylookup) | 2,595 | 2 | 🔵 اطلاعات پایه فعال |  |
| [EntityRecordNotification](#entityrecordnotification) | 10 | 10 | ⚪ تنظیمات/ثابت |  |
| [EntityReport](#entityreport) | 37 | 7 | ⚪ تنظیمات/ثابت |  |
| [Filter](#filter) | 1 | 8 | ⚪ تنظیمات/ثابت |  |
| [JalaliStartDate](#jalalistartdate) | 181 | 1 | 🔵 اطلاعات پایه فعال | تاریخ میلادی شروع سال‌های جلالی (برای تبدیل تاریخ). |
| [Job](#job) | 2,548 | 14 | 🟡 لاگ/کش/سیستمی |  |
| [LogicalResource](#logicalresource) | 3 | 10 | ⚪ تنظیمات/ثابت |  |
| [Lookup](#lookup) | 7,383 | 10 | 🔵 اطلاعات پایه فعال | قاموس enum های سیستم (Type, Code, Value فارسی). |
| [LookupInfo](#lookupinfo) | 1,679 | 8 | 🔵 اطلاعات پایه فعال |  |
| [LookupTranslation](#lookuptranslation) | 6,606 | 5 | 🔵 اطلاعات پایه فعال |  |
| [NumberingMethod](#numberingmethod) | 309 | 14 | ⚪ تنظیمات/ثابت |  |
| [NumberingMethodEntityAttribute](#numberingmethodentityattribute) | 309 | 6 | ⚪ تنظیمات/ثابت |  |
| [NumberingMethodRange](#numberingmethodrange) | 383 | 9 | ⚪ تنظیمات/ثابت |  |
| [NumberingRangeReservation](#numberingrangereservation) | 1,571 | 4 | ⚪ تنظیمات/ثابت |  |
| [NumberingReseterAttribute](#numberingreseterattribute) | 7 | 6 | ⚪ تنظیمات/ثابت |  |
| [OutgoingMessage](#outgoingmessage) | 72 | 13 | 🟡 لاگ/کش/سیستمی |  |
| [PasswordHistory](#passwordhistory) | 120 | 5 | 🟡 لاگ/کش/سیستمی |  |
| [Portal](#portal) | 1 | 4 | ⚪ تنظیمات/ثابت |  |
| [ReportPathMapping](#reportpathmapping) | 1 | 5 | ⚪ تنظیمات/ثابت |  |
| [Schedule](#schedule) | 16 | 15 | 🔵 اطلاعات پایه فعال |  |
| [SecurityEvent](#securityevent) | 4,716 | 13 | 🟡 لاگ/کش/سیستمی |  |
| [SecurityPolicy](#securitypolicy) | 35,879 | 11 | 🟡 لاگ/کش/سیستمی |  |
| [SetupValues](#setupvalues) | 1 | 2 | ⚪ تنظیمات/ثابت |  |
| [ShellNotification](#shellnotification) | 1,527 | 10 | 🟡 لاگ/کش/سیستمی |  |
| [SQLScriptExecutionLog](#sqlscriptexecutionlog) | 5,612 | 10 | 🟡 لاگ/کش/سیستمی |  |
| [StateHistory](#statehistory) | 282,020 | 12 | 🟡 لاگ/کش/سیستمی |  |
| [StaticID](#staticid) | 37,033 | 2 | 🟡 لاگ/کش/سیستمی |  |
| [TableIdGenBacking](#tableidgenbacking) | 369 | 2 | 🟡 لاگ/کش/سیستمی |  |
| [User](#user) | 45 | 21 | 🔵 اطلاعات پایه فعال | کاربران سیستم؛ ستون Password — هرگز در دسترس LLM نباشد. |
| [UserLogonAudit](#userlogonaudit) | 33,315 | 10 | 🟡 لاگ/کش/سیستمی |  |
| [UserShellNotification](#usershellnotification) | 1,527 | 8 | 🟡 لاگ/کش/سیستمی |  |

## BusinessRuleActionExecutionLog

`SYS3.BusinessRuleActionExecutionLog` — 57,913 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BusinessRuleActionExecutionLogID | bigint |  | PK |  |
| BusinessEventRuleActionRef | bigint | Y | → SYS3.BusinessEventRuleAction.BusinessEventRuleActionID |  |
| Name | nvarchar(200) | Y |  |  |
| RuleResult | nvarchar(max) |  |  |  |
| RuleDuration | bigint |  |  |  |
| ActionResult | nvarchar(max) | Y |  |  |
| ActionDuration | bigint | Y |  |  |
| StartTime | datetime |  |  |  |

## ConfigurationGroup

`SYS3.ConfigurationGroup` — 2,925 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ConfigurationGroupID | bigint |  | PK |  |
| Path | nvarchar(max) |  |  |  |
| ParentConfigurationGroupRef | bigint | Y | → SYS3.ConfigurationGroup.ConfigurationGroupID |  |

ارجاع‌شده توسط: `SYS3.ConfigurationGroup`، `SYS3.ConfigurationValue`

## ConfigurationValue

`SYS3.ConfigurationValue` — 3,658 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ConfigurationValueID | bigint |  | PK |  |
| UserRef | bigint | Y | → SYS3.User.UserID |  |
| Scope | int |  |  |  |
| Key | nvarchar(500) |  |  |  |
| Data | xml | Y |  |  |
| ConfigurationGroupRef | bigint |  | → SYS3.ConfigurationGroup.ConfigurationGroupID |  |
| CompanyRef | bigint | Y |  |  |

## DashboardCategory

`SYS3.DashboardCategory` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DashboardCategoryID | bigint |  | PK |  |
| Title | nvarchar(512) |  |  |  |
| ParentRef | bigint | Y | → SYS3.DashboardCategory.DashboardCategoryID |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `SYS3.DashboardCategory`، `SYS3.Dashboard`، `SYS3.DashboardDatasource`، `SYS3.DashboardWidget`

## DataTransferMethod

`SYS3.DataTransferMethod` — 17 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DataTransferMethodID | bigint |  | PK |  |
| UniqueId | nvarchar(250) | Y |  |  |
| Title | nvarchar(250) |  |  |  |
| Systematic | bit |  |  |  |
| EntityCode | int |  |  |  |
| SheetName | nvarchar(250) |  |  |  |
| FirstRowHasHeader | bit |  |  |  |
| HasSample | bit |  |  |  |
| SampleExcel | varbinary(max) | Y |  |  |
| SampleExcelName | nvarchar(250) | Y |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `SYS3.DataTransferMethodItem`، `SYS3.DataTransferMethodSetting`

## DBSignature

`SYS3.DBSignature` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Signature | varbinary(max) |  |  |  |
| SignedByDevModeInstaller | bit |  |  |  |

## DynamicReport

`SYS3.DynamicReport` — 18 rows — 🔵 اطلاعات پایه فعال

گزارش‌های ساخته‌شده توسط کاربران (بیمه، مالیات، وام، لیست حقوق...) — نشان‌دهنده‌ی نیاز واقعی واحد حقوق.

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DynamicReportID | bigint |  | PK |  |
| Category | nvarchar(512) |  |  |  |
| Title | nvarchar(512) |  |  |  |
| Data | nvarchar(max) |  |  |  |
| CreatorUserRef | bigint |  | → SYS3.User.UserID |  |
| Level | int |  |  |  |
| SystemReportMode | int |  |  |  |
| UniqueName | nvarchar(100) |  |  |  |
| ViewSecurityKey | nvarchar(500) | Y |  |  |
| Guid | uniqueidentifier |  |  |  |
| VersionNumber | int |  |  |  |
| CreationDate | datetime |  |  |  |
| IsPublic | bit |  |  |  |

## EntityEvent

`SYS3.EntityEvent` — 17 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntityEventID | bigint |  | PK |  |
| EntityCode | int |  |  |  |
| EventName | nvarchar(100) |  |  |  |

ارجاع‌شده توسط: `SYS3.EntityRecordNotification`، `SYS3.EntityGeneralNotification`

## EntityGeneralNotification

`SYS3.EntityGeneralNotification` — 22 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntityGeneralNotificationID | bigint |  | PK |  |
| EntityEventRef | bigint |  | → SYS3.EntityEvent.EntityEventID |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| PreviousState | int | Y |  |  |
| CurrentState | int | Y |  |  |
| Filter | nvarchar(max) | Y |  |  |
| NotificationMethod | int |  |  |  |
| Title | nvarchar(500) | Y |  |  |

## EntityLookup

`SYS3.EntityLookup` — 2,595 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Code | int |  | PK |  |
| EntityName | nvarchar(200) |  |  |  |

ارجاع‌شده توسط: `SLS3.PartInvoicePermit`، `LGS3.InventoryVoucher`، `LGS3.InventoryVoucherItem`

## EntityRecordNotification

`SYS3.EntityRecordNotification` — 10 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntityRecordNotificationID | bigint |  | PK |  |
| EntityEventRef | bigint |  | → SYS3.EntityEvent.EntityEventID |  |
| EntityRef | bigint |  |  |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| PreviousState | int | Y |  |  |
| CurrentState | int | Y |  |  |
| Filter | nvarchar(max) | Y |  |  |
| NotificationMethod | int |  |  |  |
| Title | nvarchar(500) | Y |  |  |

## EntityReport

`SYS3.EntityReport` — 37 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| EntityReportID | bigint |  | PK |  |
| ComponentName | nvarchar(500) |  |  |  |
| EntityName | nvarchar(500) |  |  |  |
| UserRef | bigint | Y |  |  |
| ReportUrl | nvarchar(520) |  |  |  |
| IsSystemReport | bit |  |  |  |

## Filter

`SYS3.Filter` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| FilterID | bigint |  | PK |  |
| Name | nvarchar(100) |  |  |  |
| ComponentName | nvarchar(100) |  |  |  |
| EntityName | nvarchar(100) |  |  |  |
| UseCase | nvarchar(100) | Y |  |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| Value | nvarchar(max) |  |  |  |

## JalaliStartDate

`SYS3.JalaliStartDate` — 181 rows — 🔵 اطلاعات پایه فعال

تاریخ میلادی شروع سال‌های جلالی (برای تبدیل تاریخ).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StartDate | datetime |  | PK |  |

## Job

`SYS3.Job` — 2,548 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| JobID | bigint |  | PK |  |
| RootJobRef | bigint | Y | → SYS3.Job.JobID |  |
| ParentRef | bigint | Y | → SYS3.Job.JobID |  |
| Title | nvarchar(500) |  |  |  |
| StartTime | datetime |  |  |  |
| FinishTime | datetime | Y |  |  |
| Status | int |  |  | `JobStatus`: 6=موفق |
| Message | nvarchar(max) | Y |  |  |
| Exception | nvarchar(max) | Y |  |  |
| ExtraInfoPresenterURL | nvarchar(max) | Y |  |  |
| ExtraInfoData | varbinary(max) | Y |  |  |
| UserRef | bigint | Y | → SYS3.User.UserID |  |
| ActionMessage | xml | Y |  |  |

ارجاع‌شده توسط: `PRC3.TimingSchedule`، `LGS3.InventoryScheduledJob`، `LGS3.ProcessesScheduling`، `LGS3.SchedulePricing`، `PRC3.PartNoticeSchedulingOperation`، `SYS3.Job`، `SYS3.JobStep`

## LogicalResource

`SYS3.LogicalResource` — 3 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LogicalResourceID | bigint |  | PK |  |
| Key | nvarchar(250) |  |  |  |
| Name | nvarchar(250) |  |  |  |
| ParentRef | bigint | Y | → SYS3.LogicalResource.LogicalResourceID |  |
| OperationType | int | Y |  |  |
| Type | int |  |  |  |
| CanHaveRecordLevel | int |  |  |  |
| EntityTypeName | nvarchar(250) | Y |  |  |
| ComponentName | nvarchar(max) | Y |  |  |

ارجاع‌شده توسط: `SYS3.LogicalResource`

## Lookup

`SYS3.Lookup` — 7,383 rows — 🔵 اطلاعات پایه فعال

قاموس enum های سیستم (Type, Code, Value فارسی).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LookupID | bigint |  | PK |  |
| Type | nvarchar(50) |  |  |  |
| Code | int |  |  |  |
| Value | nvarchar(100) |  |  |  |
| DisplayOrder | int | Y |  |  |
| Extra | nvarchar(100) | Y |  |  |
| System | nvarchar(10) |  |  |  |
| CanEdit | bit |  |  |  |
| CanDelete | bit |  |  |  |

ارجاع‌شده توسط: `SYS3.LookupTranslation`

## LookupInfo

`SYS3.LookupInfo` — 1,679 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LookupInfoID | bigint |  | PK |  |
| Type | nvarchar(50) |  |  |  |
| Title | nvarchar(100) |  |  |  |
| IsDynamic | bit |  |  |  |
| Guid | uniqueidentifier | Y |  |  |
| PackageVersion | int | Y |  |  |
| CreationDate | datetime | Y |  |  |

## LookupTranslation

`SYS3.LookupTranslation` — 6,606 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LookupRef | bigint |  | → SYS3.Lookup.LookupID |  |
| Culture | nvarchar(5) |  |  |  |
| Value | nvarchar(100) |  |  |  |
| LookupTranslationID | bigint |  | PK |  |

## NumberingMethod

`SYS3.NumberingMethod` — 309 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| NumberingMethodID | bigint |  | PK |  |
| Title | nvarchar(128) |  |  |  |
| GroupID | bigint | Y |  |  |
| EffectiveDate | datetime |  |  |  |
| NumberType | int |  |  |  |
| NumberDigitsType | int | Y |  |  |
| NumberOfDigits | tinyint | Y |  |  |
| NumberTemplate | nvarchar(500) |  |  |  |
| AssignApproch | int |  |  |  |
| NumberingMethodState | int |  |  |  |
| FixedLength | int | Y |  |  |
| CheckUniqueness | bit |  |  |  |
| MissedNumberBehavior | int |  |  |  |

ارجاع‌شده توسط: `SYS3.NumberingReseterAttribute`، `SYS3.NumberingMethodEntityAttribute`، `SYS3.NumberingMethodRange`

## NumberingMethodEntityAttribute

`SYS3.NumberingMethodEntityAttribute` — 309 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| NumberingMethodEntityAttributeID | bigint |  | PK |  |
| NumberingMethodRef | bigint |  | → SYS3.NumberingMethod.NumberingMethodID |  |
| AttributeComponentName | nvarchar(256) |  |  |  |
| AttributeEntityName | nvarchar(50) |  |  |  |
| IsForSecondNumber | bit |  |  |  |

## NumberingMethodRange

`SYS3.NumberingMethodRange` — 383 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| NumberingMethodRangeID | bigint |  | PK |  |
| NumberingMethodRef | bigint |  | → SYS3.NumberingMethod.NumberingMethodID |  |
| Priority | int |  |  |  |
| AttributeName | nvarchar(50) | Y |  |  |
| AttributeValues | nvarchar(250) | Y |  |  |
| StartSerial | bigint |  |  |  |
| FinishSerial | bigint | Y |  |  |
| SerialStep | tinyint |  |  |  |

ارجاع‌شده توسط: `SYS3.NumberingRangeReservation`

## NumberingRangeReservation

`SYS3.NumberingRangeReservation` — 1,571 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| NumberingRangeReservationID | bigint |  | PK |  |
| NumberingMethodRangeRef | bigint |  | → SYS3.NumberingMethodRange.NumberingMethodRangeID |  |
| DomainKey | nvarchar(500) |  |  |  |
| ReservedSerial | bigint |  |  |  |

## NumberingReseterAttribute

`SYS3.NumberingReseterAttribute` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| NumberingReseterAttributeID | bigint |  | PK |  |
| NumberingMethodRef | bigint |  | → SYS3.NumberingMethod.NumberingMethodID |  |
| Priority | int |  |  | `PriorityType`: 1=معمولی |
| AttributeName | nvarchar(50) |  |  |  |
| AttributeDisplayName | nvarchar(200) | Y |  |  |

## OutgoingMessage

`SYS3.OutgoingMessage` — 72 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| OutgoingMessageID | bigint |  | PK |  |
| ReferenceID | nvarchar(100) | Y |  |  |
| Status | int |  |  |  |
| StatusDetail | int |  |  |  |
| ChannelUniqueName | nvarchar(100) |  |  |  |
| MediaType | int |  |  |  |
| SubType | int |  |  |  |
| Message | xml |  |  |  |
| Recipients | xml |  |  |  |
| InsertDate | datetime |  |  |  |
| Results | xml |  |  |  |
| RetryCount | int |  |  |  |

## PasswordHistory

`SYS3.PasswordHistory` — 120 rows — 🟡 لاگ/کش/سیستمی

> ⚠️ **حساس**: تاریخچه رمز عبور

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PasswordHistoryID | bigint |  | PK |  |
| ChangeDate | datetime |  |  |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| Password | nvarchar(50) |  |  |  |

## Portal

`SYS3.Portal` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PortalID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| PortalKey | nvarchar(50) | Y |  |  |

ارجاع‌شده توسط: `SYS3.PortalComponent`

## ReportPathMapping

`SYS3.ReportPathMapping` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReportPathMappingID | bigint |  | PK |  |
| ReportPath | nvarchar(256) |  |  |  |
| MappedPath | nvarchar(256) |  |  |  |
| State | int |  |  | `State`: 0=غیر فعال |

## Schedule

`SYS3.Schedule` — 16 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ScheduleID | bigint |  | PK |  |
| UniqueName | nvarchar(255) |  |  |  |
| UniqueId | uniqueidentifier |  |  |  |
| VersionNumber | int |  |  |  |
| Title | nvarchar(255) | Y |  |  |
| ScheduleType | int |  |  |  |
| LastTick | datetime | Y |  |  |
| TickCount | int |  |  |  |
| Enabled | bit |  |  |  |
| StartDate | datetime |  |  |  |
| EndDate | datetime | Y |  |  |
| StartTime | int |  |  |  |
| EndTime | int | Y |  |  |
| Data | xml | Y |  |  |

ارجاع‌شده توسط: `LGS3.InventoryScheduledTask`

## SecurityEvent

`SYS3.SecurityEvent` — 4,716 rows — 🟡 لاگ/کش/سیستمی

> ⚠️ **حساس**: رویداد امنیتی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ID | bigint |  | PK |  |
| UniqueID | uniqueidentifier |  |  |  |
| DateTime | datetime |  |  |  |
| UserID | bigint | Y |  |  |
| ProcessID | uniqueidentifier | Y |  |  |
| UserName | nvarchar(200) | Y |  |  |
| WorkStation | nvarchar(50) | Y |  |  |
| Subject | int |  |  | `SecurityEventSubjectType`: 1=ورود به سیستم، 2=خروج از سیستم، 7=اخراج کاربر وارد شده از دستگاه دیگر، 14=تغییر تنظیمات، 25=مشاهده ی گزارش، 26=چاپ گزارش، 27=خروجی اکسل |
| Type | int |  |  | `SecurityEventType`: 1=اطلاع، 2=هشدار، 8=مهم، 256=موفق، 520=ناموفق | مهم |
| DetailSummary | nvarchar(200) | Y |  |  |
| Detail | nvarchar(max) | Y |  |  |
| Agent | nvarchar(1000) | Y |  |  |
| HostName | nvarchar(200) | Y |  |  |

## SecurityPolicy

`SYS3.SecurityPolicy` — 35,879 rows — 🟡 لاگ/کش/سیستمی

> ⚠️ **حساس**: سیاست امنیتی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PolicyID | bigint |  | PK |  |
| LogicalResourceKey | nvarchar(256) |  |  |  |
| AccessType | int |  |  |  |
| UserRef | bigint | Y | → SYS3.User.UserID |  |
| EntityGroupRef | bigint | Y | → GNR3.EntityGroup.EntityGroupID |  |
| PositionRef | bigint | Y |  |  |
| Type | int |  |  |  |
| IsOverrided | int |  |  |  |
| RowLevelConditions | xml | Y |  |  |
| CompanyRef | bigint | Y |  |  |

ارجاع‌شده توسط: `SYS3.CustomCondition`

## SetupValues

`SYS3.SetupValues` — 1 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| Key | varchar(50) |  | PK |  |
| Value | varchar(50) | Y |  |  |

## ShellNotification

`SYS3.ShellNotification` — 1,527 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ShellNotificationID | bigint |  | PK |  |
| Title | nvarchar(250) | Y |  |  |
| Body | nvarchar(max) |  |  |  |
| Type | int |  |  |  |
| Icon | nvarchar(max) | Y |  |  |
| DateTime | datetime |  |  |  |
| AutoDismiss | bit |  |  |  |
| ActionType | int | Y |  |  |
| Action | xml | Y |  |  |

ارجاع‌شده توسط: `SYS3.UserShellNotification`

## SQLScriptExecutionLog

`SYS3.SQLScriptExecutionLog` — 5,612 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SQLScriptExecutionLogID | bigint |  | PK |  |
| ExecutionEvent | varchar(20) |  |  |  |
| ModuleName | nvarchar(100) | Y |  |  |
| ComponentName | nvarchar(100) | Y |  |  |
| ScriptFileName | nvarchar(100) | Y |  |  |
| ProductVersion | varchar(25) | Y |  |  |
| Build | varchar(100) | Y |  |  |
| StartTime | datetime |  |  |  |
| EndTime | datetime | Y |  |  |
| Error | int |  |  |  |

## StateHistory

`SYS3.StateHistory` — 282,020 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| StateHistoryID | bigint |  | PK |  |
| EntityCode | int |  |  |  |
| RecordID | bigint |  |  |  |
| SourceState | int |  |  |  |
| TargetState | int |  |  |  |
| ChangeDate | datetime |  |  |  |
| ChangingUserID | bigint | Y |  |  |
| CustomOperationCode | int | Y |  |  |
| CustomOperationTitle | nvarchar(200) | Y |  |  |
| Notes | nvarchar(500) | Y |  |  |
| TaskOwnerUserID | bigint | Y |  |  |

## StaticID

`SYS3.StaticID` — 37,033 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TableName | varchar(100) |  |  |  |
| RecordID | bigint |  |  |  |

## TableIdGenBacking

`SYS3.TableIdGenBacking` — 369 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| TableName | varchar(100) |  | PK |  |
| LastId | bigint |  |  |  |

## User

`SYS3.User` — 45 rows — 🔵 اطلاعات پایه فعال

کاربران سیستم؛ ستون Password — هرگز در دسترس LLM نباشد.

> ⚠️ **حساس**: ستون Password و اطلاعات ورود کاربران

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| UserID | bigint |  | PK |  |
| Name | nvarchar(50) |  |  |  |
| Status | int |  |  | `Status`: 1=فعال، 2=غیر فعال |
| PartyRef | bigint | Y | → GNR3.Party.PartyID |  |
| Type | int |  |  |  |
| IsAdministrator | bit | Y |  |  |
| IsLocked | bit |  |  |  |
| LockExpiration | datetime | Y |  |  |
| Password | nvarchar(50) | Y |  |  |
| LastPasswordUpdate | datetime |  |  |  |
| PasswordExpiration | int |  |  |  |
| DomainUserName | nvarchar(50) | Y |  |  |
| ValidWorkstations | nvarchar(500) | Y |  |  |
| Context | nvarchar(50) | Y |  |  |
| RemoteServiceEnabled | bit |  |  |  |
| ContextData | nvarchar(500) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `HCM3.AttendanceCalculationCalendarEmployee`، `LGS3.TransportationManagementPortalDistribution`، `RMS3.GeneratedCouponInstanceRetailShop`، `HCM3.RfidLocalSecurityPolicy`، `RMS3.RetailLoyaltyProgram`، `PRC3.PurchaseMiscCost`، `FAM3.Scrap`، `LGS3.MaterialClassProposal`، `FAM3.AssetTagTemplate`، `FAM3.AssetDepreciation`، `FAM3.DefinitiveTransfer`، `RMS3.ThirdPartyCouponSettlement`، `HCM3.AppraisalForm`، `ECM.NumberingMethod`، `ECM.LetterRelation`، `PAC3.ReferenceOperationSet`، `QCM3.PartSupplierProfileCharacteristicHistory`، `XLS3.CollectionNotice`، `PAC3.DisassemblingOrder`، `RMS3.OfflineVirtualCardTransaction`، `XLS3.SalesStatement`، `FIN3.AgingReceivableSetting`، `SLS3.Invoice`، `SCM3.OrderStatusRequest`، `RMS3.RetailHandheldDevice` …

## UserLogonAudit

`SYS3.UserLogonAudit` — 33,315 rows — 🟡 لاگ/کش/سیستمی

> ⚠️ **حساس**: لاگ ورود

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| UserLogonAuditID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| LogonTime | datetime |  |  |  |
| LogonSource | nvarchar(100) | Y |  |  |
| LogonContext | nvarchar(20) |  |  |  |
| SessionID | nvarchar(50) |  |  |  |
| LogoutReason | nvarchar(200) | Y |  |  |
| LogoutTime | datetime | Y |  |  |
| LastActivityTime | datetime |  |  |  |

## UserShellNotification

`SYS3.UserShellNotification` — 1,527 rows — 🟡 لاگ/کش/سیستمی

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| UserShellNotificationID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |
| ShellNotificationRef | bigint |  | → SYS3.ShellNotification.ShellNotificationID |  |
| IsRead | bit |  |  |  |
| IsDismissed | bit |  |  |  |
| TranslatedTitle | nvarchar(250) | Y |  |  |
| TranslatedBody | nvarchar(max) | Y |  |  |
