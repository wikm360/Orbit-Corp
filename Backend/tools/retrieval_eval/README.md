# Retrieval evaluation

Measures how well document search finds the right chunk, using real company files and hand-written questions.

```
EVAL_PG_BASE=postgresql+asyncpg://postgres:PASSWORD@HOST:5432 python tools/retrieval_eval/ingest.py     # once (OCR + embeddings: minutes, costs API calls)
EVAL_PG_BASE=... python tools/retrieval_eval/evaluate.py                                               # variants on the ingested chunks
EVAL_PG_BASE=... python tools/retrieval_eval/evaluate.py --matrix                                      # chunk size x embedding model
```
- Needs a Postgres with `vector` and `pg_trgm`, and the LLM/embedding keys from `.env`. The scratch database (`EVAL_DB`, default `eval_scratch`) is dropped and rebuilt by `ingest.py`.
- `EVAL_DIR` (default `Backend/eval`) holds the originals; they are only read. `EVAL_WORKDIR` (default `/tmp/orbit_retrieval_eval`) holds copies, embedding caches and `project.json`.
- `corpus.py` lists the ingested files, `questions.py` the questions (id, category, question, must-contain strings). Add questions from real user failures; a question is only meaningful if at least one chunk in the corpus contains all its `must` strings.
- Results and conclusions: `.agents/ops/retrieval-evaluation.md`.
- Page text and page images are sent to the configured provider. Do not add financial statements, tax returns, IDs or signed/stamped scans to `corpus.py`.
