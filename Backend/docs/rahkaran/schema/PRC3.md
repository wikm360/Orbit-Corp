# Schema `PRC3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [AccountGroupDLSourceTypeRelation](#accountgroupdlsourcetyperelation) | 356 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [AccountGroupParameterRelation](#accountgroupparameterrelation) | 113 | 4 | 🔴 استفاده‌نشده (seed) |  |
| [MiscCost](#misccost) | 9 | 8 | 🔴 استفاده‌نشده (seed) |  |
| [PurchasingAdminUser](#purchasingadminuser) | 1 | 2 | 🔴 استفاده‌نشده (seed) |  |
| [SelfServiceUser](#selfserviceuser) | 1 | 10 | 🔴 استفاده‌نشده (seed) |  |

## AccountGroupDLSourceTypeRelation

`PRC3.AccountGroupDLSourceTypeRelation` — 356 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountGroupDLSourceTypeRelationID | bigint |  | PK |  |
| AccountGroup | int |  |  |  |
| DLSourceType | int |  |  | `DLSourceType`: 1=تأمین کننده، 2=طرف مقابل، 3=مرکز هزینه/پروژه، 7=سفارشات، 8=شرکت حمل، 9=سازمان مجوز دهنده، 10=شرکت بیمه، 11=وزارت صنعت و معدن، 12=گمرک ترخیص شده، 13=قراردادخرید، 14=سطح 5 قراردادخرید، 15=سطح 6 قراردادخرید |
| DLLevel | int | Y |  | `DLLevel`: 4=سطح چهار، 5=سطح پنج، 6=سطح شش |

## AccountGroupParameterRelation

`PRC3.AccountGroupParameterRelation` — 113 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| AccountGroupParameterRelationID | bigint |  | PK |  |
| AccountGroup | int |  |  |  |
| Parameter | int |  |  |  |

## MiscCost

`PRC3.MiscCost` — 9 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| MiscCostID | bigint |  | PK |  |
| Title | nvarchar(300) |  |  |  |
| DefaultEffectType | int |  |  | `DefaultEffectType`: 1=افزاینده |
| State | int |  |  | `State`: 1= فعال |
| EntityCode | int | Y |  |  |
| CostSharingMethod | int | Y |  | `CostSharingMethod`: 2=مبلغی |
| CostSharingMethodIsEditable | bit |  |  |  |

ارجاع‌شده توسط: `PRC3.MiscCostTargetEntity`، `PRC3.AccountGroupLedgerParameterValue`، `PRC3.DraftVoucherItemDetail`، `PRC3.PurchaseMiscCostItem`

## PurchasingAdminUser

`PRC3.PurchasingAdminUser` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PurchasingAdminUserID | bigint |  | PK |  |
| UserRef | bigint |  | → SYS3.User.UserID |  |

## SelfServiceUser

`PRC3.SelfServiceUser` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| SelfServiceUserID | bigint |  | PK |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| FirstName | nvarchar(250) | Y |  |  |
| LastName | nvarchar(250) | Y |  |  |
| UserName | nvarchar(50) |  |  |  |
| Password | nvarchar(50) |  |  |  |
| Email | nvarchar(200) |  |  |  |
| IsAdmin | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |

ارجاع‌شده توسط: `PRC3.SelfServiceSecurityPolicy`، `PRC3.SelfServiceUserGroupMember`، `PRC3.SelfServiceUserPermission`، `PRC3.SelfServiceUserProfile`
