### GA Readiness – Minimal Implementation Plan

This short plan captures what to do next to move from pilot to GA. Keep scope tight; ship in small PRs with tests.

### Launch stance

- **Pilot/soft launch**: Yes, with caveats
  - Core value works: upload → index → query → wiki; SoT configs; error envelopes; logging
  - Acceptable for controlled tenants
- **Public/GA**: Not yet. Address the tasks below first (ordered)

### Critical path (ordered)

1) **RLS + client hygiene**
   - Switch remaining user-scoped reads to anon client; keep admin for trusted server ops (Beam, storage mgmt)
   - Roll out RLS for `documents`, `indexing_runs`, `query_runs`, `wiki_generation_runs` to match `public/auth/owner/private`
   - Tests: cross-user denial; anon sees only public/email; auth sees own + public/auth

2) **Storage centralization**
   - Ensure all storage ops go through `StorageService` + `StorageClientResolver`
   - Remove any direct `supabase.storage.from_` calls outside the service
   - Tests: unit (resolver matrix), env-gated upload/list/download happy/error paths

3) **Error envelope sweep**
   - Replace any remaining `HTTPException` with `AppError` in flat endpoints (documents, indexing-runs, queries, wiki)
   - Tests: assert envelope `{code,message,request_id,timestamp}` and `X-Request-ID` on error paths

4) **Resource-claims (if required by UX)**
   - Minimal endpoint to claim anonymous resources after signup; service method to transfer ownership
   - Tests: claim success/failure; access transitions from public→private/owner

5) **Projects v2 (if in MVP scope)**
   - Expose basic project CRUD; wire filters consistently in list/get
   - Tests: owner-only access; filtering on project_id

### Quick, low-risk improvements (1–3 days)

- **Pydantic v2 standardization**: use `model_config = ConfigDict(...)`; add minimal `BaseResponse` for new endpoints
- **Introduce `BasePipelineRun`** and refactor `IndexingRun`/`QueryRun` to inherit (no API change; trims duplication)
- **Admin→anon audit in reads**: convert where safe; add guard tests

### Suggested sequencing (with rough estimates)

1) RLS + client hygiene (2–3 days)  → highest risk reduction first
2) Storage centralization (1–2 days)
3) Error envelope sweep (0.5–1 day)
4) Resource-claims (0.5–1 day, optional)
5) Projects v2 (1–2 days, optional)
6) Quick wins (in parallel where safe, 1–3 days total)

### Definition of Done (GA gate)

- [ ] User-scoped reads use anon client; admin restricted to trusted server ops
- [ ] RLS policies applied and validated for all core resources
- [ ] No direct storage usage outside `StorageService`; resolver decisions covered by tests
- [ ] Error envelope + `X-Request-ID` asserted across flat endpoints
- [ ] (If in scope) Resource-claims and/or Projects v2 endpoints exposed with tests
- [ ] CI green: lint/type/tests; env-gated integration tests pass

### Notes

- Keep performance work (ANN/Rerank) out of scope until GA baseline is secure.
- Ship as small PRs; run tests with the project venv activated.


