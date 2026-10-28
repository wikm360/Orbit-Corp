# تست

چارچوب: `pytest` + `pytest-asyncio` (`pytest.ini`: `asyncio_mode = auto`). آخرین اجرای کامل (۱۹ اکتبر ۲۰۲۶، پس از افزودن hybrid): **۱۸۹ تست پاس** با Postgres(pgvector+pg_trgm) و Redis زنده.

## اجرا
```bash
docker compose up -d postgres redis        # Postgres با pgvector لازم است (SQLite کار نمی‌کند)
pytest                                     # همه
pytest tests/features/db_connector -q      # یک پوشه
pytest -k refresh_tokens
```
- DB تست: `TEST_DATABASE_URL` یا `<نام DB در DATABASE_URL>_test` روی همان سرور؛ در شروع session اگر نبود با اتصال به `postgres` ساخته می‌شود. در dev compose، Postgres پورت میزبان ندارد؛ برای تست روی میزبان باید پورت را موقتاً منتشر کنید یا داخل شبکه‌ی docker اجرا کنید (نیاز به تأیید روش مورد استفاده‌ی تیم).
- افزونه‌ی `pg_trgm` لازم است (conftest آن را می‌سازد؛ در image `pgvector/pgvector` موجود است).
- Redis هم لازم است (`ws_manager` در import یک کلاینت می‌سازد و فیکسچر pool آن را می‌بندد؛ `Queue` در `documents.service` هنگام import ساخته می‌شود؛ اتصال lazy است ولی آپلودی که job صف می‌کند Redis زنده می‌خواهد).
- محافظ: `_assert_test_database()` اگر نام DB با `_test` تمام نشود **از ریست schema خودداری می‌کند**.

## `tests/conftest.py` — فیکسچرها
- قبل از import اپ، `DATABASE_URL` env را به DB تست تغییر می‌دهد (چون engine در import ساخته می‌شود).
- `_reset_schema` (autouse): برای **هر تست** `DROP SCHEMA public CASCADE` → `CREATE SCHEMA` → `CREATE EXTENSION vector` + `pg_trgm` → `Base.metadata.create_all`. بعد از تست engine و pool Redis بسته می‌شود (هر تست loop جدا دارد).
- `_stub_providers` (autouse): `get_llm_provider` (engine) → `_StubLLMProvider` (می‌گوید `Hello, world!`، بدون tool-call)، `get_embedding_provider` در document_tools/memory/hints → بردار صفر، `get_sql_llm_provider` → stub. **هیچ تستی به LLM/Embedding/SQL Server واقعی نمی‌رود.**
- `db_session` (session مستقیم) و `client` (`httpx.AsyncClient` با `ASGITransport(app)` و override `get_db`).

## نقشه‌ی تست‌ها
| پوشه | تمرکز | تعداد تقریبی |
|---|---|--:|
| `tests/core` | `test_request_logging` | 2 |
| `tests/providers` | LLM (stream, tool-call تجمیع, strip tag, retry) / embedding (retry, ترتیب) | 7 |
| `tests/test_migrations.py` | `alembic upgrade head` == `Base.metadata` (نام جدول/ستون) | 1 |
| `features/auth` | ثبت‌نام/لاگین/اولین کاربر، rotation و reuse refresh token | 10 |
| `features/access_control` | تیم/پروژه/leader/قطع دسترسی | 5 |
| `features/chat` | چت شخصی SSE، گروه، catch-up، عنوان خودکار، tool-calling، اسناد گفتگو | 16 |
| `features/agent` | حلقه‌ی engine، سقف گام، dedup | 3 |
| `features/documents` | آپلود/dedup/batch/retry، فایل‌منیجر (`test_file_manager`: پوشه، move/copy/delete، cancel/retry دسته‌ای، دسترسی 403/404)، آرشیو (`test_archive_import`: zip/7z، zip-slip، سقف‌ها، نام فارسی، تو در تو)، لغو حین پردازش (`test_ingestion_cancellation`)، parser، OCR/صفحه، تشخیص و اصلاح لایه‌ی متنی خراب PDF (`test_text_layer`)، re-embed (`test_reembed`)، خواندن ساخت‌یافته و `get_document_info`، ایزولاسیون scope، اعلان | ~110 |
| `features/memory` | سرویس و REST | 6 |
| `features/retrieval` | hybrid (RRF، normalize، match دقیق/trigram، scope) و re-rank LLM (`test_rerank`: ترتیب، [] ، fallback، timeout) | 18 |
| `features/db_connector` | validator، generator، hints، lexical، summary، formatter، artifacts، service، tool، router | 41 |

## الگوهای تست
- **Engine را با provider اسکریپت‌شده تست کنید** (`_ScriptedLLMProvider(steps)` که برای هر `stream_chat` لیست event برمی‌گرداند) به‌جای mock کردن OpenAI.
- stub مالی: `monkeypatch.setattr("app.features.db_connector.service.execute_query", fake)` (و `…summary.execute_query` برای totals/discovery).
- برای ingestion پایپ‌لاین مستقیماً `run_ingestion_pipeline` یا stepها با embedding stub استفاده می‌شود؛ صف RQ واقعی لازم نیست مگر آپلود (Redis در دسترس باشد).
- برای هر قاعده‌ی دسترسی جدید تست «کاربر غیرمجاز 403/404» بنویسید (الگو: `tests/features/documents/test_document_scope_isolation.py`).

## شکاف‌های پوشش
- **تست WebSocket واقعی** (با Redis و اتصال زنده) وجود ندارد؛ `ws_manager` فقط در فیکسچر مصرف شده.
- هیچ تستی علیه SQL Server واقعی نیست (executor/`apply.py`/`refresh.py` فقط دستی یا با `examples/run.py`).
- فرانت-بک end-to-end ندارد.
- تست rate limit/قفل حساب/ماسک PII (چون پیاده نشده‌اند).
