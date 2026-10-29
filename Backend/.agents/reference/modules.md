# نقشه‌ی ماژول‌ها (فایل‌به‌فایل)

برای هر فایل: چه می‌کند، توابع/کلاس‌های کلیدی، چه کسی صدایش می‌زند. (اندازه‌ها تقریبی.)

## `app/main.py`، `workers/`
| فایل | کار |
|---|---|
| `app/main.py` | ساخت app، middleware، روترها، `/health` |
| `workers/ingestion_worker.py` | `rq.Worker` روی صف `ingestion`؛ `python -m workers.ingestion_worker` |

## `app/core/`
| فایل | کلیدها |
|---|---|
| `config.py` | `Settings`, `get_settings()`، validator `_parse_str_list` برای `CORS_ORIGINS` و `LLM_STRIP_CONTENT_TAGS` (CSV یا JSON؛ با `NoDecode`) |
| `database.py` | `engine`, `async_session_factory` (`expire_on_commit=False`), `Base`, `get_db` |
| `dependencies.py` | `UserContext`, `get_current_user[_context]`, `require_role/admin/super_admin`, `require_team_manager`, `require_project_manager`, `require_project_access` |
| `security.py` | `hash_password/verify_password` (bcrypt), `create_access_token/decode_access_token`, `generate_refresh_token`, `hash_token`, `refresh_token_expiry` |
| `text_normalization.py` | `normalize`, `words`, `STOPWORDS` — نرمال‌سازی فارسی مشترک بین BM25 hint ها و جست‌وجوی واژگانی اسناد (یک تعریف) |
| `exceptions.py` | `NotFoundError, ForbiddenError, UnauthorizedError(+WWW-Authenticate), ConflictError, BadRequestError` |
| `model_registry.py` | import مدل‌ها (access_control, auth, chat, db_connector, documents, memory, projects) |
| `request_logging.py` | `RequestResponseLoggingMiddleware`, `configure_request_logger` |

## `app/providers/`
`llm_provider.py` (`LLMProvider`, `OpenAICompatibleLLMProvider`, `get_llm_provider`, `get_sql_llm_provider`, `_strip_tag_blocks`, تایپ‌ها `ChatMessage/ToolCall/StreamEvent`) · `embedding_provider.py` (`EmbeddingProvider`, `BGEM3EmbeddingProvider`, `get_embedding_provider`).

## `app/features/`
### auth
`models.py` (User, UserRole, RefreshToken) · `schemas.py` · `service.py` (`register_user`, `login_user`, `refresh_tokens`, `logout_user`, `_issue_tokens`) · `router.py`.
### access_control (تیم)
`models.py` (Team, TeamMembership, TeamRole) · `service.py` (`get_user_team_roles`, `get_user_team_ids`, `get_user_led_team_ids`, `is_team_member`, `list_teams`, `get_user_teams`, `create_team`, `list_team_members`, `add_user_to_team`, `remove_user_from_team`) · `router.py` (schemaها داخل router).
### projects
`models.py` (Project, ProjectMembership) · `service.py` (`get_project`, `list_team_projects`, `list_user_projects`, `get_user_project_ids`, `is_project_member`, `create_project`, `list/add/remove_project_member`) · `router.py`.
### admin
`router.py` (همه‌ی روت‌ها پشت `require_admin`) · `service.py` (`list_users`, `set_user_role`, `list_all_documents`).
### documents
| فایل | کار |
|---|---|
| `models.py` | Document, DocumentChunk, DocumentStatus, DocumentFolder, ArchiveImport(+Status), OcrCache |
| `folder_service.py` · `file_ops.py` | فایل‌منیجر: درخت پوشه، نام‌گذاری، لیست/جست‌وجو؛ آپلود پروژه، move/copy/delete/retry/cancel دسته‌ای |
| `archive_service.py` | آپلود و استخراج `.zip/.rar/.7z` در worker (محافظ‌های zip-slip/bomb، فیلتر زباله) |
| `cancellation.py` | لغو هم‌کارانه‌ی ingestion (کلید Redis + `IngestionCancelled`) |
| `schemas.py` | DocumentRead, DocumentUploadResponse, BatchUpload* |
| `router.py` | endpointهای پروژه‌ای (list/upload/batch/retry/delete) |
| `service.py` (531 خط) | آپلود و dedup، enqueue، batch، retry، delete؛ و خواندن ساخت‌یافته برای agent (info/page-range/full) |
| `spreadsheet.py` | مدل جدول شیت: `read_xlsx_tables`/`read_csv_tables`، `load_tables` (با cache کنار فایل `<file>.tables.json`، پاک‌شدن با حذف سند)، `normalize_text` (ي→ی، ك→ک، ارقام فارسی/عربی، نیم‌فاصله)، `record_pages` (متن ingestion)، `describe_tables`، `run_query` (sandbox SQLite فقط‌خواندنی) |
| `chunk_paths.py` | مسیر سند روی chunkها (`path` در metadata + پیشوند `search_text`): `path_for_new_chunks` (PersistStep)، `refresh_chunk_paths` (بعد از move/rename/copy)؛ `backfill_chunk_paths.py` = اسکریپت یک‌باره برای اسناد قدیمی |
| `ingestion/converter.py` | `converted_copy`: تبدیل فرمت‌های قدیمی با `soffice` headless (profile موقت هر فایل، تایم‌اوت، بررسی magic) |
| `ingestion/docx_pagination.py` | صفحه‌بندی Word-style: `Block`، `paragraph_blocks`، `paginate` (word/estimated)، `docx_declared_pages`، `legacy_declared_pages` |
| `ingestion/parser.py` | `parse_document_pages` و parserهای هر فرمت، `SUPPORTED_EXTENSIONS`, `DocumentPage`, `ExtractedImage` |
| `ingestion/ocr.py` | `extract_text_from_image`, `prepare_image_for_ocr`, `optimize_image_for_ocr`, `preprocess_signature`, `SYSTEM_OCR_PROMPT` |
| `ingestion/image_preprocess.py` | توابع Pillow/numpy: `is_blank`، `estimate_skew`/`deskew`، `crop_margins`، `enhance_contrast`، `normalize_background`، `split_vertical` (فقط blank در pipeline فعال است؛ بقیه برای ارزیابی/خاموش) |
| `ingestion/page_kind.py` | `looks_like_drawing`، `mark_drawing_page`، `DRAWING_NOTE` (علامت صفحه‌ی نقشه/نمودار) |
| `ingestion/image_orientation.py` | `choose_rotation` (روش‌های `osd`/`model`/`hybrid`)، `detect_rotation_osd` (Tesseract)، `find_upright_rotation` (probe مدل + تأیید) |
| `ingestion/reconstructor.py` | ذخیره/بارگذاری/پاکسازی `.reconstructed.txt/json` |
| `ingestion/chunker.py` | `chunk_text`, `chunk_document_pages`, `PageChunk` |
| `ingestion/embedder.py` | `embed_chunks` (دسته‌های ۶۴) |
| `ingestion/text_layer.py` | `assess_text_layer` (ok/visual_persian/garbled), `fix_visual_persian` |
| `reembed.py` | CLI re-embed اسناد و حافظه پس از تغییر مدل embedding |
| `ingestion/pipeline.py` | `IngestionStep`ها، `DEFAULT_PIPELINE`, `run_ingestion_pipeline(_sync)`, `_notify_conversation` |
### retrieval
`access_filter.py` (`accessible_documents_filter`) · `service.py` (`Retriever`, `VectorRetriever`, `HybridRetriever`, `RerankingRetriever`, `parse_rerank_indexes`, `RetrievedChunk`, `query_terms`, `reciprocal_rank_fusion`, `get_retriever`).
### memory
`models.py` · `schemas.py` · `service.py` (`remember`, `recall`, `list_project_memories`, `get_memory`, `update_memory`, `delete_memory`) · `router.py`.
### chat
| فایل | کار |
|---|---|
| `models.py` | Conversation, ConversationType, Message, SenderType |
| `schemas.py` | MessageRead, Conversation*, ChatRequest, GroupMessageCreate (re-export `SourceCitation`) |
| `dependencies.py` | `require_conversation_access` |
| `router.py` | `/chat/*` و WebSocket؛ `_authenticate_websocket` |
| `service.py` | مدیریت گفتگو، SSE (`stream_chat_response`), گروه (`post_group_message`, `_generate_group_ai_reply`), `_agent_engine` سراسری، عنوان خودکار، `_failed_turn_result` |
| `ws.py` | `ConnectionManager` (Redis pub/sub) + `publish_event` |
### agent
`engine.py` (`AgentEngine`, `SYSTEM_PROMPT`, `MAX_STEPS`=8) · `tools/folder_tools.py` (`BrowseFolderTool`, `project_tree_summary`) · `schemas.py` (`SourceCitation`, `AgentActivityEvent`, `ToolExecutionResult`, `AgentTurnResult`) · `scope.py` (`resolve_retrieval_scope`) · `tools/{base,registry,document_tools,project_tools,memory_tools,accounting_tools}.py`.
### db_connector
| فایل | کار |
|---|---|
| `models.py` | SchemaHint, DbQueryLog, QueryStatus |
| `hints.py` | corpus، `ingest_hints`، `retrieve_hints` (hybrid RRF)، cacheها، `load_core_prompt` |
| `lexical.py` | `Bm25Index`, `normalize`, `tokens` |
| `generator.py` | `SqlGenerator`, `LLMSqlGenerator`, `build_messages`, `extract_sql`, `CannotAnswer`, `Attempt` |
| `sql_validator.py` | `validate_sql`, `SqlValidationError`, `strip_comments` |
| `executor.py` | `execute_query`, `QueryResult`, `DbExecutionError`, `data_freshness` |
| `summary.py` | `compute_totals`, `build_totals_sql`, `empty_result_feedback` |
| `formatter.py` | `format_query_result`, `format_cell`, `format_currency_value`, `is_money_column` |
| `artifacts.py` | `build_sql_result_artifact`, `column_kind` |
| `money_columns.py` | `MONEY_COLUMNS` (تولیدی) |
| `service.py` | `run_accounting_query` (هماهنگ‌کننده)، `query_accounting_db`, `record_feedback`, `list_query_logs`, `get_query_stats` |
| `router.py` | `/accounting-db/*` + ساخت xlsx/csv |
| `ingest.py` | CLI ingest hints |
| `schemas.py` | schemaهای router |

## `tools/retrieval_eval/`
ابزار ارزیابی بازیابی روی فایل‌های واقعی (`ingest.py`، `evaluate.py`، `questions.py`، `corpus.py`، `common.py`) — راهنما: [../../tools/retrieval_eval/README.md](../../tools/retrieval_eval/README.md)، نتایج: [../ops/retrieval-evaluation.md](../ops/retrieval-evaluation.md).

## `alembic/`, `infra/`, Docker
`alembic/env.py`, `versions/0001..0007` · `infra/caddy/{Dockerfile,Caddyfile,Caddyfile.http,app.caddy}` · `Dockerfile` · `docker-compose{,.override,.prod}.yml` ← [../ops/infra-and-deploy.md](../ops/infra-and-deploy.md).

## `sql/rahkaran/`
| مسیر | کار |
|---|---|
| `00..80_*.sql` | تعریف view های `ai` |
| `apply.py` | اعمال SQLها + descriptions + ساخت reader |
| `refresh.py` | ریستور + swap |
| `descriptions.py` | توضیح فارسی view/ستون (`COLS_TEXT`, `OVERRIDES`, `VIEWS`) |
| `examples/{questions,run}.py` | نمونه سؤال/SQL و اجرای آن‌ها |
| `hints/{notes,build_hints,eval_retrieval,eval_set}.py` | دانش و ساخت corpus |
| `hints/out/` | خروجی ساخته‌شده؛ داخل git است (commit با `git add -f`، چون `.gitignore` الگوی `out/` دارد) |

## `docs/rahkaran/`
مستندات دامنه (README, GLOSSARY_*, enums, schema/*, QUESTIONS, TAXONOMY_REVIEW, ACCOUNTANT_QUESTIONS) و `tools/` (اسکریپت‌های تولید مستند؛ `db.py`, `peek.py`, `table_usage.py`, `gen_*`) و `data/mehvargostar_code.xlsx` (فایل طبقه‌بندی حسابدار).
