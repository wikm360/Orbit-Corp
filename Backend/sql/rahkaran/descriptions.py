"""Persian descriptions of the ai semantic-layer views and columns (written as MS_Description extended properties).

COLS: global column-name -> description (the same column name means the same thing in every view).
OVERRIDES: (view, column) -> description for the few generic names whose meaning depends on the view.
VIEWS: view -> description. `apply(conn)` writes them and prints coverage (undocumented views/columns).
"""

COLS_TEXT = """
absent_days | روزهای غیبت
absorption_allowance | حق جذب (ریال)
account_number | شماره حساب
account_role | نقش تجاری حساب (bank, petty_cash, receivable_customer, retention_receivable, payable_vendor, vat_input, vat_output, contract_revenue, project_cost_wip, memorandum_debit …) استخراج‌شده از کد معین
account_type | نوع حساب: دائم، موقت (درآمد/هزینه)، انتظامی
accumulated_depreciation | استهلاک انباشته (ریال)
acquisition_type | نوع تحصیل: خرید، ساخت، اهدا …
adjust_net | جمع تعدیلات ماهیت ابتدا/انتهای دوره (اسناد نوع 8 و 9)، مثبت=بدهکار
adjustment_difference | تفاوت تطبیق (ریال)
admin_expense | هزینه‌های اداری و تشکیلاتی (GL 6213) به ریال
advance_received_balance | مانده‌ی پیش‌دریافت از کارفرما (ریال)؛ مثبت = طلب کارفرما از ما
advance_received_change | تغییر پیش‌دریافت در همان سال (ریال)، بستانکار منهای بدهکار
amount | مبلغ (ریال)
apply_date | تاریخ اجرای حکم/محاسبه
apply_date_jalali | تاریخ اجرای حکم به شمسی
apply_year_month | ماه اجرا به صورت YYYYMM شمسی
approx_age | سن تقریبی (سال)
approx_age_years | سن تقریبی دارایی از تاریخ بهره‌برداری (سال)
approx_service_years | سابقه‌ی تقریبی خدمت از اولین تاریخ استخدام (سال)
armangohar_shares_deduction | کسر بابت خرید سهام آرمان گهر نصر از حقوق (ریال)
arrears_benefit | معوقه‌ی کارکنان (ریال)
asset_class | طبقه دارایی (وسایط نقلیه، ماشین‌آلات و تجهیزات، زمین، ساختمان …)
asset_class_code | کد طبقه دارایی
asset_class_id | شناسه طبقه دارایی
asset_count | تعداد دارایی
asset_group | گروه دارایی (زیرمجموعه طبقه)
asset_group_code | کد گروه دارایی
asset_group_id | شناسه گروه دارایی
asset_id | شناسه دارایی (FAM3.Asset)
asset_module_amount | مبلغ بر اساس ماژول دارایی ثابت (ریال)
asset_state_after | وضعیت دارایی پس از این رویداد
asset_state_code | کد وضعیت دارایی پس از رویداد
asset_title | عنوان دارایی
assign_type | روش مقداردهی عامل: محاسباتی یا ورودی
assignment_kind | نوع انتساب: مرکز هزینه یا پروژه
attendance_calc_id | شناسه محاسبه حضور و غیاب
attribute_name | نام ویژگی دارایی (مدل، رنگ، شماره شاسی، کشور سازنده …)
attribute_value | مقدار ویژگی
auxiliary_number | شماره فرعی سند
balance | مانده (ریال)؛ مثبت = بدهکار
balance_net | مانده‌ی خالص (بدهکار−بستانکار) به ریال
balance_net_debit | مانده‌ی خالص = بدهکار − بستانکار (ریال)؛ مثبت بدهکار، منفی بستانکار
balance_sheet_net | جمع مانده‌ی حساب‌های ترازنامه‌ای (ریال)
balance_side | سمت مانده: بدهکار / بستانکار / صفر
bank_account_dl_code | کد تفصیلی حساب بانکی شرکت در ردیف سند
bank_account_id | شناسه حساب بانکی (RPA3.BankAccount)
bank_account_name | عنوان تفصیلی حساب بانکی
bank_name | نام بانک
base_pay | مزد شغل (حقوق پایه‌ی ماهانه به ریال)
birth_date | تاریخ تولد
birth_date_jalali | تاریخ تولد شمسی
bonus_reward | پاداش (ریال)
book_value | ارزش دفتری (بها − استهلاک انباشته) به ریال
branch_code | کد شعبه
branch_name | نام شعبه
buyer_dl_code | کد تفصیلی خریدار
buyer_name | نام خریدار
calc_type | نوع محاسبه (حقوق، عیدی، بازخرید مرخصی، بازخرید سنوات، تسویه، بازنشستگی)
calculated_value | مقدار محاسبه‌شده‌ی سیستم
capacity | ظرفیت پست
car_insurance_deduction | کسورات بیمه نوین (خودرو) از حقوق (ریال)
category | دسته‌بندی
child_allowance | حق اولاد (ریال)
children_count | تعداد فرزندان ثبت‌شده (فعال)
city | شهر
closing_balance_net | مانده‌ی پایان سال قبل از اسناد بستن حساب‌ها = افتتاحیه + گردش + تعدیلات؛ مثبت بدهکار
closing_entries_net | جمع اسناد بستن حساب‌ها/اختتامیه (انواع 5 و 7)
closing_state | وضعیت بسته‌شدن سال مالی
closing_state_code | کد وضعیت سال مالی (6 بسته‌شده، 4 جاری، 0 شروع نشده، 2 نخستین سال)
code | کد
collector_name | نام متصدی/متولی دارایی
column_count | تعداد ستون‌ها
column_name | نام ستون
company_advance_deduction | کسر مساعده‌ی شرکتی از حقوق (ریال)
company_fund_membership | کسر عضویت صندوق شرکت (ریال)
company_name | نام شرکت (شخص حقوقی)
company_type | نوع شرکت (سهامی خاص، مسئولیت محدود، سازمان …)
confirm_date | تاریخ تأیید
confirmation_date | تاریخ تأیید/پرداخت وام
contract_cost | هزینه‌ی قرارداد (ریال) = گردش خالص GL 1117 (طی سال) + GL 5111 (بعد از انتقال پایان سال)
contract_cost_center_id | شناسه مرکز هزینه‌ی قرارداد
contract_dl_code | کد تفصیلی قرارداد/پیمان (مرکز هزینه 66xxxx)
contract_name | عنوان قرارداد/پروژه اجرایی (شامل شماره پیمان)
contract_revenue | درآمد پیمان‌ها (SL 411010) به ریال
contract_state | وضعیت قرارداد (فعال/غیرفعال)
cost | بهای تمام‌شده (ریال)
cost_center | نام مرکز هزینه (قرارداد، ماشین، خودرو …)
cost_center_dl_code | کد تفصیلی مرکز هزینه
cost_center_effective_ym | ماه شمسی شروع انتساب مرکز هزینه به کارمند
cost_center_id | شناسه مرکز هزینه (GNR3.CostCenter)
cost_center_name | نام مرکز هزینه
cost_center_number | شماره مرکز هزینه
cost_center_type | نوع مرکز هزینه: اداری، تولیدی، خدماتی، پیمانکار خارجی
pnl_statement | سرفصل صورت سود و زیان طبق طبقه‌بندی حسابدار (مثلاً «بهای تمام شده درآمد های عملیاتی»، «هزینه های اداری تشکیلاتی»، «درآمد های عملیاتی»، «هزینه‌های مالی»)؛ خالی = معین در طبقه‌بندی حسابدار نیست
detail_category | دسته‌ی تحلیلی حسابدار (حقوق، سوخت، مواد و مصالح، استهلاک، پیمانکاران، اجاره ماشین/ تجهیز، تعمیرات، ایمنی و بهداشت، بیمه و عوارض، سایر هزینه ها …)؛ معین‌های آینه‌ای 1117xx/5111xx/5112xx/6213xx یک دسته دارند؛ خالی = طبقه‌بندی نشده
taxonomy_source | منبع طبقه‌بندی: accountant (در فایل حسابدار) یا derived (آینه‌ی یک معین فایل حسابدار)
source_sl_name | عنوان معین در فایل حسابدار
cost_nature_key | کلید ماهیت هزینه (۲ رقم آخر کد معین) مشترک بین 1117xx / 5111xx / 5112xx / 5114xx / 6213xx؛ مثلاً 50 حق‌الزحمه پیمانکاران، 52 اجاره ماشین‌آلات، 04 حقوق
cost_of_goods_sold | قیمت تمام‌شده کالای فروش‌رفته (GL 5110)
counterparty_dl_code | کد تفصیلی طرف‌حساب (شخص یا شرکت)
counterparty_name | نام طرف‌حساب
counterparty_party_id | شناسه شخص/شرکت (GNR3.Party) طرف‌حساب
created_by | کاربر ثبت‌کننده
created_date | تاریخ ایجاد رکورد
credit | بستانکار (ریال)
credit_balance | مانده بستانکار (ریال)
current_cost_center | مرکز هزینه/قرارداد فعلی انتساب هزینه‌ی کارمند
current_cost_center_dl_code | کد تفصیلی مرکز هزینه‌ی فعلی کارمند
current_project | پروژه فعلی کارمند
current_project_dl_code | کد تفصیلی پروژه فعلی کارمند
daily_number | شماره روزانه سند
daily_wage | دستمزد روزانه (ریال)
data_type | نوع داده ستون
days_equivalent | معادل روز (مقدار دقیقه ÷ 480)
debit | بدهکار (ریال)
debit_balance | مانده بدهکار (ریال)
degree | مدرک تحصیلی
deliverer_name | نام تحویل‌دهنده/تحویل‌گیرنده
department_code | کد واحد سازمانی
department_id | شناسه واحد سازمانی
department_name | نام واحد سازمانی (وسائل نقلیه، پروژه، امور اجرائی کارگاه …)
depreciation_amount | مبلغ استهلاک (ریال)
depreciation_date | تاریخ محاسبه استهلاک
depreciation_id | شناسه رویداد استهلاک
depreciation_method | روش استهلاک (خط مستقیم n ساله، نزولی …)
depreciation_rate_percent | نرخ استهلاک (درصد) برای روش نزولی
depreciation_start_date | تاریخ شروع محاسبه استهلاک
depreciation_state | وضعیت استهلاک: مستهلک نشده / مستهلک شده / استهلاک‌ناپذیر
description | توضیحات
destination_cost_center | مرکز هزینه‌ی مقصد انتقال
destination_location | محل مقصد انتقال
destination_project | پروژه‌ی مقصد انتقال
difference | اختلاف (دفتر کل − ماژول دارایی)
discipline | رشته تحصیلی
distinct_employees | تعداد کارمندان متمایز
dl4_code | کد تفصیلی سطح 4 ردیف سند (DLLevel4)
dl5_code | کد تفصیلی سطح 5 ردیف سند (DLLevel5)
dl6_code | کد تفصیلی سطح 6 ردیف سند (DLLevel6)
dl_category | دسته‌بندی کسب‌وکاری تفصیلی (کارمند، شخص، شرکت، ماشین‌آلات سنگین، کامیون، خودرو سبک، قرارداد/پروژه اجرایی، حساب بانکی، تسهیلات …)
dl_code | کد تفصیلی (یکتا)
dl_codes | کدهای تفصیلی مرتبط با این شخص
dl_id | شناسه تفصیلی
dl_kind | نوع تفصیلی: حساب بانکی یا بانک به‌عنوان شرکت
dl_title | عنوان تفصیلی
dl_type | نوع تفصیلی (شخص، شرکت، مرکز هزینه، پروژه، حساب بانکی، تسهیلات مالی، سایر)
dl_type_id | شناسه نوع تفصیلی
document_date | تاریخ سند/رویداد
document_number | شماره سند/رویداد
document_state | وضعیت سند رویداد
document_state_code | کد وضعیت سند رویداد
duration_days | تعداد روزهای دوره استهلاک
economic_code | کد اقتصادی
edited_value | مقدار ویرایش‌شده دستی
education_center | مرکز آموزشی (دانشگاه آزاد، دولتی …)
education_degree | مدرک تحصیلی
education_id | شناسه سابقه تحصیلی
effective_date | تاریخ اثر
effective_work_days | کارکرد مؤثر (روز)
effective_year_month | ماه شمسی شروع اثر (YYYYMM)
elimination_date | تاریخ حذف دارایی
elimination_id | شناسه سند حذف دارایی
elimination_number | شماره سند حذف دارایی
email | ایمیل
employee_code | کد پرسنلی
employee_count | تعداد کارمند
employee_id | شناسه کارمند (HCM3.Employee)
employee_life_insurance | بیمه عمر سهم کارمند (ریال)
employee_name | نام کارمند
employee_social_insurance | بیمه تأمین اجتماعی سهم کارگر (۷٪ مأخذ) به ریال
employee_status | وضعیت کارمند
employee_status_after_issue | وضعیت کارمند پس از صدور حکم
employee_supplementary_insurance | بیمه تکمیلی سهم کارمند (ریال)
employer_dl_code | کد تفصیلی کارفرما
employer_name | نام کارفرما
employer_social_insurance | بیمه تأمین اجتماعی سهم کارفرما (۲۰٪ مأخذ) به ریال
employer_supplementary_insurance | بیمه تکمیلی سهم کارفرما (ریال)
employer_total_cost | هزینه‌ی کل کارفرما برای کارمند = جمع مزایا + بیمه کارفرما + بیمه بیکاری + بیمه تکمیلی کارفرما (ریال)
employment_date | تاریخ استخدام
employment_date_jalali | تاریخ استخدام شمسی
employment_type | نوع استخدام (قراردادی، رسمی …)
end_date | تاریخ پایان
end_jalali | تاریخ پایان شمسی
entity_code | کد entity فرم مبدأ (در SYS3.EntityLookup)
equipment_category | دسته تجهیزات (ماشین‌آلات سنگین، کامیون/کمپرسی، خودرو سبک، تجهیزات ثابت)
equipment_cost_center_id | شناسه مرکز هزینه‌ی دستگاه
equipment_dl_code | کد تفصیلی دستگاه/خودرو (مرکز هزینه 41/42/43/44)
equipment_name | نام دستگاه/خودرو (با پلاک/شاسی)
expiry_date | تاریخ انقضا/پایان اعتبار
expiry_year_month | ماه شمسی پایان اعتبار
facility_dl_code | کد تفصیلی تسهیلات (وام بانکی)
facility_name | عنوان تسهیلات (وام)
factor_category | طبقه عامل حقوقی: مزایا، کسور، تعهدات کارفرما، حکم مالی، سایر …
factor_id | شناسه عامل
factor_key | نام لاتین عامل
factor_kind | نوع عامل حکم: مبلغ یا امتیاز/تعداد/شرط
factor_title | عنوان فارسی عامل
father_name | نام پدر
female_count | تعداد زنان
financial_class | طبقه‌ی مالی حساب (دارایی جاری، بدهی جاری، فروش و درآمد، بهای تمام‌شده، …)
financial_expense | هزینه‌های مالی (GL 6211)
first_activity_date | اولین تاریخ فعالیت
first_date | اولین تاریخ
first_fiscal_year | اولین سال مالی با فعالیت
first_name | نام
first_revenue_date | تاریخ اولین ثبت درآمد
first_voucher_date | تاریخ اولین سند
fiscal_month_no | شماره ماه در سال مالی (مهر=1 … شهریور=12)
fiscal_quarter | فصل سال مالی (1..4 از مهر)
fiscal_year | سال مالی (مثلاً 1404 = مهر 1404 تا شهریور 1405)
fiscal_year_id | شناسه سال مالی (GNR3.FiscalYear)
follow_up_date | تاریخ پیگیری
follow_up_number | شماره پیگیری
from_date | از تاریخ
full_name | نام کامل
gender | جنسیت (مرد/زن)
gl_code | کد حساب کل (۴ رقمی)
gl_id | شناسه حساب کل
gl_title | عنوان حساب کل
gpa | معدل
graduation_date | تاریخ فارغ‌التحصیلی
gregorian_date | تاریخ میلادی
group_code | کد گروه حساب (11 دارایی جاری، 12 غیرجاری، 21/22 بدهی، 31 حقوق صاحبان سهام، 41 درآمد، 51 بهای تمام‌شده، 61/62 هزینه، 91/92 انتظامی)
group_id | شناسه گروه حساب
group_title | عنوان گروه حساب
guarantee_type | نوع ضمانت‌نامه (شرکت در مناقصه، پیش‌دریافت، حسن انجام کار، حسن انجام تعهدات …)
hard_work_allowance | فوق‌العاده شرایط کار (ریال)
has_arrears_items | آیا آیتم معوقه (ماه اجرای قبل از ماه صدور) دارد
has_postings | آیا حداقل یک ردیف سند دارد
hcm_voucher_id | شناسه فرم صدور سند حقوق (HCM3.Voucher)
holder_name | نام دارنده تنخواه
holiday_work_pay | تعطیل کاری (ریال)
housing_allowance | حق مسکن (ریال)
id_number | شماره شناسنامه
included_in_child_allowance | مشمول حق اولاد
income_tax | مالیات حقوق (ریال)
instalment_amount | مبلغ هر قسط
instalment_count | تعداد اقساط
instalment_id | شناسه قسط
insurable_earnings | دستمزد و مزایای مشمول بیمه (ریال)
insurance_base | مأخذ بیمه = حداقل(مشمول بیمه، سقف) (ریال)
insurance_branch_code | کد شعبه بیمه
insurance_ceiling | سقف مأخذ بیمه (ریال)
insurance_deposit_amount | سپرده بیمه‌ی کسر شده از صورت‌وضعیت (ریال)
insurance_job_code | کد شغل در بیمه
insurance_number | شماره بیمه
insurance_organization | سازمان بیمه‌گر
is_active | فعال است
is_active_asset | دارایی فعال (پلاک‌شده)
is_administrator | مدیر سیستم
is_closing | سند بستن حساب‌ها/اختتامیه (انواع 5 و 7)
is_contract | مرکز هزینه‌ی قرارداد/پروژه اجرایی (کد 66xxxx)
is_current | مورد جاری
is_employee | شخص، کارمند است
is_equipment | مرکز هزینه‌ی دستگاه/خودرو (کد 41/42/43/44)
is_final | سند قطعی (وضعیت 32)
is_friday | جمعه است
is_guarantee_account | حساب ضمانت‌نامه‌ای
is_insurance | ثبت بیمه‌ای (در مقابل مالیاتی)
is_latest | آخرین رکورد
is_opening | سند افتتاحیه (انواع 6 و 11)
is_readonly | فقط‌خواندنی
is_regular | سند عادی (غیر از افتتاحیه، اختتامیه، بستن، تعدیل ماهیت)؛ برای گردش دوره
is_reviewed | سند بررسی‌شده یا قطعی (وضعیت 4 یا 32)
is_temporary | موقت
is_used | حداقل یک مقدار غیرصفر ثبت شده
is_valid_for_reports | سند معتبر برای گزارش: موقت (1)، بررسی‌شده (4) یا قطعی (32)؛ وضعیت 2 (یادداشت) خارج است
issue_date | تاریخ صدور
issue_year_month | ماه صدور/محاسبه به صورت YYYYMM شمسی (مثلاً 140505 = مرداد 1405)
item | عنوان آیتم
item_description | توضیحات ردیف
item_id | شناسه ردیف
item_title | عنوان ردیف
jahan_steel_shares_deduction | کسر بابت سهام جهان فولاد (ریال)
jalali_date | تاریخ شمسی (YYYY/MM/DD)
jalali_date_int | تاریخ شمسی به عدد (YYYYMMDD)
jalali_day | روز ماه شمسی
jalali_month | ماه شمسی (1 فروردین … 12 اسفند)
jalali_month_name | نام ماه شمسی
jalali_quarter | فصل سال شمسی
jalali_year | سال شمسی
jalali_ym | سال و ماه شمسی به عدد YYYYMM (مثل 140505) - هم‌ارز issue_year_month حقوق
job | شغل
job_class | رسته شغلی
job_code | کد شغل
job_group | گروه شغلی
job_id | شناسه شغل
job_title | عنوان شغل
judicial_deductions | کسورات قضایی (ریال)
karaneh | کارانه (ریال)
kind | نوع: revenue (درآمد) یا cost (هزینه)
last_activity_date | آخرین تاریخ فعالیت
last_date | آخرین تاریخ
last_fiscal_year | آخرین سال مالی با فعالیت
last_modified_by | آخرین ویرایشگر
last_modified_date | تاریخ آخرین ویرایش
last_name | نام خانوادگی
last_revenue_date | تاریخ آخرین ثبت درآمد
last_statute_apply_date | تاریخ اجرای آخرین حکم
last_statute_type | نوع آخرین حکم
last_voucher_date | تاریخ آخرین سند
leave_balance_id | شناسه مانده مرخصی
leave_type | نوع مرخصی
ledger_amount | مبلغ بر اساس دفتر کل (ریال)
line_count | تعداد ردیف
line_description | توضیحات ردیف سند
line_id | شناسه ردیف سند (VoucherItemID)
line_no | شماره ردیف در سند
loan_amount | مبلغ وام
loan_id | شناسه وام
loan_installments | جمع اقساط وام کسر شده (ریال)
loan_number | شماره وام
loan_type | نوع وام (مساعده شرکتی، سهام آرمان گهر نصر، سهام جهان فولاد، وام خسارت، کسورات بیمه خودرو …)
location_code | کد محل استقرار
location_id | شناسه محل استقرار
location_name | محل استقرار دارایی (کارخانه، پروژه، دفتر …)
lookup_type | نام نوع enum (SYS3.Lookup.Type)
lookup_type_title | عنوان فارسی نوع enum
machinery_unit_cost | هزینه‌ی واحد ماشین‌آلات (GL 5112) - قبل از تسهیم پایان سال
main_address | آدرس اصلی
major | گرایش
management_level_code | کد سطح مدیریتی
margin | حاشیه‌ی سود = درآمد − هزینه‌ی قرارداد (ریال)
margin_ratio | نسبت حاشیه سود = (درآمد−هزینه)/درآمد
marital_allowance | حق تاهل (ریال)
marital_status | وضعیت تأهل
meaning_fa | توضیح معنی
measurement_unit | واحد اندازه‌گیری
memorandum_and_other_net | جمع حساب‌های انتظامی و سایر (باید صفر باشد)
military_service_status | وضعیت نظام وظیفه
mission_input | ماموریت ورودی (ریال)
mobile | تلفن همراه
module | ماژول راهکاران (FIN3، HCM3، FAM3 …)
money_in | ورودی وجه (بدهکار حساب بانک)
money_out | خروجی وجه (بستانکار حساب بانک)
monthly_wage | دستمزد ماهانه (ریال)
months | تعداد ماه‌های دارای حقوق
national_id | کد ملی
nature_title | عنوان ماهیت هزینه
net_debit | بدهکار − بستانکار (ریال)؛ مثبت = بدهکار، منفی = بستانکار
net_pay | خالص پرداختی = جمع مزایا − جمع کسور (ریال)
net_payable | خالص بدهی به طرف‌حساب (ریال)؛ مثبت = ما بدهکاریم
net_position | موقعیت خالص با شرکت گروه (ریال)؛ مثبت = آن شرکت به ما بدهکار است
net_reward | خالص عیدی (ریال)
net_sales | خالص فروش
new_deliverer | تحویل‌گیرنده‌ی جدید
normal_balance | ماهیت طبیعی حساب (بدهکار/بستانکار/مهم نیست)
normal_work_days | روزهای کارکرد عادی (حضور و غیاب)
notes_payable_balance | مانده اسناد پرداختنی (ریال)
notes_receivable_balance | مانده اسناد دریافتنی (ریال)
old_plaque_number | شماره پلاک قدیم
opening_credit | بستانکار افتتاحیه (ریال)
opening_debit | بدهکار افتتاحیه (ریال)
opening_net | مانده‌ی افتتاحیه‌ی سال (ریال)؛ مثبت بدهکار
opening_remainder | مانده ابتدایی وام در زمان انتقال
operating_expense | هزینه‌های فعالیت (GL 61xx غیر از 6213)
ordinal | ترتیب ستون
organization | سازمان (بیمه تأمین اجتماعی، بیمه تکمیلی، سازمان دارایی)
organization_branch_code | کد شعبه سازمان
original_title | عنوان اصلی
other_detail_dl_code | کد تفصیلی «سایر» (نوع 27)
other_detail_name | عنوان تفصیلی «سایر» (قبض، دوره مالیاتی، کسورات، شماره ضمانت‌نامه …)
other_expense | سایر هزینه‌ها و درآمدهای غیرعملیاتی
other_revenue | سایر درآمدها
overtime_input | اضافه‌کار ورودی (ریال)
parents_supplementary_insurance_employee | بیمه تکمیلی والدین سهم کارمند (ریال)
parents_supplementary_insurance_employer | بیمه تکمیلی والدین سهم کارفرما (ریال)
party_id | شناسه شخص/شرکت (GNR3.Party)
party_type | نوع شخص: حقیقی/حقوقی
pay_calc_id | شناسه محاسبه حقوق (HCM3.PayCalc)
payable | قابل پرداخت (ریال)
payable_balance | مانده‌ی پرداختنی (ریال)؛ مثبت = ما بدهکاریم
payment_date | تاریخ پرداخت
payment_location_id | شناسه محل پرداخت حقوق
payment_method | روش پرداخت (سیستمی/دستی/تسویه حساب)
payment_year_month | ماه شمسی پرداخت (YYYYMM)
period_credit | بستانکار گردش دوره (اسناد عادی) به ریال
period_debit | بدهکار گردش دوره (اسناد عادی) به ریال
period_net | گردش خالص دوره = بدهکار − بستانکار (ریال)
periodic_calc_id | شناسه محاسبه‌ی دوره‌ای
phone | تلفن ثابت
physical_location | موقعیت فیزیکی (داخل سازمان، خارج سازمان، نزد انبار)
plant_unit_cost | هزینه‌ی واحد تأسیسات و کارخانه‌جات (GL 5114)
plaque_number | شماره پلاک (شماره اموال)
pnl_class | طبقه سود و زیان: contract_revenue, other_revenue, project_cost_wip (1117), project_cost_recognized (5111), machinery_unit_cost (5112), plant_unit_cost (5114), cost_of_goods_sold, operating_expense, admin_expense, financial_expense, other_expense
pnl_net | جمع مانده‌ی حساب‌های سود و زیان بسته‌نشده (ریال)؛ منفی = سود
post_code | کد پست سازمانی
post_id | شناسه پست
post_title | عنوان پست سازمانی
prepayment_balance | مانده‌ی پیش‌پرداخت‌ها (ریال)
previous_month_debt | بدهی ماه قبل (ریال)
profit_estimate | برآورد سود = درآمد کل − هزینه کل (ریال)
profit_for_year_unclosed | سود سال از حساب‌های درآمد/هزینه‌ی بسته‌نشده (ریال)
project_dl_code | کد تفصیلی پروژه
project_id | شناسه پروژه
project_name | نام پروژه
project_number | شماره پروژه
purchase_amount | مبلغ خرید (ریال)
quantity | مقدار/تعداد در ردیف سند
rank_pay | مزد رتبه (ریال)
receipt_date | تاریخ رسید تحصیل
receipt_id | شناسه رسید تحصیل
receipt_number | شماره رسید تحصیل
receipt_state | وضعیت رسید تحصیل
receivable_amount | مبلغ دریافتنی از کارفرما در این سند (ریال)
receivable_balance | مانده‌ی دریافتنی (ریال)؛ مثبت = طلب شرکت
receivable_change | تغییر دریافتنی در همان سال (ریال)
record_created_date | تاریخ ایجاد رکورد
reference_count | تعداد ارجاعات
reference_detail | مرجع/شرح ضمانت‌نامه (تفصیلی سایر)
reference_id | شناسه رکورد مرجع
region_name | منطقه/شهر
registration_code | کد ثبت
registration_id | شناسه ثبت بیمه
relation | نسبت خانوادگی
relative_id | شناسه فرد خانواده
remainder | مانده
retention_amount | مبلغ حسن انجام کار نگهداشته‌شده در این سند (ریال)
retention_payable_balance | مانده‌ی حسن انجام کار پرداختنی به پیمانکار (ریال)
retention_receivable_balance | مانده‌ی حسن انجام کار دریافتنی از کارفرما (ریال)
retention_receivable_change | تغییر حسن انجام کار دریافتنی در همان سال (ریال)
retirement_date | تاریخ بازنشستگی
revenue | درآمد (ریال)
revenue_amount | درآمد پیمان این سند (ریال)
revenue_voucher_count | تعداد اسناد درآمد (صورت‌وضعیت)
review_date | تاریخ بررسی
review_number | شماره بررسی
reward_benefit | مزایای عیدی (ریال)
reward_payable | قابل پرداخت عیدی (ریال)
reward_provision | ذخیره‌ی ماهانه‌ی عیدی (ریال)
reward_tax | مالیات عیدی (ریال)
sale_date | تاریخ فروش
sale_id | شناسه سند فروش دارایی
sale_number | شماره سند فروش دارایی
sales_amount | مبلغ فروش (ریال)
salvage_value | ارزش اسقاط (ریال)
seniority_pay | مزد سنوات (ریال)
settlement_status | وضعیت تسویه (تسویه نشده/تسویه شده)
severance_days | روزهای سنوات
severance_provision_current | ذخیره‌ی جاری سنوات (ریال)
severance_provision_total | جمع ذخیره‌ی سنوات تا انتهای دوره (ریال)
severance_result | نتیجه‌ی محاسبه‌ی سنوات (ریال)
sheba | شماره شبا
shift_work_pay | نوبت کاری (ریال)
sick_leave_days | روزهای مرخصی استعلاجی
sl_code | کد حساب معین (۶ رقمی؛ ۴ رقم اول کد کل)
sl_id | شناسه حساب معین
sl_title | عنوان حساب معین
social_insurance_total | جمع بیمه تأمین اجتماعی (کارگر + کارفرما + بیکاری)
source_entity | فرم مبدأ سند (Depreciation، AcquisitionReceipt، Sales …)
source_system | سیستم مبدأ سند (GL دستی، FAM دارایی ثابت، HCM حقوق، AST/PAY دلفی)
start_date | تاریخ شروع
start_jalali | تاریخ شروع شمسی
state | وضعیت (فعال/غیرفعال)
statement | صورت مالی: balance_sheet، income_statement، absorption، memorandum
status | وضعیت
status_code | کد وضعیت
statute_id | شناسه حکم
statute_number | شماره حکم
statute_status_code | کد وضعیت حکم
statute_type | نوع حکم (استخدام، تغییر حقوق، اصلاحیه، تغییر شعبه بیمه، غیرفعال، ترخیص …)
sub_type | زیرنوع: ذخیره یا پرداخت
suggestion_reward_points | امتیاز پاداش نظام پیشنهادات
suggestion_system_reward | پاداش نظام پیشنهادات (ریال)
supervision_allowance | فوق‌العاده سرپرستی (ریال)
supplier_dl_code | کد تفصیلی تأمین‌کننده
supplier_name | نام تأمین‌کننده
tax_group | گروه مالیاتی (100٪، 50٪، 10٪ …)
tax_period_dl_code | کد تفصیلی دوره مالیات بر ارزش افزوده
tax_period_or_detail | دوره مالیاتی یا شرح تفصیلی (مثلاً «دوره دوم سال 1405»)
taxable_income | درآمد مشمول مالیات (ریال)
term_fa | اصطلاح کسب‌وکاری
to_date | تا تاریخ
total_amount | جمع مبلغ (ریال)
total_assets | جمع دارایی‌ها (ریال)
total_benefits | جمع مزایا (ریال)
total_contract_cost | جمع هزینه‌ی قرارداد در کل دوره (ریال)
total_cost | جمع هزینه‌ها (ریال)
total_credit | جمع بستانکار (ریال)
total_debit | جمع بدهکار (ریال)
total_deductions | جمع کسور (ریال)
total_equity_before_result | جمع حقوق صاحبان سهام قبل از سود سال (ریال)
total_exposure | مانده‌ی کل مطالبات از مشتری = دریافتنی + حسن انجام کار + اسناد − پیش‌دریافت (ریال)
total_issued | جمع صادره/بدهکار شده (ریال)
total_liabilities | جمع بدهی‌ها (ریال)
total_margin | جمع حاشیه سود قرارداد (ریال)
total_monthly_terms | جمع مبالغ ماهانه‌ی حکم (ریال)
total_released | جمع آزادشده/بستانکار شده (ریال)
total_revenue | جمع درآمد (ریال)
transaction_id | شناسه رویداد دارایی
transaction_type | نوع رویداد دارایی (تحصیل، محاسبه استهلاک، فروش، حذف، انتقال داخلی، استقرار …)
transaction_type_code | کد نوع رویداد (2 = محاسبه استهلاک)
transfer_date | تاریخ انتقال
transfer_id | شناسه انتقال
transfer_number | شماره انتقال
transport_allowance | حق ایاب و ذهاب (ریال)
unemployment_insurance | بیمه بیکاری (۳٪ مأخذ، سهم کارفرما) به ریال
useful_life_years | عمر مفید (سال)
user_id | شناسه کاربر
user_name | نام کاربر
utilization_date | تاریخ بهره‌برداری
utilization_date_jalali | تاریخ بهره‌برداری شمسی
value | مقدار
value_en | مقدار انگلیسی
value_fa | مقدار فارسی
value_minutes | مقدار به دقیقه (۴۸۰ دقیقه = یک روز کاری)
vat_amount | مالیات بر ارزش افزوده‌ی این سند (ریال)
view_name | نام view
voucher_count | تعداد سند
voucher_date | تاریخ سند (میلادی)
voucher_description | توضیحات سرفصل سند
voucher_id | شناسه سند (FIN3.Voucher)
voucher_number | شماره سند
voucher_sequence | شماره ترتیب (عطف) سند
voucher_specification | الگوی صدور سند حسابداری (سند حقوق، ذخیره سنوات، ذخیره عیدی، پرداخت عیدی)
voucher_state | وضعیت سند: موقت، یادداشت، بررسی شده، قطعی
voucher_state_code | کد وضعیت سند (1 موقت، 2 یادداشت، 4 بررسی شده، 32 قطعی)
voucher_type | نوع سند (عمومی، افتتاحیه، اختتامیه، بستن حساب‌ها، دارایی ثابت، جبران خدمات …)
voucher_type_id | شناسه نوع سند
weekday_name | نام روز هفته
weekday_no | شماره روز هفته (0 شنبه … 6 جمعه)
where_to_query | محل پرس‌وجو (view / ستون / فیلتر)
worker_bon | بن کارگری (ریال)
"""

COLS = {}
for _line in COLS_TEXT.strip().splitlines():
    _name, _, _desc = _line.partition(" | ")
    COLS[_name.strip()] = _desc.strip()

OVERRIDES = {
    ("trial_balance_sl_year", "closing_balance_net"): "مانده‌ی پایان سال قبل از اسناد بستن = افتتاحیه + گردش + تعدیلات (برای حساب‌های موقت = نتیجه‌ی سال)؛ مثبت بدهکار",
    ("balance_sheet_year", "balance_net"): "مانده‌ی پایان سال (قبل از اسناد بستن)؛ مثبت = بدهکار، منفی = بستانکار",
    ("pnl_by_account_year", "amount"): "مبلغ در جهت طبیعی حساب: درآمد = بستانکار−بدهکار، هزینه = بدهکار−بستانکار (ریال)",
    ("revenue_lines", "amount"): "مبلغ درآمد = بستانکار − بدهکار (ریال)",
    ("cost_lines", "amount"): "مبلغ هزینه = بدهکار − بستانکار (ریال)",
    ("equipment_cost_year", "amount"): "هزینه‌ی دستگاه = بدهکار − بستانکار (ریال)",
    ("cost_by_nature_year", "total_amount"): "جمع هزینه‌ی همه‌ی طبقه‌ها برای این ماهیت (ریال)",
    ("fiscal_years", "state"): "وضعیت",
    ("accounts", "is_active"): "معین فعال است",
    ("dl_accounts", "is_active"): "تفصیلی فعال است",
    ("assets", "status"): "وضعیت فعلی دارایی (پلاک شده = فعال، حذف شده، فروش رفته، اسقاط شده، خارج شده از سازمان …)",
    ("assets", "cost"): "بهای تمام‌شده‌ی فعلی (ریال)",
    ("asset_depreciation", "cost"): "بهای تمام‌شده‌ی دارایی پس از محاسبه‌ی استهلاک (ریال)",
    ("asset_depreciation", "accumulated_depreciation"): "استهلاک انباشته پس از این محاسبه (ریال)",
    ("asset_acquisitions", "description"): "توضیحات رسید تحصیل",
    ("asset_ledger_reconciliation", "item"): "موضوع مقایسه",
    ("bank_balances", "balance"): "مانده‌ی تجمعی حساب بانکی (ریال)؛ مثبت = موجودی",
    ("petty_cash_balances", "balance"): "مانده‌ی تنخواه نزد دارنده (ریال)",
    ("account_monthly_turnover", "net_debit"): "گردش خالص ماه = بدهکار − بستانکار",
    ("employees", "status"): "وضعیت کارمند: فعال، غیرفعال، معلق، جدید …",
    ("employee_statutes", "status"): "وضعیت حکم (ذخیره، تایید کارگزینی، تایید پرداخت)",
    ("employees", "description"): "توضیحات",
    ("departments", "status"): "وضعیت واحد (فعال/غیرفعال)",
    ("posts", "status"): "وضعیت پست",
    ("jobs", "status"): "وضعیت شغل",
    ("loans", "remainder"): "مانده‌ی وام (ریال)؛ 0 = تسویه",
    ("loan_instalments", "amount"): "مبلغ قسط (ریال)",
    ("payroll_factor_values", "value"): "مقدار عامل (ریال یا روز/تعداد بر اساس عامل)",
    ("periodic_calc_values", "value"): "مقدار عامل (ریال یا روز)",
    ("employee_statute_factors", "value"): "مقدار عامل در حکم (ریال ماهانه یا امتیاز)",
    ("lookup_values", "code"): "کد عددی مقدار enum",
    ("guarantee_balances", "total_issued"): "جمع بدهکار (صدور/دریافت ضمانت‌نامه)",
    ("guarantee_balances", "balance_net_debit"): "مانده‌ی ضمانت‌نامه‌های باز (ریال)؛ مثبت = معتبر/باز",
    ("vat_lines", "debit"): "بدهکار (ارزش افزوده ورودی یا تسویه)",
    ("vat_lines", "credit"): "بستانکار (ارزش افزوده خروجی)",
    ("contract_statements", "description"): "توضیحات سند صورت‌وضعیت (شامل شماره پیمان و شماره صورت‌وضعیت)",
    ("data_freshness", "value"): "مقدار",
    ("column_catalog", "description"): "توضیح ستون",
    ("view_catalog", "description"): "توضیح view",
    ("glossary", "meaning_fa"): "معنی اصطلاح",
}

VIEWS = {
    "account_taxonomy": "طبقه‌بندی حسابدار برای معین‌های درآمد و هزینه: سرفصل صورت سود و زیان (pnl_statement) ← دسته‌ی تحلیلی (detail_category) ← کد معین (sl_code). منبع: فایل mehvargostar_code.xlsx؛ برای پرسش‌های «هزینه‌ی X» اول دسته را از اینجا پیدا کن.",
    "pnl_by_category_year": "درآمد و هزینه هر سال مالی به تفکیک طبقه‌بندی حسابدار (pnl_statement و detail_category مثل حقوق، سوخت، مواد و مصالح) و pnl_class؛ هزینه‌ی 1117xx (طی سال)، 5111xx/5112xx (بعد از انتقال پایان سال) و 6213xx (اداری) در یک دسته جمع می‌شوند.",
    "calendar": "تقویم روزانه ۲۰۰۰ تا ۲۰۴۰ با تاریخ شمسی و تقویم مالی (سال مالی از اول مهر). برای تبدیل تاریخ میلادی↔شمسی با JOIN روی gregorian_date.",
    "lookup_values": "فرهنگ مقادیر enum سیستم (SYS3.Lookup) با ترجمه‌ی فارسی و انگلیسی؛ برای رمزگشایی کدهای عددی در جدول‌های خام.",
    "fiscal_years": "سال‌های مالی با برچسب واقعی ۴ رقمی (fiscal_year)، بازه‌ی تاریخ (مهر تا شهریور)، وضعیت بسته‌شدن و تعداد اسناد.",
    "accounts": "نمودار حساب‌ها: گروه > کل > معین با ماهیت، طبقه‌ی مالی، طبقه سود و زیان (pnl_class)، نقش تجاری (account_role) و کلید ماهیت هزینه.",
    "dl_accounts": "حساب‌های تفصیلی (اشخاص، شرکت‌ها، مراکز هزینه، پروژه‌ها، حساب بانکی، تسهیلات، سایر) با دسته‌بندی کسب‌وکاری و شناسه مرجع.",
    "parties": "اشخاص حقیقی و حقوقی (کارکنان، تأمین‌کنندگان، کارفرماها) با کد ملی، تماس و آدرس اصلی و پیوند به کارمند/تفصیلی. حاوی اطلاعات هویتی.",
    "cost_centers": "مراکز هزینه: قراردادها/پروژه‌های اجرایی (is_contract، کد 66xxxx)، ماشین‌آلات سنگین (41)، کامیون (42)، خودرو سبک (43)، تجهیزات ثابت (44).",
    "projects": "پروژه‌های شرکتی (GNR3.Project). بُعد پروژه در هزینه‌ها بیشتر «عمومی(اداری)» است؛ قرارداد واقعی همان مرکز هزینه 66xxxx است.",
    "bank_accounts": "حساب‌های بانکی شرکت با بانک، شعبه، نوع حساب، شبا و کد تفصیلی.",
    "users": "کاربران راهکاران (بدون اطلاعات ورود).",
    "vouchers": "اسناد حسابداری (سرفصل) با جمع بدهکار/بستانکار، نوع، وضعیت، ثبت‌کننده و تاریخ شمسی. فیلتر گزارش: is_valid_for_reports = 1.",
    "ledger_lines": "جدول اصلی گزارش‌های مالی: هر ردیف سند با سند، حساب (گروه/کل/معین)، تاریخ شمسی/سال مالی و ابعاد تفصیلی تفکیک‌شده (طرف‌حساب، قرارداد، دستگاه، مرکز هزینه، پروژه، حساب بانکی، تسهیلات، سایر). حتماً روی fiscal_year و is_valid_for_reports فیلتر کنید.",
    "trial_balance_sl_year": "تراز آزمایشی معین در هر سال مالی: افتتاحیه، گردش عادی، تعدیلات، اسناد بستن و مانده‌ی پایان سال.",
    "trial_balance_gl_year": "تراز آزمایشی در سطح کل (GL) برای هر سال مالی.",
    "balance_sheet_year": "ترازنامه: مانده‌ی پایان سال حساب‌های ترازنامه‌ای در سطح کل (قبل از اسناد بستن).",
    "balance_sheet_check_year": "کنترل ترازنامه: جمع حساب‌های ترازنامه‌ای + سود و زیان بسته‌نشده + انتظامی باید صفر شود؛ شامل جمع دارایی/بدهی/حقوق صاحبان سهام. در سال جاری هزینه‌ی قراردادها در GL 1117 (ترازنامه) است.",
    "account_monthly_turnover": "گردش ماهانه‌ی هر معین (فقط اسناد عادی) برای روند و نمودار.",
    "pnl_by_account_year": "درآمد و هزینه به تفکیک سال مالی و معین (kind = revenue/cost، amount در جهت طبیعی). هزینه‌ی قراردادها = project_cost_wip + project_cost_recognized.",
    "income_summary_year": "خلاصه سود و زیان هر سال مالی: درآمد، هزینه‌ی قراردادها، هزینه‌ی ماشین‌آلات، اداری، مالی و برآورد سود.",
    "revenue_lines": "ردیف‌های درآمد دفتر کل (اسناد عادی معتبر) با قرارداد و طرف‌حساب.",
    "cost_lines": "ردیف‌های هزینه دفتر کل (قراردادها، ماشین‌آلات، اداری، مالی …) با قرارداد، دستگاه و ماهیت هزینه.",
    "cost_by_nature_year": "هزینه به تفکیک ماهیت (حقوق، اجاره، سوخت، پیمانکار، مواد …) و سال مالی با ادغام معین‌های 1117xx/5111xx/5112xx/6213xx.",
    "contract_financials_year": "عملکرد هر قرارداد در هر سال مالی: درآمد، هزینه، حاشیه سود، تعداد صورت‌وضعیت و مانده‌ی تجمعی مطالبات/حسن انجام کار/پیش‌دریافت.",
    "contract_financials": "جمع کل هر قرارداد: کارفرما، درآمد و هزینه‌ی کل، حاشیه سود، آخرین مانده‌ی مطالبات و حسن انجام کار.",
    "contract_statements": "صورت‌وضعیت‌های کارفرما (سند درآمد پیمان): درآمد، ارزش افزوده، مطالبات، حسن انجام کار، سپرده بیمه و توضیحات.",
    "counterparty_balances": "مانده‌ی تجمعی هر طرف‌حساب (شخص/شرکت) در هر معین ترازنامه‌ای.",
    "customer_balances": "وضعیت مطالباتی هر کارفرما: دریافتنی، حسن انجام کار، اسناد دریافتنی، پیش‌دریافت و مانده‌ی کل.",
    "vendor_balances": "وضعیت بدهی به هر تأمین‌کننده/پیمانکار: پرداختنی، اسناد، حسن انجام کار پرداختنی، پیش‌پرداخت و خالص.",
    "group_company_balances": "مانده با شرکت‌های گروه (نصر): دریافتنی، پرداختنی و موقعیت خالص.",
    "guarantee_balances": "ضمانت‌نامه‌ها و اسناد تضمینی (حساب‌های انتظامی 911xxx) به تفکیک نوع، ذینفع/بانک، قرارداد و مرجع.",
    "bank_balances": "مانده‌ی حساب‌های بانکی شرکت (تجمعی تا آخرین سند معتبر).",
    "bank_movements": "گردش حساب‌های بانکی: ورود وجه (بدهکار) و خروج وجه (بستانکار) با شرح سند.",
    "voucher_search": "جستجوی متنی سبک در توضیحات سند و ردیف سند (بدون join ابعاد) برای پیدا کردن اسناد؛ سپس با voucher_id به ledger_lines/vouchers وصل کنید.",
    "vat_lines": "ردیف‌های مالیات بر ارزش افزوده (ورودی، خروجی، سپرده) با دوره‌ی مالیاتی.",
    "facility_balances": "مانده‌ی تسهیلات بانکی (وام‌ها) به تفکیک وام و معین (اصل/کارمزد).",
    "equipment_cost_year": "هزینه‌ی هر دستگاه/خودرو (مرکز هزینه 41–44) به تفکیک سال، ماهیت هزینه (تعمیر، سوخت، استهلاک، اجاره …) و معین.",
    "petty_cash_balances": "مانده‌ی تنخواه‌گردان‌ها به تفکیک دارنده.",
    "voucher_sources": "فرم مبدأ هر سند حسابداری (استهلاک، رسید تحصیل، فروش، حذف دارایی …).",
    "departments": "واحدهای سازمانی (HCM3.Department) با نام تمیز.",
    "posts": "پست‌های سازمانی.",
    "jobs": "مشاغل با رسته، گروه و کد بیمه.",
    "employee_statutes": "همه‌ی احکام کارگزینی کارکنان (استخدام، تغییر حقوق، تغییر شعبه بیمه، غیرفعال …). حکم مؤثر = آخرین حکم با status_code = 10 (تایید پرداخت).",
    "employee_current_statutes": "حکم مؤثر فعلی هر کارمند (واحد، پست، شغل، نوع استخدام).",
    "employee_statute_factors": "عوامل مالی هر حکم (مزد شغل، حق مسکن، حق اولاد …).",
    "employees": "کارکنان با مشخصات فردی، وضعیت، حکم فعلی، مرکز هزینه/قرارداد فعلی، شماره بیمه و سابقه. حاوی اطلاعات هویتی.",
    "employee_current_pay_terms": "شرایط مالی حکم فعلی هر کارمند به صورت ستونی (مزد شغل، مسکن، اولاد، سنوات، بن …).",
    "employee_cost_center_history": "تاریخچه انتساب هزینه‌ی کارمند به مرکز هزینه/قرارداد و پروژه.",
    "employee_relatives": "اعضای خانواده‌ی کارکنان (همسر، فرزند، والدین).",
    "employee_education": "سوابق تحصیلی کارکنان.",
    "employee_bank_accounts": "حساب بانکی/شبای محل پرداخت حقوق کارکنان. حساس.",
    "employee_insurance": "ثبت‌های بیمه (تأمین اجتماعی و تکمیلی) و گروه مالیاتی کارکنان در طول زمان.",
    "loans": "وام‌ها و مساعده‌ها و خرید سهام کسر از حقوق کارکنان.",
    "loan_instalments": "اقساط وام کارکنان به تفکیک ماه شمسی.",
    "leave_balances": "مانده‌ی مرخصی استحقاقی کارکنان به دقیقه و معادل روز.",
    "headcount_current": "تعداد کارکنان فعال به تفکیک واحد و نوع استخدام.",
    "payroll_monthly": "حقوق ماهانه: یک ردیف برای هر کارمند در هر ماه با عوامل اصلی به صورت ستون (مزایا، کسور، خالص، بیمه، مالیات، وام …). issue_year_month شمسی YYYYMM.",
    "payroll_factor_values": "حقوق به صورت بلند (هر عامل یک ردیف) برای عوامل غیر از ستون‌های payroll_monthly. حجیم است؛ حتماً روی issue_year_month فیلتر کنید.",
    "compensation_factors": "فرهنگ ۲۸۵ عامل حقوقی با طبقه و استفاده‌شدن.",
    "payroll_month_summary": "جمع کل حقوق هر ماه: تعداد، مزایا، کسور، خالص، بیمه‌ها، مالیات و هزینه‌ی کل کارفرما.",
    "payroll_by_cost_center_month": "هزینه حقوق هر ماه به تفکیک مرکز هزینه/قرارداد.",
    "payroll_by_department_month": "هزینه حقوق هر ماه به تفکیک واحد سازمانی.",
    "payroll_year_summary": "جمع حقوق هر سال مالی (مهر تا شهریور).",
    "periodic_calc_values": "محاسبات دوره‌ای (عیدی، بازخرید سنوات، بازخرید مرخصی، تسویه) به صورت بلند: هر عامل یک ردیف.",
    "periodic_payments": "خلاصه‌ی ستونی محاسبات دوره‌ای: عیدی و ذخیره‌ی آن، نتیجه و ذخیره‌ی سنوات.",
    "payroll_accounting_vouchers": "اسناد حسابداری صادرشده از حقوق (سند حقوق، ذخیره سنوات، ذخیره عیدی، پرداخت عیدی) برای هر ماه.",
    "attendance_monthly": "خلاصه‌ی ماهانه حضور و غیاب (فقط خلاصه؛ تردد خام وجود ندارد؛ داده‌ی معنی‌دار تا 1402 است و از 1403 فقط شاخص پاداش پیشنهادات ثبت شده).",
    "asset_groups": "طبقه و گروه دارایی‌ها با تعداد.",
    "asset_locations": "محل‌های استقرار دارایی‌ها با تعداد.",
    "assets": "دارایی‌های ثابت با وضعیت فعلی، بها، استهلاک انباشته، ارزش دفتری، روش استهلاک، محل، مرکز هزینه و تأمین‌کننده. is_active_asset=1 یعنی پلاک‌شده/فعال.",
    "asset_value_by_group": "بها، استهلاک انباشته و ارزش دفتری فعلی به تفکیک طبقه، گروه و وضعیت دارایی.",
    "asset_value_by_location": "ارزش دارایی‌های فعال به تفکیک محل، مرکز هزینه و پروژه.",
    "asset_transactions": "تاریخچه‌ی رویدادهای دارایی (تحصیل، استهلاک، استقرار، انتقال، فروش، حذف). رویدادهای استهلاک (نوع 2) بیشترین حجم‌اند.",
    "asset_depreciation": "استهلاک هر دارایی در هر دوره‌ی ماهانه با مبلغ استهلاک، استهلاک انباشته و بها.",
    "depreciation_summary_month": "هزینه‌ی استهلاک ماهانه به تفکیک طبقه و گروه دارایی.",
    "asset_acquisitions": "رسیدهای تحصیل (خرید) دارایی با تأمین‌کننده، مبلغ، شماره پلاک و محل.",
    "asset_sales": "دارایی‌های فروخته‌شده با خریدار و مبلغ فروش.",
    "asset_disposals": "دارایی‌های حذف شده (Elimination) با تاریخ و شرح.",
    "asset_transfers": "انتقال‌های داخلی دارایی بین محل‌ها/مراکز هزینه/متصدیان.",
    "asset_attributes": "ویژگی‌های آزاد دارایی (مدل، شماره شاسی، رنگ، کشور سازنده …).",
    "asset_ledger_reconciliation": "مقایسه‌ی بها و استهلاک انباشته در ماژول دارایی با دفتر کل.",
    "data_freshness": "تازگی داده‌ها: آخرین تاریخ سند معتبر/بررسی‌شده، آخرین ماه حقوق، آخرین استهلاک.",
    "glossary": "فرهنگ اصطلاحات کسب‌وکاری (فارسی) و محل پرس‌وجوی داده.",
    "view_catalog": "فهرست view های لایه‌ی معنایی (ai) با توضیح.",
    "column_catalog": "فهرست ستون‌های view های ai با نوع داده و توضیح.",
}


def apply(conn):
    cur = conn.cursor()
    cur.execute("SELECT v.name, c.name FROM sys.views v JOIN sys.columns c ON c.object_id = v.object_id WHERE v.schema_id = SCHEMA_ID('ai') ORDER BY v.name, c.column_id")
    pairs = cur.fetchall()
    views = sorted({v for v, _ in pairs})
    missing_views = [v for v in views if v not in VIEWS]
    missing_cols = [(v, c) for v, c in pairs if (v, c) not in OVERRIDES and c not in COLS]

    def upsert(level2_type, level2_name, value, level1_name='ai', level0=None, view=None):
        pass

    for v in views:
        text = VIEWS.get(v)
        if text:
            cur.execute("""
                IF EXISTS (SELECT 1 FROM sys.extended_properties WHERE class = 1 AND major_id = OBJECT_ID(%s) AND minor_id = 0 AND name = 'MS_Description')
                    EXEC sys.sp_updateextendedproperty @name = N'MS_Description', @value = %s, @level0type = N'SCHEMA', @level0name = N'ai', @level1type = N'VIEW', @level1name = %s
                ELSE
                    EXEC sys.sp_addextendedproperty @name = N'MS_Description', @value = %s, @level0type = N'SCHEMA', @level0name = N'ai', @level1type = N'VIEW', @level1name = %s
            """, ("ai." + v, text, v, text, v))
    n = 0
    for v, c in pairs:
        text = OVERRIDES.get((v, c)) or COLS.get(c)
        if not text:
            continue
        cur.execute("""
            IF EXISTS (SELECT 1 FROM sys.extended_properties ep JOIN sys.columns col ON col.object_id = ep.major_id AND col.column_id = ep.minor_id
                       WHERE ep.class = 1 AND ep.major_id = OBJECT_ID(%s) AND col.name = %s AND ep.name = 'MS_Description')
                EXEC sys.sp_updateextendedproperty @name = N'MS_Description', @value = %s, @level0type = N'SCHEMA', @level0name = N'ai', @level1type = N'VIEW', @level1name = %s, @level2type = N'COLUMN', @level2name = %s
            ELSE
                EXEC sys.sp_addextendedproperty @name = N'MS_Description', @value = %s, @level0type = N'SCHEMA', @level0name = N'ai', @level1type = N'VIEW', @level1name = %s, @level2type = N'COLUMN', @level2name = %s
        """, ("ai." + v, c, text, v, c, text, v, c))
        n += 1
    print(f"descriptions applied: {len(views) - len(missing_views)}/{len(views)} views, {n}/{len(pairs)} columns")
    if missing_views:
        print("views without description:", missing_views)
    if missing_cols:
        print("columns without description:", missing_cols[:60], "..." if len(missing_cols) > 60 else "")
