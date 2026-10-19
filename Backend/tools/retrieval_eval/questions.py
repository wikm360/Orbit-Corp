"""Evaluation questions for document retrieval: (id, category, question, must-contain list).

A retrieved chunk counts as relevant when ALL `must` strings (normalized with `app.core.text_normalization.normalize`,
whitespace collapsed) occur in it. `must=None` marks a negative question: nothing in the corpus answers it.
Written against the Sohrab tender corpus kept in Backend/eval/ (see corpus.py); replace with questions about your own files.
"""

# (id, category, question, must-contain list (normalized, ALL must appear in a relevant chunk))
Q = [
 # --- Persian fact / number questions (semantic + exact)
 ("g1-wc","fact_fa","حداکثر نسبت آب به سیمان برای دوغاب نوع G1 چقدر است؟",["g1","0 4"]),
 ("g1-comp","fact_fa","حداقل مقاومت فشاری دوغاب G1 در ۷ روز طبق چه استانداردی تعیین می‌شود؟",["c109"]),
 ("g2-store","fact_fa","حداکثر زمان نگهداری گروت بدون انقباض در محل کار چند ماه است؟",["10 ماه"]),
 ("conc-temp","fact_fa","حداکثر دمای مجاز بتن چند درجه سانتی‌گراد است؟",["60 درجه"]),
 ("conc-water","fact_fa","آب مصرفی در اختلاط بتن باید چه ویژگی‌هایی داشته باشد؟",["آب آشامیدنی","روغن"]),
 ("conc-tests","fact_fa","برای کل سازه حداقل چند آزمایش مقاومت بتن لازم است؟",["شش تست"]),
 ("conc-wc","fact_fa","نسبت آب به سیمان بتن تحت هیچ شرایطی نباید از چه مقداری بیشتر شود؟",["آب به سیمان","0 5"]),
 ("cem-store","fact_fa","سیمان نگهداری‌شده بیش از چند روز در محل باید قبل از استفاده آزمایش شود؟",["28 روز","سیمان"]),
 ("conc-cure","fact_fa","عمل‌آوری بتن با پوشش مرطوب حداقل چند روز باید ادامه داشته باشد؟",["7 روز","20 میلی"]),
 ("cold-def","fact_fa","هوای سرد در ریختن بتن چه زمانی تعریف می‌شود؟",["5 درجه","سه روز"]),
 ("steel-gap","fact_fa","حداکثر فاصله نصب در انتهای اعضای اتصال فولاد به فولاد چقدر است؟",["2 میلی متر","فاصله نصب"]),
 ("fc-min","fact_fa","حداقل مقاومت f'c برای بتن طراحی‌شده طبق آیین‌نامه چقدر است؟",["17mpa"]),
 ("conc-250","fact_fa","بتن برای دمای سرویس تا چند درجه سانتیگراد باید با سنگدانه خاص ساخته شود؟",["250 درجه"]),
 ("mortar-90","fact_fa","مقاومت مکعب‌های ملات با آب غیرقابل شرب باید حداقل چند درصد نمونه شاهد باشد؟",["90 درصد","غیر قابل شرب"]),
 ("grout-95","fact_fa","سطح دوغاب پخته‌شده هنگام برداشتن صفحه پایه باید چند درصد سطح باربری را نشان دهد؟",["95 درصد","باربری"]),
 ("g2-thick","fact_fa","حداقل و حداکثر ضخامت دوغاب نوع G2 چقدر است؟",["2 5 سانتی","5 سانتی"]),
 ("g1-ratio","fact_fa","دوغاب G1 از چه نسبت ماسه به سیمان ساخته می‌شود؟",["دو قسمت ماسه"]),
 ("g1-cement","fact_fa","برای دوغاب G1 چه نوع سیمانی باید استفاده شود؟",["پرتلند نوع ii","c150"]),
 ("lime","fact_fa","مقدار آهک در لایه خاک آهک تقریباً چند کیلوگرم بر متر مکعب است؟",["150 کیلوگرم"]),
 ("fill-layer","fact_fa","ضخامت هر لایه در خاکریزی با خاک محلی چقدر باشد؟",["15 سانتی","لایه به لایه"]),
 ("stab-pub","fact_fa","تثبیت‌کننده‌های خاک باید مطابق کدام نشریه انجام شود؟",["نشریه شماره 268"]),
 ("proctor","fact_fa","تراکم خاکریز بر اساس کدام آزمایش پروکتور اصلاح‌شده انجام می‌شود؟",["d1557"]),
 ("pqp","fact_fa","طرح کیفیت پروژه (PQP) را پیمانکار ظرف چند روز از شروع قرارداد باید ارائه کند؟",["pqp","30 روز"]),
 ("qms-6m","fact_fa","QMS پیمانکار پس از بازنگری استاندارد ارجاع‌شده طی چند ماه باید اصلاح شود؟",["شش 6 ماه"]),
 ("var-25","fact_fa","شرکت چند درصد حق افزایش یا کاهش مبلغ کار را دارد؟",["بیست و پنج درصد"]),
 ("seatbelt","fact_fa","کمربند ایمنی خودروهای سبک چه نوعی باید باشد؟",["قرقره","3 نقطه"]),
 ("ems-17","fact_fa","خدمات آمبولانس چند ماه در جدول قیمت‌ها پیش‌بینی شده است؟",["آمبولانس","17"]),
 ("km-tacit","fact_fa","تفاوت دانش ضمنی و دانش صریح چیست؟",["دانش صریح","دانش ضمنی"]),
 ("km-20","fact_fa","کارمندان چند درصد از وقت خود را صرف جستجوی اطلاعات می‌کنند؟",["20 درصد"]),
 # --- exact identifiers / short keyword queries (lexical should shine)
 ("id-astm1107","id","الزامات ASTM C 1107 برای گروت غیرمنقبض",["c 1107"]),
 ("id-ips200","id","IPS-E-CE-200",["ips e ce 200"]),
 ("id-aci305","id","ACI 305R-10",["305r 10"]),
 ("id-c33","id","ASTM C33-18",["c33 18"]),
 ("id-pub120","id","نشریه شماره 120 آیین نامه ملی بتن ایران",["نشریه شماره 120"]),
 ("id-bs3148","id","آزمایش آب مطابق BS 3148",["bs 3148"]),
 ("id-spc0003","id","SO-FE-SOGN-CI-SPC-0003",["spc 0003"]),
 ("id-spc0005","id","مشخصات SO-FE-SOGN-CI-SPC-0005 چیست؟",["spc 0005"]),
 ("id-tender","id","SO-004-00082-03",["so 004 00082 03"]),
 ("id-c150","id","ASTM C150",["c150"]),
 # --- typos / informal wording
 ("typo-epoxy","typo","دوغاب اپکسی چطور تزریق میشه",["اپوکسی"]),
 ("typo-slump","typo","حداکثر اسلامپ بتون",["حداکثر اسلامپ"]),
 ("typo-curing","typo","عمل اوری بتن در هوای گرم",["عمل آوری"]),
 # --- conceptual / paraphrase (semantic should shine)
 ("c-grout-store","concept","گروت را در محل کارگاه چگونه باید انبار و محافظت کرد؟",["پناهگاه خشک"]),
 ("c-epoxy-form","concept","قالب‌هایی که برای تزریق اپوکسی استفاده می‌شوند چطور آماده شوند؟",["اپوکسی","آب بند"]),
 ("c-mockup","concept","پیش از اجرای واقعی گروت چه آزمایشی در محل باید انجام شود؟",["ماکت"]),
 ("c-slump-low","concept","اگر اسلامپ بتون هنگام ورود به کارگاه کمتر از حد مجاز باشد چه باید کرد؟",["اسلامپ","آب اضافی"]),
 ("c-iso","concept","اگر پیمانکار گواهینامه ISO 9001 داشته باشد شرکت چه می‌کند؟",["iso 9001","قابل قبول"]),
 ("c-eff","concept","تاریخ موثر قرارداد چه زمانی است؟",["تاریخ موثر","اعطای نامه"]),
 # --- English questions over Persian text (cross-lingual) and English over English
 ("x-g1wc","cross_en","What is the maximum water to cement ratio for G1 grout?",["g1","0 4"]),
 ("x-store","cross_en","How long can non-shrink grout be stored on site?",["10 ماه"]),
 ("x-temp","cross_en","Maximum permitted temperature of concrete in degrees celsius",["60 درجه"]),
 ("x-fc","cross_en","minimum f'c compressive strength for concrete designed to the code",["17mpa"]),
 ("en-tec55","en","What minimum technical score must a bidder reach to go through commercial evaluation?",["fifty five percent"]),
 ("en-liq","en","How many points are given for a liquidity ratio above 1?",["liquidity ratio"]),
 ("x-tec55","cross_fa_en","حداقل امتیاز فنی لازم برای ورود به ارزیابی بازرگانی چقدر است؟",["fifty five percent"]),
 # --- no answer exists in the corpus (should return nothing)
 ("neg-1","negative","قیمت سیمان تیپ ۲ در بازار امروز چقدر است؟",None),
 ("neg-2","negative","برنامه غذایی کارگاه برای هفته آینده چیست؟",None),
 ("neg-3","negative","رمز عبور سیستم حسابداری چیست؟",None),
 ("neg-4","negative","How to bake a chocolate cake?",None),
 ("neg-5","negative","نتیجه بازی فوتبال پرسپولیس و استقلال دیروز",None),
]
