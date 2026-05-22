---
title: Consolidação da arquitetura — núcleo + PMOC único categorizado
date: 2026-05-22
status: aprovado
autor: luciano
---

# Consolidação da arquitetura — núcleo + PMOC único categorizado

## 1. Contexto

A documentação do repositório `cmasm.erp` (`REQUISITOS.md`, `CLAUDE.md`, `todo.md`, `MODULOS_EXTERNOS.md`, `TEMPLATE_PMOC.md`) descreve uma arquitetura de **"núcleo magro + N PMOCs offline-first"**, com um repositório HTML autônomo por domínio (`pmoc_refrigeracao`, `pmoc_predial`, `pmoc_paiois`, `pmoc_transportes`, `pmoc_grama`, `pmoc_eletrica`, `pmoc_calibracao`).

O documento `pmoc.refs/Regras de Negócio e Fluxos.md`, por outro lado, descreve um **sistema único** com ativos categorizados por `tipo`, módulo Manutenção central com tabs por categoria, e submódulos integrados (xGrama, Transportes) que alimentam o mesmo registro de ativos.

Estas duas visões são incompatíveis. A intenção real é a segunda — com a ressalva de que existe **um app PMOC de campo, offline-first**, que opera com as mesmas categorias.

## 2. Decisão

**Arquitetura adotada:**

- **Núcleo** (`cmasm.erp`): backend FastAPI + ERP web (`cmasm_erp.html`) com módulo Manutenção categorizado por `tipo` de ativo. Tela única com tabs por categoria.
- **PMOC único de campo**: aplicativo HTML offline-first em `cmasm.erp/pmoc/`, com seletor de categoria interno. Não há mais "um repo por domínio".
- **Módulos externos** (`MODULOS_EXTERNOS.md`): reservado a sistemas com hardware/Postgres próprio — `aguada-web`, `xSeguranca`, `xCFTV`, `xFonoclama`. **PMOCs não são mais módulos externos.**

**Repositórios de domínio existentes** (`pmoc_refrigeracao`, `pmoc_eletrica`, `pmoc_calibracao`, `pmoc_corte`, `pmoc_transportes`) serão **arquivados**. O usuário decide quando movê-los para `.archive_pmoc_legado/` ou `.delete/`.

**`pmoc.refs`** permanece como repositório de referências e seeds (CSVs normativos, POPs, mapas, planilhas).

**Fonte canônica do modelo de domínio**: `Regras de Negócio e Fluxos.md` será **copiado** para `cmasm.erp/` (espelhado em `pmoc.refs/` com nota indicando o canônico).

## 3. Mudanças por arquivo

### 3.1 `cmasm.erp/REQUISITOS.md` — atualizar

Substituir a visão "núcleo magro + N PMOCs" por:

> O sistema é composto por (1) um **núcleo** (`cmasm.erp`) — backend FastAPI + ERP web — que centraliza ativos, estoque, ordens de serviço e manutenção; e (2) um **PMOC único offline-first**, app HTML de campo com categorias internas (refrigeração, predial, paióis, transportes, grama, elétrica, calibração), que sincroniza com o núcleo via API.

Reescrever §3.1 (escopo do núcleo) listando módulos como tabs/seções de uma aplicação única, e o roadmap §7 removendo a noção de migrar PMOCs entre repos.

### 3.2 `cmasm.erp/CLAUDE.md` — atualizar

- Reescrever bloco introdutório: trocar "núcleo magro + PMOCs offline-first" por "núcleo + PMOC único categorizado".
- "Repository Structure": adicionar `pmoc/` como subdiretório do repo, contendo o app de campo.
- "Módulos Externos (PMOCs)": remover esta seção; PMOCs não são externos. Manter tabela só com aguada-web, xSeguranca, xCFTV, xFonoclama.
- "Reference Files": adicionar `Regras de Negócio e Fluxos.md` (fonte canônica do modelo de domínio).
- "Convenções para mudanças": substituir "PMOCs: sempre offline-first em repo próprio" por "PMOC único: adicionar categorias como tabs/seções dentro de `pmoc/`".

### 3.3 `cmasm.erp/todo.md` — reescrever

**P0 reorganizados:**

1. **Tela Manutenção categorizada no núcleo** (`cmasm_erp.html`): tabs por categoria conforme `Regras §7`, painel verde/amarelo/vermelho calculado de `uso_atual` vs `proximo_uso` por etapa de plano.
2. **API de Catálogo de Serviços + Planos**: endpoints `GET/POST/PUT /api/catalogo/servicos`, `/api/catalogo/planos`, `/api/catalogo/qualificacoes`. Schema já existe em `data/schema_catalogo.sql`. Versionamento imutável por `(codigo, versao)`.
3. **API de sincronização — fechamento**: manifest com delta (`since=`), Auth Bearer em `/api/sync/*`, teste de integração end-to-end. Contrato passa a usar `modulo=<categoria>` (ex: `modulo=refrigeracao`) — não mais `pmoc_<dom>`.
4. **PMOC único — esqueleto** (`cmasm.erp/pmoc/`): shell HTML com seletor de categoria + cliente sync embutido + wrapper IndexedDB + auth helper. Categoria piloto: refrigeração.

**P1 — categorias do PMOC** (substitui "Migrar PMOCs"):

- [ ] Categoria: refrigeração (piloto)
- [ ] Categoria: predial
- [ ] Categoria: paióis
- [ ] Categoria: transportes
- [ ] Categoria: grama
- [ ] Categoria: elétrica
- [ ] Categoria: calibração

**P2 e P3** mantidos com revisão terminológica (sem "vários PMOCs").

### 3.4 `cmasm.erp/MODULOS_EXTERNOS.md` — reescrever

Manter apenas escopo de módulos *realmente* externos (sistemas com banco/hardware próprios):

| Módulo | Stack | Porta |
|---|---|---|
| aguada-web | FastAPI + MQTT + nginx | 8001 (hardware ESP32) |
| xSeguranca | React + FastAPI + PostgreSQL | 8000/3000 |
| xCFTV | Java | — |
| xFonoclama | firmware ESP32 | — |

Manter contrato genérico de integração (`GET /api/usuarios`, `POST /api/os` com `modulo_origem`). Remover seção sobre catálogo de PMOCs.

### 3.5 `cmasm.erp/TEMPLATE_PMOC.md` — deletar

Conceito morto. Quando começar a implementação do PMOC único, criar `cmasm.erp/pmoc/CATEGORIAS.md` documentando como adicionar uma categoria nova ao app — fora do escopo deste spec.

### 3.6 `cmasm.erp/Regras de Negocio e Fluxos.md` — novo (cópia)

Copiar literalmente de `pmoc.refs/Regras de Negócio e Fluxos.md`. Adicionar header indicando que esta é a fonte canônica e que `pmoc.refs/` mantém cópia espelhada.

### 3.7 `pmoc.refs/Regras de Negócio e Fluxos.md` — adicionar nota

No topo, inserir:

> **Nota:** Fonte canônica deste documento está em `cmasm.erp/Regras de Negocio e Fluxos.md`. Esta cópia é espelho para referência junto às demais fontes de `pmoc.refs/`.

### 3.8 `cmasm.erp/Rules.md` — reconciliar

`Rules.md` (núcleo magro) e `Regras de Negocio e Fluxos.md` (modelo de domínio) têm sobreposição. Após esta consolidação:

- `Rules.md` → foca em **regras técnicas e operacionais** do núcleo (auth, schema, migrations, lifecycle de OS no banco, idempotência de sync).
- `Regras de Negocio e Fluxos.md` → foca em **modelo de domínio e fluxos de negócio** (categorias de ativos, planos por tipo, hierarquia PS/OS, NECs, transportes, estoque distribuído).

Onde houver conflito, `Regras de Negocio e Fluxos.md` prevalece para semântica de domínio; `Rules.md` prevalece para detalhes de implementação do núcleo.

## 4. Vocabulário a remover

| Termo antigo | Substituir por |
|---|---|
| "N PMOCs offline-first" | "PMOC único com categorias" |
| "Repo PMOC" / "pmoc_\<dom\>" | "Categoria do PMOC" |
| "Módulo externo PMOC" | (deletar — PMOC não é externo) |
| "Shell comum a vários PMOCs" / "pmoc-engine como biblioteca" | "Código do app PMOC" |
| "Núcleo magro" | "Núcleo" (qualificador deixa de fazer sentido) |

## 5. Fora do escopo deste spec

- Implementação da tela Manutenção categorizada.
- Implementação da API de Catálogo.
- Implementação do esqueleto do PMOC.
- Movimentação física dos repos `pmoc_*` para `.archive` ou `.delete` — usuário decide o momento.
- Documento `pmoc/CATEGORIAS.md` (criado quando a implementação começar).

## 6. Critério de aceitação

- [ ] Os 7 arquivos listados em §3 estão coerentes com a arquitetura "núcleo + PMOC único categorizado".
- [ ] Nenhum doc em `cmasm.erp/` ainda referencia "vários PMOCs" como repos separados.
- [ ] `MODULOS_EXTERNOS.md` não lista PMOCs.
- [ ] `Regras de Negocio e Fluxos.md` existe em `cmasm.erp/` e em `pmoc.refs/` (com nota de espelho).
- [ ] `todo.md` reflete os P0 reorganizados.
- [ ] `TEMPLATE_PMOC.md` foi removido.
