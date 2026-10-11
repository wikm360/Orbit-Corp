# نگاشت ستون→enum (کنترل‌شده با داده)

هر ردیف: ستون، نام نوع در `SYS3.Lookup.Type`، مقادیر (Code=Value). فقط مواردی که مقادیر واقعی ستون زیرمجموعه‌ی کدهای enum است. مقادیر کامل هر enum در [enums.md](enums.md) نیز هست.

### `FIN3.Voucher.State` → `VoucherState` — تأییدشده
1=موقت، 2=یادداشت، 4=بررسی شده، 8=در حال بررسی، 32=قطعی شده

### `FIN3.VoucherReviewRecord.State` → `VoucherState` — تأییدشده
1=موقت، 2=یادداشت، 4=بررسی شده، 8=در حال بررسی، 32=قطعی شده

### `FIN3.VoucherItemOffline.VoucherState` → `VoucherState`
1=موقت، 2=یادداشت، 4=بررسی شده، 8=در حال بررسی، 32=قطعی شده

### `FIN3.GL.Type` → `SLType` — تأییدشده با داده: 1 برای گروه 1–3، 2 برای 4–8، 3 برای 9xxx
1=دائم، 2=موقت، 3=انتظامی، 4=انتظامی قابل بستن

### `FIN3.SL.Type` → `SLType` — تأییدشده: همیشه برابر Type کل مربوط
1=دائم، 2=موقت، 3=انتظامی، 4=انتظامی قابل بستن

### `FIN3.SL.Nature` → `AccountRemainderNature` — تأییدشده با داده: 2 بدهکار (۱۲۶ از ۱۲۷ معین فعال مانده‌ی بدهکار)، 3 بستانکار (۴۲ از ۴۳)، 1 مهم نیست
1=مهم نیست، 2=بدهکار، 3=بستانکار

### `FIN3.GL.Nature` → `AccountRemainderNature` — تقریباً همه 2 است؛ برای تحلیل از SL.Nature استفاده کنید
1=مهم نیست، 2=بدهکار، 3=بستانکار

### `FIN3.SL.NatureControl` → `NatureControl` — همه 1 = بدون کنترل
1=بدون کنترل، 2=معین، 3=معین و تمام سطوح تفصیلی، 4=معین و تفصیل انتخابی

### `FIN3.SL.AccountClass` → `AccountClass`
1=مالی، 2=بودجه ای

### `FIN3.SL.ZeroBalance` → `ZeroBalanceState`
0=غیر فعال، 1= فعال

### `FIN3.DebitCreditStatement.State` → `DebitCreditStatementState`
1=ایجاد شده، 2=ارسال شده، 3=ابطال شده

### `FIN3.PeriodicOppositNatureAccounts.NewNature` → `AccountRemainderNature`
1=مهم نیست، 2=بدهکار، 3=بستانکار

### `GNR3.Party.Type` → `PartyType`
0=شخص، 1=شرکت

### `GNR3.Party.Gender` → `PersonGender` — 1=مذکر 2=مؤنث (تأییدشده با نام‌ها؛ enum «Gender» عکس آن است و استفاده نمی‌شود)
1=مذکر، 2=مؤنث

### `GNR3.Party.MaritalStatus` → `PersonMaritalStatus`
1=مجرد، 2=متأهل، 3=معیل

### `GNR3.Party.EducationDegree` → `PersonEducationDegree`
1=دیپلم، 2=لیسانس، 3=فوق لیسانس، 4=دکترا، 5=فوق دکترا، 6=کاردانی، 7=سیکل، 8=بیسواد، 9=ابتدایی

### `GNR3.Party.Subreligion` → `PersonSubreligion`
1=شیعه، 2=سنی

### `GNR3.CostCenter.Type` → `CostCenterType`
1=اداری، 2=تولیدی، 3=خدماتی، 4=پیمانکار خارجی

### `GNR3.CostCenter.State` → `CostCenterState`
1=فعال، 2=غیرفعال

### `GNR3.RegionalDivision.Type` → `RegionalDivisionType`
1=کشور، 2=استان، 3=شهر، 4=شهرستان، 5=منطقه

### `FAM3.AssetTransaction.AssetState` → `AssetState` — وضعیت دارایی بعد از تراکنش
-29=در انتظار پروانه خروج، -28=در انتظار صورت حساب رسیده پس از اخذ مجوز، -27=در انتظار درخواست مجوز، -26=در انتظار اصلاحیه رسید تحصیل، -25=در انتظار حادثه، -24=در انتظار انتقال قطعی، -22=در انتظار مستهلک شدن، -21=در انتظار اهداء، -18=در انتظار خروج از سازمان، -17=در انتظار تحویل، -16=در انتظار برگشت از خروج موقت، -15=در انتظار خروج موقت، -14=در انتظار برگشت از اسقاط، -13=در انتظار اسقاط، -12=در انتظار انتقال، -11=در انتظار برگشت از کنار گذاری، -10=در انتظار حذف، -9=در انتظار کنار گذاری، -2=در انتظار فروش، -1=در انتظار پلاک گذاری، 1=پلاک شده، 2=فروش رفته، 3=بلااستفاده، 7=اسقاط شده، 8=جدا سازی شده، 10=حذف شده، 18=خارج شده از سازمان، 19=اجاره داده شده، 20=امانت داده شده، 21=اهداء شده، 22=مستهلک شده، 24=انتقال قطعی، 25=حادثه دیده، 26=اصلاحیه رسید تحصیل، 27=در خواست مجوز، 28=صورت حساب رسیده پس از اخذ مجوز، 29=دارای پروانه خروج

### `FAM3.AssetTransaction.TransactionType` → `AssetTransactionType`
1=تحصیل، 2=محاسبه استهلاک، 3=تغییر نرخ و روش، 4=تجدید ارزیابی، 5=فروش، 6=کنارگذاری، 7=برگشت از کنارگذاری، 8=حذف، 9=اسقاط، 10=برگشت ازاسقاط، 11=مخارج پس از تحصیل، 12=تغییر قیمت، 13=اعلامیه خروج موقت، 14=برگشت از خروج موقت، 15=ارسال به انبار، 16=تحویل از انبار، 17=انتقال داخلی، 18=استقرار، 19=خروج از سازمان، 20=انتقال بین شعب، 21=اهداء، 22=مستهلک کردن دارایی، 23=استقرار حوزه محاسباتی، 24=انتقال قطعی، 25=حادثه دیده، 26=اصلاحیه رسید تحصیل، 27=درخواست مجوز، 28=صورت حساب رسیده پس از اخذ مجوز، 29=پروانه خروج

### `FAM3.AssetTransaction.DocumentState` → `DocumentState`
1=ثبت موقت، 2=تایید شده، 3=در حال پلاک گذاری، 4=پلاک شده، 5=سند صادر شده، 6=در حال تحویل، 7=تحویل شده

### `FAM3.AssetTransaction.PhysicalLocation` → `PhysicalLocationType`
1=داخل سازمان، 2=خارج سازمان، 3=نزد انبار

### `FAM3.CostPart.DepreciationState` → `DepreciationCalculationState`
1=مستهلک نشده، 2=مستهلک شده، 3=استهلاک ناپذیر

### `FAM3.CostPart.CostType` → `ChangeCostType` — حدسی
1=اصلاح بها، 2=کاهش دائمی ارزش

### `FAM3.AssetInCalculationArea.State` → `AssetState`
-29=در انتظار پروانه خروج، -28=در انتظار صورت حساب رسیده پس از اخذ مجوز، -27=در انتظار درخواست مجوز، -26=در انتظار اصلاحیه رسید تحصیل، -25=در انتظار حادثه، -24=در انتظار انتقال قطعی، -22=در انتظار مستهلک شدن، -21=در انتظار اهداء، -18=در انتظار خروج از سازمان، -17=در انتظار تحویل، -16=در انتظار برگشت از خروج موقت، -15=در انتظار خروج موقت، -14=در انتظار برگشت از اسقاط، -13=در انتظار اسقاط، -12=در انتظار انتقال، -11=در انتظار برگشت از کنار گذاری، -10=در انتظار حذف، -9=در انتظار کنار گذاری، -2=در انتظار فروش، -1=در انتظار پلاک گذاری، 1=پلاک شده، 2=فروش رفته، 3=بلااستفاده، 7=اسقاط شده، 8=جدا سازی شده، 10=حذف شده، 18=خارج شده از سازمان، 19=اجاره داده شده، 20=امانت داده شده، 21=اهداء شده، 22=مستهلک شده، 24=انتقال قطعی، 25=حادثه دیده، 26=اصلاحیه رسید تحصیل، 27=در خواست مجوز، 28=صورت حساب رسیده پس از اخذ مجوز، 29=دارای پروانه خروج

### `FAM3.AssetInCalculationArea.DepreciationType` → `DepreciationType`
1=خیر، 2=بله

### `HCM3.Employee.Status` → `EmployeeStatus`
1=جدید، 2=فعال، 3=غیر فعال، 4=معلق، 5=مرخصی پزشکی، 6=بازنشسته، 7=مستمری بگیر فعال، 8=مستمری بگیر غیرفعال، 9=وظیفه بگیر فعال، 10=وظیفه بگیر غیرفعال

### `HCM3.Employee.MilitaryServiceStatusCode` → `MilitaryServiceStatus`
1=انجام داده، 2=معاف، 3=غیبت، 4=در حال انجام

### `HCM3.Employee.MilitaryUnitCode` → `MilitaryUnit`
1=ارتش، 2=سپاه، 3=کمیته انقلاب اسلامی، 4=مدیریت وظیفه عمومی، 5=نیروی انتظامی، 6=وزارت دفاع

### `HCM3.EmployeeEducation.DisciplineCode` → `EducationDiscipline`
1=کشاورزی، 2= ریاضی فیزیک، 3=مهندسی منابع طبیعی مراتع و آبخیزداری، 4=ابتدائی، 5=ادبیات وعلوم انسانی، 6=اقتصادی واجتماعی، 7=الکتروتکنیک، 8=الکترونیک، 9=ایمنی و بهداشت، 10=برق، 11=بهداشت، 12=حسابداری، 13=دامپزشکی، 14=درودگری، 15=ریخته گری، 16=زبان وادبیات فارسی، 17=زمین شناسی، 18=زیست شناسی، 19=ساختمان، 20=صنایع، 21=علوم تجربی، 22=عمران، 23=فقه و حقوق اسلامی، 24=کامپیوتر، 25=مکانیک، 26=ماشینهای کشاورزی، 27=مدیریت بازرگانی، 28=مدیریت صنعتی، 29=مدیریت کسب و کار، 30=معدن، 31=معماری، 32=مواد، 33=نامعلوم، 34=نقشه کشی، 35=منابع طبیعی-محیط زیست، 36=حقوق، 37=جغرافیا و برنامه ریزی شهری، 38=مهندسی پزشکی، 39=مهندسی بهداشت محیط، 40=کارشناس حرفه ای ایمنی، سلامت و محیط زیست صنایع…

### `HCM3.Employee.MilitaryBranchCode` → `MilitaryBranch`
1=اداری، 2=خدماتی، 3=پشتیبانی

### `HCM3.Employee.ExemptionTypeCode` → `ExemptionType`
1=دائم، 2=موقت، 18=پایان خدمت، 19=معاف کفالت، 95=معافیت تحصیلی، 97=پزشکی، 98=معافیت رهبری، 134=(Unkown)، 135=موارد خاص، 136=جریمه مشمولان غایب

### `HCM3.EmployeeStatute.Status` → `EmployeeStatuteStatus` — 1 ذخیره، 5 تایید کارگزینی، 10 تایید پرداخت
1=ذخیره، 5=تایید کارگزینی، 10=تایید پرداخت

### `HCM3.EmployeeStatute.AfterIssueStatusCode` → `EmployeeStatuteAfterIssueStatus` — وضعیت کارمند پس از صدور حکم
1=فعال، 2=غیرفعال، 3=معلق، 4=مرخصی پزشکی، 5=بازنشسته

### `HCM3.EmployeeStatute.IssueTimeCode` → `EmployeeStatuteIssueTime`
1=در حین استخدام، 2=در شروع استخدام، 3=در پایان استخدام، 4=اتمام دوره خدمت، 5=شروع دوره بازنشستگی، 6=حین دوره بازنشستگی

### `HCM3.EmployeeRelatedOrganization.TaxGroupCode` → `TaxGroup`
1=100%، 2=50%، 3=10%، 4=بازنشسته وظیفه و مستمری بگیر، 5=آزاده و جانباز، 6=شاغلین در مناطق آزاد، 7=مشمولان قانون استخدامی وزارت اطلاعات، 8=پرسنل نیروهای مسلح، 9=جانبازان انقلاب اسلامی، 10=آزادگان

### `HCM3.EmployeeRelative.RelationCode` → `EmployeeRelation`
1=پدر، 2=مادر، 3=زن، 4=شوهر، 5=برادر، 6=خواهر، 7=پسر، 8=دختر، 9=فرزند خوانده

### `HCM3.EmployeeRelative.MaritalStatusCode` → `MaritalStatus`
1=مجرد، 2=متأهل، 3=معیل

### `HCM3.EmployeeEducation.DegreeCode` → `EducationDegree` — مقادیر HCM: 4=دیپلم، 8=لیسانس (متفاوت از PersonEducationDegree در GNR3 که 1=دیپلم است)
1=بیسواد، 2=بیسواد و کم سواد، 3=دکترا یا مدرک معادل، 4=دیپلم، 5=زیر دیپلم، 6=فوق دیپلم، 7=فوق لیسانس، 8=لیسانس، 9=نامعلوم

### `HCM3.EmployeeEducation.CenterCode` → `EducationCenter`
1=دانشگاه آزاد اسلامی، 2=دانشگاه جامع علمی-کاربردی، 3=دانشگاه دولتی، 4=غیرانتفاعی و غیردولتی، 5=نا مشخص، 6=دانشگاه فنی و حرفه ای، 7=دانشگاه پیام نور، 8=هنرستان کاردانش

### `HCM3.EmployeeEducation.QualityCode` → `EducationQuality`
1=خوب، 2=متوسط، 3=ضعیف

### `HCM3.EmployeeEducation.MajorCode` → `EducationMajor`
1=ندارد، 2=نرم افزار، 3=سخت افزار، 4=دولتی، 5=بازرگانی

### `HCM3.EmployeePaymentLocation.TypeCode` → `PaymentLocationType`
1=بانک، 2=صندوق

### `HCM3.LoanInstalment.PaymentMethodCode` → `LoanInstalmentPaymentMethod`
0=سیستمی، 1=دستی، 2=تسویه حساب

### `HCM3.LoanPayment.Status` → `LoanPaymentState`
0=تسویه نشده، 1=تسویه شده

### `HCM3.LoanPayment.ExtraPaymentMethodCode` → `LoanExtraAmountPaymentType`
1=در اولین قسط، 2=با اولین قسط، 3=در آخرین قسط، 4=با آخرین قسط

### `HCM3.PeriodicCalc.SubTypeCode` → `CompensationCalcSubType` — 1 ذخیره، 2 پرداخت
1=ذخیره، 2=پرداخت

### `HCM3.PeriodicCalc.CompensationCalcTypeRef (FK)` → `CompensationCalcGroup` — نوع محاسبه خود جدول CompensationCalcType است
1=حقوق ماهیانه، 2=ماموریت، 3=دوره ای، 4=تعریف شده توسط کاربر، 5=تسویه حساب، 6=بازنشستگی

### `HCM3.CompensationFactor.CategoryCode` → `CompensationFactorCategory` — تأییدشده
1=مزایا، 2=کسور، 3=تعهدات کارفرما، 4=حکم مالی، 5=سایر، 6=مطالبات، 7=بدهی ها، 8=بدون طبقه

### `HCM3.CompensationFactor.AssignTypeCode` → `CompensationFactorAssignType`
1=محاسباتی، 2=ورودی

### `HCM3.CompensationFactor.MeasurementUnitCode` → `CompensationMeasurementUnit`
1=واحد پولی، 2=عدد، 3=روز، 4=روز-ساعت-دقیقه، 5=ساعت-دقیقه

### `HCM3.Job.GroupCode` → `JobGroup`
1=1، 2=10، 3=11، 4=12، 5=13، 6=14، 7=15، 8=16، 9=17، 10=18، 11=19، 12=2، 13=20، 14=3، 15=4، 16=5، 17=6، 18=7، 19=8، 20=9

### `HCM3.Job.ClassCode` → `JobClass`
1=رسته شغلی پیش فرض - عمومی، 2=بازرگانی، 3=خدمات، 4=تولید، 5=کنترل کیفیت، 6=فنی و مهندسی

### `HCM3.Department.Status` → `DepartmentStatus`
1=فعال، 2=غیر فعال

### `HCM3.Post.Status` → `PostStatus`
1=فعال، 2=غیر فعال

### `HCM3.VoucherSpecificationSL.NatureCode` → `VoucherSpecificationSLNature`
1=بدهکار، 2=بستانکار

### `HCM3.BatchEmployeeStatuteFactor.AssignmentMethodCode` → `BatchEmpStatuteFactorAssignmentMethod`
1=فرمول جدید، 2=فرمول عامل، 3=بدون تغییر از آخرین حکم، 4=مقدار مشخص

### `RPA3.PartyBankAccount.DocumentType` → `PartyBankAccountDocumentType`
1=دریافت، 2=پرداخت، 100=همه

### `RPA3.BankAccount.State` → `BankAccountState`
1=فعال، 2=بسته شده، 3=مسدود شده

### `GNR3.Project.State` → `ProjectState`
1=فعال، 2=غیرفعال

### `FIN3.VATParty.VATCategory` → `FundCategory` — حدسی؛ نیاز به تأیید
1=هزینه ای، 2=سرمایه ای

## ستون‌هایی که enum ندارند ولی معنی‌شان از داده/فرمول روشن است

- `FIN3.VoucherReference.OriginalEntityCode`: 1075 = استهلاک دارایی ثابت (≈۱۱۳K ردیف)، 1032 ≈ ۸۵۰ ردیف (احتمالاً رسید تحصیل)، 1008/1005/1076 کم‌تعداد. این کدها در `SYS3.EntityLookup.EntityName` نام کامل entity را دارند.
- `FIN3.DL.EntityCode`: 232 = Party (شخص/شرکت)، 241 = مرکز هزینه، 242 = پروژه، 450 = حساب بانکی.
- `HCM3.CompensationFactorProperty.Attributes`: bitmask (۰،۲،۸،۹،۱۰،۱۲،۱۳،۱۴،۲۴،۲۹،۱۳۶،۲۵۶) ویژگی‌های محاسبه (مستمر/غیرمستمر، مالیات‌پذیر، بیمه‌پذیر …)؛ بی‌اهمیت برای RAG.
- `HCM3.Employee.Status` در تضاد ظاهری با `EmployeeStatuteAfterIssueStatus`: برای وضعیت کارمند فقط از `EmployeeStatus` استفاده کنید.