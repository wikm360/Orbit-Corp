# Schema `ECM` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [DelegationGrant](#delegationgrant) | 10 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [DocumentTemplate](#documenttemplate) | 1 | 11 | 🔴 استفاده‌نشده (seed) |  |
| [DocumentTemplateDetail](#documenttemplatedetail) | 4 | 6 | 🔴 استفاده‌نشده (seed) |  |
| [DocumentTemplateField](#documenttemplatefield) | 12 | 18 | 🔴 استفاده‌نشده (seed) |  |
| [LetterRelationType](#letterrelationtype) | 5 | 3 | 🔴 استفاده‌نشده (seed) |  |
| [LetterSecuretyLevel](#lettersecuretylevel) | 5 | 3 | 🔴 استفاده‌نشده (seed) |  |
| [LetterUrgency](#letterurgency) | 4 | 3 | 🔴 استفاده‌نشده (seed) |  |
| [PredefinedReferringReceiverPermission](#predefinedreferringreceiverpermission) | 10 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringCondition](#referringcondition) | 13 | 3 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringReason](#referringreason) | 6 | 11 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringReasonCondition](#referringreasoncondition) | 62 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringSecurityLevel](#referringsecuritylevel) | 5 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringSetting](#referringsetting) | 4 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [ReferringUrgency](#referringurgency) | 4 | 4 | 🔴 استفاده‌نشده (seed) |  |

## DelegationGrant

`ECM.DelegationGrant` — 10 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DelegationGrantID | bigint |  | PK |  |
| Category | int |  |  |  |
| Title | nvarchar(500) |  |  |  |

ارجاع‌شده توسط: `ECM.AuthorityDelegationGrant`

## DocumentTemplate

`ECM.DocumentTemplate` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DocumentTemplateID | bigint |  | PK |  |
| Name | nvarchar(256) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| EntityCode | int | Y |  |  |
| State | int |  |  | `State`: 1= فعال |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `ECM.DocumentTemplateDetail`، `ECM.DocumentTemplateField`، `ECM.Document`

## DocumentTemplateDetail

`ECM.DocumentTemplateDetail` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DocumentTemplateDetailID | bigint |  | PK |  |
| Name | nvarchar(256) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| EntityCode | int | Y |  |  |
| DocumentTemplateRef | bigint |  | → ECM.DocumentTemplate.DocumentTemplateID |  |

ارجاع‌شده توسط: `ECM.DocumentDetail`، `ECM.DocumentTemplateField`

## DocumentTemplateField

`ECM.DocumentTemplateField` — 12 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| DocumentTemplateFieldID | bigint |  | PK |  |
| Name | nvarchar(256) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| Path | nvarchar(256) | Y |  |  |
| AssignToHeader | bit | Y |  |  |
| ContentFieldName | nvarchar(256) | Y |  |  |
| Description | nvarchar(max) | Y |  |  |
| TypeCode | int |  |  | `DocumentTemplateFieldType`: 1=رشته، 3=تاریخ، 4=ضمیمه، 5=کد و شرحی، 6=ارجاع به موجودیت |
| Priority | int |  |  |  |
| Required | bit | Y |  |  |
| ReadOnly | bit | Y |  |  |
| MinValue | int | Y |  |  |
| MaxValue | int | Y |  |  |
| MaxLength | int | Y |  |  |
| DocumentTemplateRef | bigint | Y | → ECM.DocumentTemplate.DocumentTemplateID |  |
| DocumentTemplateDetailRef | bigint | Y | → ECM.DocumentTemplateDetail.DocumentTemplateDetailID |  |
| Searchable | bit |  |  |  |

ارجاع‌شده توسط: `ECM.DocumentField`

## LetterRelationType

`ECM.LetterRelationType` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LetterRelationTypeID | bigint |  | PK |  |
| Title | nvarchar(70) |  |  |  |

## LetterSecuretyLevel

`ECM.LetterSecuretyLevel` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LetterSecuretyLevelID | bigint |  | PK |  |
| Title | nvarchar(70) |  |  |  |

## LetterUrgency

`ECM.LetterUrgency` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| LetterUrgencyID | bigint |  | PK |  |
| Title | nvarchar(70) |  |  |  |

## PredefinedReferringReceiverPermission

`ECM.PredefinedReferringReceiverPermission` — 10 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PredefinedReferringReceiverPermissionID | bigint |  | PK |  |
| Title | nvarchar(100) |  |  |  |
| State | int |  |  |  |
| Type | int |  |  |  |
| CreationDate | datetime |  |  |  |
| Creator | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| Description | nvarchar(512) |  |  |  |

## ReferringCondition

`ECM.ReferringCondition` — 13 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringConditionID | bigint |  | PK |  |
| Title | nvarchar(200) | Y |  |  |

ارجاع‌شده توسط: `ECM.ReferringReasonCondition`

## ReferringReason

`ECM.ReferringReason` — 6 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringReasonID | bigint |  | PK |  |
| Title | nvarchar(500) |  |  |  |
| Type | int |  |  | `ReferringReasonType`: 1=ثابت |
| State | int |  |  | `State`: 1= فعال |
| IsDefault | bit |  |  |  |
| Description | nvarchar(max) | Y |  |  |
| Creator | bigint |  |  |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  |  |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `ECM.ReferringReasonCondition`، `ECM.ReferringTransceiver`

## ReferringReasonCondition

`ECM.ReferringReasonCondition` — 62 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringReasonConditionID | bigint |  | PK |  |
| ReferringReasonRef | bigint | Y | → ECM.ReferringReason.ReferringReasonID |  |
| ReferringConditionRef | bigint | Y | → ECM.ReferringCondition.ReferringConditionID |  |

## ReferringSecurityLevel

`ECM.ReferringSecurityLevel` — 5 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringSecurityLevelID | bigint |  | PK |  |
| Title | nvarchar(70) |  |  |  |
| LetterSecurityLevelRef | bigint |  |  |  |

ارجاع‌شده توسط: `ECM.Referring`

## ReferringSetting

`ECM.ReferringSetting` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringSettingID | bigint |  | PK |  |
| Key | nvarchar(128) |  |  |  |
| Value | nvarchar(512) |  |  |  |

## ReferringUrgency

`ECM.ReferringUrgency` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReferringUrgencyID | bigint |  | PK |  |
| Title | nvarchar(70) |  |  |  |
| LetterUrgencyRef | bigint |  |  |  |

ارجاع‌شده توسط: `ECM.Referring`
