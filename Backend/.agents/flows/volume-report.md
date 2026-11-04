# ماژول «گزارش حجم عملیات» (`app/features/volume_report/`)

> وضعیت: **در حال توسعه فازبندی‌شده**. فاز ۰ (استخراج) و فاز ۱ (زیرساخت قطعی + API + publish) پیاده شده. همه‌ی فازها (۰ تا ۴) پیاده شده‌اند؛ فقط ارزیابی با مدل واقعی ([ops/vr-evaluation.md](../ops/vr-evaluation.md)) و فرانت‌اند مانده‌اند. با `VOLUME_REPORT_ENABLED=false` (پیش‌فرض) هیچ router ثبت نمی‌شود و رفتار Orbit تغییری نمی‌کند.

## اصل‌ها
- کد عدد را می‌خواند و حساب می‌کند؛ LLM هرگز مقدار نمی‌بیند (فاز ۳ به بعد).
- منبع فایل = `documents` پروژه؛ دسترسی = عضویت پروژه (بدون جدول دسترسی جدید).
- نرمال‌سازی متن: همان `core/text_normalization.normalize` (+ جمع‌کردن whitespace در `normalize_text`).

## فاز ۰ — `extraction/` (خالص، بدون DB)
| فایل | کار |
|---|---|
| `seed_data.py` | seed واژگان (پیوست الف) و نگاشت `hard_exclusion` → `exclude_reason`؛ فاز ۱ همین داده را در `vr_lexicon` می‌ریزد |
| `extraction/units.py` | `normalize_unit` → `unit_norm` ∈ {m3,m2,m,kg,t,m2cm,m3km,hr,lump,series,pct,ea,other} + `unit_dim` |
| `extraction/normalize.py` | `Lexicon` (توکن‌گذاری روی **کلمه** با طولانی‌ترین عبارت اول؛ «زیر اساس» → `SUBBASE` نه `BASE`)، `role_hint`، `group_key`، `parse_quantity` (Decimal با ۴ رقم اعشار) |
| `extraction/workbook.py` | `open_workbook`: `.xlsx/.xlsm` با openpyxl (`data_only`, `read_only`)، `.xls` با xlrd و fallback به `converted_copy`، `.pdf` برداری با `pdf_extractor`؛ سقف ۴۰۰×۴۰؛ blocking → فقط در worker/thread |
| `extraction/pdf_extractor.py` | استخراج جداول PDFهای برداری بر اساس مختصات متنی $(X, Y)$ و تبدیل هر صفحه به یک `SheetData` مجازی بدون نیاز به OCR/LLM. آستانه‌های فاصله‌ی کلمه/ردیف با اندازه‌ی فونت صفحه مقیاس می‌شوند (شیت‌های خیلی عریض که در یک صفحه جمع شده‌اند فونت ریز دارند و برچسب‌هایی مثل «ضریب شکست» و «حجم» در یک سلول ادغام می‌شدند). خط‌های شکسته‌ی شرح (بالا/پایین ردیف کد، یا سرریز به ستون «ضریب شکست»/حجم و «متر 0») با نزدیک‌ترین ردیف کد از نظر Y چسبانده می‌شوند، وگرنه ردیف حجم‌دار بدون شرح حذف می‌شد. ردیف‌های «جمع …» به بعد دست‌نخورده می‌مانند |
| `extraction/probe.py` | رده‌بندی شیت‌ها (`hidden/planned/expense/income/other`) و `suggest_company` |
| `extraction/income_parser.py` | پیدا کردن سرتیتر/ستون‌ها با برچسب، توقف روی «جمع»، رد ردیف خالی، carry-forward عنوان بخش، نام کارگاه (تاریخ گزارش، «تاریخ : …»، «<ماه> ماه <سال>» و بازه‌ی «از … الی …» از انتهای نام حذف می‌شود تا کارگاه هر گزارش تازه ساخته نشود؛ رقم‌های خودِ نام مثل «قطعه 2» می‌مانند)، `twin_rows`، هشدار ماه |
| `extraction/runner.py` | `extract_file(path, lexicon, period_label)` → `sheet_log` + شیت‌های parse‌شده + هشدارها |

### تصمیم‌های ریز (کد درست است)
- هر شیت غیرپنهان با «برنامه» در نام `planned` است (حتی بدون «درآمد»)؛ هرگز خوانده نمی‌شود.
- `twin_rows` (شماره ردیف‌های شیت، نه id) برای ردیف‌های فیزیکی با کمیت **و واحد** یکسان و شرح متفاوت؛ فقط hint، متقارن، و خودکار dedup نمی‌شود.
- `cached_values_missing` فقط وقتی هشدار می‌دهد که ≥۳ ردیف «واحد دارد، حجم None و عدد دیگری در ردیف هست» و هیچ ردیف غیرصفری نیست.
- `group_key` به نوع کارگاه وابسته است و نوع بعد از تأیید تغییر می‌کند؛ پس parser آن را نمی‌سازد و فاز ۱ با `group_key()` می‌سازد.
- وابستگی جدید: `xlrd==2.0.2` (در `requirements.txt`).

### تست
`tests/features/volume_report/extraction/` — بدون DB/شبکه (conftest محلی fixtureهای autouse دیتابیس را خاموش می‌کند)؛ workbookهای مصنوعی با openpyxl؛ تست `.xls` واقعی با LibreOffice (skip اگر نبود).

## فاز ۱ — جریان و قراردادها
**جریان:** `POST /volume-reports` (draft) → `PUT /{id}/files` (document_id + company_id) → `POST /{id}/run` (claim اتمیک `UPDATE … WHERE status NOT IN (processing, published)` و enqueue در صف `VR_QUEUE_NAME`) → worker: `pipeline.run_report` (parse در thread → `vr_lines` → طبقه‌بندی گروه‌ها → `service.recompute`) → `needs_review|ready` → `review/confirm` → `publish` (snapshot).

| ماژول | کار |
|---|---|
| `models.py` | جدول‌های `vr_*` (migration `0014_volume_report`؛ seed در migration نیست) |
| `seed.py` / `seed_data.py` | `ensure_seeded` (lazy، فقط افزودنی: آیتم/توکنِ seed که در DB نیست اضافه می‌شود و ردیف موجود هرگز دست نمی‌خورد): ۱۶ آیتم (از جمله `pipe_laying` — لوله‌گذاری، متر طول)، واژگان، چگالی آسفالت **۲٫۳۵** t/m³ (تصمیم کارفرما؛ پیوست الف سند ۲٫۴ بود) |
| `ItemRule` (`vr_item_rules`) | «قانون زیرمجموعه‌ی آیتم»: اگر شرح ردیف (نرمال‌شده) شامل یکی از `phrases` و واحد ردیف برابر `source_unit` باشد، مقدار `quantity × factor` مستقیم به واحد خروجی آیتم تبدیل می‌شود (مثلاً آبرو دالی: ۱ m2 = ۲ m3 بتن) و گراف `convert.py` دور زده می‌شود. اولویت: قانون کارگاه‌محور > `priority` بالاتر > id. در `note` نتیجه `rule:<id>` ثبت می‌شود. تغییر قانون `catalog_version` را بالا می‌برد؛ گزارش‌های قبلی با recompute به‌روز می‌شوند. مثال: آیتم `concrete`، phrases=[«آبرو دالی»]، source_unit=`m2`، factor=2 |
| `convert.py` | گراف تبدیل واحد (BFS) با Decimal؛ تبدیل دوطرفه جرم/حجم `m3 <-> t` با `density_t_per_m3` (ضرب برای m3→t، تقسیم برای t→m3؛ `kg <-> m3` مجاز نیست)؛ `unit_mismatch` / `no_conversion` (+ `missing_param`) |
| `compute.py` | resolve + convert + aggregate **خالص** (بدون DB)؛ قاعده‌ی «یک effect برای هر ردیف» |
| `service.py` | دسترسی، گزارش/فایل، `recompute`، `gate_causes`، review/confirm، results/lines/trace، publish/reopen |
| `pipeline.py` | job؛ `run_report_sync` ورودی RQ |
| `router.py`, `schemas.py`, `export.py` | API (xlsx/csv RTL با محافظ formula-injection) |
| `workers/volume_report_worker.py` | worker صف جدا؛ compose: سرویس `vr-worker` (با `up` معمولی بالا می‌آید) |
| فرانت‌اند `Frontend/src/features/volume-reports/screens/PresentationScreen.tsx` | ارائه‌ی مدیریتی ۱۶:۹ (کانواس ثابت ۱۶in×۹in که روی صفحه scale می‌شود و در Print بدون scale چاپ می‌شود): جلد، نمای کلی، خلاصه‌ی همه‌ی آیتم‌ها، نمودار مقایسه‌ی شرکت‌ها، کارنامه‌ی شرکت‌ها (با ردیف جمع هولدینگ) و اسناد مأخذ؛ بدون کنترل کیفیت و کارنامه‌ی کارگاه‌ها. لوگوها با `<img>` ساده (نه next/image) و قبل از چاپ منتظر load می‌مانند؛ خروجی PDF از Print مرورگر و بدون endpoint جدید |

### قواعد و تصمیم‌های پیاده‌سازی (کد درست است)
- **دسترسی:** `check_project_access` = معادل `require_project_access` (عضو پروژه، leader تیم والد، admin). گزارش ناموجود 404، غیرعضو 403. تنظیمات (ساخت/ویرایش شرکت، کارگاه، پارامتر تبدیل) فقط `is_admin` یا `led_team_ids` غیرتهی؛ خواندن برای هر کاربر لاگین‌شده.
- **فایل:** `document.project_id == report.project_id` (وگرنه 404)، `READY`، پسوند اکسل یا پی‌دی‌اف (`.xls, .xlsx, .xlsm, .pdf`) (400)؛ مسیر فقط از `Document.file_path` و باید داخل `UPLOAD_DIR` باشد (در زمان run؛ تخطی → فایل `failed`).
- **اولویت طبقه‌بندی هر گروه:** تصمیم human قبلی همان گزارش (re-run حفظش می‌کند) > قاعده‌ی سخت (`hard_exclusion`) > واحد غیرفیزیکی/ساعت (`nonphysical`) > حافظه‌ی دقیق (`vr_decisions.key_hash == group_key`) > `needs_input`.
- `remember_scope=global` در `review/confirm` در `vr_decisions` upsert می‌کند (بدون embedding) و `catalog_version` را بالا می‌برد؛ `line` فقط در همان گزارش می‌ماند.
- **مجموع‌ها از مقدار گردنشده‌ی تبدیل‌شده** ساخته می‌شوند (نه جمع اعداد گردشده)؛ سپس ۴ رقم اعشار. مثال: rebar 43.1669.
- ردیف منفی با item شمرده‌شدنی → `excluded` با note `negative_qty` (هرگز کم نمی‌شود).
- `role=na` مثل اجرا شمرده می‌شود؛ فقط `supply` کنار اجرا نادیده/تنها نشمرده است. `exclude_reason=duplicate` → effect `duplicate_ignored`.
- **قفل انتشار (`VR_PUBLISH_GATE`)** علت‌ها: `open_questions`، `unconfirmed_counted`، `needs_input`، `unit_mismatch`، `no_conversion`، `site_kind_unconfirmed`. strict → 409؛ warn → در `snapshot.payload.warnings.gate`.
- publish یک `vr_snapshots` می‌سازد؛ گزارش منتشرشده تغییرناپذیر است (409 برای files/run/delete/confirm). `reopen` نسخه‌ی `version+1` با `supersedes_id` و کپی فایل‌ها و تصمیم‌های human؛ یک‌بار.
- تغییر `kind` کارگاه، `group_key` ردیف‌های موجود را عوض **نمی‌کند**؛ گزارش را دوباره run کنید. تغییر پارامتر تبدیل: `POST /{id}/recompute`.
- سؤال‌ها (`vr_questions`) فعلاً فقط جدول و شمارش در gate هستند؛ endpointهایشان فاز ۳.
- `twin_rows` هنوز در اتوماسیون استفاده نمی‌شود (فقط hint در `flags`؛ تصمیم `duplicate` با human/agent).

### endpointهای فاز ۱ (پیشوند `/api/v1/volume-reports`)
`POST /` · `GET /?project_id=&status=` · `GET|DELETE /{id}` · `PUT /{id}/files` · `POST /{id}/run` · `POST /{id}/recompute` · `GET /{id}/progress|sources` · `GET /{id}/review/groups?state=` · `POST /{id}/review/confirm` · `GET /{id}/results?group_by=&include=other,problems,nonphysical` · `GET /{id}/lines` · `GET /{id}/trace?item_key=&site_id=` · `POST /{id}/publish|reopen` · `GET /{id}/export?format=` · `GET /catalog` · `GET|POST|PUT /settings/companies` · `GET|PUT /settings/sites` · `GET|PUT /settings/conversions` · `DELETE /settings/conversions/{id}` · `GET|POST /settings/item-rules` · `PUT|DELETE /settings/item-rules/{id}`.
مقادیر به‌صورت رشته‌ی دسیمال (`"2572.8717"`) و `unit`.

### تست
`tests/features/volume_report/{test_compute,test_api}.py` (Postgres لازم؛ workbook مصنوعی، بدون شبکه): مقادیر مرجع، gate، publish/reopen، حافظه، دسترسی منفی (403/404/400)، path خارج از `UPLOAD_DIR`، run هم‌زمان.

## فاز ۲ — حافظه‌ی تصمیم‌ها (`memory.py`)
- هنگام `review/confirm` با `remember_scope=global`، `vr_decisions` upsert می‌شود و embedding شرح نرمال ساخته می‌شود (`ensure_embedding`؛ شکست provider = ذخیره بدون بردار، جست‌وجوی trigram کار می‌کند).
- **فقط تطبیق دقیق `key_hash` خودکار اعمال می‌شود** (`source=memory`, `confirmed=true`, `hits += 1`). تصمیم ابطال‌شده (`revoked_at`) یا اشاره‌کننده به آیتم غیرفعال اعمال نمی‌شود؛ گروه `needs_input` با `reason=memory_item_inactive` می‌ماند.
- `search_similar(text, unit?, site_kind?)`: ۲۰ کاندید cosine + ۲۰ کاندید trigram (`similarity`) با RRF (`retrieval.service.reciprocal_rank_fusion`) → ۵ مورد؛ بردار صفر نادیده؛ تصمیم‌های ابطال‌شده حذف. فقط نمونه برای agent/کاربر است.
- لغو: `POST /settings/decisions/{id}/revoke` (admin/leader) → `catalog_version += 1`. گزارش‌های محاسبه‌شده دست نمی‌خورند؛ اجرای بعدی تصمیم را نمی‌یابد.
- endpointها: `GET /settings/decisions?q=&include_revoked=`، `GET /settings/decisions/similar?text=&unit=&site_kind=`، `POST /settings/decisions/{id}/revoke` (همگی admin یا leader).
- تست: `tests/features/volume_report/test_memory.py` (provider embedding در تست stub می‌شود؛ بدون stub هر confirm منتظر شبکه می‌ماند).

## فاز ۳ — agent، سؤال‌ها، دورها
**provider:** `LLMProvider.complete(messages, tools, tool_choice, response_format)` غیراستریم است؛ پیاده‌سازی پیش‌فرض در ABC روی `stream_chat` می‌ایستد (پس stubهای قدیمی بدون تغییر کار می‌کنند)، و `OpenAICompatibleLLMProvider` نسخه‌ی واقعی با retry، دمای ۰ و usage دارد. `get_vr_llm_provider()` مدل `LLM_VR_MODEL or LLM_MODEL` را می‌سازد.

**جریان job:** ... → `_classify` (گروه‌های باقی‌مانده `needs_input/awaiting_classification`) → `agent.runner.run_pass` اگر گروه باقی باشد **یا** شیت `layout_unknown` داشته باشیم → resolve/aggregate → سؤال‌های سیستمی (`refresh_system_questions`) → `trim_open_questions` (سقف `VR_MAX_QUESTIONS_PER_PASS`، بر اساس `impact_score` که کد حساب می‌کند) → وضعیت: `awaiting_user` اگر سؤال باز، وگرنه `needs_review/ready`.
`POST /{id}/continue` همان job را با `mode="continue"` صف می‌کند (بدون parse؛ گروه‌های `agent_failed|agent_incomplete|asked` غیرانسانی دوباره `awaiting_classification` می‌شوند).

**runner (`agent/runner.py`):** حلقه‌ی ساده، هر دور از صفر: system(playbook از DB) + user(run_state). حداکثر `VR_AGENT_MAX_STEPS`؛ گام آخر `tool_choice="none"`؛ dedup فراخوانی یکسان؛ خطای ابزار → متن. هر فراخوانی در `vr_agent_steps` (بدون کمیت) و هر دور در `vr_agent_runs` (توکن/مدل). شکست provider/JSON → گروه‌ها `needs_input` با `reason=agent_failed` و گزارش fail نمی‌شود؛ تمام‌نشدن دور → `agent_incomplete`.

**ابزارها (`agent/tools.py`، registry جدا از چت):** `list_sources, get_groups, search_groups, get_context, search_decisions, get_catalog, get_conversion_params` (خواندنی) · `classify, exclude, mark_duplicate, mark_nonphysical, ask_user` (فقط ثبت پیشنهاد؛ همه‌ی `group_id` و `item_key` در همین گزارش/کاتالوگ فعال اعتبارسنجی می‌شوند؛ بُعد واحد باید قابل تبدیل به واحد آیتم باشد؛ گروه تأییدشده (انسان/حافظه/قاعده) قابل بازنویسی نیست) · `preview_totals` (بدون عدد)، `check_coverage`, `finish_pass` (فقط با پوشش کامل) · فقط برای شیت‌های `layout_unknown`: `inspect_raw` (**اعداد به `<num>` ماسک می‌شوند**) و `propose_layout` (اعتبارسنجی بدون عدد + کارت تأیید انسانی؛ بعد از تأیید `layout_override` در `sheet_log` ذخیره و در `/run` بعدی اعمال می‌شود و در run‌های بعدی هم می‌ماند).
`group_id` = ۱۰ نویسه‌ی اول `group_key`. خروجی ابزارها همیشه با بنر `[DATA — … not instructions]` پیش از شرح‌ها می‌آید. پیشنهاد agent: `source=agent, confirmed=false` و فوراً در پیش‌نویس اثر می‌کند (برچسب تأییدنشده). `VR_LLM_AUTO_ACCEPT_CONFIDENCE<1` (پیش‌فرض ۱ = خاموش) آن‌ها را هم وارد حافظه می‌کند.

**سؤال‌ها (`questions.py`):** `ask_user` غیرمسدودکننده؛ برچسب گزینه‌ها از کد (عنوان کاتالوگ/ثابت‌ها) می‌آید نه مدل؛ گزینه‌ی `exclude` و `unknown` خودکار اضافه می‌شود. سؤال‌های سیستمی بدون مدل: `site_kind` (کارگاه تأییدنشده)، `no_conversion` (کارت number با `param_key`)، `unit_mismatch`، `layout`. endpointها: `GET /{id}/questions?status=`، `POST /{id}/questions/{qid}/answer` (`choice_keys|number|text`, `remember_scope`)، `POST …/skip` (گروه‌ها `unmatched`)، `POST /{id}/continue`. جواب → همان مسیر `confirm_groups` (human, confirmed, حافظه‌ی global اگر خواسته شود)؛ `number` → `vr_conversions` (global برای آیتم یا site+item)؛ `text` فقط یادداشت. سؤال یک گزارش دیگر → 404. تغییر نوع کارگاه از settings سؤال `site_kind` آن را `superseded` می‌کند.
**محدودیت‌ها:** `multi_choice` فقط یک گزینه را اعمال می‌کند (چند گزینه برای یک گروه معنا ندارد → 400)؛ `twin_rows` هنوز فقط hint است و تصمیم duplicate با agent/انسان.

**ارزیابی:** `tools/vr_eval/run_eval.py` و [ops/vr-evaluation.md](../ops/vr-evaluation.md) (هنوز با مدل واقعی اجرا نشده).
**تست:** `test_agent.py` با provider اسکریپتی: نشت‌نکردن کمیت به مدل، رد `finish_pass` ناقص، dedup، سقف گام، خطای ابزار → متن، سؤال/پاسخ/skip/continue، `no_conversion`، layout، مالکیت سؤال.

## فاز ۴ — ابزار چت، settings، سخت‌سازی
- **ابزار چت** `chat_tool.GetVolumeReportTool` (ثبت شرطی در `build_default_registry`): جزئیات و شکل artifact در [reference/api-endpoints.md](../reference/api-endpoints.md).
- **settings:** `GET/POST/PUT /settings/items` (کلید غیرقابل‌تغییر؛ `output_unit` باید با `dimension` بخواند؛ rollup فقط با اعضای موجود) و `/settings/lexicon` (token بزرگ-انگلیسی؛ ویرایش `hard_exclusion` از اجرای بعدی اعمال می‌شود). هر تغییر `catalog_version` را بالا می‌برد و آیتم تازه بلافاصله در playbook agent هست (پرامپت از DB ساخته می‌شود).
- **هم‌زمانی:** (۱) claim اتمیک `UPDATE … WHERE status != published AND (status != processing OR updated_at < now()-2×VR_JOB_TIMEOUT)` → run هم‌زمان 409، و گزارش `processing`ی که worker‌اش مرده دوباره قابل claim است؛ (۲) `pg_try_advisory_lock` روی اتصال جدا در `run_report` (job تکراری skip می‌شود)؛ (۳) `publish`/`reopen` با `SELECT … FOR UPDATE`.
- **idempotency:** snapshot یکتا به‌ازای گزارش، reopen فقط یک‌بار، سؤال تکراری برای همان گروه رد می‌شود.
- **تله‌ی دانستنی:** تست‌هایی که `review/confirm` را صدا می‌زنند باید `memory.get_embedding_provider` را stub کنند (وگرنه منتظر شبکه می‌مانند).
- **deploy:** سرویس `vr-worker` با `up` معمولی (در prod همراه `-f docker-compose.yml -f docker-compose.prod.yml`) بالا می‌آید؛ بدون worker، `POST /run` فقط job را در صف می‌گذارد و گزارش برای همیشه روی «در حال پردازش» می‌ماند. `xlrd` در `requirements.txt` است (image باید rebuild شود).

## گزارش فعالیت (`activity.py`، جدول `vr_activity`، migration `0015_vr_activity`)
- timeline قابل‌نمایش به کاربر از کار job: هر مرحله‌ی pipeline (parse هر فایل/کارگاه، classify با شمارش علت‌ها، شروع/پایان agent، compute، نتیجه) و هر فراخوانی ابزار agent یک ردیف می‌شود. **در DB ذخیره می‌شود** نه فقط روی stream، پس با خروج و بازگشت به صفحه کل تاریخچه دیده می‌شود.
- عنوان‌ها (فارسی) را **کد** از نام ابزار/نتیجه می‌سازد (`describe_tool`)، نه متن مدل؛ فقط شمارش، هرگز کمیت (تست: نبودن عدد کمیتی در فید). تنها استثنا متن `prompt` سؤال agent است.
- `attempt` = شماره‌ی اجرا (هر job یکی؛ `new_attempt=True` در `_run_locked`)؛ `id` (BigInteger) همان cursor است. `kind`: `info|step|success|warn|error|question`.
- `log_activity(..., commit=False)` وقتی caller بلافاصله commit می‌کند. در runner، `report.progress` در هر گام `{step:"agent", agent_step, max_steps, done, total}` به‌روز و commit می‌شود (برای «در انتظار پاسخ مدل — گام x از y»).
- گزارش حذف‌شده → ردیف‌ها CASCADE پاک می‌شوند.

## فرانت‌اند
پیاده‌سازی و قواعدش در `Frontend/FRONTEND_PLAN.md` (بخش «ماژول گزارش حجم عملیات»). نکات قراردادی که از بک‌اند می‌آید: فعال‌بودن ماژول با probe روی `GET /volume-reports/catalog` (۴۰۴ = خاموش)؛ `review/groups` حالا `confidence` دارد و `/catalog` حالا `rollup_of`؛ خطای قفل انتشار پیام `Publish blocked: [{"code","count"}…]` است.
