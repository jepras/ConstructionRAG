### ConstructionRAG — Architecture and Risk Review (2025-08)

- **Scope**: Fast, high-signal assessment of architecture, data flows, schema, pipelines, configs, security, and performance.
- **Repo root**: `ConstructionRAG`

---

## 1) High-level system overview

- **Frontend**: `frontend/streamlit_app` Streamlit UI calling backend REST.
- **Backend API (FastAPI, Railway)**: `backend/src/main.py` with routers in `backend/src/api/` for auth, documents/uploads, pipeline status, queries, wiki.
- **Indexing pipeline (Beam GPU worker)**: `backend/beam-app.py`, orchestrated by `backend/src/pipeline/indexing/orchestrator.py`; steps in `backend/src/pipeline/indexing/steps/` (partition → metadata → enrichment → chunking → embedding).
- **Query pipeline (FastAPI runtime)**: `backend/src/pipeline/querying/orchestrator.py`; steps in `backend/src/pipeline/querying/steps/` (query_processing → retrieval → generation).
- **Wiki generation pipeline**: `backend/src/pipeline/wiki_generation/` orchestrator and steps, outputs `.md` to Supabase Storage.
- **Services**: `backend/src/services/` for Supabase auth, storage, pipelines, Beam trigger.
- **Config**: `backend/src/config/` (env settings, DB clients), JSON configs in `config/pipeline/`.
- **Database (Supabase Postgres + pgvector)**: schema migrations in `supabase/migrations/`; vector search on `document_chunks` with HNSW.

---

## 2) End-to-end data flow for core journeys

- **Email upload → Beam indexing**
  - `POST /api/email-uploads` → stores files to Supabase Storage, creates `indexing_runs`, `documents`, junction `indexing_run_documents` → background task triggers Beam via `BeamService.trigger_indexing_pipeline()`.
  - Beam runs 5-step pipeline, stores chunks and embeddings; run and per-document step results written back; progress endpoints under `/api/pipeline/indexing/...`.
- **User project upload → indexing**
  - `POST /api/projects/{project_id}/documents` → Storage upload → create/link `indexing_runs` → background processing via orchestrator for single or multi-document.
- **Query**
  - `POST /api/query` → query_processing (variations) → retrieval (vector search) → generation (OpenRouter) → stores `query_runs` with `step_timings`.
- **Wiki generation**
  - `POST /api/wiki/runs` → validates ownership and `upload_type` → orchestrates steps → writes pages/metadata to Storage; browse via `/api/wiki/runs/{...}/pages`.

---

## 3) Key modules and directories

- **API**: `backend/src/api/` — `auth.py`, `documents.py`, `pipeline.py`, `queries.py`, `wiki.py`.
- **Pipelines**:
  - Indexing: `backend/src/pipeline/indexing/` (steps + orchestrator).
  - Querying: `backend/src/pipeline/querying/` (steps + orchestrator + models).
  - Wiki: `backend/src/pipeline/wiki_generation/`.
  - Shared: `backend/src/pipeline/shared/` (base_step, models, progress tracker, config manager).
- **Services**: `backend/src/services/` — `auth_service.py`, `pipeline_service.py`, `storage_service.py`, `beam_service.py`.
- **Config**: `backend/src/config/` (settings, database); pipeline JSON under `config/pipeline/`.
- **Migrations**: `supabase/migrations/*.sql`.

---

## 4) Config and environment

- **Env settings**: `backend/src/config/settings.py` loads `.env` and exposes keys (Supabase, Voyage, OpenRouter, Beam). Defaults include embedding model/dims that currently drift from code and DB.
```startLine:48:endLine:52:backend/src/config/settings.py
    # Pipeline configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "voyage-large-2"
    embedding_dimensions: int = 1536
```
- **Pipeline JSON configs**:
  - Embedding: `config/pipeline/embedding_config.json`
```startLine:1:endLine:6:config/pipeline/embedding_config.json
{
  "model": "voyage-large-2",
  "dimensions": 1536,
  "batch_size": 32,
  "max_retries": 3,
  "timeout": 30
}
```
  - Retrieval: `config/pipeline/retrieval_config.json` (method=hybrid, top_k=5), but runtime retrieval step overrides this with a separate config.
- **Coupling/drift risks**:
  - Indexing step writes to `embedding_1024` (1024 dims) while settings/config reference 1536/voyage-large-2; retrieval uses 1024. This is a critical config-model drift (see §5, §12).
  - Query defaults in orchestrator vs JSON configs can diverge; no single source of truth for model names.

---

## 5) Database and vector store

- **Core tables**: `documents`, `document_chunks`, `indexing_runs`, `indexing_run_documents` (junction), `query_runs`, `projects`, `user_profiles`.
- **Vector column**: `document_chunks.embedding_1024 VECTOR(1024)` with HNSW index; prior migrations show 1536→rename→1024.
```startLine:8:endLine:18:supabase/migrations/20250128230000_update_to_voyage_multilingual_2.sql
-- Rename embedding column to embedding_1024
ALTER TABLE document_chunks 
RENAME COLUMN embedding TO embedding_1024;

-- Update embedding column to 1024 dimensions for voyage-multilingual-2
ALTER TABLE document_chunks 
ALTER COLUMN embedding_1024 TYPE VECTOR(1024);

-- HNSW index on embedding_1024
```
- **Embedding writes (indexing)**: stores vectors into `embedding_1024`.
```startLine:308:endLine:323:backend/src/pipeline/indexing/steps/embedding.py
self.db.table("document_chunks").update({
    "embedding_1024": embedding,
    "embedding_model": self.voyage_client.model,
    "embedding_provider": "voyage",
    "embedding_metadata": {"dimensions": len(embedding), ...},
}).eq("id", chunk["id"]).execute()
```
- **Retrieval reads**: fetches all chunks with `embedding_1024` and computes cosine similarity in Python (not SQL ANN).
```startLine:212:endLine:231:backend/src/pipeline/querying/steps/retrieval.py
query = (
  self.db.table("document_chunks")
    .select("id,content,metadata,embedding_1024,document_id,indexing_run_id")
    .not_.is_("embedding_1024", "null")
)
...
for chunk in chunks:
    if chunk.get("embedding_1024"):
        chunk_embedding_str = chunk["embedding_1024"]
        ... # parse and cosine in Python
```
- **Relationships**: many-to-many redesign via `indexing_run_documents`; `indexing_runs.document_id` removed.
```startLine:41:endLine:50:supabase/migrations/20250801030000_redesign_document_indexing_relationship.sql
CREATE TABLE IF NOT EXISTS indexing_run_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  indexing_run_id UUID NOT NULL REFERENCES indexing_runs(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ...,
  UNIQUE(indexing_run_id, document_id)
);
```
- **Invariants (must-hold)**:
  - Embedding vector length matches column dims (1024) before write; enforced implicitly by pgvector type; validated indirectly in `embedding_metadata.dimensions` but not enforced in app code.
  - `indexing_run_documents` has unique `(indexing_run_id, document_id)`; enforced by DB unique index.

---

## 6) Pipelines and background work

- **Indexing orchestration**: `IndexingOrchestrator` initializes steps, stores per-document step_results, batch-embeds all chunks across documents, and updates run status.
- **Idempotency**:
  - Chunk storage uses `chunk_id` (uuid) and DB unique index `(document_id, chunk_id)` to avoid duplicates across retries.
  - Embedding step has `resume_capability` and only updates rows where `embedding_1024 IS NULL`.
- **Failure recovery**:
  - On any step failure: marks run/document status `failed` and writes `error_message` (`pipeline_service.update_indexing_run_status`, `store_document_step_result`).
- **Batching**:
  - Batch embedding across documents per run.
- **Beam separation**: indexing runs on Beam; FastAPI only triggers and reads status.

---

## 7) External services and APIs; error handling/timeouts

- **Supabase**: Auth, Postgres, Storage. Admin client used widely.
- **Voyage AI**: embeddings in indexing and retrieval. Timeouts ~30s.
- **OpenRouter**: LLM for query processing and generation; fallbacks, per-call timeout.
- **Beam**: webhook trigger with `httpx` and 30s timeout.
- **Risks**:
  - Admin client (`service_role`) used in user-scoped endpoints can bypass RLS; ensure explicit WHERE filters.
  - Manual JWT decode (no signature verification) in auth service.

---

## 8) Logging, metrics, observability

- **Structured logging**: `backend/src/utils/logging.py` via `structlog`; not globally initialized in `main.py`.
- **Progress tracking**: `ProgressTracker` logs per-step, writes batch step results to `indexing_runs.step_results`.
- **Query metrics**: `query_runs.step_timings` and analytics view in migrations (`get_recent_query_performance`).
- **Gaps**: no centralized request logging, no tracing, no per-step metrics export, limited error context.

---

## 9) Testing strategy

- **Integration tests**: many under `backend/tests/integration/*`. Runner `backend/run_tests.py` imports test functions directly; also supports pytest.
- **How to run locally**:
  - Activate project venv and run from repo root [[memory:4729889]][[memory:4923338]]. For Docker-dependent integration, run from root [[memory:4913167]].
  - Example:
    - `python backend/run_tests.py` (smoke) or `pytest -q backend/tests/integration`.
- **Coverage gaps**: step failure paths, RLS/authorization, retrieval ANN SQL path, wiki endpoints, Storage error handling, Beam callback handling.

---

## 10) Security and privacy risks (quick wins first)

- **Critical**: Manual JWT decode without signature verification; tokens are only decoded and `exp` checked.
```startLine:146:endLine:175:backend/src/services/auth_service.py
parts = access_token.split(".")
...
payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8"))
...
user_id = payload.get("sub")
```
  - Quick win: verify via Supabase auth APIs (`get_user`) or use official client session introspection.
- **Critical**: Use of admin client (`get_supabase_admin_client`) inside user-facing endpoints returns unscoped data.
```startLine:95:endLine:121:backend/src/api/pipeline.py
result = (
  pipeline_service.supabase.table("indexing_runs")
  .select("id, upload_type, project_id, status, started_at, completed_at, error_message")
  .order("started_at", desc=True)
  .limit(5)
).execute()
```
  - Quick win: apply user scoping (JOIN via junction or filter by projects) or switch to anon client where possible.
- **CORS**: `allow_origins=["*"]` in `main.py`; restrict in production.
- **Secrets**: `/api/debug/env` exposes presence of keys; disable in prod.
- **RLS**: Policies redesigned; but admin client bypasses them. Ensure only server-to-server flows use admin, never user-scoped reads.
- **PII**: email uploads store `email` in `documents.metadata`; ensure retention/expiry enforced.

---

## 11) Performance hotspots and scalability concerns

- **Retrieval path**: Pulls all chunks into app and computes cosine in Python; not using ANN in SQL. This will not scale beyond thousands of chunks.
- **Embedding step**: Batch write per-row updates; could use RPC/bulk updates to reduce round trips.
- **Storage**: Repeated bucket existence checks per upload; cache result.
- **Indexing concurrency**: Conservative max 3 concurrent docs; may underutilize Beam instances.
- **Query generation**: Sequential fallbacks with network calls; consider timeouts/parallel racing.

---

## 12) Top 10 actionable improvements (impact/effort)

1. **Unify embedding model and dimensions across pipeline** (DB, indexing, retrieval, settings, configs). Impact: correctness + retrieval quality; Effort: M.
2. **Switch retrieval to SQL ANN using HNSW on `embedding_1024` with WHERE filters**; optionally add rerank step. Impact: 10–100x speed; Effort: M.
3. **Replace manual JWT parsing with verified Supabase auth session/user lookup**. Impact: critical security; Effort: S.
4. **Remove admin client usage from user-scoped endpoints; enforce user filters (JOIN via `indexing_run_documents`)**. Impact: data security; Effort: M.
5. **Harden CORS and disable `/api/debug/env` in prod**. Impact: security; Effort: XS.
6. **Initialize structured logging globally; add request/step IDs; standardize error logging**. Impact: ops/debuggability; Effort: S.
7. **Bulk embedding writes (UPSERT with array binding) or RPC to reduce per-chunk round trips**. Impact: throughput; Effort: M.
8. **Add idempotent run re-entry: guard duplicate chunk insert by `(document_id, chunk_id)` unique index in migration if missing**. Impact: stability; Effort: S.
9. **Test coverage on RLS/authorization and failure paths**. Impact: safety; Effort: M.
10. **Document single source of truth for models/configs and load from there (e.g., `config/pipeline/*` only)**. Impact: maintainability; Effort: S.

---

## 13) Unknowns / open questions

- Which embedding model is the intended standard now: `voyage-multilingual-2` (1024) or `voyage-large-2` (1536)? Confirm target before we refactor.
- Should email-uploaded documents be publicly queryable (current policies allow read until `expires_at`)?
- Is there a Beam callback path to update run status, or do we poll only? Any webhook validation?
- Expected max corpus size per project/indexing run? Drives ANN parameters (`ef_search`, `lists`, etc.).
- Any multi-tenant considerations beyond Supabase RLS (orgs/teams)?

---

## Additional code citations (evidence)

- Retrieval client embeds with `voyage-multilingual-2` (1024) and uses admin client.
```startLine:21:endLine:31:backend/src/pipeline/querying/steps/retrieval.py
class VoyageEmbeddingClient:
    def __init__(self, api_key: str, model: str = "voyage-multilingual-2"):
        ...
        self.dimensions = 1024
```
- Indexing embedding client defaults to `voyage-multimodal-3` while declaring 1024 dims; mismatch.
```startLine:24:endLine:31:backend/src/pipeline/indexing/steps/embedding.py
class VoyageEmbeddingClient:
    def __init__(self, api_key: str, model: str = "voyage-multimodal-3"):
        ...
        self.dimensions = 1024
```
- Query orchestrator default retrieval config uses 1024 dims.
```startLine:69:endLine:86:backend/src/pipeline/querying/orchestrator.py
"retrieval": {
  "embedding_model": "voyage-multilingual-2",
  "dimensions": 1024,
  "similarity_metric": "cosine",
  "top_k": 5,
  ...
}
```
- Pipeline status endpoint currently uses admin client and no user filter.
```startLine:190:endLine:221:backend/src/api/pipeline.py
run = await pipeline_service.get_indexing_run(run_id)
# admin client inside service; ensure scoping
```

---

## Invariants to track/enforce

- Embedding model name and vector dimension are consistent across settings, configs, indexing, retrieval, and DB schema.
- Indexing run step results are immutable once completed (avoid retroactive edits) and per-document step results reflect accurate current step.
- All user-scoped reads use anon client and respect RLS; admin client only for trusted background/Beam.

---

## Quick plan to resolve critical drifts (reference-only)

- Decide standard embedding: prefer current DB schema (`embedding_1024` + `voyage-multilingual-2`).
- Update:
  - `config/pipeline/embedding_config.json` → model `voyage-multilingual-2`, dims 1024.
  - `backend/src/config/settings.py` defaults → 1024 + correct model.
  - `backend/src/pipeline/indexing/steps/embedding.py` client default model → `voyage-multilingual-2`.
  - Revalidate retrieval to use SQL ANN and optional rerank.

---

## How to run critical tests locally

- From repo root with venv activated [[memory:4729889]][[memory:4923338]]:
  - `python backend/run_tests.py` (smoke)
  - `pytest -q backend/tests/integration/test_query_pipeline_integration.py`
  - For Docker/pgvector heavy tests, run from root [[memory:4913167]].

---

End of review.
