# مرجع ابزارهای agent

تعریف: `app/features/agent/tools/*.py` (زیرکلاس‌های `BaseTool`)، ثبت: `tools/registry.py::build_default_registry`. جریان استفاده: [../flows/agent-turn.md](../flows/agent-turn.md). افزودن ابزار: [../guides/add-agent-tool.md](../guides/add-agent-tool.md).

هر ابزار: `name`, `description` (برای مدل)، `parameters` (JSON Schema)، و `async execute(*, db, context, conversation, **arguments) -> ToolExecutionResult`. آرگومان‌های اضافی با `**_` نادیده گرفته می‌شوند؛ آرگومان الزامی گم‌شده → `TypeError` → متن «Invalid arguments».

| ابزار | فایل | پارامترها | کار | scope |
|---|---|---|---|---|
| `search_knowledge_base` | document_tools | `query` | **hybrid** (برداری + full-text + trigram، ادغام RRF؛ ← flows/document-ingestion) و top_k (۵)؛ chunkهای با cosine < ۰٫۳ که واژگانی هم پیدا نشده‌اند حذف می‌شوند؛ اگر چیزی نماند «No relevant results found in the knowledge base.»؛ وگرنه متن `[Source i: filename (صفحه N)]\n…` + `citations` | اسناد گفتگو + پروژه‌ی scope |
| `get_document_info` | document_tools | `document_id` | metadata بدون خواندن محتوا: `{document_id, filename, content_type, status, scope(project|conversation), total_pages, chunk_count, estimated_tokens, fits_read_entire_document, has_images, uploaded_at}`. عمداً `uploaded_by` ندارد. فقط برای سند READY (فیلتر دسترسی فقط READY می‌دهد) | accessible |
| `read_document_pages` | document_tools | `document_id, start_page, end_page` | متن صفحات (۱-پایه، inclusive)؛ `start_page≥1` و `end_page≥start_page` وگرنه BadRequest | accessible |
| `read_entire_document` | document_tools | `document_id` | کل متن؛ بیش از ۳۰٬۰۰۰ توکن → JSON خطای `DOCUMENT_TOO_LARGE` همراه `total_pages`؛ بهتر است مدل قبلش `get_document_info` را بزند | accessible |
| `list_user_projects` | project_tools | — | `[{id,name}]` پروژه‌های عضو (join عضویت پروژه و تیم) | کاربر |
| `list_project_documents` | project_tools | — | `[{id,filename,status}]` پایگاه دانش پروژه‌ی scope | project scope |
| `get_current_chat_attachments` | project_tools | — | فایل‌های آپلودشده در همین گفتگو | conversation |
| `recall_project_insights` | memory_tools | `query, category?` | top-5 حافظه (JSON `[{fact,category,is_verified}]`) | project scope |
| `remember_project_insight` | memory_tools | `fact, category` | ذخیره‌ی حافظه؛ فقط به درخواست صریح کاربر | project scope |
| `ask_accounting_db` | accounting_tools | `question` | پرسش مالی (← flows/accounting-query) | فقط با `RAHKARAN_DB_ENABLED` |

نکات:
- `document_id` باید UUID معتبر باشد (`BadRequestError("'document_id' must be a valid UUID")` وگرنه).
- ابزارهای سند و حافظه `resolve_retrieval_scope` را صدا می‌زنند؛ اگر گفتگو به پروژه‌ای وصل نیست، فقط اسناد خود گفتگو در دسترس است و ابزارهای memory/`list_project_documents` پیام «isn't linked to any project» می‌دهند.
- در `search_knowledge_base` شناسه‌ها/شماره‌بندها/نام‌های دقیق را باید در `query` نگه داشت (جست‌وجوی واژگانی آن‌ها را عیناً می‌یابد؛ توضیح ابزار به مدل همین را می‌گوید).
- `search_knowledge_base` تنها ابزاری است که `citations` تولید می‌کند (که در `message.sources` و `done.sources` می‌آیند)؛ `snippet` = ۳۰۰ نویسه‌ی اول chunk، `score` گرد ۴ رقم.
- نتیجه‌ی همه‌ی ابزارها متن است؛ ابزار مالی علاوه بر آن artifact برمی‌گرداند.
- ترتیب ابزارها در لیست ارسالی به مدل = ترتیب ساخت در `build_default_registry` (سند، پروژه، حافظه، سپس مالی).
