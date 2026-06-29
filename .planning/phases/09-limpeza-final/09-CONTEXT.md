# Phase 9: Limpeza Final - Context

**Gathered:** 2026-06-29
**Status:** Done (executed inline — trivial mechanical cleanup)

<domain>
## Phase Boundary
Remover os HTMLs legados de referência usados como fonte dos imports (Fases 1–5) e limpar as citações desses arquivos no código ativo, deixando o repositório limpo. CLN-01.
</domain>

<decisions>
## Implementation Decisions (confirmadas pelo usuário)
- **Deletar** os 8 HTMLs legados em `.docs_cmasm/referencias/` de forma **permanente** (eram untracked) — confirmado pelo usuário ("remover permanente"). Mantidos: mapas OSM, CSV, screenshots, db-backups, cmasm_backup.json.
- **Limpar** as citações dos nomes de arquivo legados nos comentários do código ativo (provência) — confirmado ("remover também"). Mantido o sentido ("app de campo legado"), removidos os nomes de arquivo.
- Checkpoint git: tag `milestone-import-verificado` no HEAD verificado ANTES da limpeza (recupera o estado do código).
- Importadores de uso único em `tools/` (import_ata2, import_refrig_html, seed_refrig_preventivas, seed_completo) que liam os HTMLs ficam **inertes** — dados já no DB; fora do critério (assets/pmoc/cmasm_erp.html). Anotado.
</decisions>
