# Arquitetura de Módulos — cmasm.erp

## cmasm.erp — Hub Central

Serve auth, usuários, ativos, locais, OS, estoque. Todos os módulos consomem sua API em `http://xcore:8010` (Docker) ou `http://localhost:8010` (dev local).



---

## cmasm_erp.html

São páginas renderizadas **dentro do portal principal** via `showPage()`. Não precisam de container próprio.

| Seção | Módulo (page) | Descrição |
|-------|---------------|-----------|
| HUB | `dashboard` | KPIs e visão geral |

| ERP | `organizacao` | Árvore organizacional | cargos | locais | pessoal (TMFT)
| ERP | `servicos` | Ordens de Serviço (OS) |
| ERP | `transportes` | Viaturas e deslocamentos |
| ERP | `manutencao` | Gestão de manutenção |
| ERP | `estoque` | estoques Manutencao |

### Módulos de Manutenção (PMOC)

Cada um é um HTML autônomo que usa `ativo-template.html` como base. Navegação interna: `dash → frota (equipamentos) → [unidade] → estoque → rel`.

| Arquivo | Setor |
|---------|-------|
| PMOC | `Transportes` | Viaturas e Embarcacoes |
| PMOC | `predial` | Locais e inspeção predial |
| PMOC | `grama` | Controle vegetal / xGrama |
| PMOC | `eletrica.html` | Elétrica |
| PMOC | `aguada.html` | hidraulica |
| PMOC | `refrigeracao.html` | Refrigeração |
| PMOC | `maq-corte` | Máquinas e Equipamentos de Corte |
| PMOC | `maq-peso` | Controle Vegetal (xGrama) |
| PMOC | `paiois` | Paiois / munição |
| PMOC | `eletronica.html` | eletronicos | fonoclama | sensores |
| PMOC | `calibracao` | Controle de calibração |






| Admin | `Usuario` | Configurações | perfil usuario |
 
| Admin | `admin` | Configurações |Edicao de usuários | Árvore organizacional | cargos | locais | Pessoal


---

