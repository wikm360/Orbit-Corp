# راهنما: افزودن endpoint یا feature جدید

## endpoint در feature موجود
1. **schema** (pydantic) در `schemas.py` (یا بالای `router.py` اگر feature همین سبک را دارد). برای خروجی از ORM: `model_config = ConfigDict(from_attributes=True)`.
2. **منطق** در `service.py` به‌صورت `async def fn(db: AsyncSession, …)`؛ commit در service؛ خطا با `core.exceptions`.
3. **router**: `@router.<method>(path, response_model=…)`، dependency دسترسی مناسب:
   - هر کاربر لاگین: `Depends(get_current_user_context)`
   - فقط admin: `dependencies=[Depends(require_admin)]`
   - مدیر تیم/پروژه: `require_team_manager` / `require_project_manager`
   - خواندن پروژه: `require_project_access`
   - گفتگو: `chat.dependencies.require_conversation_access`
4. اگر منبع وابسته به پارامتر مسیر است، **مالکیت را چک کنید** (مثل `document.project_id == project.id`).
5. تست در `tests/features/<feature>/` شامل مسیر موفق و دسترسی منفی.
6. مستند: ردیف در [../reference/api-endpoints.md](../reference/api-endpoints.md)، ماتریس دسترسی در [../03-access-control.md](../03-access-control.md) اگر قاعده‌ی جدید است.

## feature جدید
1. پوشه `app/features/<name>/` با `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`.
2. مدل را در `app/core/model_registry.py` import کنید (`from app.features.<name> import models as _<name>_models  # noqa: F401`).
3. migration جدید ← [add-migration.md](add-migration.md).
4. router را در `app/main.py` با `app.include_router(<router>, prefix=settings.api_prefix)` ثبت کنید.
5. اگر agent باید از آن استفاده کند ← [add-agent-tool.md](add-agent-tool.md).
6. فایل `reference/modules.md` و [../04-data-model.md](../04-data-model.md) را به‌روز کنید.

## SSE یا WebSocket جدید
- SSE: `StreamingResponse(media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})`. generator باید **session خودش** را باز کند (نه `Depends(get_db)`).
- رویداد WS جدید: با `ws_manager.broadcast(conversation_id, {"event": "...", ...})` (API) یا `publish_event` (worker/خارج از loop اصلی). قرارداد را در [../flows/chat-group-ws.md](../flows/chat-group-ws.md) و `api-endpoints.md` ثبت کنید و فرانت را هماهنگ کنید.
