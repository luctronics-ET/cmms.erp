# xCMASM / cmasm.erp

Workspace consolidado de gestão operacional do CMASM, com núcleo central em `xCore` e espelhos locais dos módulos satélite que antes ficavam fora da pasta principal.

## Escopo deste repositório

Este repositório passa a concentrar o workspace principal do `xCMASM` em `cmasm.erp`.

- `xCore/` é o núcleo da plataforma e concentra API central, ativos, locais, ordens de serviço, estoque e o domínio de controle vegetal.
- `xPredial/`, `xPaiol/`, `xSeguranca/`, `xCalibracao/`, `xFonoclama/`, `xCFTV/` e `aguada-web/` agora existem também como cópias locais dentro deste workspace.
- O ponto de entrada canônico do portal institucional é `xCore/cmasm-erp.html`.

Importações recentes:

- módulos externos foram espelhados localmente para facilitar manutenção, busca e migração incremental;
- diretórios de dependência e ambiente não foram trazidos (`.git`, `node_modules`, `.venv`, caches e builds);
- `cmasm_erp.html` permanece no repositório como ponte de compatibilidade para o portal canônico em `xCore/`.

## Estado atual

| Área | Situação |
|---|---|
| `xCore/` | funcional, portal principal em `xCore/cmasm-erp.html` |
| `xPredial/` | funcional, com Docker e pytest |
| `xCalibracao/` | importado localmente, ainda parcial |
| `aguada-web/` | importado localmente como espelho do sistema hídrico |
| `xSeguranca/` | frontend presente; backend pendente |

## Estrutura principal

```text
xCore/         núcleo FastAPI + SQLite
xPredial/      gestão predial
xCalibracao/   instrumentos e certificados
aguada-web/    sistema hídrico e MQTT
xSeguranca/    vigilância/CFTV com frontend React
```

## Execução rápida

### xCore

```bash
cd xCore
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8010
```

### xPredial

```bash
cd xPredial
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8002
pytest tests -q
```

## Documentos úteis

- `PLANO_IMPLEMENTACAO.md` descreve o estado atual do workspace e as próximas frentes.
- `importacao.md` registra os espelhos locais e o alinhamento de caminhos após a consolidação em `cmasm.erp`.
- `Rules.md` concentra regras de negócio e fluxos do sistema.

## Observações

- O domínio de `xGrama` está embutido no `xCore` neste workspace.
- O domínio de serviços/OS também está hoje concentrado no núcleo e em frontends locais, sem módulo `xServicos` independente.
- Os satélites ainda podem existir em repositórios externos, mas `cmasm.erp` agora mantém cópias locais para referência e migração.