/**
 * erp-docs.js — Módulo de Documentos e Ajuda Contextual (xCMASM ERP)
 * Fase 08 — Ajuda e Documentação (DOC-01, DOC-02, DOC-03)
 *
 * Expõe window.erpDocs com:
 *   - mount()         : popula #page-documentos
 *   - openAjuda(chave): abre o drawer de ajuda contextual
 *   - closeAjuda()    : fecha o drawer
 */
(function () {
  'use strict';

  // ── el() helper (cópia local — pmoc-engine.js não exporta el publicamente) ─
  function el(tag, props, children) {
    const e = document.createElement(tag);
    if (props) {
      for (const [k, v] of Object.entries(props)) {
        if (k === 'style' && typeof v === 'object') {
          Object.assign(e.style, v);
        } else if (k.startsWith('on') && typeof v === 'function') {
          e.addEventListener(k.slice(2).toLowerCase(), v);
        } else if (k === 'class') {
          e.className = v;
        } else if (k === 'data') {
          for (const [dk, dv] of Object.entries(v)) {
            e.dataset[dk] = dv;
          }
        } else {
          e.setAttribute(k, v);
        }
      }
    }
    if (children) {
      for (const c of [].concat(children)) {
        if (c == null) continue;
        e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      }
    }
    return e;
  }

  // ── API base + auth ────────────────────────────────────────────────────────
  function apiBase() {
    return (window.XCMASM_API_BASE || 'http://localhost:8010').replace(/\/$/, '');
  }

  function getToken() {
    return localStorage.getItem('xcmasm_token') || '';
  }

  function authHeaders(extra) {
    return Object.assign({ 'Authorization': 'Bearer ' + getToken() }, extra || {});
  }

  async function authFetch(url, opts) {
    const options = opts || {};
    options.headers = Object.assign(authHeaders(), options.headers || {});
    return fetch(apiBase() + url, options);
  }

  // ── Papel do utilizador ────────────────────────────────────────────────────
  function getUserRole() {
    try {
      const me = JSON.parse(localStorage.getItem('xcmasm_me') || 'null');
      return (me && me.role) ? me.role : 'visitante';
    } catch (_) { return 'visitante'; }
  }

  function canWrite() {
    const role = getUserRole();
    // 'visitante' = unauthenticated/unparseable; 'visualizador' = DB read-only role (WR-01)
    return role !== 'visitante' && role !== 'visualizador';
  }

  // ── Constantes ─────────────────────────────────────────────────────────────
  const CATEGORIAS = [
    { value: '', label: 'Todas' },
    { value: 'geral', label: 'Geral' },
    { value: 'refrigeracao', label: 'Refrigeração' },
    { value: 'predial', label: 'Predial' },
    { value: 'paiois', label: 'Paióis' },
    { value: 'transportes', label: 'Transportes' },
    { value: 'grama', label: 'Grama' },
    { value: 'eletrica', label: 'Elétrica' },
    { value: 'calibracao', label: 'Calibração' },
  ];

  const TIPOS = [
    { value: '', label: 'Todos os tipos' },
    { value: 'modelo', label: 'Modelo' },
    { value: 'formulario', label: 'Formulário' },
    { value: 'guia', label: 'Guia' },
    { value: 'norma', label: 'Norma' },
  ];

  const TIPO_COLORS = {
    modelo:    { bg: 'rgba(0,180,216,.18)', color: '#00b4d8' },
    formulario:{ bg: 'rgba(34,197,94,.18)', color: '#22c55e' },
    guia:      { bg: 'rgba(245,158,11,.18)', color: '#f59e0b' },
    norma:     { bg: 'rgba(239,68,68,.18)', color: '#ef4444' },
  };

  // ── Safe Markdown Renderer (DOC-01 — ajuda contextual) ─────────────────────
  // NUNCA usa innerHTML de conteúdo não-confiável. Apenas textContent + DOM.

  function _applyInline(parent, text) {
    // Tokens: **bold**, *italic*, `code`  (ordem importa: ** antes de *)
    const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
    let last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) {
        parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      }
      let node;
      if (m[0].startsWith('**'))    { node = document.createElement('strong'); node.textContent = m[2]; }
      else if (m[0].startsWith('*')){ node = document.createElement('em');     node.textContent = m[3]; }
      else                          { node = document.createElement('code');   node.textContent = m[4]; }
      parent.appendChild(node);
      last = m.index + m[0].length;
    }
    if (last < text.length) {
      parent.appendChild(document.createTextNode(text.slice(last)));
    }
  }

  function renderMdSafe(md, container) {
    container.innerHTML = ''; // limpar container com string vazia é seguro
    const lines = (md || '').split('\n');
    let ul = null;

    for (const raw of lines) {
      const line = raw.trimEnd();

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

  // ── Funções utilitárias de UI ──────────────────────────────────────────────
  function showMsg(container, text, isError) {
    const p = el('p', { style: { color: isError ? 'var(--red)' : 'var(--green)', padding: '8px 0', margin: '0' } });
    p.textContent = text;
    container.insertBefore(p, container.firstChild);
    setTimeout(() => { if (p.parentNode) p.parentNode.removeChild(p); }, 4000);
  }

  function tipoBadge(tipo) {
    const cfg = TIPO_COLORS[tipo] || { bg: 'rgba(255,255,255,.1)', color: '#ccc' };
    const span = el('span', {
      style: {
        display: 'inline-block',
        padding: '1px 7px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: '600',
        background: cfg.bg,
        color: cfg.color,
        textTransform: 'capitalize',
      }
    });
    span.textContent = tipo || '—';
    return span;
  }

  function buildSelect(opts, currentVal, onChange) {
    const sel = el('select', { style: { background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '4px 8px' } });
    for (const opt of opts) {
      const o = el('option', { value: opt.value });
      o.textContent = opt.label;
      if (opt.value === currentVal) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener('change', () => onChange(sel.value));
    return sel;
  }

  // Extensões aceitas no upload/import (espelha ALLOWED_EXTS do backend).
  const ACCEPT_EXTS = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.png,.jpg,.jpeg,.txt,.md,.csv';

  // ── Estado da página Documentos ────────────────────────────────────────────
  const docsState = {
    pastas: [],      // lista plana {id, nome, parent_id, caminho}
    pastaId: null,   // pasta selecionada (null = todas)
    tipo: '',
    q: '',
    docs: [],
  };

  let docsRoot = null;
  let listPaneEl = null;  // painel direito (lista de documentos)

  // ── Pastas: carregar + montar árvore ───────────────────────────────────────
  async function loadPastas() {
    try {
      const r = await authFetch('/api/docs/pastas');
      docsState.pastas = r.ok ? await r.json() : [];
    } catch (_) {
      docsState.pastas = [];
    }
  }

  function buildPastaTree(flat) {
    const byId = {}, roots = [];
    flat.forEach(p => { byId[p.id] = Object.assign({ children: [] }, p); });
    flat.forEach(p => {
      if (p.parent_id != null && byId[p.parent_id]) byId[p.parent_id].children.push(byId[p.id]);
      else roots.push(byId[p.id]);
    });
    return roots;
  }

  async function criarPasta(parentId) {
    const nome = prompt('Nome da nova pasta:');
    if (!nome || !nome.trim()) return;
    try {
      const r = await authFetch('/api/docs/pastas', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome: nome.trim(), parent_id: parentId != null ? parentId : null }),
      });
      if (!r.ok) { const e = await r.json().catch(() => ({ detail: 'Erro ' + r.status })); throw new Error(e.detail || r.status); }
      await loadPastas();
      render();
    } catch (e) {
      if (docsRoot) showMsg(docsRoot, 'Erro ao criar pasta: ' + e.message, true);
    }
  }

  async function removerPasta(id) {
    if (!confirm('Remover esta pasta? (precisa estar vazia)')) return;
    try {
      const r = await authFetch('/api/docs/pastas/' + id, { method: 'DELETE' });
      if (!r.ok) { const e = await r.json().catch(() => ({ detail: 'Erro ' + r.status })); throw new Error(e.detail || r.status); }
      if (docsState.pastaId === id) docsState.pastaId = null;
      await loadPastas();
      render();
    } catch (e) {
      if (docsRoot) showMsg(docsRoot, 'Erro ao remover pasta: ' + e.message, true);
    }
  }

  function selectFolder(id) {
    docsState.pastaId = id;
    render();        // atualiza destaque da árvore
    loadDocs();      // recarrega painel direito
  }

  // Import direto: para cada arquivo escolhido, cria o documento (título = nome do
  // arquivo) na pasta atual e sobe o arquivo como versão 1 — tudo numa ação.
  async function importarArquivos(files) {
    const arr = Array.from(files || []);
    if (!arr.length) return;
    const pid = docsState.pastaId;
    let ok = 0; const erros = [];
    if (docsRoot) showMsg(docsRoot, 'Importando ' + arr.length + ' arquivo(s)…', false);
    for (const f of arr) {
      try {
        const titulo = f.name.replace(/\.[^.]+$/, '') || f.name;
        const r = await authFetch('/api/docs/documentos', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ titulo, tipo: 'modelo', pasta_id: pid != null ? pid : null }),
        });
        if (!r.ok) { const e = await r.json().catch(() => ({ detail: 'Erro ' + r.status })); throw new Error(e.detail || r.status); }
        const doc = await r.json();
        const fd = new FormData(); fd.append('file', f);
        const up = await fetch(apiBase() + '/api/docs/documentos/' + doc.id + '/versoes', {
          method: 'POST', headers: { 'Authorization': 'Bearer ' + getToken() }, body: fd,
        });
        if (!up.ok) { const e = await up.json().catch(() => ({ detail: 'Erro ' + up.status })); throw new Error(e.detail || up.status); }
        ok++;
      } catch (e) {
        erros.push(f.name + ': ' + e.message);
      }
    }
    await loadPastas();
    render();
    loadDocs();
    if (docsRoot) {
      const msg = ok + ' arquivo(s) importado(s)' + (erros.length ? ' · ' + erros.length + ' com erro (' + erros[0] + ')' : '');
      showMsg(docsRoot, msg, erros.length > 0);
    }
  }

  function renderTreeNode(node, depth, container) {
    const sel = docsState.pastaId === node.id;
    const row = el('div', { style: {
      display: 'flex', alignItems: 'center', gap: '2px',
      padding: '4px 6px', paddingLeft: (6 + depth * 14) + 'px',
      borderRadius: '4px', cursor: 'pointer', fontSize: '13px',
      background: sel ? 'var(--bg3, rgba(0,180,216,.12))' : 'transparent',
      color: sel ? 'var(--acc)' : 'var(--text1)',
    } });
    const label = el('span', { style: { flex: '1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } });
    label.textContent = '📁 ' + node.nome;
    label.addEventListener('click', () => selectFolder(node.id));
    row.appendChild(label);
    if (canWrite()) {
      const add = el('span', { title: 'Nova subpasta', style: { cursor: 'pointer', opacity: '.55', padding: '0 4px' } });
      add.textContent = '＋';
      add.addEventListener('click', (e) => { e.stopPropagation(); criarPasta(node.id); });
      row.appendChild(add);
      const del = el('span', { title: 'Remover pasta', style: { cursor: 'pointer', opacity: '.55', padding: '0 4px' } });
      del.textContent = '🗑';
      del.addEventListener('click', (e) => { e.stopPropagation(); removerPasta(node.id); });
      row.appendChild(del);
    }
    container.appendChild(row);
    node.children.forEach(c => renderTreeNode(c, depth + 1, container));
  }

  // ── Documentos: carregar lista (painel direito) ────────────────────────────
  async function loadDocs() {
    const params = new URLSearchParams();
    if (docsState.pastaId != null) params.set('pasta_id', docsState.pastaId);
    if (docsState.tipo)            params.set('tipo', docsState.tipo);
    if (docsState.q)               params.set('q', docsState.q);
    const url = '/api/docs/documentos' + (params.toString() ? '?' + params : '');
    try {
      const r = await authFetch(url);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      docsState.docs = await r.json();
    } catch (e) {
      docsState.docs = [];
      if (docsRoot) showMsg(docsRoot, 'Erro ao carregar documentos: ' + e.message, true);
    }
    renderList();
  }

  // ── Shell de dois painéis (árvore | lista) ─────────────────────────────────
  function render() {
    if (!docsRoot) return;
    docsRoot.innerHTML = '';

    // Sem token de servidor → módulo de documentos não funciona (precisa de backend).
    if (!getToken()) {
      const warn = el('div', { style: { padding: '14px 16px', marginBottom: '14px', borderRadius: '6px', background: 'rgba(245,158,11,.12)', border: '1px solid var(--amber, #f59e0b)', color: 'var(--text1)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' } });
      const txt = el('span', { style: { flex: '1', minWidth: '220px' } });
      txt.textContent = 'Sessão do servidor indisponível. Clique em "Reconectar" para ativar o repositório de documentos.';
      warn.appendChild(txt);
      const cur = (typeof window.xcmasmCurrentUser === 'function') ? window.xcmasmCurrentUser() : null;
      const btnReconn = el('button', { class: 'btn btn-primary btn-sm' });
      btnReconn.textContent = 'Reconectar ao servidor';
      btnReconn.addEventListener('click', async () => {
        if (!cur || cur.visitante) { showMsg(docsRoot, 'Faça login no ERP (não como visitante) para usar o servidor.', true); return; }
        const pw = prompt('Senha de ' + cur.nome + ' para conectar ao servidor:');
        if (pw == null) return;
        btnReconn.disabled = true; btnReconn.textContent = 'Conectando…';
        const ok = (typeof window.xcmasmReconnect === 'function') ? await window.xcmasmReconnect(pw) : false;
        if (ok) { mount(); }
        else {
          btnReconn.disabled = false; btnReconn.textContent = 'Reconectar ao servidor';
          showMsg(docsRoot, 'Não foi possível conectar (senha incorreta ou backend offline).', true);
        }
      });
      warn.appendChild(btnReconn);
      docsRoot.appendChild(warn);
    }

    // Cabeçalho
    const hdr = el('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' } });
    const title = el('h2', { style: { margin: '0', color: 'var(--text1)' } });
    title.textContent = 'Repositório de Documentos';
    hdr.appendChild(title);
    if (canWrite()) {
      const acts = el('div', { style: { display: 'flex', gap: '8px' } });

      // Import direto — INPUT FILE VISÍVEL (botão nativo do navegador). Sem JS .click(),
      // sem display:none: o controle nativo SEMPRE abre o diálogo em qualquer navegador.
      const impWrap = el('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0,180,216,.12)', border: '1px solid var(--acc, #00b4d8)', borderRadius: '6px', padding: '4px 8px' } });
      const impLbl = el('span', { style: { color: 'var(--acc, #00b4d8)', fontSize: '12px', fontWeight: '600', whiteSpace: 'nowrap' } });
      impLbl.textContent = '⬆ Importar:';
      const inputImport = el('input', { type: 'file', multiple: '', title: 'Selecionar arquivo(s) para importar', style: { color: 'var(--text1)', fontSize: '12px', maxWidth: '210px' } });
      inputImport.accept = ACCEPT_EXTS;
      // copia os File ANTES de limpar value (FileList é vivo — limpar esvazia a referência)
      inputImport.addEventListener('change', () => { const fs = Array.from(inputImport.files); inputImport.value = ''; importarArquivos(fs); });
      impWrap.appendChild(impLbl);
      impWrap.appendChild(inputImport);
      acts.appendChild(impWrap);

      const btnNovo = el('button', { class: 'btn btn-secondary btn-sm', onclick: () => renderNovoDocForm() });
      btnNovo.textContent = '+ Documento';
      acts.appendChild(btnNovo);
      const btnPasta = el('button', { class: 'btn btn-secondary btn-sm', onclick: () => criarPasta(docsState.pastaId) });
      btnPasta.textContent = '+ Pasta';
      acts.appendChild(btnPasta);
      hdr.appendChild(acts);
    }
    docsRoot.appendChild(hdr);

    // Toolbar: busca + tipo
    const tb = el('div', { style: { display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap', alignItems: 'center' } });
    const search = el('input', {
      type: 'search', placeholder: '🔍  Buscar por título ou descrição…',
      style: { flex: '1', minWidth: '220px', background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '7px 10px' },
    });
    search.value = docsState.q;
    search.addEventListener('input', () => { docsState.q = search.value.trim(); loadDocs(); });
    tb.appendChild(search);
    tb.appendChild(buildSelect(TIPOS, docsState.tipo, val => { docsState.tipo = val; loadDocs(); }));
    docsRoot.appendChild(tb);

    // Layout dois painéis
    const grid = el('div', { style: { display: 'flex', gap: '16px', alignItems: 'flex-start' } });

    // Painel esquerdo: árvore de pastas
    const aside = el('div', { style: { flex: '0 0 240px', maxWidth: '240px', borderRight: '1px solid var(--border)', paddingRight: '12px' } });
    const rootRow = el('div', { style: {
      padding: '4px 6px', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: '600',
      background: docsState.pastaId == null ? 'var(--bg3, rgba(0,180,216,.12))' : 'transparent',
      color: docsState.pastaId == null ? 'var(--acc)' : 'var(--text1)',
    } });
    rootRow.textContent = '🗂  Todos os documentos';
    rootRow.addEventListener('click', () => selectFolder(null));
    aside.appendChild(rootRow);
    const treeBox = el('div', { style: { marginTop: '4px' } });
    buildPastaTree(docsState.pastas).forEach(n => renderTreeNode(n, 0, treeBox));
    aside.appendChild(treeBox);
    grid.appendChild(aside);

    // Painel direito: lista de documentos
    listPaneEl = el('div', { style: { flex: '1', minWidth: '0' } });
    grid.appendChild(listPaneEl);
    docsRoot.appendChild(grid);

    renderList();
  }

  function renderList() {
    if (!listPaneEl) return;
    listPaneEl.innerHTML = '';

    if (!docsState.docs.length) {
      const empty = el('p', { style: { color: 'var(--text2)', padding: '24px 0' } });
      empty.textContent = docsState.q
        ? 'Nenhum documento corresponde à busca.'
        : 'Nenhum documento nesta pasta.';
      listPaneEl.appendChild(empty);
      return;
    }

    const table = el('table', { style: { width: '100%', borderCollapse: 'collapse' } });
    const thead = el('thead');
    const tr = el('tr');
    for (const h of ['Título', 'Categoria', 'Tipo', 'Última versão', 'Ações']) {
      const th = el('th', { style: { textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid var(--border)', color: 'var(--text2)', fontWeight: '600', fontSize: '12px', textTransform: 'uppercase' } });
      th.textContent = h;
      tr.appendChild(th);
    }
    thead.appendChild(tr);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const doc of docsState.docs) {
      const row = el('tr', { style: { borderBottom: '1px solid rgba(255,255,255,.05)' } });

      const tdTitulo = el('td', { style: { padding: '10px 10px', color: 'var(--text1)', fontWeight: '500' } });
      tdTitulo.textContent = doc.titulo || '—';
      row.appendChild(tdTitulo);

      const tdCat = el('td', { style: { padding: '10px 10px', color: 'var(--text2)', fontSize: '13px' } });
      tdCat.textContent = doc.categoria || '—';
      row.appendChild(tdCat);

      const tdTipo = el('td', { style: { padding: '10px 10px' } });
      tdTipo.appendChild(tipoBadge(doc.tipo));
      row.appendChild(tdTipo);

      const tdVersao = el('td', { style: { padding: '10px 10px', color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: '13px' } });
      tdVersao.textContent = doc.ultima_versao != null && doc.ultima_versao > 0 ? 'v' + doc.ultima_versao : '—';
      if (doc.ultimo_arquivo_nome) tdVersao.title = doc.ultimo_arquivo_nome;
      row.appendChild(tdVersao);

      const tdAcoes = el('td', { style: { padding: '10px 10px' } });
      const acoes = el('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap' } });

      const btnHist = el('button', { class: 'btn btn-ghost btn-sm', onclick: () => renderHistorico(doc) });
      btnHist.textContent = 'Histórico';
      acoes.appendChild(btnHist);

      if (canWrite()) {
        // input visualmente oculto (NÃO display:none — alguns navegadores não disparam
        // o diálogo via label se for display:none). O clique no <label> abre nativamente.
        const inputFile = el('input', { type: 'file', style: { position: 'absolute', width: '1px', height: '1px', padding: '0', margin: '-1px', overflow: 'hidden', clip: 'rect(0,0,0,0)', border: '0' } });
        inputFile.accept = ACCEPT_EXTS;
        inputFile.addEventListener('change', () => {
          if (inputFile.files && inputFile.files[0]) uploadVersao(doc.id, inputFile.files[0], row);
        });
        const lblUpload = el('label', { class: 'btn btn-secondary btn-sm', style: { cursor: 'pointer' } });
        lblUpload.textContent = 'Importar versão';
        lblUpload.appendChild(inputFile);
        acoes.appendChild(lblUpload);
      }

      if (doc.ultima_versao != null && doc.ultima_versao > 0) {
        const btnBaixar = el('button', {
          class: 'btn btn-ghost btn-sm',
          onclick: () => downloadVersao(doc.id, doc.ultima_versao, doc.ultimo_arquivo_nome || ('doc_' + doc.id + '_v' + doc.ultima_versao)),
        });
        btnBaixar.textContent = 'Exportar';
        acoes.appendChild(btnBaixar);
      }

      tdAcoes.appendChild(acoes);
      row.appendChild(tdAcoes);
      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    listPaneEl.appendChild(table);
  }

  // ── Upload de versão ───────────────────────────────────────────────────────
  async function uploadVersao(docId, file, rowEl) {
    const formData = new FormData();
    formData.append('file', file);

    // Feedback visual no row
    const msg = el('span', { style: { color: 'var(--acc)', fontSize: '12px', marginLeft: '4px' } });
    msg.textContent = 'Enviando…';
    if (rowEl) rowEl.querySelector('td:last-child div') && rowEl.querySelector('td:last-child div').appendChild(msg);

    try {
      const r = await fetch(apiBase() + '/api/docs/documentos/' + docId + '/versoes', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + getToken() },
        body: formData,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: 'Erro ' + r.status }));
        throw new Error(err.detail || 'HTTP ' + r.status);
      }
      await r.json();
      if (msg.parentNode) msg.parentNode.removeChild(msg);
      loadDocs();
    } catch (e) {
      if (msg.parentNode) msg.parentNode.removeChild(msg);
      if (docsRoot) showMsg(docsRoot, 'Upload falhou: ' + e.message, true);
    }
  }

  // ── Download de versão ─────────────────────────────────────────────────────
  async function downloadVersao(docId, versao, nomeArquivo) {
    try {
      const r = await authFetch('/api/docs/documentos/' + docId + '/versoes/' + versao + '/download');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // textContent (seguro) — o nomeArquivo vem dos metadados do doc, não innerHTML
      a.download = nomeArquivo || ('documento_' + docId + '_v' + versao);
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      if (docsRoot) showMsg(docsRoot, 'Download falhou: ' + e.message, true);
    }
  }

  // ── Histórico de versões ───────────────────────────────────────────────────
  async function renderHistorico(doc) {
    if (!docsRoot) return;
    docsRoot.innerHTML = '';

    const btnVoltar = el('button', { class: 'btn btn-ghost btn-sm', onclick: () => { render(); loadDocs(); } });
    btnVoltar.textContent = '← Voltar';
    docsRoot.appendChild(btnVoltar);

    const titulo = el('h2', { style: { margin: '12px 0 4px', color: 'var(--text1)' } });
    titulo.textContent = '';
    titulo.appendChild(document.createTextNode('Histórico: '));
    const strong = el('strong');
    strong.textContent = doc.titulo;
    titulo.appendChild(strong);
    docsRoot.appendChild(titulo);

    const sub = el('p', { style: { color: 'var(--text2)', margin: '0 0 16px', fontSize: '13px' } });
    sub.textContent = 'Categoria: ' + (doc.categoria || '—') + ' · Tipo: ';
    sub.appendChild(tipoBadge(doc.tipo));
    docsRoot.appendChild(sub);

    // Carregar detalhes do documento com versões
    let versoes = [];
    try {
      const r = await authFetch('/api/docs/documentos/' + doc.id);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      versoes = data.versoes || [];
    } catch (e) {
      showMsg(docsRoot, 'Erro ao carregar histórico: ' + e.message, true);
      return;
    }

    if (!versoes.length) {
      const empty = el('p', { style: { color: 'var(--text2)' } });
      empty.textContent = 'Nenhuma versão cadastrada.';
      docsRoot.appendChild(empty);
      return;
    }

    const table = el('table', { style: { width: '100%', borderCollapse: 'collapse' } });
    const thead = el('thead');
    const tr = el('tr');
    for (const h of ['Versão', 'Arquivo', 'Tamanho', 'Autor', 'Data', 'Ações']) {
      const th = el('th', { style: { textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid var(--border)', color: 'var(--text2)', fontSize: '12px', textTransform: 'uppercase' } });
      th.textContent = h;
      tr.appendChild(th);
    }
    thead.appendChild(tr);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const v of versoes) {
      const row = el('tr', { style: { borderBottom: '1px solid rgba(255,255,255,.05)' } });

      const tdV = el('td', { style: { padding: '9px 10px', fontFamily: 'var(--mono)', color: 'var(--acc)' } });
      tdV.textContent = 'v' + v.versao;
      row.appendChild(tdV);

      const tdArq = el('td', { style: { padding: '9px 10px', color: 'var(--text1)', fontSize: '13px', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } });
      tdArq.textContent = v.arquivo_nome || '—';
      tdArq.title = v.arquivo_nome || '';
      row.appendChild(tdArq);

      const tdTam = el('td', { style: { padding: '9px 10px', color: 'var(--text2)', fontSize: '12px' } });
      tdTam.textContent = v.tamanho != null ? _formatBytes(v.tamanho) : '—';
      row.appendChild(tdTam);

      const tdAutor = el('td', { style: { padding: '9px 10px', color: 'var(--text2)', fontSize: '13px' } });
      tdAutor.textContent = v.autor || '—';
      row.appendChild(tdAutor);

      const tdData = el('td', { style: { padding: '9px 10px', color: 'var(--text2)', fontSize: '12px', fontFamily: 'var(--mono)' } });
      tdData.textContent = v.data ? v.data.slice(0, 16).replace('T', ' ') : '—';
      row.appendChild(tdData);

      const tdAcoes = el('td', { style: { padding: '9px 10px' } });
      const btnBaixar = el('button', {
        class: 'btn btn-ghost btn-sm',
        onclick: () => downloadVersao(doc.id, v.versao, v.arquivo_nome),
      });
      btnBaixar.textContent = 'Baixar';
      tdAcoes.appendChild(btnBaixar);
      row.appendChild(tdAcoes);

      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    docsRoot.appendChild(table);
  }

  function _formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  // ── Novo documento: formulário ─────────────────────────────────────────────
  function renderNovoDocForm() {
    if (!docsRoot) return;
    docsRoot.innerHTML = '';

    const btnVoltar = el('button', { class: 'btn btn-ghost btn-sm', onclick: () => { render(); loadDocs(); } });
    btnVoltar.textContent = '← Voltar';
    docsRoot.appendChild(btnVoltar);

    const titulo = el('h2', { style: { margin: '12px 0 16px', color: 'var(--text1)' } });
    titulo.textContent = 'Novo Documento';
    docsRoot.appendChild(titulo);

    const form = el('form', { style: { maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: '12px' } });

    // Título
    const lblTitulo = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblTitulo.textContent = 'Título';
    const inputTitulo = el('input', {
      type: 'text', required: '', placeholder: 'Ex: POP-001 Manutenção Preventiva',
      style: { width: '100%', background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '7px 10px', boxSizing: 'border-box' }
    });
    form.appendChild(lblTitulo);
    form.appendChild(inputTitulo);

    // Descrição
    const lblDesc = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblDesc.textContent = 'Descrição (opcional)';
    const inputDesc = el('textarea', {
      style: { width: '100%', background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '7px 10px', minHeight: '64px', resize: 'vertical', boxSizing: 'border-box' }
    });
    form.appendChild(lblDesc);
    form.appendChild(inputDesc);

    // Categoria
    const lblCat = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblCat.textContent = 'Categoria';
    const selCat = buildSelect(CATEGORIAS.slice(1), docsState.categoria || 'geral', () => {});
    form.appendChild(lblCat);
    form.appendChild(selCat);

    // Tipo
    const lblTipo = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblTipo.textContent = 'Tipo';
    const selTipo = buildSelect(TIPOS.slice(1), docsState.tipo || 'modelo', () => {});
    form.appendChild(lblTipo);
    form.appendChild(selTipo);

    // Pasta (árvore) — opções a partir do caminho materializado
    const lblPasta = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblPasta.textContent = 'Pasta';
    const pastaOpts = [{ value: '', label: '(Sem pasta)' }].concat(
      docsState.pastas.map(p => ({ value: String(p.id), label: p.caminho }))
    );
    const selPasta = buildSelect(pastaOpts, docsState.pastaId != null ? String(docsState.pastaId) : '', () => {});
    form.appendChild(lblPasta);
    form.appendChild(selPasta);

    // Arquivo — importa direto como versão 1 ao criar (PDF, DOC, XLS, PPT…)
    const lblFile = el('label', { style: { color: 'var(--text2)', fontSize: '13px' } });
    lblFile.textContent = 'Arquivo (PDF, DOC, XLS, PPT…)';
    const inputFile = el('input', {
      type: 'file',
      style: { width: '100%', background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '7px 10px', boxSizing: 'border-box' },
    });
    inputFile.accept = ACCEPT_EXTS;
    // Se o título estiver vazio, pré-preenche com o nome do arquivo (sem extensão)
    inputFile.addEventListener('change', () => {
      const f = inputFile.files && inputFile.files[0];
      if (f && !inputTitulo.value.trim()) inputTitulo.value = f.name.replace(/\.[^.]+$/, '');
    });
    form.appendChild(lblFile);
    form.appendChild(inputFile);

    // Botões
    const rowBtns = el('div', { style: { display: 'flex', gap: '8px', marginTop: '4px' } });

    const btnCancelar = el('button', { class: 'btn btn-ghost', type: 'button', onclick: () => { render(); loadDocs(); } });
    btnCancelar.textContent = 'Cancelar';

    const btnSalvar = el('button', { class: 'btn btn-primary', type: 'submit' });
    btnSalvar.textContent = 'Criar e importar';

    rowBtns.appendChild(btnCancelar);
    rowBtns.appendChild(btnSalvar);
    form.appendChild(rowBtns);

    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const file = inputFile.files && inputFile.files[0];
      if (!file) { showMsg(form, 'Selecione um arquivo para importar.', true); inputFile.focus(); return; }
      const tituloVal = inputTitulo.value.trim() || file.name.replace(/\.[^.]+$/, '');
      if (!tituloVal) { inputTitulo.focus(); return; }
      btnSalvar.disabled = true;
      btnSalvar.textContent = 'Salvando…';
      try {
        const r = await authFetch('/api/docs/documentos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            titulo: tituloVal,
            descricao: inputDesc.value.trim() || null,
            categoria: selCat.value || 'geral',
            tipo: selTipo.value || 'modelo',
            pasta_id: selPasta.value ? Number(selPasta.value) : null,
          }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: 'Erro ' + r.status }));
          throw new Error(err.detail || 'HTTP ' + r.status);
        }
        const created = await r.json();
        // Importa o arquivo escolhido como versão 1 (mesma ação de "criar e importar")
        if (file) {
          btnSalvar.textContent = 'Importando arquivo…';
          const fd = new FormData();
          fd.append('file', file);
          const up = await fetch(apiBase() + '/api/docs/documentos/' + created.id + '/versoes', {
            method: 'POST', headers: { 'Authorization': 'Bearer ' + getToken() }, body: fd,
          });
          if (!up.ok) {
            const e = await up.json().catch(() => ({ detail: 'Erro ' + up.status }));
            throw new Error('Documento criado, mas falha ao importar o arquivo: ' + (e.detail || up.status));
          }
        }
        // Mostra a pasta onde o documento foi criado
        docsState.pastaId = selPasta.value ? Number(selPasta.value) : null;
        docsState.tipo = '';
        docsState.q = '';
        render();
        loadDocs();
      } catch (e) {
        btnSalvar.disabled = false;
        btnSalvar.textContent = 'Criar e importar';
        showMsg(form, 'Erro: ' + e.message, true);
      }
    });

    docsRoot.appendChild(form);
  }

  // ── Ponto de montagem principal da página Documentos ─────────────────────
  function mount() {
    // Tenta o div interno docs-root (padrão preferido, sem apagar o page-container)
    // Fallback: page-documentos se docs-root não existir
    docsRoot = document.getElementById('docs-root') || document.getElementById('page-documentos');
    if (!docsRoot) return;
    loadPastas().then(() => { render(); loadDocs(); });
  }

  // ── DRAWER DE AJUDA (DOC-01) ──────────────────────────────────────────────
  let drawerEl = null;
  let drawerChave = null;
  let _ajudaData = null; // { titulo, conteudo_md, chave }

  const DRAWER_STYLES = {
    position: 'fixed',
    top: '0',
    right: '-420px',
    width: '400px',
    height: '100vh',
    background: 'var(--panel, #0f2035)',
    borderLeft: '1px solid var(--border, rgba(255,255,255,.1))',
    zIndex: '9999',
    display: 'flex',
    flexDirection: 'column',
    transition: 'right .25s ease',
    overflowY: 'auto',
    boxShadow: '-4px 0 24px rgba(0,0,0,.35)',
  };

  function _ensureDrawer() {
    if (drawerEl && document.body.contains(drawerEl)) return;
    drawerEl = el('div', { id: 'erp-docs-ajuda-drawer', role: 'dialog', 'aria-label': 'Ajuda contextual', style: DRAWER_STYLES });
    document.body.appendChild(drawerEl);
  }

  function _closeOverlay() {
    if (drawerEl) drawerEl.style.right = '-420px';
    const ov = document.getElementById('erp-docs-ajuda-overlay');
    if (ov) ov.style.opacity = '0';
    setTimeout(() => {
      const o2 = document.getElementById('erp-docs-ajuda-overlay');
      if (o2 && o2.parentNode) o2.parentNode.removeChild(o2);
    }, 250);
  }

  function _ensureOverlay() {
    let ov = document.getElementById('erp-docs-ajuda-overlay');
    if (!ov) {
      ov = el('div', {
        id: 'erp-docs-ajuda-overlay',
        style: {
          position: 'fixed', top: '0', left: '0', width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,.4)', zIndex: '9998', transition: 'opacity .2s',
          opacity: '0',
        },
      });
      ov.addEventListener('click', closeAjuda);
      document.body.appendChild(ov);
      requestAnimationFrame(() => { ov.style.opacity = '1'; });
    }
  }

  function _renderAjudaContent() {
    if (!drawerEl) return;
    drawerEl.innerHTML = '';

    // Cabeçalho
    const hdr = el('div', {
      style: {
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 18px', borderBottom: '1px solid var(--border, rgba(255,255,255,.1))',
        flexShrink: '0',
      }
    });

    const tituloEl = el('strong', { style: { color: 'var(--text1)', fontSize: '15px' } });
    tituloEl.textContent = (_ajudaData && _ajudaData.titulo) ? _ajudaData.titulo : 'Ajuda';
    hdr.appendChild(tituloEl);

    const btnFechar = el('button', {
      class: 'btn btn-ghost btn-sm',
      'aria-label': 'Fechar ajuda',
      onclick: closeAjuda,
    });
    btnFechar.textContent = '✕';
    hdr.appendChild(btnFechar);
    drawerEl.appendChild(hdr);

    // Corpo do conteúdo
    const body = el('div', { style: { padding: '18px', flex: '1', overflowY: 'auto' } });

    const conteudo = el('div', { class: 'ajuda-md-body', style: { color: 'var(--text1)', lineHeight: '1.6', fontSize: '14px' } });
    // renderMdSafe usa apenas textContent/createTextNode — ZERO innerHTML de conteúdo do servidor
    renderMdSafe((_ajudaData && _ajudaData.conteudo_md) ? _ajudaData.conteudo_md : '_Nenhum conteúdo de ajuda disponível para esta página._', conteudo);
    body.appendChild(conteudo);

    // Modo de edição para gestores/operadores
    if (canWrite()) {
      const sep = el('hr', { style: { border: 'none', borderTop: '1px solid var(--border, rgba(255,255,255,.1))', margin: '16px 0' } });
      body.appendChild(sep);

      const editArea = el('div', { id: 'ajuda-edit-area' });

      const btnEditar = el('button', { class: 'btn btn-ghost btn-sm', onclick: () => _showEditMode(editArea, conteudo, btnEditar) });
      btnEditar.textContent = 'Editar';
      editArea.appendChild(btnEditar);

      body.appendChild(editArea);
    }

    drawerEl.appendChild(body);

    // Rodapé com chave
    const foot = el('div', { style: { padding: '10px 18px', borderTop: '1px solid var(--border, rgba(255,255,255,.1))', fontSize: '11px', color: 'var(--text3, rgba(255,255,255,.35))', flexShrink: '0' } });
    foot.textContent = 'Chave: ';
    const chaveEl = el('code', { style: { fontSize: '11px' } });
    chaveEl.textContent = drawerChave || 'geral';
    foot.appendChild(chaveEl);
    drawerEl.appendChild(foot);
  }

  function _showEditMode(editArea, conteudoEl, btnEditar) {
    editArea.innerHTML = '';

    const lblEdit = el('label', { style: { color: 'var(--text2)', fontSize: '12px', display: 'block', marginBottom: '6px' } });
    lblEdit.textContent = 'Editar conteúdo Markdown:';
    editArea.appendChild(lblEdit);

    const inputTitulo = el('input', {
      type: 'text',
      placeholder: 'Título',
      style: { width: '100%', background: 'var(--bg2)', color: 'var(--text1)', border: '1px solid var(--border)', borderRadius: '4px', padding: '6px 8px', marginBottom: '8px', boxSizing: 'border-box', fontSize: '13px' }
    });
    inputTitulo.value = (_ajudaData && _ajudaData.titulo) ? _ajudaData.titulo : '';
    editArea.appendChild(inputTitulo);

    const textarea = el('textarea', {
      style: {
        width: '100%', minHeight: '140px', background: 'var(--bg2)', color: 'var(--text1)',
        border: '1px solid var(--border)', borderRadius: '4px', padding: '8px', resize: 'vertical',
        fontFamily: 'var(--mono, monospace)', fontSize: '12px', boxSizing: 'border-box',
      }
    });
    // Usar textContent/value para setar conteúdo do servidor na textarea — seguro (não vai para DOM como HTML)
    textarea.value = (_ajudaData && _ajudaData.conteudo_md) ? _ajudaData.conteudo_md : '';
    editArea.appendChild(textarea);

    const rowBtns = el('div', { style: { display: 'flex', gap: '6px', marginTop: '8px' } });

    const btnCancelar = el('button', { class: 'btn btn-ghost btn-sm', type: 'button', onclick: () => {
      editArea.innerHTML = '';
      editArea.appendChild(btnEditar);
    }});
    btnCancelar.textContent = 'Cancelar';

    const btnSalvar = el('button', { class: 'btn btn-primary btn-sm', type: 'button' });
    btnSalvar.textContent = 'Salvar';

    btnSalvar.addEventListener('click', async () => {
      btnSalvar.disabled = true;
      btnSalvar.textContent = 'Salvando…';
      try {
        const r = await authFetch('/api/docs/ajuda/' + encodeURIComponent(drawerChave || 'geral'), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            titulo: inputTitulo.value.trim() || (drawerChave || 'geral'),
            conteudo_md: textarea.value,
            categoria: null,
          }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: 'Erro ' + r.status }));
          throw new Error(err.detail || 'HTTP ' + r.status);
        }
        const saved = await r.json();
        _ajudaData = saved;
        // Re-render do conteúdo seguro via renderMdSafe
        renderMdSafe(saved.conteudo_md || '', conteudoEl);
        editArea.innerHTML = '';
        editArea.appendChild(btnEditar);
      } catch (e) {
        btnSalvar.disabled = false;
        btnSalvar.textContent = 'Salvar';
        const errMsg = el('span', { style: { color: 'var(--red)', fontSize: '12px' } });
        errMsg.textContent = 'Erro: ' + e.message;
        rowBtns.appendChild(errMsg);
      }
    });

    rowBtns.appendChild(btnCancelar);
    rowBtns.appendChild(btnSalvar);
    editArea.appendChild(rowBtns);
  }

  async function openAjuda(chave) {
    const key = chave || 'geral';
    drawerChave = key;
    _ajudaData = null;

    _ensureDrawer();
    _ensureOverlay();

    // Mostrar drawer imediatamente com loading
    drawerEl.innerHTML = '';
    const loading = el('div', { style: { padding: '24px 18px', color: 'var(--text2)' } });
    loading.textContent = 'Carregando ajuda…';
    drawerEl.appendChild(loading);
    requestAnimationFrame(() => { drawerEl.style.right = '0'; });

    try {
      const r = await authFetch('/api/docs/ajuda?chave=' + encodeURIComponent(key));
      if (r.ok) {
        _ajudaData = await r.json();
      } else if (r.status === 404) {
        _ajudaData = { titulo: 'Ajuda: ' + key, conteudo_md: '' };
      } else {
        throw new Error('HTTP ' + r.status);
      }
    } catch (e) {
      _ajudaData = { titulo: 'Ajuda', conteudo_md: '' };
    }

    _renderAjudaContent();
  }

  function closeAjuda() {
    _closeOverlay();
  }

  // ── Exposição pública ──────────────────────────────────────────────────────
  window.erpDocs = {
    mount: mount,
    openAjuda: openAjuda,
    closeAjuda: closeAjuda,
    renderMdSafe: renderMdSafe, // exposta para testes
  };

})();
