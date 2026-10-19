# جریان: چت شخصی با AI (SSE)

فایل‌ها: `features/chat/router.py` (`POST /chat`), `features/chat/service.py` (`stream_chat_response`, `_stream_chat_events`), `features/agent/engine.py`.

## درخواست
`POST /api/v1/chat` با بدنه‌ی `ChatRequest{conversation_id?: uuid, message: str}` و Bearer token.
پاسخ: `StreamingResponse` با `text/event-stream` و هدرهای `Cache-Control: no-cache`, `X-Accel-Buffering: no` (و Caddy با `flush_interval -1` بدون buffer).

## مراحل (`_stream_chat_events`)
1. **گفتگو**: `get_or_create_personal_conversation`: اگر `conversation_id` داده شده و گفتگو `personal` و `created_by == user` است همان؛ **در غیر این صورت بی‌صدا گفتگوی جدید ساخته می‌شود** (حتی اگر id وجود داشته ولی مال دیگری یا group باشد؛ ادمین هم استثنا نیست). عنوان = ۸۰ نویسه‌ی اول پیام (`@bot` حذف و فاصله‌ها فشرده).
2. **عنوان خودکار**: `_auto_title_on_first_message` فقط اگر عنوان یکی از placeholderها (`New conversation`, `New group conversation`) باشد و هنوز پیامی نیست.
3. پیام کاربر ذخیره و commit.
4. `event: start` با `{conversation_id, title}`.
5. engine در `asyncio.Task` اجرا می‌شود (فقط آن task به `db` دست می‌زند). حلقه‌ی generator هر ۰٫۰۸ث صف را تخلیه و SSE می‌فرستد:
   - `agent_activity` → event `status`
   - `delta` → `delta` (و در `partial_text` جمع می‌شود)
   - `artifact` → `artifact` (و در `seen_artifacts`)
6. پایان task: اگر استثنا → لاگ، `_failed_turn_result(partial, artifacts)`، و یک `delta` اضافی با متن خطای فارسی.
7. پیام assistant (`content`, `sources=[citation.model_dump()]`, `artifacts`) ذخیره و commit.
8. `event: done` با `{sources, artifacts, message_id}`.

## قرارداد رویدادها
| event | data |
|---|---|
| `start` | `{"conversation_id": "<uuid>", "title": "<str>"}` |
| `status` | `{"status": "generating|searching|reading_documents|querying_database", "tool"?: str, "args"?: {...}}` |
| `delta` | `{"content": "<تکه متن>"}` |
| `artifact` | `{"artifact": {…sql_result…}}` (شکل در [../reference/api-endpoints.md](../reference/api-endpoints.md)) |
| `done` | `{"sources": [SourceCitation], "artifacts": [...], "message_id": "<uuid>"}` |
فرمت فریم: `event: <name>\ndata: <json>\n\n` (`json.dumps` پیش‌فرض: `ensure_ascii=True`).

## session
`stream_chat_response` **session خودش** را با `async_session_factory()` باز می‌کند (به‌خاطر بسته‌شدن session وابستگی درخواست قبل از شروع body در FastAPI < 0.118). `UserContext` از endpoint می‌آید.

## بازیابی/RAG
در این مسیر **retrieval اجباری انجام نمی‌شود**؛ agent اگر لازم دید `search_knowledge_base` را صدا می‌زند. scope: اسناد خود گفتگو + پروژه‌ی متصل‌شده (اگر `linked_project_id` و کاربر هنوز عضو). اتصال پروژه: `PATCH /chat/conversations/{id}` با `linked_project_id` (الزامی اما nullable؛ `null` = جداکردن).

## مدیریت گفتگو
| endpoint | کار |
|---|---|
| `POST /chat/conversations` | ساخت (`type`, `project_id` برای group, `linked_project_id` برای personal, `title?`) — اعتبارسنجی با `model_validator` |
| `GET /chat/conversations` | گفتگوهای خودم + گروه‌های پروژه‌های عضو (`created_by==me OR project_id IN my_projects`)؛ ادمین چت شخصی دیگران را اینجا نمی‌بیند (فقط با id مستقیم) |
| `GET /chat/conversations/{id}` | جزئیات + همه‌ی پیام‌ها |
| `PATCH /chat/conversations/{id}` | `title` (هر نوع) و `linked_project_id` (فقط personal؛ برای group باید `null` فرستاد وگرنه 400) |
| `GET …/messages?after=<id>` | catch-up |
| `GET/POST …/documents[/batch]` | اسناد گفتگو |
حذف گفتگو/پیام API ندارد.
