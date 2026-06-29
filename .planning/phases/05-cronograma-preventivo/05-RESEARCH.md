# Phase 5: Cronograma Preventivo — Research

**Researched:** 2026-06-28
**Domain:** Greedy day-packing scheduling algorithm (Python port from JS legacy)
**Confidence:** HIGH — algorithm fully extracted from authoritative source

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Endpoint read-only computado: `GET /api/manutencao/cronograma` (filtro opcional por categoria). Sem nova tabela; lê dados existentes.
- Determinístico: para um dataset fixo de ativos + config de equipe conhecida, a saída é estável (ordenação estável por criticidade depois por falta/proximo_uso depois id). Requisito do teste.
- Demanda: ativos com manutenção preventiva pendente/próxima — derivar de `ativo_plano_estado` (proximo_uso vs uso_atual) e/ou dos planos aplicáveis (como em `GET /api/manutencao/vencimentos` / `_vencimentos_para_ativo`). Itens VENCIDA/URGENTE entram primeiro.
- Criticidade: do ativo (campo criticidade já existente em refrig/ativos) — CRITICA→ALTA→MEDIA→BAIXA. Se ausente, default MEDIA.
- Duração estimada por ativo/serviço: usar duração do serviço/plano se existir; senão um default razoável (documentar; seguir o legado).
- Capacidade: `equipe_config` da Fase 4 (`GET /api/manutencao/equipe/config` → horas/dia) + dias úteis (dias_semana).
- Algoritmo greedy packing: ordenar demanda por criticidade desc, depois urgência (falta menor primeiro), depois id (estável). Iterar dias úteis; em cada dia, alocar ativos até capacidade; transbordar p/ próximo dia útil.
- KPIs: total OS, horas-pessoa, dias úteis, data de conclusão, % utilização, alerta quando demanda > capacidade.
- Endpoint em `backend/manutencao.py` (sem schema novo). Aba em `assets/erp-manutencao.js`.
- Nova aba "Cronograma" (TAB_DEFS), visual portado do legado.
- `_require_auth`. Read-only GET.
- `tests/test_manutencao.py::test_cronograma`: dataset fixo + config conhecida → asserta alocação determinística.

### Claude's Discretion
- Default de duração por ativo quando o serviço não define (seguir legado).
- Horizonte máximo de dias do cronograma.
- Shape fino do JSON.

### Deferred Ideas (OUT OF SCOPE)
- Persistir/versionar cronogramas; gerar OS em lote a partir do cronograma.
- Otimização além de greedy (bin-packing ótimo).
</user_constraints>

---

## Summary

Phase 5 ports the `pmocCronograma()` greedy scheduling function from `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (JS, lines 1983–2086) into a Python `GET /api/manutencao/cronograma` endpoint in `backend/manutencao.py`. The algorithm is fully specified in the legacy source — no design decisions remain except the duration-fallback for non-refrigeration asset types, the maximum horizon cap, and the precise JSON response shape.

The demand source is `ativo_plano_estado` joined with `catalogo_plano_itens` and `ativos`. The algorithm iterates working days forward from an injectable "today" date, packs jobs into each day up to `h_dia_total × 60` minutes, overflows to the next working day, and computes five KPIs. Determinism requires a stable three-key sort: criticidade rank → falta ascending → ativo_id ascending. Date-dependence is the primary testability pitfall; `today` must be injectable via a query param or function argument.

A new "Cronograma" tab is added to `TAB_DEFS` in `assets/erp-manutencao.js` (after line 31), and its `async 'cronograma'(cont)` renderer fetches from the new endpoint and renders a day-by-day list with criticality badges, capacity bars, and a KPI header row — mirroring the legacy `.crono-wrap` layout adapted to the dark theme.

**Primary recommendation:** Port `pmocCronograma` exactly, injecting `today` as a parameter for testability. Derive criticidade from `pmoc_{categoria}.criticidade` via a LEFT JOIN, falling back to `ativos.criticidade` (migration default `'operacional'` → treat as `'BAIXA'`), then to `'MÉDIA'`. Use duration = `SETUP_MIN + n_checklist_items × MIN_POR_ITEM × FATOR_TIPO_EQUIP × FATOR_MANUT` where `n_checklist_items` defaults to 9 (SPLIT baseline) for non-refrigeration types.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Greedy packing algorithm | API / Backend | — | Pure computation over DB state; no UI input drives the algorithm |
| Demand query (ativos due) | API / Backend | — | SQL join of ativo_plano_estado + catalogo_plano_itens + ativos |
| Capacity config fetch | API / Backend | — | Reads equipe_config singleton (Phase 4 data) |
| Duration estimation | API / Backend | — | Deterministic formula; no client input needed |
| KPI computation | API / Backend | — | Derived from schedule output; computed server-side |
| Day-by-day rendering | Browser / Client | — | Frontend renders the `dias[]` array returned by the endpoint |
| Criticality badge colors | Browser / Client | — | CSS/JS mapping; existing CRIT_COLOR pattern |
| Capacity bar per day | Browser / Client | — | `(horas_usadas / horas_disponiveis) × 100` pct width |

---

## The Exact Legacy Algorithm (Source of Truth)

**File:** `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html`
**Function:** `pmocCronograma(cap)`, lines 1983–2086 [VERIFIED: direct file read]

### Step-by-step (verbatim JS logic translated to prose)

**Step 1 — Build demand queue (lines 1987–1995)**

```javascript
var ordem = ['CRÍTICA','ALTA','MÉDIA','BAIXA'];
var fila = DATA.filter(function(e){
  return !e.ultimaManutencao && !getLatestLogDate(e.id);   // initial mobilization only
}).map(function(e){
  return {e:e, crit:autoCrit(e), min:estTempoServico(e,'PREVENTIVA')};
}).sort(function(a,b){
  var d = ordem.indexOf(a.crit) - ordem.indexOf(b.crit);   // criticidade ASC index
  return d !== 0 ? d : b.min - a.min;                      // then duration DESC within same crit
});
```

**Python translation (IMP-05 context):**
- Legacy uses "no history" as the filter for initial mobilization.
- In IMP-05 the CONTEXT.md says demand comes from `ativo_plano_estado` (proximo_uso vs uso_atual) and/or vencimentos — items VENCIDA/URGENTE first.
- Sort key: `(CRIT_ORDER[criticidade], falta_asc, ativo_id)` — three stable keys.
  - Secondary key in legacy is `b.min - a.min` (longest duration first within same criticidade). CONTEXT.md says "falta menor primeiro" for the recurrent case. **Use falta ascending as secondary key** (CONTEXT.md overrides legacy secondary for the recurrent/hybrid source).
  - Tertiary key: `ativo_id` string (lexicographic) for full determinism.

**Step 2 — Daily capacity in minutes (lines 2004–2006)**

```javascript
var capDiaMin = cap.hDiaTotal * 60;
if (capDiaMin <= 0) capDiaMin = 240;  // guard: fallback 4h = 240 min
```

Python: `cap_dia_min = max(cap["h_dia_total"] * 60, 1)` — use 240 as guard only if `h_dia_total <= 0`.

**Step 3 — Working day iterator (lines 2008–2021)**

```javascript
var cursor = new Date(); cursor.setHours(0,0,0,0);
var diaAtual = null, restante = 0;

function novoDia(){
  while (t.diasUteis.indexOf(cursor.getDay()) < 0) {
    cursor.setDate(cursor.getDate() + 1);
  }
  diaAtual = {data: new Date(cursor), os: [], usado: 0};
  dias.push(diaAtual);
  restante = capDiaMin;
  cursor.setDate(cursor.getDate() + 1);   // ← advance AFTER recording
}
novoDia();  // open first working day
```

**Python equivalent:**

```python
from datetime import date, timedelta

DOW_MAP = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}

def _dias_uteis_set(dias_semana: list[str]) -> set[int]:
    """Convert ["seg","ter",...] → set of Python weekday integers (Mon=0)."""
    return {DOW_MAP[d] for d in dias_semana if d in DOW_MAP}

def _proximo_dia_util(cursor: date, dias_uteis: set[int]) -> date:
    while cursor.weekday() not in dias_uteis:
        cursor += timedelta(days=1)
    return cursor
```

Note: Python `date.weekday()` returns Mon=0…Sun=6. JS `getDay()` returns Sun=0…Sat=6. The `equipe_config.dias_semana` stores string tokens `["seg","ter","qua","qui","sex"]` from Phase 4 — map these to Python weekday integers before the loop.

**Step 4 — Pack jobs into days (lines 2023–2034)**

```javascript
fila.forEach(function(job){
  guard++; if (guard > 5000) return;
  if (job.min > restante && diaAtual.os.length > 0) novoDia();
  diaAtual.os.push(job);
  diaAtual.usado += job.min;
  restante -= job.min;
  if (restante <= 0) novoDia();
});
// remove trailing empty day
if (dias.length && dias[dias.length-1].os.length === 0) dias.pop();
```

Key behaviours:
1. If `job.min > restante` **and** current day already has at least 1 OS → open new day, then place job.
2. If the day is empty and `job.min > cap_dia_min` → job still goes on that day (partial fill, no split).
3. Guard of 5000 iterations prevents infinite loop (safe to keep as `MAX_JOBS = 5000`).
4. Pop trailing empty day at end.

**Step 5 — KPI computation (lines 2036–2050)**

```javascript
var totalMin = fila.reduce(function(s,j){ return s + j.min; }, 0);
// KPI cards:
//   OS de Mobilização  = fila.length
//   Esforço Total      = (totalMin / 60).toFixed(0)  → horas-pessoa int
//   Dias Úteis         = dias.length
//   Conclusão          = fmtDate(dias[dias.length-1].data)   → last day
```

Python KPIs:

```python
total_os       = len(fila)
horas_pessoa   = round(total_min / 60, 1)         # one decimal
dias_uteis     = len(dias)
data_conclusao = dias[-1]["data"].isoformat() if dias else None
cap_total_min  = cap_dia_min * dias_uteis          # total available
pct_utilizacao = round(total_min / cap_total_min * 100, 1) if cap_total_min > 0 else 0.0
alerta         = total_min > cap_total_min         # demand > available
```

No annual-capacity utilization KPI in the `pmocCronograma` section — only mobilization KPIs. The annual utilization is in the `pmocPlano` section (line 1876 in legacy), which is a separate view. IMP-05 is only the mobilization schedule.

---

## Demand Source

### Source 1: `ativo_plano_estado` (recurrent/hybrid — primary for IMP-05)

[VERIFIED: direct file reads of `data/schema_manutencao.sql` lines 29–39 and `backend/manutencao.py` lines 302–470]

```sql
-- ativo_plano_estado schema (schema_manutencao.sql):
-- ativo_id TEXT, catalogo_plano_item_id INTEGER, ultimo_uso REAL, proximo_uso REAL
-- PRIMARY KEY (ativo_id, catalogo_plano_item_id)
```

Join path to get all assets with pending work:

```sql
SELECT
    a.id          AS ativo_id,
    a.nome        AS ativo_nome,
    a.tipo        AS tipo,
    a.categoria   AS categoria,
    a.uso_atual   AS uso_atual,
    a.criticidade AS criticidade_ativo,   -- fallback field (migration default 'operacional')
    ape.proximo_uso,
    (ape.proximo_uso - a.uso_atual) AS falta,
    cpi.id        AS item_id
FROM ativo_plano_estado ape
JOIN ativos a ON a.id = ape.ativo_id AND a.ativo = 1
JOIN catalogo_plano_itens cpi ON cpi.id = ape.catalogo_plano_item_id
WHERE ape.proximo_uso <= (a.uso_atual + <horizonte>)  -- configurable window
```

Filter to include `falta <= 0` (VENCIDA) and `falta <= intervalo * 0.15` (URGENTE) first; include PROXIMA if within horizon.

### Source 2: Initial mobilization (ativos without ativo_plano_estado)

Ativos that have no rows in `ativo_plano_estado` and no rows in `manut_registros` for that asset are candidates for "first preventive". The legacy uses this as the sole source. IMP-05 (per CONTEXT.md) uses the hybrid: both sources, with VENCIDA/URGENTE prioritized via the sort key.

**Simplest approach for IMP-05:** Query all ativos matching the optional `categoria` filter, join LEFT to `ativo_plano_estado`, compute `falta`. Assets with no estado row get a synthetic `falta = 0` (treat as "due now"). Sort by `(CRIT_ORDER, falta ASC, ativo_id ASC)`.

**Deduplication:** One ativo can appear multiple times (once per plan item). For the scheduling queue, one entry per ativo is enough (use the most urgent item's `falta` for sorting; duration is per-ativo, not per-item). The plan is to generate one OS per ativo, not one per plan item.

---

## Criticidade Source

[VERIFIED: direct file reads of `db_core.py` line 32, `data/schema_core.sql` lines 256/327/362/392, `backend/main.py` lines 1086–1184]

**Three-tier resolution (most specific first):**

1. **PMOC table** (most reliable): `pmoc_refrigeracao.criticidade`, `pmoc_transportes.criticidade`, `pmoc_corte.criticidade`, `pmoc_fonoclama.criticidade` — values: `'CRÍTICA'`, `'ALTA'`, `'MÉDIA'`, `'BAIXA'` (with accent).
2. **`ativos.criticidade`** column (migration in `db_core.py` line 32): default `'operacional'` — NOT a valid CRIT_ORDER value; treat `'operacional'` as `'MÉDIA'`.
3. **Fallback**: `'MÉDIA'` when both are NULL or invalid.

**SQL for refrigeration (canonical pattern, `backend/main.py` line 1106):**
```sql
SELECT a.id, a.nome, a.tipo, a.categoria, a.uso_atual,
       COALESCE(p.criticidade, a.criticidade, 'MÉDIA') AS criticidade
FROM ativos a
LEFT JOIN pmoc_refrigeracao p ON p.ativo_id = a.id
WHERE a.categoria = 'climatizacao' AND a.ativo = 1
```

**For other categories:**
```sql
LEFT JOIN pmoc_transportes pt ON pt.ativo_id = a.id AND a.categoria IN ('viaturas','embarcacoes',...)
-- or pmoc_corte, pmoc_fonoclama
```

**Criticidade normalization in Python:**
```python
CRIT_ORDER = {"CRÍTICA": 0, "ALTA": 1, "MÉDIA": 2, "BAIXA": 3}
CRIT_VALID = {"CRÍTICA", "ALTA", "MÉDIA", "BAIXA"}

def _normaliza_crit(raw: str | None) -> str:
    if raw and raw.upper().replace("Í","Í") in CRIT_VALID:
        return raw
    return "MÉDIA"  # default for None, 'operacional', or any unrecognized value
```

Note: The DB stores accented values (`'CRÍTICA'`, `'MÉDIA'`). Python string comparison must handle the same encoding. Use exact string match or normalize via `.casefold()` + accent strip only if needed — the stored values use Unicode correctly.

---

## Duration Estimation

[VERIFIED: direct file reads of `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` lines 911–924]

**Legacy formula:**
```
duration_min = round(n_checklist_items × MIN_POR_ITEM × FATOR_TIPO_EQUIP × FATOR_MANUT + SETUP_MIN)
```

**Constants (verbatim from legacy, line 911–917):**
```python
MIN_POR_ITEM = 10          # minutes per checklist item
SETUP_MIN    = 15          # setup / displacement overhead
FATOR_TIPO_EQUIP = {
    "SPLIT":          1.0,
    "PISO/TETO":      1.15,
    "JANELA":         0.7,
    "SELF CONTAINED": 1.6,
}
FATOR_MANUT = {
    "INSPEÇÃO":    0.4,
    "PREVENTIVA":  1.0,
    "REVISÃO":     1.6,
    "LIMPEZA":     0.6,
    "CORRETIVA":   1.3,
    "RECARGA GÁS": 0.8,
    "SUBSTITUIÇÃO":2.0,
}
```

**Checklist item counts (verbatim from legacy `CHECKLIST`, lines 1012–1057):**
```python
N_CHECKLIST = {
    "SPLIT":          9,   # 9 items
    "PISO/TETO":      9,   # 9 items
    "SELF CONTAINED": 12,  # 12 items
    "JANELA":         6,   # 6 items
    # fallback for non-refrigeration:
    "_DEFAULT":        9,  # SPLIT baseline (as per legacy: CHECKLIST['SPLIT'])
}
```

**Python implementation:**
```python
def _est_duracao_min(tipo: str, tipo_manut: str = "PREVENTIVA") -> int:
    """Porta exata de estTempoServico(e, tipoManut) — JS lines 919–925."""
    n = N_CHECKLIST.get(tipo, N_CHECKLIST["_DEFAULT"])
    f_eq = FATOR_TIPO_EQUIP.get(tipo, 1.0)
    f_m  = FATOR_MANUT.get(tipo_manut, 1.0)
    return round(n * MIN_POR_ITEM * f_eq * f_m + SETUP_MIN)
```

**Computed durations for common types (preventiva):**
| Tipo | n_items | f_eq | min = round(n×10×f_eq×1.0 + 15) |
|------|---------|------|-----------------------------------|
| SPLIT | 9 | 1.0 | 105 min |
| PISO/TETO | 9 | 1.15 | 119 min |
| JANELA | 6 | 0.7 | 57 min |
| SELF CONTAINED | 12 | 1.6 | 207 min |
| _DEFAULT (outros) | 9 | 1.0 | 105 min |

**Claude's Discretion on duration:** For non-refrigeration asset types (viaturas, maquinas_corte, fonoclama), there is no FATOR_TIPO_EQUIP entry. The legacy defaults to `f_eq = 1.0` (same as SPLIT). This is correct behavior to port — use `FATOR_TIPO_EQUIP.get(tipo, 1.0)`.

---

## Greedy Packing Algorithm — Python Port

### Complete implementation skeleton

```python
from datetime import date, timedelta
from typing import Optional

# Day-of-week mapping: equipe_config stores ["seg","ter","qua","qui","sex"]
_DOW_STR_TO_PY = {"dom": 6, "seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5}

CRIT_ORDER = {"CRÍTICA": 0, "ALTA": 1, "MÉDIA": 2, "BAIXA": 3}

MAX_JOBS    = 5000    # guard matching legacy line 2024
MAX_DAYS    = 365     # horizon cap (Claude's Discretion)
DEFAULT_CAP = 240     # fallback capacity in minutes (= 4h, same as legacy line 2006)


def _proximo_dia_util(cursor: date, dias_uteis_py: set[int]) -> date:
    """Advance cursor to next working day (skip non-working days)."""
    while cursor.weekday() not in dias_uteis_py:
        cursor += timedelta(days=1)
    return cursor


def computar_cronograma(
    fila: list[dict],         # sorted demand: [{ativo_id, nome, criticidade, duracao_min, falta, ...}]
    cap_dia_min: float,       # h_dia_total × 60
    dias_uteis_py: set[int],  # Python weekday integers {0,1,2,3,4}
    today: Optional[date] = None,
) -> tuple[list[dict], dict]:
    """
    Greedy packing: porta exata de pmocCronograma() — JS lines 2004–2034.

    Returns:
        dias   — list of day dicts [{data, dia_semana, itens, horas_usadas, horas_disponiveis}]
        kpis   — {total_os, horas_pessoa, dias_uteis, data_conclusao, pct_utilizacao, alerta}
    """
    if today is None:
        today = date.today()

    cap_dia_min = max(cap_dia_min, 1)  # guard zero
    if cap_dia_min <= 0:
        cap_dia_min = DEFAULT_CAP

    dias: list[dict] = []
    cursor = today

    def novo_dia():
        nonlocal cursor
        cursor = _proximo_dia_util(cursor, dias_uteis_py)
        dia = {
            "data": cursor.isoformat(),
            "dia_semana": cursor.strftime("%a"),   # "Mon","Tue", etc. — or use pt-BR abbr
            "itens": [],
            "horas_usadas": 0.0,
            "horas_disponiveis": round(cap_dia_min / 60, 2),
        }
        dias.append(dia)
        cursor += timedelta(days=1)                # advance AFTER recording (mirrors JS line 2019)
        return dia, cap_dia_min                    # return dia and restante

    dia_atual, restante = novo_dia()
    guard = 0

    for job in fila:
        guard += 1
        if guard > MAX_JOBS:
            break

        job_min = job["duracao_min"]

        # Overflow to next day: only if current day already has items
        if job_min > restante and len(dia_atual["itens"]) > 0:
            if len(dias) >= MAX_DAYS:
                break
            dia_atual, restante = novo_dia()

        dia_atual["itens"].append(job)
        dia_atual["horas_usadas"] = round(dia_atual["horas_usadas"] + job_min / 60, 2)
        restante -= job_min

        if restante <= 0:
            if len(dias) >= MAX_DAYS:
                break
            dia_atual, restante = novo_dia()

    # Remove trailing empty day (mirrors JS line 2033–2034)
    if dias and not dias[-1]["itens"]:
        dias.pop()

    # KPI computation (JS lines 2036–2050)
    total_min   = sum(j["duracao_min"] for j in fila[:guard])
    total_os    = len(fila[:guard])
    dias_uteis  = len(dias)
    cap_total   = cap_dia_min * dias_uteis
    horas_pessoa = round(total_min / 60, 1)
    data_conclusao = dias[-1]["data"] if dias else None
    pct_utilizacao = round(total_min / cap_total * 100, 1) if cap_total > 0 else 0.0
    alerta      = total_min > cap_total

    kpis = {
        "total_os":       total_os,
        "horas_pessoa":   horas_pessoa,
        "dias_uteis":     dias_uteis,
        "data_conclusao": data_conclusao,
        "pct_utilizacao": pct_utilizacao,
        "alerta":         alerta,
    }
    return dias, kpis
```

---

## equipe_config Consumption

[VERIFIED: `backend/manutencao.py` lines 1013–1066, 1181–1207]

`GET /api/manutencao/equipe/config` returns:
```json
{
  "config": {
    "id": 1,
    "num_equipes": 1,
    "dias_semana": ["seg","ter","qua","qui","sex"],
    "turnos": [{"nome":"Manhã","horas":2},{"nome":"Tarde","horas":2}]
  },
  "capacidade": {
    "h_dia_equipe": 4.0,
    "h_dia_total": 4.0,
    "h_semana": 20.0,
    "h_mes": 86.9,
    "h_ano": 1040.0
  }
}
```

**Key field for cronograma:** `capacidade.h_dia_total` — total hours per day across all teams.

**Python: read config inside the endpoint (reuse `_capacidade` helper):**
```python
from backend.manutencao import _capacidade, _DEFAULT_CONFIG, _db

async def _get_config() -> tuple[dict, float, set[int]]:
    """Returns (config, cap_dia_min, dias_uteis_py_set)."""
    row = await _db().fetch_one("SELECT * FROM equipe_config WHERE id = 1")
    if row:
        config = dict(row)
        config["dias_semana"] = json.loads(config["dias_semana"])
        config["turnos"] = json.loads(config["turnos"])
    else:
        config = dict(_DEFAULT_CONFIG)
    cap = _capacidade(config)
    cap_dia_min = cap["h_dia_total"] * 60
    dias_uteis_py = {_DOW_STR_TO_PY[d] for d in config["dias_semana"] if d in _DOW_STR_TO_PY}
    if not dias_uteis_py:
        dias_uteis_py = {0, 1, 2, 3, 4}  # Mon–Fri fallback
    return config, cap_dia_min, dias_uteis_py
```

**Default config (used when table is empty):**
```python
_DEFAULT_CONFIG = {
    "id": 1,
    "num_equipes": 1,
    "dias_semana": ["seg", "ter", "qua", "qui", "sex"],
    "turnos": [{"nome": "Manhã", "horas": 2}, {"nome": "Tarde", "horas": 2}],
}
# cap_dia_total = 2+2 = 4 h → 240 min
```

---

## Endpoint Contract

[VERIFIED: `05-CONTEXT.md` decisions section]

```python
@router.get("/cronograma")
async def get_cronograma(
    categoria: Optional[str] = None,
    today: Optional[str] = None,  # YYYY-MM-DD; injectable for tests (Claude's Discretion)
    authorization: str | None = Header(None),
):
    """GET /api/manutencao/cronograma — read-only computed schedule.

    Query params:
      categoria — filter assets by categoria (optional)
      today     — override today's date as YYYY-MM-DD (for deterministic tests)

    Response shape:
      {
        "dias": [
          {
            "data": "2026-07-01",
            "dia_semana": "Ter",
            "itens": [
              {
                "ativo_id": "u01",
                "nome": "Split Sala Comando",
                "tipo": "SPLIT",
                "criticidade": "CRÍTICA",
                "duracao_min": 105,
                "duracao_h": 1.75,
                "falta": -10.0,
                "status": "VENCIDA"
              }
            ],
            "horas_usadas": 1.75,
            "horas_disponiveis": 4.0
          }
        ],
        "kpis": {
          "total_os": 5,
          "horas_pessoa": 8.75,
          "dias_uteis": 3,
          "data_conclusao": "2026-07-03",
          "pct_utilizacao": 72.9,
          "alerta": false
        }
      }
    """
```

---

## Demand Query (SQL)

The endpoint must query all assets with preventive maintenance pending. Strategy: combine assets with `ativo_plano_estado` data (recurrent) and assets with NO `ativo_plano_estado` rows (initial mobilization, `falta = 0`).

```sql
-- Assets with plan state (recurrent):
SELECT
    a.id          AS ativo_id,
    a.nome,
    a.tipo,
    a.categoria,
    a.uso_atual,
    COALESCE(pr.criticidade, pt.criticidade, pc.criticidade, pf.criticidade,
             CASE WHEN a.criticidade IN ('CRÍTICA','ALTA','MÉDIA','BAIXA')
                  THEN a.criticidade ELSE 'MÉDIA' END)  AS criticidade,
    ape.proximo_uso,
    (ape.proximo_uso - a.uso_atual)  AS falta
FROM ativos a
JOIN ativo_plano_estado ape ON ape.ativo_id = a.id
LEFT JOIN pmoc_refrigeracao  pr ON pr.ativo_id = a.id
LEFT JOIN pmoc_transportes   pt ON pt.ativo_id = a.id
LEFT JOIN pmoc_corte         pc ON pc.ativo_id = a.id
LEFT JOIN pmoc_fonoclama     pf ON pf.ativo_id = a.id
WHERE a.ativo = 1
  AND (? IS NULL OR a.categoria = ?)          -- categoria filter
  AND ape.proximo_uso <= a.uso_atual + 500    -- horizon: within 500 usage units
ORDER BY a.id

UNION ALL

-- Assets with NO plan state (initial mobilization — falta = 0):
SELECT
    a.id, a.nome, a.tipo, a.categoria, a.uso_atual,
    COALESCE(pr.criticidade, pt.criticidade, pc.criticidade, pf.criticidade,
             CASE WHEN a.criticidade IN ('CRÍTICA','ALTA','MÉDIA','BAIXA')
                  THEN a.criticidade ELSE 'MÉDIA' END),
    NULL AS proximo_uso,
    0.0  AS falta
FROM ativos a
LEFT JOIN ativo_plano_estado ape ON ape.ativo_id = a.id
LEFT JOIN pmoc_refrigeracao  pr  ON pr.ativo_id = a.id
LEFT JOIN pmoc_transportes   pt  ON pt.ativo_id = a.id
LEFT JOIN pmoc_corte         pc  ON pc.ativo_id = a.id
LEFT JOIN pmoc_fonoclama     pf  ON pf.ativo_id = a.id
WHERE a.ativo = 1
  AND (? IS NULL OR a.categoria = ?)
  AND ape.ativo_id IS NULL                    -- no plan state row → initial mobilization
```

After the query, deduplicate by `ativo_id` (keep the row with lowest `falta`), compute `duracao_min` via `_est_duracao_min(tipo)`, compute `status` from `falta` and the item's interval, then sort.

**Deduplication note:** One ativo may have multiple `ativo_plano_estado` rows (multiple plan items). For scheduling, we need ONE entry per ativo. Pick the row where `falta` is minimum (most urgent item). Duration covers the whole preventive visit, not one plan item.

---

## Sort Key — Determinism Contract

[VERIFIED: `05-CONTEXT.md` decisions — "ordenação estável por criticidade depois por falta/proximo_uso depois id"]

```python
CRIT_ORDER = {"CRÍTICA": 0, "ALTA": 1, "MÉDIA": 2, "BAIXA": 3}

fila.sort(key=lambda j: (
    CRIT_ORDER.get(j["criticidade"], 2),   # criticidade ASC (0=most critical first)
    j["falta"],                            # falta ASC (most overdue / most urgent first)
    j["ativo_id"],                         # ativo_id ASC (string; stable tie-breaker)
))
```

Python's `list.sort()` is stable and fully deterministic for equal keys. No `random`, no `dict.items()` iteration order dependency. **Do not use `reversed()` on a dict** — always build the list then sort.

---

## Determinism Pitfalls

### Pitfall 1: Date dependence
**Problem:** `date.today()` makes tests non-reproducible. A test that passes on 2026-07-01 fails on 2026-07-02 if working-day boundaries shift.
**Solution:** Inject `today` as optional query param `?today=YYYY-MM-DD`. Default to `date.today()` in production. Tests always pass a fixed date.

### Pitfall 2: DOW string-to-integer mapping
**Problem:** JS uses `getDay()` (Sun=0), Python uses `weekday()` (Mon=0). Legacy `diasUteis` stores `[1,2,3,4,5]` (Mon–Fri). `equipe_config` stores `["seg","ter","qua","qui","sex"]`. Converting incorrectly shifts the schedule by 1 day.
**Solution:** Map explicitly: `{"dom":6,"seg":0,"ter":1,"qua":2,"qui":3,"sex":4,"sab":5}`. Test: `date(2026,6,29).weekday() == 0` (Monday = 0). Verify `"seg" → 0` mapping.

### Pitfall 3: Unstable deduplication
**Problem:** If two `ativo_plano_estado` rows tie on `falta`, different Python versions may order them differently.
**Solution:** Always use `min(..., key=lambda r: (r["falta"], r["catalogo_plano_item_id"]))` when picking the most urgent item per ativo.

### Pitfall 4: Criticidade encoding
**Problem:** `'CRITICA'` (without accent) ≠ `'CRÍTICA'` (with). SQLite stores accented strings; Python comparisons are case-sensitive by default.
**Solution:** Use exact Unicode match (the DB stores accented forms). The `CRIT_ORDER` dict keys must match the stored form exactly: `'CRÍTICA'`, `'ALTA'`, `'MÉDIA'`, `'BAIXA'`. Missing key → default 2 (MÉDIA equivalent).

### Pitfall 5: Zero-capacity guard
**Problem:** If `h_dia_total = 0` (corrupt config), `cap_dia_min = 0` causes an infinite loop (every job always exceeds restante, `restante <= 0` never triggers).
**Solution:** `cap_dia_min = max(cap_dia_min, 1)` and enforce `MAX_DAYS` guard on `len(dias)`.

---

## Deterministic Test Dataset

[ASSUMED — design based on schema constraints; values chosen for unambiguous expected output]

Test fixture (for `tests/test_manutencao.py::test_cronograma`):

**Crew config:** 1 team, Mon–Fri (`["seg","ter","qua","qui","sex"]`), 1 turno of 4h → `cap_dia_min = 240 min`.
**Today (injectable):** `2026-07-06` (Monday).

**Assets (3 ativos, distinct criticidades):**

| ativo_id | nome | tipo | criticidade | falta | duracao_min (computed) |
|----------|------|------|-------------|-------|------------------------|
| `a01` | AC Sala Comando | SPLIT | CRÍTICA | -5.0 | 105 |
| `a02` | AC Sala TI | SPLIT | ALTA | 10.0 | 105 |
| `a03` | AC Refeitório | JANELA | MÉDIA | 20.0 | 57 |

**Sort order:** CRÍTICA(a01) → ALTA(a02) → MÉDIA(a03).

**Pack into days (cap = 240 min):**
- Day 1 (2026-07-06, Mon): a01 (105 min used, restante=135), a02 (105 min, restante=30), a03 (57 > 30 → overflow since day has items).
- Day 2 (2026-07-07, Tue): a03 (57 min used, restante=183). `restante > 0` → no new day. End.
- Pop trailing empty: Day 2 has 1 item → no pop.

**Expected output:**
```python
{
  "dias": [
    {
      "data": "2026-07-06",
      "dia_semana": "Seg",
      "itens": [
        {"ativo_id":"a01","criticidade":"CRÍTICA","duracao_min":105},
        {"ativo_id":"a02","criticidade":"ALTA",   "duracao_min":105},
      ],
      "horas_usadas": 3.5,       # (105+105)/60
      "horas_disponiveis": 4.0,
    },
    {
      "data": "2026-07-07",
      "dia_semana": "Ter",
      "itens": [
        {"ativo_id":"a03","criticidade":"MÉDIA","duracao_min":57},
      ],
      "horas_usadas": 0.95,      # 57/60 = 0.95
      "horas_disponiveis": 4.0,
    }
  ],
  "kpis": {
    "total_os": 3,
    "horas_pessoa": 4.45,        # (105+105+57)/60 = 267/60 = 4.45
    "dias_uteis": 2,
    "data_conclusao": "2026-07-07",
    "pct_utilizacao": round(267 / (240*2) * 100, 1),  # = 55.6
    "alerta": False,             # 267 < 480
  }
}
```

**Demand > capacity test (alerta=True):** 3 assets of type SELF CONTAINED (207 min each = 621 min total) vs cap 240 min. Expected: alerta=True, dias=3, pct_utilizacao=86.25%.

---

## Frontend: Tab and Renderer

[VERIFIED: `assets/erp-manutencao.js` lines 23–32 (TAB_DEFS), 1072–1151 (subCronograma existing)]

### Where to add the Cronograma tab

**Current TAB_DEFS (lines 23–32):**
```javascript
const TAB_DEFS = [
  { id: 'dashboard',      icon: '📊', label: 'Painel' },
  { id: 'refrigeracao',   icon: '❄️', label: 'Refrigeração' },
  { id: 'transportes',    icon: '🚚', label: 'Transportes' },
  { id: 'corte',          icon: '🌿', label: 'Máq. Corte' },
  { id: 'fonoclama',      icon: '📣', label: 'Fonoclama' },
  { id: 'registrar-uso',  icon: '⏱',  label: 'Registrar Uso' },
  { id: 'sobressalentes', icon: '🔩', label: 'Sobressalentes' },
  { id: 'equipe-tecnica', icon: '👥', label: 'Equipe Técnica' },   // ← Phase 4
  // ADD HERE:
  { id: 'cronograma',     icon: '📅', label: 'Cronograma' },       // ← Phase 5
];
```

**Add after line 31** (after equipe-tecnica entry).

### Renderer skeleton (dark-theme port of legacy `.crono-wrap`)

Note: An existing `subCronograma()` function at line 1072 is a completely different widget (per-asset maintenance timeline within the asset detail view — uses horímetro-based intervals, not the greedy scheduler). The new Phase 5 renderer is a top-level tab renderer, not a sub-view. Name it `async 'cronograma'(cont)`.

```javascript
async 'cronograma'(cont) {
  // 1. Fetch from backend
  const token = /* current bearer token */;
  cont.innerHTML = '<div style="padding:20px;color:var(--ink-3)">Calculando cronograma...</div>';
  try {
    const r = await fetch(apiUrl('/api/manutencao/cronograma'), {
      headers: { Authorization: 'Bearer ' + token }
    });
    if (!r.ok) { /* show error */ return; }
    const data = await r.json();   // { dias:[], kpis:{} }

    // 2. KPI header row (4 cards like legacy: OS, Esforço, Dias, Conclusão)
    // 3. Alert banner if data.kpis.alerta
    // 4. Day-by-day list: for each dia in data.dias:
    //      - date header + "X.Xh / 4.0h · N OS"
    //      - capacity bar (horas_usadas / horas_disponiveis × 100%)
    //      - list of itens with criticidade badge + nome + duracao_min
    // All via el() + textContent — no innerHTML for user data
  } catch (e) { /* toast error */ }
}
```

**Criticidade badge colors (dark theme — adapted from legacy CRIT_COLOR):**
```javascript
const CRIT_COLOR_DARK = {
  'CRÍTICA': 'var(--red)',    // #ef4444
  'ALTA':    'var(--amber)',  // #f59e0b
  'MÉDIA':   'var(--acc)',    // #00b4d8
  'BAIXA':   'var(--green)',  // #22c55e
};
```

Note: Legacy uses light-theme gov.br palette (`#E52207`, `#B46800`, `#1351B4`, `#168821`). CLAUDE.md mandates dark theme. Use `var(--red)`, `var(--amber)`, `var(--acc)`, `var(--green)` instead.

---

## Standard Stack

No new packages required. This phase is pure Python/JS with existing dependencies.

| Component | What | Where |
|-----------|------|--------|
| `backend/manutencao.py` | New `@router.get("/cronograma")` endpoint | Append to existing file |
| `_capacidade()` | Reuse Phase 4 helper (line 1024) | Already in manutencao.py |
| `_DEFAULT_CONFIG` | Default config fallback (line 1016) | Already in manutencao.py |
| `_require_auth()` | Auth gate (line 32) | Already in manutencao.py |
| `_db()` | DB access helper (line 27) | Already in manutencao.py |
| `aiosqlite` | Async DB driver | Already installed |
| `datetime.date`, `timedelta` | Working day iteration | Python stdlib |
| `assets/erp-manutencao.js` | TAB_DEFS + renderer | Append new tab + renderer |

---

## Package Legitimacy Audit

No new packages to install. Phase 5 uses only existing dependencies.

---

## Architecture Patterns

### Recommended project structure (new code only)

```
backend/
└── manutencao.py          # append: _est_duracao_min, _get_cap, computar_cronograma, get_cronograma endpoint

assets/
└── erp-manutencao.js      # append: new TAB_DEF entry + async 'cronograma'(cont) renderer

tests/
└── test_manutencao.py     # append: test_cronograma, test_cronograma_alerta
```

### Endpoint registration

`backend/manutencao.py` is already included as a router in `backend/main.py`. No change to `main.py` needed — the new endpoint registers automatically on the existing `router` prefix `/api/manutencao`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Working-day skip logic | Custom calendar/holiday library | Simple `while cursor.weekday() not in dias_uteis` loop (exact port of legacy) |
| Capacity calculation | Re-derive from raw config | Reuse `_capacidade(config)` already in `manutencao.py` line 1024 |
| Auth | Custom token check | Reuse `_require_auth(authorization)` line 32 |
| Test DB setup | Custom fixtures | Reuse `app_client` fixture from `tests/conftest.py` |
| JSON serialization | Manual dict building | FastAPI auto-serializes return dicts |

---

## Common Pitfalls

### Pitfall 1: DOW encoding mismatch
**What goes wrong:** `equipe_config.dias_semana = ["seg","ter","qua","qui","sex"]`. If mapped to JS `[1,2,3,4,5]` instead of Python `{0,1,2,3,4}`, Saturday becomes a working day and Monday is skipped.
**Root cause:** JS `getDay()` is Sun=0; Python `weekday()` is Mon=0. Off-by-one on Sunday/Monday.
**How to avoid:** Use the explicit `_DOW_STR_TO_PY` dict. Add an assertion in tests: `date(2026,6,29).weekday() == 0` and `"seg" → 0`.

### Pitfall 2: Non-deterministic dict ordering used as sort
**What goes wrong:** Iterating over a dict like `CRIT_ORDER.keys()` or using `dict.items()` for sorting without an explicit key.
**Root cause:** Python dicts preserve insertion order since 3.7 but `.items()` iteration order is NOT the same as alphabetical or semantic sort.
**How to avoid:** Always `list.sort(key=lambda j: (CRIT_ORDER.get(...), ...))`.

### Pitfall 3: Missing trailing empty-day removal
**What goes wrong:** When the last job exactly fills a day (restante = 0), `novo_dia()` is called, creating an empty day appended to `dias`. Response has a trailing empty day.
**Root cause:** The JS guard `if (restante <= 0) novoDia()` opens a new day that may stay empty.
**How to avoid:** Port the exact JS guard `if dias and not dias[-1]["itens"]: dias.pop()`.

### Pitfall 4: Criticidade 'operacional' not in CRIT_ORDER
**What goes wrong:** `ativos.criticidade` defaults to `'operacional'` (db_core.py line 32). `CRIT_ORDER.get('operacional')` returns `None`, which sorts before 0 in Python.
**Root cause:** The migration default was chosen for the asset status tracking, not for the scheduling domain.
**How to avoid:** `CRIT_ORDER.get(criticidade, 2)` — default 2 = MÉDIA position.

### Pitfall 5: Integer vs float durations in KPI
**What goes wrong:** `horas_pessoa = 267 / 60 = 4.45` computes correctly in Python 3. But if `total_min` is an int and `60` is an int, `267 // 60 = 4` (floor division) gives the wrong answer.
**Root cause:** Using `//` instead of `/`.
**How to avoid:** Always use `/` for division in KPI formulas: `round(total_min / 60, 1)`.

---

## Environment Availability

Step 2.6: SKIPPED for new runtime dependencies (no new packages). Python 3.12 and aiosqlite already confirmed running (existing backend).

---

## Security Domain

This endpoint is GET / read-only computed. `_require_auth` is applied. No user-supplied data is written to DB. The only user input is `categoria` (query param) and `today` (query param for test injection). Both must be sanitized:
- `categoria`: parameterized SQL (`WHERE a.categoria = ?`)
- `today`: parse with `date.fromisoformat(today)` and catch `ValueError` → 422

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V2 Authentication | yes | `_require_auth` (existing pattern) |
| V5 Input Validation | yes | `date.fromisoformat()` + parameterized SQL |
| V4 Access Control | read-only | GET; no write path |

---

## Project Constraints (from CLAUDE.md)

- **Dark theme required** on all pages. Use `var(--bg)`, `var(--acc)`, `var(--red)`, etc. — not gov.br light palette from legacy.
- **No build step** — vanilla JS, no React/Vue.
- **DOM safety** — use `el()` and `textContent`, never `innerHTML` for user data.
- **Backend patterns** — Pydantic for request bodies (N/A here — GET only), `async/await` + `aiosqlite`, raw SQL, parameterized queries.
- **Additive migrations only** — `PRAGMA table_info` before any `ALTER`. No new table needed for this phase.
- **Fonts** — DM Sans + JetBrains Mono (self-hosted). No inline font changes needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Duration fallback for non-refrigeration types uses SPLIT baseline (9 items, f_eq=1.0) | Duration Estimation | Non-refrigeration assets may be over/under-estimated by ±30 min; acceptable for mobilization planning |
| A2 | Horizon for recurrent demand is "proximo_uso <= uso_atual + 500 usage units" | Demand Query | Too narrow: missing assets due soon. Too wide: overcrowds schedule. Configurable via MAX_DAYS guard |
| A3 | One OS per ativo (not per plan item) for scheduling granularity | Demand Source | Plan items are granular; one OS per visit is the legacy behavior and the practical choice |
| A4 | `dia_semana` label in response uses Portuguese abbreviations ("Seg","Ter",...) matching legacy DOW_ABBR | Endpoint Contract | Frontend must use same strings; if pt-BR label is wrong, day header is unreadable |
| A5 | `today` query param injection is the test mechanism (not a separate test-only route) | Pitfall 1 | Alternative: monkeypatch `date.today` in tests — either works; query param is more explicit |

---

## Sources

### Primary (HIGH confidence)
- `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` lines 855–2086 — complete JS algorithm extracted directly
- `backend/manutencao.py` lines 1–1249 — Phase 1–4 existing code (auth, capacity, plan state)
- `data/schema_manutencao.sql` — ativo_plano_estado, uso_registros, equipe_config schemas
- `data/schema_core.sql` — ativos, pmoc_* tables and criticidade fields
- `backend/db_core.py` lines 27–52 — criticidade migration on ativos
- `backend/main.py` lines 2529–2583 — existing vencimentos demand logic
- `assets/erp-manutencao.js` lines 23–32 — TAB_DEFS for insertion point
- `.planning/phases/05-cronograma-preventivo/05-CONTEXT.md` — locked decisions

### Metadata
- **Research date:** 2026-06-28
- **Valid until:** 2026-07-28 (stable — no external packages)
