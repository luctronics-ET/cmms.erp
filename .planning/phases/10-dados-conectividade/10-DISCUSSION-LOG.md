# Phase 10: Dados & Conectividade - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 10-dados-conectividade
**Areas discussed:** Unificar grama↔ativos (CON-04), Lotação na OS (CON-02), Órfãos no backfill (CON-01), Relatório integridade (CON-06)

---

## Unificar grama↔ativos (CON-04)

| Option | Description | Selected |
|--------|-------------|----------|
| FK + backfill | grama_maquinas.ativo_id→ativos.id, mantém 2 tabelas, menor churn | |
| Aposentar grama_maquinas | grama.py lê ativos direto; tabela paralela vira legado | ✓ |
| Só relatório agora | Só sinaliza duplo cadastro; unifica depois | |

**User's choice:** Aposentar grama_maquinas
**Notes:** Elimina redundância de vez. Risco: grama_operacoes/kanban/calendário/status referenciam a máquina — planner deve mapear e repontar para ativos.id (item de pesquisa).

---

## Lotação na OS (CON-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto + override | Default do cargo do solicitante + seletor opcional no form | ✓ |
| Só auto | Deriva sempre do cargo, sem seletor | |
| Só seletor manual | Usuário escolhe sempre | |

**User's choice:** Auto + override
**Notes:** os.departamento (TEXT) permanece como rótulo denormalizado; nova FK os.lotacao_id→estrutura.

---

## Órfãos no backfill (CON-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Pular + listar | Backfilla match; órfãos ficam null e entram no relatório de integridade | ✓ |
| Exigir resolução antes | Backfill falha se houver órfãos; mapear todos manualmente | |
| Criar nó na estrutura | Gera nó sintético por codigo órfão | |

**User's choice:** Pular + listar
**Notes:** Não-destrutivo, produção-first. Fallback COALESCE(estrutura_id, codigo) sobrevive só enquanto houver órfãos.

---

## Relatório integridade (CON-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Endpoint + UI admin | /api/admin/integridade vivo + painel na aba admin | ✓ |
| Script one-off tools/ | Script Python sob demanda, sem UI | |
| Ambos | Script agora + endpoint depois | |

**User's choice:** Endpoint + UI admin
**Notes:** Auditoria contínua; reusa aba admin existente do cmasm_erp.html.

## Claude's Discretion

Nome do flag de arquivamento, layout do painel de integridade, forma do seletor de lotação, estratégia de casamento modelo/série no backfill de grama.

## Deferred Ideas

De-dup rotas /api/pmoc/refrigeracao + 3 UIs refrig; vínculo doc→ativo (Fase 12); backfill ativos.local_id não-climatização (Fase 11 / RES-06); popular estoque.local_id (futuro).
