# xCMASM / cmasm.erp

Repositório do **HUB + ERP central** do xCMASM (Centro de Mísseis e Armas Submarinas da Marinha do Brasil).

## O que é este repo

`cmasm.erp` contém o núcleo operacional da plataforma:

- **`cmasm_erp.html`** — portal principal single-file (HTML + JS, localStorage, sem build step)
- **`backend/`** — API FastAPI (xCore, porta 8010): auth, usuários, ativos, locais, OS, estoque, grama
- **`assets/`** — SDK JS, CSS shell, fontes compartilhadas entre todos os módulos
- **`data/`** — schemas SQLite (`schema_core.sql`, `schema_grama.sql`)
- **`tools/`** — scripts de seed e importação
- **`referencias/`** — templates para devs de módulos externos (`ativo-template.html`, govbr-template)

Módulos PMOC e módulos externos vivem em repos independentes em `/home/luciano/DEV/`.

## Início rápido

### ERP (frontend)

```bash
cd /home/luciano/DEV/cmasm.erp
npx serve .
# → http://localhost:3000/cmasm_erp.html
```

### API xCore (backend)

```bash
source .venv/bin/activate
uvicorn backend.main:app --port 8010 --reload
# → http://localhost:8010/docs
```

### Primeiro uso (seed)

```bash
python tools/seed_usuarios.py   # 12 usuários; senha padrão "1234" → hash djb2 "170842"
python tools/seed_ativos.py
python tools/seed_estoque.py
```

## Módulos externos

| Módulo | Porta | Repo |
|--------|-------|------|
| xPredial | 8002 | `/home/luciano/DEV/xPredial` |
| xPaiol | 8003 | `/home/luciano/DEV/xPaiol` |
| xAguada | 8001 | `/home/luciano/DEV/xAguada` |
| xCalibracao | 8004 | `/home/luciano/DEV/pmoc_calibracao` |
| xSeguranca | 8000/3000 | `/home/luciano/DEV/xSeguranca` |
| xRegrigeracao | — | `/home/luciano/DEV/xRegrigeracao` |
| xFonoclama | — | `/home/luciano/DEV/xFonoclama` |
| xCFTV | — | `/home/luciano/DEV/xCFTV` |

Todos os externos consomem `GET /api/usuarios` via `XCORE_URL=http://localhost:8010`.

## Docs

| Arquivo | Conteúdo |
|---------|----------|
| `CLAUDE.md` | Guia para Claude Code — estrutura, padrões, endpoints |
| `AGENTS.md` | Instruções de domínio para agentes IA |
| `Rules.md` | Regras de negócio, fluxos, relacionamentos |
| `MODULOS_EXTERNOS.md` | Arquitetura de integração entre módulos |
| `PLANO_IMPLEMENTACAO.md` | Roadmap e status de cada módulo |
