# جریان: چت گروهی پروژه (REST + WebSocket + Redis pub/sub)

فایل‌ها: `features/chat/{router,service,ws,dependencies}.py`, `features/agent/engine.py`.

## اصل طراحی
- **ارسال از REST** (تا هر پیام قبل از پخش ذخیره شود)، **دریافت زنده از WebSocket** (سرور فقط event می‌فرستد؛ پیام‌های ورودی WS نادیده گرفته می‌شوند — حلقه فقط `receive_text()` می‌کند تا قطع اتصال را بفهمد).
- پخش از **Redis pub/sub** (کانال `conversation:<uuid>`)، پس چند instance از بک‌اند هم کار می‌کند.

## ساخت گفتگو
`POST /chat/conversations` با `{"type":"project_group","project_id":…}`: نیاز به عضویت پروژه یا leader تیم (یا admin). عنوان پیش‌فرض `New group conversation` (مستقل از نام پروژه، قابل ویرایش). چند گروه برای یک پروژه ممکن است (محدودیت یکتایی نیست).

## ارسال پیام
`POST /chat/conversations/{id}/messages` با `{content}` (فقط گروه؛ برای personal → 400):
1. `_auto_title_on_first_message` (عنوان placeholder → ۸۰ نویسه‌ی اول بدون `@bot`).
2. ذخیره‌ی `Message(user)` و commit.
3. `ws_manager.broadcast(conversation_id, {"event":"message","message":MessageRead})`.
4. اگر عنوان عوض شد: `{"event":"conversation_updated","conversation_id","title"}`.
5. اگر `content.strip().lower()` با `AI_TRIGGER_TOKEN.lower()` (پیش‌فرض `@bot`) شروع شود → `asyncio.create_task(_generate_group_ai_reply(conversation.id, context, message.id))` و پاسخ HTTP همان پیام کاربر است (پاسخ AI در پس‌زمینه).

## پاسخ AI (`_generate_group_ai_reply`)
- session جدا (`async_session_factory`) چون request تمام شده؛ `UserContext` همان request است (فقط فیلدهای scalar استفاده می‌شود).
- ابتدا `{"event":"assistant_start","reply_to_message_id"}`.
- engine با callback:
  - `agent_activity` → `{"event":"assistant_status","reply_to_message_id", status, tool?, args?}`
  - `delta` → `{"event":"assistant_delta","reply_to_message_id","delta"}`
  - `artifact` → **جمع می‌شود و فقط با پیام نهایی** می‌آید (در گروه artifact زنده پخش نمی‌شود).
- پایان: استثنا → `_failed_turn_result`. ذخیره‌ی `Message(assistant, reply_to_message_id=trigger, sources, artifacts)` و broadcast `{"event":"message","message":…}` (پیام نهایی کامل).
- در گروه هر پیام کاربر برای مدل با نام فرستنده پیشوند می‌شود و scope RAG همیشه `conversation.project_id` است.
- ⚠️ ابزار مالی در گروه نیز فعال است و نتیجه برای **همه‌ی اعضا** پخش می‌شود (← known-issues).
- task پس‌زمینه ارجاع نگه‌داشته نشده (`create_task` بدون ذخیره)؛ در بازنشانی process از بین می‌رود و پیام assistant ذخیره نمی‌شود.

## WebSocket
`WS /api/v1/chat/conversations/{id}/ws?token=<access_token>`
1. باز کردن session موقت؛ `_authenticate_websocket` (خطا → close 1008).
2. گفتگو باید وجود داشته باشد؛ دسترسی: personal ← `created_by==me or admin`؛ group ← `is_project_member(project_id)` یا leader تیم پروژه. در غیر این صورت close 1008 (قبل از accept).
3. `ws_manager.connect`: **اول subscribe به Redis (`_ensure_listener` تا `ready`) و بعد `websocket.accept()`** — تا کلاینت بعد از دیدن اتصال باز، چیزی را از دست ندهد.
4. هر listener یک task `_listen` برای هر گفتگو دارد (نه برای هر سوکت)؛ پیام Redis به همه‌ی سوکت‌های محلی همان گفتگو `send_text` می‌شود (خطای ارسال بی‌صدا نادیده). با رفتن آخرین سوکت listener لغو و unsubscribe می‌شود.

### رویدادهای WS (JSON)
| event | داده |
|---|---|
| `message` | `{message: MessageRead}` — پیام کاربر یا پاسخ نهایی AI (شامل `sources`, `artifacts`) |
| `assistant_start` | `{reply_to_message_id}` |
| `assistant_status` | `{reply_to_message_id, status, tool?, args?}` |
| `assistant_delta` | `{reply_to_message_id, delta}` |
| `conversation_updated` | `{conversation_id, title}` |
| `document_status` | `{document_id, status, filename}` — از worker پس از ingestion سند همین گفتگو |

## reconnect و catch-up
کلاینت بعد از اتصال مجدد `GET /chat/conversations/{id}/messages?after=<آخرین message id>` را می‌زند. ترتیب با tuple `(created_at, id)` است (مقایسه‌ی `>` روی tuple) پس پیام‌های هم‌زمان جا نمی‌افتند/تکرار نمی‌شوند. اگر `after` ناشناخته باشد کل تاریخچه برمی‌گردد. تیکه‌های `assistant_delta` که در قطعی از دست رفته‌اند بازیابی نمی‌شوند؛ پیام نهایی `message` از catch-up می‌آید.

## کانال مشترک با worker
`document_status` در پروسه‌ی worker با `publish_event()` منتشر می‌شود (کلاینت Redis موقت)، چون `manager.broadcast` به event loop اولیه‌ی API وابسته است.

## تست
`tests/features/chat/test_group_chat.py`, `test_catch_up.py`, `test_auto_title.py`, `test_conversation_title_update.py`, `test_conversation_documents.py`. تست WebSocket واقعی با Redis زنده **نوشته نشده** (فقط منطق سرویس/REST و `ws_manager` در فیکسچر).
