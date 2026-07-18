---
status: complete
phase: 10-dados-conectividade
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md, 10-04-SUMMARY.md, 10-05-SUMMARY.md, 10-06-SUMMARY.md]
started: 2026-07-18T22:55:22Z
updated: 2026-07-18T23:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Servidor inicia do zero sem erros; migrações aditivas completam; ERP carrega com dados reais (login + listagens funcionam).
result: pass
evidence: Verificado via Playwright em 2026-07-18 — uvicorn cold start limpo (startup complete, sem exceções), GET / = 200, login UI (seed frontend) OK, Portal com dados reais (14 TMFT, 225 ativos PMOC, frota 12/14). Observação (não-bloqueante, design offline-first): bridge backend retorna 401 para usuários do SEED frontend pois os seeds de usuários front/back divergem; comportamento best-effort documentado no código.

### 2. Painel "Integridade de Dados" na aba admin
expected: Painel "Integridade de Dados" aparece na aba admin existente (#page-admin) e renderiza categorias com badges de contagem, expansível por item.
result: pass
evidence: Verificado via Playwright em 2026-07-18 — painel renderiza em #page-admin (Configurações) com "Gerado em", categorias com badges (Locais sem estrutura_id=163, Estoque sem local_id=65, Ativos loc texto=40 — batem com baseline do RESEARCH), e expansão por item lista os registros (screenshot admin-page.png).

### 3. Coluna os.lotacao_id criada via migração aditiva idempotente
expected: Coluna os.lotacao_id (TEXT REFERENCES estrutura(id)) criada via migração aditiva idempotente
result: pass
source: automated

### 4. Coluna ativos.grama_maquina_id criada via migração aditiva idempotente
expected: Coluna ativos.grama_maquina_id (TEXT REFERENCES grama_maquinas(id)) criada via migração aditiva idempotente
result: pass
source: automated

### 5. Coluna catalogo_planos.arquivado_motivo criada via migração aditiva idempotente
expected: Coluna catalogo_planos.arquivado_motivo (TEXT) criada via migração aditiva idempotente
result: pass
source: automated

### 6. Módulo fonoclama registrado com manifest funcional
expected: Módulo fonoclama registrado em modulos_registrados; GET /api/sync/manifest?modulo=fonoclama retorna 10 ativos + 5 planos distintos
result: pass
source: automated

### 7. Backfill estrutura_id roda idempotente
expected: tools/backfill_estrutura_id.py roda sem exceção, imprime contagens e é idempotente (2ª execução = 0 alterações)
result: pass
source: automated

### 8. Matching popula estrutura_id corretamente
expected: Mecanismo de matching popula estrutura_id quando codigo bate com estrutura.id (validado em cópia isolada)
result: pass
source: automated

### 9. Nenhum nó sintético criado em estrutura
expected: Nenhum nó sintético criado em estrutura ao rodar o backfill contra data/core.db real (79 antes/depois)
result: pass
source: automated

### 10. Org joins resolvem por FK com fallback
expected: Org joins em main.py resolvem por FK (estrutura_id) com fallback para codigo via COALESCE
result: pass
source: automated

### 11. GET /api/locais fim-a-fim com join
expected: GET /api/locais funciona fim-a-fim com o join (200, campo estrutura_nome presente por linha)
result: pass
source: automated

### 12. POST /api/os deriva lotacao_id do solicitante
expected: POST /api/os deriva lotacao_id de cargos.usuario_id → cargos.unidade_id quando corpo não envia lotacao_id mas envia solicitante_id
result: pass
source: automated

### 13. POST /api/os respeita override de lotacao_id
expected: POST /api/os respeita override explícito de lotacao_id no corpo, mesmo com solicitante_id presente
result: pass
source: automated

### 14. Contrato externo POST /api/os preservado
expected: Módulos sem auth (PMOC/satélites): POST /api/os com modulo_origem e sem lotacao_id/solicitante_id retorna 201 e departamento preservado
result: pass
source: automated

### 15. Seletor "Lotação" no form de OS
expected: Seletor opcional "Lotação" no modal Nova OS grava lotacao_id via auto-fill quando vazio e via override quando selecionado
result: pass
source: automated

### 16. Conclusão de operação de grama incrementa uso_atual
expected: update_operacao_status (grama.py) incrementa ativos.uso_atual ao concluir operação com horas_utilizadas; combustivel_atual continua em grama_maquinas
result: pass
source: automated

### 17. GET /api/grama/maquinas preserva shape
expected: GET /api/grama/maquinas preserva o shape de normalizeVegMaq servindo por ativos + LEFT JOIN grama_maquinas
result: pass
source: automated

### 18. Backfill grama link 1:1 idempotente
expected: tools/backfill_grama_link.py linka apenas MS650+SOL (1:1); ambíguos não pareados; idempotente; grama_maquinas nunca DROP
result: pass
source: automated

### 19. Plano órfão arquivado via flag
expected: Plano plano-3c349c22f4 arquivado via ativo=0 + arquivado_motivo, nunca DROP
result: pass
source: automated

### 20. Plano arquivado some do manifest
expected: Plano arquivado some da query real do manifest (backend/sync.py:519, WHERE ativo=1)
result: pass
source: automated

### 21. Vizinhos plano-clima intactos
expected: Planos plano-clima-g1..g12 (aplicavel_tipos=NULL) permanecem intactos e ativos
result: pass
source: automated

### 22. Script de arquivamento idempotente
expected: Segunda execução não sobrescreve arquivado_motivo
result: pass
source: automated

### 23. Rules.md documenta planos_manutencao como legado
expected: Rules.md §11 documenta planos_manutencao (0 linhas) como APOSENTADO/legado, nunca DROP
result: pass
source: automated

### 24. GET /api/admin/integridade com auth por role
expected: GET /api/admin/integridade retorna 401 sem token, 403 para role != admin, 200 com JSON {gerado_em, categorias} para admin
result: pass
source: automated

### 25. Categorias de integridade batem com baseline
expected: Categorias retornam contagens reais batendo com baseline do RESEARCH (locais_sem_estrutura=163, estoque_sem_local=65)
result: pass
source: automated

## Summary

total: 25
passed: 25
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
