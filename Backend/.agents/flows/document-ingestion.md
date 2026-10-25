# جریان: آپلود و ایندکس اسناد (ingestion)

فایل‌ها: `features/documents/{models,schemas,router,service}.py`، `features/documents/ingestion/{parser,ocr,reconstructor,chunker,embedder,pipeline}.py`، `workers/ingestion_worker.py`، `features/retrieval/*`، `providers/embedding_provider.py`.

## خلاصه
```
POST آپلود ─► اعتبارسنجی (پسوند/حجم/خالی/نام) ─► SHA-256
     ├─ فایل هم‌محتوای READY با همان embedding model هست؟ ─► chunkها کپی ─► سند READY بلافاصله
     └─ وگرنه: ذخیره روی دیسک (یا استفاده از فایل موجود) ─► Document(PROCESSING) ─► job در صف RQ
worker: Parse ─► OCR ─► Reconstruct ─► Chunk ─► Embed ─► Persist ─► READY (یا FAILED + error_message)
```

## endpointهای آپلود
| endpoint | دسترسی | scope |
|---|---|---|
| `POST /projects/{id}/documents` (یک فایل `file`) | manager | project |
| `POST /projects/{id}/documents/batch` (چند `files`) | manager | project |
| `POST /chat/conversations/{id}/documents` و `/batch` | هر کسی که به گفتگو دسترسی دارد | conversation |
| `GET /projects/{id}/documents`، `GET /chat/conversations/{id}/documents` | دسترسی خواندن | لیست + `status` |
| `POST /projects/{id}/documents/{doc}/retry` | manager | فقط برای `FAILED` |
| `DELETE /projects/{id}/documents/{doc}` | manager | |
پاسخ تک‌فایل: `DocumentUploadResponse{document, message}`. دسته‌ای: `BatchUploadResponse{items:[{filename,status:accepted|rejected,document,error}], accepted, rejected}`؛ فایل ردشده بقیه را رد نمی‌کند.
(حذف سند گفتگو از طریق API وجود ندارد؛ با حذف گفتگو cascade می‌شود.)

## اعتبارسنجی
- پسوند باید در `SUPPORTED_EXTENSIONS` باشد: **`.pdf .docx .pptx .xlsx .txt` + تصاویر `.png .jpg .jpeg .webp .bmp .tif .tiff`**. در غیر این‌صورت 400.
- حجم ≤ `MAX_UPLOAD_SIZE_MB` (۵۰). در endpoint تک‌فایل کل فایل در حافظه خوانده می‌شود (`await file.read()`)؛ در batch فایل‌ها یکی‌یکی.
- batch: حداکثر `MAX_BATCH_UPLOAD_FILES` (۲۰) فایل در هر درخواست، وگرنه 400؛ فایل خالی / نام >۵۰۰ نویسه / حجم زیاد به‌صورت `rejected` گزارش می‌شود.
- Caddy `request_body max_size 60MB` روی `/api/*`.
- `.doc/.xls/.ppt` قدیمی پشتیبانی نمی‌شود.

## dedup بر اساس محتوا (`documents/service._create_document`)
1. `content_hash = sha256(bytes)`.
2. `_find_reusable_document`: جدیدترین سند **READY** با همان hash (از هر scope/پروژه).
3. فایل: اگر reusable هست `file_path` همان استفاده می‌شود (فایل دوباره نوشته نمی‌شود)؛ وگرنه `UPLOAD_DIR/<uuid4><suffix>`.
4. ردیف `Document(PROCESSING)` ساخته و commit می‌شود.
5. اگر reusable هست **و** `reusable.embedding_model == settings.embedding_model`: chunkها (`content, chunk_index, embedding, chunk_metadata`) کپی، `embedding_model` ست، `status=READY` — بدون صف.
6. وگرنه `_enqueue_ingestion` → RQ `Queue(INGESTION_QUEUE_NAME)` تابع `app.features.documents.ingestion.pipeline.run_ingestion_pipeline_sync(document.id, document.file_path)` با `job_timeout=600`.
نتیجه: دو سند می‌توانند یک `file_path` (و فایل‌های `.reconstructed.*`) مشترک داشته باشند؛ حذف فیزیکی فقط وقتی انجام می‌شود که هیچ `Document` دیگری به همان مسیر اشاره نکند. هر سند همچنان scope و chunkهای خودش را دارد، پس dedup دسترسی را نشت نمی‌دهد.
(سند هم‌محتوایی که هنوز PROCESSING است reuse نمی‌شود.)

## پایپ‌لاین worker (`ingestion/pipeline.py`)
`DEFAULT_PIPELINE = [ParseStep, OCRStep, PageKindStep, ReconstructStep, ChunkStep, EmbedStep, PersistStep]` — هر step یک `IngestionStep.run(IngestionContext)`؛ context شامل `document_id, file_path, db, filename, pages, raw_text, page_chunks, chunks, embeddings` است.

1. **ParseStep** — `parse_document_pages(file_path)` → `list[DocumentPage(page_number, text, images, metadata, needs_ocr)]`؛ NUL (`\x00`) از متن حذف می‌شود.
   - **کنترل کیفیت لایه‌ی متنی PDF** (`ingestion/text_layer.py`، روی هر صفحه): `assess_text_layer` سه حالت می‌دهد: `ok`؛ `visual_persian` (متن فارسی با presentation forms عربی `U+FB50–FDFF / U+FE70–FEFF` در ترتیب بصری: حروف هر کلمه برعکس و فاصله‌ی اضافه وسط کلمه — معمولاً فایل‌های «Machine Translated by Google» یا print-to-PDF؛ **روی داده‌ی واقعی اندازه‌گیری شد: هم‌پوشانی کلمه با متن درست = ۰٪**)؛ `garbled` (لایه‌ی OCR قدیمی اسکن که فقط نویز نمادی است؛ معیار: `wordlike<0.15` و `noise≥0.10`). صفحه‌ی غیر `ok` علامت `needs_ocr` و `metadata.text_layer` می‌گیرد؛ برای `visual_persian` فوراً `fix_visual_persian` اعمال می‌شود (چسباندن chunkهای شکسته با قاعده‌ی joining form، برعکس‌کردن حروف هر کلمه، NFKC، اصلاح ترتیب run لاتین/عدد). این اصلاح فقط fallback است (~۷۰٪ کلمات درست برمی‌گردد؛ OCR ~۹۳–۹۵٪).
   پارس PDF بلند (≥۸ صفحه) بین `PDF_PARSE_WORKERS`=۴ process (fork، `ProcessPoolExecutor`) به بازه‌های صفحه تقسیم می‌شود چون decode عکس‌های اسکن توسط pypdf CPU-bound است (اندازه‌گیری واقعی: ۴۲ صفحه ≈ ۵۵ ثانیه تک‌process؛ ۴۲٫۵ ثانیه‌اش decode تصویر). هر خطا در pool ← fallback به تک‌process. لاگ INFO `PDF parse …` زمان هر فاز را می‌دهد؛ `ParseStep/OCRStep/…` هم زمان خود را لاگ می‌کنند.
   **صفحه‌ی اسکن**: صفحه‌ای که متن ندارد و یک تصویر در اندازه‌ی صفحه (ضلع کوتاه ≥ ۴۰۰px، از دیکشنری PDF خوانده می‌شود، decode نمی‌شود) دارد `needs_ocr=True` و `metadata.text_layer="scan"` می‌گیرد، `images=[]` می‌ماند و `OCRStep` کل صفحه را رندر و یک‌بار OCR می‌کند. دلیل: اسکنرها/MRC صفحه را به لایه‌ی پس‌زمینه + پیش‌زمینه (+ماسک) می‌شکنند؛ هر لایه به‌تنهایی ناخوانا یا غلط خوانده می‌شود (اندازه‌گیری روی `eval/10.pdf`: یک لایه متن **پروژه‌ای دیگر** برگرداند) و decode آن‌ها کندترین بخش parse بود (~۱٫۲ث/صفحه) و فراخوانی vision را دو برابر می‌کرد. فقط وقتی فعال است که `OCR_ENABLED` و `OCR_REPLACE_BAD_TEXT_LAYER` هر دو true باشند؛ وگرنه رفتار قدیمی (تک‌تک تصاویر). تصویرهای تو در توی form XObject بررسی نمی‌شوند (← مسیر قدیمی). به همین دلیل صفحه‌ی `needs_ocr` از هر نوع (`garbled`/`visual_persian`/`scan`) تصویرهایش را هم decode نمی‌کند (OCRStep آن‌ها را هرگز جدا نمی‌خواند) — اندازه‌گیری: `eval/10.pdf` ۴۲ صفحه از ~۵۵ثانیه به ~۱٫۲ثانیه رسید.
   | فرمت | «صفحه» |
   |---|---|
   | PDF (pypdf) | هر صفحه؛ متن + تصاویر embed شده (فیلتر: حداقل `OCR_MIN_IMAGE_DIMENSION`=۶۰ در هر بعد). اگر صفحه نه متن دارد نه تصویر (اسکن) → رندر با `pdftoppm -r `PDF_RENDER_DPI` (۲۰۰)` (timeout ۲۰ثانیه) و یک تصویر برای OCR |
   | DOCX | یک صفحه‌ی واحد: پاراگراف‌ها + جدول‌ها (`a | b | c`) + تصاویر |
   | PPTX | هر اسلاید: متن frameها + جدول + تصاویر |
   | XLSX | هر sheet یک صفحه (`=== Sheet: name ===` + ردیف‌ها با `|`)، `data_only=True`، `metadata.sheet_name` |
   | TXT | یک صفحه؛ تشخیص UTF-16/UTF-8-BOM/heuristic |
   | تصویر | یک صفحه با یک تصویر خام برای OCR |
2. **OCRStep** — اگر `OCR_ENABLED`. قبل از هر فراخوانی پولی دو لایه‌ی cache (`_OcrReader`): (۱) **داخل سند**: یک تصویر با بایت‌های یکسان (لوگو/مهر/header تکراری، صفحه‌ی مشابه) فقط یک‌بار خوانده و نتیجه بین همه‌ی صفحات به‌اشتراک گذاشته می‌شود (متن همچنان به هر صفحه اضافه می‌شود)؛ تصویر تکراری از سقف `OCR_MAX_IMAGES_PER_DOC` کم نمی‌کند. (۲) **بین سندها**: جدول `ocr_cache` با کلید `sha256(تصویر)` + hash مدل/prompt؛ برای صفحه‌ی رندرشده‌ی `needs_ocr` هم همین (رندر قطعی است، پس همان صفحه‌ی PDF در سند دیگر hit می‌شود). فقط نتیجه‌ی غیرخالی cache می‌شود (شکست/تصویر خالی دفعه‌ی بعد دوباره امتحان می‌شود)؛ خطای خود cache فقط warning است و تصویر مستقیم خوانده می‌شود. تنها فراخوانی API با `OCR_CONCURRENCY` محدود می‌شود. همه‌ی فراخوانی‌های OCR یک سند از یک `AsyncOpenAI` مشترک (`ocr_client_session`، ContextVar) با connect-timeout ۳۰ثانیه می‌روند؛ پیش‌فرض SDK (۵ثانیه) زیر بار با ده‌ها اتصال TLS هم‌زمان `Request timed out` + retry می‌داد و بار را چند برابر می‌کرد. لاگ پایان: «N vision calls, M cache hits, K shared within the document». dedup کل‌فایل (بالا) و این cache مستقل‌اند: این یکی وقتی کار می‌کند که فایل بایت‌به‌بایت یکی نیست ولی صفحه/تصویرش هست. دو کار، با هم‌زمانی `OCR_CONCURRENCY`=۱۲ صفحه (تصاویر یک صفحه متوالی می‌مانند تا ترتیب ثابت باشد):
   - **صفحه‌ی `needs_ocr`** (و `OCR_REPLACE_BAD_TEXT_LAYER`، سقف `OCR_MAX_REPLACED_PAGES`=۳۰۰ صفحه در سند): با `pdftoppm -r `PDF_RENDER_DPI` (۳۰۰)` رندر و OCR می‌شود و متن OCR **جایگزین** لایه‌ی متنی می‌شود (`metadata.text_layer="ocr"`)؛ اگر OCR شکست خورد یا <۲۰ نویسه داد، متن اصلاح‌شده‌ی مرحله‌ی parse می‌ماند. تصاویر چنین صفحه‌ای جدا OCR نمی‌شوند.
   - **سایر صفحات**: برای هر تصویر (تا سقف `OCR_MAX_IMAGES_PER_DOC`=۵۰ در کل سند) `extract_text_from_image`؛ نتیجه به `page.text` اضافه می‌شود با برچسب `[محتوای استخراج‌شده از تصویر / جدول]:`.
   خطای OCR صرفاً warning است و سند ادامه می‌دهد. `extract_text_from_image` تا ۳ تلاش برای خطاهای عادی دارد (backoff ۲ و ۴ ثانیه). پاسخ `finish_reason=content_filter` با متن خالی (فیلتر ایمنی Gemini؛ روی یک نامه‌ی اداری با مهر در حدود نیمی از درخواست‌های یکسان خالی برمی‌گشت، تصادفی) بودجه‌ی جدا دارد: `OCR_CONTENT_FILTER_RETRIES` (پیش‌فرض ۲) بار تکرار می‌شود، با مکث ۱ ثانیه و **هر بار با درخواستی کمی متفاوت**: تصویر دوباره JPEG می‌شود با حاشیه‌ی سفید ۱۰ پیکسلی (و از retry دوم ۲٪ کوچک‌تر + حاشیه‌ی ۲۰ پیکسلی) و یک جمله‌ی خنثی به آخر prompt اضافه می‌شود؛ هرگز دو بار همان بایت‌ها فرستاده نمی‌شوند (فرض: رد شدن ممکن است به ورودی وابسته باشد؛ این فرض را **نتوانستم اثبات کنم**: نرخ فیلتر روی همان نامه بین اجراها ۱ تا ۵ از ۸ بود و در سنجش آخر بایت‌های یکسان ۱ از ۱۰ و نسخه‌ی تغییریافته ۰ از ۱۰ — اختلاف معنادار نیست). با ۲ retry و نرخ ۵۰٪، حدود ۱۲٪ شکست می‌ماند؛ برای نرخ بالا آن را زیاد کنید. بعد از تمام‌شدن retryها warning و «بدون متن».
   - **معماری دو‌مرحله‌ای OCR (Two-Stage Hybrid OCR)**:
     ۱. مرحله ۱ (Layout Analysis): با مدل `mistral-ocr-latest` (در صورت فعال بودن `OCR_TWO_STAGE_ENABLED` و وجود `MISTRAL_API_KEY`) موقعیت جداول (`type="table"`) شناسایی و بلوک‌های متنی خارج از جدول (سربرگ، قرارداد، تاریخ، زون، پاورقی و امضاها) استخراج می‌شوند (`DocumentLayoutResult`).
     ۲. مرحله ۲ (High-Res Crop): محدوده جدول از تصویر ۳۰۰ DPI با احتساب مقیاس و Padding بریده می‌شود.
     ۳. مرحله ۳ (Vision Extraction & Stitching): تصویر کراپ‌شده با `SYSTEM_TABLE_OCR_PROMPT` به مدل ویژن ارسال می‌شود تا ارقام اعشاری و ساختار Markdown بدون خطا استخراج گردند. سپس متون سربرگ و پاورقی/امضاها (با کنترل عدم تکرار) در بالا و پایین جدول تلفیق می‌شوند تا زمینه و شناسنامه سند در RAG حفظ شود.
     در صورت بروز هرگونه خطای شبکه، تایم‌اوت، یا نبود جدول، سیستم به صورت خودکار به استخراج کل صفحه با `SYSTEM_OCR_PROMPT` برمی‌گردد (Fallback).
   - `extract_text_from_image`: اگر `LLM_API_KEY` خالی باشد یا تصویر <۱۰۰ بایت → رشته‌ی خالی. تصویر ابتدا **پیش‌پردازش** می‌شود (پایین) و بعد با prompt فارسی «OCR + جدول→Markdown + توضیح نمودار» به مدل `LLM_VISION_MODEL or LLM_MODEL` فرستاده می‌شود (`detail:"high"`, `max_tokens=OCR_MAX_TOKENS`=۶۰۰۰). خروجی `---`/`N/A`/`none`/`خالی` = تهی.
   - **پیش‌پردازش تصویر** (`ocr.prepare_image_for_ocr`، توابع در `ingestion/image_preprocess.py` و `ingestion/image_orientation.py`)؛ ترتیب: decode + EXIF + حذف alpha ← **صفحه‌ی خالی** (اگر `OCR_SKIP_BLANK_IMAGES`، `is_blank`: کمتر از ۰٫۲٪ پیکسل با اختلاف >۳۵ سطح از زمینه؛ فراخوانی vision انجام نمی‌شود و نتیجه خالی است؛ صفحه‌های واقعی ≥۳٫۶٪ و خالی‌ها ۰٪ اندازه‌گیری شدند) ← **راست‌کردن جهت** (اگر `OCR_AUTO_ORIENT` و ضلع کوتاه ≥ `OCR_ORIENT_MIN_DIMENSION`=۶۰۰) ← deskew و crop حاشیه (فقط اگر `OCR_DESKEW` / `OCR_CROP_MARGINS`؛ پیش‌فرض خاموش) ← کاهش اندازه (`OCR_MAX_IMAGE_DIMENSION`) + JPEG. هر خطای غیرمنتظره در پیش‌پردازش فقط warning است و تصویر ساده‌ی بهینه‌شده فرستاده می‌شود.
   - **تشخیص جهت** (`OCR_AUTO_ORIENT`، روش با `OCR_ORIENT_METHOD`؛ `image_orientation.choose_rotation`). متادیتا از قبل اعمال شده است و تصمیم‌گیر نیست: `exif_transpose` (در `_to_rgb` و `parser`) و `/Rotate` صفحه‌ی PDF (برای تصویرهای embed شده در `parser`؛ صفحه‌های رندرشده با `pdftoppm` را خودش اعمال می‌کند). این‌ها فقط وقتی اثر دارند که فایل چیزی گفته باشد؛ اسکن با پیکسل‌های چرخیده و بدون برچسب (یا با برچسب غلط) را فقط مرحله‌ی زیر می‌گیرد، همیشه روی تصویری که متادیتا رویش اعمال شده.
     - `osd`: Tesseract OSD (`tesseract stdin stdout --psm 0 -l osd`، تصویر خاکستری؛ ضلع بلند <۲۴۰۰px بزرگ می‌شود چون OSD ~۳۰۰dpi می‌خواهد، >۳۲۰۰px کوچک می‌شود). خروجی `Rotate` (درجه‌ی ساعتگرد) و `Orientation confidence`. محلی، ~۰٫۶ثانیه CPU، بدون API. پاسخ با اطمینان <`OCR_ORIENT_OSD_MIN_CONFIDENCE`=۲ یا بدون پاسخ = «نامطمئن» ← چرخش نده. حداکثر `OCR_OSD_CONCURRENCY` پردازش هم‌زمان (semaphore در سطح process، چون هر job event loop خودش را دارد؛ `OMP_THREAD_LIMIT=1`). نبودن `tesseract` = warning و «نامطمئن».
     - `model`: probe مدل vision با تصویر ۷۶۸px (≈۱٫۱k توکن ورودی): «متن راست‌ایستاده است؟ اگر نه چند درجه ساعتگرد؟». مدل (gemini-flash-lite) همیشه درست می‌گفت صفحه **چرخیده هست یا نه** ولی **جهت** را گاهی غلط (۹۰ به‌جای ۲۷۰)؛ پس جواب فقط راهنماست: اگر ≠۰ بود **اول فقط خود حدس تأیید می‌شود** (یک فراخوانی دیگر روی صفحه‌ی چرخانده‌شده)؛ فقط اگر تأیید نشد دو چرخش دیگر هم‌زمان امتحان می‌شوند و چرخشی که پاسخ «۰» بگیرد اعمال می‌شود. صفحه‌ی راست = ۱ فراخوانی، چرخیده با حدس درست = ۲، با حدس غلط = ۴ (دقت همان تأیید هر سه چرخش بود؛ روی صفحه‌ی ۷۵ ۴ فراخوانی ← ۲ شد و تصمیم جهت ۲۳٫۸ ← ۱۱٫۸ ثانیه).
     - `hybrid` (پیش‌فرض): اول OSD. اگر مطمئن (≥`OCR_ORIENT_OSD_UPRIGHT_CONFIDENCE`=۶) و «۰» بود ← همان، بدون فراخوانی API؛ «۰» با اطمینان کمتر ← مدل دوباره چک می‌کند (نقشه‌ی خوابیده با اطمینان ۲٫۶ «راست» گفته شد). اگر مطمئن و «بچرخان X» بود ← **یک** probe مدل روی صفحه‌ی چرخانده‌شده تأیید می‌کند (خطای نامتقارن OSD: «چرخیده» را «راست» گفتن وضع را بدتر نمی‌کند ولی صفحه‌ی سالم را «چرخیده» دانستن آن را خراب می‌کند)؛ اگر مدل موافق نبود یا OSD نامطمئن/ناموجود بود ← روال کامل `model`. خطا در هر مرحله = چرخش نده.
     - **لاگ**: برای هر تصویر بررسی‌شده یک خط INFO (در `dc logs worker`، فیلتر: `grep 'OCR orientation'`) مسیر تصمیم را می‌گوید، مثلاً `OCR orientation [hybrid] 1240x1949: osd: 90 (confidence 6.3) -> model confirmed => rotate 90 (2.1s)`؛ `osd: 0 (confidence 11.4) -> accepted: no model call => keep as is`؛ `osd: 90 (confidence 1.0, below 2 = unsure) -> falling back to the model -> model: says rotated, hint 270; checked 270->180,90->upright,180->90 => rotate 90`؛ `osd: 180 (confidence 4.6) -> model disagreed (said 180 after the rotation) -> model: upright => keep as is`. اگر tesseract نصب نباشد: `osd: no answer (too little text or tesseract missing)` (و یک بار warning).
     - اندازه‌گیری (۲۲ صفحه‌ی راست × ۴ چرخش = ۸۸ حالت): `model` ۸۸/۸۸ با ۲۸۶ probe؛ `osd` ۷۹/۸۸ با ۱ صفحه‌ی راستِ خراب‌شده؛ **`hybrid` ۸۶/۸۸، هیچ صفحه‌ی راستی خراب نشد، با ۸۵ probe (≈۷۰٪ کمتر)**؛ هر دو خطای hybrid «چرخش ازدست‌رفته» بود. جزئیات: [../ops/ocr-preprocessing-evaluation.md](../ops/ocr-preprocessing-evaluation.md). دلیل اصلی: متن فارسی متراکم که ۹۰/۱۸۰/۲۷۰ چرخیده بود با مدل بدون اصلاح ۲۰–۸۰٪ مقادیر کلیدی را از دست داد؛ در PDF صورت‌وضعیت نمونه ۶ از ۸ صفحه‌ی اسکن واقعاً چرخیده بودند.
   - **چرخش ذخیره می‌شود و دوباره محاسبه نمی‌شود**: `prepare_image_for_ocr(..., report=)` چرخش پیداشده را گزارش می‌دهد؛ `OCRStep` آن را در `page.metadata["rotation"]` (۰/۹۰/۱۸۰/۲۷۰ ساعتگرد) می‌گذارد، فقط برای صفحه‌ای که تصویر OCR‌شده **همان صفحه** است (صفحه‌ی اسکن رندرشده و فایل تصویری آپلودی؛ تصویر embed شده در صفحه‌ی PDF چیزی درباره‌ی چرخش صفحه نمی‌گوید). از آنجا در metadata chunkها و `.reconstructed.json` می‌آید. ستون `ocr_cache.rotation` هم آن را نگه می‌دارد، چون cache hit فراخوانی OCR را رد می‌کند و چرخش را از دست می‌داد. `view_document_page` آن را از `.reconstructed.json` می‌خواند و `prepare_image_for_ocr(image, rotation=…)` تشخیص را رد می‌کند (`۰` هم جواب معتبر است). اسناد قبلی که چرخش ندارند مثل قبل تشخیص می‌دهند. اندازه‌گیری روی صفحه‌ی ۷۵: سؤال از نقشه ۵۷٫۵ ← ۱۵٫۵ ثانیه، ingestion ۴۶ ← ۲۸ ثانیه، و در turn چت هیچ لاگ تشخیص جهت نیامد.
   - کلید cache (`ocr_cache`) شامل `preprocess_signature()` (نسخه‌ی پیش‌پردازش + پرچم‌های orient/deskew/crop + `OCR_ORIENT_METHOD`) هم هست؛ تغییر پیش‌پردازش نتیجه‌ی قدیمی را برنمی‌گرداند. با تغییر کدِ پیش‌پردازش که متن را عوض می‌کند `PREPROCESS_VERSION` را زیاد کنید.
2b. **PageKindStep** (`ingestion/page_kind.py`، با `OCR_MARK_DRAWING_PAGES`) — صفحه‌ای که **نقشه/نمودار** است (OCR فقط نوشته و عدد پراکنده درمی‌آورد و معلوم نیست هر عدد چه چیزی را اندازه می‌گیرد) علامت `metadata.page_kind="drawing"` می‌گیرد و بالای متنش `DRAWING_NOTE` می‌آید که به agent می‌گوید عدد را حدس نزند و `view_document_page` را بزند. معیار (هر کدام): هر دو برچسب `PL=` و `GL=`؛ حداقل ۳ سطر برچسب نما (پلان/نما/مقطع/جزئیات/C.L)؛ یا صفحه‌ی خرده‌متن (≥۱۵ سطر غیرجدولی که ≥۶۰٪ آن‌ها فقط عدد یا ≤۲ کلمه‌اند). روی ۱۲ صفحه‌ی واقعی (۴ نقشه/نمودار، ۸ جدول/متن) هر ۴ نقشه پیدا شد و هیچ صفحه‌ی دیگر نه (معیار روی همین نمونه تنظیم شد؛ نمونه کوچک است). اسناد قبلاً ingest‌شده این علامت را ندارند تا دوباره پردازش شوند؛ ابزار به‌هرحال با توضیح و system prompt قابل استفاده است.
3. **ReconstructStep** — `save_reconstructed_document` دو فایل کنار فایل اصلی می‌نویسد: `<file_path>.reconstructed.txt` (خوانا، با `--- [صفحه N] ---`) و `<file_path>.reconstructed.json` (`{filename,total_pages,pages:[{page,text,has_images,metadata}]}`). این‌ها منبع سریع ابزارهای خواندن سند هستند. خطای نوشتن فقط warning.
4. **ChunkStep** — `chunk_document_pages`: برای هر صفحه‌ی غیرخالی، `chunk_text` با پنجره‌ی `CHUNK_SIZE_TOKENS`=۵۰۰ و overlap `CHUNK_OVERLAP_TOKENS`=۵۰ (tiktoken `cl100k_base`؛ بدون tiktoken ← تخمین ۰٫۷۵ کلمه/توکن). metadata هر chunk: `page, total_pages, chunk_in_page, total_chunks_in_page` + metadata صفحه. اگر هیچ صفحه‌ای نبود از `chunk_text(raw_text)` با `page=1` استفاده می‌شود.
5. **EmbedStep** — `embed_chunks` دسته‌های ۶۴تایی را هم‌زمان (حداکثر `EMBEDDING_CONCURRENCY`=۴ دسته، با `asyncio.gather` + semaphore؛ ترتیب خروجی حفظ می‌شود) به `EmbeddingProvider.embed` می‌فرستد (retry داخل provider). همه‌ی دسته‌های یک سند از یک `httpx.AsyncClient` مشترک (connection pool/keep-alive) استفاده می‌کنند: `BGEM3EmbeddingProvider.session()` آن را در یک `ContextVar` می‌گذارد؛ خارج از `session()` هر `embed()` مثل قبل client موقت می‌سازد. provider singleton است ولی هر job event loop خودش را دارد، به همین دلیل client روی نمونه نگه داشته نمی‌شود.
6. **PersistStep** — برای هر chunk یک `DocumentChunk(chunk_index=ترتیب سراسری)` و commit یکجا. اگر chunk یا embedding نیست (هیچ متنی استخراج نشده: فایل خالی، اسکن ناخوانا، OCR خاموش/ناموفق) `ValueError` می‌دهد ← سند `FAILED` با `error_message` می‌شود، نه READY.
- پایان موفق: `status=READY`, `embedding_model=settings.embedding_model` ← `_notify_conversation`.
- خطا: rollback، `status=FAILED`, `error_message=str(exc)[:2000]`، اعلان، و `raise` (job در RQ failed می‌شود).

## اعلان وضعیت
فقط برای اسناد **گفتگو**: `publish_event(conversation_id, {event:"document_status", document_id, status, filename})` روی کانال Redis `conversation:<id>`. برای اسناد پروژه هیچ event‌ای نیست (کلاینت باید poll کند: `GET …/documents`).

## retry و حذف
- `retry_failed_document`: فقط برای FAILED؛ chunkهای احتمالی پاک، وضعیت→PROCESSING، `error_message=None`، دوباره enqueue.
- `delete_document`: ردیف و (cascade) chunkها حذف؛ فایل و `.reconstructed.*` فقط اگر هیچ سند دیگری به همان `file_path` اشاره نکند.
- ⚠️ سند PROCESSING که worker کشته شود (OOM/timeout ۶۰۰ثانیه) خودکار FAILED نمی‌شود؛ مسیر بازیابی خودکار وجود ندارد (نیاز به تأیید رفتار RQ failed registry و ابزار دستی).

## worker
`workers/ingestion_worker.py`: `rq.Worker([INGESTION_QUEUE_NAME], connection=Redis.from_url(REDIS_URL)).work()`. replicaها در compose: `WORKER_REPLICAS` (پیش‌فرض ۳). هر worker هم‌زمان یک سند را پردازش می‌کند. گلوگاه عملی: نرخ مجاز embedding/LLM-vision API. RQ برای هر job process فرزند fork می‌کند.

## خواندن ساخت‌یافته برای agent (`documents/service.py`)
- `get_document_info`: `total_pages` از JSON بازسازی‌شده (یا بیشینه‌ی `page` متادیتا، یا تعداد chunk)، `estimated_tokens` از `.reconstructed.txt` (یا الحاق chunkها)، `fits_read_entire_document` در برابر `FULL_DOCUMENT_MAX_TOKENS` (۳۰٬۰۰۰)، `has_images` از `pages[].has_images`. سند غیر READY یا خارج از scope → NotFound.
- `get_document_page_range`: اول JSON بازسازی‌شده؛ بعد chunkهای DB با `page`؛ بعد fallback قدیمی (`chunk_index` به‌جای صفحه). خروجی متنی با هدر `=== مستند: … ===` و `[صفحه N]`.
- `get_full_document_content`: `.reconstructed.txt`؛ اگر >۳۰٬۰۰۰ توکن → دیکشنری `{"error":"DOCUMENT_TOO_LARGE","total_pages",…}` تا مدل با `read_document_pages` بازه‌ی صفحات را بخواند.
همه‌ی این‌ها با `_get_accessible_document` scope را اعمال می‌کنند.

## بازیابی hybrid (`retrieval/service.py`)
مصرف‌کننده‌ی واحد: ابزار `search_knowledge_base`. `get_retriever()` → `HybridRetriever` (اگر `RETRIEVAL_HYBRID_ENABLED`، پیش‌فرض true) وگرنه `VectorRetriever` (رفتار قدیمی)؛ و در صورت `RETRIEVAL_RERANK_ENABLED` در `RerankingRetriever` پیچیده می‌شود.

**ستون‌های جدید `document_chunks`** (migration 0008): `search_text` (همان chunk با `core/text_normalization.normalize`: ی/ک عربی→فارسی، نیم‌فاصله→فاصله، ارقام فارسی/عربی→لاتین، حذف نقطه‌گذاری، lower؛ در `before_insert` ORM پر می‌شود) و `search_tsv` (ستون generated: `to_tsvector('simple', search_text)`) با ایندکس GIN؛ و ایندکس GIN trigram (`gin_trgm_ops`) روی `search_text` (افزونه‌ی `pg_trgm`).

**سه رتبه‌بندی، هر کدام با همان فیلتر دسترسی** (`accessible_documents_filter`، پس لایه‌ی واژگانی هم از scope بیرون نمی‌رود):
1. **برداری**: `ORDER BY embedding <=> q LIMIT N` (N = `RETRIEVAL_CANDIDATES`=۳۰).
2. **full-text**: کلمات پرسش (`query_terms`: نرمال، بدون stopword، یکتا، ≤۱۶) با `|` (OR) به `to_tsquery('simple', …)`؛ ترتیب با `ts_rank_cd`. سپس در پایتون هر کاندیدا باید حداقل `min(RETRIEVAL_LEXICAL_MIN_TERM_HITS=2, تعداد کلمات پرسش)` کلمه‌ی متمایز از پرسش را واقعاً داشته باشد وگرنه کنار گذاشته می‌شود (چون Postgres FTS مثل BM25 وزن IDF ندارد و یک کلمه‌ی رایج نباید chunk نامربوط را بیاورد).
3. **trigram** (فقط پرسش کوتاه ≤ `RETRIEVAL_TRIGRAM_MAX_TERMS`=۳ کلمه): `phrase <% search_text` با `pg_trgm.word_similarity_threshold` = `RETRIEVAL_TRIGRAM_THRESHOLD` (۰٫۶۵، با `set_config(..., true)` فقط در همان تراکنش)؛ تحمل غلط املایی («موقد»↔«موقت»).

**ادغام**: Reciprocal Rank Fusion با `k=RETRIEVAL_RRF_K`=۶۰ (`reciprocal_rank_fusion`) و برش به `top_k` (=۵). `RetrievedChunk.score` همچنان **cosine similarity** است (برای آستانه و UI)، و `lexical_match=True` یعنی full-text/trigram هم آن را پیدا کرده.
**آستانه** (`RETRIEVAL_SCORE_THRESHOLD`=۰٫۳): *قبل از برش top_k* هر chunk باید `sim ≥ آستانه` **یا** `lexical_match` باشد (NaN، مثلاً بردار صفر، رد نمی‌شود؛ مثل قبل). ⚠️ تغییر نسبت به قبل: قبلاً فقط «بهترین chunk زیر آستانه ⇒ هیچ‌چیز» بود؛ حالا هر chunk جدا ارزیابی می‌شود.
پرس‌وجوها فقط ستون‌های لازم را می‌خوانند (بدون embedding و tsvector).
اگر پرسش بعد از حذف stopword هیچ کلمه‌ای نداشته باشد، فقط برداری اجرا می‌شود.
**re-rank اختیاری** (`RerankingRetriever`، `RETRIEVAL_RERANK_ENABLED`): ۲۰ کاندیدای retriever داخلی (با `min_similarity`) را با یک prompt کوتاه به LLM (`LLM_RERANK_MODEL` یا `LLM_MODEL`) می‌دهد که اندیس بهترین ≤۵ مورد را به‌صورت آرایه‌ی JSON برگرداند (`[]` = هیچ‌کدام جواب پرسش نیست ⇒ نتیجه‌ی خالی). هر خطا/timeout/پاسخ نامعتبر ⇒ برگشت به ترتیب بدون re-rank. اگر پرسشی نباشد یا فقط یک کاندیدا باشد LLM صدا زده نمی‌شود. نتایج اندازه‌گیری: [../ops/retrieval-evaluation.md](../ops/retrieval-evaluation.md).
`Retriever` یک ABC است؛ امضا: `retrieve(db, project_id, conversation_id, query_embedding, top_k, query_text=None, min_similarity=None)`.
نگاشت دانشی: ← [../decisions.md](../decisions.md) (بند hybrid).
