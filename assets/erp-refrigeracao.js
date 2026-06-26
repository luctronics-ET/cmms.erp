/**
 * erp-refrigeracao.js — página rica de Refrigeração no módulo Manutenção.
 *
 * window.erpRefrig.render(container) — monta sub-abas Inventário / Alertas /
 * Térmico / PMOC. Lê /api/pmoc/refrigeracao (ativo+pmoc+ambiente), deriva
 * gás/criticidade/carga térmica via window.RefrigEngine. Tabelas usam .tbl
 * (tbl-enhance dá sort+filtro).
 *
 * ponytail: capacidade usa equipe-padrão fixa (1 equipe, 8h, seg-sex) até a
 *   config de equipe via estrutura/cargos existir. Trocar quando a aba Equipe vier.
 */
(function () {
  'use strict';

  var TEAM_DEFAULT = { equipes: 1, diasUteis: [1, 2, 3, 4, 5], turnos: [{ horas: 8 }] };
  var TIPO_REV = { AC_SPLIT: 'SPLIT', AC_PISO_TETO: 'PISO/TETO', AC_JANELA: 'JANELA', AC_SELF: 'SELF CONTAINED' };

  var state = { rows: [], equipe: [], servicos: [], sub: 'inventario', loaded: false };

  function toEngine(r) {
    return {
      id: r.ativo_id,
      tipo: TIPO_REV[r.ativo_tipo] || 'SPLIT',
      btu: r.btu,
      estado: r.estado_conservacao,
      fabricante: r.fabricante,
      funciona: r.funciona,
      refrigPermanente: !!r.permanencia,
      criticidade: r.criticidade,
      criticidadeManual: false,
      obs: r.obs || '',
      local: r.local_nome || '',
      predio: r.predio_nome || r.local_nome || '',
      ultimaManutencao: r.ultima_manutencao,
    };
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
  function critBadge(c) {
    var col = (window.RefrigEngine.CRIT_COLOR[c]) || '#64748b';
    return '<span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;color:#fff;background:' + col + '">' + esc(c) + '</span>';
  }
  function statusBadge(f) {
    var ok = f === 'OK';
    return '<span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;color:#fff;background:' + (ok ? '#22c55e' : '#ef4444') + '">' + esc(f || '—') + '</span>';
  }

  function kpiRow(items) {
    return '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">' +
      items.map(function (k) {
        return '<div style="flex:1;min-width:130px;background:var(--bg2,#0d1e33);border:1px solid var(--border,#1c3350);border-radius:12px;padding:12px 14px">' +
          '<div style="font-size:22px;font-weight:800;color:' + (k.color || 'var(--acc,#00b4d8)') + '">' + k.value + '</div>' +
          '<div style="font-size:11px;color:var(--text3,#9fb3cc);text-transform:uppercase;letter-spacing:.5px">' + esc(k.label) + '</div>' +
          (k.sub ? '<div style="font-size:11px;color:var(--text2,#9fb3cc);margin-top:2px">' + esc(k.sub) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
  }

  // ── sub-renders ────────────────────────────────────────────────────────
  function renderInventario() {
    var E = window.RefrigEngine;
    var rows = state.rows;
    var nNok = rows.filter(function (r) { return r.funciona === 'NOK'; }).length;
    var critCount = {};
    rows.forEach(function (r) { var c = E.autoCrit(toEngine(r)); critCount[c] = (critCount[c] || 0) + 1; });
    var kpis = kpiRow([
      { label: 'Máquinas', value: rows.length },
      { label: 'Operantes', value: rows.length - nNok, color: '#22c55e' },
      { label: 'Inoperantes', value: nNok, color: '#ef4444' },
      { label: 'Críticas', value: critCount['CRÍTICA'] || 0, color: '#E52207' },
    ]);
    var body = rows.map(function (r) {
      var e = toEngine(r); var g = E.estimateGas(e); var crit = E.autoCrit(e);
      var loc = (r.predio_nome ? r.predio_nome + ' / ' : '') + (r.local_nome || r.loc_txt || '—');
      return '<tr>' +
        '<td>' + esc(loc) + '</td>' +
        '<td>' + esc(e.tipo) + '</td>' +
        '<td>' + (e.btu || 0).toLocaleString('pt-BR') + '</td>' +
        '<td>' + esc(g.gas) + ' · ' + g.carga + 'g</td>' +
        '<td>' + esc(e.fabricante || '—') + '</td>' +
        '<td>' + esc(e.estado || '—') + '</td>' +
        '<td>' + statusBadge(e.funciona) + '</td>' +
        '<td>' + critBadge(crit) + '</td>' +
        '</tr>';
    }).join('');
    return kpis + '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
      '<th>Local</th><th>Tipo</th><th>BTU</th><th>Gás (est.)</th><th>Fabricante</th><th>Estado</th><th>Status</th><th>Criticidade</th>' +
      '</tr></thead><tbody>' + body + '</tbody></table></div>';
  }

  function renderAlertas() {
    var rows = state.rows;
    var nok = rows.filter(function (r) { return r.funciona === 'NOK'; });
    var vaz = rows.filter(function (r) { return /VAZAMENTO|VAZA/i.test(r.obs || ''); });
    var ver = rows.filter(function (r) { return /VERIFICAR|CHECAR/i.test(r.obs || ''); });
    function grp(title, list, color) {
      if (!list.length) return '';
      var body = list.map(function (r) {
        var loc = (r.predio_nome ? r.predio_nome + ' / ' : '') + (r.local_nome || '—');
        return '<tr><td>' + esc(loc) + '</td><td>' + esc(TIPO_REV[r.ativo_tipo] || '') + '</td><td>' + (r.btu || 0).toLocaleString('pt-BR') + '</td><td>' + esc(r.obs || '—') + '</td></tr>';
      }).join('');
      return '<h3 style="margin:18px 0 8px;color:' + color + ';font-size:14px">' + esc(title) + ' (' + list.length + ')</h3>' +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Local</th><th>Tipo</th><th>BTU</th><th>Observação</th></tr></thead><tbody>' + body + '</tbody></table></div>';
    }
    var html = grp('Inoperantes (NOK)', nok, '#ef4444') + grp('Vazamento', vaz, '#f59e0b') + grp('A verificar', ver, '#3b82f6');
    return html || '<div style="padding:24px;color:var(--text3,#9fb3cc)">Sem alertas.</div>';
  }

  function renderTermico() {
    var E = window.RefrigEngine;
    // agrupa por ambiente (local_id quando houver, senão texto)
    var envs = {};
    state.rows.forEach(function (r) {
      var key = r.local_id || (r.predio_nome + '||' + r.local_nome);
      if (!envs[key]) envs[key] = { nome: (r.predio_nome ? r.predio_nome + ' / ' : '') + (r.local_nome || '—'), area_m2: r.local_area_m2, altura: r.local_altura_m, inst: 0, n: 0 };
      envs[key].inst += (r.btu || 0); envs[key].n += 1;
    });
    var list = Object.keys(envs).map(function (k) { return envs[k]; }).sort(function (a, b) { return a.nome.localeCompare(b.nome, 'pt-BR'); });
    var pend = 0;
    var body = list.map(function (env) {
      var calc = env.area_m2 ? E.calcBTU({ area: env.area_m2, altura: env.altura || 2.7 }) : null;
      var st = E.thermalStatus(env.inst, calc ? E.btuComercial(calc.q_total) : null);
      if (!calc) pend++;
      var col = st.cls === 'ts-sub' ? '#ef4444' : st.cls === 'ts-super' ? '#f59e0b' : st.cls === 'ts-adequado' ? '#22c55e' : '#64748b';
      return '<tr>' +
        '<td>' + esc(env.nome) + '</td>' +
        '<td>' + env.n + '</td>' +
        '<td>' + (env.area_m2 ? env.area_m2 + ' m²' : '—') + '</td>' +
        '<td>' + env.inst.toLocaleString('pt-BR') + '</td>' +
        '<td>' + (calc ? E.btuComercial(calc.q_total).toLocaleString('pt-BR') : '—') + '</td>' +
        '<td><span style="color:' + col + ';font-weight:700">' + esc(st.lbl) + (st.gap != null ? ' (' + (st.gap > 0 ? '+' : '') + st.gap.toFixed(0) + '%)' : '') + '</span></td>' +
        '</tr>';
    }).join('');
    var kpis = kpiRow([
      { label: 'Ambientes', value: list.length },
      { label: 'Sem área (m²)', value: pend, color: '#f59e0b', sub: 'preencher locais.area_m2' },
    ]);
    return kpis + '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
      '<th>Ambiente</th><th>ACs</th><th>Área</th><th>BTU instalado</th><th>BTU calculado</th><th>Diagnóstico</th>' +
      '</tr></thead><tbody>' + body + '</tbody></table></div>' +
      '<p style="font-size:11px;color:var(--text3,#9fb3cc);margin-top:10px">Cálculo nível 1 (NBR 16401) com área/altura do ambiente. Preencha <code>locais.area_m2</code>/<code>altura_m</code> para os pendentes.</p>';
  }

  function renderPMOC() {
    var E = window.RefrigEngine;
    var demH = 0, demOS = 0, critCount = {};
    state.rows.forEach(function (r) {
      var e = toEngine(r); var d = E.demandaAnual(e);
      demH += d.horas; demOS += d.os;
      var c = E.autoCrit(e); critCount[c] = (critCount[c] || 0) + 1;
    });
    var cap = E.capacidade(TEAM_DEFAULT);
    var util = cap.hAno ? (demH / cap.hAno * 100) : 0;
    var utilCol = util > 100 ? '#ef4444' : util > 80 ? '#f59e0b' : '#22c55e';
    var kpis = kpiRow([
      { label: 'Demanda anual (h)', value: Math.round(demH) },
      { label: 'OS/ano estimadas', value: Math.round(demOS) },
      { label: 'Capacidade (h/ano)', value: Math.round(cap.hAno), sub: cap.equipes + ' equipe(s) · ' + cap.hDiaEquipe + 'h/dia' },
      { label: 'Utilização', value: util.toFixed(0) + '%', color: utilCol },
    ]);
    var order = ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'];
    var body = order.filter(function (c) { return critCount[c]; }).map(function (c) {
      return '<tr><td>' + critBadge(c) + '</td><td>' + critCount[c] + '</td><td>' + esc(E.PMOC_INT[c].desc) + '</td></tr>';
    }).join('');
    var eqBody = (state.equipe || []).map(function (t) {
      return '<tr><td>' + esc(t.nome) + '</td><td>' + esc(t.posto || '—') + '</td><td>' + esc(t.setor || '—') + '</td></tr>';
    }).join('');
    var eqBlock = '<h3 style="margin:18px 0 8px;font-size:14px">Equipe técnica · Divisão de Manutenção Especializada (CMASM-13)</h3>' +
      (eqBody
        ? '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Nome</th><th>Posto</th><th>Seção</th></tr></thead><tbody>' + eqBody + '</tbody></table></div>'
        : '<p style="font-size:12px;color:var(--text3,#9fb3cc)">Nenhum técnico lotado na subárvore CMASM-13.</p>');
    return kpis + '<h3 style="margin:18px 0 8px;font-size:14px">Demanda por criticidade</h3>' +
      '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Criticidade</th><th>Máquinas</th><th>Intervalos PMOC</th></tr></thead><tbody>' + body + '</tbody></table></div>' +
      eqBlock +
      '<p style="font-size:11px;color:var(--text3,#9fb3cc);margin-top:10px">' + (state.equipe || []).length + ' técnico(s) reais (estrutura/cargos). Capacidade usa equipe-padrão (1 equipe, 8h, seg-sex) — config de turnos é o próximo passo.</p>';
  }

  function _aplic(s) {
    var ap = s.aplicavel_a;
    if (!ap) return {};
    if (typeof ap === 'string') { try { return JSON.parse(ap); } catch (e) { return {}; } }
    return ap; // já é objeto (API faz parse)
  }
  function _tiposDe(s) { return (_aplic(s).tipos || []).join(', '); }
  function renderServicos() {
    var svc = state.servicos;
    var prev = svc.filter(function (s) { return /prevent/i.test(s.nome || ''); });
    var corr = svc.filter(function (s) { return !/prevent/i.test(s.nome || ''); });
    function tbl(list) {
      var body = list.map(function (s) {
        return '<tr><td class="text-mono">' + esc(s.codigo || '') + '</td><td>' + esc(s.nome) + '</td>' +
          '<td>' + esc(_tiposDe(s)) + '</td><td>' + (s.tempo_estimado_min ? s.tempo_estimado_min + ' min' : '—') + '</td></tr>';
      }).join('');
      return '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Código</th><th>Serviço</th><th>Tipos AC</th><th>Tempo</th></tr></thead><tbody>' + body + '</tbody></table></div>';
    }
    var kpis = kpiRow([
      { label: 'Serviços climatização', value: svc.length },
      { label: 'Preventivas (PMOC)', value: prev.length, color: '#22c55e' },
      { label: 'Corretivas / peças (ARP)', value: corr.length, color: '#f59e0b' },
    ]);
    return kpis +
      '<h3 style="margin:18px 0 8px;font-size:14px">Preventivas PMOC (por tipo)</h3>' + (prev.length ? tbl(prev) : '<p style="font-size:12px;color:var(--text3,#9fb3cc)">Nenhuma preventiva.</p>') +
      '<h3 style="margin:18px 0 8px;font-size:14px">Corretivas e peças (ARP)</h3>' + (corr.length ? tbl(corr) : '<p style="font-size:12px;color:var(--text3,#9fb3cc)">Nenhuma corretiva.</p>');
  }

  var SUBS = [
    { id: 'inventario', label: '📋 Inventário', fn: renderInventario },
    { id: 'alertas', label: '⚠️ Alertas', fn: renderAlertas },
    { id: 'termico', label: '🌡️ Térmico', fn: renderTermico },
    { id: 'pmoc', label: '📅 PMOC', fn: renderPMOC },
    { id: 'servicos', label: '🛠️ Serviços', fn: renderServicos },
  ];

  function paint(container) {
    var bar = SUBS.map(function (s) {
      var on = s.id === state.sub;
      return '<button data-sub="' + s.id + '" style="padding:8px 14px;border-radius:9px;border:1px solid ' +
        (on ? 'var(--acc,#00b4d8)' : 'var(--border,#1c3350)') + ';background:' + (on ? 'rgba(0,180,216,.12)' : 'transparent') +
        ';color:' + (on ? 'var(--acc,#00b4d8)' : 'var(--text2,#9fb3cc)') + ';cursor:pointer;font-size:13px;font-weight:600">' + s.label + '</button>';
    }).join('');
    var cur = SUBS.find(function (s) { return s.id === state.sub; });
    container.innerHTML = '<div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">' + bar + '</div>' +
      '<div id="refrig-sub-body">' + cur.fn() + '</div>';
    container.querySelectorAll('[data-sub]').forEach(function (b) {
      b.onclick = function () { state.sub = b.dataset.sub; paint(container); };
    });
    if (window.tblEnhance) setTimeout(window.tblEnhance, 30);
  }

  function render(container) {
    if (!window.RefrigEngine) { container.innerHTML = '<div style="padding:24px;color:#ef4444">RefrigEngine não carregado.</div>'; return; }
    container.innerHTML = '<div style="padding:24px;color:var(--text3,#9fb3cc)">Carregando refrigeração…</div>';
    Promise.all([
      fetch('/api/pmoc/refrigeracao').then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }),
      fetch('/api/equipe/refrigeracao').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
      fetch('/api/catalogo/servicos').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
    ]).then(function (res) {
      state.rows = res[0] || []; state.equipe = res[1] || [];
      state.servicos = (res[2] || []).filter(function (s) { return (_aplic(s).categorias || []).indexOf('climatizacao') >= 0; });
      state.loaded = true; paint(container);
    }).catch(function (e) {
      container.innerHTML = '<div style="padding:24px;color:#ef4444">Falha ao carregar /api/pmoc/refrigeracao: ' + esc(e.message) + '</div>';
    });
  }

  window.erpRefrig = { render: render };
})();
