import os, re, collections
from db import conn
OUT=os.environ.get('RAHKARAN_DOCS_OUT','docs/rahkaran')
os.makedirs(OUT+'/schema',exist_ok=True)
c=conn(); cur=c.cursor(as_dict=True)
def Q(sql,a=()):
    cur.execute(sql,a); return cur.fetchall()

tables=Q("""SELECT s.name sch,t.name tbl,t.object_id oid,p.rows n FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
 JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1) WHERE p.rows>0 AND s.name<>'dbo' ORDER BY s.name,t.name""")
cols=collections.defaultdict(list)
for r in Q("""SELECT c.object_id oid,c.name,ty.name typ,c.max_length ml,c.precision pr,c.scale sc,c.is_nullable nul,c.column_id
  FROM sys.columns c JOIN sys.types ty ON ty.user_type_id=c.user_type_id JOIN sys.tables t ON t.object_id=c.object_id ORDER BY c.column_id"""):
    cols[r['oid']].append(r)
pk=set((r['oid'],r['name']) for r in Q("""SELECT ic.object_id oid,c.name FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
  JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE i.is_primary_key=1"""))
fk={}; inbound=collections.defaultdict(list)
for r in Q("""SELECT fc.parent_object_id po,pc.name col,rs.name+'.'+rt.name ref,rc.name refcol,ps.name psch,pt.name ptbl
  FROM sys.foreign_key_columns fc JOIN sys.columns pc ON pc.object_id=fc.parent_object_id AND pc.column_id=fc.parent_column_id
  JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
  JOIN sys.tables rt ON rt.object_id=fc.referenced_object_id JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
  JOIN sys.tables pt ON pt.object_id=fc.parent_object_id JOIN sys.schemas ps ON ps.schema_id=pt.schema_id"""):
    fk[(r['po'],r['col'])]=f"{r['ref']}.{r['refcol']}"
    inbound[r['ref']].append(f"{r['psch']}.{r['ptbl']}.{r['col']}")
lk=collections.defaultdict(dict); lksys={}
for r in Q("select Type,Code,Value,System from SYS3.Lookup"):
    lk[r['Type']][r['Code']]=r['Value']; lksys[r['Type']]=r['System']
lktitle={r['Type']:r['Title'] for r in Q("select Type,Title from SYS3.LookupInfo")}
lkl={k.lower():k for k in lk}
INT={'int','smallint','tinyint','bigint'}
def tyname(r):
    t=r['typ']
    if t in('nvarchar','nchar'): return f"{t}({'max' if r['ml']==-1 else r['ml']//2})"
    if t in('varchar','char','varbinary'): return f"{t}({'max' if r['ml']==-1 else r['ml']})"
    if t=='decimal': return f"decimal({r['pr']},{r['sc']})"
    return t
used_enums={}
def enum_for(sch,tbl,col,oid):
    cand=[col,tbl+col,re.sub(r'(Code)$','',col),tbl+re.sub(r'(Code)$','',col),col+'Type',tbl+col+'Type']
    found=[lkl[x.lower()] for x in cand if x.lower() in lkl]
    if not found: return None
    try:
        cur.execute(f"SELECT DISTINCT TOP 60 [{col}] v FROM [{sch}].[{tbl}] WHERE [{col}] IS NOT NULL"); vals=[r['v'] for r in cur.fetchall()]
    except Exception: return None
    for f in found:
        if all(v in lk[f] for v in vals): return f,vals
    return None
by_schema=collections.defaultdict(list)
for t in tables: by_schema[t['sch']].append(t)
SENSITIVE={'SYS3.User':'ستون Password و اطلاعات ورود کاربران','SYS3.PasswordHistory':'تاریخچه رمز عبور','SYS3.SecurityPolicy':'سیاست امنیتی','SYS3.UserLogonAudit':'لاگ ورود','SYS3.SecurityEvent':'رویداد امنیتی','HCM3.Employee':'کد ملی/نظام وظیفه/فایل پیوست','GNR3.Party':'کد ملی، موبایل، شناسنامه','HCM3.PayCalcItem':'حقوق افراد','HCM3.PeriodicCalcItem':'حقوق افراد','HCM3.CompensationTax':'مالیات حقوق افراد','HCM3.EmployeeStatute':'احکام حقوقی افراد','HCM3.EmployeeStatuteFactor':'احکام حقوقی افراد','HCM3.LoanPayment':'وام افراد','HCM3.EmployeePaymentLocation':'شماره حساب/شبا','RPA3.PartyBankAccount':'حساب بانکی اشخاص','HCM3.EmployeeRelative':'اطلاعات خانواده','HCM3.EmployeeMarriage':'اطلاعات خانواده'}

UNUSED_SCHEMAS={'SLS3','LGS3','RMS3','QCM3','PRC3','SCM3','CMMS3','CAC3','BDG3','WFE3','GNR','ECM'}
INFRA_SCHEMAS={'RLS3','CNV3'}
SYS_REF={'SYS3.User','SYS3.Lookup','SYS3.LookupTranslation','SYS3.LookupInfo','SYS3.JalaliStartDate','SYS3.EntityLookup','SYS3.DynamicReport','SYS3.Schedule'}
CORE={'FIN3.Voucher','FIN3.VoucherItem','FAM3.AssetTransaction','FAM3.CostPartTransaction','FAM3.Depreciation','FAM3.AcquisitionReceipt','FAM3.AcquisitionReceiptItem','FAM3.InternalTransfer','FAM3.InternalTransferItem','FAM3.Elimination','FAM3.EliminationItem','FAM3.Sales','FAM3.SalesItem','FAM3.MaintenanceExpenditures','FAM3.MaintenanceExpendituresItem','FAM3.ExitFromOrganization','FAM3.AssetOperationSummary',
'HCM3.PayCalc','HCM3.PayCalcItem','HCM3.PeriodicCalc','HCM3.PeriodicCalcItem','HCM3.MonthlyFactorData','HCM3.MonthlyFactorDataCompensationItem','HCM3.AttendanceCalc','HCM3.AttendanceCalcMonthlyItem','HCM3.CompensationTax','HCM3.EmployeeStatute','HCM3.EmployeeStatuteFactor','HCM3.FinancialStatute','HCM3.LoanPayment','HCM3.LoanInstalment','HCM3.LoanAdjustment','HCM3.Voucher','HCM3.VoucherEmployee','HCM3.EmployeePriorPeriod','HCM3.LeaveRemainder','HCM3.BatchEmployeeStatute','HCM3.BatchEmployeeStatuteEmployee','HCM3.BatchEmployeeStatuteFactor'}
MASTER={'FIN3.GL','FIN3.SL','FIN3.DL','FIN3.DLType','FIN3.AccountGroup','FIN3.VoucherType','FIN3.DLTypeRelation','FIN3.VATParty','FIN3.DebitCreditStatement','FIN3.DebitCreditStatementItem','FIN3.GLVoucher','FIN3.GLVoucherItem',
'GNR3.Party','GNR3.Address','GNR3.PartyAddress','GNR3.CostCenter','GNR3.Project','GNR3.FiscalYear','GNR3.LedgerFiscalYear','GNR3.Company','GNR3.Branch','GNR3.Ledger','GNR3.Currency','GNR3.RegionalDivision',
'FAM3.Asset','FAM3.AssetInCalculationArea','FAM3.AssetGroup','FAM3.AssetClass','FAM3.CostPart','FAM3.SettlementPlace','FAM3.Collector','FAM3.DepreciationMethod','FAM3.AssetExtraField','FAM3.AssetExtraFieldValue',
'HCM3.Employee','HCM3.Department','HCM3.Post','HCM3.Job','HCM3.PostJob','HCM3.CompensationFactor','HCM3.CompensationFactorProperty','HCM3.CompensationCalcType','HCM3.StatuteType','HCM3.StatuteFactor','HCM3.EmploymentType','HCM3.LoanType','HCM3.LeaveType','HCM3.EmployeeRelatedDL','HCM3.EmployeeRelatedOrganization','HCM3.EmployeePaymentLocation','HCM3.EmployeeEducation','HCM3.EmployeeRelative','HCM3.EmployeeMarriage','HCM3.Organization','HCM3.OrganizationBranch','HCM3.TaxTable','HCM3.TaxTableItem','HCM3.VoucherSpecification','HCM3.VoucherSpecificationSL',
'RPA3.BankAccount','RPA3.Bank','RPA3.BankBranch','RPA3.BankAccountType','RPA3.PartyBankAccount'}
LOG={'FIN3.VoucherItemOffline','FIN3.PeriodicOppositNatureAccounts','FIN3.SLDLFlow','FIN3.VoucherLock','FIN3.VoucherReviewRecord','FIN3.DeletedVoucher','FIN3.GLVoucherReference','FIN3.VoucherReference','FIN3.VoucherHistory','HCM3.AuditLog','HCM3.EmployeeStatuteStateHistory','HCM3.EmpStatuteConvertMapping','HCM3.EmployeeLocalSyncData','SYS3.StateHistory','SYS3.BusinessRuleActionExecutionLog','SYS3.UserLogonAudit','SYS3.SecurityEvent','SYS3.SecurityPolicy','SYS3.SQLScriptExecutionLog','SYS3.Job','SYS3.ShellNotification','SYS3.UserShellNotification','SYS3.OutgoingMessage','SYS3.StaticID','SYS3.TableIdGenBacking','SYS3.PasswordHistory','GNR3.SessionLock','CNV3.Log'}
STATUS_LABEL={'core':'🟢 تراکنشی فعال','master':'🔵 اطلاعات پایه فعال','config':'⚪ تنظیمات/ثابت','log':'🟡 لاگ/کش/سیستمی','unused':'🔴 استفاده‌نشده (seed)','infra':'⚫ نصب/مهاجرت'}
def status(full,sch):
    if full in CORE: return 'core'
    if full in MASTER or full in SYS_REF: return 'master'
    if full in LOG: return 'log'
    if sch in UNUSED_SCHEMAS: return 'unused'
    if sch in INFRA_SCHEMAS: return 'infra'
    return 'config'
NOTES={
'FIN3.Voucher':'سرفصل سند حسابداری. State: 1 موقت،4 بررسی‌شده،32 قطعی. تاریخ میلادی.',
'FIN3.VoucherItem':'ردیف‌های سند (بدهکار/بستانکار). Debit/Credit nullable. تفصیلی‌ها در DLLevel4..20.',
'FIN3.VoucherItemOffline':'کپی denormalized و عقب‌مانده‌ی VoucherItem (۲۲۲ ردیف جدید را ندارد). برای گزارش استفاده نشود.',
'FIN3.GL':'حساب کل (۷۳). FIN3.SL معین (۶ رقمی؛ ۴ رقم اول = کد کل).',
'FIN3.SL':'حساب معین (۶۱۸).',
'FIN3.DL':'حساب تفصیلی (طرف‌حساب‌ها/مراکز هزینه/پروژه/حساب بانکی). Code یکتاست و از DLLevelN ارجاع می‌شود؛ ReferenceID به Party/CostCenter/Project/BankAccount.',
'FIN3.DLType':'نوع تفصیلی: 1 شخص،2 شرکت،4 مرکز هزینه،5 پروژه،10 حساب بانکی،13 تسهیلات،27 سایر.',
'FIN3.DLTypeRelation':'هر معین در هر سطح (Level) چه نوع تفصیلی می‌پذیرد.',
'FIN3.VoucherType':'نوع سند (عمومی، افتتاحیه، اختتامیه، بستن حساب‌ها، اسناد خودکار FAM/HCM).',
'FIN3.AccountGroup':'گروه حساب (11 دارایی جاری ... 91/92 انتظامی).',
'FIN3.VoucherReference':'ارتباط سند با سند/فرم مبدأ (مثلاً استهلاک، حقوق) با کد entity.',
'FIN3.SLDLFlow':'کش گردش حساب‌ها (صورت‌حساب تفصیلی) برای گزارش.',
'FIN3.PeriodicOppositNatureAccounts':'کش گزارش حساب‌های خلاف ماهیت.',
'FIN3.DebitCreditStatement':'صورت‌ریز بدهکار/بستانکار مورد استفاده برای مغایرت‌گیری/تطبیق طرف‌حساب.',
'FIN3.GLVoucher':'اسناد سطح کل (تجمیعی) با GLVoucherItem و GLVoucherReference.',
'FIN3.DeletedVoucher':'لاگ سندهای حذف‌شده.',
'FIN3.VATParty':'اشخاص مشمول ارزش افزوده.',
'FIN3.SeasonalZone':'فهرست ثابت شهر/استان/کشور (اظهارنامه فصلی).',
'FIN3.CodingStandard':'استاندارد کدینگ سنا/سناما؛ جدول‌های CodingStandard* تنظیمات ثابت‌اند.',
'GNR3.Party':'اشخاص حقیقی/حقوقی (Type 0 شخص،1 شرکت). حاوی کد ملی/موبایل — حساس.',
'GNR3.CostCenter':'مراکز هزینه (۵۱۱: کارخانه آسفالت، پروژه‌ها، ماشین‌آلات...). Type: 1 اداری،2 تولیدی،3 خدماتی،4 پیمانکار.',
'GNR3.Project':'پروژه‌ها (۸۹).',
'GNR3.FiscalYear':'سال مالی؛ عنوان سال‌های قدیمی دو رقمی است (88..98) و سال‌های بعد 4 رقمی. تاریخ‌ها در LedgerFiscalYear.',
'GNR3.LedgerFiscalYear':'بازه‌ی تاریخ و وضعیت بستن هر سال مالی.',
'GNR3.Company':'یک شرکت: «شرکت محور گستر نصر».',
'HCM3.Employee':'کارمند (۲۲۱۱ سابقه؛ Status 2 فعال). حساس.',
'HCM3.PayCalc':'محاسبه‌ی حقوق ماهانه هر کارمند؛ IssueYearMonth جلالی (YYYYMM).',
'HCM3.PayCalcItem':'مقادیر عوامل حقوقی هر محاسبه؛ CompensationFactorRef=63 خالص پرداختی، 55 قابل پرداخت، 62 جمع کسور، 61 جمع مزایا. حساس.',
'HCM3.CompensationFactor':'تعریف عوامل حقوق/مزایا/کسورات (Name لاتین، Title فارسی).',
'HCM3.PeriodicCalc':'محاسبات دوره‌ای (عیدی، بازخرید...) به‌تفکیک CompensationCalcType.',
'HCM3.EmployeeStatute':'حکم کارگزینی (پست/واحد/شغل/نوع استخدام). Status 10 = نهایی.',
'HCM3.Department':'واحد سازمانی (۵۸).',
'HCM3.LoanPayment':'وام/مساعده‌ی پرداختی به کارکنان؛ LoanInstalment اقساط.',
'HCM3.Voucher':'ارتباط محاسبه‌ی حقوق با سند حسابداری (VoucherRef → FIN3.Voucher).',
'HCM3.AttendanceCalc':'محاسبه‌ی حضور و غیاب ماهانه؛ تردد خام وجود ندارد.',
'HCM3.CompensationTax':'محاسبه‌ی مالیات حقوق.',
'HCM3.Formula':'فرمول‌های محاسبه (کد C#/متن) برای عوامل.',
'FAM3.Asset':'دارایی ثابت (۷۳۲۷) با PlaqueNumber (شماره پلاک).',
'FAM3.AssetTransaction':'تراکنش‌های دارایی؛ TransactionType: 1 تحصیل،2 استهلاک،5 فروش،8 حذف،17 انتقال،18 استقرار.',
'FAM3.CostPart':'جزء بهای دارایی و پارامترهای استهلاک؛ IsActive=1 جاری.',
'FAM3.CostPartTransaction':'جزئیات مبلغی هر تراکنش (استهلاک ماهانه و انباشته).',
'FAM3.Depreciation':'رویداد محاسبه‌ی استهلاک ماهانه.',
'FAM3.vwAssetCost':'view: بهای تمام‌شده/استهلاک انباشته/ارزش دفتری فعلی هر دارایی.',
'FAM3.vwAssetDeployment':'view مسطح و آماده: مشخصات و مبلغ فعلی هر دارایی.',
'RPA3.BankAccount':'حساب‌های بانکی شرکت (۵۷). اشخاص: PartyBankAccount (حساس).',
'SYS3.Lookup':'قاموس enum های سیستم (Type, Code, Value فارسی).',
'SYS3.User':'کاربران سیستم؛ ستون Password — هرگز در دسترس LLM نباشد.',
'SYS3.DynamicReport':'گزارش‌های ساخته‌شده توسط کاربران (بیمه، مالیات، وام، لیست حقوق...) — نشان‌دهنده‌ی نیاز واقعی واحد حقوق.',
'SYS3.JalaliStartDate':'تاریخ میلادی شروع سال‌های جلالی (برای تبدیل تاریخ).',
}

for sch,ts in by_schema.items():
    L=[f"# Schema `{sch}` — جدول‌های دارای داده\n","(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)\n"]
    L.append("| جدول | ردیف | ستون | وضعیت | توضیح |\n|---|---:|---:|---|---|")
    for t in ts:
        f=f"{sch}.{t['tbl']}"; L.append(f"| [{t['tbl']}](#{t['tbl'].lower()}) | {t['n']:,} | {len(cols[t['oid']])} | {STATUS_LABEL[status(f,sch)]} | {NOTES.get(f,'')} |")
    L.append("")
    for t in ts:
        full=f"{sch}.{t['tbl']}"
        L.append(f"## {t['tbl']}\n\n`{full}` — {t['n']:,} rows — {STATUS_LABEL[status(full,sch)]}" + (f"\n\n{NOTES[full]}" if full in NOTES else "") + (f"\n\n> ⚠️ **حساس**: {SENSITIVE[full]}" if full in SENSITIVE else ""))
        L.append("\n| ستون | نوع | null | کلید/ارجاع | enum |\n|---|---|:-:|---|---|")
        for r in cols[t['oid']]:
            k=[]
            if (t['oid'],r['name']) in pk: k.append('PK')
            if (t['oid'],r['name']) in fk: k.append('→ '+fk[(t['oid'],r['name'])])
            en=''
            if r['typ'] in INT and (t['oid'],r['name']) not in fk and (t['oid'],r['name']) not in pk:
                e=enum_for(sch,t['tbl'],r['name'],t['oid'])
                if e:
                    name,vals=e; used_enums[name]=1
                    en=f"`{name}`: "+"، ".join(f"{v}={lk[name][v]}" for v in sorted(vals)[:12])
            if r['typ'] in('timestamp',): continue
            L.append(f"| {r['name']} | {tyname(r)} | {'' if not r['nul'] else 'Y'} | {' '.join(k)} | {en} |")
        inb=inbound.get(full,[])
        if inb:
            grp=collections.OrderedDict()
            for x in inb: grp.setdefault(x.rsplit('.',1)[0],[]).append(x.rsplit('.',1)[1])
            L.append("\nارجاع‌شده توسط: "+"، ".join(f"`{k}`" for k in list(grp)[:25])+(' …' if len(grp)>25 else ''))
        L.append("")
    open(f"{OUT}/schema/{sch}.md",'w').write("\n".join(L))
# enums file
E=["# Lookup enums استفاده‌شده در جدول‌های دارای داده\n","مقادیر از جدول `SYS3.Lookup` (ستون Value فارسی؛ ترجمه انگلیسی در `SYS3.LookupTranslation`).\n"]
for name in sorted(used_enums):
    E.append(f"### {name}" + (f" — {lktitle[name]}" if name in lktitle else "") + f"  _(system: {lksys[name]})_")
    E.append("\n".join(f"- {k} = {v}" for k,v in sorted(lk[name].items()))+"\n")
open(f"{OUT}/enums.md",'w').write("\n".join(E))
print(len(tables),'tables',len(used_enums),'enums used')
