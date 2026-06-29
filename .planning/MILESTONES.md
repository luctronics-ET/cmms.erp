# Milestones

## v1.0 Produção: Import + Hardening (Shipped: 2026-06-29)

**Phases completed:** 9 phases, 20 plans, 12 tasks

**Key accomplishments:**

- Async pytest fixture (LifespanManager + ASGITransport) and Registrar Uso tab (API-backed, dark-theme, namespaced) completing IMP-01 vertical slice end-to-end
- Atomic SQLite backend for maintenance plan execution — GET /plano-ativo computes VENCIDA/URGENTE/PROXIMA/EM_DIA per item, POST /registro upserts ativo_plano_estado with anti-double-count proximo_uso inside a single aiosqlite transaction.
- Async manut sub-tab renderer using el()/textContent fetches GET /api/manutencao/plano-ativo and renders per-item checkboxes, status badges (VENCIDA/URGENTE/PROXIMA/EM_DIA), progress bars and "faltam X h"; regManut POSTs to /api/manutencao/registro with Bearer token and reloads the checklist on success.
- Dedicated local spare-parts inventory (sobressalentes) with badge/valor endpoints, atomic ajuste, and estoque-isolation proof via pytest.
- Sobressalentes tab in Manutenção with ZERADO/BAIXO/OK badges, valor estimado total, +Nova Peça/Editar forms, and Ajustar modal (motivo+obs) wired to Phase-3 endpoints via Bearer token.
- Roster CRUD + singleton config + derived capacity via `_capacidade()` helper using exact legacy formula (config-only, not member count).
- Equipe Técnica tab with roster CRUD (add/edit/soft-deactivate) and capacity-config panel showing backend-recomputed h/dia, h/semana, h/ano on save.
- Greedy day-packing scheduler for preventive maintenance with KPIs, ported from JS legacy into `GET /api/manutencao/cronograma` with deterministic tests.
- Dark-theme day-by-day preventive schedule tab with criticality badges, capacity bars, KPI header and red overload alert, fetching Wave 1 endpoint via Bearer token.
- Additive `locais.altura_m` migration + date-based por_tempo vencimento branch in both evaluation paths, with 6 targeted tests following TDD RED/GREEN cycle.
- 1. [Rule 1 - Bug] Fixed two existing tests broken by POST /api/locais gaining auth guard
- SR modal pre-fills stock item + qty from service context; refrigeration ficha exposes editable local selector (via PUT /api/pmoc/refrigeracao → _ATIVO_EDIT whitelist).
- JWT login handler upgraded from djb2 to Argon2id with transparent lazy-upgrade: first legacy login re-hashes and persists in-request; subsequent logins verify via argon2 path only.
- Removed all `_djb2("1234")` defaults from write paths; POST/PUT /api/usuarios now store Argon2id hashes when senha is provided, or empty string when absent — accounts without a provisioned password cannot authenticate.
- All Phase 1-5 manutencao routes now covered by passing tests; full suite 12 failed / 127 passed with 0 new regressions vs 14-failure baseline.
- SQLite schema (ajuda_topicos + docs_documentos + docs_versoes) e router FastAPI `/api/docs/*` com upload seguro (whitelist categoria/extensão, 25 MB cap, path server-controlled, normpath prefix check no download, attachment download, versão atômica aiosqlite).
- pytest suite (10 tests) covering DOC-01 ajuda upsert, DOC-02 versioned upload/download with history, DOC-03 categoria filter, 4 security rejections (extension/oversize/traversal/403), and migration idempotency — all green with zero regressions beyond the documented 12-failure baseline.
- Vanilla JS IIFE module wiring a Documentos repository page (browse/upload/history/download with tipo badges) and a contextual help "?" drawer with a DOM-only safe markdown renderer — zero innerHTML of server content.
- CLN-01

---
