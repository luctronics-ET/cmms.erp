# Importação de Dados — xCMASM

## Scripts disponíveis em `tools/`

| Script | Fonte | Destino | Uso |
|--------|-------|---------|-----|
| `seed_usuarios.py` | hardcoded | `usuarios` | Primeiro uso: cria 12 usuários reais (senha `1234` → hash djb2 `170842`) |
| `seed_ativos.py` | hardcoded | `ativos` | Primeiro uso: popula frota de ativos |
| `seed_estoque.py` | hardcoded | `estoque` | Primeiro uso: popula itens de almoxarifado |
| `seed_completo.py` | hardcoded | todos | Executa os três seeds acima em sequência |
| `migrate_from_backup.py` | `cmasm_backup.json` | todas as tabelas | Importa backup JSON do ERP legado |
| `migrate_legacy_js.py` | localStorage export | todas as tabelas | Importa export de localStorage do ERP_core HTML |
| `import_from_refs.py` | `pmoc.refs/` | `locais`, `ativos` | Importa dados de locais/ativos dos CSVs de referência CMASM |
| `import_pmoc_refrigeracao.py` | `pmoc.refs/CMASM_PMOC_REFRIG*.csv` | `locais`, `ativos`, `pmoc_refrigeracao` | Importa planilha PMOC de refrigeração |
| `import_org_from_reference.py` | `.docs_cmasm/` | `usuarios`, `estrutura` | Importa organograma e TMFT dos CSVs |
| `import_locais_xpredial.py` | xPredial DB | `locais` | Sincroniza locais do xPredial para o núcleo |

## Execução

```bash
# Primeiro uso completo
cd /home/luciano/DEV/cmasm.erp
source .venv/bin/activate
python tools/seed_completo.py

# Importar PMOC de Refrigeração
python tools/import_pmoc_refrigeracao.py
# Dry-run (não grava no banco):
python tools/import_pmoc_refrigeracao.py --dry-run

# Importar locais/ativos dos CSVs de referência
python tools/import_from_refs.py
```

## Fontes de dados

| Diretório | Conteúdo |
|-----------|----------|
| `.docs_cmasm/` | CSVs autoritativos: usuários, cargos, TMFT, mapas OSM |
| `/home/luciano/DEV/pmoc.refs/` | Planilhas PMOC: refrigeração, calibração, tabelas de locais |

## Banco de dados

O banco SQLite é criado automaticamente em `data/core.db` ao iniciar o servidor. O schema é carregado de `data/schema_core.sql` + `data/schema_grama.sql`. Todas as migrações são aditivas (nunca DROP).
