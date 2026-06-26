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

  var state = { rows: [], equipe: [], servicos: [], estoque: [], sub: 'inventario', loaded: false };

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
  var INV_VIEWS = [
    { id: 'base', label: 'Base' },
    { id: 'eletrico', label: 'Elétrico' },
    { id: 'uso', label: 'Uso / PMOC' },
  ];
  function _loc(r) { return (r.predio_nome ? r.predio_nome + ' / ' : '') + (r.local_nome || r.loc_txt || '—'); }
  function num(v) { return (v == null ? '—' : Number(v).toLocaleString('pt-BR')); }

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
    var view = state.invView || 'base';
    var toggle = '<div style="display:flex;gap:6px;margin-bottom:12px">' + INV_VIEWS.map(function (v) {
      var on = v.id === view;
      return '<button data-invview="' + v.id + '" style="padding:5px 12px;border-radius:8px;border:1px solid ' +
        (on ? 'var(--acc,#00b4d8)' : 'var(--border,#1c3350)') + ';background:' + (on ? 'rgba(0,180,216,.12)' : 'transparent') +
        ';color:' + (on ? 'var(--acc,#00b4d8)' : 'var(--text2,#9fb3cc)') + ';cursor:pointer;font-size:12px">' + v.label + '</button>';
    }).join('') + '</div>';

    var head, body;
    if (view === 'eletrico') {
      head = '<th>Local</th><th>Tipo</th><th>Tensão (V)</th><th>Corrente (A)</th><th>Potência (W)</th><th>Gás (est.)</th><th>Status</th>';
      body = rows.map(function (r) {
        var e = toEngine(r); var g = E.estimateGas(e);
        return '<tr data-ativo="' + esc(r.ativo_id) + '" style="cursor:pointer">' + '<td>' + esc(_loc(r)) + '</td><td>' + esc(e.tipo) + '</td>' +
          '<td>' + num(r.tensao_nominal) + '</td><td>' + num(r.corrente_nominal) + '</td>' +
          '<td>' + num(E.estimatePower(e.btu)) + '</td><td>' + esc(g.gas) + ' · ' + g.carga + 'g</td>' +
          '<td>' + statusBadge(e.funciona) + '</td></tr>';
      }).join('');
    } else if (view === 'uso') {
      head = '<th>Local</th><th>Tipo</th><th>Criticidade</th><th>h/dia</th><th>d/sem</th><th>h/sem</th><th>Uso est. (h)</th><th>Permanente</th><th>Status</th>';
      body = rows.map(function (r) {
        var e = toEngine(r); var crit = E.autoCrit(e);
        var hsem = (r.horas_dia != null && r.dias_semana != null) ? num(r.horas_dia * r.dias_semana) : '—';
        var uso = E.horasUsoEstimado(r.data_instalacao, r.horas_dia, r.dias_semana);
        return '<tr data-ativo="' + esc(r.ativo_id) + '" style="cursor:pointer">' + '<td>' + esc(_loc(r)) + '</td><td>' + esc(e.tipo) + '</td>' +
          '<td>' + critBadge(crit) + '</td><td>' + num(r.horas_dia) + '</td><td>' + num(r.dias_semana) + '</td>' +
          '<td>' + hsem + '</td><td>' + (uso == null ? '—' : num(uso)) + '</td><td>' + (r.permanencia ? '❄️ 24h' : '—') + '</td>' +
          '<td>' + statusBadge(e.funciona) + '</td></tr>';
      }).join('');
    } else {
      head = '<th>Local</th><th>Tipo</th><th>BTU</th><th>Gás (est.)</th><th>Fabricante</th><th>Estado</th><th>Status</th><th>Criticidade</th>';
      body = rows.map(function (r) {
        var e = toEngine(r); var g = E.estimateGas(e); var crit = E.autoCrit(e);
        return '<tr data-ativo="' + esc(r.ativo_id) + '" style="cursor:pointer">' + '<td>' + esc(_loc(r)) + '</td><td>' + esc(e.tipo) + '</td>' +
          '<td>' + num(e.btu) + '</td><td>' + esc(g.gas) + ' · ' + g.carga + 'g</td>' +
          '<td>' + esc(e.fabricante || '—') + '</td><td>' + esc(e.estado || '—') + '</td>' +
          '<td>' + statusBadge(e.funciona) + '</td><td>' + critBadge(crit) + '</td></tr>';
      }).join('');
    }
    return kpis + toggle + '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
      head + '</tr></thead><tbody>' + body + '</tbody></table></div>';
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
    function matsTxt(s) {
      var m = s.materiais || [];
      if (!m.length) return '—';
      return m.map(function (x) {
        var nm = x.estoque_codigo || x.nome_livre || '?';
        return esc(nm) + ' ×' + num(x.qtd) + (x.unidade ? ' ' + esc(x.unidade) : '');
      }).join(', ');
    }
    function tbl(list) {
      var body = list.map(function (s) {
        return '<tr><td class="text-mono">' + esc(s.codigo || '') + '</td><td>' + esc(s.nome) + '</td>' +
          '<td>' + esc(_tiposDe(s)) + '</td><td>' + (s.tempo_estimado_min ? s.tempo_estimado_min + ' min' : '—') + '</td>' +
          '<td style="font-size:11px">' + matsTxt(s) + '</td></tr>';
      }).join('');
      return '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Código</th><th>Serviço</th><th>Tipos AC</th><th>Tempo</th><th>Materiais (consumo)</th></tr></thead><tbody>' + body + '</tbody></table></div>';
    }
    var kpis = kpiRow([
      { label: 'Serviços climatização', value: svc.length },
      { label: 'Preventivas (PMOC)', value: prev.length, color: '#22c55e' },
      { label: 'Corretivas / peças (ARP)', value: corr.length, color: '#f59e0b' },
    ]);
    var actions = '<div style="display:flex;justify-content:flex-end;margin-bottom:10px"><button data-action="novo-servico" style="padding:7px 14px;border-radius:8px;border:none;background:var(--acc,#00b4d8);color:#001018;font-weight:700;cursor:pointer">+ Serviço</button></div>';
    return actions + kpis +
      '<h3 style="margin:18px 0 8px;font-size:14px">Preventivas PMOC (por tipo)</h3>' + (prev.length ? tbl(prev) : '<p style="font-size:12px;color:var(--text3,#9fb3cc)">Nenhuma preventiva.</p>') +
      '<h3 style="margin:18px 0 8px;font-size:14px">Corretivas e peças (ARP)</h3>' + (corr.length ? tbl(corr) : '<p style="font-size:12px;color:var(--text3,#9fb3cc)">Nenhuma corretiva.</p>');
  }

  // ── cronograma de mobilização (porta de pmocCronograma do html) ──────────
  var DOW = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  function fmtD(d) { return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + d.getFullYear(); }
  function renderCronograma() {
    var E = window.RefrigEngine;
    var ordem = ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'];
    // fila: 1ª preventiva de quem ainda não tem histórico (ultima_manutencao vazia)
    var fila = state.rows.filter(function (r) { return !r.ultima_manutencao; }).map(function (r) {
      var e = toEngine(r);
      return { r: r, crit: E.autoCrit(e), min: E.estTempoServico(e, 'PREVENTIVA') };
    }).sort(function (a, b) {
      var d = ordem.indexOf(a.crit) - ordem.indexOf(b.crit);
      return d !== 0 ? d : b.min - a.min;
    });
    if (!fila.length) {
      return '<div style="padding:24px;color:var(--text2,#9fb3cc)"><b>Nenhuma mobilização inicial pendente.</b><br>Todos os equipamentos já têm registro de manutenção; o cronograma recorrente segue as frequências do plano.</div>';
    }
    var cap = E.capacidade(TEAM_DEFAULT);
    var capDiaMin = cap.hDiaTotal * 60 || 240;
    var dias = [], cursor = new Date(); cursor.setHours(0, 0, 0, 0);
    var dia = null, restante = 0, guard = 0;
    function novoDia() {
      while (TEAM_DEFAULT.diasUteis.indexOf(cursor.getDay()) < 0) cursor.setDate(cursor.getDate() + 1);
      dia = { data: new Date(cursor), os: [], usado: 0 }; dias.push(dia);
      restante = capDiaMin; cursor.setDate(cursor.getDate() + 1);
    }
    novoDia();
    fila.forEach(function (job) {
      if (++guard > 5000) return;
      if (job.min > restante && dia.os.length > 0) novoDia();
      dia.os.push(job); dia.usado += job.min; restante -= job.min;
      if (restante <= 0) novoDia();
    });
    if (dias.length && !dias[dias.length - 1].os.length) dias.pop();
    var totalMin = fila.reduce(function (s, j) { return s + j.min; }, 0);
    var kpis = kpiRow([
      { label: 'OS de mobilização', value: fila.length, color: '#E52207', sub: '1ª preventiva por equip.' },
      { label: 'Esforço total', value: (totalMin / 60).toFixed(0) + ' h', color: '#f59e0b' },
      { label: 'Dias úteis', value: dias.length, sub: cap.hDiaTotal + 'h/dia' },
      { label: 'Conclusão', value: dias.length ? fmtD(dias[dias.length - 1].data) : '—', color: '#22c55e' },
    ]);
    var agenda = dias.map(function (d) {
      var pct = Math.min(d.usado / capDiaMin * 100, 100);
      var col = d.usado > capDiaMin ? '#ef4444' : '#22c55e';
      var rows = d.os.map(function (job) {
        var cc = E.CRIT_COLOR[job.crit] || '#64748b';
        var loc = (job.r.predio_nome ? job.r.predio_nome + ' / ' : '') + (job.r.local_nome || '—');
        return '<div data-ativo="' + esc(job.r.ativo_id) + '" style="cursor:pointer;display:flex;gap:10px;align-items:center;padding:5px 8px;border-radius:6px" onmouseover="this.style.background=\'rgba(255,255,255,.04)\'" onmouseout="this.style.background=\'\'">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + cc + ';flex:none"></span>' +
          '<span style="flex:1;font-size:12px">' + esc(loc) + '</span>' +
          '<span style="font-size:11px;color:var(--text3,#9fb3cc)">' + esc(TIPO_REV[job.r.ativo_tipo] || '') + '</span>' +
          '<span style="font-size:11px;color:var(--text2,#9fb3cc);width:60px;text-align:right">' + job.min + ' min</span></div>';
      }).join('');
      return '<div style="background:var(--bg2,#0d1e33);border:1px solid var(--border,#1c3350);border-radius:10px;padding:12px;margin-bottom:10px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
        '<div style="font-weight:700"><span style="color:var(--acc,#00b4d8);margin-right:6px">' + DOW[d.data.getDay()] + '</span>' + fmtD(d.data) + '</div>' +
        '<div style="font-size:12px"><span style="color:' + col + '">' + (d.usado / 60).toFixed(1) + 'h</span> / ' + (capDiaMin / 60).toFixed(0) + 'h · ' + d.os.length + ' OS</div></div>' +
        '<div style="height:6px;background:var(--bg3,#0a1828);border-radius:4px;overflow:hidden;margin-bottom:8px"><div style="height:100%;width:' + pct + '%;background:' + col + '"></div></div>' +
        rows + '</div>';
    }).join('');
    return kpis +
      '<p style="font-size:11px;color:var(--text3,#9fb3cc);margin:10px 0">Mobilização inicial: sem histórico, cada máquina recebe 1ª preventiva completa, distribuída por dia útil respeitando capacidade (' + cap.hDiaTotal + 'h/dia) e priorizada por criticidade. Registre manutenções p/ o plano calcular vencimentos recorrentes.</p>' +
      agenda;
  }

  // ── estoque de refrigeração (consumíveis/sobressalentes/ferramentas) ─────
  function renderEstoque() {
    var itens = state.estoque;
    var baixo = itens.filter(function (i) { return (i.qtd_atual || 0) < (i.qtd_minima || 0); });
    var kpis = kpiRow([
      { label: 'Itens', value: itens.length },
      { label: 'Abaixo do mínimo', value: baixo.length, color: baixo.length ? '#ef4444' : '#22c55e' },
      { label: 'Consumíveis', value: itens.filter(function (i) { return i.categoria === 'consumivel'; }).length },
      { label: 'Ferramentas', value: itens.filter(function (i) { return i.categoria === 'ferramenta'; }).length },
    ]);
    var CATS = [['consumivel', 'Consumíveis'], ['sobressalente', 'Sobressalentes (estoque mínimo)'], ['ferramenta', 'Ferramentas']];
    var html = CATS.map(function (ct) {
      var list = itens.filter(function (i) { return i.categoria === ct[0]; });
      if (!list.length) return '';
      var body = list.map(function (i) {
        var low = (i.qtd_atual || 0) < (i.qtd_minima || 0);
        var badge = low ? '<span style="display:inline-block;padding:1px 7px;border-radius:9px;font-size:10px;font-weight:700;color:#fff;background:#ef4444">Baixo</span>' : '<span style="color:#22c55e">OK</span>';
        return '<tr><td class="text-mono">' + esc(i.codigo || '') + '</td><td>' + esc(i.nome) + '</td>' +
          '<td>' + num(i.qtd_atual) + ' ' + esc(i.unidade || '') + '</td><td>' + num(i.qtd_minima) + '</td>' +
          '<td>' + badge + '</td></tr>';
      }).join('');
      return '<h3 style="margin:18px 0 8px;font-size:14px">' + esc(ct[1]) + ' (' + list.length + ')</h3>' +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Código</th><th>Item</th><th>Qtd atual</th><th>Mínimo</th><th>Status</th></tr></thead><tbody>' + body + '</tbody></table></div>';
    }).join('');
    return kpis + (html || '<p style="padding:24px;color:var(--text3,#9fb3cc)">Sem itens de estoque de refrigeração.</p>');
  }

  var SUBS = [
    { id: 'inventario', label: '📋 Inventário', fn: renderInventario },
    { id: 'alertas', label: '⚠️ Alertas', fn: renderAlertas },
    { id: 'termico', label: '🌡️ Térmico', fn: renderTermico },
    { id: 'pmoc', label: '📅 PMOC', fn: renderPMOC },
    { id: 'cronograma', label: '🗓️ Cronograma', fn: renderCronograma },
    { id: 'servicos', label: '🛠️ Serviços', fn: renderServicos },
    { id: 'estoque', label: '📦 Estoque', fn: renderEstoque },
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
    container.querySelectorAll('[data-invview]').forEach(function (b) {
      b.onclick = function () { state.invView = b.dataset.invview; paint(container); };
    });
    container.querySelectorAll('[data-ativo]').forEach(function (el) {
      el.addEventListener('click', function () { openFicha(el.dataset.ativo, container); });
    });
    var nv = container.querySelector('[data-action="novo-servico"]');
    if (nv) nv.onclick = function () { openNovoServico(container); };
    if (window.tblEnhance) setTimeout(window.tblEnhance, 30);
  }

  // ── ficha do ativo (detalhe + edição) ───────────────────────────────────
  var SELECTS = {
    funciona: ['OK', 'NOK'],
    estado_conservacao: ['NOVA', 'SEMI', 'VELHA'],
    criticidade: ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'],
  };
  function fld(label, name, val, type) {
    var v = val == null ? '' : val;
    var input;
    if (SELECTS[name]) {
      input = '<select name="' + name + '" style="width:100%;padding:6px 8px;border-radius:7px;border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text1,#e6eefc)">' +
        '<option value=""></option>' + SELECTS[name].map(function (o) { return '<option' + (String(v) === o ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>';
    } else if (type === 'check') {
      input = '<input type="checkbox" name="' + name + '"' + (v ? ' checked' : '') + ' style="width:18px;height:18px">';
    } else {
      input = '<input name="' + name + '" type="' + (type || 'text') + '" value="' + esc(v) + '" style="width:100%;box-sizing:border-box;padding:6px 8px;border-radius:7px;border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text1,#e6eefc)">';
    }
    return '<label style="display:flex;flex-direction:column;gap:3px;font-size:11px;color:var(--text3,#9fb3cc)">' + esc(label) + input + '</label>';
  }
  function grp(title, html) {
    return '<div style="margin-bottom:14px"><div style="font-size:12px;font-weight:700;color:var(--acc,#00b4d8);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;border-bottom:1px solid var(--border,#1c3350);padding-bottom:4px">' + esc(title) + '</div>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">' + html + '</div></div>';
  }

  var _fichaOverlay = null;
  function closeFicha() { if (_fichaOverlay) { _fichaOverlay.remove(); _fichaOverlay = null; } }

  function openFicha(ativoId, container) {
    var E = window.RefrigEngine;
    var r = state.rows.find(function (x) { return String(x.ativo_id) === String(ativoId); });
    if (!r) return;
    var e = toEngine(r); var g = E.estimateGas(e); var crit = E.autoCrit(e);
    var loc = (r.predio_nome ? r.predio_nome + ' / ' : '') + (r.local_nome || r.loc_txt || '—');
    closeFicha();
    var ov = document.createElement('div');
    ov.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.55);display:flex;align-items:flex-start;justify-content:center;overflow:auto;padding:30px 12px';
    var derived = '<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--text2,#9fb3cc);background:var(--bg3,#0a1828);border-radius:8px;padding:10px 12px;margin-bottom:14px">' +
      '<span>Gás (est.): <b style="color:var(--text1,#e6eefc)">' + esc(g.gas) + ' · ' + g.carga + 'g</b></span>' +
      '<span>Potência: <b style="color:var(--text1,#e6eefc)">' + E.estimatePower(e.btu) + ' W</b></span>' +
      (function () { var u = E.horasUsoEstimado(r.data_instalacao, r.horas_dia, r.dias_semana); return '<span>Uso est.: <b style="color:var(--text1,#e6eefc)">' + (u == null ? '— (preencha instalação)' : u + ' h') + '</b></span>'; })() +
      '<span>Criticidade (auto): ' + critBadge(crit) + '</span>' +
      '<span>PMOC: <b style="color:var(--text1,#e6eefc)">' + esc((E.PMOC_INT[crit] || {}).desc || '') + '</b></span></div>';
    ov.innerHTML = '<div style="background:var(--bg2,#0d1e33);border:1px solid var(--border,#1c3350);border-radius:14px;max-width:760px;width:100%;padding:20px;color:var(--text1,#e6eefc)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
      '<h2 style="margin:0;font-size:18px">❄️ ' + esc(r.ativo_nome || r.ativo_id) + '</h2>' +
      '<button id="ficha-x" style="background:none;border:none;color:var(--text3,#9fb3cc);font-size:22px;cursor:pointer">×</button></div>' +
      '<div style="font-size:12px;color:var(--text3,#9fb3cc);margin-bottom:14px">' + esc(r.ativo_id) + ' · ' + esc(loc) + '</div>' +
      derived +
      '<form id="ficha-form">' +
      grp('Identificação', fld('Nome', 'nome', r.ativo_nome) + fld('Patrimônio', 'patrimonio', r.patrimonio) + fld('Fabricante', 'fabricante', r.fabricante) + fld('BTU', 'btu', r.btu, 'number')) +
      grp('Estado', fld('Funciona', 'funciona', r.funciona) + fld('Conservação', 'estado_conservacao', r.estado_conservacao) + fld('Criticidade (manual)', 'criticidade', r.criticidade)) +
      grp('Elétrico', fld('Tensão (V)', 'tensao_nominal', r.tensao_nominal, 'number') + fld('Corrente (A)', 'corrente_nominal', r.corrente_nominal, 'number') + fld('Quadro', 'quadro', r.quadro) + fld('Disjuntor', 'disjuntor', r.disjuntor) + fld('Cabo', 'cabo', r.cabo)) +
      grp('Uso / PMOC', fld('h/dia', 'horas_dia', r.horas_dia, 'number') + fld('dias/semana', 'dias_semana', r.dias_semana, 'number') + fld('Permanente 24h', 'permanencia', r.permanencia, 'check') + fld('Instalação', 'data_instalacao', (r.data_instalacao || '').slice(0, 10), 'date') + fld('Última manutenção', 'ultima_manutencao', (r.ultima_manutencao || '').slice(0, 10), 'date')) +
      grp('Observações', '<label style="grid-column:1/-1;display:flex;flex-direction:column;gap:3px;font-size:11px;color:var(--text3,#9fb3cc)">Obs<textarea name="obs" rows="2" style="width:100%;box-sizing:border-box;padding:6px 8px;border-radius:7px;border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text1,#e6eefc)">' + esc(r.obs || '') + '</textarea></label>') +
      '<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">' +
      '<button type="button" id="ficha-cancel" style="padding:8px 16px;border-radius:8px;border:1px solid var(--border,#1c3350);background:transparent;color:var(--text2,#9fb3cc);cursor:pointer">Cancelar</button>' +
      '<button type="submit" style="padding:8px 16px;border-radius:8px;border:none;background:var(--acc,#00b4d8);color:#001018;font-weight:700;cursor:pointer">Salvar</button></div>' +
      '</form></div>';
    document.body.appendChild(ov);
    _fichaOverlay = ov;
    ov.querySelector('#ficha-x').onclick = closeFicha;
    ov.querySelector('#ficha-cancel').onclick = closeFicha;
    ov.onclick = function (ev) { if (ev.target === ov) closeFicha(); };
    ov.querySelector('#ficha-form').onsubmit = function (ev) { ev.preventDefault(); saveFicha(ativoId, ev.target, container); };
  }

  var NUMS = { btu: 1, tensao_nominal: 1, corrente_nominal: 1, horas_dia: 1, dias_semana: 1 };
  function saveFicha(ativoId, form, container) {
    var fd = new FormData(form);
    var body = {};
    fd.forEach(function (v, k) { body[k] = NUMS[k] ? (v === '' ? null : Number(v)) : v; });
    body.permanencia = form.querySelector('[name=permanencia]').checked ? 1 : 0;
    // ativo nome vai pra ativos; patrimonio existe nos dois — manda nos dois
    if (body.patrimonio != null) body.pat = body.patrimonio;
    fetch('/api/pmoc/refrigeracao/' + encodeURIComponent(ativoId), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function () {
      closeFicha();
      render(container); // recarrega dados frescos do backend
    }).catch(function (err) {
      alert('Falha ao salvar: ' + err.message);
    });
  }

  function render(container) {
    if (!window.RefrigEngine) { container.innerHTML = '<div style="padding:24px;color:#ef4444">RefrigEngine não carregado.</div>'; return; }
    container.innerHTML = '<div style="padding:24px;color:var(--text3,#9fb3cc)">Carregando refrigeração…</div>';
    Promise.all([
      fetch('/api/pmoc/refrigeracao').then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }),
      fetch('/api/equipe/refrigeracao').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
      fetch('/api/catalogo/servicos?materiais=1').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
      fetch('/api/estoque').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
    ]).then(function (res) {
      state.rows = res[0] || []; state.equipe = res[1] || [];
      state.servicos = (res[2] || []).filter(function (s) { return (_aplic(s).categorias || []).indexOf('climatizacao') >= 0; });
      state.estoque = (res[3] || []).filter(function (i) { return i.obs === 'refrigeracao'; });
      state.loaded = true; paint(container);
    }).catch(function (e) {
      container.innerHTML = '<div style="padding:24px;color:#ef4444">Falha ao carregar /api/pmoc/refrigeracao: ' + esc(e.message) + '</div>';
    });
  }

  // ── criar serviço padrão (catálogo compartilhado) ───────────────────────
  var AC_TIPOS = ['AC_SPLIT', 'AC_PISO_TETO', 'AC_JANELA', 'AC_SELF', 'AC_CHILLER'];
  function openNovoServico(container) {
    closeFicha();
    var ov = document.createElement('div');
    ov.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.55);display:flex;align-items:flex-start;justify-content:center;overflow:auto;padding:40px 12px';
    ov.innerHTML = '<div style="background:var(--bg2,#0d1e33);border:1px solid var(--border,#1c3350);border-radius:14px;max-width:560px;width:100%;padding:20px;color:var(--text1,#e6eefc)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h2 style="margin:0;font-size:18px">🛠️ Novo serviço de refrigeração</h2><button id="ns-x" style="background:none;border:none;color:var(--text3,#9fb3cc);font-size:22px;cursor:pointer">×</button></div>' +
      '<form id="ns-form" style="display:grid;gap:12px">' +
      fld('Código', 'codigo', '') + fld('Nome', 'nome', '') +
      fld('Tempo estimado (min)', 'tempo_estimado_min', '', 'number') +
      '<label style="font-size:11px;color:var(--text3,#9fb3cc)">Tipos AC aplicáveis<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:6px">' +
      AC_TIPOS.map(function (t) { return '<label style="display:flex;gap:5px;align-items:center;font-size:12px;color:var(--text1,#e6eefc);text-transform:none"><input type="checkbox" name="tipo" value="' + t + '">' + t + '</label>'; }).join('') + '</div></label>' +
      '<label style="font-size:11px;color:var(--text3,#9fb3cc)">Descrição / tarefas<textarea name="descricao" rows="3" style="width:100%;box-sizing:border-box;padding:6px 8px;border-radius:7px;border:1px solid var(--border,#1c3350);background:var(--bg3,#0a1828);color:var(--text1,#e6eefc)"></textarea></label>' +
      '<div style="display:flex;gap:10px;justify-content:flex-end"><button type="button" id="ns-cancel" style="padding:8px 16px;border-radius:8px;border:1px solid var(--border,#1c3350);background:transparent;color:var(--text2,#9fb3cc);cursor:pointer">Cancelar</button>' +
      '<button type="submit" style="padding:8px 16px;border-radius:8px;border:none;background:var(--acc,#00b4d8);color:#001018;font-weight:700;cursor:pointer">Criar</button></div>' +
      '</form></div>';
    document.body.appendChild(ov);
    _fichaOverlay = ov;
    ov.querySelector('#ns-x').onclick = closeFicha;
    ov.querySelector('#ns-cancel').onclick = closeFicha;
    ov.onclick = function (ev) { if (ev.target === ov) closeFicha(); };
    ov.querySelector('#ns-form').onsubmit = function (ev) { ev.preventDefault(); saveNovoServico(ev.target, container); };
  }
  function saveNovoServico(form, container) {
    var fd = new FormData(form);
    var tipos = []; form.querySelectorAll('[name=tipo]:checked').forEach(function (c) { tipos.push(c.value); });
    var codigo = (fd.get('codigo') || '').trim();
    var nome = (fd.get('nome') || '').trim();
    if (!codigo || !nome) { alert('Código e nome obrigatórios.'); return; }
    var body = {
      codigo: codigo, nome: nome, descricao: fd.get('descricao') || null, escopo: 'local',
      tempo_estimado_min: fd.get('tempo_estimado_min') ? Number(fd.get('tempo_estimado_min')) : null,
      aplicavel_a: { categorias: ['climatizacao'], tipos: tipos }, criado_por_modulo: 'refrigeracao',
    };
    var token = localStorage.getItem('xcmasm_token');
    var headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    fetch('/api/catalogo/servicos', { method: 'POST', headers: headers, body: JSON.stringify(body) })
      .then(function (res) {
        if (res.status === 401) throw new Error('Faça login (não-visitante) para criar serviços.');
        if (res.status === 409) throw new Error('Código já existe.');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      }).then(function () { closeFicha(); render(container); })
      .catch(function (err) { alert('Falha: ' + err.message); });
  }

  window.erpRefrig = { render: render };
})();
