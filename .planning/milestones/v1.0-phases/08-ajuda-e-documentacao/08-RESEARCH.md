# Phase 8: Ajuda e Documentacao — Research

**Researched:** 2026-06-29
**Domain:** FastAPI file upload/download + SQLite versioning + vanilla JS safe markdown rendering
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Armazenamento (servidor local)**
- Documentos/arquivos: filesystem em `data/documentos/<categoria>/` (já criado), 1 arquivo por versão (nome com id+versão), + metadados no SQLite. Sem nuvem.
- Ajuda contextual: conteúdo markdown direto no SQLite (textos curtos).
- Migração aditiva: tabelas novas em `schema_manutencao.sql` (ou novo `schema_docs.sql` adicionado a `CoreDB._SCHEMAS`). CREATE TABLE IF NOT EXISTS, nunca DROP.

**Modelo de dados**
- `ajuda_topicos`: `id` PK, `categoria` (nullable/geral), `chave` (página/seção, UNIQUE), `titulo`, `conteudo_md` TEXT, `updated_at`, `updated_by`.
- `documentos`: `id` PK, `categoria` TEXT, `tipo` TEXT (modelo|formulario|guia|norma), `titulo`, `descricao`, `ativo` INTEGER DEFAULT 1, `criado_em`, `criado_por`.
- `documento_versoes`: `id` PK, `documento_id` FK, `versao` INTEGER, `arquivo_path` TEXT (relativo a data/documentos), `arquivo_nome` TEXT, `mime` TEXT, `tamanho` INTEGER, `autor`, `data` (created_at), `ativo` INTEGER DEFAULT 1. UNIQUE(documento_id, versao).

**Endpoints (router backend/docs.py registrado em main.py)**
- Ajuda: `GET /api/docs/ajuda?chave=`, `GET /api/docs/ajuda`, `PUT /api/docs/ajuda/{chave}` (upsert). `_require_auth`; edição exige não-visitante (`_require_escrita`).
- Documentos: `GET /api/docs/documentos?categoria=&tipo=`, `POST /api/docs/documentos`, `GET /api/docs/documentos/{id}`, `POST /api/docs/documentos/{id}/versoes` (upload), `GET /api/docs/documentos/{id}/versoes/{versao}/download`. Soft-delete (ativo=0).
- `_require_escrita` nas escritas; GET livre (auth).

**Frontend (UX)**
- Ajuda contextual: botão "?" na shell que abre painel/drawer com markdown renderizado de forma segura; modo edição p/ gestor (textarea → PUT).
- Aba "Documentos" (TAB_DEFS no mesmo padrão de erp-manutencao.js): navegação por categoria + tipo; lista de documentos com última versão; ações upload/histórico/download. Badges por tipo.
- Categorias = as do PMOC (refrigeracao, predial, paiois, transportes, grama, eletrica, calibracao) + "geral".
- DOM seguro via el()/textContent; markdown da ajuda renderizado sem innerHTML de conteúdo não-confiável.

**Testes** (`tests/test_docs.py`): ajuda GET/PUT; criar doc; upload → versão incrementa (1→2), versão anterior preservada, autor+data gravados; download correto; listagem por categoria; soft-delete; db.init() 2x (idempotente); escrita por visualizador → 403.

### Claude's Discretion
- Router em `backend/docs.py` novo vs estender `manutencao.py` (preferir docs.py).
- Limites de tamanho/extensão de upload (definir um teto razoável; validar extensão).
- Render de markdown na ajuda: lib mínima vs formatação própria segura.
- Conferir `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` por UI de ajuda/docs a portar — opcional.

### Deferred Ideas (OUT OF SCOPE)
- Busca full-text / OCR nos documentos.
- Editor WYSIWYG da ajuda (textarea markdown por agora).
- Versionamento de diff/preview.
</user_constraints>

---

## Summary

Esta fase implementa dois sub-sistemas distintos dentro do mesmo router (`backend/docs.py`): (1) ajuda contextual com conteúdo markdown armazenado em SQLite, e (2) repositório de documentos versionado com arquivos no filesystem local. O contrato de dados e endpoints está completamente definido no CONTEXT.md — não há decisões de design abertas no plano, apenas implementação.

O risco técnico mais alto é segurança de upload de arquivos: path traversal via `categoria` ou `arquivo_nome` vindos do cliente, content-type spoofing e ausência de limite de tamanho são vetores imediatos. O padrão seguro é gerar o path do arquivo a partir de dados controlados pelo servidor (`doc_id` + `versao` + extensão extraída do `filename` original), nunca do nome original. O segundo risco é a atomicidade da versão: `max(versao)+1` dentro de uma transação aiosqlite resolve o incremento sem race condition.

`python-multipart` **já está instalado** (`requirements.txt` linha 5, versão 0.0.9 em runtime). `aiofiles` também está instalado (versão 25.1.0). Nenhum pacote novo precisa ser adicionado ao projeto.

**Recomendação primária:** Usar `aiofiles.open(..., 'wb')` para escrita assíncrona dos uploads; `FileResponse` para download (quando o arquivo existe em disco); `StreamingResponse` como fallback se precisar de headers dinâmicos. Markdown da ajuda: renderer mínimo hand-rolled com textContent (5 regras de substituição sem innerHTML) — suficiente para textos curtos de ajuda.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Upload de arquivo | API / Backend | — | `UploadFile` vive no backend; frontend só envia `FormData` |
| Download de arquivo | API / Backend | — | `FileResponse`/`StreamingResponse` com path resolvido server-side |
| Versioning atômico | Database / Storage | API | `max(versao)+1` em transação aiosqlite |
| Storage de arquivos | API / Backend (filesystem) | — | `data/documentos/<cat>/<id>_v<v><ext>` no servidor |
| Conteúdo markdown da ajuda | Database / Storage | — | SQLite `ajuda_topicos.conteudo_md` |
| Render seguro do markdown | Browser / Client | — | Vanilla JS sem innerHTML; textContent + DOM |
| Validação categoria/extensão | API / Backend | — | Whitelist server-side; nunca confiar no cliente |
| Auth / write-guard | API / Backend | — | `_require_auth` + `_require_escrita` já existentes em main.py |

---

## Standard Stack

### Core (todos já presentes — nenhuma instalação nova)

| Library | Version (confirmada) | Purpose | Source |
|---------|---------------------|---------|--------|
| `fastapi` | 0.115.0 | Framework HTTP + `UploadFile` | `requirements.txt` L1 [VERIFIED: arquivo local] |
| `python-multipart` | 0.0.29 (runtime) / 0.0.9 (pinned) | Parsing multipart/form-data (obrigatório para `UploadFile`) | `requirements.txt` L5 [VERIFIED: arquivo local] |
| `aiofiles` | 25.1.0 | Escrita assíncrona de arquivo em disco | `requirements.txt` L6 [VERIFIED: pip show] |
| `aiosqlite` | 0.20.0 | DB async — transação atomica para versioning | `requirements.txt` L3 [VERIFIED: arquivo local] |
| `pydantic` | 2.7.4 | Modelos de request/response | `requirements.txt` L4 [VERIFIED: arquivo local] |

**Nenhum pacote novo é necessário.** `python-multipart` foi confirmado presente e é o que o FastAPI usa internamente para parsear `multipart/form-data`. Sem ele, qualquer endpoint com `UploadFile` levanta `RuntimeError: Form data requires "python-multipart" to be installed`.

### Sem pacotes novos

Decisão: zero dependências novas. O renderer de markdown da ajuda é hand-rolled no frontend (ver seção "Markdown Rendering").

---

## Package Legitimacy Audit

> Nenhum pacote externo novo será instalado nesta fase. Todos os pacotes utilizados já estão em `requirements.txt` e em uso no projeto. Auditoria de legitimidade não aplicável.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious (SUS):** none

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (cmasm_erp.html)
  │
  ├─ [?] button / drawer ──→ GET /api/docs/ajuda?chave=<page>
  │        render markdown    ← { titulo, conteudo_md }
  │        (safe renderer)
  │
  ├─ Aba "Documentos" ──────→ GET /api/docs/documentos?categoria=&tipo=
  │        lista + filtros     ← [{ id, titulo, ultima_versao, tipo, ... }]
  │
  ├─ Upload (FormData) ─────→ POST /api/docs/documentos/{id}/versoes
  │        file + Authorization  (UploadFile, _require_escrita)
  │                               → sanitize categoria + gerar path seguro
  │                               → aiofiles.write(data/documentos/<cat>/<id>_v<n><ext>)
  │                               → INSERT documento_versoes (versao = max+1)
  │                               ← { versao, arquivo_path, ... }
  │
  └─ Download ──────────────→ GET /api/docs/documentos/{id}/versoes/{v}/download
                               → fetch_one(documento_versoes) → resolve abs path
                               → FileResponse(path, filename=arquivo_nome)
                               ← binary stream com Content-Disposition

backend/docs.py  ←→  CoreDB (aiosqlite)  ←→  data/core.db
                                              tables: ajuda_topicos
                                                      documentos
                                                      documento_versoes

filesystem: data/documentos/<categoria>/<doc_id>_v<versao><ext>
            (categoria whitelist-validated; path nunca usa nome do cliente)
```

### Recommended Project Structure

```
backend/
├── docs.py               # novo router — /api/docs/* (ajuda + documentos)
data/
├── schema_docs.sql       # novo schema — ajuda_topicos, documentos, documento_versoes
├── documentos/           # ja criado; sub-dirs por categoria criados no upload
│   ├── geral/
│   ├── refrigeracao/
│   └── ...               # demais categorias PMOC
tests/
└── test_docs.py          # testes unitários (pytest-asyncio)
assets/
└── erp-docs.js           # módulo frontend — aba Documentos + help drawer
```

**`schema_docs.sql` é adicionado a `CoreDB._SCHEMAS`** em `backend/db_core.py` (linha 7-12), seguindo o padrão exato das entradas existentes.

---

## Key Implementation Patterns

### Pattern 1: FastAPI UploadFile + aiofiles (upload seguro)

**O que é:** FastAPI recebe `multipart/form-data` via `UploadFile`; `aiofiles` grava assincronamente no disco.

**Dependência crítica:** `python-multipart` deve estar instalado (CONFIRMADO em `requirements.txt` L5).

```python
# Source: FastAPI docs + padrão projeto xCMASM
import aiofiles
import os, re
from fastapi import UploadFile, File, Form, HTTPException

ALLOWED_CATS = frozenset({
    "geral", "refrigeracao", "predial", "paiois",
    "transportes", "grama", "eletrica", "calibracao",
})
ALLOWED_EXTS = frozenset({
    ".pdf", ".docx", ".xlsx", ".odt", ".ods",
    ".png", ".jpg", ".jpeg", ".txt", ".csv",
})
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

_DATA_DOCS = os.path.join(os.path.dirname(__file__), "..", "data", "documentos")

def _safe_ext(filename: str) -> str:
    """Extrai extensão em lowercase; levanta 400 se não permitida."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Extensão não permitida: {ext!r}")
    return ext

def _make_safe_path(categoria: str, doc_id: int, versao: int, ext: str) -> str:
    """Gera path absoluto a partir de dados controlados pelo servidor.
    NUNCA usa o nome original do arquivo — previne path traversal.
    """
    if categoria not in ALLOWED_CATS:
        raise HTTPException(400, f"Categoria inválida: {categoria!r}")
    cat_dir = os.path.join(_DATA_DOCS, categoria)
    os.makedirs(cat_dir, exist_ok=True)
    filename = f"{doc_id}_v{versao}{ext}"           # ex: 42_v3.pdf
    return os.path.join(cat_dir, filename)

@router.post("/documentos/{doc_id}/versoes", status_code=201)
async def upload_versao(
    doc_id: int,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
):
    user = await _require_auth(authorization)
    _require_escrita(user)  # main.py:857 — lança 403 se role == 'visualizador'

    # 1. Valida tamanho antes de ler tudo na memória
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Arquivo excede 20 MB")

    ext = _safe_ext(file.filename or "")

    db = _db()
    doc = await db.fetch_one(
        "SELECT id, categoria FROM documentos WHERE id = ? AND ativo = 1", (doc_id,)
    )
    if not doc:
        raise HTTPException(404, "Documento não encontrado")

    # 2. Versão atômica: max(versao)+1 dentro de uma única conexão aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT COALESCE(MAX(versao), 0) + 1 AS next_v "
            "FROM documento_versoes WHERE documento_id = ?",
            (doc_id,),
        )
        row = await cur.fetchone()
        next_v = row["next_v"]

        abs_path = _make_safe_path(doc["categoria"], doc_id, next_v, ext)
        rel_path = os.path.relpath(abs_path, start=os.path.join(_DATA_DOCS, ".."))

        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(contents)

        await conn.execute(
            "INSERT INTO documento_versoes "
            "(documento_id, versao, arquivo_path, arquivo_nome, mime, tamanho, autor) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, next_v, rel_path, file.filename, file.content_type,
             len(contents), user["nome"]),
        )
        await conn.commit()

    return {"documento_id": doc_id, "versao": next_v, "arquivo_path": rel_path}
```

**Pontos-chave:**
- `file.read(MAX + 1)` detecta excesso SEM carregar o arquivo inteiro antes da checagem.
- `_make_safe_path` usa apenas `(doc_id, versao, ext)` — dados server-controlled; ignora `file.filename` para o path real.
- `file.filename` é preservado apenas como metadado (`arquivo_nome`) para o `Content-Disposition` no download.
- Toda a sequência `SELECT max → INSERT` ocorre dentro de UMA conexão aiosqlite com `commit()` único — atomicidade real mesmo com aiosqlite por-conexão.

### Pattern 2: Download com FileResponse

```python
# Source: FastAPI docs + main.py:701,714,717 (padrão FileResponse já em uso)
from fastapi.responses import FileResponse
import os

@router.get("/documentos/{doc_id}/versoes/{versao}/download")
async def download_versao(
    doc_id: int,
    versao: int,
    authorization: str | None = Header(None),
):
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one(
        "SELECT arquivo_path, arquivo_nome, mime FROM documento_versoes "
        "WHERE documento_id = ? AND versao = ? AND ativo = 1",
        (doc_id, versao),
    )
    if not row:
        raise HTTPException(404, "Versão não encontrada")

    # Resolve abs path a partir da raiz data/ (rel_path gravado no INSERT)
    abs_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", row["arquivo_path"])
    )
    # Sanity check: path deve estar dentro de _DATA_DOCS
    if not abs_path.startswith(os.path.abspath(_DATA_DOCS)):
        raise HTTPException(403, "Acesso negado")
    if not os.path.isfile(abs_path):
        raise HTTPException(404, "Arquivo físico não encontrado")

    return FileResponse(
        path=abs_path,
        filename=row["arquivo_nome"],   # Content-Disposition: attachment; filename=...
        media_type=row["mime"] or "application/octet-stream",
    )
```

**Nota:** `os.path.normpath` + `startswith(abspath(_DATA_DOCS))` é a segunda linha de defesa contra path traversal — mesmo que `arquivo_path` no DB fosse corrompido (não deveria ser, pois é gerado pelo servidor).

### Pattern 3: Upsert ajuda_topicos

```python
# PUT /api/docs/ajuda/{chave} — upsert por chave (UNIQUE constraint)
@router.put("/ajuda/{chave}")
async def upsert_ajuda(chave: str, body: AjudaIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    now = datetime.utcnow().isoformat()
    await _db().execute(
        """INSERT INTO ajuda_topicos (chave, categoria, titulo, conteudo_md, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(chave) DO UPDATE SET
             titulo       = excluded.titulo,
             conteudo_md  = excluded.conteudo_md,
             updated_at   = excluded.updated_at,
             updated_by   = excluded.updated_by""",
        (chave, body.categoria, body.titulo, body.conteudo_md, now, user["nome"]),
    )
    return await _db().fetch_one("SELECT * FROM ajuda_topicos WHERE chave = ?", (chave,))
```

**Pattern de upsert:** `INSERT ... ON CONFLICT(chave) DO UPDATE SET` — SQLite syntax válida desde 3.24 (2018). Mais idiomático do que `INSERT OR REPLACE` porque preserva o `id` PK original.

### Pattern 4: Router registration (main.py)

Seguindo exatamente o padrão das linhas 23-26 e 329-332 de `backend/main.py`:

```python
# Em backend/main.py — adicionar junto aos outros imports de routers (linha ~26):
from .docs import router as docs_router

# Junto aos include_router (linha ~333):
app.include_router(docs_router)
```

Em `backend/docs.py`:
```python
router = APIRouter(prefix="/api/docs", tags=["docs"])
```

### Pattern 5: _require_escrita (já em main.py:857-861)

```python
# backend/main.py:857-861 — função já existente, importada via sys.modules
def _require_escrita(user: dict) -> None:
    """RES-05: lança 403 se role == 'visualizador'."""
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não têm permissão de escrita")
```

Em `backend/docs.py`, usa o mesmo padrão de `manutencao.py` para acessar `main.py` via `sys.modules`:

```python
import sys

def _db():
    return sys.modules["backend.main"].db

def _require_escrita(user: dict) -> None:
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não têm permissão de escrita")
```

(Copiar a função localmente é mais seguro do que tentar importar de `main` — evita circular import, igual ao padrão de `manutencao.py:27-29` e `catalogo.py`.)

### Pattern 6: Schema SQL (schema_docs.sql)

Seguindo o estilo de `schema_manutencao.sql` (L1-19):

```sql
-- xCMASM · Schema Docs — Ajuda Contextual + Repositório de Documentos
-- Fase 08. Aditivo — CREATE TABLE IF NOT EXISTS obrigatório. Nunca DROP.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ajuda_topicos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  chave        TEXT    NOT NULL UNIQUE,        -- ex: 'manutencao', 'estoque/lista'
  categoria    TEXT,                           -- categoria PMOC ou NULL (geral)
  titulo       TEXT    NOT NULL DEFAULT '',
  conteudo_md  TEXT    NOT NULL DEFAULT '',
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_by   TEXT                            -- snapshot nome do usuário
);
CREATE INDEX IF NOT EXISTS idx_ajuda_chave ON ajuda_topicos(chave);

CREATE TABLE IF NOT EXISTS documentos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  categoria    TEXT    NOT NULL,               -- whitelist: geral|refrigeracao|...
  tipo         TEXT    NOT NULL DEFAULT 'modelo', -- modelo|formulario|guia|norma
  titulo       TEXT    NOT NULL,
  descricao    TEXT,
  ativo        INTEGER NOT NULL DEFAULT 1,     -- soft-delete: 0 = inativo
  criado_em    TEXT    NOT NULL DEFAULT (datetime('now')),
  criado_por   TEXT                            -- snapshot nome do usuário
);
CREATE INDEX IF NOT EXISTS idx_doc_cat_tipo ON documentos(categoria, tipo, ativo);

CREATE TABLE IF NOT EXISTS documento_versoes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  documento_id  INTEGER NOT NULL REFERENCES documentos(id),
  versao        INTEGER NOT NULL,              -- 1, 2, 3, ... por documento
  arquivo_path  TEXT    NOT NULL,              -- relativo a data/ (ex: documentos/geral/42_v1.pdf)
  arquivo_nome  TEXT    NOT NULL,              -- nome original (Content-Disposition)
  mime          TEXT,
  tamanho       INTEGER,                       -- bytes
  autor         TEXT,                          -- snapshot nome do usuário
  data          TEXT    NOT NULL DEFAULT (datetime('now')),
  ativo         INTEGER NOT NULL DEFAULT 1,    -- soft-delete de versão
  UNIQUE(documento_id, versao)
);
CREATE INDEX IF NOT EXISTS idx_dv_doc ON documento_versoes(documento_id, versao DESC);
```

**Adição a `db_core.py`** (linha 7-12 — `_SCHEMAS` list):

```python
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
    os.path.join(_DATA_DIR, "schema_catalogo.sql"),
    os.path.join(_DATA_DIR, "schema_manutencao.sql"),
    os.path.join(_DATA_DIR, "schema_docs.sql"),   # <-- fase 08
]
```

### Pattern 7: el() helper (frontend)

`el()` está definido em `assets/pmoc-engine.js:25-40` e exposto via `window.engine`. Em `erp-manutencao.js` é chamado diretamente (pmoc-engine.js é carregado antes). O módulo `erp-docs.js` deve seguir o mesmo padrão IIFE com `'use strict'` e acesso a `window.engine.el` ou redefinir localmente (pmoc-engine.js já expõe `el` via `global.engine.utils.el` — verificar exports do engine antes de usar).

**Alternativa segura:** copiar a função `el` dentro do IIFE do módulo (é pequena — 16 linhas). Isso evita dependência de que pmoc-engine.js exponha `el` publicamente.

### Pattern 8: Sidebar nav item (cmasm_erp.html)

Seguindo o padrão das linhas 625-656 de `cmasm_erp.html`:

```html
<!-- Dentro de <div class="sb-section">Infraestrutura (CMASM-10)</div> -->
<div class="ni" data-page="documentos" onclick="showPage('documentos',this)">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
  </svg>
  Documentos
</div>
```

O help drawer ("?") deve ser inserido na `.sb-tools` div (linha 187) ou no topbar como um `button.btn-icon` adicional — já existem `.topbar-alert` buttons ali. O drawer é um `<div>` com `position:fixed; right:0; top:0; height:100vh` que aparece/desaparece via classe CSS.

---

## Safe Markdown Rendering (DOC-01 — ajuda contextual)

### Recomendação: renderer mínimo hand-rolled via textContent

O CONTEXT.md proíbe `innerHTML` de conteúdo não-confiável. A recomendação é um renderer que:
1. Divide o markdown em linhas.
2. Para cada linha, cria um elemento DOM via `document.createElement`.
3. Define o texto via `textContent` (nunca `innerHTML`).
4. Aplica formatações inline (bold/italic) via DOM manipulation, não regex+innerHTML.

```javascript
// Renderer mínimo seguro — sem innerHTML de conteúdo não-confiável
// Suporta: # ## (h1/h2), **bold**, *italic*, `code`, - listas, linhas em branco
function renderMdSafe(md, container) {
  container.innerHTML = '';  // limpa o container (innerHTML vazio é seguro)
  const lines = (md || '').split('\n');
  let ul = null;

  for (const raw of lines) {
    const line = raw.trimEnd();

    // Linha em branco: fecha lista pendente
    if (!line.trim()) {
      if (ul) { container.appendChild(ul); ul = null; }
      container.appendChild(document.createElement('br'));
      continue;
    }

    let node;
    if (/^## /.test(line)) {
      node = document.createElement('h3');
      _applyInline(node, line.slice(3));
    } else if (/^# /.test(line)) {
      node = document.createElement('h2');
      _applyInline(node, line.slice(2));
    } else if (/^- /.test(line) || /^\* /.test(line)) {
      if (!ul) ul = document.createElement('ul');
      const li = document.createElement('li');
      _applyInline(li, line.slice(2));
      ul.appendChild(li);
      continue;
    } else {
      if (ul) { container.appendChild(ul); ul = null; }
      node = document.createElement('p');
      _applyInline(node, line);
    }
    if (ul) { container.appendChild(ul); ul = null; }
    container.appendChild(node);
  }
  if (ul) container.appendChild(ul);
}

// Aplica bold/italic/code via DOM — sem innerHTML
function _applyInline(parent, text) {
  // Tokens: **bold**, *italic*, `code`  (ordem importa: ** antes de *)
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      parent.appendChild(document.createTextNode(text.slice(last, m.index)));
    }
    let el;
    if (m[0].startsWith('**')) { el = document.createElement('strong'); el.textContent = m[2]; }
    else if (m[0].startsWith('*'))  { el = document.createElement('em'); el.textContent = m[3]; }
    else { el = document.createElement('code'); el.textContent = m[4]; }
    parent.appendChild(el);
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    parent.appendChild(document.createTextNode(text.slice(last)));
  }
}
```

**Por que não usar uma lib externa (marked.js, micromark)?**
- O CONTEXT.md delimita o escopo a "textos curtos de ajuda" — um renderer de 50 linhas cobre 100% dos casos.
- Adicionar uma lib externa requer auditoria de legitimidade, bundle review, e possibilidade de XSS se usada sem sanitização (`marked` por padrão produz HTML — requer `DOMPurify` em seguida).
- Sem build step: libs externas seriam CDN ou arquivo local, adicionando latência ou arquivo estático novo.
- O renderer acima é determinístico, auditável, zero-dependency. [ASSUMED: suficiente para o escopo de ajuda contextual — confirmar com usuário se Markdown mais rico for necessário no futuro]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing `multipart/form-data` | Parser de boundary manual | FastAPI `UploadFile` + `python-multipart` (já instalado) | Edge cases de boundary, encoding, streaming |
| Versioning com lock otimista | Flag `em_uso` no DB | `UNIQUE(documento_id, versao)` + `COALESCE(MAX(versao),0)+1` em transação aiosqlite | SQLite garante serialização; constraint viola duplicata |
| Sanitização de path | Regex customizado | `os.path.normpath` + `startswith(abspath(DATA_DOCS))` | `../` e `%2F` já resolvidos pelo normpath |
| Token/auth do usuário | Decode JWT/token manual | `_require_auth` já em `main.py:843-854` + padrão em `manutencao.py:32-44` | Auth já testada e auditada |
| Soft-delete | Hard DELETE | `ativo = 0` (padrão do projeto inteiro) | Auditoria, histórico, FK integridade |

---

## Common Pitfalls

### Pitfall 1: Path traversal via nome de arquivo ou categoria

**O que vai errado:** `categoria = "../../../etc"` ou `arquivo_nome = "../../evil.sh"` vindos do cliente são usados diretamente no `os.path.join`. O arquivo fica fora de `data/documentos/`.

**Por que acontece:** confiar no cliente para compor o path do arquivo.

**Como evitar:**
1. `categoria` deve ser validada contra `ALLOWED_CATS` (whitelist) ANTES de qualquer uso em path.
2. O path do arquivo armazenado em disco deve ser `f"{doc_id}_v{versao}{ext}"` — não usa o nome original.
3. No download, após recuperar `arquivo_path` do DB: `os.path.normpath(joined)` e então `assert abs_path.startswith(abspath(DATA_DOCS))`.

**Sinais de alerta:** `../` em qualquer campo vindo do cliente; `arquivo_path` computado a partir de `file.filename`.

### Pitfall 2: Race condition no incremento de versão

**O que vai errado:** dois uploads simultâneos para o mesmo `doc_id` leem `max(versao) = 3` e ambos tentam inserir `versao = 4`. O `UNIQUE(documento_id, versao)` captura a colisão, mas o segundo upload retorna 500 em vez de retry automático.

**Por que acontece:** `db.fetch_one` + `db.execute` separados abrem DUAS conexões aiosqlite — não são atômicos.

**Como evitar:** executar `SELECT COALESCE(MAX(versao),0)+1` e `INSERT` na MESMA conexão aiosqlite com `async with aiosqlite.connect(...)`. Ver Pattern 1 acima. A constraint `UNIQUE(documento_id, versao)` ainda garante integridade se a proteção da transação falhar.

**Sinais de alerta:** dois rows com mesmo `(documento_id, versao)` — impossível se a constraint estiver no DDL.

### Pitfall 3: `python-multipart` ausente silencia `UploadFile`

**O que vai errado:** FastAPI levanta `RuntimeError: Form data requires "python-multipart" to be installed` no primeiro request de upload — não em startup.

**Status neste projeto:** `python-multipart==0.0.9` está em `requirements.txt` L5 — CONFIRMADO PRESENTE. [VERIFIED: arquivo local]

**Sinais de alerta:** se for instalado em novo ambiente, `pip install -r requirements.txt` resolve. Não adicionar ao `requirements.txt` novamente.

### Pitfall 4: content-type spoofing

**O que vai errado:** cliente envia `Content-Type: image/jpeg` com um executável `.sh` dentro. O `file.content_type` vem do cliente — não é confiável.

**Como evitar:** validar a **extensão** do `file.filename` contra `ALLOWED_EXTS` (whitelist), independente do `mime` informado. Para server local (naval, sem internet), isso é suficiente. Não usar `file.content_type` para decisões de segurança — usá-lo apenas como metadado armazenado para o `Content-Type` no download.

### Pitfall 5: `INSERT OR REPLACE` destrói o `id` original em `ajuda_topicos`

**O que vai errado:** `INSERT OR REPLACE INTO ajuda_topicos ... WHERE chave = ?` cria um novo row com novo `id` PK, quebrando qualquer FK ou referência externa.

**Como evitar:** usar `INSERT ... ON CONFLICT(chave) DO UPDATE SET ...` (ver Pattern 3). Essa sintaxe preserva o `id` original e atualiza apenas os campos especificados.

### Pitfall 6: Markdown com `innerHTML` direto

**O que vai errado:** `elem.innerHTML = conteudo_md` — mesmo que o conteúdo venha do próprio banco, qualquer gestor pode inserir `<script>alert(1)</script>` e executar código arbitrário na sessão de qualquer usuário.

**Como evitar:** usar o renderer de Pattern 8 acima (textContent + DOM). Nunca atribuir `innerHTML` ao conteúdo de `ajuda_topicos.conteudo_md`.

### Pitfall 7: `aiofiles` com `db_core.CoreDB.execute` para arquivos grandes

**O que vai errado:** tentar usar `db.execute` para gravar bytes no disco (não faz sentido, mas pode ser confundido com `aiofiles`).

**Como evitar:** `aiofiles.open(path, "wb")` para arquivos; `db.execute` apenas para SQL. São dois sistemas separados.

---

## Deterministic Test Approach (tests/test_docs.py)

O projeto já tem `pytest-asyncio>=0.23` e `asgi-lifespan>=2.1` em `requirements.txt` (L7-8). Padrão de teste com `asgi-lifespan` já deve existir ou pode ser montado como nos demais testes.

```python
# tests/test_docs.py — abordagem determinística
import io, pytest, pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from backend.main import app

@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    # Banco limpo por teste: apontar DB_PATH para tmp_path
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    # Apontar DATA_DOCS para tmp_path
    import backend.docs as docs_mod
    monkeypatch.setattr(docs_mod, "_DATA_DOCS", str(tmp_path / "documentos"))

    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Login com usuário seed (ou criar inline)
            yield c

async def test_ajuda_upsert_persists(client, token_operador):
    """PUT cria; PUT de novo atualiza sem mudar o id."""
    r1 = await client.put("/api/docs/ajuda/manutencao",
        json={"titulo": "Ajuda Manutenção", "conteudo_md": "# Olá\nTexto."},
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    assert r1.status_code == 200
    id1 = r1.json()["id"]
    r2 = await client.put("/api/docs/ajuda/manutencao",
        json={"titulo": "Atualizado", "conteudo_md": "# Novo"},
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    assert r2.json()["id"] == id1    # id preservado (ON CONFLICT DO UPDATE)
    assert r2.json()["titulo"] == "Atualizado"

async def test_upload_versao_increment(client, token_operador):
    """Upload v1 → v2: versão incrementa, v1 permanece."""
    # Criar doc
    r = await client.post("/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "POP Teste"},
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    doc_id = r.json()["id"]

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake content v1")
    fake_pdf.name = "pop.pdf"
    r1 = await client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files={"file": ("pop.pdf", fake_pdf, "application/pdf")},
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    assert r1.status_code == 201
    assert r1.json()["versao"] == 1

    fake_pdf2 = io.BytesIO(b"%PDF-1.4 fake content v2")
    r2 = await client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files={"file": ("pop_v2.pdf", fake_pdf2, "application/pdf")},
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    assert r2.json()["versao"] == 2

    # v1 ainda existe no banco
    rows = (await client.get(f"/api/docs/documentos/{doc_id}",
        headers={"Authorization": f"Bearer {token_operador}"})).json()
    versoes = rows["versoes"]
    assert len(versoes) == 2
    assert versoes[0]["versao"] == 1  # antiga preservada

async def test_download_returns_correct_file(client, token_operador, tmp_path):
    """Download da versão 1 retorna os bytes corretos."""
    # (criar doc e upload como acima)
    ...
    r = await client.get(
        f"/api/docs/documentos/{doc_id}/versoes/1/download",
        headers={"Authorization": f"Bearer {token_operador}"},
    )
    assert r.status_code == 200
    assert b"%PDF-1.4 fake content v1" in r.content

async def test_visualizador_escrita_403(client, token_visualizador):
    """Visualizador não pode criar doc nem fazer upload."""
    r = await client.post("/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "Negado"},
        headers={"Authorization": f"Bearer {token_visualizador}"},
    )
    assert r.status_code == 403

async def test_schema_idempotente(tmp_path):
    """db.init() chamado 2x não causa erro (CREATE TABLE IF NOT EXISTS)."""
    from backend.db_core import CoreDB
    import os
    os.environ["DB_PATH"] = str(tmp_path / "idem.db")
    db = CoreDB(str(tmp_path / "idem.db"))
    await db.init()
    await db.init()  # segunda chamada não deve levantar erro
```

**Nota sobre `token_operador` / `token_visualizador`:** usar fixtures que chamam `POST /api/auth/login` com usuários pré-criados no banco de teste (igual ao padrão de outros `tests/test_*.py` no projeto).

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| `INSERT OR REPLACE` para upsert | `INSERT ... ON CONFLICT DO UPDATE SET` (SQLite 3.24+) | Preserva PK original |
| `aiofiles.open` com `mode='wb'` direto | Mesmo padrão — sem mudança | Padrão estável |
| `FileResponse` path sem validação | `normpath` + `startswith(abspath)` | Previne path traversal |

**Sem deprecações relevantes para esta fase.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python-multipart` | UploadFile | Yes | 0.0.29 | — (sem fallback; necessário) |
| `aiofiles` | escrita assíncrona em disco | Yes | 25.1.0 | `open()` síncrono (aceitável para arquivos < 20 MB em servidor local) |
| `data/documentos/` dir | storage | Yes | — | criar com `os.makedirs` no startup |
| SQLite 3.24+ | `ON CONFLICT DO UPDATE` | Yes (Python 3.11 inclui SQLite 3.39+) | — | — |

**Missing dependencies with no fallback:** nenhuma.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | whitelist `ALLOWED_CATS`, whitelist `ALLOWED_EXTS`, max size check |
| V5.2 Sanitization | yes | `os.path.normpath` + prefix check no download; textContent (não innerHTML) no frontend |
| V4 Access Control | yes | `_require_auth` em todos os endpoints; `_require_escrita` nas escritas |
| V6 Cryptography | no | sem criptografia de arquivo (servidor local, rede naval isolada) |
| V2 Authentication | no (reutiliza auth existente) | Bearer token via sessoes table |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal em `categoria` ou `arquivo_nome` | Tampering | Whitelist `ALLOWED_CATS`; path gerado server-side com `doc_id+versao+ext` |
| Content-type spoofing | Spoofing | Validar extensão do `file.filename` (não o `Content-Type` do cliente) |
| Upload ilimitado (DoS) | Denial of Service | `file.read(MAX+1)` com limite 20 MB antes de gravar |
| XSS via conteúdo markdown | Tampering/Elevation | `textContent` no renderer; nunca `innerHTML` de `conteudo_md` |
| Acesso sem auth a arquivos | Information Disclosure | Todos os endpoints (GET/POST/PUT/download) exigem `_require_auth` |
| Escrita por visualizador | Elevation of Privilege | `_require_escrita` nas mutações (lança 403) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Renderer hand-rolled de 50 linhas cobre o escopo de textos de ajuda (sem necessidade de Markdown mais rico) | Markdown Rendering | Se gestores precisarem de tabelas ou links no markdown, o renderer precisará de extensão |
| A2 | `el()` de `pmoc-engine.js` não é exportado publicamente para uso fora do engine — deve ser copiado no IIFE de `erp-docs.js` | Pattern 7 | Se o engine exportar `el` via `window.engine`, copiar é redundante mas inofensivo |
| A3 | `data/documentos/` já existe no servidor de produção (visto por `ls` no dev) — sub-diretórios por categoria criados no primeiro upload | Environment | Se não existir, `os.makedirs` no handler cobre; sem risco |

**Se esta tabela tiver apenas 3 itens:** a maior parte desta pesquisa foi verificada diretamente nos arquivos do projeto.

---

## Open Questions

1. **Limite de extensões de upload**
   - O que sabemos: CONTEXT.md diz "definir um teto razoável". Lista sugerida: `.pdf`, `.docx`, `.xlsx`, `.odt`, `.ods`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.csv`.
   - O que está incerto: normas técnicas (DOC-03) podem chegar como `.zip` ou `.html` — o gestor deve confirmar.
   - Recomendação: implementar com a lista acima e expor via constante `ALLOWED_EXTS` facilmente editável.

2. **Conteúdo de `el()` em `erp-docs.js`**
   - Verificar se `window.engine` exporta `el` antes de criar cópia local. Grep em `pmoc-engine.js` mostra que `el` é local ao IIFE (não atribuído a `global.engine`). [VERIFIED: pmoc-engine.js L25 — `function el` é local, não exportada via `global.engine`]. Portanto: **copiar `el` no IIFE de `erp-docs.js`** é necessário.

---

## Sources

### Primary (HIGH confidence — verificado nos arquivos do projeto)
- `/home/luc/DEV_ERP/cmasm.erp/requirements.txt` — confirmação de `python-multipart`, `aiofiles`, `aiosqlite`, `pydantic`, `fastapi` com versões exatas
- `/home/luc/DEV_ERP/cmasm.erp/backend/main.py` L843-861 — `_require_auth` e `_require_escrita` (texto exato da função)
- `/home/luc/DEV_ERP/cmasm.erp/backend/main.py` L23-26, L329-332 — padrão de `include_router`
- `/home/luc/DEV_ERP/cmasm.erp/backend/db_core.py` L7-12 — `_SCHEMAS` list e onde adicionar `schema_docs.sql`
- `/home/luc/DEV_ERP/cmasm.erp/backend/manutencao.py` L22-44 — padrão `router`, `_db()`, `_require_auth` local via `sys.modules`
- `/home/luc/DEV_ERP/cmasm.erp/data/schema_manutencao.sql` — estilo DDL, comentários, convenções de indexação
- `/home/luc/DEV_ERP/cmasm.erp/assets/pmoc-engine.js` L25-40 — `el()` helper (local, não exportado)
- `/home/luc/DEV_ERP/cmasm.erp/cmasm_erp.html` L618-756 — sidebar `ni` pattern e onde inserir nav item
- `pip show python-multipart` — versão 0.0.29 em runtime
- `pip show aiofiles` — versão 25.1.0 em runtime

### Secondary (MEDIUM confidence)
- FastAPI docs sobre `UploadFile` e `File()` — padrão de upload com multipart [ASSUMED: baseado em conhecimento de treinamento + confirmação que a versão instalada (0.115.0) suporta o padrão descrito]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verificado em `requirements.txt` e `pip show`
- Architecture patterns: HIGH — derivados diretamente dos arquivos fonte do projeto
- Security pitfalls: HIGH — path traversal e content-type spoofing são padrões documentados
- Markdown renderer: MEDIUM — design hand-rolled suficiente para o escopo, mas não testado empiricamente neste projeto

**Research date:** 2026-06-29
**Valid until:** 2026-08-30 (stack estável; dependências pinadas)
