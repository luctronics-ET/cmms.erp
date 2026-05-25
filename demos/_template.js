/**
 * Renderer comum dos PMOCs demo. Cada página carrega um objeto MOCK
 * (definido inline ou via /demos/mock/<modulo>.js) e este template
 * monta o layout padrão: header + tabs (dashboard / ativos / OS-kanban /
 * calendário / gantt / chat / docs).
 *
 * MOCK shape: {
 *   modulo, titulo, icon,
 *   user: { nome },
 *   sync: { online, pending, lastSync },
 *   kpis:  [{ label, value, sub }],
 *   donut: { title, data: [{label,value,color}] },
 *   line:  { title, series: [{label,points:[{x,y}]}] },
 *   ativos: { cols, rows },
 *   kanban: { columns, cards },
 *   calendar: { events },
 *   gantt:  { range, tasks },
 *   chat:   { currentUser, messages },
 *   docs:   { cols, rows },
 * }
 */
(function () {
  const { el, fmt } = engine.utils;

  function tabBar(tabs, onChange) {
    const bar = el('div', {
      style: {
        display: 'flex', gap: '4px', padding: '4px',
        background: 'var(--bg2)', borderRadius: '8px',
        marginBottom: '14px', overflowX: 'auto',
      },
    });
    const update = activeId => {
      bar.querySelectorAll('[data-tab]').forEach(b => {
        const on = b.dataset.tab === activeId;
        Object.assign(b.style, {
          background: on ? 'var(--panel)' : 'transparent',
          color: on ? 'var(--ink)' : 'var(--ink-2)',
          boxShadow: on ? 'inset 0 -2px 0 var(--acc)' : 'none',
        });
      });
    };
    tabs.forEach(t => {
      bar.appendChild(el('button', {
        class: 'pe-btn pe-btn--ghost',
        dataset: { tab: t.id },
        style: { borderRadius: '6px', minHeight: '32px', whiteSpace: 'nowrap' },
        onclick: () => { onChange(t.id); update(t.id); },
      }, `${t.icon || ''} ${t.label}`));
    });
    setTimeout(() => update(tabs[0].id), 0);
    return bar;
  }

  function kpiGrid(kpis) {
    return el('div', {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))',
        gap: '12px', marginBottom: '14px',
      },
    }, ...kpis.map(k => el('div', {
      style: {
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: '8px', padding: '12px',
      },
    },
      el('div', { style: { fontSize: '11px', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '.5px' } }, k.label),
      el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '22px', color: 'var(--acc)', fontWeight: '700', marginTop: '4px' } }, String(k.value)),
      k.sub ? el('div', { style: { fontSize: '11px', color: 'var(--ink-2)' } }, k.sub) : null,
    )));
  }

  window.renderPMOC = function renderPMOC(MOCK) {
    document.title = `xCMASM · ${MOCK.titulo}`;

    // header
    engine.header(document.getElementById('hdr'), {
      modulo: `${MOCK.icon || ''} ${MOCK.titulo}`,
      user: MOCK.user,
      syncStatus: MOCK.sync,
    });

    const mountPoint = document.getElementById('app');
    const view = el('div');

    function render(tabId) {
      view.replaceChildren();
      if (tabId === 'dashboard') {
        view.appendChild(kpiGrid(MOCK.kpis || []));
        const row = el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' } });
        const a = el('div'); const b = el('div');
        row.appendChild(a); row.appendChild(b);
        view.appendChild(row);
        if (MOCK.donut) engine.chartDonut(a, MOCK.donut);
        if (MOCK.line)  engine.chartLine(b, MOCK.line);
      }
      if (tabId === 'ativos' && MOCK.ativos) {
        const wrap = el('div');
        view.appendChild(wrap);
        engine.table(wrap, { ...MOCK.ativos, onRowClick: r => {
          const m = engine.modal({
            title: r[MOCK.ativos.cols[0].key],
            body: el('div', {},
              ...MOCK.ativos.cols.map(c =>
                el('div', { style: { display: 'flex', gap: '8px', padding: '6px 0', borderBottom: '1px solid var(--line)' } },
                  el('div', { style: { color: 'var(--ink-3)', minWidth: '120px' } }, c.label),
                  el('div', {}, c.format ? c.format(r[c.key], r) : String(r[c.key] ?? '')),
                )),
            ),
            footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
          });
          m.open();
        }});
      }
      if (tabId === 'os' && MOCK.kanban) {
        const wrap = el('div');
        view.appendChild(wrap);
        engine.kanban(wrap, { ...MOCK.kanban, onCardClick: c => {
          const m = engine.modal({
            title: c.title,
            body: el('div', {},
              el('p', {}, c.descricao || 'Detalhes da OS demo.'),
              c.badges?.length ? el('div', { style: { display: 'flex', gap: '4px', flexWrap: 'wrap' } },
                ...c.badges.map(b => engine.badge(b.text, b.kind))) : null,
            ),
            footer: [
              el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
              el('button', { class: 'pe-btn pe-btn--primary' }, 'Avançar status'),
            ],
          });
          m.open();
        }});
      }
      if (tabId === 'calendar' && MOCK.calendar) {
        const wrap = el('div'); view.appendChild(wrap);
        engine.calendar(wrap, MOCK.calendar);
      }
      if (tabId === 'gantt' && MOCK.gantt) {
        const wrap = el('div'); view.appendChild(wrap);
        engine.gantt(wrap, MOCK.gantt);
      }
      if (tabId === 'chat' && MOCK.chat) {
        const wrap = el('div', { style: { height: '420px' } }); view.appendChild(wrap);
        engine.chat(wrap, MOCK.chat);
      }
      if (tabId === 'docs' && MOCK.docs) {
        const wrap = el('div'); view.appendChild(wrap);
        engine.table(wrap, MOCK.docs);
      }
    }

    const tabs = [
      { id: 'dashboard', icon: '📊', label: 'Dashboard' },
      MOCK.ativos   && { id: 'ativos',   icon: '📦', label: 'Ativos' },
      MOCK.kanban   && { id: 'os',       icon: '🧰', label: 'OS' },
      MOCK.calendar && { id: 'calendar', icon: '📅', label: 'Calendário' },
      MOCK.gantt    && { id: 'gantt',    icon: '📈', label: 'Gantt' },
      MOCK.chat     && { id: 'chat',     icon: '💬', label: 'Chat' },
      MOCK.docs     && { id: 'docs',     icon: '📄', label: 'POPs' },
    ].filter(Boolean);

    mountPoint.replaceChildren(
      el('div', { style: { display: 'flex', alignItems: 'center', marginBottom: '12px' } },
        el('a', { href: '/demo.html', style: { color: 'var(--ink-2)', textDecoration: 'none', fontSize: '13px' } }, '‹ Hub'),
      ),
      tabBar(tabs, render),
      view,
    );
    render('dashboard');
  };
})();
