# SKILL: Padrão Digital de Governo (DSGOV)

## Quando usar esta skill

Ativar **sempre** que o usuário pedir para criar artefatos HTML, páginas web, dashboards,
documentos ou sistemas que devem seguir o **Padrão Digital de Governo Brasileiro** (DSGOV /
govbr-ds). Palavras-chave: "padrão gov.br", "design system governo", "govbr", "identidade
visual governo federal", "componente br-", "visual govbr".

---

## 1. O que é o DSGOV

O **Padrão Digital de Governo** é o Design System oficial do Governo Federal Brasileiro,
desenvolvido pelo SERPRO e mantido pela Secretaria de Governo Digital (SGD/MGI). É baseado
em Web Components agnósticos (HTML puro, Angular, React, Vue). Versão estável atual: **3.7.0**.

- Site oficial: https://www.gov.br/ds/
- NPM: `@govbr-ds/core`
- GitLab: https://gitlab.com/govbr-ds/bibliotecas/javascript/govbr-ds-core
- Licença: MIT

---

## 2. CDN — Template base para artefatos HTML

> ⚠️ IMPORTANTE: O CDN do SERPRO (`cdngovbr-ds.estaleiro.serpro.gov.br`) pode falhar em
> ambientes sandboxed (Claude artifacts). Use sempre a versão do jsDelivr como fallback.

```html
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="X-UA-Compatible" content="ie=edge" />
  <title>Sistema GOV.BR</title>

  <!-- Fonte Rawline (SERPRO CDN) -->
  <link rel="stylesheet"
    href="https://cdngovbr-ds.estaleiro.serpro.gov.br/design-system/fonts/rawline/css/rawline.css" />

  <!-- Fonte Raleway (Google Fonts — fallback tipográfico) -->
  <link rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700;800;900&display=swap" />

  <!-- DSGOV Core CSS (jsDelivr — funciona em ambientes sandboxed) -->
  <link rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/@govbr-ds/core@3.7.0/dist/core.min.css" />

  <!-- Font Awesome 5 (ícones obrigatórios no DSGOV) -->
  <link rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.11.2/css/all.min.css" />
</head>
<body>

  <!-- === CONTEÚDO AQUI === -->

  <!-- DSGOV Core JS (inicializa componentes interativos) -->
  <script src="https://cdn.jsdelivr.net/npm/@govbr-ds/core@3.7.0/dist/core.min.js"></script>
</body>
</html>
```

---

## 3. Paleta de Cores Oficial

| Token semântico          | Hex       | Uso principal                        |
|--------------------------|-----------|--------------------------------------|
| `--color-primary`        | `#1351b4` | Azul primário — cor institucional    |
| `--color-primary-dark`   | `#0c326f` | Azul escuro — hover, énfase          |
| `--color-primary-light`  | `#2670e8` | Azul claro — links, interativos      |
| `--color-secondary`      | `#fff`    | Branco — fundo padrão                |
| `--color-highlight`      | `#ffcd07` | Amarelo — destaque, avisos           |
| `--color-success`        | `#168821` | Verde — sucesso, confirmação         |
| `--color-warning`        | `#ffcd07` | Amarelo — alerta                     |
| `--color-danger`         | `#e52207` | Vermelho — erro, perigo              |
| `--color-info`           | `#155bcb` | Azul info — informativo              |
| `--gray-2`               | `#f8f8f8` | Fundo suave                          |
| `--gray-5`               | `#cccccc` | Bordas, divisores                    |
| `--gray-7`               | `#888888` | Texto secundário                     |
| `--gray-9`               | `#333333` | Texto principal                      |

### CSS Variables mínimas para artefatos sem o CDN completo

```css
:root {
  /* Cores */
  --color-primary:       #1351b4;
  --color-primary-dark:  #0c326f;
  --color-primary-light: #2670e8;
  --color-highlight:     #ffcd07;
  --color-success:       #168821;
  --color-danger:        #e52207;
  --color-warning:       #fa7d1e;
  --color-info:          #155bcb;

  /* Neutros */
  --pure-0:   #000000;
  --pure-100: #ffffff;
  --gray-2:   #f8f8f8;
  --gray-5:   #cccccc;
  --gray-7:   #888888;
  --gray-9:   #333333;

  /* Tipografia */
  --font-family-base:    'Rawline', 'Raleway', sans-serif;
  --font-size-base:      14px;
  --font-size-h1:        2.5rem;
  --font-size-h2:        2rem;
  --font-size-h3:        1.75rem;
  --font-weight-regular: 400;
  --font-weight-medium:  500;
  --font-weight-bold:    700;

  /* Espaçamento (escala de 8px) */
  --spacing-scale-base:  8px;
  --spacing-scale-2x:    16px;
  --spacing-scale-3x:    24px;
  --spacing-scale-4x:    32px;
  --spacing-scale-5x:    40px;
  --spacing-scale-6x:    48px;

  /* Bordas */
  --border-radius-small: 4px;
  --border-radius-large: 8px;
  --border-width:        1px;
  --border-color:        var(--gray-5);
}
```

---

## 4. Tipografia

- **Rawline** — fonte primária, desenvolvida para o governo (CDN SERPRO)
- **Raleway** — fonte secundária / fallback (Google Fonts)
- Escala: 12 / 14 / 16 / 20 / 24 / 32 / 40 / 48 / 56px
- `font-size: 14px` no body é o padrão do sistema

---

## 5. Grid e Layout

O DSGOV usa grid de **12 colunas** com container fixo por breakpoint:

| Breakpoint | Largura min | Container max |
|------------|-------------|---------------|
| `sm`       | 576px       | 540px         |
| `md`       | 768px       | 720px         |
| `lg`       | 992px       | 960px         |
| `xl`       | 1280px      | 1200px         |

Classes de grid: `.container`, `.container-lg`, `.row`, `.col-*`, `.col-sm-*`, `.col-md-*`

---

## 6. Componentes — Classes e Exemplos

### 6.1 Botões (`br-button`)

```html
<!-- Primário (ação principal) -->
<button class="br-button primary" type="button">Enviar</button>

<!-- Secundário -->
<button class="br-button secondary" type="button">Cancelar</button>

<!-- Terciário (link) -->
<button class="br-button tertiary" type="button">Voltar</button>

<!-- Block (largura total) -->
<button class="br-button primary block" type="button">Confirmar</button>

<!-- Com ícone -->
<button class="br-button primary" type="button">
  <i class="fas fa-check" aria-hidden="true"></i> Confirmar
</button>

<!-- Circular (apenas ícone) -->
<button class="br-button circle" type="button" aria-label="Fechar">
  <i class="fas fa-times" aria-hidden="true"></i>
</button>

<!-- Tamanhos: small, medium (padrão), large -->
<button class="br-button primary small" type="button">Pequeno</button>
<button class="br-button primary large" type="button">Grande</button>
```

### 6.2 Header (`br-header`)

```html
<header class="br-header compact" id="header">
  <div class="container-lg">
    <div class="header-top">
      <div class="header-logo">
        <img src="https://www.gov.br/ds/assets/img/govbr-logo.png" alt="Governo Federal" />
        <span class="br-divider vertical mx-half mx-sm-1"></span>
        <div class="header-sign">Nome do Sistema</div>
      </div>
      <div class="header-actions">
        <!-- Ações do header aqui -->
      </div>
    </div>
  </div>
</header>
```

### 6.3 Cards (`br-card`)

```html
<div class="br-card hover">
  <div class="card-header">
    <span>Título do Card</span>
  </div>
  <div class="card-content">
    <p>Conteúdo do card aqui.</p>
  </div>
  <div class="card-footer">
    <button class="br-button primary small" type="button">Ação</button>
  </div>
</div>
```

### 6.4 Inputs e Formulários (`br-input`, `br-select`, `br-textarea`)

```html
<!-- Input texto -->
<div class="br-input">
  <label for="nome">Nome completo</label>
  <input id="nome" type="text" placeholder="Digite seu nome" />
</div>

<!-- Com mensagem de erro -->
<div class="br-input danger">
  <label for="cpf">CPF</label>
  <input id="cpf" type="text" placeholder="000.000.000-00" />
  <p class="feedback danger" role="alert">CPF inválido</p>
</div>

<!-- Select -->
<div class="br-select">
  <label>Estado</label>
  <select>
    <option value="">Selecione</option>
    <option value="RJ">Rio de Janeiro</option>
  </select>
</div>

<!-- Textarea -->
<div class="br-textarea">
  <label for="obs">Observações</label>
  <textarea id="obs" rows="4" placeholder="Digite aqui..."></textarea>
</div>
```

### 6.5 Tabela (`br-table`)

```html
<div class="br-table">
  <table>
    <thead>
      <tr>
        <th scope="col">Coluna A</th>
        <th scope="col">Coluna B</th>
        <th scope="col">Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Valor 1</td>
        <td>Valor 2</td>
        <td><span class="br-tag success">Ativo</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

### 6.6 Tags / Badges (`br-tag`)

```html
<span class="br-tag">Padrão</span>
<span class="br-tag success">Aprovado</span>
<span class="br-tag danger">Reprovado</span>
<span class="br-tag warning">Pendente</span>
<span class="br-tag info">Informação</span>
```

### 6.7 Mensagens / Alertas (`br-message`)

```html
<div class="br-message success">
  <i class="fas fa-check-circle fa-lg" aria-hidden="true"></i>
  <div class="content">Operação realizada com sucesso.</div>
</div>

<div class="br-message danger">
  <i class="fas fa-times-circle fa-lg" aria-hidden="true"></i>
  <div class="content">Ocorreu um erro. Tente novamente.</div>
</div>

<div class="br-message warning">
  <i class="fas fa-exclamation-triangle fa-lg" aria-hidden="true"></i>
  <div class="content">Atenção: verifique os dados antes de continuar.</div>
</div>

<div class="br-message info">
  <i class="fas fa-info-circle fa-lg" aria-hidden="true"></i>
  <div class="content">Esta informação é para sua referência.</div>
</div>
```

### 6.8 Loading / Spinner (`br-loading`)

```html
<div class="br-loading medium"></div>
```

### 6.9 Divider

```html
<span class="br-divider"></span>           <!-- horizontal -->
<span class="br-divider vertical"></span>  <!-- vertical -->
```

### 6.10 List (`br-list`)

```html
<div class="br-list">
  <a class="br-item" href="#">Item 1</a>
  <a class="br-item" href="#">Item 2</a>
  <span class="br-divider"></span>
  <a class="br-item" href="#">Item 3</a>
</div>
```

---

## 7. Acessibilidade — Requisitos Obrigatórios

O DSGOV é fundamentado nas diretrizes **WCAG 2.1 nível AA** e na **eMAG** (Modelo de
Acessibilidade em Governo Eletrônico). Sempre aplicar:

1. **`lang="pt-br"`** no `<html>`
2. **`aria-label`** em botões sem texto visível (ex: botões circulares com ícone)
3. **`aria-hidden="true"`** em todos os ícones decorativos Font Awesome
4. **`alt`** descritivo em todas as imagens funcionais
5. **`role="alert"`** em mensagens de erro geradas dinamicamente
6. **Contraste mínimo**: 4.5:1 para texto normal, 3:1 para texto grande
7. **Foco visível**: não remover outline do foco via CSS
8. **`scope="col"` / `scope="row"`** em cabeçalhos de tabela

---

## 8. Estados dos Componentes

| Estado      | Classe CSS           | Descrição                          |
|-------------|----------------------|------------------------------------|
| Hover       | (automático)         | Ao passar o mouse                  |
| Focus       | (automático)         | Ao receber foco via teclado        |
| Active      | `active`             | Selecionado / ativo                |
| Disabled    | `disabled` ou attr   | Indisponível para interação        |
| Loading     | `loading`            | Processando                        |
| Success     | `success`            | Estado de sucesso                  |
| Danger      | `danger`             | Estado de erro                     |
| Warning     | `warning`            | Estado de alerta                   |
| Info        | `info`               | Estado informativo                 |

---

## 9. Uso no Claude — Estratégia Recomendada

### ✅ Melhor abordagem: Skill (este arquivo) + CDN jsDelivr

**Por que:**
- O CDN do SERPRO pode falhar no sandbox do Claude (CORS / disponibilidade)
- O **jsDelivr** (`cdn.jsdelivr.net/npm/@govbr-ds/core@3.7.0`) é mais confiável
- A fonte Rawline pode não carregar → Raleway como fallback garante visual aproximado
- Os UIKits Figma são para designers, não para geração de código em Claude

**Fluxo para artefatos HTML:**
1. Claude lê esta skill
2. Usa o template base da seção 2 com CDN jsDelivr
3. Aplica tokens CSS da seção 3 como `:root { ... }` inline
4. Usa classes `br-*` da seção 6
5. Aplica regras de acessibilidade da seção 7

**Limitação conhecida:** A fonte Rawline é hospedada no SERPRO e pode não carregar
em todos os ambientes. Nesse caso, Raleway cobre visual muito próximo.

### Para projetos web reais (fora do Claude)

```bash
npm install @govbr-ds/core
```

```js
// webpack / vite
import '@govbr-ds/core/dist/core.min.css'
import '@govbr-ds/core/dist/core.min.js'
```

### Para React

```bash
npm install @govbr-ds/webcomponents-react
```

### Para Angular

```bash
npm install @govbr-ds/webcomponents-angular
```

---

## 10. Recursos Oficiais

| Recurso            | URL                                                            |
|--------------------|----------------------------------------------------------------|
| Site principal     | https://www.gov.br/ds/                                         |
| Documentação V4    | https://next-ds.estaleiro.serpro.gov.br/                       |
| Storybook          | https://www.gov.br/ds/componentes/                             |
| UIKit Figma        | Disponível no site oficial > "Como Começar" > UIKit            |
| NPM Package        | https://www.npmjs.com/package/@govbr-ds/core                   |
| GitLab Core        | https://gitlab.com/govbr-ds/bibliotecas/javascript/govbr-ds-core |
| Discord comunidade | https://discord.gg/NkaVZERAT7                                  |

---

## 11. Anti-padrões — O que NÃO fazer

- ❌ Usar cores hardcoded sem os tokens (`#1351b4` diretamente em vez de `var(--color-primary)`)
- ❌ Remover ou substituir a fonte Rawline/Raleway por fontes genéricas
- ❌ Criar botões sem o prefixo `br-button` e esperar o comportamento de estados
- ❌ Ignorar `aria-hidden="true"` nos ícones Font Awesome decorativos
- ❌ Usar Font Awesome 6 — o DSGOV usa **Font Awesome 5** (`fas`, `far`, `fab`)
- ❌ Tentar usar o logo `govbr-logo.png` em projetos não-governamentais (uso restrito)
- ❌ Modificar a identidade visual (cores primárias) para uso institucional público

---

*Referências: gov.br/ds, next-ds.estaleiro.serpro.gov.br, npmjs.com/@govbr-ds/core,
jsDelivr @govbr-ds/core v3.7.0*
