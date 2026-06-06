---
applyTo: "xPredial/**"
description: >
  Guia de correção e melhoria do módulo xPredial. Use quando corrigir bugs,
  adicionar features ou melhorar páginas do módulo de gestão predial.
  Cobre: locais, edifícios, ambientes, inspeções, laudos prediais,
  pedidos de serviço, ordens de serviço, estilo xCMASM.
---

# xPredial — Correções e Melhorias

## 1. Correções Obrigatórias (aplicar em toda edição)

### predial.js — navHTML()
A função `navHTML()` deve incluir TODAS as páginas do módulo:

```js
const pages = [
  { id: 'index',               label: 'Dashboard',    href: 'index.html' },
  { id: 'locais',              label: 'Locais',        href: 'locais.html' },
  { id: 'planejamento',        label: 'Planejamento',  href: 'planejamento.html' },
  { id: 'inspecoes',           label: 'Inspeções',     href: 'inspecoes.html' },
  { id: 'aprovacoes',          label: 'Aprovações',    href: 'aprovacoes.html' },
  { id: 'laudos',              label: 'Laudos',        href: 'laudos.html' },
  { id: 'normas',              label: 'Normas',        href: 'normas.html' },
  { id: 'historico-relatorios',label: 'Histórico',     href: 'historico-relatorios.html' },
];
```

### Todas as páginas HTML — Google Fonts no `<head>`
Todo `<head>` deve conter:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

### inspecoes.html — Salvar Análise Técnica
Verificar estado atual ANTES de tentar transição:
```js
async function salvarAnalise() {
  const insp = await predialAPI.getInspecao(currentId);
  // Só transicionar se ainda estiver em 'planejada'
  if (insp.status === 'planejada') {
    await predialAPI.transition(currentId, { para_status: 'em_execucao', ... });
  }
  // Se já em_execucao, apenas salvar sem transicionar
  await salvarItensMarcados();
}
```

### inspecoes.html — Filtrar inspeções acionáveis
Ao listar inspeções na página de execução, filtrar apenas `planejada` e `em_execucao`:
```js
// Buscar planejadas e em execução
const [planejadas, emExec] = await Promise.all([
  predialAPI.listInspecoes({ status: 'planejada' }),
  predialAPI.listInspecoes({ status: 'em_execucao' }),
]);
const lista = [...planejadas, ...emExec];
```

### predial.js — badge() consistência
O backend usa `"critico"` (sem 'a'). A função `badge()` deve mapear apenas `"critico"`, remover alias `"critica"`:
```js
critico: 'crit',  // não 'critica'
```

### aprovacoes.html — toast type
Substituir `toast(msg, 'warn')` por `toast(msg, 'error')` — `'warn'` não é tipo válido.

## 2. Melhorias de Modelo — Locais, Edifícios, Ambientes

### Tipos de local expandidos
O campo `tipo` em `locais` deve suportar:
- `edificio` — prédio físico com múltiplos ambientes
- `bloco` — conjunto de edificações
- `sala` / `laboratorio` / `escritorio` — ambientes internos
- `almoxarifado` / `paiol` — depósitos/armazéns
- `cais` / `atracadouro` — estruturas náuticas
- `area_externa` / `patio` / `campo` — áreas descobertas
- `instalacao` — instalação técnica (casa de bombas, subestação, etc.)

### Página locais.html — Detalhes do local
O botão "Detalhes" deve abrir um painel lateral com:
- Informações completas do local (NEO, código, área, restrição, área m²)
- Lista de inspeções vinculadas (últimas 5, com status badge)
- Link para "Nova inspeção neste local" (vai para planejamento.html?local_id=X)
- Laudos vinculados ao local

### Backend — Endpoint GET /api/v1/locais/{id}
Adicionar endpoint para buscar um local específico com dados completos:
```python
@app.get("/api/v1/locais/{local_id}")
async def get_local(local_id: int):
    local = await db.fetch_one("SELECT * FROM locais WHERE id = ?", [local_id])
    inspecoes = await db.fetch_all(
        "SELECT id, titulo, status, data_planejada FROM inspecoes WHERE local_id = ? ORDER BY created_at DESC LIMIT 5",
        [local_id]
    )
    laudos = await db.fetch_all("SELECT * FROM laudos WHERE local_id = ?", [local_id])
    return {**local, "inspecoes_recentes": inspecoes, "laudos": laudos}
```

## 3. Melhorias de Inspeções e Laudos

### inspecoes.html — Botão Histórico
O `#historicoBtn` precisa de event listener:
```js
document.getElementById('historicoBtn').addEventListener('click', () => {
  window.location.href = `historico-relatorios.html?local_id=${currentLocalId}`;
});
```

### Workflow de inspeção completo
Cada inspeção deve permitir ao usuário ver claramente o próximo passo:

| Status atual | Próxima ação | Botão |
|---|---|---|
| `planejada` | Iniciar execução | "Iniciar Inspeção" |
| `em_execucao` | Enviar para aprovação | "Concluir e Enviar" |
| `aguardando_aprovacao` | (só aprovadores podem agir) | — |
| `aprovada` | Concluir / Gerar laudo | "Concluir" |
| `reprovada` | Retornar à execução | "Retomar Execução" |

### laudos.html — Geração a partir de inspeção
Ao criar um laudo, permitir vincular uma inspeção aprovada:
```js
// Ao selecionar inspecao_id, preencher título automaticamente
// "Laudo - <nome do local> - <data>"
```

## 4. Pedidos de Serviço e Ordens de Serviço

### Fluxo de integração xPredial → xServicos
Quando uma inspeção detecta itens `critico` ou `atencao`, deve permitir:
1. **Gerar PS** (Pedido de Serviço) → cria registro no módulo xServicos
2. O `servico_id` da inspeção armazena a referência ao PS/OS
3. Na conclusão da OS, o `servico_id` permite rastrear o desfecho

### inspecoes.html — Painel de Itens Críticos
Após salvar itens do checklist, exibir resumo de não conformidades:
- Contar itens `critico` e `atencao`
- Se houver itens críticos: exibir botão "Gerar Pedido de Serviço"
- O botão deve abrir modal com: descrição pré-preenchida dos itens críticos, prioridade, local

### Backend — Endpoint para resumo de não conformidades
```python
@app.get("/api/v1/inspecoes/{id}/nao-conformidades")
async def get_nao_conformidades(id: int):
    itens = await db.fetch_all(
        "SELECT * FROM inspecao_itens WHERE inspecao_id = ? AND condicao != 'ok'",
        [id]
    )
    return {"total": len(itens), "criticos": [...], "atencao": [...]}
```

## 5. Estilo — Compatibilidade xCMASM

### CSS tokens obrigatórios (de xpredial-core.css)
Nunca hardcodar cores. Usar sempre variáveis:
```css
color: var(--acc);        /* ciano para destaques */
background: var(--panel); /* fundo de cards/painéis */
border-color: var(--acc); /* bordas ativas */
color: var(--red);        /* erros/crítico */
color: var(--amber);      /* atenção/warning */
color: var(--green);      /* ok/sucesso */
```

### Badges de status — classes corretas
```js
// Em predial.js badge()
const map = {
  planejada: 'info',
  em_execucao: 'warn',
  aguardando_aprovacao: 'warn',
  aprovada: 'ok',
  concluida: 'ok',
  reprovada: 'crit',
  ok: 'ok',
  atencao: 'warn',
  critico: 'crit',
};
```

### Layout de páginas
- Header sticky com nav horizontal (não sidebar)
- Cards com classe `.card` e `border-left: 3px solid var(--acc)`
- Tabelas com classe `.tw` dentro de `.fg`
- KPIs com `.kpi-grid` > `.kpi`
- Botões: `.btn.btn-p` (primário ciano), `.btn.btn-s` (secundário), `.btn.btn-d` (danger vermelho)
- Modais: overlay `.moverlay` > `.modal`

## 6. Novas Páginas a Criar

### `frontend/ambientes.html` — Visão por edificação
Página para navegar por edificação e ver todos os seus ambientes (sub-locais):
- Seletor de edifício no topo
- Cards para cada ambiente com: nome, tipo, status da última inspeção, badge de condição
- Link para "Planejar inspeção" de cada ambiente

### `frontend/servicos.html` — Acompanhamento de OS
Página para visualizar OS/PS vinculados ao módulo predial:
- Tabela de inspeções com `servico_id` preenchido
- Status da OS derivado do campo `servico_id` (se houver API no xServicos)
- Link de navegação para o módulo xServicos

## 7. Backend — Melhorias

### PUT /api/v1/locais/{id}
Adicionar endpoint de atualização de local (hoje só existe POST):
```python
@app.put("/api/v1/locais/{local_id}")
async def update_local(local_id: int, data: LocalUpdate):
    # LocalUpdate com campos opcionais
    ...
```

### GET /api/v1/inspecoes com múltiplos status
Suportar filtro por múltiplos status: `?status=planejada,em_execucao`

### Conclusão automática de OS
Quando `inspecao.status → concluida` e `servico_id` preenchido, registrar no `workflow_events` com comentário indicando a OS concluída.
