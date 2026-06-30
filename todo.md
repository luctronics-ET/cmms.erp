# todo.md — Backlog

## Refrigeração ✅ (na main, branch feat/refrig-erp merged)
- import 171 máquinas (fonte autoritativa = app de campo html)
- motor de cálculo `assets/refrig-engine.js` (criticidade, gás, potência, térmico, capacidade, horas de uso)
- página 7-abas (Inventário Base/Elétrico/Uso · Alertas · Térmico · PMOC+equipe · Cronograma · Serviços · Estoque)
- ficha CRUD do ativo (`PUT /api/pmoc/refrigeracao/{id}`)
- catálogo compartilhado: 4 preventivas + 30 corretivas ARP; criar serviço (+ Serviço)
- materiais por serviço (display + editor add/remove)
- estoque refrigeração (25 itens, consumível/sobressalente/ferramenta, mínimo)
- planos preventivos por máquina (171, freq por criticidade)
- gerar OS preventiva do plano (etapas = checklist)
- organograma (estrutura 79 nós) + equipe técnica via CMASM-13

## Próximas frentes
- [x] Descontar estoque ao concluir OS (status→concluída debita `estoque_movimentos`) — `_debitar_estoque_os` em main.py; débito do `servico_id` da OS via `catalogo_servico_materiais`; idempotente; estoque insuficiente debita disponível e anota falta
- [x] Replicar padrão refrig: Corte + Transportes (viaturas+embarcações)
  - schema: `pmoc_corte`, `pmoc_transportes` (data/schema_core.sql, aditivo)
  - backend: `/api/pmoc/transportes`, `/api/pmoc/corte` (GET list + PUT edit) + backfill no boot (`_seed_pmoc_frota_corte_if_empty`)
  - núcleo: tabs Transportes 🚚 + Corte 🌿 em Manutenção (erp-manutencao.js, FICHA_CFG + renderFichaTab)
  - PMOC app de campo: categorias viaturas/embarcacoes/maq_corte JÁ existiam (pmoc.js)
  - FALTA (próximo): OS preventiva por tipo p/ corte (plano multi-intervalo ≠ molde refrig single-servico); KPIs/gráficos por tab; térmico não se aplica
- [x] Fonoclama integrado como categoria (migrado de xFonoclama/fonoclama.html — era app localStorage standalone)
  - 5 tipos (amplificador/console/alto-falante/linha 70V/sirene) + planos → `_MANUT_TIPOS_PLANOS`
  - 10 dispositivos + 10 peças seedados (`_seed_fonoclama_if_empty`), tabela `pmoc_fonoclama`
  - tab 📣 Fonoclama em Manutenção + `/api/pmoc/fonoclama` (list/edit)
  - NB: fonoclama runtime (firmware ESP32) segue externo; aqui é só a gestão de manutenção dos ativos
- [ ] Térmico real: preencher `locais.area_m2` / `altura_m` (import planilha?)
- [ ] Religar `local_id` dos 39 ativos não-climatizacao (locs ≠ universo refrig)
- [ ] `refri171` (ELETRÔNICA/BIBLIOTECA) sem local — atribuir manual
- [ ] `proxima_execucao` dos planos popula na 1ª manutenção registrada
- [ ] Edição de materiais/serviço exige login não-visitante (token) — ok, documentar

## Modelo de Planos (unificado em catalogo_planos)
- [x] Plano = pacote nomeado de serviços+materiais + disparo (h/km/tempo), aplicável a N tipos por nome
  - schema: `catalogo_planos` +`frequencia`(default) +`aplicavel_tipos`(JSON); `catalogo_plano_itens` +`frequencia`(override por serviço)
  - disparo POR SERVIÇO com default no plano (decisão do usuário)
  - migração: `_seed_catalogo_planos_from_tipos` traz corte(7)+fono(5) p/ o modelo; climatização(12) já vinha da ATA2 → 24 planos
  - backend: `GET /api/catalogo/planos-catalogo?categoria=&tipo=` (lista) + `/{id}` (itens c/ freq+materiais)
  - UI: sub-aba Planos lê o modelo nomeado, escopada por categoria; drawer mostra serviços+disparo+materiais
  - [x] planos viaturas/embarcações: `_seed_planos_transportes_if_empty` (VTR_PICKUP, VTR_CARGA km; EMB_LANCHA h) — serviços+materiais+itens
  - [x] criar/editar plano pela UI: CRUD `/api/catalogo/planos-catalogo` (POST/PUT/DELETE + itens add/remove); botão "+ Plano", drawer com +Serviço/excluir/remover-item
  - [x] vencimento: `GET /api/manutencao/vencimentos?categoria=` (plano↔tipo via aplicavel_tipos + uso_atual → próximo/falta) + sub-aba **Vencimentos** + botão Gerar OS (`POST /api/manutencao/os-preventiva`)
  - decisão: plano↔tipo (aplicavel_tipos) É a atribuição; sem coluna plano_id no ativo
  - FALTA: disparo por_tempo no vencimento (precisa base de data/última exec)
- [x] `planos_manutencao` APOSENTADO (catalogo_planos é fonte única; tabela mantida, regra nunca-DROP)
  - seed parado (`_seed_catalogo_manut_if_empty` não insere mais; mantém serviços+materiais)
  - refrig os-preventiva → resolve por `catalogo_planos` (por tipo; fallback 1º plano clima p/ AC_JANELA/PISO_TETO/SELF que não têm plano próprio); etapas = serviços preventivos
  - `sync.py` → payload `planos_manutencao` DERIVADO de catalogo_planos+itens (mesma shape {tipo_codigo,intervalo}; app PMOC intacto); clima default 90 dias setado p/ preservar intervalo
  - `catalogo.py` `/api/catalogo/planos` deprecado: GET→[], escrita→410 Gone
  - frontend `fetchAll` não busca mais `/api/catalogo/planos`; `calcProxManut`/drawers refrig seguem (usam ERP_MANUT_MOCKS.TIPOS, não a tabela)
  - residual: 240 linhas órfãs em planos_manutencao (inofensivas, ninguém lê); limpar quando quiser

## Pré-preenchimento de OS/SR a partir de item
- [x] mecanismo `_osPrefill` + `setOsPrefill(ctx)` (cmasm_erp.html) — contexto lido pelo openModal e consumido
- [x] modal-nova-ps: campos **Ativo (opcional)** + **Departamento (lotação)**; pré-preenche solicitante/depto/ativo/serviço do contexto; serviço auto-carrega assunto/materiais/requisitos/custo (onPSServicoChange); grava `ativo_id`/`ativoNome`/`departamento` na OS
- [x] ativo OPCIONAL (nem toda OS tem ativo — ex.: mover material por pessoas)
- [x] novaOSManut: responsável default = usuário logado
- [x] no-cache middleware (HTML/JS) no backend → fim do hard-refresh
- [x] export PDF/Excel + ordenação/filtro em todas tabelas (agente bg: `tbl-enhance.js`, `pmoc-engine.js`)
- [x] gatilhos → Nova OS com contexto (helper global `novaOSComContexto({ativoId,servicoId,assunto,descricao})`):
  - Ficha (Manut): botão "Nova OS" por ativo → preenche ativo+assunto
  - Vencimentos: botão "Nova OS…" (ao lado de "Gerar OS") → ativo+assunto+descrição do plano
  - Catálogo: drawer do serviço → "Nova OS com este serviço" → assunto=nome
  - prefill aceita assunto/descrição como texto (serviços do backend não estão no catálogo local do modal)
- FALTA: SR pré-preencher ativo+item quando vier de serviço; gravar `departamento` na OS do backend (coluna nova); pré-fill em dashboards/outras páginas

## Notas técnicas
- Backend: `.venv/bin/python -m uvicorn backend.main:app --port 8010` (script uvicorn tinha shebang quebrado, corrigido)
- ERP servido pelo backend em `/` (mesma origem, sem CORS) — abrir http://localhost:8010/
- Seeders refrig em `tools/`: import_refrig_html · seed_refrig_preventivas · seed_refrig_planos · seed_refrig_estoque · seed_refrig_materiais · seed_organograma
- Backups do DB: `data/core.backup_*.db` (gitignored junto com .venv e *.db)
