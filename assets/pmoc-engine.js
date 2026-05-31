/**
 * pmoc-engine v2.0.0
 *
 * Shell + componentes para PMOCs do xCMASM.
 * Vanilla JS, sem build step, sem dependências externas.
 *
 * Ver TEMPLATE_PMOC.md §9 para o contrato.
 *
 * Componentes: header, modal, badge, table, kanban, calendar,
 *              chartDonut, chartLine, chat, camera, confirm, gantt.
 *
 * Cada componente recebe (el, options) e retorna uma API com
 * { update, destroy, ... } e dispara eventos via CustomEvent.
 */
(function (global) {
  'use strict';

  const VERSION = '2.0.0';

  // ─────────────────── utils ───────────────────

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class')      node.className = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
      else if (k === 'dataset' && typeof v === 'object') Object.assign(node.dataset, v);
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : v);
    }
    for (const ch of children.flat()) {
      if (ch == null || ch === false) continue;
      node.appendChild(typeof ch === 'string' ? document.createTextNode(ch) : ch);
    }
    return node;
  }

  function emit(target, type, detail) {
    target.dispatchEvent(new CustomEvent('pe:' + type, { detail, bubbles: true }));
  }

  const fmt = {
    date:  iso => iso ? new Date(iso).toLocaleDateString('pt-BR') : '—',
    dt:    iso => iso ? new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—',
    time:  iso => iso ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—',
    num:   (n, d = 0) => Number(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }),
    iso:   d => (d instanceof Date ? d : new Date(d)).toISOString().slice(0, 10),
  };

  function uuid() {
    if (crypto?.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  // ─────────────────── header ───────────────────

  function header(target, opts = {}) {
    const state = {
      user:   opts.user   || { nome: 'Operador' },
      modulo: opts.modulo || 'PMOC',
      sync:   opts.syncStatus || { online: navigator.onLine, pending: 0, lastSync: null },
    };

    const root = el('header', { class: 'pe-header' });

    function render() {
      const dotCls = state.sync.online ? 'pe-header__dot--online' : 'pe-header__dot--offline';
      root.replaceChildren(
        el('div', { class: 'pe-header__logo' }, 'xCMASM'),
        el('div', { class: 'pe-header__title' }, state.modulo),
        el('div', { class: 'pe-header__spacer' }),
        el('div', { class: 'pe-header__user' }, state.user.nome || '—'),
        el('div', { class: 'pe-header__sync' },
          el('span', { class: 'pe-header__dot ' + dotCls }),
          el('span', {}, state.sync.online ? 'online' : 'offline'),
          state.sync.pending > 0
            ? el('span', { class: 'pe-header__pending' }, String(state.sync.pending))
            : null,
          el('span', { class: 'mono', style: { fontFamily: 'var(--font-mono)', fontSize: '11px' } },
            state.sync.lastSync ? `· ${fmt.time(state.sync.lastSync)}` : '· nunca'),
        ),
        el('button', {
          class: 'pe-header__sync-btn',
          onclick: () => emit(root, 'sync-click'),
        }, 'Sincronizar'),
      );
    }

    render();
    if (target) target.replaceChildren(root);

    return {
      element: root,
      update(patch) { Object.assign(state, patch); render(); },
      setSync(s)    { state.sync = { ...state.sync, ...s }; render(); },
    };
  }

  // ─────────────────── badge ───────────────────

  function badge(text, kind = '') {
    const cls = kind ? `pe-badge pe-badge--${kind}` : 'pe-badge';
    return el('span', { class: cls }, text);
  }

  // ─────────────────── modal ───────────────────

  function modal(opts = {}) {
    let backdrop = null;
    const root = el('div', { class: 'pe-modal', role: 'dialog', 'aria-modal': 'true' });

    function close() {
      if (!backdrop) return;
      backdrop.remove();
      backdrop = null;
      opts.onClose?.();
    }

    function render() {
      root.replaceChildren(
        el('div', { class: 'pe-modal__header' },
          el('div', { class: 'pe-modal__title' }, opts.title || ''),
          el('button', { class: 'pe-modal__close', onclick: close, 'aria-label': 'Fechar' }, '×'),
        ),
        el('div', { class: 'pe-modal__body' },
          typeof opts.body === 'string' ? el('div', {}, opts.body) : (opts.body || '')),
        opts.footer != null
          ? el('div', { class: 'pe-modal__footer' },
              Array.isArray(opts.footer) ? opts.footer : [opts.footer])
          : null,
      );
    }

    return {
      open() {
        if (backdrop) return;
        backdrop = el('div', {
          class: 'pe-modal-backdrop',
          onclick: e => { if (e.target === backdrop && opts.closeOnBackdrop !== false) close(); },
        });
        render();
        backdrop.appendChild(root);
        document.body.appendChild(backdrop);
      },
      close,
      update(patch) { Object.assign(opts, patch); render(); },
      element: root,
    };
  }

  // ─────────────────── confirm ───────────────────

  async function confirmDlg(opts = {}) {
    return new Promise(resolve => {
      const reasonInput = opts.requireReason
        ? el('textarea', { class: 'pe-textarea', rows: '3', placeholder: 'Motivo obrigatório...' })
        : null;
      const m = modal({
        title: opts.title || 'Confirmar',
        body: el('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
          el('div', {}, opts.text || ''),
          reasonInput,
        ),
        footer: [
          el('button', { class: 'pe-btn', onclick: () => { m.close(); resolve(null); } }, 'Cancelar'),
          el('button', {
            class: 'pe-btn ' + (opts.kind === 'danger' ? 'pe-btn--danger' : 'pe-btn--primary'),
            onclick: () => {
              if (opts.requireReason && !reasonInput.value.trim()) {
                reasonInput.focus(); return;
              }
              m.close();
              resolve(opts.requireReason ? reasonInput.value.trim() : true);
            },
          }, opts.okText || 'OK'),
        ],
      });
      m.open();
    });
  }

  // ─────────────────── table ───────────────────

  function table(target, opts = {}) {
    const state = {
      cols: opts.cols || [],
      rows: opts.rows || [],
      pageSize: opts.pageSize || 25,
      page: 1,
      sortKey: null,
      sortDir: 1,
      search: '',
      filters: {},      // { key: value }
    };

    const root = el('div', { class: 'pe-table-wrap' });
    if (target) target.replaceChildren(root);

    function filtered() {
      let rows = state.rows;
      const term = state.search.trim().toLowerCase();
      if (term) {
        rows = rows.filter(r => state.cols.some(c => {
          const v = r[c.key];
          return v != null && String(v).toLowerCase().includes(term);
        }));
      }
      for (const [k, v] of Object.entries(state.filters)) {
        if (v === '' || v == null) continue;
        rows = rows.filter(r => String(r[k] ?? '') === String(v));
      }
      if (state.sortKey) {
        const k = state.sortKey, dir = state.sortDir;
        rows = rows.slice().sort((a, b) => {
          const av = a[k], bv = b[k];
          if (av == null) return 1; if (bv == null) return -1;
          if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
          return String(av).localeCompare(String(bv), 'pt-BR') * dir;
        });
      }
      return rows;
    }

    function render() {
      const rows = filtered();
      const total = rows.length;
      const pages = Math.max(1, Math.ceil(total / state.pageSize));
      if (state.page > pages) state.page = pages;
      const start = (state.page - 1) * state.pageSize;
      const slice = rows.slice(start, start + state.pageSize);

      const toolbar = el('div', { class: 'pe-table-toolbar' },
        el('input', {
          class: 'pe-input pe-table-toolbar__search',
          placeholder: 'Buscar…',
          value: state.search,
          oninput: e => { state.search = e.target.value; state.page = 1; render(); },
        }),
        ...state.cols.filter(c => c.filter).map(c => {
          const opts = ['', ...new Set(state.rows.map(r => r[c.key]).filter(Boolean))];
          return el('select', {
            class: 'pe-select', style: { width: 'auto' },
            onchange: e => { state.filters[c.key] = e.target.value; state.page = 1; render(); },
          }, ...opts.map(v =>
            el('option', { value: v, selected: state.filters[c.key] === v }, v || `Todos: ${c.label}`),
          ));
        }),
      );

      const thead = el('thead', {}, el('tr', {},
        ...state.cols.map(c => el('th', {
          onclick: c.sort !== false ? () => {
            if (state.sortKey === c.key) state.sortDir *= -1;
            else { state.sortKey = c.key; state.sortDir = 1; }
            render();
          } : null,
        }, c.label,
          state.sortKey === c.key
            ? el('span', { class: 'sort-arrow' }, state.sortDir === 1 ? '↑' : '↓')
            : null,
        )),
      ));

      const tbody = slice.length
        ? el('tbody', {}, ...slice.map(r => {
            const tr = el('tr', { onclick: () => opts.onRowClick?.(r) },
              ...state.cols.map(c => {
                const v = c.format ? c.format(r[c.key], r) : r[c.key];
                if (v instanceof Node) return el('td', {}, v);
                return el('td', {}, v == null ? '' : String(v));
              }),
            );
            return tr;
          }))
        : el('tbody', {}, el('tr', {}, el('td', { class: 'pe-table__empty', colspan: state.cols.length }, 'Nenhum resultado')));

      root.replaceChildren(
        toolbar,
        el('div', { style: { overflowX: 'auto' } },
          el('table', { class: 'pe-table' }, thead, tbody),
        ),
        el('div', { class: 'pe-table__pager' },
          el('button', {
            class: 'pe-btn', disabled: state.page <= 1,
            onclick: () => { state.page--; render(); },
          }, '‹'),
          el('span', { class: 'mono', style: { fontFamily: 'var(--font-mono)' } },
            `${state.page} / ${pages}`),
          el('button', {
            class: 'pe-btn', disabled: state.page >= pages,
            onclick: () => { state.page++; render(); },
          }, '›'),
          el('div', { class: 'spacer' }),
          el('span', {}, `${total} registros`),
        ),
      );
    }

    render();
    return {
      element: root,
      update(rows) { state.rows = rows; render(); },
      setFilter(key, value) { state.filters[key] = value; state.page = 1; render(); },
      getFiltered: filtered,
    };
  }

  // ─────────────────── kanban (HTML5 DnD) ───────────────────

  function kanban(target, opts = {}) {
    const state = {
      columns: opts.columns || [],
      cards:   opts.cards   || [],
    };
    const root = el('div', { class: 'pe-kanban' });
    if (target) target.replaceChildren(root);
    let dragId = null;

    function render() {
      root.replaceChildren(...state.columns.map(col => {
        const cards = state.cards.filter(c => c.columnId === col.id);
        const colEl = el('div', {
          class: 'pe-kanban__col',
          dataset: { col: col.id },
          ondragover: e => { e.preventDefault(); colEl.classList.add('pe-kanban__col--drop-target'); },
          ondragleave: () => colEl.classList.remove('pe-kanban__col--drop-target'),
          ondrop: e => {
            e.preventDefault();
            colEl.classList.remove('pe-kanban__col--drop-target');
            const cardId = e.dataTransfer.getData('text/plain') || dragId;
            const card = state.cards.find(c => c.id === cardId);
            if (!card) return;
            const from = card.columnId;
            if (from === col.id) return;
            card.columnId = col.id;
            opts.onMove?.(cardId, from, col.id);
            emit(root, 'kanban-move', { cardId, from, to: col.id });
            render();
          },
        },
          el('div', { class: 'pe-kanban__col-header' },
            el('span', {}, col.title),
            el('span', { class: 'count' }, String(cards.length)),
          ),
          el('div', { class: 'pe-kanban__col-body' },
            ...cards.map(card => el('div', {
              class: 'pe-card',
              draggable: 'true',
              dataset: { card: card.id },
              ondragstart: e => {
                dragId = card.id;
                e.dataTransfer.setData('text/plain', card.id);
                e.dataTransfer.effectAllowed = 'move';
                e.target.classList.add('dragging');
              },
              ondragend: e => { e.target.classList.remove('dragging'); dragId = null; },
              onclick: () => { opts.onCardClick?.(card); emit(root, 'card-click', card); },
            },
              el('div', { class: 'pe-card__title' }, card.title),
              card.badges?.length
                ? el('div', { class: 'pe-card__meta' },
                    ...card.badges.map(b => badge(b.text, b.kind)))
                : null,
            )),
          ),
        );
        return colEl;
      }));
    }

    render();
    return {
      element: root,
      update(cards) { state.cards = cards; render(); },
      addCard(card) { state.cards.push(card); render(); },
      removeCard(id) { state.cards = state.cards.filter(c => c.id !== id); render(); },
    };
  }

  // ─────────────────── calendar (mensal, com DnD) ───────────────────

  function calendar(target, opts = {}) {
    const state = {
      year:  opts.year  || new Date().getFullYear(),
      month: opts.month != null ? opts.month : new Date().getMonth(),  // 0-11
      events: opts.events || [],
      draggable: opts.draggable !== false,
    };
    const root = el('div', { class: 'pe-cal' });
    if (target) target.replaceChildren(root);

    function eventsOn(iso) {
      return state.events.filter(e => e.date === iso);
    }

    function render() {
      const first = new Date(state.year, state.month, 1);
      const firstDow = first.getDay();
      const daysIn = new Date(state.year, state.month + 1, 0).getDate();
      const cells = [];
      const monthName = first.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
      const todayIso = fmt.iso(new Date());

      // dias do mês anterior para preencher
      const prevDays = new Date(state.year, state.month, 0).getDate();
      for (let i = firstDow - 1; i >= 0; i--) {
        const d = new Date(state.year, state.month - 1, prevDays - i);
        cells.push({ date: d, out: true });
      }
      for (let d = 1; d <= daysIn; d++) {
        cells.push({ date: new Date(state.year, state.month, d), out: false });
      }
      // próximo mês até completar grid múltiplo de 7
      while (cells.length % 7 !== 0) {
        const d = cells[cells.length - 1].date;
        const next = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1);
        cells.push({ date: next, out: next.getMonth() !== state.month });
      }

      root.replaceChildren(
        el('div', { class: 'pe-cal__header' },
          el('button', { class: 'pe-cal__nav', onclick: () => { state.month--; if (state.month < 0) { state.month = 11; state.year--; } render(); } }, '‹'),
          el('div', { class: 'pe-cal__title' }, monthName.charAt(0).toUpperCase() + monthName.slice(1)),
          el('button', { class: 'pe-cal__nav', onclick: () => { state.month++; if (state.month > 11) { state.month = 0; state.year++; } render(); } }, '›'),
        ),
        el('div', { class: 'pe-cal__grid' },
          ...['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'].map(d => el('div', { class: 'pe-cal__dow' }, d)),
          ...cells.map(cell => {
            const iso = fmt.iso(cell.date);
            const evs = eventsOn(iso);
            const classes = ['pe-cal__cell'];
            if (cell.out) classes.push('pe-cal__cell--out');
            if (iso === todayIso) classes.push('pe-cal__cell--today');
            const cellEl = el('div', {
              class: classes.join(' '),
              dataset: { iso },
              ondragover: e => { if (state.draggable) { e.preventDefault(); cellEl.classList.add('pe-cal__cell--drop'); } },
              ondragleave: () => cellEl.classList.remove('pe-cal__cell--drop'),
              ondrop: e => {
                e.preventDefault();
                cellEl.classList.remove('pe-cal__cell--drop');
                const eid = e.dataTransfer.getData('text/plain');
                const ev = state.events.find(x => x.id === eid);
                if (!ev || ev.date === iso) return;
                const old = ev.date;
                ev.date = iso;
                opts.onEventDrop?.(eid, iso, old);
                emit(root, 'event-drop', { id: eid, newDate: iso, oldDate: old });
                render();
              },
              onclick: e => { if (e.target === cellEl) opts.onDayClick?.(iso); },
            },
              el('div', { class: 'pe-cal__day' }, String(cell.date.getDate())),
              ...evs.map(ev => el('div', {
                class: 'pe-cal__event',
                draggable: state.draggable ? 'true' : 'false',
                style: ev.color ? { background: ev.color } : null,
                title: ev.title,
                ondragstart: e => {
                  e.dataTransfer.setData('text/plain', ev.id);
                  e.dataTransfer.effectAllowed = 'move';
                  e.target.classList.add('dragging');
                  e.stopPropagation();
                },
                ondragend: e => e.target.classList.remove('dragging'),
                onclick: e => { e.stopPropagation(); opts.onEventClick?.(ev); },
              }, ev.title)),
            );
            return cellEl;
          }),
        ),
      );
    }

    render();
    return {
      element: root,
      update(events) { state.events = events; render(); },
      goto(year, month) { state.year = year; state.month = month; render(); },
    };
  }

  // ─────────────────── chart donut (SVG) ───────────────────

  function chartDonut(target, opts = {}) {
    const root = el('div', { class: 'pe-chart' });
    if (target) target.replaceChildren(root);
    const data = opts.data || [];
    const total = opts.total ?? data.reduce((s, d) => s + (d.value || 0), 0);
    const W = 200, R = 80, S = 22, CX = W / 2, CY = W / 2;
    let acc = 0;
    const arcs = data.map(d => {
      const frac = total > 0 ? d.value / total : 0;
      const a0 = acc * Math.PI * 2 - Math.PI / 2;
      acc += frac;
      const a1 = acc * Math.PI * 2 - Math.PI / 2;
      const large = frac > 0.5 ? 1 : 0;
      const x0 = CX + R * Math.cos(a0), y0 = CY + R * Math.sin(a0);
      const x1 = CX + R * Math.cos(a1), y1 = CY + R * Math.sin(a1);
      const path = `M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1}`;
      return { d, path, color: d.color || 'var(--acc)' };
    });

    const svg = `<svg viewBox="0 0 ${W} ${W}" width="${W}" height="${W}" style="display:block;margin:0 auto">
      ${arcs.map(a => `<path d="${a.path}" fill="none" stroke="${a.color}" stroke-width="${S}"/>`).join('')}
      <text x="${CX}" y="${CY - 6}" text-anchor="middle" fill="var(--ink)" font-family="var(--font-mono)" font-size="22" font-weight="700">${fmt.num(total)}</text>
      <text x="${CX}" y="${CY + 14}" text-anchor="middle" fill="var(--ink-3)" font-family="var(--font-ui)" font-size="11">${opts.totalLabel || 'total'}</text>
    </svg>`;

    root.replaceChildren(
      opts.title ? el('div', { class: 'pe-chart__title' }, opts.title) : '',
      el('div', { /* spacer */ }),
    );
    // inject svg
    const svgWrap = el('div', {});
    svgWrap.innerHTML = svg;
    root.appendChild(svgWrap);
    root.appendChild(el('div', { class: 'pe-chart__legend' },
      ...data.map(d => el('span', { class: 'pe-chart__legend-item' },
        el('span', { class: 'swatch', style: { background: d.color || 'var(--acc)' } }),
        `${d.label} · ${fmt.num(d.value)}`,
      )),
    ));

    return { element: root };
  }

  // ─────────────────── chart line (SVG) ───────────────────

  function chartLine(target, opts = {}) {
    const root = el('div', { class: 'pe-chart' });
    if (target) target.replaceChildren(root);
    const series = opts.series || [];
    const W = opts.width || 480, H = opts.height || 200, P = 32;
    const allPts = series.flatMap(s => s.points);
    const xs = allPts.map(p => +p.x), ys = allPts.map(p => +p.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(0, ...ys), yMax = Math.max(...ys, 1);
    const sx = x => P + (W - 2 * P) * (xMax === xMin ? 0.5 : (x - xMin) / (xMax - xMin));
    const sy = y => H - P - (H - 2 * P) * (y - yMin) / (yMax - yMin);

    const grid = [0, 0.25, 0.5, 0.75, 1].map(t => {
      const y = P + (H - 2 * P) * (1 - t);
      const val = yMin + t * (yMax - yMin);
      return `<line x1="${P}" y1="${y}" x2="${W - P}" y2="${y}" stroke="var(--line)" stroke-dasharray="2 4"/>
              <text x="${P - 6}" y="${y + 4}" text-anchor="end" fill="var(--ink-3)" font-size="10" font-family="var(--font-mono)">${fmt.num(val, 0)}</text>`;
    }).join('');

    const paths = series.map((s, i) => {
      const color = s.color || ['var(--acc)', 'var(--green)', 'var(--amber)', 'var(--red)'][i % 4];
      const d = s.points.map((p, j) => `${j === 0 ? 'M' : 'L'} ${sx(+p.x)} ${sy(+p.y)}`).join(' ');
      return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2"/>`;
    }).join('');

    const svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none">
      ${grid}${paths}
    </svg>`;

    root.replaceChildren(
      opts.title ? el('div', { class: 'pe-chart__title' }, opts.title) : '',
    );
    const wrap = el('div', {}); wrap.innerHTML = svg;
    root.appendChild(wrap);
    root.appendChild(el('div', { class: 'pe-chart__legend' },
      ...series.map((s, i) => el('span', { class: 'pe-chart__legend-item' },
        el('span', { class: 'swatch', style: { background: s.color || ['var(--acc)','var(--green)','var(--amber)','var(--red)'][i % 4] } }),
        s.label,
      )),
    ));
    return { element: root };
  }

  // ─────────────────── chat ───────────────────

  function chat(target, opts = {}) {
    const state = {
      messages: opts.messages || [],
      currentUser: opts.currentUser || 'eu',
    };
    const root = el('div', { class: 'pe-chat' });
    if (target) target.replaceChildren(root);

    let thread, input;

    function renderThread() {
      thread.replaceChildren(...state.messages.map(m => {
        const self = m.author === state.currentUser;
        return el('div', { class: 'pe-chat__msg' + (self ? ' pe-chat__msg--self' : '') },
          !self ? el('div', { class: 'pe-chat__msg-author' }, m.author) : null,
          el('div', {}, m.text),
          el('div', { class: 'pe-chat__msg-meta' }, fmt.dt(m.ts)),
        );
      }));
      thread.scrollTop = thread.scrollHeight;
    }

    function render() {
      thread = el('div', { class: 'pe-chat__thread' });
      input = el('input', {
        class: 'pe-input', placeholder: 'Mensagem...',
        onkeydown: e => { if (e.key === 'Enter') send(); },
      });
      root.replaceChildren(
        thread,
        el('div', { class: 'pe-chat__input' },
          input,
          el('button', { class: 'pe-btn pe-btn--primary', onclick: send }, 'Enviar'),
        ),
      );
      renderThread();
    }

    function send() {
      const text = input.value.trim();
      if (!text) return;
      const msg = { id: uuid(), author: state.currentUser, text, ts: new Date().toISOString() };
      state.messages.push(msg);
      opts.onSend?.(msg);
      emit(root, 'send', msg);
      input.value = '';
      renderThread();
    }

    render();
    return {
      element: root,
      append(msg) { state.messages.push(msg); renderThread(); },
      update(messages) { state.messages = messages; renderThread(); },
    };
  }

  // ─────────────────── camera ───────────────────

  function camera(opts = {}) {
    const video = el('video', { autoplay: 'true', playsinline: 'true', muted: 'true' });
    const preview = el('img', { alt: 'captura', style: { display: 'none' } });
    let stream = null;

    const captureBtn = el('button', { class: 'pe-btn pe-btn--primary', onclick: capture }, '📸 Capturar');
    const retakeBtn  = el('button', { class: 'pe-btn', style: { display: 'none' }, onclick: retake }, 'Refazer');

    const root = el('div', { class: 'pe-cam' },
      video, preview,
      el('div', { class: 'pe-cam__actions' }, captureBtn, retakeBtn),
    );

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: opts.facing || 'environment' }, audio: false,
        });
        video.srcObject = stream;
      } catch (e) {
        root.replaceChildren(el('div', { style: { color: 'var(--red)' } },
          'Câmera indisponível: ' + e.message));
      }
    }

    function stop() {
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    }

    function capture() {
      const c = document.createElement('canvas');
      c.width = video.videoWidth; c.height = video.videoHeight;
      c.getContext('2d').drawImage(video, 0, 0);
      const data = c.toDataURL('image/jpeg', opts.quality ?? 0.8);
      preview.src = data;
      preview.style.display = 'block';
      video.style.display = 'none';
      captureBtn.style.display = 'none';
      retakeBtn.style.display = 'inline-block';
      opts.onCapture?.(data);
      emit(root, 'capture', { dataUrl: data });
    }

    function retake() {
      preview.style.display = 'none';
      video.style.display = 'block';
      captureBtn.style.display = 'inline-block';
      retakeBtn.style.display = 'none';
    }

    return {
      element: root,
      start, stop, capture, retake,
    };
  }

  // ─────────────────── gantt ───────────────────

  function gantt(target, opts = {}) {
    const state = {
      tasks: opts.tasks || [],
      range: opts.range || {
        start: fmt.iso(new Date()),
        end:   fmt.iso(new Date(Date.now() + 30 * 86400 * 1000)),
      },
      draggable: opts.draggable !== false,
    };
    const root = el('div', { class: 'pe-gantt' });
    if (target) target.replaceChildren(root);

    function daysBetween(a, b) {
      return Math.round((new Date(b) - new Date(a)) / 86400000);
    }

    function render() {
      const totalDays = daysBetween(state.range.start, state.range.end) + 1;
      const colWidth = 28;
      const labelWidth = 160;
      const todayIso = fmt.iso(new Date());

      const grid = el('div', { class: 'pe-gantt__grid', style: {
        gridTemplateColumns: `${labelWidth}px repeat(${totalDays}, ${colWidth}px)`,
      } });

      // header row
      grid.appendChild(el('div', { class: 'pe-gantt__label pe-gantt__header' }, 'Tarefa'));
      for (let i = 0; i < totalDays; i++) {
        const d = new Date(new Date(state.range.start).getTime() + i * 86400000);
        const iso = fmt.iso(d);
        grid.appendChild(el('div', {
          class: 'pe-gantt__head-cell pe-gantt__header' + (iso === todayIso ? ' pe-gantt__cell--today' : ''),
        }, String(d.getDate())));
      }

      // task rows
      for (const t of state.tasks) {
        grid.appendChild(el('div', { class: 'pe-gantt__label' }, t.label));
        for (let i = 0; i < totalDays; i++) {
          const iso = fmt.iso(new Date(new Date(state.range.start).getTime() + i * 86400000));
          const cell = el('div', {
            class: 'pe-gantt__cell' + (iso === todayIso ? ' pe-gantt__cell--today' : ''),
            ondragover: e => { if (state.draggable) e.preventDefault(); },
            ondrop: e => {
              e.preventDefault();
              const tid = e.dataTransfer.getData('text/plain');
              const task = state.tasks.find(x => x.id === tid);
              if (!task) return;
              const dur = daysBetween(task.start, task.end);
              const oldStart = task.start;
              task.start = iso;
              task.end = fmt.iso(new Date(new Date(iso).getTime() + dur * 86400000));
              opts.onTaskMove?.(tid, task.start, task.end, oldStart);
              emit(root, 'task-move', { id: tid, start: task.start, end: task.end });
              render();
            },
          });
          // place bar in the start cell
          const startOffset = daysBetween(state.range.start, t.start);
          if (i === startOffset) {
            const span = daysBetween(t.start, t.end) + 1;
            const bar = el('div', {
              class: 'pe-gantt__bar',
              draggable: state.draggable ? 'true' : 'false',
              style: { width: (colWidth * span - 4) + 'px', background: t.color || 'var(--acc)' },
              title: `${t.label} (${fmt.date(t.start)} → ${fmt.date(t.end)})`,
              ondragstart: e => { e.dataTransfer.setData('text/plain', t.id); e.target.classList.add('dragging'); },
              ondragend: e => e.target.classList.remove('dragging'),
              onclick: () => { opts.onTaskClick?.(t); emit(root, 'task-click', t); },
            }, t.label);
            cell.appendChild(bar);
          }
          grid.appendChild(cell);
        }
      }

      root.replaceChildren(grid);
    }

    render();
    return {
      element: root,
      update(tasks) { state.tasks = tasks; render(); },
      setRange(start, end) { state.range = { start, end }; render(); },
    };
  }

  // ─────────────────── bootstrap ───────────────────

  function bootstrap(opts = {}) {
    const cfg = {
      modulo: opts.modulo || 'pmoc_demo',
      nucleo: opts.nucleo || 'http://localhost:8010',
      ...opts,
    };
    // garante CSS carregado
    if (!document.getElementById('pe-css')) {
      const link = el('link', { id: 'pe-css', rel: 'stylesheet', href: opts.cssPath || '/assets/pmoc-engine.css' });
      document.head.appendChild(link);
    }
    return { ...cfg, version: VERSION };
  }

  // ─────────────────── exports ───────────────────

  global.engine = {
    VERSION,
    bootstrap,
    header, modal, badge, confirm: confirmDlg,
    table, kanban, calendar, chartDonut, chartLine,
    chat, camera, gantt,
    utils: { el, $, $$, fmt, uuid, emit },
  };

})(typeof window !== 'undefined' ? window : globalThis);
