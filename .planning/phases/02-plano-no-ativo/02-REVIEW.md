---
phase: 02-plano-no-ativo
reviewed: 2026-06-28T21:45:00-03:00
depth: deep
files_reviewed: 4
files_reviewed_list:
  - data/schema_manutencao.sql
  - backend/manutencao.py
  - tests/test_manutencao.py
  - assets/erp-manutencao.js
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: findings
---

# Phase 02: Plano no Ativo — Code Review Report

**Reviewed:** 2026-06-28T21:45:00-03:00
**Depth:** deep (cross-file, call-chain tracing)
**Commits reviewed:** fd39d8d (schema), 3730794 (endpoints), 7725c75 (tests), 67377b5 (frontend)
**Files Reviewed:** 4
**Status:** findings

## Summary

Four files reviewed covering the full vertical slice: SQL schema, two new FastAPI
endpoints (GET `/plano-ativo`, POST `/registro`), the test suite, and the frontend
sub-tab renderer.

Backend is sound on the focus checklist:

- **Atomicity**: all `HTTPException` raises in step (b) of `registrar_manutencao`
  occur before the first `conn.execute` write; the audit INSERT at step (c) is never
  reached on validation failure. Single `conn.commit()` at step (e) is the only
  commit path. `aiosqlite.Connection.__aexit__` calls `close()` without committing,
  so any uncommitted changes are rolled back by SQLite on connection close. Correct.
- **Anti-double-count**: `novo_proximo = uso_no_momento + item["iv"]` reads
  `uso_no_momento` fresh from the DB inside the transaction; does not accumulate from
  `proximo_uso`. The `ON CONFLICT DO UPDATE` overwrites both columns.
  `test_plano_no_ativo` proves the invariant with an explicit intermediate `UPDATE`.
- **`por_tempo` guard**: checked before `float(f["valor"])` in both GET and POST.
  `por_tempo` items return from the upsert loop via `continue`; they do reach the
  audit row (intentional by the comment on line 520).
- **SQL injection**: all parameters use `?` placeholders. No f-string interpolation
  in any SQL string.
- **Auth**: `_require_auth` required on both endpoints. `operador` derived from
  token query result, never from `RegistroIn` payload.
- **XSS**: `renderSubManutAPI` uses `el()`/`textContent` throughout; no `innerHTML`
  of server data.
- **`renderSub` routing**: `activeSub === 'manut'` early-return prevents
  `SUBS['manut']` lookup (key absent). No double-render.
- **`_mnRespEl` staleness**: `regManut()` reads `window._manutD._mnRespEl?.value`
  with optional-chain; if the async render has not yet completed `_mnRespEl` is
  `undefined`, `?.value` returns `undefined`, `|| ''` gives `''`, and the `!resp`
  guard catches it cleanly.

Two issues found — one in the frontend visual logic and one in the display string
for items with no interval.

---

## Critical Issues

### CR-01: Label `onclick` reads checkbox state *before* toggle — visual feedback is inverted

**File:** `assets/erp-manutencao.js:1975-1978`

**Issue:** When the user clicks the `<label>` element that wraps the checkbox, the
browser fires the label's `onclick` handler *before* toggling `cb.checked`. At the
moment the handler runs, `cb.checked` still holds the pre-click value, so the
conditional is backwards:

- User clicks an **unchecked** item → `cb.checked` is `false` → border stays
  `var(--line)` and background stays `var(--panel)` — looks like nothing happened.
- User clicks an already **checked** item → `cb.checked` is `true` → border turns
  `var(--acc)` and background turns highlighted — the item appears to be selected
  while actually becoming deselected.

The underlying checkbox toggles correctly (the `querySelectorAll('._mn-cb:checked')`
collection in `regManut` will be accurate at submission time), but the visual
feedback that guides the user to know which items are selected is consistently
wrong throughout the interaction.

**Fix:** Negate the condition, or read `cb.checked` after the click event propagates
by using `requestAnimationFrame` / `setTimeout(0)`. The simplest correct fix is to
flip the condition:

```js
onclick: () => {
  // cb.checked is pre-toggle at this point — negate to get post-toggle intent
  const willBeChecked = !cb.checked;
  lbl.style.borderColor = willBeChecked ? 'var(--acc)' : 'var(--line)';
  lbl.style.background  = willBeChecked ? 'rgba(0,180,216,.08)' : 'var(--panel)';
},
```

---

## Warnings

### WR-01: `detalheEl.textContent` displays literal `"null"` for `por_tempo` / `SEM_FREQ` items

**File:** `assets/erp-manutencao.js:1964`

**Issue:** Items with `status` of `POR_TEMPO` or `SEM_FREQ` arrive from the backend
with `item.intervalo === null` and `item.falta === null`. The detail line is built
unconditionally:

```js
detalheEl.textContent =
  'A cada ' + item.intervalo + ' ' + unidade + ' · faltam ' +
  Math.max(0, falta).toFixed(0) + ' ' + unidade;
```

`'A cada ' + null` coerces `null` to the string `"null"`, producing:

> A cada null h · faltam 0 h

This appears for every `POR_TEMPO` / `SEM_FREQ` item in the checklist and is
visible to end users.

**Fix:** Guard the detail line on `item.por_tempo`:

```js
if (item.por_tempo) {
  detalheEl.textContent = 'Frequência por tempo — verificar calendário';
} else {
  detalheEl.textContent =
    'A cada ' + item.intervalo + ' ' + unidade +
    ' · faltam ' + Math.max(0, falta).toFixed(0) + ' ' + unidade;
}
```

---

_Reviewed: 2026-06-28T21:45:00-03:00_
_Reviewer: Claude (gsd-code-reviewer, adversarial stance)_
_Depth: deep_
