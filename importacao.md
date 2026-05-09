# Importações e Consolidação do Workspace

Atualizado em 2026-05-08.

## Objetivo

Registrar a consolidação do antigo núcleo `xCMASM` dentro de `cmasm.erp` e o espelhamento local dos módulos que ainda estavam fora da pasta principal.

## Estrutura consolidada

- `xCore/` permanece como o núcleo operacional e canônico do ERP.
- `xCore/cmasm-erp.html` é o ponto de entrada principal do portal institucional.
- `cmasm_erp.html` agora funciona como ponte de compatibilidade para `xCore/cmasm-erp.html`.
- `index.html` funciona como portal de acesso rápido e agora aponta para caminhos válidos dentro do workspace atual.

## Módulos espelhados localmente

Os diretórios abaixo foram copiados para dentro de `cmasm.erp/`:

- `xFonoclama/`
- `xPaiol/`
- `xPredial/`
- `xSeguranca/`
- `aguada-web/`
- `xCalibracao/`
- `xCFTV/`

## Critérios da cópia

Foram excluídos do espelhamento:

- `.git/`
- `node_modules/`
- `.venv/`
- `.pytest_cache/`
- `.playwright-mcp/`
- `dist/`
- `build/`
- `coverage/`
- `__pycache__/`

O objetivo foi trazer código-fonte, documentação e artefatos de configuração úteis para manutenção e migração, sem replicar dependências e metadados de ambiente.

## Ajustes aplicados após a importação

- `xCMASM.code-workspace` passou a apontar para os diretórios locais dentro de `cmasm.erp/`.
- `index.html` deixou de apontar para o caminho legado `/ERP_core/cmasm-erp.html` e passou a usar `xCore/cmasm-erp.html`.
- Links de retorno no `xCore/frontend/servicos/` e no shell do `xPredial` foram alinhados com o novo layout.
- O script `xPredial/scripts/seed_locais_cmasm.py` foi ajustado para ler `/.docs_cmasm/cmasm_cargos.csv` em vez de depender de `ERP_core/`.

## Observações

- Os módulos externos podem continuar existindo em repositórios separados fora de `cmasm.erp`, mas a manutenção cotidiana agora pode ser feita a partir deste workspace consolidado.
- URLs de execução dos módulos continuam centralizadas em `assets/xcmasm-module-links.js` e podem depender de serviços locais em `localhost`.