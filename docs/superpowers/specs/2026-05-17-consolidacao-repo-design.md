# Design: Consolidação do Repositório cmasm.erp

**Data:** 2026-05-17  
**Status:** Aprovado

## Objetivo

Limpar o repositório `cmasm.erp` para que reflita seu papel real: HUB + ERP central. Módulos PMOC e páginas legadas migram para repositórios externos próprios. O repo fica enxuto e sem ambiguidade de responsabilidade.

## Estrutura Resultante

### Fica na raiz / permanece inalterado

| Path | Papel |
|------|-------|
| `cmasm_erp.html` | Portal principal (HUB + ERP) |
| `index.html` | Acesso rápido entre módulos |
| `backend/` | FastAPI API — xCore nucleus |
| `assets/` | SDK, CSS shell, fontes |
| `data/` | `schema_core.sql`, `schema_grama.sql` |
| `tools/` | Scripts de seed/migração |
| `CLAUDE.md`, `AGENTS.md`, `Rules.md` | Docs de referência do repo |
| `MODULOS_EXTERNOS.md`, `PLANO_IMPLEMENTACAO.md` | Docs de referência do repo |
| `README.md`, `importacao.md`, `todo.md` | Docs de trabalho |
| `Dockerfile`, `requirements.txt`, `.gitignore`, `.env.example` | Config |
| `cmasm.erp.code-workspace`, `xCMASM.code-workspace` | Workspaces |

### Nova pasta `referencias/`

Templates e engines que desenvolvedores de módulos externos consomem como ponto de partida.

| Arquivo | Motivo |
|---------|--------|
| `ativo-template.html` | Template base para novos módulos |
| `xcmasm-govbr-portal.html` | Template GOV.BR portal |
| `xcmasm-govbr-template.html` | Template GOV.BR genérico |
| `pmoc-engine.js` | Engine PMOC — repos externos vão consumir |

### Nova pasta `.delete/`

Staging area para arquivos retirados do núcleo. Podem ser excluídos permanentemente após cada módulo externo confirmar que tem cópia própria.

**Módulos PMOC:**
- `refrigeracao.html`, `eletrica.html`, `calibracao.html`
- `maq-corte.html`, `fonoclama.html`

**Legado X-prefixado:**
- `xgrama.html`, `xmap.html`, `xservicos.html`

**Versões antigas do portal:**
- `cmasm-erp.html` (portal antigo separado), `servicos.html`

**Stubs de módulos externos:**
- `cftv.html`, `seguranca.html`, `paiol.html`, `predial.html`

**Frontend legado:**
- `frontend/` (launcher Vue + mapa Leaflet)

## O que NÃO muda

- Nenhum path de `backend/`, `assets/` ou `data/` é alterado — sem risco de quebrar imports, rotas FastAPI ou referências de CSS.
- `CLAUDE.md` recebe atualização mínima: seção de estrutura de repo refletindo as novas pastas `referencias/` e `.delete/`.

## Critério de remoção definitiva de `.delete/`

Cada arquivo em `.delete/` pode ser removido com `git rm` depois que o módulo externo responsável confirmar que tem cópia funcional do artefato.
