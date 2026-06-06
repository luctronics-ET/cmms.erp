# Spec — Zonas no GeoMap + melhorias do mapa

**Data:** 2026-06-06
**Arquivo alvo:** `cmasm-mapa.html` (+ `backend/main.py`, `data/schema_core.sql`)
**Status:** aprovado para implementação

## Objetivo

Adicionar **criação de zonas** (setores nomeados) ao `cmasm-mapa.html` e melhorar o
mapa com persistência no núcleo, medição de área/perímetro, edição de geometria,
rótulos e lista/filtro de zonas.

Decisões do usuário (brainstorming):

- **Zona** = polígono nomeado (setor). **Nome livre + cor manual** (sem tipos fixos).
- **Persistência** = API do núcleo (FastAPI `:8010`), nova tabela + endpoints.
- **Melhorias** = medir área/perímetro, editar vértices/mover, rótulo da zona no mapa,
  lista/filtro de zonas no painel direito.

## Abordagem escolhida (A)

Store unificado GeoJSON + camada de display própria.

- 1 tabela `mapa_features` guarda **tudo** (pontos, linhas, zonas) como geometria GeoJSON.
- **MapboxDraw vira só ferramenta** de desenho/edição. O **display de zonas** usa
  fontes/camadas MapLibre próprias (`zones-fill`, `zones-outline`, `zones-label`).
  Motivo: o código já avisa *"não customizar estilos do Draw — sistema hot/cold quebra
  com IDs externos"* (`cmasm-mapa.html` ~L361). Camada própria dá cor por-zona e rótulo
  livres, e o export atual já produz `FeatureCollection`.
- Pontos (símbolos) continuam como markers HTML (já é o padrão atual).

Rejeitadas: **B** (styling custom do Draw — risco de quebra, contra aviso do código);
**C** (tabela `zonas` separada — duplica CRUD/sync sem ganho; YAGNI).

## Schema — `data/schema_core.sql` (aditivo)

```sql
CREATE TABLE IF NOT EXISTS mapa_features (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL DEFAULT 'ponto',   -- ponto | linha | zona
  nome          TEXT DEFAULT '',                 -- tag/nome livre
  cor           TEXT DEFAULT '#00d4ff',          -- hex manual
  layer         TEXT DEFAULT 'anotacoes',
  status        TEXT DEFAULT 'operacional',
  tipo_simbolo  TEXT,                            -- id do símbolo (só ponto)
  descricao     TEXT DEFAULT '',
  props         TEXT DEFAULT '{}',               -- JSON livre (area_m2, perimetro_m, abbr...)
  geometry      TEXT NOT NULL,                   -- GeoJSON geometry (JSON serializado)
  criado_em     TEXT DEFAULT (datetime('now')),
  atualizado_em TEXT
);
```

- Tabela nova via `CREATE TABLE IF NOT EXISTS`; `db_core.py::_SCHEMAS` já carrega
  `schema_core.sql`. **Sem** bloco de migração em `db_core.py` (não é ALTER de tabela
  existente). Regra do projeto: aditivo, nunca DROP.

## Endpoints — `backend/main.py` (estilo colab: `payload: dict`, sem auth)

| Método | Rota | Ação |
|--------|------|------|
| GET    | `/api/mapa/features`        | lista tudo como `FeatureCollection` |
| POST   | `/api/mapa/features`        | cria (gera id se faltar) → retorna feature |
| PUT    | `/api/mapa/features/{id}`   | atualiza geometria/props/cor/nome/status; seta `atualizado_em` |
| DELETE | `/api/mapa/features/{id}`   | remove (404 se não existir) |

Formato de resposta GET:

```json
{ "type": "FeatureCollection",
  "features": [
    { "type":"Feature",
      "id":"<id>",
      "geometry": { ...geojson... },
      "properties": { "kind","nome","cor","layer","status","tipo_simbolo",
                      "descricao","props":{...},"criado_em","atualizado_em" } }
  ] }
```

- POST/PUT recebem `geometry` (objeto GeoJSON) + campos de `properties`; o backend
  serializa `geometry` e `props` com `json.dumps` antes do INSERT/UPDATE, e faz
  `json.loads` ao devolver.
- DELETE inexistente → `HTTPException(404, "Feature não encontrada")`.

## Fluxo frontend — `cmasm-mapa.html`

### Config
- Constante `const API_BASE = 'http://localhost:8010';` no topo do `<script>`.
- Helpers `apiGet/apiPost/apiPut/apiDelete` finos sobre `fetch`, com try/catch →
  toast vermelho em falha (degradação graciosa, mantém em memória).

### Carregar
- Em `map.on('load')`: `GET /api/mapa/features` → reconstrói `elements[]`, markers de
  ponto, e a fonte `zones` (features kind=zona). Falha → toast, app segue vazio/memória.

### Criar zona
- Botão **"+ ZONA"** (header ou painel esquerdo) → `Draw.changeMode('draw_polygon')`.
- `draw.create` com `geometry.type==='Polygon'`:
  1. cria objeto zona em `elements[]` (kind='zona', nome='', cor padrão editável);
  2. **remove a feature do Draw** (`Draw.delete`) — display próprio assume;
  3. adiciona à fonte `zones` (com cor/nome nas props);
  4. calcula área/perímetro (turf);
  5. `POST` → guarda id retornado;
  6. seleciona zona e abre painel de props (campo nome + color picker).

### Criar ponto / linha
- Como hoje (`click` insere símbolo; `draw.create` LineString). Acrescentar `POST`
  ao final de cada criação.

### Editar zona (vértices/mover)
- Selecionar zona (clique no `zones-fill` ou na lista) → botão **"✎ EDITAR"**:
  - carrega a geometria de volta no Draw (`Draw.add` + `Draw.changeMode('direct_select', {featureId})`);
  - esconde temporariamente a zona da fonte própria;
  - `draw.update` → recalcula área/perímetro;
  - ao **"✔ CONCLUIR"**: copia geometria do Draw → fonte `zones`, `Draw.delete`, `PUT`.

### Salvar / Deletar
- `saveEl()` → `PUT` (nome, cor, status, descrição, geometria).
- `deleteEl()` → `DELETE` + remove de markers/fonte/Draw.
- Arrastar/editar com debounce (~400ms) antes do PUT para não floodar.

### Color picker
- Campo `<input type="color">` no painel de props para zonas (cor manual).
  Alterar cor → atualiza paint da fonte `zones` (data-driven: `['get','cor']`).

## Área / perímetro

- Adicionar `@turf/turf` via CDN (`<script src="https://unpkg.com/@turf/turf@6/turf.min.js">`).
- `area_m2 = turf.area(featurePolygon)`; `perimetro_m = turf.length(turf.polygonToLine(poly), {units:'meters'})`.
- Exibidos read-only no painel de props e salvos em `props` (`area_m2`, `perimetro_m`).
- Formatar: área em m² (ou ha se > 10000 m²), perímetro em m.

## Melhorias (as 4)

1. **Medir** — seção "Área/perímetro" acima.
2. **Editar vértices/mover** — `direct_select` do Draw + `draw.update` (fluxo de edição acima).
3. **Rótulo no mapa** — camada `zones-label` (`type:'symbol'`) com `text-field: ['get','nome']`,
   ancorada no `turf.centroid` de cada zona (fonte de pontos `zone-labels` atualizada junto).
4. **Lista/filtro** — zonas entram em `renderElList()` com dot da cor; clique →
   `map.fitBounds(turf.bbox(zona))` + highlight (aumenta `line-width` da zona selecionada
   via feature-state ou filtro).

## Camadas MapLibre adicionadas

- `zones` (source geojson) → `zones-fill` (fill-color `['get','cor']`, fill-opacity ~0.18),
  `zones-outline` (line-color `['get','cor']`, line-width 2; selecionada → 3.5).
- `zone-labels` (source geojson de centróides) → `zones-label` (symbol text).
- Respeitam `LAYERS[layer].visible/opacity` (zonas usam o layer escolhido).

## Edge cases

- Migração aditiva, `IF NOT EXISTS`, nunca DROP (regra do projeto). ✔
- Polígono < 3 pontos: MapboxDraw já barra.
- Backend offline: toast vermelho, app opera em memória, sem persistir.
- `geometry`/`props` sempre `json.dumps`/`json.loads` na fronteira do backend.
- IDs: backend gera `uuid4()[:8]` se `payload` não trouxer (estilo colab).
- Export GeoJSON existente continua funcionando (agora inclui zonas da fonte própria).

## Fora de escopo (YAGNI)

- Agrupar/contar ativos dentro de zona; vínculo com OS/PMOC (usuário não pediu agora).
- Tipos fixos de setor (escolhido: nome/cor livre).
- Snap de vértices; import de .geojson.
- Autenticação nos endpoints de mapa (colab também é aberto; manter consistência).
