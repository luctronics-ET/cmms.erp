# Phase 7: Auth Hardening - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Substituir o hash de senha djb2 por Argon2id com upgrade lazy (re-hash na primeira autenticação bem-sucedida), sem lockout de nenhuma conta existente nem quebra dos módulos externos que chamam `POST /api/auth/login`. Remover a senha default hardcoded `1234`/`170842`. Expandir a suíte pytest p/ cobrir as rotas de manutenção das Fases 1–5.

Fora: CSRF/cookies/rate-limit (v2 SECA-*); audit trail.
</domain>

<decisions>
## Implementation Decisions

### SEC-01 — Argon2id com upgrade lazy
- Adicionar `argon2-cffi` (>=23, conforme STACK.md) ao requirements.txt. NÃO usar passlib (morto). Python 3.8+ ok.
- Detecção de tipo de hash no login (`POST /api/auth/login`, main.py:965): se `pw_hash` começa com `$argon2` → verificar com `PasswordHasher.verify`; senão (hash djb2 legado, hex curto) → verificar com `_djb2(senha) == pw_hash` E, em caso de sucesso, RE-HASH para Argon2id e `UPDATE usuarios SET pw_hash=? WHERE id=?` na mesma requisição (upgrade lazy). Próximo login usa só o caminho Argon2.
- Manter `_djb2` apenas como verificador legado (não gerar novos hashes djb2).
- Contrato de `POST /api/auth/login` inalterado: mesmo request `{mat, senha}` e mesma resposta `{token, usuario}`. Módulos externos (xPredial, aguada-web, PMOC) seguem funcionando — suas contas de serviço têm hash (djb2→argon2 no 1º login).
- Argon2 PasswordHasher com parâmetros default da lib (seguros). Tratar `VerifyMismatchError`/`InvalidHash` → 401.

### SEC-02 — remover senha default
- Login (main.py:975): remover o fallback `or _djb2("1234")`. Se `pw_hash` é NULL/vazio → NÃO autentica (401). 
- `POST /api/usuarios` (1045) e `PUT /api/usuarios` (1056): remover o `else _djb2("1234")`. Criar/editar conta sem senha → `pw_hash` fica NULL/vazio (conta não autentica até definir senha) OU exigir senha. Decisão: não gravar hash default; conta sem senha não loga. Seed (1371) não injeta `1234`.
- Documentar: contas existentes sem hash precisarão de reset de senha (provisionar via endpoint/seed com senha real).

### QA-01 — expandir pytest
- Garantir que `tests/test_manutencao.py` cobre TODAS as rotas novas das Fases 1–5: uso, plano-ativo/registro, sobressalentes (CRUD+ajuste), equipe (membros+config), cronograma. Já há muitos testes dessas fases — auditar cobertura e preencher lacunas.
- Testes de auth: login djb2 legado faz upgrade p/ argon2 (verificar pw_hash mudou para `$argon2`); 2º login só argon2; conta sem hash → 401; conta de serviço (hash pré-existente) → token; senha errada → 401.
- `pytest -x` verde na suíte completa. ATENÇÃO: há 14 falhas pré-existentes (test_catalogo/test_sync/test_import) não relacionadas a auth — avaliar se alguma é trivialmente corrigível agora (já que QA-01 pede suíte verde); se não forem do escopo de auth, documentar. Objetivo mínimo: 0 novas regressões + novos testes de auth/manutenção passam. Tentar reduzir as 14 se barato.

### Testes
- `tests/test_auth.py` (novo) ou em test_manutencao.py: cenários de upgrade lazy + sem-default + serviço.

### Claude's Discretion
- Parâmetros exatos do Argon2 (usar defaults da lib).
- Como provisionar contas sem senha (endpoint de set-senha vs deixar NULL).
- Quão fundo ir nas 14 falhas pré-existentes (priorizar não-regressão + auth).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets / Exact locations
- `backend/main.py:818` `_djb2(pw)` — manter como verificador legado.
- `backend/main.py:965` `POST /api/auth/login` — ponto do upgrade lazy. Linha 975 `expected = user.get("pw_hash") or _djb2("1234")` (remover fallback). 976 `given = _djb2(body.senha)`. 977 aceita comparação direta.
- `backend/main.py:1045` `POST /api/usuarios` `pw = _djb2(body.senha) if body.senha else _djb2("1234")` (remover default).
- `backend/main.py:1056` `PUT /api/usuarios` idem.
- `backend/main.py:1371` seed `INSERT OR REPLACE ... pw_hash` — não injetar 1234.
- `.planning/research/STACK.md` — argon2-cffi recomendado; lazy dual-hash upgrade pattern; passlib morto.
- `tests/` — suíte pytest existente (auth via _djb2 hoje; tests/test_catalogo.py tem _seed_user/_seed_sessao).

### Established Patterns
- Migração aditiva (sem schema change aqui — `pw_hash` já existe). Erros com `detail`.
- aiosqlite raw SQL.

### Integration Points
- `backend/main.py` (login + create/update usuarios + seed). requirements.txt (+argon2-cffi). tests/.
</code_context>

<specifics>
## Specific Ideas

- Upgrade lazy é requisito explícito (sem lockout; re-hash no 1º login).
- Contrato POST /api/auth/login inalterado (módulos externos).
- Senha default `1234`/`170842` totalmente removida.
</specifics>

<deferred>
## Deferred Ideas

- CSRF/cookie httpOnly/rate-limit/audit → v2 (SECA-*).
- Reset de senha self-service → futuro.
</deferred>
