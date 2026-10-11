# Schema `RPA3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [Bank](#bank) | 16 | 11 | 🔵 اطلاعات پایه فعال |  |
| [BankAccount](#bankaccount) | 57 | 19 | 🔵 اطلاعات پایه فعال | حساب‌های بانکی شرکت (۵۷). اشخاص: PartyBankAccount (حساس). |
| [BankAccountHistory](#bankaccounthistory) | 31 | 6 | ⚪ تنظیمات/ثابت |  |
| [BankAccountType](#bankaccounttype) | 18 | 5 | 🔵 اطلاعات پایه فعال |  |
| [BankBranch](#bankbranch) | 34 | 12 | 🔵 اطلاعات پایه فعال |  |
| [OnlinePaymentSimulatorUser](#onlinepaymentsimulatoruser) | 7 | 5 | ⚪ تنظیمات/ثابت |  |
| [PartyBankAccount](#partybankaccount) | 2,926 | 11 | 🔵 اطلاعات پایه فعال |  |
| [ReconciliationReason](#reconciliationreason) | 12 | 16 | ⚪ تنظیمات/ثابت |  |

## Bank

`RPA3.Bank` — 16 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BankID | bigint |  | PK |  |
| Name | nvarchar(255) |  |  |  |
| Name_En | nvarchar(255) | Y |  |  |
| Phone | nvarchar(100) | Y |  |  |
| WebSite | nvarchar(255) | Y |  |  |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| BankType | int |  |  | `BankType`: 1=بانک، 3=صندوق قرض الحسنه |
| SwiftCode | nvarchar(8) | Y |  |  |
| Code | nvarchar(16) |  |  |  |

ارجاع‌شده توسط: `RPA3.BankBranch`، `RMS3.EReceiptTransaction`، `RPA3.ReceivableCollateral`، `RMS3.Cheque`، `DSD3.TourReceiptMoneyInfo`، `RMS3.EReceipt`، `RPA3.ReceivableNote`، `RMS3.EReceiptSurplusage`، `RMS3.BankReceipt`، `RPA3.OnlineMoneyTransfer`، `HCM3.EmployeePaymentLocation`، `HCM3.FileStructureBank`، `HCM3.TreasuryReportSetting`، `RPA3.ChequePattern`، `HCM3.RetirementReportSetting`، `RMS3.WalletPosTransaction`، `RPA3.PayableNote`، `RPA3.BankTransferDisketteStructure`، `RPA3.ReceiptDeposit`، `XLS3.CollectionNotice`، `RPA3.OnlineMoneyTransferItem`، `RPA3.CommittedBank`، `RPA3.ReceiptReceivableNote`، `RPA3.PartyBankAccount`، `RPA3.OnlineGatewayBank` …

## BankAccount

`RPA3.BankAccount` — 57 rows — 🔵 اطلاعات پایه فعال

حساب‌های بانکی شرکت (۵۷). اشخاص: PartyBankAccount (حساس).

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BankAccountID | bigint |  | PK |  |
| BranchRef | bigint |  | → GNR3.Branch.BranchID |  |
| BankBranchRef | bigint |  | → RPA3.BankBranch.BankBranchID |  |
| Number | nvarchar(50) |  |  |  |
| BankAccountTypeRef | bigint |  | → RPA3.BankAccountType.BankAccountTypeID |  |
| CurrencyRef | bigint |  | → GNR3.Currency.CurrencyID |  |
| SavedAmount | decimal(28,6) | Y |  |  |
| ValidationAmount | decimal(28,6) | Y |  |  |
| BlockedAmount | decimal(28,6) | Y |  |  |
| State | int |  |  | `State`: 1= فعال |
| Description | nvarchar(512) | Y |  |  |
| Description_En | nvarchar(512) | Y |  |  |
| ParentRef | bigint | Y | → RPA3.BankAccount.BankAccountID |  |
| InternationalNumber | nvarchar(26) | Y |  |  |
| AutomaticTransfer | bit |  |  |  |
| LedgerRef | bigint |  | → GNR3.Ledger.LedgerID |  |
| ImportanceAmount | decimal(28,6) | Y |  |  |
| TransferMethod | int | Y |  | `TransferMethod`:  |

ارجاع‌شده توسط: `RPA3.Reconciliation`، `RPA3.ExternalCreditProviderPreReceipt`، `RPA3.TransferRestorePayableCheque`، `RPA3.ExternalCreditProviderTransaction`، `XLS3.Proforma`، `RPA3.PayableCollateral`، `RPA3.VoucherReconciliationAllItem`، `RMS3.EPayment`، `RPA3.BankAccountReconciliationSl`، `RPA3.PaymentOrder`، `RMS3.EReceiptTransaction`، `RPA3.ReconciliationTreasuryAllItem`، `RPA3.TransferPayableCheque`، `RPA3.PaymentOrderPayableNote`، `RMS3.EReceipt`، `RPA3.BankTransfer`، `RPA3.PettyCashCardCollection`، `BDG3.PaymentInformationItem`، `RMS3.EReceiptSurplusage`، `XLS3.Invoice`، `RPA3.BankAccountTransaction`، `RPA3.PayableCollateralBlockedBankAccount`، `RPA3.ReconciliationDeployment`، `RPA3.CollectionRejection`، `RPA3.ReconciliationBankBillAllItem` …

## BankAccountHistory

`RPA3.BankAccountHistory` — 31 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BankAccountHistoryID | bigint |  | PK |  |
| BankAccountRef | bigint |  | → RPA3.BankAccount.BankAccountID |  |
| State | int |  |  | `State`: 1= فعال |
| Date | datetime |  |  |  |
| Amount | decimal(28,6) |  |  |  |

## BankAccountType

`RPA3.BankAccountType` — 18 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BankAccountTypeID | bigint |  | PK |  |
| Name | nvarchar(255) |  |  |  |
| HasChequeBook | bit |  |  |  |
| CanWithdrawal | bit |  |  |  |

ارجاع‌شده توسط: `HCM3.EmployeePaymentLocation`، `HCM3.FileStructureBank`، `RPA3.BankAccount`

## BankBranch

`RPA3.BankBranch` — 34 rows — 🔵 اطلاعات پایه فعال

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| BankBranchID | bigint |  | PK |  |
| BankRef | bigint |  | → RPA3.Bank.BankID |  |
| CityRef | bigint | Y | → GNR3.RegionalDivision.RegionalDivisionID |  |
| Name | nvarchar(255) |  |  |  |
| Name_En | nvarchar(255) | Y |  |  |
| Code | nvarchar(10) |  |  |  |
| Phone | nvarchar(50) | Y |  |  |
| Address | nvarchar(255) | Y |  |  |
| WebSite | nvarchar(255) | Y |  |  |
| SwiftCode | nvarchar(11) | Y |  |  |
| CityName | nvarchar(256) | Y |  |  |

ارجاع‌شده توسط: `RMS3.BankReceipt`، `RPA3.OnlineMoneyTransfer`، `HCM3.EmployeePaymentLocation`، `HCM3.FileStructureBank`، `HCM3.TreasuryReportSetting`، `HCM3.RetirementReportSetting`، `XLS3.CollectionNotice`، `RPA3.ReceiptReceivableNote`، `RPA3.BankAccount`، `RPA3.PartyBankAccount`

## OnlinePaymentSimulatorUser

`RPA3.OnlinePaymentSimulatorUser` — 7 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| OnlinePaymentSimulatorUserID | bigint |  | PK |  |
| Name | nvarchar(64) |  |  |  |
| Role | int |  |  | `OnlinePaymentSimulatorUserRole`: 0=تأیید کننده، 1=اجرا کننده، 2=ایجاد کننده، 3=نامعلوم |
| GenderType | int |  |  | `OnlinePaymentSimulatorUserGenderType`: 0=آقا |

ارجاع‌شده توسط: `RPA3.OnlinePaymentSimulatorBankAccountUser`، `RPA3.OnlinePaymentSimulatorCartableUser`

## PartyBankAccount

`RPA3.PartyBankAccount` — 2,926 rows — 🔵 اطلاعات پایه فعال

> ⚠️ **حساس**: حساب بانکی اشخاص

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| PartyBankAccountID | bigint |  | PK |  |
| State | int |  |  | `State`: 1= فعال |
| AccountNumber | nvarchar(64) |  |  |  |
| PartyRef | bigint |  | → GNR3.Party.PartyID |  |
| BankRef | bigint |  | → RPA3.Bank.BankID |  |
| BankBranchRef | bigint |  | → RPA3.BankBranch.BankBranchID |  |
| DocumentType | int |  |  | `PartyBankAccountDocumentType`: 1=دریافت، 2=پرداخت، 100=همه |
| IsInBlackList | bit |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| InternationalNumber | nvarchar(26) | Y |  |  |

ارجاع‌شده توسط: `RPA3.ReceiptReceivableNote`، `XLS3.Proforma`، `RPA3.PaymentOrderList`، `DSD3.TourReceiptMoneyInfo`، `XLS3.Invoice`، `HCM3.EmployeePaymentLocation`، `BDG3.AdjustmentFactorReceiptInformation`، `XLS3.CollectionNotice`، `BDG3.ReceiptInformationItem`

## ReconciliationReason

`RPA3.ReconciliationReason` — 12 rows — ⚪ تنظیمات/ثابت

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| ReconciliationReasonId | bigint |  | PK |  |
| Code | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Description | nvarchar(512) |  |  |  |
| ShowInDebitRPATransaction | bit |  |  |  |
| ShowInCreditRPATransaction | bit |  |  |  |
| ShowInDebitBankBill | bit |  |  |  |
| ShowInCreditBankBill | bit |  |  |  |
| ShowInDebitVoucherItem | bit |  |  |  |
| ShowInCreditVoucherItem | bit |  |  |  |
| State | int |  |  | `State`: 1= فعال |
| Creator | bigint |  | → SYS3.User.UserID |  |
| CreationDate | datetime |  |  |  |
| LastModifier | bigint |  | → SYS3.User.UserID |  |
| LastModificationDate | datetime |  |  |  |

ارجاع‌شده توسط: `RPA3.ReconciliationOpenItemReason`، `RPA3.VoucherReconciliationOpenItemReason`
