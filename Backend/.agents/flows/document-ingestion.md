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
- پسوند باید در `SUPPORTED_EXTENSIONS` باشد: **`.pdf .docx .pptx .xlsx .txt` + تصاویر `.png .jpg .jpeg .webp .bmp .tiff`**. در غیر این‌صورت 400.
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
`DEFAULT_PIPELINE = [ParseStep, OCRStep, ReconstructStep, ChunkStep, EmbedStep, PersistStep]` — هر step یک `IngestionStep.run(IngestionContext)`؛ context شامل `document_id, file_path, db, filename, pages, raw_text, page_chunks, chunks, embeddings` است.

1. **ParseStep** — `parse_document_pages(file_path)` → `list[DocumentPage(page_number, text, images, metadata, needs_ocr)]`؛ NUL (`\x00`) از متن حذف می‌شود.
   - **کنترل کیفیت لایه‌ی متنی PDF** (`ingestion/text_layer.py`، روی هر صفحه): `assess_text_layer` سه حالت می‌دهد: `ok`؛ `visual_persian` (متن فارسی با presentation forms عربی `U+FB50–FDFF / U+FE70–FEFF` در ترتیب بصری: حروف هر کلمه برعکس و فاصله‌ی اضافه وسط کلمه — معمولاً فایل‌های «Machine Translated by Google» یا print-to-PDF؛ **روی داده‌ی واقعی اندازه‌گیری شد: هم‌پوشانی کلمه با متن درست = ۰٪**)؛ `garbled` (لایه‌ی OCR قدیمی اسکن که فقط نویز نمادی است؛ معیار: `wordlike<0.15` و `noise≥0.10`). صفحه‌ی غیر `ok` علامت `needs_ocr` و `metadata.text_layer` می‌گیرد؛ برای `visual_persian` فوراً `fix_visual_persian` اعمال می‌شود (چسباندن chunkهای شکسته با قاعده‌ی joining form، برعکس‌کردن حروف هر کلمه، NFKC، اصلاح ترتیب run لاتین/عدد). این اصلاح فقط fallback است (~۷۰٪ کلمات درست برمی‌گردد؛ OCR ~۹۳–۹۵٪).
   پارس PDF بلند (≥۸ صفحه) بین `PDF_PARSE_WORKERS`=۴ process (fork، `ProcessPoolExecutor`) به بازه‌های صفحه تقسیم می‌شود چون decode عکس‌های اسکن توسط pypdf CPU-bound است (اندازه‌گیری واقعی: ۴۲ صفحه ≈ ۵۵ ثانیه تک‌process؛ ۴۲٫۵ ثانیه‌اش decode تصویر). هر خطا در pool ← fallback به تک‌process. لاگ INFO `PDF parse …` زمان هر فاز را می‌دهد؛ `ParseStep/OCRStep/…` هم زمان خود را لاگ می‌کنند.
   **صفحه‌ی اسکن**: صفحه‌ای که متن ندارد و یک تصویر در اندازه‌ی صفحه (ضلع کوتاه ≥ ۴۰۰px، از دیکشنری PDF خوانده می‌شود، decode نمی‌شود) دارد `needs_ocr=True` و `metadata.text_layer="scan"` می‌گیرد، `images=[]` می‌ماند و `OCRStep` کل صفحه را رندر و یک‌بار OCR می‌کند. دلیل: اسکنرها/MRC صفحه را به لایه‌ی پس‌زمینه + پیش‌زمینه (+ماسک) می‌شکنند؛ هر لایه به‌تنهایی ناخوانا یا غلط خوانده می‌شود (اندازه‌گیری روی `eval/10.pdf`: یک لایه متن **پروژه‌ای دیگر** برگرداند) و decode آن‌ها کندترین بخش parse بود (~۱٫۲ث/صفحه) و فراخوانی vision را دو برابر می‌کرد. فقط وقتی فعال است که `OCR_ENABLED` و `OCR_REPLACE_BAD_TEXT_LAYER` هر دو true باشند؛ وگرنه رفتار قدیمی (تک‌تک تصاویر). تصویرهای تو در توی form XObject بررسی نمی‌شوند (← مسیر قدیمی).
   | فرمت | «صفحه» |
   |---|---|
   | PDF (pypdf) | هر صفحه؛ متن + تصاویر embed شده (فیلتر: حداقل `OCR_MIN_IMAGE_DIMENSION`=۶۰ در هر بعد). اگر صفحه نه متن دارد نه تصویر (اسکن) → رندر با `pdftoppm -r 150` (timeout ۲۰ثانیه) و یک تصویر برای OCR |
   | DOCX | یک صفحه‌ی واحد: پاراگراف‌ها + جدول‌ها (`a | b | c`) + تصاویر |
   | PPTX | هر اسلاید: متن frameها + جدول + تصاویر |
   | XLSX | هر sheet یک صفحه (`=== Sheet: name ===` + ردیف‌ها با `|`)، `data_only=True`، `metadata.sheet_name` |
   | TXT | یک صفحه؛ تشخیص UTF-16/UTF-8-BOM/heuristic |
   | تصویر | یک صفحه با یک تصویر خام برای OCR |
2. **OCRStep** — اگر `OCR_ENABLED`. قبل از هر فراخوانی پولی دو لایه‌ی cache (`_OcrReader`): (۱) **داخل سند**: یک تصویر با بایت‌های یکسان (لوگو/مهر/header تکراری، صفحه‌ی مشابه) فقط یک‌بار خوانده و نتیجه بین همه‌ی صفحات به‌اشتراک گذاشته می‌شود (متن همچنان به هر صفحه اضافه می‌شود)؛ تصویر تکراری از سقف `OCR_MAX_IMAGES_PER_DOC` کم نمی‌کند. (۲) **بین سندها**: جدول `ocr_cache` با کلید `sha256(تصویر)` + hash مدل/prompt؛ برای صفحه‌ی رندرشده‌ی `needs_ocr` هم همین (رندر قطعی است، پس همان صفحه‌ی PDF در سند دیگر hit می‌شود). فقط نتیجه‌ی غیرخالی cache می‌شود (شکست/تصویر خالی دفعه‌ی بعد دوباره امتحان می‌شود)؛ خطای خود cache فقط warning است و تصویر مستقیم خوانده می‌شود. تنها فراخوانی API با `OCR_CONCURRENCY` محدود می‌شود. لاگ پایان: «N vision calls, M cache hits, K shared within the document». dedup کل‌فایل (بالا) و این cache مستقل‌اند: این یکی وقتی کار می‌کند که فایل بایت‌به‌بایت یکی نیست ولی صفحه/تصویرش هست. دو کار، با هم‌زمانی `OCR_CONCURRENCY`=۱۲ صفحه (تصاویر یک صفحه متوالی می‌مانند تا ترتیب ثابت باشد):
   - **صفحه‌ی `needs_ocr`** (و `OCR_REPLACE_BAD_TEXT_LAYER`، سقف `OCR_MAX_REPLACED_PAGES`=۳۰۰ صفحه در سند): با `pdftoppm -r 150` رندر و OCR می‌شود و متن OCR **جایگزین** لایه‌ی متنی می‌شود (`metadata.text_layer="ocr"`)؛ اگر OCR شکست خورد یا <۲۰ نویسه داد، متن اصلاح‌شده‌ی مرحله‌ی parse می‌ماند. تصاویر چنین صفحه‌ای جدا OCR نمی‌شوند.
   - **سایر صفحات**: برای هر تصویر (تا سقف `OCR_MAX_IMAGES_PER_DOC`=۵۰ در کل سند) `extract_text_from_image`؛ نتیجه به `page.text` اضافه می‌شود با برچسب `[محتوای استخراج‌شده از تصویر / جدول]:`.
   خطای OCR صرفاً warning است و سند ادامه می‌دهد. `extract_text_from_image` تا ۳ تلاش (backoff ۲ و ۴ ثانیه) دارد. هر صفحه‌ی OCR حدود ۲۰–۲۵ ثانیه طول می‌کشد؛ job timeout سند `INGESTION_JOB_TIMEOUT_SECONDS`=۳۶۰۰ (قبلاً ثابت ۶۰۰ بود که برای PDF طولانی کافی نبود).
   - `extract_text_from_image`: اگر `LLM_API_KEY` خالی باشد یا تصویر <۱۰۰ بایت → رشته‌ی خالی. تصویر با Pillow به JPEG (حداکثر ۲۰۴۸px) بهینه، base64 و با prompt فارسی «OCR + جدول→Markdown + توضیح نمودار» به مدل `LLM_VISION_MODEL or LLM_MODEL` فرستاده می‌شود (`detail:"high"`, `max_tokens=2048`). خروجی `---`/`N/A`/`none`/`خالی` = تهی.
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
