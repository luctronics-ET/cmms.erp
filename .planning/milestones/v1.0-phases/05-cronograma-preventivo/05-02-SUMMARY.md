---
phase: 05-cronograma-preventivo
plan: 02
subsystem: frontend/manutencao
tags: [scheduling, preventive-maintenance, frontend, tab, dark-theme, vanilla-js]
status: complete

dependency_graph:
  requires:
    - Phase 05 Plan 01: GET /api/manutencao/cronograma endpoint (dias+kpis JSON)
    - assets/erp-manutencao.js TAB_DEFS + RENDERERS dispatch infrastructure
    - Phase 4 equipe_config (crew capacity, working days)
  provides:
    - Cronograma tab in Manutenção nav (id='cronograma', icon=📅)
    - async cronograma(cont) renderer in RENDERERS
  affects:
    - assets/erp-manutencao.js — 226 lines added (1 TAB_DEFS entry + 225-line renderer)

tech_stack:
  added:
    - CRIT_COLOR_DARK: module-local badge color map (CRÍTICA→red, ALTA→amber, MÉDIA→acc, BAIXA→green)
    - crToken()/crAuthHeaders(): local token helpers (mirror of eqToken/eqAuthHeaders pattern)
  patterns:
    - Async tab renderer (mirror of equipe-tecnica renderer structure)
    - el()/textContent for all server data (T-05-05 DOM safety)
    - Loading placeholder → fetch → replaceChildren pattern
    - Capacity bar: width = Math.min(100, usadoH/dispH×100)%, color-coded by saturation

key_files:
  modified:
    - assets/erp-manutencao.js:
        - line 32: TAB_DEFS entry { id: 'cronograma', icon: '📅', label: 'Cronograma' }
        - lines 2429-2653: async cronograma(cont) renderer in RENDERERS

decisions:
  - key: "Shorthand method syntax for renderer"
    rationale: |
      Used `async cronograma(cont) {}` (shorthand, no quotes) in RENDERERS object,
      consistent with how other renderers like `dashboard(cont)` are defined.
      renderActiveTab dispatches RENDERERS[id](cont) which resolves correctly.
  - key: "CRIT_COLOR_DARK defined inside renderer"
    rationale: |
      Per plan spec. Keeps the mapping co-located with the renderer that uses it.
      No global namespace pollution.
  - key: "Alert banner uses rgba(239,68,68,.15) background"
    rationale: |
      Matches the dark-theme error banner pattern used by showErrorBanner() in the
      same file — consistent visual language for red alerts.
  - key: "barFill color tied to utilization percentage"
    rationale: |
      >90% → var(--red), >70% → var(--amber), else → var(--acc). Provides at-a-glance
      overload warning without additional badges.

metrics:
  duration: "~10 min"
  completed: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
  lines_added: ~226
---

# Phase 05 Plan 02: Cronograma Tab Frontend Summary

**One-liner:** Dark-theme day-by-day preventive schedule tab with criticality badges, capacity bars, KPI header and red overload alert, fetching Wave 1 endpoint via Bearer token.

---

## What Was Built

### Task 1: TAB_DEFS entry

Added `{ id: 'cronograma', icon: '📅', label: 'Cronograma' }` to the TAB_DEFS array in `assets/erp-manutencao.js` (line 32), immediately after the `'equipe-tecnica'` entry. The tab `id` matches the RENDERERS key exactly for `renderActiveTab` dispatch.

### Task 2: async cronograma(cont) renderer

Added to the RENDERERS object (lines 2429–2653) mirroring the `equipe-tecnica` async renderer pattern:

**Auth helpers:**
- `crToken()` reads `localStorage.getItem('xcmasm_token')`
- `crAuthHeaders()` returns `{ Authorization: 'Bearer ' + crToken() }`

**Loading state:** `cont.replaceChildren(…'Calculando cronograma…'…)` shown immediately.

**Fetch:** `GET /api/manutencao/cronograma` with Bearer header. Non-OK → error card with status + `detail`. Network error → catch → error card with message.

**KPI header (5 cards in auto-fit grid):**

| Card | Source field |
|------|-------------|
| Total de OS | kpis.total_os |
| Horas-pessoa | kpis.horas_pessoa + 'h' |
| Dias úteis | kpis.dias_uteis |
| Conclusão | kpis.data_conclusao |
| Utilização | kpis.pct_utilizacao + '%' |

**Alert banner:** When `kpis.alerta === true` — red background `rgba(239,68,68,.15)`, `border: var(--red)`, text "Demanda excede a capacidade da equipe no horizonte".

**Day-by-day cards:** For each `dia` in `dias[]`:
- Header: `dia.data · dia.dia_semana` (left) + `N OS · Xh / Yh` (right)
- Capacity bar: outer `var(--bg2)` track + inner fill at `Math.min(100, usadoH/dispH×100)%`; color coded: >90%→red, >70%→amber, else→acc
- Item rows: `CRIT_COLOR_DARK[item.criticidade]` badge + `item.nome` (textContent) + duration (`duracao_h`+'h' or `duracao_min`+' min')

**CRIT_COLOR_DARK mapping:**
```
CRÍTICA → var(--red)
ALTA    → var(--amber)
MÉDIA   → var(--acc)
BAIXA   → var(--green)
```

**Empty state:** If `dias.length === 0`, shows "Nenhum ativo com manutenção preventiva pendente."

---

## Verification Results

- `node --check assets/erp-manutencao.js` — **SYNTAX OK**
- `python -m pytest tests/test_manutencao_smoke.py -q` — **6 passed, 0 failed**
- No `innerHTML` for server-supplied data in renderer (T-05-05 mitigated)
- TAB_DEFS 'cronograma' entry confirmed at line 32
- RENDERERS `async cronograma(cont)` confirmed at line 2429

---

## Human-Verify (Deferred — Non-blocking)

The plan's Task 2 includes a `<human-check>` verification that requires the backend running with seeded data:

**Steps (for gestor / human QA):**
1. Start: `uvicorn backend.main:app --port 8010 --reload`
2. Open ERP → Manutenção → Cronograma tab (📅)
3. Verify:
   - (a) Day-by-day list renders with criticality badges in dark-theme colors and capacity bar per day
   - (b) KPI header shows total OS / horas-pessoa / dias úteis / conclusão / % utilização
   - (c) Red alert banner appears when demand exceeds capacity (set tiny crew config in Equipe Técnica, reload)
   - (d) Changing Fase 4 crew config and reopening the tab changes the schedule

This checkpoint is deferred as non-blocking per plan instructions.

---

## Deviations from Plan

None. Plan executed exactly as written.

- Task 1: TAB_DEFS entry added (1 line, after equipe-tecnica) — commit ce549c2
- Task 2: Renderer added (225 lines) to RENDERERS object — commit 1c4e78a
- Renderer mirrors equipe-tecnica pattern: crToken/crAuthHeaders, loading placeholder, fetch, error card, replaceChildren
- CRIT_COLOR_DARK uses design system CSS vars per CLAUDE.md (not gov.br light palette)

---

## Known Stubs

None. The renderer fetches live data from the Wave 1 endpoint.

---

## Threat Flags

No new security surface introduced. All planned mitigations applied:
- T-05-05: All server strings rendered via `el()/textContent` — no `innerHTML` for server data
- T-05-06: Bearer token from `localStorage('xcmasm_token')` sent on GET; endpoint enforces `_require_auth`

---

## Self-Check: PASSED

- `assets/erp-manutencao.js` modified: FOUND
- TAB_DEFS 'cronograma' entry at line 32: FOUND
- RENDERERS async cronograma(cont) at line 2429: FOUND
- Commit ce549c2 (Task 1 — TAB_DEFS): FOUND
- Commit 1c4e78a (Task 2 — renderer): FOUND
- `node --check assets/erp-manutencao.js`: PASSED
- `python -m pytest tests/test_manutencao_smoke.py -q`: 6 passed, 0 failed
