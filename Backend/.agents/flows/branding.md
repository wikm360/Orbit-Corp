# هویت و برند سازمان (`app/features/branding/`)

هر سازمان یک deploy جدا دارد (دیتابیس جدا)، پس برند **یک ردیف** در جدول `org_branding` است (`id = 1` با CHECK؛ بدون tenant). migration `0029` ردیف را با هویت مشتری اول seed می‌کند تا نصب فعلی بدون تغییر بماند؛ نصب جدید همان را از پنل عوض می‌کند. ردیف نبودن (مثلاً در تست) = `service.DEFAULTS`.

## فیلدها
متن‌ها: `name`، `short_name`، `app_title` (عنوان تب)، `description`، `tagline`، `product_label` (برچسب لاتین سایدبار)، `login_headline`، `login_footer`. رنگ‌ها (hex ‌۷کاراکتری): `color_brand` (زمینه‌ی تیره)، `color_highlight` (دکمه/لینک؛ در Tailwind با نام `teal`)، `color_accent`. لوگو: `logo_data` (bytea، deferred) + `logo_content_type` + `logo_version` (cache-busting)، فقط در DB (در backup هست؛ بدون وابستگی به volume).

## API
- **عمومی (بدون توکن؛ صفحه‌ی ورود لازم دارد):** `GET /branding` (متن‌ها، `colors`، `palette`، `logo_url`)، `GET /branding/logo` (بایت‌ها؛ `Cache-Control: immutable` چون URL شامل `?v=<version>` است، `nosniff`).
- **فقط super_admin:** `PUT /admin/branding` (هر فیلد اختیاری؛ `null` = بدون تغییر)، `POST /admin/branding/logo` (multipart `file`)، `DELETE /admin/branding/logo`.
- اعتبارسنجی: متن خالی/بلندتر از سقف → 400 (فاصله‌ها فشرده می‌شوند)؛ رنگ باید `#rrggbb` باشد؛ `brand` و `highlight` باید با **متن سفید روی سایه‌ی ۶۰۰** کنتراست ≥ ۳ داشته باشند (رنگ‌های اولیه معاف‌اند). لوگو: **محتوای واقعی** تعیین‌کننده است (Pillow؛ نه header کلاینت): فقط PNG/JPEG/WebP، ≤ ۵۱۲KB، ≤ ۲۰۴۸px؛ SVG عمداً رد می‌شود (می‌تواند اسکریپت حمل کند).

## پالت (`palette.py`)
هر رنگ پایه سایه‌ی `500` است؛ ۵۰–۴۰۰ به سمت سفید و ۶۰۰–۹۰۰ به سمت مشکی مخلوط می‌شوند. تا وقتی رنگ پایه همان رنگ‌های اولیه است، پالت اولیه **عیناً** برمی‌گردد (ظاهر نصب قبلی تغییر نمی‌کند). `palette.ground` سطوح تیره (سایدبار، دکمه‌ی اصلی) است: رنگ اولیه‌ی ثابت، یا سایه‌های ۹۰۰/۸۰۰ رنگ اصلی. خروجی به شکل `"r g b"` است (برای `rgb(var(--x) / <alpha-value>)` در Tailwind).

## فرانت
- `src/shared/lib/branding.ts`: `getBranding()` سمت سرور برای هر درخواست (`connection()` + `fetch no-store`، timeout ۲٫۵ث، هرگز throw نمی‌کند و در خطا `FALLBACK_BRANDING` و رنگ‌های پیش‌فرض `globals.css`)؛ `brandingCss()` فقط سه‌تایی‌های عددی معتبر را به `:root[data-brand]{--brand-500:…}` تبدیل می‌کند.
- `app/layout.tsx` (async): `generateMetadata` (عنوان، توضیح، favicon از لوگو)، `<style>` رنگ‌ها قبل از اولین رندر (بدون فلش رنگ پیش‌فرض)، و `BrandingProvider` برای کلاینت‌ها؛ `useBranding()`، `BrandLogo` (لوگو یا حرف اول نام روی رنگ اصلی).
- `tailwind.config.ts`: `brand/accent/teal/ground` = `rgb(var(--…) / <alpha-value>)`؛ مقادیر پیش‌فرض در `globals.css`. رنگ‌های ثابت قبلی (سایدبار `#142b40`، دکمه `#163b48`، focus/selection) به `ground` و `teal-*` رفتند. ⚠️ سایه‌های `teal-200/800/900` قبلاً از پالت پیش‌فرض Tailwind می‌آمدند و حالا تولیدشده‌اند.
- آدرس سمت سرور: `INTERNAL_API_URL` (پیش‌فرض `http://localhost:8000/api/v1`؛ در `docker-compose.prod.yml` برابر `http://backend:8000/api/v1`)، چون `NEXT_PUBLIC_API_URL` در پروداکشن مسیر نسبی `/api/v1` است.
- پنل: `features/admin/components/BrandingPanel.tsx` (فقط super_admin؛ ذخیره → `router.refresh()`).

## خارج از دامنه (فعلاً)
محتوای ماژول گزارش حجم مخصوص مشتری اول است (لوگو/رنگ شرکت‌های هلدینگ در `volume-reports/lib/presentation.ts` و `public/volume-reports/logo_mehvar.png`، نام دیتابیس راهکاران در `RAHKARAN_DB_NAME`) و برند عمومی حساب نمی‌شود؛ روشن/خاموش بودن ماژول همچنان با `VOLUME_REPORT_ENABLED` (env) است. رنگ‌های hex داخل نمودارها و اسلایدها دست‌نخورده‌اند.
