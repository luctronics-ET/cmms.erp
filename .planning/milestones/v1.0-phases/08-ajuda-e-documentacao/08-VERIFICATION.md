---
phase: 08-ajuda-e-documentacao
verified: 2026-06-29T12:00:00Z
status: passed
score: 7/8
behavior_unverified: 1
overrides_applied: 0
human_verification:
  - test: "Abrir o ERP no browser, clicar '?' no topbar — drawer de ajuda abre mostrando o tópico da página ativa. Como gestor, clicar Editar, alterar o texto, Salvar — reabrir e confirmar que o conteúdo persiste. Verificar que bold/listas são renderizados corretamente (não como markup bruto)."
    expected: "Drawer abre, exibe conteúdo renderizado em markdown seguro, salva via PUT /api/docs/ajuda/{chave}, reaparece atualizado."
    why_human: "Comportamento visual interativo + estado DOM após animação + renderização markdown — não verificável por grep ou testes unitários."
  - test: "Clicar 'Documentos' na sidebar — página carrega com filtros categoria + tipo. Criar um documento (+ Novo documento), fazer upload de PDF (v1), upload novamente (v2). Abrir Histórico e confirmar ambas as versões com autor e data. Clicar Baixar v1 — confirmar que o arquivo baixado é o v1."
    expected: "Página lista documentos, upload incrementa versão, histórico mostra v1 e v2 preservadas, download v1 retorna bytes do v1."
    why_human: "Fluxo visual completo com file input, FormData multipart, Blob URL download e renderização de lista — não testável sem browser real."
  - test: "Tentar fazer upload de um arquivo .exe — confirmar que a UI exibe a rejeição (4xx do backend) sem adicionar versão."
    expected: "Toast/mensagem de erro exibida; nenhuma versão criada na lista."
    why_human: "Feedback visual de rejeição no DOM — requer interação real com file picker."
  - test: "Logar como visualizador — confirmar que os botões de escrita (+ Novo documento, Upload de versão, Editar ajuda) estão ocultos ou retornam 403 ao backend."
    expected: "Controles de escrita invisíveis para visualizador; qualquer chamada de escrita resulta em 403."
    why_human: "Condicional de role client-side + bloqueio server-side — a lógica client-side exige inspeção visual no browser."
behavior_unverified_items:
  - truth: "Help markdown is rendered without innerHTML of untrusted content — via textContent/createTextNode DOM building only (XSS defense)"
    test: "Abrir o drawer de ajuda com conteúdo contendo '<script>alert(1)</script>' e '<img onerror=alert(1) src=x>' e verificar que nenhum alert é disparado e o markup é exibido como texto literal."
    expected: "O conteúdo malicioso é exibido como texto puro; nenhum script executa; sem innerHTML de conteúdo do servidor."
    why_human: "A implementação usa exclusivamente textContent/createTextNode (verificado por grep) mas a garantia de não-execução XSS só pode ser provada com execução real no browser."
---

# Phase 08: Ajuda e Documentacao — Verification Report

**Phase Goal:** Contextual help system (DOC-01), versioned document repository (DOC-02), and category-organized norms/guides (DOC-03) available to ERP users.
**Verified:** 2026-06-29T12:00:00Z
**Status:** human_needed (7/8 truths verified; 1 behavior-unverified truth; 4 human-verification items)
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/docs/ajuda?chave=X returns topic; PUT /api/docs/ajuda/{chave} upserts preserving id (DOC-01) | VERIFIED | `backend/docs.py` lines 163-206: GET with chave query, PUT with ON CONFLICT DO UPDATE. `test_ajuda_upsert_persists` passes: PUT twice same chave → same id, GET returns updated content. |
| 2 | POST /api/docs/documentos creates; POST /api/docs/documentos/{id}/versoes uploads version = MAX(versao)+1, prior versions preserved (DOC-02) | VERIFIED | `docs.py` lines 292-374: atomic SELECT COALESCE(MAX(versao),0)+1 + INSERT in one aiosqlite connection. `test_upload_versao_increments_and_preserves_history` passes: v1→v2 confirmed, both rows in DB with autor+data. |
| 3 | GET /api/docs/documentos?categoria=&tipo= lists docs by PMOC category and tipo with latest version (DOC-02, DOC-03) | VERIFIED | `docs.py` lines 211-248: SQL filter on categoria and tipo with COALESCE MAX(versao). `test_documento_create_and_list_by_categoria` passes: geral filter returns doc, refrigeracao filter excludes it. |
| 4 | GET /api/docs/documentos/{id}/versoes/{versao}/download streams exact bytes with original filename (DOC-02) | VERIFIED | `docs.py` lines 377-420: FileResponse with arquivo_nome as filename; os.path.normpath + abspath prefix guard. `test_download_returns_correct_bytes` passes: v1 bytes exactly returned; Content-Disposition: attachment confirmed. |
| 5 | Visualizador gets 403 on PUT ajuda, POST documentos, POST versoes; all GET/download require auth (RES-05) | VERIFIED | `docs.py` _require_escrita() at lines 106-109, called on all write endpoints. `test_visualizador_write_403` passes: all 3 write endpoints return 403; GET /ajuda returns 200 for visualizador. |
| 6 | Uploads with non-whitelisted extension, non-whitelisted categoria, or size over cap are rejected 4xx; stored path never derives from client filename (path-traversal defense) | VERIFIED | ALLOWED_CATS frozenset (line 47), ALLOWED_EXTS frozenset (line 58), MAX_UPLOAD_BYTES=25MB (line 75); path = `<doc_id>_v<versao><ext>` only. `test_extension_rejected` (400 for .exe/.sh/.zip), `test_oversize_rejected` (413 for 17 bytes with cap=16), `test_path_traversal_defense` (400/422 for bad categorias) all pass. |
| 7 | Migrations are additive and idempotent; db.init() twice raises no error; ajuda_topicos, docs_documentos, docs_versoes exist with UNIQUE(documento_id,versao) | VERIFIED | `schema_docs.sql` uses CREATE TABLE IF NOT EXISTS throughout. `test_migracoes_idempotentes` passes: double db.init() OK, all 3 tables confirmed, UNIQUE constraint confirmed in DDL. Direct migration check also confirmed (see Step 7b). |
| 8 | Help markdown is rendered without innerHTML of untrusted content — via textContent/createTextNode DOM building only (XSS defense) | PRESENT_BEHAVIOR_UNVERIFIED | `erp-docs.js` renderMdSafe() at lines 124-160 and _applyInline() at lines 104-122 use exclusively createElement/textContent/createTextNode. Node check confirms 0 non-empty innerHTML assignments. Code is present and wired. Runtime XSS non-execution requires browser verification. |

**Score:** 7/8 truths verified (1 present, behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/schema_docs.sql` | SQLite schema: ajuda_topicos, docs_documentos, docs_versoes | VERIFIED | Exists (63 lines); all 3 tables with CREATE TABLE IF NOT EXISTS; UNIQUE(documento_id, versao) present in docs_versoes DDL; indexed correctly. Tables prefixed docs_ to avoid collision with legacy documentos table in schema_core.sql. |
| `backend/docs.py` | FastAPI router with all /api/docs/* endpoints | VERIFIED | Exists (421 lines); router prefix=/api/docs; ALLOWED_CATS (8 categories), ALLOWED_EXTS (14 types), MAX_UPLOAD_BYTES=25MB; all 7 route families registered and confirmed via `python -c "import backend.docs, backend.main"`. |
| `tests/test_docs.py` | Pytest suite covering all DOC behaviors and security | VERIFIED | Exists (699 lines); 10 tests: test_ajuda_upsert_persists, test_documento_create_and_list_by_categoria, test_upload_versao_increments_and_preserves_history, test_download_returns_correct_bytes, test_extension_rejected, test_oversize_rejected, test_path_traversal_defense, test_visualizador_write_403, test_migracoes_idempotentes, test_ajuda_list_all. All 10 pass. |
| `assets/erp-docs.js` | Frontend IIFE module: Documentos page + help drawer + safe MD renderer | VERIFIED | Exists (837 lines); 'use strict' IIFE; renderMdSafe + _applyInline present; 0 non-empty innerHTML assignments; /api/docs/documentos and /api/docs/ajuda endpoints called with Bearer token; mount(), openAjuda(), closeAjuda() exposed on window.erpDocs. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `data/schema_docs.sql` | `backend/db_core.py` `_SCHEMAS` | `os.path.join(_DATA_DIR, "schema_docs.sql")` | WIRED | `db_core.py` line 12: schema_docs.sql is the 5th entry in `_SCHEMAS`. db.init() creates all 3 tables. Verified by direct migration test. |
| `backend/docs.py` | `backend/main.py` | `from .docs import router as docs_router` + `app.include_router(docs_router)` | WIRED | `main.py` line 27: import; line 334: include_router. All 7 /api/docs/* routes confirmed registered. |
| `assets/erp-docs.js` | `cmasm_erp.html` | `<script src="assets/erp-docs.js" defer></script>` at line 549 | WIRED | Script tag present, deferred, after pmoc-engine.js load order. |
| `cmasm_erp.html` nav | `#page-documentos` | `data-page="documentos"` onclick `showPage('documentos',this)` | WIRED | Line 658: nav item present in sidebar. Line 1433: `#page-documentos` page container. Line 3106: `documentos: ()=>{ if(window.erpDocs&&window.erpDocs.mount) window.erpDocs.mount(); }` in renders map. |
| Help button | `window.erpDocs.openAjuda` | `.sb-tools` button onclick derives chave from `.ni.active` dataset.page | WIRED | Line 793: button present with inline handler reading active nav page's data-page attribute. |
| `erp-docs.js` mount() | `#docs-root` | `document.getElementById('docs-root')` fallback to `#page-documentos` | WIRED | Line 602 in erp-docs.js; `#docs-root` div exists inside `#page-documentos` (cmasm_erp.html line 1435). |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `erp-docs.js` renderDocsList | `docsState.docs` | `authFetch('/api/docs/documentos?...')` → `_db().fetch_all(sql, params)` | Yes — live SQL query with categoria/tipo filters | FLOWING |
| `erp-docs.js` openAjuda drawer | `_ajudaData` | `authFetch('/api/docs/ajuda?chave=...')` → `_db().fetch_one(...)` | Yes — live SQL query on ajuda_topicos | FLOWING |
| `backend/docs.py` list_documentos | `docs_documentos JOIN docs_versoes` | `_db().fetch_all(sql, params)` with COALESCE(MAX(versao)) | Yes — real DB query with filters and latest-version aggregation | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| test_docs.py (10 tests) | `python -m pytest tests/test_docs.py -q` | 10 passed, 0 failed | PASS |
| test_manutencao.py (24 tests) regression | `python -m pytest tests/test_docs.py tests/test_manutencao.py -q` | 34 passed, 0 failed | PASS |
| Full suite regression | `python -m pytest tests/ -q --tb=no` | 12 failed (pre-existing baseline), 138 passed | PASS (no new failures) |
| Router routes registered | `python -c "import backend.docs, backend.main; ..."` | All 7 /api/docs/* routes confirmed | PASS |
| erp-docs.js safety check | `node -e "... no non-empty innerHTML ..."` | OK erp-docs.js safe + wired | PASS |
| cmasm_erp.html wiring check | `node -e "... documentos nav + page + script + openAjuda ..."` | OK cmasm_erp.html wired | PASS |
| Migration idempotency (direct) | `python -c "asyncio.run(db.init()); asyncio.run(db.init())"` | All 3 tables present; no error | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DOC-01 | 08-01, 08-02, 08-03 | Contextual help: user opens help panel/button and sees page text; manager edits and saves (ajuda_topicos) | SATISFIED | GET /api/docs/ajuda endpoint returns topic; PUT upserts preserving id (ON CONFLICT DO UPDATE). Help button wired in .sb-tools. test_ajuda_upsert_persists passes. Human verification needed for UI interaction. |
| DOC-02 | 08-01, 08-02, 08-03 | Manager uploads new version → version increments, autor+data recorded, prior version preserved; download; navigate repository | SATISFIED | Atomic MAX(versao)+1, UNIQUE(documento_id,versao) backstop. test_upload_versao_increments_and_preserves_history and test_download_returns_correct_bytes pass. Human verification needed for full browser flow. |
| DOC-03 | 08-01, 08-02, 08-03 | Documents and guides organized by category (PMOC categories) | SATISFIED | GET /api/docs/documentos?categoria=&tipo= filter; ALLOWED_CATS includes all 7 PMOC categories + geral; tipo filter covers norma/guia. test_documento_create_and_list_by_categoria passes. Frontend categoria+tipo selectors wired in erp-docs.js. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/docs.py` | 193, 262 | `datetime.utcnow()` deprecated in Python 3.12+ | Info | DeprecationWarning in tests; no functional impact. Not a TBD/FIXME/XXX marker. |

No TBD, FIXME, or XXX debt markers found in phase files. No stub patterns. No empty return values in rendering paths.

---

### Human Verification Required

#### 1. Contextual Help Drawer — Open and Edit (DOC-01)

**Test:** Serve the app (`python3 -m http.server 8080`) and start the backend (`uvicorn backend.main:app --port 8010 --reload`). Log in as a write-capable user. Click "?" in the topbar — the help drawer should slide open showing the current page's ajuda topic. As a manager, click "Editar", change the content, click "Salvar". Close and reopen the drawer to confirm content persists.
**Expected:** Drawer opens with safe-rendered markdown (bold and lists visible, no raw `**` or `#` markup). Edit mode allows changing content. After saving, reopening shows the updated text.
**Why human:** Visual animation, DOM state after transition, markdown rendering quality, and persistence across opens are not testable via grep or unit tests.

#### 2. Documentos Page — Browse, Upload Versions, Download (DOC-02, DOC-03)

**Test:** Click "Documentos" in the sidebar. Create a document via "+ Novo documento" under categoria "geral", tipo "modelo". Upload a small PDF — confirm versao 1 appears. Upload a different PDF — confirm versao 2. Open "Histórico" and confirm both versions with autor and data. Click "Baixar" on versao 1 and confirm the downloaded file is the v1 file (not v2 content).
**Expected:** Page renders with categoria and tipo filters. Each upload increments the version counter. History shows both entries. Version-specific download returns correct bytes.
**Why human:** file input interaction, FormData multipart POST, Blob URL download, and visual list rendering require a real browser session.

#### 3. Extension Rejection — UI Feedback (Security)

**Test:** In the Documentos page, try uploading a file with .exe extension via "Upload de versão". Confirm the UI surfaces the backend's 400 rejection.
**Expected:** Error message/toast appears; no new version is shown in the list.
**Why human:** The backend rejection is proven by tests; the UI error surfacing in the DOM is not testable without a browser.

#### 4. Visualizador Role — Write Controls Hidden (RES-05)

**Test:** Log in as a user with role "visualizador". Navigate to Documentos and the help drawer. Confirm that "+ Novo documento", "Upload de versão", and the help "Editar" button are absent or trigger 403.
**Expected:** Write affordances not rendered (canWrite() returns false for visitante/visualizador role); any write attempt returns 403 from the backend.
**Why human:** Client-side role-gating requires visual inspection; `canWrite()` logic reads from localStorage which requires a real login session.

---

### XSS Safety — Behavior Unverified

The `renderMdSafe()` function (erp-docs.js lines 124-160) and `_applyInline()` (lines 104-122) use only `createElement`, `textContent`, and `createTextNode`. Zero non-empty `.innerHTML =` assignments exist in the file (confirmed by node grep check). The mechanism is present and structurally correct. However, runtime non-execution of injected scripts (e.g., `<script>alert(1)</script>` or `<img onerror=...>` in a malicious ajuda topic) can only be proven in a real browser environment.

---

### Gaps Summary

No gaps found. All 7 verified truths have full artifact + wiring + data-flow evidence confirmed by passing pytest tests and direct code inspection. The 1 PRESENT_BEHAVIOR_UNVERIFIED truth (XSS safety) is structurally sound — the implementation is correct — but the runtime guarantee requires human browser verification. The 12 full-suite failures are the documented pre-existing baseline (test_catalogo.py x10, test_import_ata2_climatizacao x1, test_sync x1), unchanged by this phase.

---

_Verified: 2026-06-29T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
