# Phase 9 — Limpeza Final: SUMMARY

**Requirement:** CLN-01
**Executed:** 2026-06-29 (inline, mechanical)

## What was done
1. **Git checkpoint tag** `milestone-import-verificado` criada no HEAD verificado (`686aa1d`) antes de qualquer deleção — estado completo do milestone (Fases 1–8) recuperável.
2. **Removidos (permanente)** os 8 HTMLs legados de referência em `.docs_cmasm/referencias/`:
   - CMASM_Gestao_v2.html, cmasm13-govbr-v8_3.html, ata2_carioca_solution.html, ativo-template.html, pmoc-2a-ficha-ambiente.html, pmoc-2b-equipamento-refrig.html, pmoc-equipe-tecnica.html, pmoc-ocupante.html
   - Eram untracked; remoção permanente confirmada pelo usuário.
   - **Mantidos**: map_cmasm-bnrj.osm, map_cmasm_2026abr.osm, cmasm_backup.json, screenshots/, screenshot_catalogo.jpeg, db-backups/ (dados/refs autoritativos, não UI legada).
3. **Limpeza de citações** dos nomes de arquivo legados nos comentários de procedência do código ativo (mantido o sentido, removido o nome do arquivo deletado):
   - `assets/refrig-engine.js:4`, `assets/erp-manutencao.js:1365`, `backend/manutencao.py` (3 comentários).

## Verification
- `grep -rn "Gestao_v2\|cmasm13-govbr" assets/ pmoc/ cmasm_erp.html backend/` → **ZERO** ✓ (critério SC-3 atendido)
- `node --check` em assets/refrig-engine.js + erp-manutencao.js → OK
- `python -c "import backend.main, backend.manutencao, backend.docs"` → OK (deleção não afetou runtime)
- Edits são apenas comentários → sem mudança de lógica/testes.

## Notas
- Importadores de uso único em `tools/` (import_ata2_climatizacao.py, import_refrig_html.py, seed_refrig_preventivas.py, seed_completo.py) referenciavam os HTMLs como fonte de seed — dados já carregados no DB; agora inertes. Fora do escopo do critério (que cobre assets/pmoc/cmasm_erp.html). `test_import_ata2_climatizacao` permanece entre as 12 falhas pré-existentes (baseline), sem nova regressão.
- App não importa nenhum HTML legado em runtime — só os seeds históricos, já executados.

## Commits
- tag `milestone-import-verificado` (686aa1d)
- chore(09): limpeza final — remover HTMLs legados + citacoes de procedencia (CLN-01)
