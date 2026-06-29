# Phase 5: Cronograma Preventivo - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Gestor visualiza o cronograma de manutenção preventiva calculado dia-a-dia: packing greedy por capacidade de equipe (dias úteis + turnos da Fase 4), ordenação por criticidade (CRITICA→ALTA→MEDIA→BAIXA), duração estimada por ativo, capacidade usada vs disponível por dia, e KPIs de mobilização (total OS, horas-pessoa, dias úteis, data de conclusão, % utilização, alerta demanda>capacidade). Endpoint COMPUTADO (sem estado persistente). Algoritmo portado de `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (JS já implementado → traduzir p/ Python). Visual portado também.

Fora: registrar execução (já existe na Fase 2); persistir o cronograma (é recomputado a cada reload).
</domain>

<decisions>
## Implementation Decisions

### Natureza
- Endpoint read-only computado: `GET /api/manutencao/cronograma` (filtro opcional por categoria). Sem nova tabela; lê dados existentes.
- Determinístico: para um dataset fixo de ativos + config de equipe conhecida, a saída é estável (ordenação estável por criticidade depois por falta/proximo_uso depois id). Requisito do teste.

### Fontes de dados
- Demanda: ativos com manutenção preventiva pendente/próxima — derivar de `ativo_plano_estado` (proximo_uso vs uso_atual) e/ou dos planos aplicáveis (como em `GET /api/manutencao/vencimentos` / `_vencimentos_para_ativo`). Itens VENCIDA/URGENTE entram primeiro.
- Criticidade: do ativo (campo criticidade já existente em refrig/ativos) — CRITICA→ALTA→MEDIA→BAIXA. Se ausente, default MEDIA.
- Duração estimada por ativo/serviço: usar duração do serviço/plano se existir; senão um default razoável (documentar; seguir o legado).
- Capacidade: `equipe_config` da Fase 4 (`GET /api/manutencao/equipe/config` → horas/dia) + dias úteis (dias_semana).

### Algoritmo (greedy packing) — seguir o legado
- Ordenar demanda por criticidade desc, depois urgência (falta menor primeiro), depois id (estável).
- Iterar dias úteis a partir de hoje (respeitando dias_semana); em cada dia, alocar ativos até a capacidade de horas/dia ser atingida; transbordar p/ o próximo dia útil.
- KPIs: total OS = nº ativos agendados; horas-pessoa = Σ durações; dias úteis = nº de dias usados; data de conclusão = último dia; % utilização = horas-pessoa / (capacidade × dias); alerta quando demanda > capacidade no horizonte.
- O planner/executor confirma os detalhes exatos lendo o JS legado (RESEARCH).

### Contrato de endpoint
- `GET /api/manutencao/cronograma?categoria=` → `{ dias:[{data, dia_semana, itens:[{ativo_id, nome, criticidade, duracao_h, ...}], horas_usadas, horas_disponiveis}], kpis:{total_os, horas_pessoa, dias_uteis, data_conclusao, pct_utilizacao, alerta} }`.
- `_require_auth`. Read-only (GET) — leitura pode permitir visitante; manter consistente com outros GET autenticados.

### Frontend (UX)
- Nova aba "Cronograma" (TAB_DEFS), visual portado do legado.
- Vista dia-a-dia (lista/colunas): por dia, ativos agendados com badge de criticidade (cores dark), duração, barra capacidade usada vs disponível. KPIs no topo; alerta visual vermelho quando demanda>capacidade.
- Recarrega ao abrir; alterar config da equipe (Fase 4) muda o cronograma no reload.
- Fetch + Bearer; DOM seguro via el()/textContent.

### Testes
- `tests/test_manutencao.py::test_cronograma`: dataset fixo de ativos (criticidades + faltas conhecidas) + config de equipe conhecida → asserta a alocação determinística (ordem por criticidade, dias, KPIs exatos). Cobrir caso demanda>capacidade (alerta=true).

### Claude's Discretion
- Default de duração por ativo quando o serviço não define (seguir legado).
- Horizonte máximo de dias do cronograma.
- Shape fino do JSON.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/manutencao.py`: `_vencimentos_para_ativo` / lógica de vencimento, `_db`, `_require_auth`. `GET /api/manutencao/equipe/config` (Fase 4 — capacidade), `ativo_plano_estado` (Fase 2 — proximo_uso/falta por item).
- `GET /api/manutencao/vencimentos` (main.py ~2527) — demanda preventiva por ativo.
- Campo `criticidade` dos ativos (refrigeração já usa). `assets/erp-manutencao.js` (TAB_DEFS, el()).
- Legado: `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (cronograma + cálculo por equipe — algoritmo JS completo + visual).

### Established Patterns
- Endpoints computados read-only já existem (vencimentos). Frontend vanilla, fetch+Bearer, DOM seguro via el().

### Integration Points
- Endpoint em `backend/manutencao.py` (sem schema novo). Aba em `assets/erp-manutencao.js`.
- Consome equipe_config (Fase 4) + ativo_plano_estado (Fase 2) + uso/vencimentos.
</code_context>

<specifics>
## Specific Ideas

- Packing greedy determinístico é requisito (teste com dataset fixo).
- Cronograma reflete a config da equipe (acoplamento Fase 4→5).
- Visual e algoritmo seguem o legado cmasm13-govbr-v8_3.html (aprovado).
</specifics>

<deferred>
## Deferred Ideas

- Persistir/versionar cronogramas; gerar OS em lote a partir do cronograma → futuro.
- Otimização além de greedy (bin-packing ótimo) → não necessário.
</deferred>
