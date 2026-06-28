# Feature Research

**Domain:** CMMS — Computerized Maintenance Management System (naval facility, brownfield import)
**Researched:** 2026-06-28
**Confidence:** HIGH (legacy HTML fully analyzed; schema fully mapped; CMMS patterns well-established)

---

## Context for This Research

This is a **brownfield import milestone**, not a greenfield build. The system already has assets (`ativos`), work orders (`ordens_servico`), central inventory (`estoque`), named maintenance plans (`catalogo_planos`), preventive OS generation, and categorized maintenance tabs. The 5 features below come from legacy HTML mockups whose visual design is approved — the task is to wire them to `core.db`, not redesign them.

---

## Feature 1 — Registrar Uso (Asset Usage Recording)

### What It Is in CMMS

Asset usage recording is how usage-based preventive triggers know when to fire. The asset has a meter (`uso_atual`) that accumulates hours (h), kilometers (km), or calendar months depending on asset type. Each "use session" appends a delta to the meter. When `uso_atual >= proximo_uso` on any plan step, the system raises a preventive alert.

### Standard CMMS Behavior

**Data captured per use record:**
- `ativo_id` — which asset
- `data` — date of use (not necessarily today; field operators record retrospectively)
- `delta_uso` — hours worked or km driven (positive increment only)
- `operador_id` — who operated it (references `usuarios`)
- `combustivel_l` — fuel consumed (optional; relevant for vehicles and engines)
- `obs` — free text (area worked, conditions, incidents)
- `checklist_pre_uso` — JSON or boolean flags for pre-use checks (oil level, brakes, blades, belts, tires); these are safety gates, not blocking the save

**State changes:**
- `ativos.uso_atual += delta_uso` (atomic; must not allow negative values)
- Record appended to `uso_registros` (audit log, not just the running total)
- After update: evaluate open plan steps — if `uso_atual >= proximo_uso` on any step, mark alert

**What the legacy HTML (`CMASM_Gestao_v2.html`) already has:**
- Full UI: date + hours + fuel + operator + pre-use checklist + alert warning for overdue items
- Logic: `h.hor += h_in` (in-memory horímetro accumulation)
- Missing: persisted to `localStorage` only; no backend endpoint; no `uso_registros` log table in schema

**What the backend must add:**
- `POST /api/ativos/{id}/uso` — accepts `{data, delta_uso, operador_id, combustivel_l, obs, checklist}`; atomically increments `ativos.uso_atual`; inserts into a new `uso_registros` table
- New table: `uso_registros (id, ativo_id, data, delta_uso, uso_acumulado_apos, operador_id, combustivel_l, obs, checklist_json, criado_em)`
  - `uso_acumulado_apos` = snapshot of `uso_atual` after this record (for audit; makes log self-contained)
- `GET /api/ativos/{id}/uso` — paginated history for the "Registros Recentes" panel
- Edit/delete of a record: recalculate `uso_atual` by summing all `delta_uso` for that asset — do NOT allow direct edits to `ativos.uso_atual` from this endpoint; derive it from the log

**Table-stakes vs nice-to-have:**

| Behavior | Status |
|----------|--------|
| Increment `uso_atual` with a delta | TABLE STAKES |
| Persist a log record per session | TABLE STAKES |
| Record operator and date | TABLE STAKES |
| Pre-use checklist (safety items) | TABLE STAKES (blocking UX; non-blocking save is fine) |
| Fuel consumption field | TABLE STAKES for engines/vehicles; nice-to-have for others |
| Edit/delete a past record (with recalculation) | NICE-TO-HAVE (can be added after core works) |
| Alert overlay when overdue items exist | TABLE STAKES (already in legacy HTML) |
| Combustível sub-report / L per hour | NICE-TO-HAVE |

**Complexity:** LOW. The `uso_atual` column already exists on `ativos`. The main work is: new table + one POST endpoint + wiring the existing UI to call it instead of localStorage.

**Sync note:** The PMOC field app already emits `uso_atual_inc` sync events (`sync.py:_h_uso_atual_inc`). The new `uso_registros` table should be populated from that handler too so ERP and PMOC share one audit trail.

---

## Feature 2 — Maintenance Plan Applied to Selected Asset with Checkbox Service Items

### What It Is in CMMS

When a technician opens the maintenance tab for a specific asset, they see the plan steps applicable to that asset type, ordered by urgency. Each step is selectable via checkbox. Submitting the form registers which items were performed at the current meter reading.

### Standard CMMS Behavior

**The plan is already resolved by type** — in this system `catalogo_planos.aplicavel_tipos` maps plan steps to asset types. The UI needs to:
1. Receive the selected asset (from sidebar or asset picker)
2. Fetch plan steps for that asset's type via `GET /api/catalogo/planos-catalogo?tipo={tipo}`
3. Render each step as a checkbox row showing: step name, interval, current status (VENCIDA/URGENTE/PRÓXIMA/EM DIA), progress bar
4. On submit: persist which items were checked + current `uso_atual` + responsible technician + date + notes → creates a maintenance record that updates `proximo_uso` for each checked item

**Data model for the maintenance record:**
- `manut_registros (id, ativo_id, data, uso_no_momento, responsavel_id, obs, itens_json, criado_em)`
  - `itens_json`: array of `{plano_item_id, servico_id, nome}` — only checked items
- On each checked item: `proximo_uso = uso_no_momento + intervalo` on that plan step for this asset

**The key challenge — plan-to-asset assignment:**
Current system uses `catalogo_planos.aplicavel_tipos` (JSON array of type codes) as the assignment. No `plano_id` on individual `ativos`. This means: for a given asset, fetch all plans whose `aplicavel_tipos` includes the asset's `tipo`. This is the correct pattern; no schema change needed for the assignment itself.

**What the legacy HTML has:**
- Full rendering: `subManut()` renders each plan item as a checkbox card with status badge, progress bar, interval display
- `toggleMC()`: visual feedback on check (border color, background change)
- `regManut()`: collects checked IDs, records maintenance in memory, updates `ulm[pid] = h.hor`
- Also shows "Materiais urgentes/vencidos" panel and "Próximas manutenções" sidebar

**What the backend must add:**
- `GET /api/manutencao/vencimentos?ativo_id={id}` — returns plan steps with status for a specific asset (uses `ativos.uso_atual` + plan intervals). Note: `/api/manutencao/vencimentos?categoria=` already exists for the category-level view; needs a per-asset variant or the frontend resolves locally.
- `POST /api/manutencao/registrar` — `{ativo_id, data, responsavel_id, obs, itens:[{catalogo_plano_item_id}]}` — saves `manut_registros`, updates `proximo_uso` per item per asset (needs new table for per-asset plan state)
- New table: `ativo_plano_estado (ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso, PRIMARY KEY (ativo_id, catalogo_plano_item_id))`
  - This replaces the in-memory `ulm` (last-maintained-at per item) from the legacy HTML

**Table-stakes vs nice-to-have:**

| Behavior | Status |
|----------|--------|
| Show plan items as checkboxes for selected asset | TABLE STAKES |
| Show status per item (VENCIDA/URGENTE/PRÓXIMA/EM DIA) | TABLE STAKES |
| Show progress bar + "faltam X h" | TABLE STAKES |
| Require at least one item checked | TABLE STAKES (validation) |
| Require responsible technician | TABLE STAKES |
| Update `proximo_uso` per checked item | TABLE STAKES |
| Materials panel for urgent items | TABLE STAKES (already in legacy HTML) |
| Free-text notes per item | NICE-TO-HAVE (milestone notes, not blocking) |
| Photo attachment per item | OUT OF SCOPE |
| Auto-open OS from this screen | NICE-TO-HAVE (already exists via `novaOSComContexto`) |

**Complexity:** MEDIUM. Needs one new junction table (`ativo_plano_estado`) and a new POST endpoint. Frontend logic from legacy HTML is complete; wiring to backend is the work.

**Dependency:** Requires Feature 1 (Registrar Uso) to be working, because the maintenance trigger uses `uso_atual`.

---

## Feature 3 — Estoque de Sobressalentes (Technicians' Local Spare-Parts Stock)

### What It Is in CMMS

Distinct from the central warehouse inventory (`estoque` table), technicians maintain a local bench stock — a small working supply of consumables and spare parts kept in the workshop or tool room. In Brazilian naval maintenance, this is called "estoque de sobressalentes" (spare-parts stock) and is typically domain-specific (e.g., the refrigeration team has their own stock of filters, refrigerant, and oils).

### Standard CMMS Behavior vs Central Inventory

| Aspect | Central Inventory (`estoque`) | Local Spare-Parts (`estoque_sobressalentes`) |
|--------|-------------------------------|----------------------------------------------|
| Scope | Facility-wide | Per-category or per-team |
| Control | Warehouse manager | Technician or supervisor |
| Movements | Formal requisitions, OS debit | Informal top-up, direct consumption |
| Valuation | Full cost tracking | Simpler: unit price × qty |
| Reorder | Purchase order workflow | Replenishment request |
| Link to OS | Auto-debit on OS close | Manual adjustment |

**What the legacy HTML has (`CMASM_Gestao_v2.html`, `renderEstoque()`):**
- Full UI: table of parts with qty/unit price/estimated value
- Status badges: ZERADO (qty=0), BAIXO (qty≤2), OK
- Quick ±1 buttons + full adjust modal (new qty + motivo dropdown + obs)
- CRUD: new part modal (description, unit, category, unit price, initial qty, notes)
- Categories: óleo, graxa, filtro, motor, corte, correia, pneu, elétrico, químico, ferramenta, outro
- Movement log per part (last 30 events stored)
- Summary KPIs: total value, zero-stock count, etc.

**The refrigeration category already has its own stock:** 25 items seeded in `estoque` via `tools/seed_refrig_estoque.py` with `tipo IN ('consumivel','sobressalente','ferramenta')`. The `estoque` table has a `categoria` column. The "local spare-parts" for other categories (corte, transportes, etc.) either don't exist yet or are lumped into central stock.

**Options for import:**
- Option A (simpler, recommended): The existing `estoque` table already has `categoria` and `tipo` columns. Add a `scope` column: `central` (default, warehouse) vs `local` (tech bench). Filter the UI by scope. No new table needed.
- Option B: New `estoque_sobressalentes` table mirroring `estoque` but with `equipe` or `categoria_manut` field. Cleaner separation but duplicates the schema.

Recommendation: **Option A** — additive migration to `estoque`, add `scope TEXT DEFAULT 'central'`. The local stock page is then `GET /api/estoque?scope=local&categoria={x}`. Movement logic is identical.

**What the backend must add:**
- Additive migration: `ALTER TABLE estoque ADD COLUMN scope TEXT DEFAULT 'central'`
- Seed local spare-parts items per category (corte, transportes, etc.) with `scope='local'`
- `GET /api/estoque?scope=local&categoria=` filtered endpoint (or extend existing)
- `POST /api/estoque/{id}/movimentos` already handles adjustment; no change needed

**Table-stakes vs nice-to-have:**

| Behavior | Status |
|----------|--------|
| List of local parts with qty and status badges | TABLE STAKES |
| Quick ±1 adjustment buttons | TABLE STAKES |
| Full adjustment modal (qty + reason + notes) | TABLE STAKES |
| Add new part to local stock | TABLE STAKES |
| Movement log per part | TABLE STAKES |
| Total value KPI | TABLE STAKES |
| Zero-stock count / alert | TABLE STAKES |
| Auto-debit from local stock when OS closes | NICE-TO-HAVE (complex; can remain manual) |
| Replenishment request workflow | OUT OF SCOPE for this milestone |
| Barcode scanning | OUT OF SCOPE |

**Complexity:** LOW. Legacy HTML is complete. Option A migration is minimal. The main work is: seeding items per category + filtering endpoint.

---

## Feature 4 — Equipe Técnica (Technical Team / Crew Management)

### What It Is in CMMS

Crew management in a CMMS tracks who can do what maintenance work. In the simplest form: a roster of people with names and specialties. In more advanced systems: qualification tracking, certification expiry, workload allocation, shift definitions.

### Standard CMMS Behavior

**Minimum viable (table stakes):**
- Roster: name, military rank/post (posto/graduação), specialty/qualification, active/inactive status
- People can be "system users" (with login) or "crew members only" (appear on assignments but don't log in)
- Inactive people excluded from capacity calculations and assignment dropdowns

**Advanced (nice-to-have for this system):**
- Qualification certificates with expiry dates
- Workload per person per period
- Shift/schedule definitions per person

**What the legacy HTML has (`cmasm13-govbr-v8_3.html`, `renderTeam()`):**
- Configuration card: number of parallel teams, working days (checkboxes Mon–Sun), shifts per team per day (name + hours each)
- People roster table: name, posto/grad, especialidade, isUser flag, ativo flag
- CRUD modal: add/edit person (nome, posto, especialidade, isUser, ativo)
- Capacity summary auto-computed from config: h/dia/equipe, h/dia total, h/semana, h/mês, h/ano

**What already exists in the backend:**
- `usuarios` table with `nome`, `cargo`, `setor`, `role` fields — these are system users
- `qualificacoes_catalogo` + `usuario_qualificacoes` tables — qualification tracking already modeled
- `estrutura` table — organizational chart (79 nodes from seed)

**The gap:** The legacy HTML's "team" concept is separate from `usuarios`. It includes:
1. People who are crew members but not system users (e.g., assigned technicians who don't log into ERP)
2. Team/shift configuration (number of parallel teams, working days, shift hours) — this feeds the schedule calculation

**What the backend must add:**
- New table: `equipe_config (id, categoria TEXT, num_equipes INT, dias_uteis JSON, turnos JSON, criado_em, atualizado_em)` — stores the capacity configuration per maintenance category. Default: 1 team, Mon–Fri, 2 shifts of 2h each.
- New table (or extend `usuarios`): Option A — add `is_technician` + `especialidade` to `usuarios`. Option B — new `equipe_membros (id, usuario_id nullable, nome, posto, especialidade, categoria, ativo)`. Recommendation: **Option B** — some crew members won't have system logins; a separate table avoids bloating `usuarios`.
- `GET/PUT /api/equipe/config?categoria=` — read/write team capacity config
- `GET/POST/PUT/DELETE /api/equipe/membros?categoria=` — CRUD for roster

**Table-stakes vs nice-to-have:**

| Behavior | Status |
|----------|--------|
| Roster of team members with name, rank, specialty | TABLE STAKES |
| Active/inactive toggle (inactive excluded from capacity) | TABLE STAKES |
| "Is system user" flag (link to usuarios) | TABLE STAKES |
| Team config: number of teams, working days, shifts | TABLE STAKES (needed for Feature 5) |
| Edit/add/remove person | TABLE STAKES |
| Qualification display from `usuario_qualificacoes` | NICE-TO-HAVE (schema exists) |
| Per-person workload tracking | OUT OF SCOPE for this milestone |

**Complexity:** LOW–MEDIUM. Schema is straightforward. Two new tables, three new endpoint groups. The interesting part is linking `equipe_membros.usuario_id` optionally to `usuarios`.

**Dependency:** Feature 4 must come before Feature 5. The schedule calculation reads team config from Feature 4.

---

## Feature 5 — Cronograma de Manutenção Preventiva com Cálculo de Equipe

### What It Is in CMMS

A preventive maintenance schedule answers: "given our backlog of assets needing their first or next preventive, and given our team's capacity, what day does each asset get serviced?" This is a mobilization planner — not a calendar of fixed appointments, but an allocation algorithm that respects daily capacity.

### Standard CMMS Behavior

**The algorithm (from legacy HTML `pmocCronograma()`):**
1. Build a queue of all assets needing service (those with no maintenance history get "first preventive"; ongoing assets use `proximo_uso` date)
2. Sort queue by criticality (CRÍTICA → ALTA → MÉDIA → BAIXA), then by estimated service time (longest first within same criticality)
3. Walk forward through working days (skip weekends/holidays per `equipe_config.dias_uteis`)
4. Each day has capacity = `num_equipes × sum(shift_hours) × 60` minutes
5. Pack jobs into days greedily: if a job fits in remaining capacity, assign it; if it doesn't fit and the day already has jobs, open the next day
6. Output: per-day list of assets, estimated duration, criticality, cumulative workload vs capacity

**Service time estimation (from legacy HTML):**
- Formula: `n_checklist_items × min_per_item × fator_tipo_equipamento × fator_tipo_manutencao + setup_min`
- Defaults: 10 min/item, setup 15 min, type factors per equipment class (SPLIT 1.0, PISO/TETO 1.15, JANELA 0.7, SELF CONTAINED 1.6)
- Maintenance type factors: inspection 0.4, preventive 1.0, revision 1.6

**Key output KPIs:**
- Total mobilization OS count
- Total estimated person-hours
- Number of working days to complete
- Estimated completion date
- Capacity utilization % (demand vs supply); warning if >100%

**Recurrent vs initial mobilization:**
- Initial mobilization: assets with no maintenance history get their first preventive scheduled
- Recurrent PMOC: assets with history use `proximo_uso` date to determine urgency; sort by days-until-due
- The legacy HTML implements initial mobilization; recurrent needs `ativo_plano_estado` (Feature 2 output)

**What the legacy HTML has (`pmocCronograma()`):**
- Full algorithm for initial mobilization
- Day-by-day timeline with capacity bar, OS list, criticality color coding
- KPI summary row (OS count, person-hours, days, completion date)
- Informational note about methodology

**What the backend must add:**
- `GET /api/cronograma?categoria=&tipo=inicial|recorrente` — compute and return schedule
  - `inicial`: use assets without `ativo_plano_estado` records
  - `recorrente`: use `ativo_plano_estado` to find assets with `proximo_uso <= hoje + X days`
- Response shape: `{kpis:{...}, dias:[{data, capacidade_min, usado_min, os:[{ativo_id, nome, criticidade, tipo_manut, minutos_estimados}]}]}`
- Service time estimation can be computed backend-side (the formula is deterministic from asset type + checklist length)
- This is a **read-only computed view** — no persistent state; recalculate on each request

**Capacity vs demand view (Plano & Capacidade):**
- Aggregated annually: total demand hours vs total capacity hours
- Demand by criticality breakdown (table)
- Utilization bar with warning if >100%
- This also reads `equipe_config` + all `ativos` for the category

**Table-stakes vs nice-to-have:**

| Behavior | Status |
|----------|--------|
| Initial mobilization schedule (assets with no history) | TABLE STAKES |
| Sort by criticality + service time | TABLE STAKES |
| Respect working days from equipe_config | TABLE STAKES |
| Day-by-day capacity packing | TABLE STAKES |
| Capacity utilization KPIs (h/day, h/week, h/year) | TABLE STAKES |
| Completion date estimate | TABLE STAKES |
| Warning when demand > capacity | TABLE STAKES |
| Recurrent schedule (based on proximo_uso dates) | NICE-TO-HAVE (needs Feature 2 first) |
| Drag-and-drop rescheduling | OUT OF SCOPE |
| Export to PDF/Excel | NICE-TO-HAVE (tbl-enhance.js already handles this globally) |
| Assignment of specific technicians to specific OS | OUT OF SCOPE for this milestone |

**Complexity:** MEDIUM. The algorithm is already fully implemented in the legacy HTML JS. Backend port is mainly translating JS logic to Python, reading from real DB instead of localStorage. The hard dependency is Feature 4 (needs `equipe_config` to exist).

---

## Feature Landscape Summary

### Table Stakes (All 5 Must Ship)

| Feature | Why Expected | Complexity | Legacy HTML Gives | Backend Must Add |
|---------|--------------|------------|-------------------|------------------|
| Registrar Uso | Preventive triggers are meaningless without usage data | LOW | Full UI + form | `uso_registros` table + `POST /api/ativos/{id}/uso` |
| Plano c/ checkboxes | Core CMMS interaction — technician marks what was done | MEDIUM | Full UI + rendering | `ativo_plano_estado` table + `POST /api/manutencao/registrar` |
| Estoque Sobressalentes | Local stock is table stakes for any workshop | LOW | Full UI + CRUD | Additive migration `estoque.scope` + seeds |
| Equipe Técnica | Capacity calculation is meaningless without team data | LOW–MEDIUM | Full UI + config | `equipe_config` + `equipe_membros` tables + endpoints |
| Cronograma | "When will we get through backlog?" is the key manager question | MEDIUM | Full algorithm in JS | `GET /api/cronograma` + service time estimation |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Capacity utilization warning (>100%) | Surfaces understaffing before crisis, not after | LOW | Already in legacy HTML; feed real data |
| Pre-use checklist with overdue alert | Safety gate before operating equipment | LOW | Already in legacy HTML |
| Service time estimation formula | Turns vague "how long will this take?" into a number | LOW | Constants already tuned in legacy HTML |
| Criticality-based scheduling priority | CRÍTICA assets always serviced first, not first-come-first-served | LOW | Already in legacy HTML sort logic |

### Anti-Features (Do Not Build in This Milestone)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Per-technician schedule assignment | Looks like a CMMS feature | Adds complex workload balancing; this team is small enough to assign manually | Show OS list per day; supervisor assigns verbally |
| Real-time usage telemetry (IoT) | Automatic horímetro from machines | Hardware integration out of scope; adds ESP32 dependency | Manual `Registrar Uso` form is sufficient |
| Full procurement workflow for local stock | "We need to reorder" button | Full PO workflow is months of work | Reorder flag (stock low badge) is sufficient; actual PO happens outside this system |
| Per-person workload balancing | Fair distribution of jobs | Complex optimization; not needed at this team size | Capacity utilization at team level is sufficient |

---

## Feature Dependencies

```
Feature 1: Registrar Uso (uso_registros, /api/ativos/{id}/uso)
    └──required by──> Feature 2: Plano c/ Checkboxes
                          └──feeds──> Feature 5: Cronograma (recorrente mode)

Feature 4: Equipe Técnica (equipe_config, equipe_membros)
    └──required by──> Feature 5: Cronograma (capacity calculation)

Feature 3: Estoque Sobressalentes
    └──independent (no hard deps, enhances Feature 2 materials panel)
```

### Dependency Notes

- **Feature 2 requires Feature 1:** `ativo_plano_estado.ultimo_uso` is set from `ativos.uso_atual`, which must be reliably updated. Without Feature 1 working, the maintenance registration has no reliable meter reading to snapshot.
- **Feature 5 requires Feature 4:** The schedule algorithm reads `equipe_config.dias_uteis`, `equipe_config.num_equipes`, and `equipe_config.turnos` to compute daily capacity. Without that config, the algorithm falls back to the legacy default (1 team, Mon–Fri, 2h+2h) — which is acceptable for initial mobilization but not configurable.
- **Feature 5 recurrent mode requires Feature 2:** The recurrent schedule needs `ativo_plano_estado.proximo_uso` to know which assets are due. Initial mobilization (assets with no history) can run without Feature 2.
- **Feature 3 is independent:** No hard dependency on the other features. Can ship in any order.

---

## MVP Definition

### This Milestone (ship all 5 in order)

Recommended implementation order based on dependencies:

1. **Feature 1: Registrar Uso** — foundation; no dependencies; LOW complexity; unblocks Feature 2
2. **Feature 3: Estoque Sobressalentes** — independent; LOW complexity; easy win
3. **Feature 4: Equipe Técnica** — low complexity; unblocks Feature 5
4. **Feature 2: Plano c/ Checkboxes** — MEDIUM complexity; requires Feature 1
5. **Feature 5: Cronograma** — MEDIUM complexity; requires Feature 4; initial mobilization mode requires no other features

### Add After Initial Import (v1.x)

- Feature 5 recurrent mode (requires Feature 2 data to exist)
- Edit/delete uso records with horímetro recalculation
- Fuel sub-report per operator
- Qualification expiry warnings in Equipe Técnica roster

### Future Consideration (v2+)

- Per-technician job assignment within the daily schedule
- Procurement workflow integration for local stock replenishment
- IoT/PMOC sync of `uso_atual_inc` events to populate `uso_registros` automatically

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Registrar Uso | HIGH | LOW | P1 |
| Plano c/ Checkboxes | HIGH | MEDIUM | P1 |
| Estoque Sobressalentes | HIGH | LOW | P1 |
| Equipe Técnica | HIGH | LOW | P1 |
| Cronograma (inicial) | HIGH | MEDIUM | P1 |
| Cronograma (recorrente) | MEDIUM | MEDIUM | P2 |
| Qualification expiry alerts | MEDIUM | LOW | P2 |
| Local stock auto-debit on OS close | LOW | HIGH | P3 |

---

## Sources

- Legacy HTML analysis: `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (Features 1–3)
- Legacy HTML analysis: `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (Features 4–5)
- Existing schema: `data/schema_core.sql`, `data/schema_catalogo.sql`
- Architecture map: `.planning/codebase/ARCHITECTURE.md`
- Active backlog: `todo.md`
- CMMS domain patterns: industry-standard behavior (ISO 55000, ABNT NBR 5674, Portaria 3523/GM cited in reference docs)

---

*Feature research for: xCMASM ERP — brownfield import milestone*
*Researched: 2026-06-28*
