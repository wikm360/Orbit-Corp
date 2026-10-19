# جریان: تیم، پروژه و عضویت

فایل‌ها: `features/access_control/{models,service,router}.py` (تیم)، `features/projects/{models,service,router}.py`، `core/dependencies.py`.
مرجع قواعد: [../03-access-control.md](../03-access-control.md).

## مدل ذهنی
```
Team ──< TeamMembership(user, role=leader|member)
Team ──< Project ──< ProjectMembership(user)        (کاربر پروژه باید عضو تیم هم باشد)
Project ──< Document (پایگاه دانش) , Conversation(project_group) , ProjectMemory
```
هر پروژه دقیقاً به یک تیم تعلق دارد. اعضای ساده‌ی تیم فقط پروژه‌هایی را می‌بینند که به آن‌ها اضافه شده‌اند؛ leader و admin همه‌ی پروژه‌های تیم را.

## قدم‌ها (روند عادی سازمان)
1. **admin** تیم می‌سازد: `POST /teams` (نام یکتا؛ تکراری 409).
2. **admin** leader تعیین می‌کند: `POST /teams/{id}/members` با `{user_id, role:"leader"}`. (`add_user_to_team` هم upsert است: اگر عضو بود فقط `role` عوض می‌شود.)
3. **leader** اعضای ساده اضافه می‌کند (`role:"member"`).
4. **leader** پروژه می‌سازد: `POST /teams/{team_id}/projects` (`require_team_manager`؛ نام داخل تیم یکتا، 409). سازنده خودکار `ProjectMembership` می‌گیرد (دو commit جدا: اول پروژه، بعد عضویت).
5. **leader** اعضای پروژه را از میان اعضای تیم اضافه می‌کند: `POST /projects/{id}/members` (`require_project_manager`). اگر کاربر عضو تیم نباشد → 400 «The user must belong to the project's team…». اضافه‌ی تکراری idempotent است.
6. **leader** اسناد پروژه را آپلود می‌کند ← [document-ingestion.md](document-ingestion.md).
7. اعضا چت گروهی پروژه را می‌سازند/باز می‌کنند ← [chat-group-ws.md](chat-group-ws.md).

## حذف عضو از تیم
`DELETE /teams/{team_id}/members/{user_id}` (204):
- باید `leads_team(team_id)`؛ اگر هدف leader است فقط admin.
- `remove_user_from_team` رکورد عضویت تیم را پاک می‌کند **و** همه‌ی `project_memberships` همان کاربر را در پروژه‌های آن تیم حذف می‌کند (یک commit).
- نتیجه: دسترسی به اسناد و چت گروهی آن پروژه‌ها از درخواست بعدی قطع است. (سوکت WS باز می‌ماند؛ ← known-issues.)
- گفتگوهای شخصی خود کاربر که `linked_project_id` به آن پروژه دارد باقی می‌مانند ولی `resolve_retrieval_scope` دیگر پروژه را نشان نمی‌دهد چون عضویت دوباره چک می‌شود.

## حذف عضو از پروژه
`DELETE /projects/{id}/members/{user_id}` — فقط manager؛ 404 اگر عضو نبود. عضویت تیم دست‌نخورده.

## لیست‌ها
| endpoint | رفتار |
|---|---|
| `GET /teams` | admin: همه |
| `GET /teams/mine` | تیم‌های خود کاربر |
| `GET /teams/{id}/members` | عضو تیم یا admin؛ خروجی `[{user, role}]` |
| `GET /teams/{id}/projects` | عضو تیم یا admin؛ leader/admin همه، member فقط پروژه‌های خودش |
| `GET /projects/mine` | `list_user_projects`: join روی عضویت پروژه **و** عضویت تیم. ⚠️ ادمینی که صراحتاً عضو پروژه نیست در این لیست نمی‌آید (ولی به آن دسترسی دارد) |
| `GET /projects/{id}`, `/members` | `require_project_access` |

## نکات پیاده‌سازی
- `add_user_to_team`/`add_project_member` فقط وجود user/team را چک می‌کنند؛ تیم/پروژه‌ی ناموجود = 404.
- `Team` و `Project` هیچ فیلد وضعیت/soft-delete ندارند؛ حذف cascade دیتابیسی فقط از راه SQL دستی ممکن است (حذف تیم ← پروژه‌ها ← اسناد/گفتگوها/حافظه).
- ساخت گفتگوی گروهی نیاز به عضویت پروژه یا leader بودن دارد (`chat.service.create_conversation`).
