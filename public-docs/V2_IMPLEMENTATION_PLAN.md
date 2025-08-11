# ConstructionRAG v2 — Implementation Plan

This plan sequences v2 work into clear phases with tasks, testing, and milestones. Assumptions: work on a separate branch; merge to main when all phases in scope are green. No deprecation headers needed (no external users during the migration).

---

## Phase 0: Decisions, Guardrails, and Tooling

### Tasks
- ✅ Add/confirm tooling baselines for new code only: Ruff (lint), mypy (type checks). Do not modify requirements without approval.
- ✅ Lock embedding standard: `voyage-multilingual-2` with 1024 dimensions across DB, indexing, retrieval.
- ✅ Establish single source of truth (SoT) for configuration:
  - Central typed settings (`backend/src/config/settings.py`) sources values from SoT JSON.
  - ✅ Remove any `voyage-large-*` references in backend code and SoT configs; frontend and legacy example configs still contain references (cleanup pending).
- ✅ Define `RequestContext` concept for optional-auth flows (used later by services and APIs).

#### Configuration decisions (finalized)
- Single SoT file for pipeline parameters: `config/pipeline/pipeline_config.json` (JSON).
  - Chosen for maintainability and UI round-tripping; explicit types; stable diffs; no YAML macro/anchor pitfalls.
  - Secrets (API keys) stay in environment via `backend/src/config/settings.py`; never stored in the config file.
- Override precedence (no database overrides table):
  - Per-request UI overrides → pipeline-specific section (`indexing`/`query`/`wiki`) → `defaults`.
  - No `user_config_overrides` table; persistent presets can be added later if needed, but are out of scope for Phase 0.
- Per-run persistence:
  - Always persist the full, effective merged config on every run (Indexing, Query, Wiki) to the corresponding run record.
-  - No additional hash/version metadata in Phase 0 (can be added later if needed).
- Invariants and enforcement:
  - Embedding invariants locked in Phase 0: `voyage-multilingual-2` with 1024 dimensions; fail-fast on drift.
  - Remove/override any hardcoded or conflicting embedding values; stop using YAML templating/macros and inject embedding values programmatically from the SoT.
- Loader/validation:
  - Introduce a small `ConfigService` that loads and caches the SoT JSON, merges per-request overrides with the precedence above, enforces locked keys, and validates via Pydantic models before handing configs to orchestrators/steps.
  - File paths resolved relative to repo root; no runtime templating in YAML.

#### RequestContext decisions (finalized)
- Fields: `request_id` (str), `user_id` (optional str), `is_authenticated` (bool), `org_id` (optional str), `roles` (list[str]).
- Creation: FastAPI dependency verifies Supabase token if present; anonymous fallback when absent/invalid. `request_id` provided by middleware.
- Propagation: passed to services/orchestrators only in Phase 0 (steps remain config-driven).

#### Startup validation (finalized)
- Fail-fast on: missing/invalid SoT file; embedding invariants violated (model/dims); missing critical environment secrets in non-development.
- Warn-only (development): optional sections missing where defaults exist.
- Explicitly skip DB vector column verification in Phase 0.

### Testing
- ✅ Unit: SoT loading and embedding invariants (voyage-multilingual-2, 1024) consistent across indexing/query
- ✅ Startup validation: fail-fast on missing/invalid SoT and required generation keys (model, fallback_models)
- ✅ Orchestrator usage: query orchestrator uses SoT for generation model and retrieval dims/model
- ✅ No YAML usage in backend/src (scan asserts no yaml.safe_load or .yaml references)
- ✅ Lint/type checks on the new v2 modules

### Milestone
- Config SoT established; embedding decision enforced; basic lint/type guardrails in place for new v2 code.

#### Summary (completed)
- Lint/type baseline added (Ruff, mypy) and scoped to new v2 modules.
- Single SoT enforced for pipelines; runtime file located at `config/pipeline/pipeline_config.json` with loader discovery and fail-fast startup validation; legacy YAML no longer used at runtime. The older `backend/src/config/pipeline/` JSON is deprecated.
- Embedding invariants enforced end-to-end (`voyage-multilingual-2`, 1024); removed `voyage-large-*` references from backend.
- `RequestContext` model added for optional-auth flows; propagated to services/orchestrators.
- Orchestrators and wiki steps read config from SoT; effective config persisted per run.
- Unit tests added and passing: SoT loading, invariants, orchestrator usage, and no YAML usage verified.

---

## Phase 1: Consistent Error Handling Foundation

### Tasks
- ✅ Implement exception hierarchy (`AppError`), request ID middleware, and centralized error handlers (per `own/v2/CONSISTENT_ERROR_HANDLING_GUIDE.md`).
- ✅ Wire handlers in `backend/src/main.py` and enable structlog ProcessorFormatter.
- ✅ Convert representative endpoint(s) in `backend/src/api/documents.py` to the new error pattern.
- ✅ Standardize error JSON and `X-Request-ID` response header; ensure logs include `request_id`, `error_code`, `path`, `method`, `status_code`.
- ✅ Add unit/app tests for handlers and endpoint validation.
- ✅ Bind `request_id` (and when available `run_id`, `pipeline_type`) in orchestrators/`ProgressTracker` for inheritance in logs (thin slice).
 
 #### Design decisions
 - **Request ID**: Accept `X-Request-ID` if present; else UUID4. Add `X-Request-ID` to every response. Store in `RequestContext` and bind into logs via structlog contextvars.
 - **Error envelope**: `{code, message, details?, request_id, path, timestamp}`; always include `X-Request-ID` header.
 - **Exceptions**: Use `AppError` as base. Define stable error codes and map to HTTP: Validation→422, Auth→401, Access→403, NotFound→404, External/DB/Storage→502, Config/Internal→500. Ensure `StorageError` subclasses `AppError`.
 - **Global handlers**: Register for `AppError`, `HTTPException`, `RequestValidationError`, and fallback `Exception`. Hide stack traces in production; include `request_id` in all responses.
 - **Logging**: Every error log includes `request_id`, `error_code`, `path`, `method`, `status_code`. Treat 4xx as warning, 5xx as error.
- **Logging plumbing**: Enable structlog ProcessorFormatter so stdlib `logging` emits structured JSON; new code uses structlog via `src.utils.logging`.
- **Logging cleanup later**: Plan a later sweep to simplify messages and remove remaining `print` calls.
 - **Scope now vs later**: Implement this thin slice now; defer OTel/metrics/log shipping. Bind `run_id`/`pipeline_type` in orchestrators/`ProgressTracker` for correlation with step timings and query metrics.
 - **Representative endpoint**: Start with `GET /api/documents/{id}` to validate handlers, envelope, headers, and logs.

### Testing
- ✅ Unit tests: `upload_email_pdf` validation errors raise `ValidationError` with proper `ErrorCode`.
- ✅ App-level tests: centralized handlers return standardized error JSON and include `X-Request-ID`.
- ✅ Integration smoke tests: real `main.app` with startup validation monkeypatched; `/health` echoes `X-Request-ID`; `AppError` route standardized.

### Milestone
- Reliable, uniform error surface and logging across the stack; ready for broader adoption.

---

## Phase 2: Core Pydantic Models and Pipeline Step IO Contracts (start with Query pipeline)

### Tasks
- ✅ Define strict Pydantic models for query-related resources only (Document; keep QueryRun as-is for now) and shared types (per `own/v2/PYDANTIC_MODEL_REFACTORING_GUIDE.md`). IndexingRun is deferred to Phase 2B.
- ✅ Define query pipeline step IO contracts and refactor the query pipeline first:
  - ✅ Add adapters to serialize typed models to `StepResult.sample_outputs` with `model_dump(exclude_none=True)` while preserving keys.
- ✅ Adjust querying orchestrator interfaces to consume/produce these contracts.
- ✅ Apply consistent error handling in query module: replace `HTTPException`/ad-hoc errors with `AppError`; ensure standardized error envelope and `X-Request-ID`.

#### Design decisions (Phase 2 model refactor)
- **Pydantic v2 style**: Use `model_config = ConfigDict(...)` in refactored models (replace `class Config` only where we touch code).
- **Serialization policy**: Prefer FastAPI `response_model_exclude_none=True` for new routes; when manually serializing, call `model_dump(exclude_none=True)`. Use `by_alias=True` only where aliases are explicitly defined.
- **Datetime policy**: Keep current behavior (naive UTC via `datetime.utcnow`, ISO output) for Phase 2 to avoid regressions; revisit timezone-awareness later.
- **Model naming**: Use `ResourceCreate`/`ResourceUpdate` for API inputs; responses use the resource model unless a distinct shape is required (then `ResourceResponse`).
- **Layering**:
  1) Pydantic validation (shape/fields/validators)
  2) Business logic in services (existence/auth, ConfigService-driven invariants, DB calls)
  3) Centralized error handling (`AppError` → uniform envelope, `X-Request-ID`).
- **Unstructured fields**: Keep `Dict[str, Any]` for `metadata`/`retrieval_metadata` in Phase 2; optionally tighten later with `TypedDict`/`JSONValue`.
- **Embeddings**:
  - Domain and step IO models expose `embedding: list[float]` (no dimensions in the field name).
  - Database column remains `embedding_1024`; map between model and DB at the repository/service boundary (alias/adapter), not in the domain model.
  - Enforce model/dimensions centrally in `ConfigService` (SoT); avoid redundant hardcoded 1024 checks in models.
- **Base classes**: Add `backend/src/models/base.py` for shared enums/base types and `@computed_field`s (e.g., durations). Keep models pure (no logging inside models).
- **Step IO contracts (Query)**: Define typed inputs/outputs for `query_processing`, `retrieval`, `generation`. Keep `StepResult` non-generic for now. Preserve existing `step_results` JSON structure for compatibility (adapters in place).
- **Alignment**: This approach aligns with `API_REDESIGN_PLAN.md`, `SHARED_SERVICES_STRATEGY.md`, and current `RequestContext`; optimized for simplicity, maintainability, and clarity.

### Testing
- ✅ Minimal integration test: end-to-end orchestrator smoke (`backend/tests/integration/test_query_pipeline_integration.py`).
- ✅ API e2e test: `/api/query` returns expected JSON shape and echoes `X-Request-ID` (`backend/tests/integration/test_query_api_e2e.py`).
- ✅ App smoke tests green: health and `AppError` handler (`backend/tests/integration/test_main_app_smoke.py`).
- Note: Dedicated per-step unit tests can be added later if needed; current integration coverage validates typed IO and surfaces.

### Milestone
- Phase 2 complete: Query-domain models validated; query pipeline refactored end-to-end to contract-based IO (typed adapters in place; orchestrator using typed models); standardized error handling applied; tests green. Indexing models unchanged (moved to Phase 2B).

---

## Phase 2B: Indexing Pipeline IO Contracts

### Tasks
- ✅ Define step IO contracts and refactor the indexing pipeline in order:
  - ✅ Partition → ✅ Metadata → ✅ Enrichment → ✅ Chunking → ✅ Embedding
  - Implemented typed IO models and adapters in `backend/src/pipeline/indexing/models.py` (no behavior change).
- ✅ Adjust indexing orchestrator interfaces to the new contracts; preserve resume/idempotency behavior.
  - Orchestrator now converts `StepResult.data` via adapters between steps to validated dicts.
- ✅ Ensure embedding step writes 1024-dim vectors and reads model/dim from shared config.
  - Voyage client uses `voyage-multilingual-2` (1024 dims); step writes to `embedding_1024`.
- ✅ Apply consistent error handling in indexing pipeline: raise/propagate `AppError` from steps; ensure standardized error surface.

### Testing
- Pending: Unit tests for each step validating inputs/outputs per contract.
- Pending: Small-corpus integration test that runs the indexing pipeline and validates persisted artifacts against models.
- Pending: Tests that failed steps/orchestrator paths produce standardized error details.

### Milestone
- Code changes complete; tests pending. Indexing pipeline migrated to contract-based IO, consistent with shared configs and embedding invariants.

---

## Phase 2C: Wiki Generation Pipeline IO Contracts

### Tasks
- ✅ Define IO contracts for wiki steps and refactor:
  - ✅ Overview generation → ✅ Structure generation → ✅ Page content retrieval → ✅ Markdown generation → ✅ Metadata collection → ✅ Semantic clustering
- ✅ Update wiki orchestrator to use the new contracts.
- ✅ Apply consistent error handling in wiki pipeline: use `AppError` across steps/orchestrator; standardized error payloads when exposed via API.

### Testing
- Integration test that runs a minimal wiki generation flow and validates produced pages/metadata against models. ✅ `backend/tests/integration/test_wiki_e2e.py`
- (Optional) Unit tests per step validating contract conformance.
- (Optional) Tests asserting standardized error envelope for wiki API failures (covered by global handlers in Phase 1).

### Milestone
- ✅ Wiki pipeline aligned to contract-based IO; ready for Beam-only execution in later phases.

---

## Phase 3: Access Control Data Model (DB + Minimal Infra)

### Tasks
- ✅ Add `access_level` columns (`documents`, `indexing_runs`, `query_runs`, `wiki_generation_runs`) and set DEFAULT 'private'.
- ✅ Allow `user_id` to be nullable where anonymous flows are supported (`query_runs`, `documents` ensured).
- ✅ Introduce `RequestContext` into data access paths; define conservative filters (anonymous → public only) — foundation in place, enforcement to be used by services in later phases.
- ✅ Add `AccessLevel` enum in `backend/src/models/base.py` with values: `public`, `auth`, `owner`, `private` (default `private`).

#### Notes
- RLS policies: Full database-wide RLS policy review is deferred to Phase 9 (Security Hardening), alongside the admin-client vs anon-client sweep. In Phase 3 we only add columns and code-level filters; we do not enable/modify RLS globally.

### Testing
- ✅ Migration applied to production database (no external users). Backfilled sensible defaults; set column defaults.
- Pending: Unit tests for query builders filtering by `access_level` and `user_id` (will be added when services are introduced in Phase 4/7).
- Pending: Integration tests for anonymous vs authenticated list/get (after service layer and v2 endpoints are in place).

### Milestone
- ✅ Access control primitives added at the data model level and ready for use in services and API v2.

---

## Feature-driven Execution Slices (recommended order)

Rather than strict sequential phases, execute end-to-end feature slices after Phase 0–3 are complete. This reduces integration debt and accelerates feedback.

### Slice A: Storage-aware Services (Phase 4 + 5 together)
- Scope
  - Minimal `DbService` (get_by_id, create) used by `DocumentService`
  - `StorageService` wired via resolver (still admin client in Phase 4)
  - Email and single project uploads use `DocumentService`; project multi-upload left as-is (note to refactor later)
  - Adopt `ConfigService` SoT everywhere; enforce error contract and structured logging
- Testing
  - ✅ Unit: `DocumentService` happy paths (email, project)
  - ✅ Unit: `DbService` happy/error paths (mocked Supabase client)
  - ✅ Unit: `StorageClientResolver` basic client resolution (skipped if Supabase env missing)
  - ✅ Unit: `ConfigService` SoT loading + embedding invariants (skipped if env missing)
  - ✅ Live smoke: email upload endpoint with a sample PDF responded 200 OK and returned IDs

### Slice B: Secure API (in-place refactor; Phase 7 + 9 scoped)
- Scope
  - ✅ Refactor existing endpoints in-place to use shared services (no /v2 prefix) for documents, pipeline runs, and wiki reads
  - ✅ Add basic access checks in read services (authenticated → owner-scoped; anonymous allowed only for email-run paths)
  - ✅ Expose flat read endpoints:
    - `/api/documents?project_id=&limit=&offset=` (auth), `/api/documents/{id}?project_id=` (auth)
    - `/api/documents?index_run_id=` (anonymous for email runs), `/api/documents/{id}?index_run_id=` (anonymous for email runs)
    - `/api/indexing-runs` (auth) and `/api/indexing-runs/{id}` (anonymous for email runs; auth otherwise)
  - ✅ Add flat progress endpoint `/api/indexing-runs/{id}/progress` (proxy current pipeline progress)
  - Keep current client usage; full RLS and admin→anon hygiene remains in Phase 9 hardening
- Testing
  - ✅ Endpoint contract tests for documents and pipeline runs (401/403/404), skipped when Supabase env is missing
  - ✅ Endpoint contract tests for wiki endpoints (anon email runs vs auth project runs)
  - ⬜ Access behavior tests per `access_level`; standardized errors and X-Request-ID

### Slice C: Query Stack now, Performance later (Phase 8 now, Phase 10 later)
- Scope
  - Build query endpoints and orchestration using current retrieval approach; ensure 1024-dim invariant
  - Defer SQL ANN/HNSW and reranking to Phase 10
- Testing
  - E2E correctness tests first; schedule performance and top-k parity tests for Phase 10

Notes
- The detailed Phase sections below remain as reference for scope and tests; execute them in the slice groupings above.

---

## Phase 4: Shared Service Skeletons

Note: Executed together with Phase 5 as Slice A.

### Tasks
- Implement `DbService` minimal CRUD (`get_by_id`, `create`) used by services. — [Done]
- Implement `AuthService` using verified Supabase calls (no manual JWT parsing). — [Done]
- Implement `ConfigService` that exposes typed access to SoT configs (embedding, timeouts, batching). — [Done]
- Implement `StorageClientResolver` and `StorageService` that select admin vs anon client based on ownership and access level. — [In Progress]
- Apply consistent error handling in services: raise `AppError` subclasses (`AuthenticationError`, `AuthorizationError`, `StorageError`, `DatabaseError`, `ConfigurationError`) instead of ad-hoc errors. — [In Progress]

#### Design decisions (Phase 4)
- Config SoT location: Use repo-root `config/pipeline/pipeline_config.json` as the only source. During Phase 4, keep code working but switch discovery to prefer repo-root and deprecate the duplicate under `backend/src/config/pipeline/` (no file deletion yet).
- Embedding invariant: Enforce `voyage-multilingual-2` with 1024 dims via `ConfigService` (already in place); no DB migration changes now.
- Retrieval: Do not move to SQL ANN in this phase (defer to Phase 10). Keep existing retrieval logic, only ensure model/dim consistency from SoT.
- Database client/RLS: Defer to Phase 5. For now, reuse current client patterns inside shared services (no behavior change).
- Base CRUD scope: Start minimal to avoid overengineering. Provide `get_by_id` and `create` first; add a simple `list` only where immediately needed. Skip generic filters/pagination/sorting in Phase 4.
- Error model: Use `AppError` + `ErrorCode` exclusively; services raise typed errors; middleware renders standard envelope.
- Logging: Use global structlog setup; include `request_id` and, where relevant, `run_id`/`document_id` in logs.
- CORS: No changes in Phase 4 (keep permissive in dev; restrict later).
- Testing policy: After adopting each shared service in a small surface area, run tests and expand only when green.

### Testing
- ✅ Unit tests for `DocumentService` happy paths
- ✅ Unit tests for `DbService` error/happy paths
- ✅ Unit tests for `StorageClientResolver` covering admin/anon selection cases
- ✅ Unit tests for `ConfigService` loading and error cases
- ⬜ Tests for service error paths mapping to expected `ErrorCode`

### Milestone
- Reusable shared services in place to eliminate duplication in API and pipelines.

---

## Phase 5: Storage Refactor

Note: Executed together with Phase 4 as Slice A.

### Tasks
- Migrate all existing storage operations to `StorageService` (upload, download, list, signed URLs, existence checks). — [In Progress]
- Remove direct usage of admin client in user-scoped operations; rely on resolver decisions. — [In Progress]
- Adopt consistent error handling for storage failures. — [Done]

### Testing
- Unit tests for storage operations (success/failure, access checks). — [In Progress]
- Integration test that uploads and retrieves a file using anon vs authenticated contexts. — [To Do]

### Milestone
- Storage usage is centralized, access-aware, and consistently handled.

---

## Phase 6: Beam-only Execution Cleanup

### Tasks
- Remove local orchestrator execution pathways; keep only Beam-triggered runs. — [Done]
- Move wiki generation orchestration to Beam; ensure progress/status writes are consistent with indexing. — [To Do]
- Confirm background tasks in API only trigger/monitor; no local step execution. — [In Progress]

### Testing
- Integration tests that start an indexing run and a wiki run, then poll status endpoints until completion/failed. — [To Do]
- Tests for Beam trigger timeouts and error surfaces via centralized handlers. — [To Do]

### Milestone
- Single, consistent execution environment for background work (Beam-only).

---

## Phase 7: API — Minimal Slice (Documents & Indexing Runs)

Note: Executed together with Phase 9 (scoped security) as Slice B. Refactor existing endpoints in-place (no /v2).

### Tasks
- Implement flat, resource-based endpoints (in-place, no `/v2` prefix for now) — [Done]:
  - ✅ `POST /api/uploads` (create upload for anonymous/auth users)
  - ✅ `GET /api/documents` and `GET /api/documents/{id}`
  - ✅ `POST /api/indexing-runs`
  - ✅ `GET /api/indexing-runs` and `GET /api/indexing-runs/{id}`
  - ✅ `GET /api/indexing-runs/{id}/progress` (flat proxy to existing pipeline progress)
- Back these endpoints by shared services, `RequestContext`, access filters, and error handling — [In Progress].
- Keep legacy routes unchanged on the branch; no deprecation steps needed — [Done].
- Ensure endpoints use `AppError` patterns and centralized handlers; no direct `HTTPException` except framework handling — [In Progress].

### Testing
- ✅ Endpoint contract tests (request/response, validation) on current routes for documents and pipeline runs (skipped if env missing)
  - ✅ Integration tests for anonymous email-run flow (upload, run details, doc list/get, progress) with env skip guard
- Structured errors and `X-Request-ID` header asserted across new flat endpoints — [In Progress]

### Milestone
- Core document and indexing management refactored to shared services with access-aware behavior (in-place)

---

## Phase 8: API v2 — Queries and Wikis

Note: Executed now; performance upgrade (Phase 10) follows as Slice C.

### Tasks
- ✅ Implement `POST /api/queries`, `GET /api/queries`, `GET /api/queries/{id}` using content scoping by access level.
- ✅ Implement `POST /api/wikis`, `GET /api/wikis`, `GET /api/wikis/{id}`, `GET /api/wikis/{id}/pages` backed by Beam and Storage.
- ✅ Keep retrieval on current approach initially; ensure it uses 1024-dim embeddings and central config.
- ✅ Ensure endpoints use `AppError`/centralized handlers; no direct `HTTPException`.

### Testing
- ✅ Integration tests for anonymous and authenticated query flows; verify only accessible content is searched.
- ✅ Integration tests for wiki creation and page listing/retrieval with access enforcement.
- ✅ Error-path tests (invalid inputs, unauthorized access, missing resources).
- ✅ Tests assert standardized error envelope and `X-Request-ID` header.

### Follow-ups (Left)
- Ensure production DB has `query_runs.pipeline_config JSONB` (apply migration); then remove the insert fallback in the orchestrator.
- Add explicit test for `GET /api/queries/{id}` access rules (anonymous/public vs authenticated/owner).
- Add access-behavior tests per `access_level` across documents/indexing/wiki/query.
- Add assertions for standardized error envelope and `X-Request-ID` on the new flat query endpoints.
- Replace remaining `HTTPException` usages in legacy query routes with `AppError` for consistency.

### Milestone
- End-to-end functionality (query and wiki) exposed via v2 with access-aware behavior.

---

## Phase 9: Security Hardening

Note: Executed together with Phase 7 (scoped) as Slice B for endpoint security; remaining hardening continues here.

### Tasks
- Eliminate any remaining admin-client usage from user-scoped reads; rely on anon client with RLS or explicit filters. — [In Progress]
- Tighten CORS configuration for non-development environments. — [In Progress]
 - Remove or guard any debug endpoints in production configuration. — [Done]
- Perform full RLS review and rollout across `documents`, `indexing_runs`, `query_runs`, `wiki_generation_runs` (and related link tables). Align policies with `AccessLevel` semantics: public/auth/owner/private. Validate that normal client access matches service filters. — [To Do]


### Testing
- Integration tests asserting cross-user access is forbidden. — [In Progress]
- Configuration tests for CORS and environment-based toggles. — [To Do]

### Milestone
- Security baseline aligned with least privilege and consistent RLS usage.

---

## Phase 10: Retrieval Performance Upgrade (Post-v2 Stabilization)

Note: Follows Phase 8 as Slice C; implement SQL ANN/HNSW and performance tests here.

### Tasks
- Switch retrieval to SQL ANN using HNSW on `document_chunks.embedding_1024`, with WHERE filters for access control. — [To Do]
- Optionally add a reranking step using the current generation model. — [To Do]
- Consider batching/UPSERT improvements for embedding writes. — [To Do]

### Testing
- Correctness tests comparing top-k results with the legacy approach on a fixed corpus. — [To Do]
- Performance tests validating latency improvements and stability under load. — [To Do]

### Milestone
- Scalable, performant retrieval with DB-side vector search and proper access filters.

---

## Phase 11: Cleanup and Practices

### Tasks
- Remove dead code and any obsolete endpoints after branch merge. — [To Do]
- Document concise code practices (config SoT, error patterns, service usage) in an internal dev guide. — [To Do]
- Propose cleanup of temporary test artifacts/files once their purpose is served. — [To Do]

### Testing
- Full test suite green (unit, integration, e2e where applicable) from project root with venv activated. — [To Do]
- Lint/type checks pass. — [To Do]

### Milestone
- v2 completed, repository simplified, and maintainable patterns documented.

---

## Cross-cutting Acceptance Criteria

- Embedding model name and vector dimension are consistent across settings, configs, indexing, retrieval, and DB schema.
- All user-scoped reads respect RLS via anon client or explicit filters; admin client restricted to server-to-server tasks (Beam, maintenance).
- API error responses follow the standardized JSON structure with request IDs and error codes.
- New endpoints follow RESTful patterns with typed request/response models.
- Tests are runnable from the project root with the project venv activated.

---

## Notes

- Branch-based strategy avoids the need for runtime feature flags and deprecation headers.
- Performance upgrades (ANN retrieval, bulk embedding writes) are intentionally deferred until v2 API surfaces are stable.


---

## Execution Plan (Phases 4–9 Finish Order)

This plan sequences remaining In Progress and To Do items for Phases 4–9. As we complete items, we will update the task status flags above (Done/In Progress/To Do) in place.

1) Phase 7/4: Complete error and service backing
   - AppError sweep in API: replace remaining HTTPException raises with AppError across documents, pipeline, and wiki routes.
   - Back endpoints by services: ensure documents/indexing flat endpoints consistently call read/services instead of direct DB.
   - Tests: targeted assertions for standardized error envelope and X-Request-ID on affected routes.
   - Exit: all API routes in phases 4–8 return AppError envelopes; tests assert code/message/request_id.

2) Phase 5: Finalize Storage centralization
   - Resolver matrix: finalize anon vs admin selection by operation/access_level; keep admin for trusted server ops (bucket mgmt, uploads, signed URLs).
   - Service usage: remove remaining direct supabase.storage/from_ calls outside StorageService.
   - Tests: unit tests for resolver variants; env-gated integration for email and project uploads.
   - Exit: grep shows no direct .storage usage outside StorageService; uploads pass under RLS.

3) Phase 9: Admin→anon hygiene in reads
   - Clients: switch user-scoped reads (documents/indexing/query/wiki) to anon client; keep admin only where strictly needed.
   - Tests: env-gated cross-user denial tests for each resource; confirm owner-only visibility.
   - Exit: all user-scoped services use anon; denial tests pass.

4) Phase 9: RLS rollout and validation
   - Policies: align documents/indexing_runs/query_runs/wiki_generation_runs with access_level semantics (public/auth/owner/private).
   - Tests: env-gated checks that anon sees only public/email, auth sees own + public/auth, cross-user forbidden.
   - Exit: RLS policies applied; row access matches service filters.


6) Phase 7: Structured error assertions
   - Add assertions for standardized error envelope and X-Request-ID across flat endpoints (documents, indexing, wiki, queries).
   - Exit: tests green with envelope assertions for all flat endpoints.

7) Phase 9: CORS/debug hygiene
   - CORS: tighten for non-dev via settings; keep dev permissive.
   - Debug: remove/guard debug endpoints.
   - Tests: minimal config toggle tests.
   - Exit: CORS respects environment; no unguarded debug in prod.

8) Housekeeping (parallel, low risk)
   - Fix linter warnings (Depends defaults, long lines) and minor logging cleanup.
   - No functional changes.
