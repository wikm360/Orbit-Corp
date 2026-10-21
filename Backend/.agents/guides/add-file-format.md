# راهنما: پشتیبانی از فرمت فایل جدید

فرمت‌های فعلی: `.pdf .docx .pptx .xlsx .txt` + تصاویر `.png .jpg .jpeg .webp .bmp .tif .tiff`. جریان کامل: [../flows/document-ingestion.md](../flows/document-ingestion.md).

## قدم‌ها
1. `app/features/documents/ingestion/parser.py`:
   - پسوند را به `DOCUMENT_EXTENSIONS` (یا `IMAGE_EXTENSIONS`) اضافه کنید → `SUPPORTED_EXTENSIONS` خودکار به‌روز می‌شود و validation آپلود آن را می‌پذیرد.
   - تابع `_parse_<fmt>_pages(file_path) -> list[DocumentPage]` بنویسید و در `parse_document_pages` شاخه اضافه کنید. هر `DocumentPage` شماره‌ی ۱-پایه، `text`، `images` (برای OCR) و `metadata` (حداقل `{"page": n}`) دارد.
   - تصاویر را با فیلتر ابعاد `OCR_MIN_IMAGE_DIMENSION` جمع کنید (الگو: PDF/PPTX).
2. اگر به کتابخانه نیاز دارد: `requirements.txt` (نسخه‌ی pin) و در صورت نیاز بسته‌ی سیستمی در `Dockerfile`.
3. تست: `tests/features/documents/test_parser.py` (فایل نمونه کوچک در حافظه/tmp).
4. Content-type/پسوند `.doc/.xls/.ppt` قدیمی: تبدیل با LibreOffice یا کتابخانه‌ی جدا لازم است (فعلاً پشتیبانی نمی‌شود).
5. در پایان [../flows/document-ingestion.md](../flows/document-ingestion.md) و [../reference/api-endpoints.md](../reference/api-endpoints.md) (پیام خطای فرمت) را به‌روز کنید.

## نکات
- parse در worker و sync است؛ فایل بزرگ حافظه زیادی می‌گیرد (`mem_limit` worker ۲GB).
- هر متنی که برمی‌گردانید NUL نداشته باشد (pipeline حذف می‌کند ولی بهتر است خود parser هم رعایت کند).
- «صفحه» برای فرمت‌های بدون صفحه را به واحد منطقی (sheet، اسلاید) نگاشت کنید؛ ابزارهای `read_document_pages` از آن استفاده می‌کنند.
