"""Seed rows for the volume-report lexicon (appendix A of the design). Pure data, no DB import: the extraction layer
builds its default `Lexicon` from this and the Phase 1 migration/seed inserts the very same rows into `vr_lexicon`."""

# (token, kind, phrases). Phrases are written naturally; `Lexicon` normalizes them, so ZWNJ/ی/ک variants are irrelevant.
LEXICON_SEED: list[tuple[str, str, list[str]]] = [
    ("SUBBASE", "item_hint", ["زیراساس", "زیر اساس", "ساب بیس", "سابیس", "sub base", "subbase"]),
    ("BASE", "item_hint", ["اساس"]),
    ("SUBGRADE", "item_hint", ["سابگرید", "ساب گرید"]),
    ("PRIME", "item_hint", ["پریمکت", "پریم کت", "پریم کوت", "پریمکوت", "اندود نفوذی"]),
    ("TACK", "item_hint", ["تک کت", "تککت", "اندود سطحی", "اندود قیر"]),
    ("BINDER", "item_hint", ["بیندر", "بایندر", "قشر آستر"]),
    ("TOPKA", "item_hint", ["توپکا", "توپ کا", "قشر رویه", "آسفالت رویه"]),
    ("EXCAV", "item_hint", ["خاکبرداری", "خاک برداری", "حفاری خاک"]),
    ("FILL", "item_hint", ["خاکریزی", "خاک ریزی"]),
    ("BORROW", "item_hint", ["قرضه"]),
    ("CONCRETE", "item_hint", ["بتن ریزی", "بتنریزی", "بتن", "ماهیچه", "بتن مگر"]),
    ("REBAR", "item_hint", ["آرماتور بندی", "آرماتوربندی", "آرماتور", "میلگرد"]),
    ("FORM", "item_hint", ["قالب بندی", "قالببندی", "قالب"]),
    ("PILE", "item_hint", ["شمع"]),
    ("PIPE", "item_hint", ["لوله گذاری", "لوله‌گذاری", "لوله رانی", "لوله کشی", "کارگذاری لوله", "لوله گذار"]),
    ("PRECAST", "item_hint", ["پیش ساخته", "پیشساخته", "نیوجرسی"]),
    ("SUPPLY", "role", ["تهیه", "تامین", "خرید"]),
    ("EXEC", "role", ["اجرا", "اجرای", "پخش", "کوبیدن", "تراکم", "آب پاشی", "آبپاشی", "نصب", "ریختن"]),
    ("HAUL", "item_hint", ["بارگیری و حمل", "حمل و بارگیری", "بارگیری", "حمل"]),
    ("SURCHARGE", "hard_exclusion", ["اضافه بها", "اضافه بهای"]),
    ("DEMOLITION", "hard_exclusion", ["تخریب"]),
    ("TRENCH", "hard_exclusion", ["کانال کنی", "کانالکنی", "حفر کانال"]),
    ("POINTING", "hard_exclusion", ["بند کشی", "بندکشی"]),
    ("SITE_SETUP", "hard_exclusion", ["تجهیز کارگاه", "تجهیزکارگاه"]),
]

# hard_exclusion token -> `exclude_reason` enum value of `vr_classifications`/`vr_decisions`
HARD_EXCLUSION_REASONS: dict[str, str] = {
    "SURCHARGE": "surcharge",
    "DEMOLITION": "demolition",
    "TRENCH": "trenching",
    "POINTING": "pointing",
    "SITE_SETUP": "site_setup",
}


# (key, title_fa, dimension, output_unit, decimals, mining_only, description_fa)
ITEMS_SEED: list[tuple[str, str, str, str, int, bool, str]] = [
    ("excavation", "خاکبرداری", "volume", "m3", 2, False, "خاکبرداری و حفاری خاک (پی‌کنی و دکاپاژ پیش‌فرض اینجا پیشنهاد می‌شوند ولی تأییدنشده‌اند)."),
    ("fill", "خاکریزی", "volume", "m3", 2, False, "خاکریزی و تراکم. «خاکبرداری از قرضه … پخش و خاکریزی/تراکم» یعنی خاکریزی."),
    ("subbase", "زیراساس", "volume", "m3", 2, False, "لایه‌ی زیراساس. با «اساس» فرق دارد."),
    ("base", "اساس", "volume", "m3", 2, False, "لایه‌ی اساس. «زیراساس» جزو این آیتم نیست."),
    ("asphalt_binder", "آسفالت بیندر", "mass", "t", 2, False, "قشر بیندر (آستر)."),
    ("asphalt_topka", "آسفالت توپکا", "mass", "t", 2, False, "قشر توپکا (رویه)."),
    ("asphalt_total", "آسفالت (جمع)", "mass", "t", 2, False, "جمع بیندر و توپکا؛ هرگز مستقیم طبقه‌بندی نمی‌شود."),
    ("concrete", "بتن", "volume", "m3", 2, False, "همه‌ی انواع بتن‌ریزی (پی، دیوار، دال، شناژ، ماهیچه، مگر، شمع) یک عدد؛ نوع مهم نیست."),
    ("rebar", "آرماتور", "mass", "t", 3, False, "آرماتوربندی/میلگرد."),
    ("formwork", "قالب", "area", "m2", 2, False, "قالب‌بندی. «اضافه بها» حذف می‌شود."),
    ("prime_coat", "پریمکت", "mass", "kg", 1, False, "پریمکت/اندود نفوذی. واحد خروجی منتظر تأیید کارفرما."),
    ("tack_coat", "تک‌کت", "mass", "kg", 1, False, "تک‌کت/اندود سطحی. واحد خروجی منتظر تأیید کارفرما."),
    ("precast", "بتن پیش‌ساخته", "volume", "m3", 2, False, "قطعات پیش‌ساخته (جدول، نیوجرسی). اگر واحد متر طول است مقطع لازم است."),
    ("pile_drilling", "حفاری شمع", "length", "m", 2, False, "حفاری شمع (طول). «بتن‌ریزی شمع» جزو بتن است."),
    ("pipe_laying", "لوله‌گذاری", "length", "m", 2, False,
     "لوله‌گذاری و لوله‌رانی با واحد متر طول (مثل «لوله گذاری با لوله های جوشی ۱۶۰۰»، «لوله رانی در هر نوع زمین»، «تهیه و کارگذاری لوله»). "
     "غیرمثال: «ریسه کردن لوله» (واحد عدد)، عایق‌بندی و رنگ لوله (مترمربع)، حفاری/کانال‌کنی، حوضچه و اتصالات، ردیف مقطوع یا سری؛ "
     "فقط-تهیه‌ی لوله شمرده نمی‌شود."),
    ("mining_load", "بارگیری ماده معدنی و باطله", "volume", "m3", 2, True, "فقط کارگاه‌های نوع معدن: همه‌ی ردیف‌های «حمل و بارگیری» حجمی."),
]
ROLLUPS_SEED: dict[str, list[str]] = {"asphalt_total": ["asphalt_binder", "asphalt_topka"]}

# (key, item_key | None, value, unit, note). Asphalt density agreed with the client as 2.35 t/m3 (editable).
CONVERSIONS_SEED: list[tuple[str, str | None, str, str, str]] = [
    ("density_t_per_m3", "asphalt_binder", "2.35", "t/m3", "چگالی آسفالت"),
    ("density_t_per_m3", "asphalt_topka", "2.35", "t/m3", "چگالی آسفالت"),
]
