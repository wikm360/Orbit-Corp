# ۰۳ — نقش‌ها و مدل دسترسی

این مهم‌ترین بخش برای تغییر ایمن است: داده‌ی سازمان (اسناد، چت‌ها، داده‌ی مالی) فقط با همین قواعد محافظت می‌شود.

## دو نوع نقش
**نقش سراسری** — `users.role` (`UserRole` در `features/auth/models.py`):
| مقدار | معنی |
|---|---|
| `super_admin` | بالاترین سطح. **اولین کاربر ثبت‌نام‌شده** خودکار این نقش را می‌گیرد (قفل `pg_advisory_xact_lock(7_204_001)` تا دو ثبت‌نام هم‌زمان هر دو ادمین نشوند). فقط او می‌تواند نقش دیگران را عوض کند. |
| `admin` | مدیر سازمان (CEO). به همه‌ی تیم‌ها/پروژه‌ها/گفتگوها (حتی چت شخصی دیگران) دسترسی دارد. |
| `user` | کاربر عادی؛ فقط به چیزهایی که اضافه شده. |

**نقش داخل تیم** — `team_memberships.role` (`TeamRole`): `leader` یا `member`. یک نفر می‌تواند در تیم A لیدر و در تیم B عضو ساده باشد. (مفهوم «Leader Team» در سند اولیه‌ی نیازمندی.)

سلسله‌مراتب سازمانی: `System Admin` ← `CEO(admin)` ← `Leader Team` ← `User`. «افراد باید توسط لیدر تیم به پروژه assign شوند و پروژه هم توسط لیدر ساخته می‌شود.»

## `UserContext` (`core/dependencies.py`)
در هر درخواست احراز‌هویت‌شده ساخته می‌شود (`get_current_user_context`) و شامل:
- `user`, `id`, `role`
- `team_ids` — همه‌ی تیم‌های کاربر (leader یا member)
- `led_team_ids` — تیم‌هایی که لیدرش است
- `project_ids` — `get_user_project_ids`: عضویت پروژه **join‌شده با عضویت تیمِ همان پروژه**؛ یعنی عضویت پروژه‌ای که کاربر دیگر عضو تیمش نیست نادیده گرفته می‌شود
- `is_admin` = `role in (SUPER_ADMIN, ADMIN)`
- `leads_team(team_id)` = `is_admin or team_id in led_team_ids`
- `is_project_member(project_id)` = `is_admin or project_id in project_ids`  ← ⚠️ **ادمین به‌طور خودکار عضو همه‌ی پروژه‌ها حساب می‌شود**

هزینه: هر درخواست ۳ query اضافه برای ساخت context (+ query خود کاربر).

## Dependencyها
| dependency | شرط | استثنا |
|---|---|---|
| `get_current_user` | Bearer JWT معتبر (HS256، `sub`=uuid) و کاربر **هنوز در DB وجود دارد** | 401 |
| `get_current_user_context` | بالا + ساخت `UserContext` | |
| `require_role(*roles)` | `user.role in roles` | 403 |
| `require_admin` / `require_super_admin` | admin+super / فقط super | 403 |
| `require_team_manager(team_id)` | `context.leads_team(team_id)` | 403 |
| `require_project_manager(project_id)` | لیدر تیمِ پروژه یا admin → خروجی `Project` | 404 اگر پروژه نباشد |
| `require_project_access(project_id)` | عضو پروژه، یا لیدر تیم پروژه، یا admin → خروجی `Project` | |
| `chat.dependencies.require_conversation_access` | شخصی: صاحب یا admin. گروهی: عضو پروژه (`is_project_member`) یا لیدر تیم پروژه | 403/404 |

نکات:
- نقش از **DB** در هر درخواست خوانده می‌شود (نه از claim `role` داخل JWT)، پس تغییر نقش فوراً اثر می‌کند. access token را نمی‌شود ابطال کرد (stateless)؛ فقط حذف کاربر از DB یا انقضا (۳۰ دقیقه).
- WebSocket دور از `Depends` است: `_authenticate_websocket` در `chat/router.py` همان منطق را دستی تکرار می‌کند (**اگر قاعده‌ی دسترسی عوض شد هر دو جا را عوض کنید**).

## ماتریس دسترسی (رفتار واقعی کد)
| کار | user عادی | عضو پروژه | leader همان تیم | admin | super_admin |
|---|:-:|:-:|:-:|:-:|:-:|
| ساخت تیم / لیست همه‌ی تیم‌ها | ✗ | ✗ | ✗ | ✓ | ✓ |
| دیدن اعضای تیم | ✗ (مگر عضو تیم) | عضو تیم ✓ | ✓ | ✓ | ✓ |
| افزودن/تغییر نقش **member** | ✗ | ✗ | ✓ (تیم خودش) | ✓ | ✓ |
| تعیین **leader** / حذف leader | ✗ | ✗ | ✗ | ✓ | ✓ |
| حذف member از تیم (+ قطع دسترسی پروژه‌های آن تیم) | ✗ | ✗ | ✓ | ✓ | ✓ |
| ساخت پروژه در تیم | ✗ | ✗ | ✓ | ✓ | ✓ |
| لیست پروژه‌های تیم | عضو تیم: فقط پروژه‌های خودش | | همه‌ی پروژه‌های تیم | همه | همه |
| افزودن/حذف عضو پروژه (فقط از اعضای همان تیم) | ✗ | ✗ | ✓ | ✓ | ✓ |
| دیدن پروژه / اعضا / اسناد / چت گروهی | ✗ | ✓ | ✓ | ✓ | ✓ |
| آپلود/retry/cancel/حذف/تغییر نام سند **پروژه** و همه‌ی عملیات فایل‌منیجر (پوشه، move/copy، آپلود آرشیو) | ✗ | ✗ | ✓ | ✓ | ✓ |
| دیدن درخت پوشه‌ها و جست‌وجوی نام فایل | ✗ | ✓ | ✓ | ✓ | ✓ |
| لیست/ساخت/ویرایش/حذف **حافظه‌ی پروژه** از REST | ✗ | ✗ | ✓ | ✓ | ✓ |
| آپلود سند داخل **گفتگو** | صاحب گفتگو | هر شرکت‌کننده‌ی گروه | ✓ | ✓ | ✓ |
| دیدن چت شخصی دیگران | ✗ | ✗ | ✗ | ✓ | ✓ |
| تغییر نقش سراسری | ✗ | ✗ | ✗ | ✗ | ✓ |
| `/admin/users`, `/admin/documents` | ✗ | ✗ | ✗ | ✓ | ✓ |
| `/accounting-db/queries`, `/queries/stats`, `/hints/ingest`, `/freshness` | ✗ | ✗ | ✗ | ✓ | ✓ |
| استفاده از ابزار مالی `ask_accounting_db` در چت | ✗ | ✗ | ✗ | ✓ | ✓ |

قواعد مهم:
1. دسترسی به **پروژه** فقط از راه `project_memberships` است و عضو پروژه باید عضو **تیمِ پروژه** هم باشد (در `add_project_member` چک می‌شود و در `get_user_project_ids` هم join است).
2. **حذف از تیم** در `access_control.service.remove_user_from_team` همه‌ی `project_memberships` کاربر در پروژه‌های آن تیم را هم پاک می‌کند.
3. سازنده‌ی پروژه خودکار عضو پروژه می‌شود.
4. تغییر نقش `leader→member` توسط leader دیگر ممکن است: `POST /teams/{id}/members` با `role=member` فقط `leads_team` می‌خواهد؛ فقط **ارتقا به leader** admin می‌خواهد. (رفتار فعلی؛ در صورت نیاز سخت‌گیری شود.)
5. endpoint حذف تیم/پروژه/کاربر وجود ندارد. تغییر نام تیم/پروژه هم نیست.

## تعیین «scope بازیابی» برای agent (`agent/scope.py`)
`resolve_retrieval_scope(context, conversation) -> project_id | None` تعیین می‌کند agent کدام **پایگاه دانش پروژه** را ببیند:
- گفتگوی `project_group` ← همیشه `conversation.project_id`
- گفتگوی `personal` ← `linked_project_id` اگر تنظیم شده **و کاربر هنوز عضو آن پروژه است** (هر بار دوباره چک می‌شود؛ ادمین همیشه عضو حساب می‌شود)؛ وگرنه `None`
علاوه بر پروژه، همیشه اسناد **خود گفتگو** (`conversation_id`) قابل‌دیدن‌اند.

## فیلتر دسترسی اسناد (`retrieval/access_filter.py`)
`accessible_documents_filter(project_id, conversation_id)`:
```
Document.status == READY  AND  ( Document.conversation_id == :conversation_id
                                  OR Document.project_id == :project_id   -- فقط اگر project_id داده شده )
```
- این فیلتر **داخل خود query برداری** اعمال می‌شود (نه بعد از آن) تا chunk غیرمجاز هرگز به LLM نرسد.
- `conversation_id` عمداً non-optional است: `== None` در SQLAlchemy به `IS NULL` تبدیل می‌شود و اسناد پروژه را بی‌قید باز می‌کرد.
- ابزارهای خواندن سند (`get_document_info`, `read_document_pages`, `read_entire_document`) از `_get_accessible_document` استفاده می‌کنند که همین فیلتر را روی یک سند اعمال می‌کند؛ پس مدل با حدس زدن UUID نمی‌تواند سند پروژه‌ی دیگر را بخواند (نتیجه: «Document not found or not accessible»).
- `uploaded_by` فقط metadata است و **هیچ‌وقت دسترسی نمی‌دهد**.

## اصل «ابزار به آرگومان مدل اعتماد نمی‌کند»
`BaseTool` مستند می‌کند که هر ابزار باید دسترسی را از `context` و `conversation` خودش دوباره بسنجد. مدل فقط *انتخاب* می‌کند کدام سند/پروژه، نه اینکه اجازه داشته باشد. `ToolRegistry.dispatch` هر `ForbiddenError` را به متن `Permission Denied` تبدیل می‌کند.

## WebSocket
- توکن در query string (`?token=`) — محدودیت مرورگر.
- بعد از handshake و چک دسترسی، اتصال باز می‌ماند؛ **حذف کاربر از پروژه اتصال باز را قطع نمی‌کند** (فقط اتصال‌های جدید رد می‌شوند). ← [known-issues.md](known-issues.md)
- گفتگوی شخصی هم WS دارد (فقط برای event `document_status`): مجاز برای صاحب یا admin.

## فهرست «کجا چه چیزی چک می‌شود» (برای بازبینی/تغییر)
| مکان | چک |
|---|---|
| `core/dependencies.py` | همه‌ی dependencyهای بالا |
| `access_control/router.py` | قواعد leader/member داخل خود handlerها (نه dependency) |
| `projects/service.add_project_member` | عضو تیم بودن کاربر هدف |
| `projects/router.list_team_projects` | فیلتر پروژه‌های قابل‌دیدن عضو ساده |
| `chat/service.create_conversation` / `update_conversation` | عضویت پروژه برای group/link |
| `chat/service.get_or_create_personal_conversation` | `conversation.created_by == context.id` (وگرنه **بی‌صدا گفتگوی جدید می‌سازد**) |
| `chat/router.conversation_websocket` | احراز و دسترسی WS |
| `documents/router.py` | `require_project_access` / `require_project_manager`؛ بررسی `document.project_id == project.id` در retry/delete/cancel. فایل‌منیجر: `folder_service.get_folder` و `file_ops.resolve_selection` هر پوشه/سند را با `project_id` تطبیق می‌دهند (آیتم پروژه‌ی دیگر = 404). پوشه هرگز مرز دسترسی نیست؛ `accessible_documents_filter` دست‌نخورده است |
| `memory/router.py` | `require_project_manager` + `memory.project_id == project.id` |
| `db_connector/router._get_owned_log` | صاحب log یا admin (برای feedback/export) |
| `agent/tools/*` | `resolve_retrieval_scope` + فیلتر اسناد |
