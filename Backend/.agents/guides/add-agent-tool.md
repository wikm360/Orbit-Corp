# راهنما: افزودن ابزار به agent

مرجع ابزارهای موجود: [../reference/agent-tools.md](../reference/agent-tools.md). جریان: [../flows/agent-turn.md](../flows/agent-turn.md).

## قدم‌ها
1. کلاس جدید در `app/features/agent/tools/<x>_tools.py`:
   ```python
   class MyTool(BaseTool):
       name = "my_tool"
       description = "یک یا دو جمله: چه می‌کند، کِی استفاده شود، کِی نه."   # مدل بر اساس همین تصمیم می‌گیرد
       parameters = {"type": "object", "properties": {"x": {"type": "string", "description": "…"}}, "required": ["x"]}

       async def execute(self, *, db, context, conversation, x: str, **_: Any) -> ToolExecutionResult:
           project_id = resolve_retrieval_scope(context, conversation)   # دسترسی را خودتان بسنجید
           ...
           return ToolExecutionResult(text="…", citations=[…], artifacts=[…])
   ```
2. ثبت در `registry.build_default_registry()` (شرطی اگر feature flag دارد، مثل `rahkaran_db_enabled`).
3. اگر برچسب فعالیت خاص می‌خواهید: `engine.py` دو جا — مجموعه‌ی `_DOCUMENT_READ_TOOLS` یا شاخه‌ی `status` در حلقه (`querying_database`). status جدید را به فرانت اطلاع دهید.
4. اگر مدل باید از ابزار خبر داشته باشد (مثل بخش مالی)، متن system prompt در `engine._build_messages` را به‌روز کنید.
5. تست: با `_ScriptedLLMProvider` یک turn که ابزار را صدا می‌زند؛ تست دسترسی (گفتگوی بدون پروژه، پروژه‌ی دیگر، کاربر غیرعضو).
6. مستند: جدول `agent-tools.md`.

## قواعد
- **به آرگومان مدل اعتماد نکنید**؛ id‌ها را با فیلتر scope بگیرید (`_get_accessible_document` الگو است).
- خطاهای قابل‌انتظار را با `NotFoundError/BadRequestError/ForbiddenError` بالا بدهید؛ registry آن‌ها را متن می‌کند. استثنای ناشناخته → پیام عمومی و لاگ.
- خروجی متنی کوتاه و ساخت‌یافته (JSON با `ensure_ascii=False` برای داده)، سقف برای متن‌های بزرگ.
- ابزار نباید commit ناخواسته یا اثر جانبی غیرقابل‌برگشت داشته باشد مگر کاربر صریح خواسته (مثل `remember_project_insight`: در توضیح هم نوشته شده).
- `**_: Any` را نگه دارید تا آرگومان اضافی مدل باعث `TypeError` نشود (اگرچه registry TypeError را هم به متن تبدیل می‌کند).
- برای کار سنگین sync از `asyncio.to_thread` استفاده کنید.
- اگر artifact برمی‌گردانید باید JSON-safe و دارای `type`/`version` باشد و کلاینت برایش renderer داشته باشد.
