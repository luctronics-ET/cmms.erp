# Spec — Integração Refrigeração no ERP (Fase 1)

**Data:** 2026-06-26
**Origem:** `.docs_cmasm/cmasm13-govbr-v8_3 (1).html` (app de campo standalone, 171 máquinas AC, localStorage).
**Objetivo:** Portar dados + motor de cálculo do app de refrigeração para o núcleo `cmasm.erp`, como página rica dentro do módulo Manutenção, ancorada no modelo de domínio compartilhado do core.

---

## 1. Decisões registradas (brainstorming 2026-06-26)

- **PMOC centralizado** — manter arquitetura núcleo + PMOC único. Não criar HTMLs separados por categoria.
- **Onde:** módulo Manutenção do `cmasm_erp.html` (online, usa backend :8010).
- **Escopo:** motor de cálculo **+** dados.
- **Faseado:** Fase 1 = Refrigeração (este spec). Fases 2-4 (Maq Corte, Viaturas, Embarcações) = specs próprios depois. View genérica categorizada já existe.
- **Motor de cálculo:** JS no cliente (`assets/refrig-engine.js`), porta os algoritmos do html sem reescrever. Backend só persiste.
- **Reconciliação de dados:** html = fonte autoritativa (171, curado, rico). Core tinha 162 de import CSV bruto (loc bagunçado). Diff de 9 era ruído de nomenclatura/split.
- **G1:** adicionar `ativos.local_id → locais` (aditivo) e religar os 201 ativos.
- **G2:** equipe técnica via `estrutura`/`cargos` (organograma) — técnicos = pessoas do setor de refrigeração.
- **G3:** descartar zona geográfica AZUL/VERMELHA. Usar só `locais.area` funcional.

---

## 2. Modelo de domínio — spine compartilhado (já existe no core)

A regra central: **o app de refrigeração não tem modelo próprio**. Tudo pendura nas tabelas do núcleo.

```
estrutura (setores, árvore via pai)
   └─ cargos (usuario ↔ posição)
        └─ usuarios (pessoas)  ── qualificações ──> usuario_qualificacoes
locais (árvore predio→sala via parent_id; area_m2, altura_m)
   ├─ ativos (equipamentos; +local_id FK)         ← G1
   │     └─ pmoc_refrigeracao (detalhe AC; FK local_id já existe)
   └─ param térmico do ambiente (estende locais)  ← novo
ordens_servico + os_etapas + os_historico (manutenção)
   └─ estoque + estoque_movimentos (materiais/peças)
```

Princípio de negócio (do usuário): *pessoas pertencem a setores e têm cargos; trabalham em locais; locais têm equipamentos e parâmetros; refrigeração regula temp/umidade do local; equipamentos precisam manutenção periódica ou por uso; manutenção realiza serviços e consome materiais.*

---

## 3. Migrações de schema (aditivas — `PRAGMA table_info` antes, nunca DROP)

1. **`ativos.local_id INTEGER REFERENCES locais(id)`** (G1). Índice `idx_ativos_local`.
2. **Parâmetros térmicos do ambiente** — estende `locais` com colunas usadas pelo `calcBTU` que ainda não existem:
   - `area_m2`, `altura_m` — **já existem**.
   - novas: `tipo_uso TEXT`, `solar TEXT`, `pessoas INTEGER`, `janelas INTEGER`, `ilum_w REAL`, `equip_w REAL`, `uso_continuo INTEGER`, `nivel_calc INTEGER`.
   - *(decisão de implementação: colunas em `locais` vs side-table `local_termico`. Default: colunas em `locais`, pois é 1:1 com o ambiente e evita join. Revisar no plano se poluir a tabela.)*
3. Log de manutenção do html (`cmasm13_log_v1`) → mapeia para `ordens_servico` (tipo preventiva/corretiva/inspecao) + `os_historico` + checklist em `os_etapas`. Sem tabela nova.
4. Equipe técnica → **sem tabela nova**: deriva de `estrutura`/`cargos`/`usuarios` (G2). Config de capacidade (nº equipes, turnos, dias úteis) — tabela leve `pmoc_refrig_config` (chave-valor JSON) OU constante; decidir no plano.

---

## 4. Migração de dados (171 html → core)

Script `tools/import_refrig_html.py` (idempotente, backup antes):

1. Extrai `INITIAL_DATA` (171) do html via regex+json.
2. Para cada máquina: resolve `local_id` casando `predio`/`local` (normalizado, sem acento) contra a árvore `locais`. Onde não casar (nomes divergentes — ver diff §invest.), **corrige o local no core** ou cria o nó faltante (predio/sala) — html manda.
3. Upsert em `ativos` (categoria `climatizacao`): mapeia camelCase→snake (`btu`, `tensao`, `fabricante`, `pat`=patrimonio, `tipo` AC_SPLIT/PISO_TETO/JANELA/SELF, `uso_atual`, `local_id`).
4. Upsert em `pmoc_refrigeracao` (detalhe): `funciona`, `estado`, `refrig_permanente`, `horas_dia`, `dias_semana`, `criticidade`+`criticidade_manual`, `corrente_nominal`, `data_instalacao`, `ultima_manutencao`, `obs`.
5. Params térmicos (`cmasm13_thermal_v1` do html, se exportado) → colunas térmicas de `locais`. Se não houver export, ficam null e o usuário preenche pela UI.
6. Relink dos 201 `ativos.local_id` (G1) — refrig pelo passo 2; demais por melhor-esforço do texto `loc` atual.

Backup `data/core.backup_<ts>.db` antes de rodar.

---

## 5. Motor de cálculo — `assets/refrig-engine.js`

Porta **verbatim** (ajuste só de I/O) os algoritmos do html. São a propriedade intelectual a preservar:

| Função | O que faz |
|---|---|
| `autoCrit(e)` | criticidade automática (refrigPermanente→CRÍTICA; servidor/paióis EXOCET/ASPIDE/MK48…→CRÍTICA; saúde/segurança/comando→ALTA; NOK→ALTA; …) |
| `PMOC_INT` + `nextPmoc(e,tipo)` | intervalos inspeção/preventiva/revisão por criticidade |
| `estimateGas(e)` | inferência R-22/R-410A/R-404A + carga (g) por interpolação BTU |
| `estimatePower(btu)` / corrente nominal | btu/10.5 W; corrente = btu/10.5/tensão |
| `estTempoServico(e,tipo)` | homem-hora: itens×10min×fator_equip×fator_manut+setup |
| `demandaAnual(e)` | demanda anual de h e nº OS por máquina |
| `capacidade()` | h/ano da equipe (equipes×turnos×dias) + utilização |
| `calcBTU(p)` | carga térmica NBR 5858/16401, 3 níveis, fatores altura/solar/pessoas/janelas/eletr/ilum/equip/contínuo |
| `thermalStatus(inst,calc)` | gap analysis sub/super/adequado |
| cronograma | fila por criticidade distribuída em dias úteis respeitando capacidade |

Entrada muda: em vez de ler localStorage, recebe objetos vindos da API (ativo+pmoc_refrigeracao+local). Saída idêntica.

**Self-test:** `node assets/refrig-engine.js` com asserts nos cálculos-chave (calcBTU em caso conhecido, autoCrit nos gatilhos, estimateGas por tipo/estado). Sem framework.

---

## 6. Página Refrigeração na Manutenção

Nova sub-página categoria `climatizacao` no módulo Manutenção (`assets/erp-manutencao.js` já tem chips por categoria). Reproduz as telas do html lendo do backend:

- **Inventário** (sub-abas Base / Elétrico / Uso-PMOC) — tabela com filtros+sort (reusa `tbl-enhance.js`), badges, highlight NOK. Detalhe + form editar/novo.
- **Alertas** — agrupados (vazamento/NOK/verificar).
- **PMOC** — Plano & Capacidade / Cronograma de Mobilização / Equipamentos por criticidade.
- **Cálculo Térmico** — por ambiente (`locais`), gap analysis, form lateral.
- **Equipe** — read de `estrutura`/`cargos` (setor refrigeração); config de turnos/dias.
- Export/import CSV (inventário, alertas, PMOC, térmico) — reusa o que o html já faz.

UI segue design system dark do ERP (não govbr — o ERP é dark). Reaproveita componentes existentes (`pmoc-engine.js`, `tbl-enhance.js`).

---

## 7. API endpoints (backend :8010)

- `GET /api/ativos?categoria=climatizacao` — já existe; incluir join pmoc_refrigeracao + local.
- `GET/POST/PUT /api/pmoc/refrigeracao/{id}` — CRUD detalhe refrig (novo, em `backend/`).
- `GET/PUT /api/locais/{id}/termico` — params térmicos do ambiente (novo).
- `GET /api/equipe/refrigeracao` — técnicos via estrutura/cargos (novo).
- Manutenção/OS já cobertas por `/api/os`.

---

## 8. Dependências / pré-requisitos

- **Organograma:** `estrutura`/`cargos` estão vazias. Rodar/estender `tools/seed_completo.py` (fonte `.docs_cmasm/cmasm_backup.json`, 79 nós) para popular, e identificar o nó do setor de refrigeração (G2).
- **Qualificações:** opcional — se preferir qualificação a setor, `usuario_qualificacoes` está vazia.

---

## 9. Fora de escopo (fases futuras)

- Fase 2 Maq Corte (horímetro; planos TIPOS já em `erp-manutencao-mocks.js`).
- Fase 3 Viaturas (km; reusa frota do módulo Transportes).
- Fase 4 Embarcações (horas).
- Modo offline do PMOC de campo para refrigeração (sync via `/api/sync/*`).

---

## 10. Verificação

- `node assets/refrig-engine.js` → asserts dos cálculos passam.
- `tools/import_refrig_html.py` rodado: 171 ativos climatizacao + 171 pmoc_refrigeracao, todos com `local_id` resolvido; relatório de locais criados/corrigidos.
- Página Refrigeração carrega do backend, KPIs/alertas/cronograma batem com o html para o mesmo dataset.
- Testes existentes (`pytest`) seguem passando.
