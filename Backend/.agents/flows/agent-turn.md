# جریان: یک turn از agent (موتور و tool-calling)

فایل‌ها: `features/agent/{engine,schemas,scope}.py`, `features/agent/tools/*`, `providers/llm_provider.py`.
فراخواننده‌ها: `chat/service.py` (چت شخصی و گروهی). ابزارها: [../reference/agent-tools.md](../reference/agent-tools.md).

## ورودی/خروجی
`AgentEngine.run_agent_loop(db, conversation, context, callback) -> AgentTurnResult{content, citations, artifacts}`
- پیش‌شرط: پیام کاربر **قبلاً** در جدول `messages` ذخیره شده؛ engine آن را به‌عنوان آخرین ردیف تاریخچه می‌خواند.
- `callback(event, data)` مستقل از transport است:
  | event | داده | مصرف |
  |---|---|---|
  | `agent_activity` | `{status, tool?, args?}` | status ∈ `generating`, `searching`, `reading_documents`, `querying_database` |
  | `delta` | `{content}` | توکن متن پاسخ نهایی |
  | `artifact` | `{artifact}` | بلافاصله پس از اجرای ابزار (مثلاً نتیجه‌ی SQL) |

## ساخت prompt (`_build_messages`)
0. **ترتیب برای prefix cache:** بخش‌های ثابت اول، کم‌تغییر بعد، پرتغییر آخر (provider روی prefix یکسان تخفیف می‌دهد؛ اندازه‌گیری: ورودی ≈۱۰ برابر ارزان‌تر). پس ترتیب واقعی: `SYSTEM_PROMPT` ← group ← accounting ← **درخت سطح اول پروژه** ← پیوست‌های گفتگو ← تاریخچه. ابزارها هم قبل از پیام‌ها در prefix هستند: فهرستشان بین گام‌های یک turn عوض نمی‌شود (گام آخر ابزارها را حذف نمی‌کند، `tool_choice="none"` می‌دهد).
1. `system` = `SYSTEM_PROMPT` (انگلیسی: دستیار داخلی سازمان؛ از ابزارها استفاده کن؛ فقط دو نوع فایل می‌بینی؛ هرگز ادعای خواندن فایلی که با ابزار باز نکردی نکن) + **روال اسناد و تصاویر**: اسناد و تصاویر آپلودشده قبلاً توسط پایپ‌لاین OCR استخراج متن شده‌اند. برای درخواست کل متن/رونویسی یک فایل یا تصویر، بلافاصله `read_entire_document` (یا `read_document_pages`) با `document_id` از فهرست فایل‌های آپلودشده چت فراخوانی شود (نام فایل در RAG سرچ نشود و از `view_document_page` برای متن استفاده نشود). برای سؤالات موضوعی و جزئی از `search_knowledge_base` استفاده شود. ابزار دیداری `view_document_page` فقط مخصوص نقشه‌های فنی، کروکی و دیاگرام‌های غیرمتنی است.
1b. اگر گفتگو scope پروژه دارد: بند «Project knowledge base - top level» = پوشه‌های سطح اول با تعداد فایل‌های بازگشتی (و not ready) + فایل‌های سطح اول (حداکثر ۴۰ پوشه/۱۵ فایل، `folder_tools.project_tree_summary`) و قاعده‌ی agentic: اگر پرسش به پوشه/نوع سند/نام فایل اشاره دارد، با `browse_folder` بگرد، با `read_*` باز کن؛ قبل از پیمایش نتیجه نگیر که چیزی نیست؛ فایل غیر ready را «هست ولی هنوز خوانده نشده» گزارش کن.
2. اگر گفتگو سند دارد: فهرست **متادیتا** (نام، `document_id`، status؛ حداکثر ۵۰) با راهنمایی صریح که متن استخراج‌شده از طریق `read_entire_document` در دسترس است.
3. اگر `project_group`: توضیح گروه‌بودن + پیشوند `@bot` + اینکه پیام انسان‌ها با نام فرستنده شروع می‌شود.
4. اگر `RAHKARAN_DB_ENABLED`: بند طولانی درباره‌ی `ask_accounting_db` (یک‌بار صدا بزن؛ پرسش خودبسنده‌ی فارسی؛ UI خودش SQL/جدول را نشان می‌دهد پس کوتاه جواب بده؛ اعداد را عیناً نقل کن؛ واحد ریال/تومان؛ تعداد ردیف را از «total rows» ابزار بگو؛ نتیجه‌ی صفر ردیف ≠ نبودن داده).
5. تاریخچه: **۳۰ پیام آخر** (`_load_history`)؛ نقش `assistant` برای پاسخ‌های AI، `user` برای بقیه. در گروه، پیام کاربر با `"<نام یا ایمیل>: "` شروع می‌شود (نام‌ها با یک query).
⚠️ فقط `content` پیام‌ها بازپخش می‌شود؛ `sources`/`artifacts` و نتایج ابزارهای turnهای قبلی نه. پس مدل در turn بعد جدول SQL قبلی را «نمی‌بیند» جز آنچه در متن پاسخ قبلی‌اش آمده.

## حلقه (`MAX_STEPS = 8`)
```
for step in 0..7:
    tools = registry.to_openai_tools()
    stream = llm.stream_chat(messages, tools, tool_choice="none" if step == 7 else "auto")   # آخرین گام: همان ابزارها ولی ممنوع → مجبور به پاسخ، بدون خراب‌کردن prefix cache
      - content delta → callback("agent_activity",{generating}) (یک‌بار) + callback("delta")
      - tool_calls    → ذخیره
    اگر tool_calls نبود: full_response = متن گام؛ break
    messages += assistant(tool_calls)
    برای هر call:
        کلید (name, آرگومان canonical) تکراری؟ → نتیجه‌ی قبلی بدون اجرای دوباره
        status = reading_documents | querying_database | searching ؛ callback(agent_activity, {status,tool,args})
        result = registry.dispatch(...)   # هرگز استثنا بالا نمی‌دهد
        citations/artifacts جمع؛ callback("artifact") برای هر artifact
        messages += tool(tool_call_id, result.text)
return AgentTurnResult(full_response, citations, artifacts)
```
- **dedup داخل turn**: اگر مدل همان ابزار با همان آرگومان را دوباره بزند (موازی یا گام بعد) فقط یک‌بار اجرا می‌شود (برای `ask_accounting_db` مهم است: دو LLM call + دو query صرفه‌جویی).
- `_DOCUMENT_READ_TOOLS` = info/read pages/read entire/get_current_chat_attachments/browse_folder → status `reading_documents`.
- متنی که مدل *قبل از* tool call می‌گوید هم stream (delta) می‌شود ولی در `full_response` (و پیام ذخیره‌شده) نمی‌آید؛ فقط متن گام نهایی ذخیره می‌شود. ⚠️ ممکن است کلاینت متنی را در حین stream ببیند که بعد از بارگذاری مجدد گفتگو نیست.
- اگر LLM وسط turn قطع شود، engine استثنا می‌دهد؛ **فراخواننده** آن را می‌گیرد (`_failed_turn_result`): متن نیمه‌کاره + پیام فارسی «ارتباط با مدل قطع شد» (یا نسخه‌ای که می‌گوید جدول دیتابیس در artifact هست)، با artifactsی که تا آن لحظه ساخته شده.

## `ToolRegistry` (`tools/registry.py`)
- `build_default_registry()`: ۹ ابزار ثابت + `AskAccountingDbTool` اگر `rahkaran_db_enabled`. (ثبت در **زمان ساخت engine** — `_agent_engine = AgentEngine()` در سطح ماژول `chat/service.py` — پس تغییر env بدون restart اثر نمی‌کند.)
- `dispatch(name, arguments_json, db, context, conversation)` همه‌ی خطاها را به **متن** تبدیل می‌کند تا turn نمیرد:
  | خطا | متن به مدل |
  |---|---|
  | ابزار ناشناخته | `Unknown tool: '<name>'` |
  | JSON نامعتبر | `Invalid arguments for tool '<name>': not valid JSON` |
  | `ForbiddenError` | `Permission Denied` |
  | `NotFoundError` | `exc.detail` |
  | `BadRequestError` | `Invalid request: <detail>` |
  | `TypeError` (آرگومان ناسازگار) | `Invalid arguments for tool …: <msg>` |
  | سایر | لاگ + `Tool '<name>' failed unexpectedly. Try a different approach.` |

## `ToolExecutionResult`
`text` (برای مدل) · `citations: list[SourceCitation]` (برای `sources` نهایی؛ توسط `search_knowledge_base`، `read_entire_document`، `read_document_pages` و `view_document_page` پر می‌شود) · `artifacts: list[dict]` (برای کلاینت؛ فقط ابزار مالی).
`SourceCitation{document_id, document_filename, chunk_index, snippet(≤300), score, page?}`.

## تست
`tests/features/agent/test_engine.py` با `_ScriptedLLMProvider` (دنباله‌ی ثابت event) و `_AlwaysToolCallLLMProvider` (برای اثبات سقف `MAX_STEPS` گام و `tool_choice="none"` در گام آخر)؛ `tests/features/chat/test_tool_calling.py`.


## تصویر صفحه (`view_document_page`)
ابزار `ToolExecutionResult.images` برمی‌گرداند؛ چون پیام `tool` فقط متن می‌پذیرد، engine بعد از **همه‌ی** پیام‌های tool همان step یک پیام `user` با partهای `text` + `image_url` می‌گذارد (متن: پیام سیستمی، نه از کاربر). تصویر فقط در همان turn در `messages` هست و ذخیره‌ی DB نمی‌شود. سقف `AGENT_MAX_PAGE_VIEWS_PER_TURN`. تماس تکراری با همان آرگومان دوباره تصویر نمی‌فرستد (dedup). prompt سیستم می‌گوید برای ابعاد/برچسب نقشه از روی اعداد پراکنده یا صفحه‌ی دیگر حدس نزن و ابزار را بزن.
