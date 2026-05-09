# xCMASM — Regras de Negócio e Fluxos do Sistema

Documento de referência para os fluxos, relações entre entidades e regras que governam o comportamento do sistema. Mantido junto ao código — atualizar quando os fluxos mudarem.

---

## 1. Entidades Principais e Relações

```
Ativos ──────────────────────────────────────────────────────┐
  │  cada ativo tem tipo → tipo define categoria,            │
  │  plano de manutenção e materiais necessários             │
  │                                                           │
  ├──► Manutenção (PMOC por tipo de ativo)                   │
  │      │  gatilho: uso_atual ≥ proximo_uso                 │
  │      │  ao disparar → gera OS preventiva + NEC de mat.  │
  │      └──► Materiais (itens do plano → Estoque)           │
  │                                                           │
  ├──► Transportes (uso operacional de viaturas/emb.)        │
  │      agendamento → log de viagem → incrementa uso_atual  │
  │      ao concluir → verifica intervalo de manutenção      │
  │                                                           │
  └──► Ordens de Serviço / Pedidos de Serviço (PS)           │
         PS aberto → autorizado → em execução → concluído    │
         pode ter: etapas, NECs, materiais, custo             │
         ao concluir → movimenta Estoque (saída de materiais) │
                    → atualiza uso_atual do ativo             │

Estoque ─────────────────────────────────────────────────────┘
  movimentações: entrada / saída / ajuste
  saída automática ao concluir OS com materiais
  alerta quando qtd_atual < qtd_minima
```

---

## 2. Ativos

### Categorias e tipos reais

| Categoria | Tipos | Unidade de uso |
|-----------|-------|----------------|
| `maquinas_corte` | FS220, GAR, MS650, TS114, SOL | horas (h) |
| `viaturas_pessoal` | VTR_PICKUP, VTR_SEDAN | km |
| `viaturas_carga` | VTR_CARGA, VTR_GUINDASTE | km |
| `embarcacoes` | EMB_LANCHA, EMB_BOTE | horas (h) |
| `climatizacao` | AC_SPLIT, AC_CENTRAL | meses |
| `eletrica` | GERADOR | horas (h) |
| `predial` | — (livre) | meses |
| `outros` | — (livre) | h / km / meses |

> `VTR_PICKUP` é subtipo de `viaturas_pessoal`. A S-10 (pessoal) e o MUNK (carga) são tipos distintos, não o mesmo campo `tipo`.

### Subcategorias de viaturas (campo `subtipo`)

- `vtr_int` — Viaturas internas (Ilha do Engenho): serviços, transporte de material e pessoal dentro do CMASM
- `vtr_ext` — Viaturas externas (Ilha das Flores): transporte a destinos fora do CMASM (DCAM, ASD, BFNIF…)
- `emb_rot` — Embarcações de rotina (ETPM Fátima, tipo translado diário Ilha das Flores)
- `emb_pat` — Embarcações de patrulha / sobreaviso (Lancha Natal, Sargento Freitas)

### Frota base cadastrada

**Máquinas de corte**: FS220 ×5, GAR ×3, MS650 ×1, TS114 ×2, SOL ×1  
**Viaturas**: MUNK (KPJ-8385), S-10 (LRZ-5099), Ambulância, Doblô 1.4, Caminhão Constellation, XCMG (guindaste)  
**Embarcações**: ETPM Fátima (CMASM-08), Lancha Natal (CMASM-05), Sargento Freitas (CMASM-10)

### Regras

- `ativo = 1` → em serviço; `ativo = 0` → arquivado (nunca deletar)
- `uso_atual` é incrementado por: conclusão de OS de transporte, registro manual, ou integração com módulo de uso
- O campo `tipo` determina qual plano de manutenção se aplica
- Ativos do sistema hidráulico e ETE vêm de `aguada-web` (integração futura)

---

## 3. Planos de Manutenção Preventiva

Cada **tipo de ativo** tem um plano com etapas definidas por intervalo de uso:

```
Plano (por tipo)
  └─ Etapa
       ├─ intervalo: a cada N horas / km / meses
       ├─ nome: descrição do serviço (ex: "Troca de óleo + filtro")
       └─ materiais: lista de itens do Estoque necessários
```

### Exemplos reais

| Tipo | Etapa | Intervalo | Materiais |
|------|-------|-----------|-----------|
| GAR (cortador) | Troca de óleo 4T | 50h | Óleo SAE 30 1L |
| SOL (trator) | Troca óleo + filtro diesel | 50h | Óleo 15W-40, Filtro óleo Solis |
| VTR_PICKUP | Troca de óleo + filtro | 5.000km | Óleo 5W-30 sint. 4L, Filtro de óleo |
| VTR_PICKUP | Inspeção de freios | 10.000km | Pastilhas de freio |
| EMB_LANCHA | Troca de óleo motor de popa | 50h | Óleo náutico 2T, Filtro de óleo |
| GERADOR | Troca óleo + filtro | 250h | Óleo 15W-40, Filtro óleo gerador |
| AC_SPLIT | Limpeza de filtros | 1 mês | — |
| AC_SPLIT | Verificação de gás | 12 meses | Gás R-410A (se necessário) |

### Disparo de manutenção

1. Sistema compara `uso_atual` do ativo com `proximo_uso` de cada etapa do plano
2. Quando `uso_atual ≥ proximo_uso` → gera alerta de manutenção vencida
3. Operador confirma → sistema abre OS de manutenção automaticamente
4. OS de manutenção herda os materiais da etapa → reserva no Estoque
5. Ao concluir OS → `proximo_uso = uso_atual + intervalo`; Estoque debitado

---

## 4. Ordens de Serviço (OS)

### Tipos de OS

| Tipo | Origem | Quem abre |
|------|--------|-----------|
| `preventiva` | Plano de manutenção atingido | Sistema automático |
| `corretiva` | Defeito / ocorrência reportada | Qualquer usuário |
| `inspecao` | Checklist periódico do ativo | Responsável |
| `transporte` | Agendamento de viagem | Módulo Transportes |
| `administrativa` | Tarefas admin, relatórios, processos licitatórios | Gestor / admin |
| `instalacao` | Instalação de novos equipamentos ou sistemas | Responsável técnico |
| `periodica` | Serviço recorrente com frequência fixa (ex: varrição diária — Quarto D'Alva) | Sistema / admin |

### Ciclo de vida (status)

```
PS (Pedido de Serviço) aberto
  │ autorização por gestor competente + NECs satisfeitas
  ▼
Autorizada
  │ responsável designado, recursos confirmados
  ▼
Iniciada  ──────────────────────────────► Espera
  │ necessidades materiais confirmadas,   (aguardando recurso / autorização /
  │ executor designado                     material pendente)
  ▼                                         │
Em Execução ◄──────────────────────────────┘
  │ executor registra andamento das etapas
  ▼
Pronto (aguardando aprovação do gestor)
  │ gestor valida o serviço executado
  ▼
Concluída ─────────────────────► Estoque debitado + uso_atual do ativo atualizado

Em qualquer estado anterior → Cancelada (motivo obrigatório)
```

Valores de status no banco: `aberta | autorizada | iniciada | em_execucao | espera | pronto | concluida | cancelada`

### PS, NECs e hierarquia de OS

**PS (Pedido de Serviço)** é a entrada de qualquer demanda. Pode gerar uma ou várias OS filhas.

| Entidade | Descrição |
|----------|-----------|
| PS | Pedido de Serviço — nível de solicitação (ex: "Reforma da Sala 201") |
| OS | Ordem de Serviço — unidade de execução (ex: "Pintura da Sala 201") |
| OS filha | OS gerada a partir de um PS ou de outra OS pai |

> Um PS de "Reforma da Sala 201" pode gerar OS filhas de pintura, elétrica, carpintaria — cada uma com responsável, materiais e status próprios.

**NEC (Necessidade)** — requisito que deve ser satisfeito antes de autorizar/iniciar uma OS:

| Tipo NEC | Descrição |
|----------|-----------|
| `nec_material` | Item de estoque necessário (ex: 5L de tinta époxy) |
| `nec_ativo` | Equipamento ou viatura necessária (ex: MUNK, embarcação) |
| `nec_servico` | Serviço externo ou de outro setor (ex: terceirizado, xPredial) |
| `nec_local` | Reserva de espaço (sala, cais, área externa) |

Enquanto NECs não satisfeitas → OS permanece em status `espera`.

### Campos obrigatórios

- `titulo`, `tipo`, `prioridade` (baixa / media / alta / urgente)
- `ativo_id` — qual ativo está sendo atendido (quando aplicável)
- `responsavel_id` — quem executa
- `modulo_origem` — `manutencao` | `transportes` | `manual` | `predial`

### Materiais em OS

- Lista de itens com `material_id` (ref. Estoque), `quantidade`, `unidade`
- Status: `reservado` (OS aberta) → `utilizado` (OS concluída) → `devolvido` (cancelada)
- Ao concluir: `estoque.movimentos` recebe saída automática com `os_id` como referência

---

## 5. Transportes

### Entidades

```
Viagem
  ├─ ativo_id → qual VTR ou EMB
  ├─ tipo_uso: rotina | missao | sobreaviso | manutencao
  ├─ data_saida, hora_saida, hora_chegada (prevista e real)
  ├─ destino: texto + lista de destinos frequentes
  ├─ missao: descrição
  ├─ motorista_id → usuario
  ├─ responsavel_id → usuario (quem autorizou)
  ├─ km_saida, km_chegada → diferença incrementa uso_atual do ativo
  └─ status: agendada → em_andamento → concluida | cancelada
```

### Destinos frequentes (VTR EXT)

DCAM, ASD, BFNIF, Ilha das Flores (translado pessoal), Hospital Naval Marcílio Dias, Comandos Navais

### Regras

- VTR interna: não registra km de destino externo; destino é sempre "CMASM interno"
- VTR externa: exige destino, responsável (oficial autorizador) e previsão de retorno
- Embarcações de rotina: viagens diárias recorrentes com horários fixos (ETPM Fátima: ~12 saídas/dia)
- Embarcações de patrulha: modo sobreaviso com período (ex: 18h às 06h)
- Ao concluir viagem: `uso_atual` do ativo incrementa por `(km_chegada - km_saida)` ou horas
- Se ativo atingir intervalo de manutenção durante viagem → alerta ao concluir

### Funcionalidades de suporte

**Quadro de condição de frota**: painel resumo do estado de cada viatura/embarcação (disponível, em uso, em manutenção, sobreaviso).

**Formulários oficiais**: Papeleta 6 de Serviço (formulário naval padrão para registro diário de uso de viaturas/embarcações) — gerada ao concluir viagem com todos os dados preenchidos.

**Calculadores operacionais**:
- Consumo de combustível estimado por km/h percorridos
- Estimativa de vida útil de componentes: pneus, filtros, óleo, baterias
- Planejamento de uso: intervalo hora / dia / semana
- Estimativa de custo de operação e manutenção

**Relatórios periódicos**: diário, semanal e mensal — por viatura, motorista e destino.

---

## 6. Estoque

### Tipos de material

| Tipo | Exemplos | Saída por |
|------|----------|-----------|
| `consumivel` | Óleo, filtros, graxas, tintas | OS de manutenção |
| `sobressalente` | Impeller, correia dentada, sensor NTC | OS de manutenção |
| `epi` | Luvas, óculos, protetor auricular | Requisição direta |
| `material_escritorio` | — | Requisição direta |
| `nautico` | Anodo de zinco, tinta anti-incrustante | OS de manutenção naval |

### Fluxo de movimentação

```
Entrada: nota fiscal / transferência / devolução de OS
Saída:   OS concluída (automático) | requisição direta (manual)
Ajuste:  inventário / correção
```

### Alerta de nível mínimo

- Quando `qtd_atual < qtd_minima` → badge "Baixo" na tela de Estoque
- Gera item em "Necessidades" (pedido de material a ser gerado)

### Modelo distribuído de estoque

O estoque do ERP é distribuído: cada seção gerencia seu próprio mínimo, e aquisições podem ser centralizadas ou setorizadas.

| Conta / Seção | Responsável | Exemplos de material |
|---------------|-------------|---------------------|
| CMASM-13 (Manutenção) | Div. de Manutenção Especializada | Óleos, filtros, solda, tinta, madeira, parafusos, material elétrico |
| CMASM-11 (Prefeitura) | Div. de Prefeitura | Material de limpeza, EPI, ferramentas gerais |
| CMASM-20 (Armas) | Dep. de Armas | Sobressalentes específicos de armamento |

**CADBEM**: sistema patrimonial próprio da Marinha para bens permanentes (sem API disponível). Integração futura planejada via exportação CSV. O Estoque do ERP cobre materiais de consumo e sobressalentes operacionais — **não substitui o CADBEM**.

---

## 7. Módulo Manutenção (visão geral)

A tela de Manutenção é o painel central de controle preventivo. Não executa OS — gera e monitora.

```
Manutenção
  ├─ Por tipo de ativo (tab ou seção por categoria)
  ├─ Lista de ativos com status do próximo serviço
  │    verde = ok | amarelo = próximo (< 20% do intervalo restante) | vermelho = vencido
  ├─ Detalhe do ativo: histórico de OS de manutenção, horímetro/km atual
  ├─ Criar OS manual de manutenção
  └─ Configurar plano de um ativo (sobrescrever intervalos padrão do tipo)
```

### Atualização de uso

Fontes que incrementam `uso_atual`:
1. **Transportes** → ao concluir viagem (km ou horas)
2. **Manutenção** → registro manual de horímetro pelo operador
3. **Grama** → ao registrar operação de corte (horas de uso da máquina)
4. **Futuro** → integração IoT (aguada-web, xEletrica) via API

---

## 8. Módulo xGrama (Controle Vegetal) — integrado no xCore

- Máquinas de corte em xGrama **são** ativos da categoria `maquinas_corte`
- Ao registrar operação de corte: `uso_atual` do ativo é incrementado pelas horas da operação
- Manutenção das máquinas segue o plano preventivo do tipo (FS220, GAR, etc.)
- OS geradas pelo xGrama têm `modulo_origem = 'grama'`

---

## 9. Satélites (fora do xCore)

| Satélite | Porta | Dados que usa do xCore |
|----------|-------|------------------------|
| xPredial | 8002 | `GET /api/usuarios` (lista de executantes) |
| xPaiol | 8003 | `GET /api/usuarios`, futura integração de ativos |
| xSegurança | 8000 | Independente (próprio PG + Redis) |
| aguada-web | 8001 | Independente; futuramente enviará dados de ativos hidráulicos via API |

---

## 10. Template de Módulo de Ativos (`ativo-template.html`)

### Propósito

`xCore/ativo-template.html` é o ponto de partida para criar módulos autônomos de gestão de ativos com manutenção preventiva e estoque, sem backend — tudo em localStorage. Use para: `ar-condicionado.html`, `eletrica.html`, `embarcacoes-manut.html`, etc.

### Passos para criar um novo módulo

1. **Copie** o arquivo: `cp xCore/ativo-template.html xCore/nome-modulo.html`
2. **`<title>`** → troque `[MÓDULO]` pelo nome real (ex: `CMASM · Ar-Condicionado`)
3. **`.sb-sub`** no HTML → troque `[Módulo] · Manutenção` (ex: `Climatização · Manutenção`)
4. **`TIPOS`** → preencha com os tipos de equipamento. Estrutura obrigatória:
   ```js
   CHAVE: {
     nome: 'Nome do tipo',
     cor:  '#hex',           // cor do ponto de status na sidebar
     emoji: '❄️',
     plano: [
       { id: 'p01', iv: 500,  n: 'Nome da manutenção', its: ['Material A', 'Material B'] },
       // iv = intervalo em horas entre manutenções
     ]
   }
   ```
5. **`UNIDADES_DEFAULT`** → lista de equipamentos do inventário inicial:
   ```js
   { id:'u01', tipo:'CHAVE_TIPOS', nome:'AC-Sala01', pat:'12345', obs:'Sala de reuniões', ativo:true }
   ```
6. **`PECAS_DEFAULT`** → peças e insumos do módulo:
   ```js
   { id:'pe01', d:'Spray bactericida AC 300ml', un:'UN', cat:'quimico', pr:32.00}
   ```
7. **`SK` e `SE`** → chaves únicas de localStorage (evitar colisão entre módulos):
   ```js
   const SK='arcond_state', SE='arcond_est';  // prefixo único por módulo
   ```
8. **Checklists pré-uso** → busque os dois blocos `[Item de verificação N]` no HTML e substitua pelas verificações reais do equipamento
9. **Categorias de peças** no modal `m-peca` → ajuste as `<option>` ao vocabulário do módulo
10. **Link no portal** → adicione entrada em `cmasm-erp.html` na sidebar:
    ```html
    <a class="ni" href="/nome-modulo.html"><span class="ni-ico">❄️</span>Ar-Condicionado</a>
    ```

### Estrutura de dados (localStorage)

| Chave | Conteúdo |
|-------|----------|
| `SK` (`*_state`) | `{ unidades: [...], hist: { uid: { hor, regs, manut, ulm } } }` |
| `SE` (`*_est`) | `{ pe_id: { qt, movs: [{dt, delta, motivo, obs}] } }` |

### Integração com xCore (opcional, futura)

Quando o módulo precisar criar OS ao registrar manutenção, adicionar ao `regManut()`:
```js
await fetch('http://localhost:8010/api/os', {
  method: 'POST',
  headers: {'Content-Type':'application/json'},
  body: JSON.stringify({
    titulo: `Manutenção ${u.nome} – ${nomes.join(', ')}`,
    tipo: 'preventiva',
    modulo_origem: 'nome-modulo',  // ex: 'arcond', 'eletrica'
    ativo_id: null,                // se o ativo estiver no xCore
    responsavel: resp
  })
});
```

### Módulos existentes baseados nesse padrão

| Arquivo | Módulo | `SK` / `SE` |
|---------|--------|------------|
| `maq-corte.html` | Máquinas de corte | `cmasm_v2_state` / `cmasm_v2_est` |
| `ativo-template.html` | Template | `MODULE_state` / `MODULE_est` |

---

## 11. Chaves de Integração entre Módulos

| De | Para | Como |
|----|------|------|
| Manutenção | Serviços | `POST /api/os` com `tipo=preventiva`, `modulo_origem=manutencao`, `ativo_id` |
| Transportes | Serviços | `POST /api/os` com `tipo=transporte`, `modulo_origem=transportes`, `ativo_id` |
| OS concluída | Estoque | `POST /api/estoque/{id}/movimentos` com `tipo=saida`, `os_id` |
| OS concluída | Ativos | `PUT /api/ativos/{id}` atualizando `uso_atual` |
| xGrama / operação | Ativos | `PUT /api/ativos/{id}` incrementando `uso_atual` com horas da operação |
| xPredial | Usuários | `GET /api/usuarios` via `XCORE_URL` |
