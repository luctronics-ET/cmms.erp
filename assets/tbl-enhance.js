/**
 * tbl-enhance.js — sort + multi-select checkbox filter para toda <table class="tbl">.
 *
 * Progressive enhancement: nenhance(table) é idempotente e re-aplica sozinho via
 * MutationObserver quando o <tbody> muda (tabelas do ERP são repovoadas por JS).
 *
 * - Click no rótulo do <th>  → ordena asc/desc (numérico-aware).
 * - Ícone funil no <th>      → dropdown com checkbox dos valores distintos da coluna.
 *   Multi-seleção: OR dentro da coluna, AND entre colunas. Busca p/ listas longas.
 * - Colunas sem dado (ex: "Ações") não ganham filtro, só sort é pulado se vazio.
 *
 * ponytail: opera direto no DOM da tabela, sem virtualização. Some/hide rows via
 *   style.display — ok até ~milhares de linhas; se passar disso, paginar.
 */
(function () {
  'use strict';

  // ── núcleo puro (testável sem DOM) ──────────────────────────────────────
  function parseNum(s) {
    if (s == null) return null;
    // pega primeiro número (aceita 1.234,56 e 1234.56 e "12 h")
    const m = String(s).replace(/\s/g, '').match(/-?[\d.,]*\d/);
    if (!m) return null;
    let t = m[0];
    // 1.234,56 → 1234.56 ; 1,5 → 1.5
    if (/,\d+$/.test(t)) t = t.replace(/\./g, '').replace(',', '.');
    const n = parseFloat(t);
    return Number.isNaN(n) ? null : n;
  }

  function compareValues(a, b) {
    const na = parseNum(a), nb = parseNum(b);
    if (na !== null && nb !== null && na !== nb) return na - nb;
    return String(a).localeCompare(String(b), 'pt-BR', { numeric: true, sensitivity: 'base' });
  }

  const SKIP_FILTER_HEADERS = new Set(['ações', 'acoes', 'ação', 'acao', '']);

  // node self-test: roda com `node assets/tbl-enhance.js`
  if (typeof document === 'undefined') {
    const assert = (c, m) => { if (!c) { console.error('FAIL:', m); process.exit(1); } };
    assert(parseNum('12 h') === 12, 'parseNum unidade');
    assert(parseNum('1.234,56') === 1234.56, 'parseNum pt-BR');
    assert(parseNum('abc') === null, 'parseNum texto');
    assert(compareValues('2', '10') < 0, 'numérico 2<10');
    assert(compareValues('banana', 'abacaxi') > 0, 'texto b>a');
    assert([['10'], ['2'], ['1']].sort((x, y) => compareValues(x[0], y[0])).map(r => r[0]).join() === '1,2,10', 'sort numérico');
    console.log('tbl-enhance self-test OK');
    return;
  }

  // ── CSS injetado uma vez ────────────────────────────────────────────────
  const CSS = `
  .tbl th.tblx{cursor:default;position:relative}
  .tbl th.tblx .tblx-lbl{cursor:pointer;user-select:none;display:inline-flex;align-items:center;gap:4px}
  .tbl th.tblx .tblx-lbl:hover{color:var(--acc)}
  .tbl th.tblx .tblx-sort{font-size:14px;opacity:.5}
  .tbl th.tblx.sorted .tblx-sort{opacity:1;color:var(--acc)}
  .tbl th.tblx .tblx-funnel{margin-left:6px;cursor:pointer;font-size:16px;line-height:1;opacity:.45;border:none;background:none;color:inherit;padding:0 2px}
  .tbl th.tblx .tblx-funnel:hover{opacity:1;color:var(--acc)}
  .tbl th.tblx.filtered .tblx-funnel{opacity:1;color:var(--acc)}
  .tblx-pop{position:fixed;z-index:9999;background:var(--bg2,#0d1e33);border:1px solid var(--border,#1c3350);
    border-radius:10px;box-shadow:0 12px 30px rgba(0,0,0,.45);padding:8px;min-width:200px;max-width:300px;
    font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--text1,#e6eefc)}
  .tblx-pop input[type=search]{width:100%;box-sizing:border-box;margin-bottom:6px;padding:5px 8px;border-radius:7px;
    border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text1,#e6eefc);font-size:12px}
  .tblx-pop .tblx-list{max-height:240px;overflow:auto;display:flex;flex-direction:column;gap:2px}
  .tblx-pop label{display:flex;align-items:center;gap:7px;padding:4px 6px;border-radius:6px;cursor:pointer;text-transform:none;letter-spacing:0;font-weight:400}
  .tblx-pop label:hover{background:rgba(255,255,255,.05)}
  .tblx-pop label span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .tblx-pop .tblx-acts{display:flex;gap:6px;margin-top:8px;border-top:1px solid var(--border,#1c3350);padding-top:8px}
  .tblx-pop .tblx-acts button{flex:1;padding:5px;border-radius:7px;border:1px solid var(--border,#1c3350);
    background:var(--bg3,#0a1828);color:var(--text2,#9fb3cc);cursor:pointer;font-size:11px}
  .tblx-pop .tblx-acts button:hover{border-color:var(--acc,#00b4d8);color:var(--acc,#00b4d8)}
  .tblx-exportbar{display:flex;gap:6px;justify-content:flex-end;margin:0 0 6px}
  .tblx-expbtn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:7px;
    border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text2,#9fb3cc);
    cursor:pointer;font-size:11px;font-family:inherit}
  .tblx-expbtn:hover{border-color:var(--acc,#00b4d8);color:var(--acc,#00b4d8)}`;

  function injectCSS() {
    if (document.getElementById('tblx-css')) return;
    const s = document.createElement('style');
    s.id = 'tblx-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // estado por tabela: { filters: {colIdx:Set<string>}, sort:{col,dir} }
  function getState(table) {
    if (!table.__tblx) table.__tblx = { filters: {}, sort: null };
    return table.__tblx;
  }

  function bodyRows(table) {
    const tb = table.tBodies[0];
    if (!tb) return [];
    // ignora linhas "vazias"/mensagem (1 td com colspan)
    return Array.from(tb.rows).filter(r => r.cells.length > 1 || !r.cells[0] || !r.cells[0].hasAttribute('colspan'));
  }

  function cellText(row, idx) {
    const c = row.cells[idx];
    return c ? c.textContent.trim() : '';
  }

  function applyFilters(table) {
    const st = getState(table);
    const tb = table.tBodies[0];
    if (!tb) return;
    // filters[col]: Set de valores permitidos quando ativo; null/ausente = inativo.
    // Set vazio = nada permitido = esconde tudo.
    for (const row of tb.rows) {
      let show = true;
      for (const k in st.filters) {
        const set = st.filters[k];
        if (set && !set.has(cellText(row, +k))) { show = false; break; }
      }
      row.style.display = show ? '' : 'none';
    }
  }

  function applySort(table) {
    const st = getState(table);
    if (!st.sort) return;
    const tb = table.tBodies[0];
    if (!tb) return;
    const rows = bodyRows(table);
    const { col, dir } = st.sort;
    rows.sort((ra, rb) => {
      const r = compareValues(cellText(ra, col), cellText(rb, col));
      return dir === 'desc' ? -r : r;
    });
    rows.forEach(r => tb.appendChild(r));
  }

  function distinctValues(table, col) {
    const seen = new Set();
    for (const row of bodyRows(table)) seen.add(cellText(row, col));
    return Array.from(seen).filter(v => v !== '').sort((a, b) => compareValues(a, b));
  }

  // ── popup de filtro ─────────────────────────────────────────────────────
  let openPop = null;
  function closePop() {
    if (openPop) { openPop.remove(); openPop = null; document.removeEventListener('mousedown', onDocDown, true); }
  }
  function onDocDown(e) {
    if (openPop && !openPop.contains(e.target) && !e.target.classList.contains('tblx-funnel')) closePop();
  }

  function openFilter(table, col, anchor) {
    closePop();
    const st = getState(table);
    const vals = distinctValues(table, col);
    const th = anchor.closest('th');
    const checked = new Set(st.filters[col] || vals);
    const pop = document.createElement('div');
    pop.className = 'tblx-pop';

    const search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'buscar…';
    const list = document.createElement('div');
    list.className = 'tblx-list';

    function commit() {
      // tudo marcado = sem filtro (null); senao guarda exatamente os marcados
      st.filters[col] = checked.size === vals.length ? null : new Set(checked);
      th.classList.toggle('filtered', st.filters[col] != null);
      applyFilters(table);
    }
    function renderList(q) {
      list.innerHTML = '';
      vals.filter(v => !q || v.toLowerCase().includes(q.toLowerCase())).forEach(v => {
        const lbl = document.createElement('label');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = checked.has(v);
        cb.onchange = () => { cb.checked ? checked.add(v) : checked.delete(v); commit(); };
        const span = document.createElement('span');
        span.textContent = v;
        lbl.append(cb, span);
        list.appendChild(lbl);
      });
    }
    search.oninput = () => renderList(search.value);
    renderList('');

    const acts = document.createElement('div');
    acts.className = 'tblx-acts';
    const bAll = document.createElement('button'); bAll.textContent = 'Todos';
    const bNone = document.createElement('button'); bNone.textContent = 'Limpar';
    // atuam nas CHECKBOXES: marcam/desmarcam todas; o filtro segue o estado delas
    bAll.onclick = () => { vals.forEach(v => checked.add(v)); commit(); renderList(search.value); };
    bNone.onclick = () => { checked.clear(); commit(); renderList(search.value); };
    acts.append(bAll, bNone);

    pop.append(search, list, acts);
    document.body.appendChild(pop);
    const r = anchor.getBoundingClientRect();
    pop.style.top = Math.min(r.bottom + 4, window.innerHeight - pop.offsetHeight - 8) + 'px';
    pop.style.left = Math.min(r.left, window.innerWidth - pop.offsetWidth - 8) + 'px';
    openPop = pop;
    document.addEventListener('mousedown', onDocDown, true);
    search.focus();
  }

  // ── export (Excel/CSV + PDF) — zero dependência ─────────────────────────
  function csvEscape(s) {
    s = String(s == null ? '' : s);
    return /[";\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function downloadBlob(content, mime, filename) {
    const b = new Blob([content], { type: mime });
    const u = URL.createObjectURL(b);
    const a = document.createElement('a');
    a.href = u; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
  }
  function slug(s) { return String(s || 'tabela').toLowerCase().replace(/[^\w]+/g, '-').replace(/^-|-$/g, '') || 'tabela'; }

  // Excel via CSV (BOM UTF-8 + separador ';' que o Excel pt-BR entende)
  function exportExcel(title, headers, rows) {
    const sep = ';';
    const lines = [headers.map(csvEscape).join(sep), ...rows.map(r => r.map(csvEscape).join(sep))];
    downloadBlob('﻿' + lines.join('\r\n'), 'text/csv;charset=utf-8', slug(title) + '.csv');
  }
  // PDF via iframe oculto + window.print (Salvar como PDF) — sem popup, sem bloqueador
  function exportPDF(title, headers, rows) {
    const esc = s => String(s == null ? '' : s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
    const thead = '<tr>' + headers.map(h => '<th>' + esc(h) + '</th>').join('') + '</tr>';
    const tbody = rows.map(r => '<tr>' + r.map(c => '<td>' + esc(c) + '</td>').join('') + '</tr>').join('');
    const html = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>' + esc(title) + '</title>'
      + '<style>body{font-family:Arial,Helvetica,sans-serif;margin:18px;color:#111}'
      + 'h1{font-size:15px;margin:0 0 4px}.meta{font-size:10px;color:#666;margin-bottom:12px}'
      + 'table{border-collapse:collapse;width:100%;font-size:10px}'
      + 'th,td{border:1px solid #999;padding:4px 6px;text-align:left;vertical-align:top}'
      + 'th{background:#e9eef5}tr:nth-child(even) td{background:#f6f8fb}</style></head><body>'
      + '<h1>' + esc(title) + '</h1><div class="meta">' + rows.length + ' registro(s) · cmasm.erp</div>'
      + '<table><thead>' + thead + '</thead><tbody>' + tbody + '</tbody></table></body></html>';
    const ifr = document.createElement('iframe');
    ifr.setAttribute('aria-hidden', 'true');
    ifr.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden';
    document.body.appendChild(ifr);
    const doc = ifr.contentWindow.document;
    doc.open(); doc.write(html); doc.close();
    // document.write nem sempre dispara onload; aciona print após pequeno delay
    setTimeout(() => {
      try { ifr.contentWindow.focus(); ifr.contentWindow.print(); }
      catch (e) { alert('Falha ao gerar PDF: ' + e.message); }
      setTimeout(() => ifr.remove(), 1500);
    }, 300);
  }

  // extrai cabeçalhos + linhas VISÍVEIS (respeita filtros) de uma <table.tbl>,
  // pulando colunas de ação
  function tableData(table) {
    const ths = Array.from((table.tHead && table.tHead.rows[0] && table.tHead.rows[0].cells) || []);
    const keep = ths
      .map((th, i) => ({ i, label: (th.querySelector('.tblx-lbl') || th).textContent.replace(/[↕▲▼▾]/g, '').trim() }))
      .filter(c => !SKIP_FILTER_HEADERS.has(c.label.toLowerCase()));
    const headers = keep.map(c => c.label);
    const rows = bodyRows(table)
      .filter(r => r.style.display !== 'none')
      .map(r => keep.map(c => cellText(r, c.i)));
    return { headers, rows };
  }

  function addExportBar(table) {
    if (table.__tblxBar || !table.parentNode) return;
    const bar = document.createElement('div');
    bar.className = 'tblx-exportbar';
    const title = () => {
      const h = document.querySelector('.page.active h1');
      return (h && h.textContent.trim()) || 'Tabela';
    };
    const mk = (txt, fn) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tblx-expbtn'; b.textContent = txt; b.onclick = fn;
      return b;
    };
    bar.append(
      mk('⬇ Excel', () => { const d = tableData(table); exportExcel(title(), d.headers, d.rows); }),
      mk('⬇ PDF', () => { const d = tableData(table); exportPDF(title(), d.headers, d.rows); }),
    );
    table.parentNode.insertBefore(bar, table);
    table.__tblxBar = bar;
  }

  // exposto p/ outros componentes (ex.: engine.table do pmoc-engine.js)
  window.tblExport = { excel: exportExcel, pdf: exportPDF };

  // ── enhance de uma tabela ───────────────────────────────────────────────
  function enhance(table) {
    if (table.__tblxDone) { refresh(table); return; }
    const head = table.tHead;
    if (!head || head.rows.length !== 1) return;          // só thead simples
    const ths = head.rows[0].cells;
    if (!ths.length) return;
    if (Array.from(ths).some(th => th.colSpan > 1)) return; // pula headers agrupados

    Array.from(ths).forEach((th, col) => {
      const label = th.textContent.trim();
      th.classList.add('tblx');
      th.innerHTML = '';
      const lbl = document.createElement('span');
      lbl.className = 'tblx-lbl';
      lbl.append(document.createTextNode(label));
      const sortIcon = document.createElement('span');
      sortIcon.className = 'tblx-sort';
      sortIcon.textContent = '↕';
      lbl.appendChild(sortIcon);
      lbl.onclick = () => {
        const st = getState(table);
        const dir = (st.sort && st.sort.col === col && st.sort.dir === 'asc') ? 'desc' : 'asc';
        st.sort = { col, dir };
        Array.from(ths).forEach(t => { t.classList.remove('sorted'); const si = t.querySelector('.tblx-sort'); if (si) si.textContent = '↕'; });
        th.classList.add('sorted');
        sortIcon.textContent = dir === 'asc' ? '▲' : '▼';
        applySort(table);
      };
      th.appendChild(lbl);

      if (!SKIP_FILTER_HEADERS.has(label.toLowerCase())) {
        const funnel = document.createElement('button');
        funnel.className = 'tblx-funnel';
        funnel.textContent = '▾';
        funnel.title = 'Filtrar';
        funnel.onclick = (e) => { e.stopPropagation(); openFilter(table, col, funnel); };
        th.appendChild(funnel);
      }
    });

    addExportBar(table);

    // re-aplica sort/filtro quando o tbody é repovoado
    const tb = table.tBodies[0];
    if (tb) {
      const obs = new MutationObserver(() => {
        clearTimeout(table.__tblxT);
        table.__tblxT = setTimeout(() => refresh(table), 50);
      });
      obs.observe(tb, { childList: true });
    }
    table.__tblxDone = true;
  }

  function refresh(table) {
    applySort(table);
    applyFilters(table);
  }

  function enhanceAll() {
    injectCSS();
    document.querySelectorAll('table.tbl').forEach(enhance);
  }

  // expõe + auto-run: novas tabelas que aparecem em troca de aba também pegam
  window.tblEnhance = enhanceAll;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', enhanceAll);
  else enhanceAll();
  // re-scan periódico leve p/ tabelas criadas dinamicamente sem repintar a página
  setInterval(enhanceAll, 1500);
})();
