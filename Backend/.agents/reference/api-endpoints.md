# مرجع API

پیشوند همه‌ی endpointها: `/api/v1` (`API_PREFIX`) مگر `GET /health`. احراز هویت: هدر `Authorization: Bearer <access_token>` مگر ذکر شده. خطاها: `400` درخواست نامعتبر، `401` احراز هویت، `403` دسترسی، `404` یافت نشد، `409` تکراری، `422` اعتبارسنجی pydantic. بدنه‌ی خطا: `{"detail": "..."}`.
مستندات تعاملی Swagger روی `/docs` (در پروداکشن توسط Caddy مسدود).
منطق دسترسی هر مورد: [../03-access-control.md](../03-access-control.md).

## Auth (عمومی مگر `me`)
| متد/مسیر | بدنه | پاسخ |
|---|---|---|
| `POST /auth/register` | `{email, password(8..72), full_name?}` | `TokenResponse` |
| `POST /auth/login` | `{email, password}` | `TokenResponse` |
| `POST /auth/refresh` | `{refresh_token}` | `TokenResponse` (rotation) |
| `POST /auth/logout` | `{refresh_token}` | 204 |
| `GET /auth/me` | — | `UserRead{id,email,full_name,role,created_at}` |
`TokenResponse = {access_token, refresh_token, token_type:"bearer", user}`.

## Teams / Projects
| endpoint | دسترسی | نکته |
|---|---|---|
| `POST /teams` `{name, description?}` · `GET /teams` | admin | |
| `GET /teams/mine` | لاگین | |
| `GET /teams/{id}/members` | عضو تیم/admin | `[{user, role}]` |
| `POST /teams/{id}/members` `{user_id, role=member}` | leader/admin (leader شدن: admin) | 204، upsert |
| `DELETE /teams/{id}/members/{user}` | leader/admin (حذف leader: admin) | 204، عضویت پروژه‌ها هم پاک |
| `POST /teams/{id}/projects` `{name, description?}` | leader/admin | `ProjectRead{id,team_id,name,description}` |
| `GET /teams/{id}/projects` | عضو تیم/admin | فیلتر برای member |
| `GET /projects/mine` · `GET /projects/{id}` | لاگین / عضو پروژه | |
| `GET /projects/{id}/members` | عضو پروژه | `[{user}]` |
| `POST /projects/{id}/members` `{user_id}` · `DELETE …/{user}` | manager | 204 |

## Documents
| endpoint | دسترسی |
|---|---|
| `GET /projects/{id}/documents` | عضو پروژه (لیست تخت همه‌ی اسناد) |
| `POST /projects/{id}/documents` (multipart `file` + اختیاری `folder_id`) | manager |
| `POST /projects/{id}/documents/batch` (multipart `files[]` ≤۲۰ + اختیاری `folder_id`) | manager |
| `POST /projects/{id}/documents/{doc}/retry` | manager (`failed`/`cancelled`/`unsupported` که حالا پشتیبانی می‌شود) |
| `POST /projects/{id}/documents/{doc}/cancel` | manager (فقط `processing`) |
| `PATCH /projects/{id}/documents/{doc}` `{filename}` (تغییر نام؛ 409 اگر نام در همان پوشه هست) | manager |
| `DELETE /projects/{id}/documents/{doc}` | manager (204) |
`DocumentRead{id,filename,content_type,status:processing|ready|failed|cancelled|unsupported,error_message,project_id,conversation_id,folder_id,uploaded_by,created_at}`.
آپلود پروژه: فایل با نوع بدون parser رد نمی‌شود، با `status=unsupported` نگه داشته می‌شود؛ نام نسبی (`a/b/c.pdf`، آپلود پوشه‌ی مرورگر) پوشه می‌سازد؛ نام تکراری در همان پوشه `name (1).ext` می‌شود؛ `.zip/.rar/.7z` به‌جای `document` یک `archive` (`ArchiveImportRead`) برمی‌گرداند که worker داخل `folder_id` باز می‌کند. پاسخ تک‌فایل: `{document|null, archive|null, message}`؛ آیتم batch: `{filename,status,document,archive,error}`.

### File manager (فقط scope پروژه؛ دسترسی همان دسترسی پروژه است، پوشه دسترسی را محدود نمی‌کند)
| endpoint | دسترسی |
|---|---|
| `GET /projects/{id}/files?folder_id=` (بدون `folder_id` = ریشه) | عضو پروژه |
| `GET /projects/{id}/files/search?q=` (نام فایل، با مسیر پوشه) | عضو پروژه |
| `POST /projects/{id}/folders` `{name,parent_id?}` (201؛ 409 نام تکراری) | manager |
| `PATCH /projects/{id}/folders/{folder}` `{name}` | manager |
| `POST /projects/{id}/files/move` `{document_ids,folder_ids,target_folder_id,on_conflict}` | manager |
| `POST /projects/{id}/files/copy` (همان بدنه؛ پوشه‌ها بازگشتی) | manager |
| `POST /projects/{id}/files/delete` `{document_ids,folder_ids}` | manager |
| `POST /projects/{id}/files/retry` · `/files/cancel` `{document_ids,folder_ids}` | manager |
| `DELETE /projects/{id}/archives/{archive}` (حذف رکورد آرشیو تمام‌شده/ناموفق؛ 400 اگر هنوز در حال باز شدن) | manager (204) |
`FolderListing{folder_id,breadcrumb[FolderRead],folders[{folder,status_counts{status:n} (بازگشتی روی زیرشاخه‌ها)}],documents[DocumentRead],archives[ArchiveImportRead]}`؛ `ArchiveImportRead{id,folder_id,filename,status:extracting|done|failed,error_message,total_files,imported_files,skipped_files,failed_files[{path,error}],created_at,finished_at}`. `BulkResult{count,skipped}`.
`on_conflict`: `fail` (پیش‌فرض) ← 409 بدون هیچ تغییری؛ `rename` ← `name (n)`. مقصد `null` = ریشه. انتقال پوشه به داخل خودش/زیرشاخه‌اش 400. آیتم پروژه‌ی دیگر 404. move فقط `folder_id`/`filename` را عوض می‌کند (بدون پردازش مجدد)؛ copy سند READY را با کپی chunk بدون OCR/embedding می‌سازد.

## Memory (manager)
`GET|POST /projects/{id}/memories` · `PATCH|DELETE /projects/{id}/memories/{mid}`. `ProjectMemoryRead{id,project_id,created_by_user_id,fact_text,category,confidence_score,is_verified,created_at,updated_at}`.

## Chat
| endpoint | کار |
|---|---|
| `POST /chat` `{message, conversation_id?}` | چت شخصی، پاسخ SSE ([../flows/chat-personal-sse.md](../flows/chat-personal-sse.md)) |
| `POST /chat/conversations` · `GET /chat/conversations` | ساخت / لیست |
| `GET /chat/conversations/{id}` | `ConversationDetail` (با `messages`) |
| `PATCH /chat/conversations/{id}` `{linked_project_id (الزامی, nullable), title?}` | |
| `GET /chat/conversations/{id}/messages?after=<uuid>` | catch-up |
| `POST /chat/conversations/{id}/messages` `{content}` | پیام گروهی (فقط group) |
| `GET /chat/conversations/{id}/documents` | وضعیت اسناد گفتگو |
| `POST /chat/conversations/{id}/documents` · `/documents/batch` | آپلود سند گفتگو |
| `WS /chat/conversations/{id}/ws?token=<access>` | رویدادهای زنده |
`MessageRead{id,sender_type,sender_id,content,sources:[SourceCitation],artifacts:[dict],reply_to_message_id,created_at}`.
`SourceCitation{document_id,document_filename,chunk_index,snippet,score,page?}`.

### رویدادهای SSE (`POST /chat`)
`start{conversation_id,title}` · `status{status,tool?,args?}` · `delta{content}` · `artifact{artifact}` · `done{sources,artifacts,message_id}`.

### رویدادهای WebSocket
`message{message}` · `assistant_start{reply_to_message_id}` · `assistant_status{reply_to_message_id,status,tool?,args?}` · `assistant_delta{reply_to_message_id,delta}` · `conversation_updated{conversation_id,title}` · `document_status{document_id,status,filename}`.
جزئیات: [../flows/chat-group-ws.md](../flows/chat-group-ws.md).

### artifact: `sql_result` (نسخه ۱)
```json
{
  "type": "sql_result", "version": 1,
  "query_id": "<uuid db_query_logs>", "question": "…", "sql": "SELECT …",
  "columns": [{"name": "fiscal_year", "kind": "text"}, {"name": "net_pay", "kind": "money"}],
  "rows": [[1404, 123456789]],
  "row_count": 1234, "rows_fetched": 500, "rows_shown": 100, "total_exact": true,
  "truncated": true, "duration_ms": 820, "executed_at": "2026-10-10T08:00:00+00:00",
  "data_as_of": {"<کلید فارسی ai.data_freshness>": "<مقدار>"}, "currency": "IRR"
}
```
`kind ∈ money|ratio|number|date|text` (تعیین نحوه‌ی فرمت در کلاینت). `row_count` تعداد کل واقعی نتیجه است وقتی `total_exact`.

## Accounting DB (`/accounting-db`)
| endpoint | دسترسی |
|---|---|
| `POST /queries/{id}/feedback` `{feedback:-1..1, note?}` | صاحب log / admin |
| `GET /queries/{id}/export?format=xlsx\|csv` | صاحب log / admin |
| `GET /queries?limit&offset&status` · `GET /queries/stats` · `POST /hints/ingest` | admin |
| `GET /freshness` | هر کاربر لاگین |
`DbQueryStats{total_queries,successful_queries,rejected_queries,error_queries,positive_feedback,negative_feedback,avg_duration_ms}`؛ `IngestResponse{total,unchanged,embedded,stored_without_embedding,deleted}`.

## Admin (`require_admin`)
`GET /admin/users` · `POST /admin/users` · `PATCH /admin/users/{id}/role` `{role}` (super_admin) · `GET /admin/documents` (همه‌ی اسناد).
داشبورد بازرس دیداری و متنی: `/db-admin/ocr-inspector` و `/admin/ocr-inspector` شامل:
- بازرسی دیداری OCR و برش‌ها (`/api/v1/admin/ocr-debug/*`)
- بازرسی متنی اسناد و صفحات، تصویر رندرشده صفحه و پردازش مجدد با OCR (`/api/v1/admin/documents-inspect/list`، `GET /documents-inspect/{id}`، `GET /documents-inspect/{id}/page-image/{page}`، `POST /documents-inspect/{id}/reprocess`)
- راهنمای لاگ‌های زنده Agent و RAG

## پنل مدیریت دیتابیس (SQLAdmin)
مسیر `/db-admin`: پنل تعاملی وب برای مشاهده و مدیریت کامل جداول دیتابیس (مشابه Django Admin برای Users, Teams, Projects, Documents, Chunks, Messages, Conversations, QueryLogs, SchemaHints).
احراز هویت: مبتنی بر Session با ایمیل و رمز عبور؛ منحصراً برای نقش‌های `super_admin` و `admin` (CEO).

## سلامت
`GET /health` → `{"status":"ok"}` (بدون احراز؛ خارج از `/api/v1`؛ healthcheck کانتینر از آن استفاده می‌کند).

## ناسازگاری‌های شناخته‌شده‌ی قرارداد
- فرانت قبلاً با مسیرهای قدیمی (`/documents`, `/admin/teams`, `sender_type` جدید, refresh token, چت گروهی) هماهنگ نبود؛ وضعیت فعلی هماهنگی را در `../Frontend` بررسی کنید (نیاز به تأیید).
- وضعیت `agent_activity.status = querying_database` را کلاینت باید بشناسد.
