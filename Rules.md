# xCMASM · Regras técnicas e operacionais (núcleo)

Documento vivo. Cobre regras **técnicas e operacionais** do núcleo `cmasm.erp`: schema, lifecycle de OS no banco, idempotência de sync, modelo do catálogo, condicionais. Para o **modelo de domínio** (categorias de ativos, fluxos de PS/OS/SR, transportes, estoque distribuído) ver `Regras de Negocio e Fluxos.md`.

> Princípio: o núcleo é a **fonte da verdade** do cadastro mestre (usuários, ativos, estoque, OS). O PMOC único de campo trabalha offline e sincroniza com o núcleo via API. Onde houver conflito de semântica entre este documento e `Regras de Negocio e Fluxos.md`, o último prevalece para domínio; este prevalece para implementação.

---

## 1. Escopo do núcleo

| Domínio | Responsabilidade |
|---------|------------------|
| **Usuários / Organização** | Cadastro mestre de pessoas, cargos, lotações, estrutura organizacional. Auth e sessão. |
| **Ativos** | Cadastro mestre de equipamentos/viaturas/embarcações/instalações. Estado de uso (`uso_atual`), arquivamento. |
| **Estoque** | Catálogo de materiais, saldos por seção, movimentos. Alertas de mínimo e validade. |
| **OS / Serviços** | Workflow PS → OS → SR (Solicitação de Recursos). Painel de execução e Kanban. |
| **Manutenção (painel)** | Visão consolidada de planos preventivos, vencimentos e histórico — não executa OS, **gera e monitora**. |
| **Documentos** | Repositório de POPs, certificados, fotos, normas. Vinculáveis a ativos / OS / locais. |
| **Hub** | Portal de acesso aos módulos externos + dashboards de saúde de sincronização do PMOC. |

Tudo o que **não** está nessa lista (regras técnicas específicas de cada categoria de ativo — climatização, frota, etc.) vive **dentro do PMOC único** como categoria interna, ou em módulo *realmente* externo (hardware/Postgres próprio — ver `MODULOS_EXTERNOS.md`).

---

## 2. Entidades e relações

```
Usuários ─────────────► OS (responsável, solicitante, autorizador)

Ativos (cadastro mestre)
  │  uso_atual incrementado por: OS concluída, push de PMOC, lançamento manual
  ├──► Plano de Manutenção (por tipo)
  │      gatilho: uso_atual ≥ proximo_uso  → alerta no painel Manutenção
  │
  └──► OS (filhas)
         ciclo: PS → autorizada → iniciada → em_execucao → pronto → concluída
         pode ter: NECs, SRs, materiais, etapas, custo
         ao concluir → baixa Estoque + incrementa uso_atual do ativo

Estoque (mestre + movimentos)
  │  movimentações: entrada / saída / ajuste / reserva
  │  saída automática ao concluir OS com materiais
  └──► alerta quando qtd_atual < qtd_minima ou validade próxima

Documentos
  └──► vinculam-se opcionalmente a ativo_id, os_id, local_id
```

---

## 3. Ativos

### Princípio

O núcleo guarda o **cadastro mestre**. O PMOC opera sobre uma cópia local sincronizada (por categoria) — não cria ativos novos sem aprovação no núcleo.

### Campos críticos

| Campo | Regra |
|-------|-------|
| `id` | UUID/ID estável. Nunca reaproveitar. |
| `tipo` | Determina o plano de manutenção aplicável. |
| `categoria` | Agrupa para painéis e seleciona qual aba do PMOC opera o ativo (climatizacao, frota_terrestre, frota_naval, maquinas_corte, eletrica, predial, instrumentos, paiois_item, outros). |
| `uso_atual` | Numérico (h/km/meses). Atualizado por OS, push de PMOC, ou manual. **Nunca decrementar.** |
| `ativo` | `1` = em serviço; `0` = arquivado. **Nunca deletar.** |
| `responsavel_pmoc` | Qual categoria do PMOC é dona operacional do ativo (informativo). Evita ambiguidade ao avaliar planos. |

### Categorias mantidas pelo núcleo

| Categoria | Unidade | Categoria do PMOC |
|-----------|---------|-------------------|
| `climatizacao` | meses ou horas | refrigeracao |
| `frota_terrestre` | km | transportes |
| `frota_naval` | horas | transportes |
| `maquinas_corte` | horas | grama |
| `eletrica` | horas | eletrica |
| `predial` | meses | predial |
| `instrumentos` | meses (validade) | calibracao |
| `paiois_item` | — | paiois |
| `outros` | livre | — |

> O núcleo **não** carrega regras técnicas de cada categoria (intervalos, materiais específicos). Isso vive no PMOC como configuração da categoria correspondente. O núcleo só guarda o ativo, o `uso_atual` e as OS resultantes.

---

## 4. Ordens de Serviço (OS)

### Origens

| Tipo | Quem abre | Origem |
|------|-----------|--------|
| `corretiva` | Qualquer usuário | Defeito reportado |
| `preventiva` | PMOC ou painel Manutenção | Plano vencido |
| `inspecao` | PMOC | Checklist periódico |
| `administrativa` | Gestor | Tarefa admin |
| `instalacao` | Técnico | Novo equipamento |
| `periodica` | Sistema/admin | Rotina fixa (varrição, recolha) |

### Ciclo de vida

```
PS (Pedido de Serviço)
  │  autorização do gestor da lotação + NECs satisfeitas
  ▼
autorizada → iniciada → em_execucao ⇄ espera
                                │
                                ▼
                              pronto (aguarda aprovação)
                                │
                                ▼
                            concluida ─► debita estoque + atualiza uso_atual

Em qualquer estado → cancelada (motivo obrigatório)
```

Status no banco: `aberta | autorizada | iniciada | em_execucao | espera | pronto | concluida | cancelada`.

### PS vs OS vs SR

- **PS (Pedido de Serviço)** — entrada da demanda. Pode gerar 1+ OS filhas.
- **OS (Ordem de Serviço)** — unidade de execução.
- **SR (Solicitação de Recursos)** — pedido material/transporte/local/serviço externo vinculado a uma OS. Bloqueia execução até atendido.

### NECs (necessidades de pré-execução)

| Tipo | Bloqueia até |
|------|--------------|
| `nec_material` | Reserva confirmada no Estoque |
| `nec_ativo` | Ativo disponível e alocado |
| `nec_servico` | Fornecedor/terceiro confirmado |
| `nec_local` | Reserva de espaço confirmada |

Enquanto há NEC pendente → OS fica em `espera`.

### Campos obrigatórios

`titulo`, `tipo`, `prioridade` (`baixa|media|alta|urgente`), `solicitante_id`, `lotacao_origem`, `modulo_origem`.

`ativo_id` e `responsavel_id` exigidos quando aplicáveis.

### `modulo_origem`

Identifica quem criou a OS. Valores: `manual`, `manutencao`, `pmoc:<categoria>` (ex: `pmoc:refrigeracao`, `pmoc:transportes`), ou nome de módulo externo (ex: `aguada-web`, `xseguranca` — ver `MODULOS_EXTERNOS.md`).

---

## 5. Estoque

### Tipos de material

| Tipo | Saída por |
|------|-----------|
| `consumivel` | OS de manutenção |
| `sobressalente` | OS de manutenção |
| `epi` | Requisição direta |
| `material_escritorio` | Requisição direta |
| `nautico` | OS naval |

### Movimentações

| Operação | Origem |
|----------|--------|
| `entrada` | NF, transferência, devolução de OS |
| `saida` | OS concluída (automático) ou requisição direta |
| `ajuste` | Inventário/correção |
| `reserva` | OS aberta com material (estado intermediário) |

### Alertas

- `qtd_atual < qtd_minima` → badge "Baixo" + item em "Necessidades".
- Validade ≤ 30/90/180 dias → painel de validades com semáforo.

### Modelo distribuído

Cada seção gerencia seu próprio mínimo. Aquisições podem ser centralizadas ou setorizadas.

| Seção | Materiais típicos |
|-------|-------------------|
| CMASM-13 (Manutenção) | Óleos, filtros, solda, madeira, parafusos, material elétrico |
| CMASM-11 (Prefeitura) | Limpeza, EPI, ferramentas gerais |
| CMASM-20 (Armas) | Sobressalentes de armamento |

**CADBEM** (sistema patrimonial da Marinha) cobre bens permanentes. O Estoque do ERP cobre apenas consumo e sobressalentes operacionais — **não substitui** o CADBEM. Integração futura via export CSV.

---

## 6. Painel de Manutenção (núcleo)

Visão consolidada e read-mostly. **Não executa OS** — gera, monitora e abre OS no fluxo PS→OS.

```
Manutenção (painel núcleo)
  ├─ Lista de ativos por categoria, com status do próximo serviço:
  │     verde = ok  |  amarelo = < 20% do intervalo  |  vermelho = vencido
  ├─ Origem do uso_atual: OS concluída | push de PMOC | manual
  ├─ Botão "Abrir OS preventiva" → cria PS pré-preenchido
  └─ Histórico de OS por ativo
```

### Atualização de `uso_atual` — fontes válidas

1. OS concluída (núcleo) — incremento por delta declarado na OS.
2. Push do PMOC — evento `uso_atual_inc`.
3. Lançamento manual no painel (com justificativa).

> Decrementos **não** são aceitos. Correção de leitura errada → `ajuste` com motivo obrigatório.

---

## 7. Documentos

Repositório vinculável a ativo / OS / local. Cobre:

- POPs, instruções de trabalho, normas técnicas
- Certificados (calibração, NR-12, NR-13, ART)
- Fotos antes/depois de OS, plantas
- Relatórios PMOC mensais/anuais

### Regras

- Arquivos imutáveis. Nova versão = novo upload, com `substitui_doc_id`.
- Vinculação opcional a `ativo_id`, `os_id`, `local_id` (qualquer combinação).
- Acesso filtrado por lotação (documentos restritos só aparecem para a lotação dona).

---

## 8. Integrações PMOC ↔ núcleo

O PMOC único sincroniza com o núcleo por **categoria**. Cada categoria do PMOC (refrigeracao, predial, paiois, transportes, grama, eletrica, calibracao) faz sync independente usando o mesmo contrato.

| Direção | Endpoint | Carga |
|---------|----------|-------|
| Núcleo → PMOC | `GET /api/sync/manifest?modulo=<categoria>&since=<iso>` | Ativos, usuários, estoque, catálogo + planos relevantes à categoria |
| PMOC → Núcleo | `POST /api/sync/push` | Lista de eventos: OS criada, movimento de estoque, incremento de uso, documento |
| Núcleo → PMOC | `GET /api/sync/cursor?modulo=<categoria>&device=<>` | Último evento confirmado |

**IDs:** PMOC gera UUIDs locais. Núcleo aceita o UUID como `origem_id`. Não há renumeração.

**Conflito:** núcleo sempre vence em conflito de cadastro mestre (ativos, usuários). PMOC vence em fato operacional (registro de manutenção, leitura de horímetro).

**Categorias e canonização:** valor de `modulo=` no manifest é a categoria (ex: `modulo=refrigeracao`), não `pmoc_refrigeracao`. Tabela `modulos_registrados` reflete essa lista.

---

## 9. Princípios de migração de schema

- **Aditiva apenas.** `PRAGMA table_info` antes de qualquer `ALTER`. Nunca `DROP`.
- IDs são estáveis. Reaproveitamento é proibido.
- Arquivamento (`ativo=0`) substitui exclusão.

---

## 10. Catálogo de Serviços (modelo híbrido)

Catálogo é o **vocabulário compartilhado** que define o que pode ser executado. Núcleo guarda o catálogo oficial; o PMOC pode criar entradas locais para casos pontuais que **não** voltam ao núcleo (decisão híbrido).

### Entidades

```
catalogo_servicos
  ├─ id                    UUID
  ├─ codigo                slug curto (LIMPEZA_SPLIT_PADRAO_v2)
  ├─ nome                  "Limpeza padrão split 9k–18k BTU"
  ├─ escopo                'central' | 'local'
  ├─ versao                int (incrementa a cada revisão)
  ├─ pop_doc_id            → documentos (POP em md/pdf)
  ├─ tempo_estimado_min
  ├─ servico_pai_id        UUID nullable (hierarquia)
  ├─ aplicavel_a           JSON: { categorias: [...], tipos: [...] }
  ├─ criado_por_modulo     'manutencao' | 'pmoc:<categoria>'  (local → não sincroniza)
  ├─ criado_em / criado_por
  └─ ativo                 bool (arquivamento, nunca deletar)

catalogo_servico_materiais
  └─ servico_id, material_id, qtd, unidade, obrigatorio:bool

catalogo_servico_ferramentas
  └─ servico_id, nome_ferramenta, qtd, obrigatorio:bool

catalogo_servico_pessoal
  └─ servico_id, qualificacao_codigo, qtd, opcional:bool

catalogo_condicionais
  └─ servico_id, expressao  (DSL simples: 'clima!=chuva && energia==ativa')
                             avaliada localmente pelo PMOC
```

### Regras

- **Versionamento imutável**: editar um serviço gera **nova versão** (`versao+1`); OS sempre referencia a versão **vigente no momento da geração** (`servico_id` + `servico_versao_snapshot`). Histórico não muda mesmo após revisão do POP.
- **Escopo `central`**: editável só no núcleo. Replicado para o PMOC via `manifest` (filtrado por categoria).
- **Escopo `local`**: criado dentro de uma categoria do PMOC, vive no IndexedDB do device. **Não** é enviado de volta ao núcleo no `push`. Quando uma OS local for criada a partir dele, a OS leva um **snapshot completo do serviço embarcado** (materiais, POP inline, pessoal), para que o núcleo tenha histórico íntegro sem precisar do catálogo local.
- Promoção: serviço local pode ser **promovido** a central via UI do núcleo (operador copia e formaliza). Não há promoção automática.

### Hierarquia

Serviço pai agrupa filhos (ex: "Revisão completa anual" → filhos: troca de óleo, troca de filtros, balanceamento). Execução do pai cria 1 OS por filho mais 1 OS pai (rastreio).

---

## 11. Planos de Manutenção

Plano liga **serviço × ativo (ou tipo) × frequência × criticidade**.

```
planos_manutencao
  ├─ id                 UUID
  ├─ ativo_id           OU tipo_codigo (1 dos dois — plano por instância ou por tipo)
  ├─ servico_id         + servico_versao_pin (opcional, fixa versão)
  ├─ frequencia         JSON: { tipo: 'periodica', valor: 'P1M' }   ISO 8601 duration
                              { tipo: 'por_uso',   valor: 500, unidade: 'h' }
                              { tipo: 'cron',      valor: '0 0 1 * *' }
  ├─ criticidade_override  nullable — sobrescreve regra por nível do ativo
  ├─ proxima_execucao   data calculada
  ├─ ultima_execucao    data
  ├─ janela_permitida   JSON: { hora_inicio: '02:00', hora_fim: '05:00', dias: ['sab','dom'] }
  ├─ ativo              bool
  └─ criado_por_modulo, criado_em
```

### Resolução por criticidade

Cada ativo tem `criticidade ∈ {admin | operacional | critico_24x7}` (campo do ativo). O plano pode definir frequências diferentes por criticidade:

```
frequencia: {
  admin:        'P1Y',
  operacional:  'P3M',
  critico_24x7: 'P1M'
}
```

A frequência efetiva é resolvida no momento de avaliação. `criticidade_override` no plano vence o valor padrão do ativo.

### Janela de manutenção

`janela_permitida` define quando a OS pode iniciar (ex: AC do CIC só fora do expediente). Avaliada como condicional implícita.

---

## 12. Motor de geração de OS (executado no PMOC offline)

O PMOC tem cópia local do catálogo + planos + ativos da categoria selecionada. Avalia periodicamente (a cada N min ou em evento `pull` confirmado):

```
para cada plano ATIVO da categoria:
  1. resolver frequencia conforme criticidade
  2. calcular proxima_execucao
  3. se proxima_execucao ≤ hoje:
       a. avaliar condicionais (do serviço + janela do plano)
          → falhou: plano marcado 'adiado', tenta de novo depois
       b. verificar materiais no estoque local + reservas
          → faltam: gera NEC, status = 'espera'
       c. verificar pessoal disponível (qualificações + escala)
          → falta: status = 'espera_recurso'
       d. emitir evento `ps_criada` na fila local com snapshot
            do serviço (materiais, POP inline se local, pessoal)
  4. quando PS for autorizada (no núcleo, no próximo sync):
       gera OS, envia para celular do executor
```

### Snapshot embarcado

PS local criada a partir de **serviço local** carrega `servico_snapshot` JSON completo:

```json
{
  "servico_snapshot": {
    "codigo": "LIMP_LOCAL_AC_PAIOL3",
    "nome": "Limpeza AC paiol 3 (caso especial)",
    "versao": 1,
    "escopo": "local",
    "materiais": [...],
    "ferramentas": [...],
    "pessoal": [...],
    "pop_inline_md": "..."
  }
}
```

Núcleo armazena o snapshot. Não cria entrada em `catalogo_servicos` (escopo local fica no device).

---

## 13. Qualificações de pessoal

Cada serviço declara `pessoal_necessario` em qualificações. Cada usuário tem qualificações com validade.

```
qualificacoes_catalogo        (núcleo)
  ├─ codigo: 'tec_refrig' | 'eletricista_nr10' | 'operador_munk' | ...
  ├─ nome, descricao
  └─ requer_validade: bool

usuario_qualificacoes
  ├─ usuario_id, qualificacao_codigo
  ├─ obtida_em, valida_ate (nullable se requer_validade=false)
  ├─ doc_id → certificado em documentos
  └─ status: 'valida' | 'vencida' | 'suspensa'
```

### Regras

- OS só pode ser **alocada** a usuário com qualificação requerida válida.
- Vencimento próximo (30/60/90 dias) gera alerta no Hub.
- Seed inicial vem de `pmoc.refs/cmasm10_competencias.csv`.

---

## 14. Condicionais — DSL local

Expressão booleana avaliada pelo PMOC com contexto disponível no device:

| Variável | Origem |
|---|---|
| `clima.chuva`, `clima.temp` | API meteo (cache local) ou input manual |
| `energia.ativa` | input manual no PMOC ou sensor |
| `ativo.disponivel` | status do ativo (não em outra OS) |
| `data.hora`, `data.dia_semana` | clock local |
| `estoque[<id>].qtd` | catálogo local |

Operadores: `==  !=  <  >  <=  >=  &&  ||  !`. Sem efeitos colaterais. Avaliação pura.

Falha de condicional registra `motivo` na fila de pendentes e **não** bloqueia o plano — só adia a geração de PS.

---

## 15. Atualizações no cadastro de Ativos

Campos novos exigidos pelo motor (aditivos):

| Campo | Tipo | Função |
|---|---|---|
| `criticidade` | enum `admin\|operacional\|critico_24x7` | Resolve frequência diferenciada por nível |
| `responsavel_pmoc` | string (categoria do PMOC) | Quem é dono operacional. Evita 2 categorias avaliarem o mesmo plano |
| `janela_default` | JSON | Janela permitida do ativo (override pelo plano) |

---

## 16. Roadmap de regras (não implementado)

- **RFID/QR no Estoque** — cada movimento associado a leitura de tag. Saída automática ao escanear na requisição.
- **Telemetria IoT** — equipamentos com sensor (ESP32) reportam horímetro/temperatura via MQTT → bridge → `POST /api/sync/push`.
- **Assinatura digital de OS** — gestor confirma "pronto → concluída" com gov.br.
- **CADBEM bridge** — exportação periódica de bens permanentes para conferência.
- **Promoção de serviço local → central** com fluxo de aprovação.
- **Simulação de plano** antes de ativar (mostra carga prevista).
- **Substituição de executor** com motivo registrado e re-aviso no celular.
