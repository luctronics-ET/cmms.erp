/**
 * refrig-engine.js — motor de cálculo de refrigeração.
 *
 * Porta verbatim os algoritmos do app de campo legado:
 * criticidade automática, intervalos PMOC, estimativa de gás/carga, potência,
 * homem-hora, demanda anual, capacidade de equipe, carga térmica (NBR/ASHRAE),
 * gap analysis. São a propriedade intelectual a preservar.
 *
 * Entrada = objeto `e` no shape do app de campo (camelCase). A página do ERP
 * mapeia as linhas da API para esse shape antes de chamar.
 *
 * Dual: browser (window.RefrigEngine) + node (self-test em `node refrig-engine.js`).
 */
(function (root) {
  'use strict';

  // ── criticidade ──────────────────────────────────────────────────────────
  function autoCrit(e) {
    if (e.criticidadeManual && e.criticidade) return e.criticidade;
    var local = (e.local || '').toUpperCase();
    var predio = (e.predio || '').toUpperCase();
    if (e.refrigPermanente) return 'CRÍTICA';
    if (['SERVIDOR', 'INFORMÁTICA'].some(function (x) { return local.indexOf(x) >= 0; })) return 'CRÍTICA';
    if (['EXOCET', 'ASPIDE', 'F21', 'MK48', 'PCI', 'MISTRAL'].some(function (x) { return predio.indexOf(x) >= 0; })) return 'CRÍTICA';
    if (['SAÚDE', 'SEGURANÇA', 'COMANDO'].some(function (x) { return predio.indexOf(x) >= 0; })) return 'ALTA';
    if (e.funciona === 'NOK') return 'ALTA';
    if (e.estado === 'NOVA' || e.estado === 'SEMI') return 'MÉDIA';
    return 'BAIXA';
  }

  var CRIT_COLOR = { 'CRÍTICA': '#E52207', 'ALTA': '#B46800', 'MÉDIA': '#1351B4', 'BAIXA': '#168821' };

  var PMOC_INT = {
    'CRÍTICA': { inspecao: 30, preventiva: 90, revisao: 180, desc: 'Inspeção 30d · Preventiva 90d · Revisão 180d' },
    'ALTA': { inspecao: 60, preventiva: 180, revisao: 365, desc: 'Inspeção 60d · Preventiva 180d · Revisão 365d' },
    'MÉDIA': { inspecao: 90, preventiva: 365, revisao: 730, desc: 'Inspeção 90d · Preventiva 365d · Revisão 730d' },
    'BAIXA': { inspecao: 180, preventiva: 365, revisao: 730, desc: 'Inspeção 180d · Preventiva 365d' },
  };

  function nextPmoc(e, tipo, lastDateFallback) {
    var crit = autoCrit(e);
    var interval = (PMOC_INT[crit] || PMOC_INT['BAIXA'])[tipo];
    var lastDate = e.ultimaManutencao || lastDateFallback;
    if (!lastDate || !interval) return null;
    var d = new Date(lastDate);
    d.setDate(d.getDate() + interval);
    return d;
  }

  // ── gás / carga ──────────────────────────────────────────────────────────
  var FABS_R410A = ['ELGIN', 'MIDEA', 'GREE', 'SAMSUNG', 'COMFEE', 'PHILCO', 'CARRIER', 'CONSUL', 'ELETROLUX', 'CHILI', 'VOGA'];
  var C22 = { 7500: 400, 9000: 550, 12000: 700, 12500: 720, 13000: 730, 18000: 1000, 21000: 1100, 22000: 1150, 24000: 1300, 30000: 1600, 36000: 1900, 48000: 2500, 60000: 3100, 75000: 3800, 90000: 4500, 120000: 6000, 180000: 9000 };
  var C410 = { 7500: 380, 9000: 500, 12000: 650, 12500: 670, 13000: 680, 18000: 900, 21000: 1050, 22000: 1100, 24000: 1200, 30000: 1500, 36000: 1750, 48000: 2300, 60000: 2800, 75000: 3500, 90000: 4200, 120000: 5500, 180000: 8000 };
  var C404 = { 2500: 200, 15000: 900, 18000: 1100, 20000: 1200, 24000: 1400, 36000: 2000, 54000: 2900, 57000: 3000, 58000: 3100, 60000: 3200, 90000: 4500, 120000: 6000, 130000: 6500, 180000: 9000 };

  function lerp(t, b) {
    if (!b) return 0;
    if (t[b] !== undefined) return t[b];
    var keys = Object.keys(t).map(Number).sort(function (a, c) { return a - c; });
    var lo = null, hi = null;
    for (var i = 0; i < keys.length; i++) {
      if (keys[i] <= b) lo = keys[i];
      else if (hi === null) { hi = keys[i]; break; }
    }
    if (lo === null) return t[keys[0]];
    if (hi === null) return t[keys[keys.length - 1]];
    return Math.round(t[lo] + ((b - lo) / (hi - lo)) * (t[hi] - t[lo]));
  }

  function estimateGas(e) {
    var b = e.btu || 0;
    if (!b) return { gas: '—', carga: 0 };
    if (e.tipo === 'SELF CONTAINED') return { gas: 'R-404A', carga: lerp(C404, b) };
    if (e.estado === 'VELHA' || e.tipo === 'JANELA') return { gas: 'R-22', carga: lerp(C22, b) };
    if (e.estado === 'NOVA') return { gas: 'R-410A', carga: lerp(C410, b) };
    if (e.estado === 'SEMI') {
      var f = (e.fabricante || '').toUpperCase();
      return FABS_R410A.indexOf(f) >= 0 ? { gas: 'R-410A', carga: lerp(C410, b) } : { gas: 'R-22', carga: lerp(C22, b) };
    }
    return { gas: 'R-410A', carga: lerp(C410, b) };
  }

  function estimatePower(btu) { return btu ? Math.round(btu / 10.5) : 0; }

  // horas de uso acumuladas estimadas: dias desde instalação × (h/dia × dias/sem ÷ 7)
  function horasUsoEstimado(dataInstISO, horasDia, diasSemana, refISO) {
    if (!dataInstISO || !horasDia || !diasSemana) return null;
    var inst = new Date(dataInstISO);
    if (isNaN(inst.getTime())) return null;
    var ref = refISO ? new Date(refISO) : new Date();
    var days = Math.max(0, (ref - inst) / 86400000);
    return Math.round(days * (horasDia * diasSemana / 7));
  }

  // ── homem-hora / demanda ─────────────────────────────────────────────────
  var MIN_POR_ITEM = 10, SETUP_MIN = 15;
  var CHECKLIST_LEN = { 'SPLIT': 9, 'PISO/TETO': 9, 'SELF CONTAINED': 12, 'JANELA': 6 };
  var FATOR_TIPO_EQUIP = { 'SPLIT': 1.0, 'PISO/TETO': 1.15, 'JANELA': 0.7, 'SELF CONTAINED': 1.6 };
  var FATOR_MANUT = { 'INSPEÇÃO': 0.4, 'PREVENTIVA': 1.0, 'REVISÃO': 1.6, 'LIMPEZA': 0.6, 'CORRETIVA': 1.3, 'RECARGA GÁS': 0.8, 'SUBSTITUIÇÃO': 2.0 };

  function estTempoServico(e, tipoManut) {
    var nItens = CHECKLIST_LEN[e.tipo] || CHECKLIST_LEN['SPLIT'];
    var fEq = FATOR_TIPO_EQUIP[e.tipo] || 1.0;
    var fM = FATOR_MANUT[tipoManut] || 1.0;
    return Math.round(nItens * MIN_POR_ITEM * fEq * fM + SETUP_MIN);
  }

  function demandaAnual(e) {
    var crit = autoCrit(e);
    var intv = PMOC_INT[crit] || PMOC_INT['BAIXA'];
    var horas = 0, os = 0, ni, np, nr;
    if (intv.inspecao) { ni = 365 / intv.inspecao; horas += ni * estTempoServico(e, 'INSPEÇÃO') / 60; os += ni; }
    if (intv.preventiva) { np = 365 / intv.preventiva; horas += np * estTempoServico(e, 'PREVENTIVA') / 60; os += np; }
    if (intv.revisao) { nr = 365 / intv.revisao; horas += nr * estTempoServico(e, 'REVISÃO') / 60; os += nr; }
    return { horas: horas, os: os };
  }

  // ── capacidade da equipe ───────────────────────────────────────────────
  // team = {equipes:int, diasUteis:[..], turnos:[{horas}]}
  function capacidade(team) {
    var hDia = (team.turnos || []).reduce(function (s, t) { return s + (+t.horas || 0); }, 0);
    var diaSem = (team.diasUteis || []).length;
    var hDiaTot = hDia * (team.equipes || 1);
    var hSem = hDiaTot * diaSem;
    return { hDiaEquipe: hDia, hDiaTotal: hDiaTot, diasSemana: diaSem, hSemana: hSem, hMes: hSem * 4.345, hAno: hSem * 52, equipes: team.equipes || 1 };
  }

  // ── carga térmica ────────────────────────────────────────────────────────
  var TIPO_USO = {
    escritorio: { lbl: 'Escritório', ilum_wm2: 12, pessoa_btu: 600, base_btu_m2: 600 },
    sala_reuniao: { lbl: 'Sala de Reunião', ilum_wm2: 15, pessoa_btu: 700, base_btu_m2: 650 },
    sala_tecnica: { lbl: 'Sala Técnica/TI', ilum_wm2: 20, pessoa_btu: 600, base_btu_m2: 700 },
    dormitorio: { lbl: 'Dormitório/Quarto', ilum_wm2: 8, pessoa_btu: 500, base_btu_m2: 600 },
    refeitorio: { lbl: 'Refeitório', ilum_wm2: 14, pessoa_btu: 800, base_btu_m2: 650 },
    corredor: { lbl: 'Corredor/Hall', ilum_wm2: 5, pessoa_btu: 600, base_btu_m2: 500 },
    almoxarifado: { lbl: 'Almoxarifado', ilum_wm2: 6, pessoa_btu: 600, base_btu_m2: 550 },
    enfermaria: { lbl: 'Enfermaria', ilum_wm2: 16, pessoa_btu: 700, base_btu_m2: 650 },
    garagem: { lbl: 'Garagem/Oficina', ilum_wm2: 8, pessoa_btu: 600, base_btu_m2: 700 },
    outro: { lbl: 'Outro', ilum_wm2: 10, pessoa_btu: 600, base_btu_m2: 600 },
  };
  var SOLAR_FACTOR = { baixa: 1.0, media: 1.1, alta: 1.15, muito_alta: 1.25 };
  var ELEC_BTU = { nenhuma: 0, baixa: 500, media: 1000, alta: 2000, muito_alta: 4000 };
  var BTU_COMERCIAIS = [7500, 9000, 10000, 12000, 18000, 21000, 22000, 24000, 30000, 36000, 48000, 60000, 72000, 90000, 120000];

  function calcBTU(p) {
    if (!p || !p.area || p.area <= 0) return null;
    var area = +p.area || 0, altura = +p.altura || 2.7, pessoas = +p.pessoas || 1;
    var janelas = +p.janelas || 0, tipo = p.tipo_uso || 'escritorio', solar = p.solar || 'media';
    var eletr = p.eletr || 'nenhuma', ilum_w = +p.ilum_w || 0, equip_w = +p.equip_w || 0, continuo = !!p.continuo;
    var cfg = TIPO_USO[tipo] || TIPO_USO.outro;
    var q_base = area * cfg.base_btu_m2;
    var f_alt = 1.0;
    if (altura > 4.0) f_alt = 1.30; else if (altura > 3.5) f_alt = 1.20;
    else if (altura > 3.0) f_alt = 1.10; else if (altura > 2.8) f_alt = 1.05;
    var f_solar = SOLAR_FACTOR[solar] || 1.0;
    var q_pess = pessoas * cfg.pessoa_btu, q_jan = janelas * 800, q_el = ELEC_BTU[eletr] || 0;
    var q_ilum = ilum_w > 0 ? ilum_w * 3.412 : area * cfg.ilum_wm2 * 3.412;
    var q_equip = equip_w * 3.412;
    var f_cont = continuo ? 1.10 : 1.0;
    var nivel1 = Math.round(q_base * f_solar * f_alt * f_cont);
    var nivel2 = Math.round((q_base + q_pess + q_jan + q_el) * f_solar * f_alt * f_cont);
    var nivel3 = Math.round((q_base + q_pess + q_jan + q_el + q_ilum + q_equip) * f_solar * f_alt * f_cont);
    var nivel_calc = p.nivel || 1;
    var q_total = nivel_calc === 3 ? nivel3 : nivel_calc === 2 ? nivel2 : nivel1;
    return {
      q_base: Math.round(q_base), q_pess: Math.round(q_pess), q_jan: Math.round(q_jan),
      q_el: Math.round(q_el), q_ilum: Math.round(q_ilum), q_equip: Math.round(q_equip),
      f_solar: f_solar, f_alt: f_alt, f_cont: f_cont,
      nivel1: nivel1, nivel2: nivel2, nivel3: nivel3, q_total: q_total, nivel_calc: nivel_calc,
    };
  }

  function btuComercial(btu) {
    for (var i = 0; i < BTU_COMERCIAIS.length; i++) if (BTU_COMERCIAIS[i] >= btu) return BTU_COMERCIAIS[i];
    return BTU_COMERCIAIS[BTU_COMERCIAIS.length - 1];
  }

  function thermalStatus(btu_inst, btu_calc) {
    if (!btu_calc) return { cls: 'ts-pending', lbl: 'Pendente', gap: null };
    var gap = (btu_inst / btu_calc - 1) * 100;
    if (gap < -20) return { cls: 'ts-sub', lbl: 'Subdimensionado', gap: gap };
    if (gap > 30) return { cls: 'ts-super', lbl: 'Superdimensionado', gap: gap };
    return { cls: 'ts-adequado', lbl: 'Adequado', gap: gap };
  }

  var API = {
    autoCrit: autoCrit, CRIT_COLOR: CRIT_COLOR, PMOC_INT: PMOC_INT, nextPmoc: nextPmoc,
    estimateGas: estimateGas, estimatePower: estimatePower, lerp: lerp, horasUsoEstimado: horasUsoEstimado,
    estTempoServico: estTempoServico, demandaAnual: demandaAnual, capacidade: capacidade,
    TIPO_USO: TIPO_USO, SOLAR_FACTOR: SOLAR_FACTOR, ELEC_BTU: ELEC_BTU,
    calcBTU: calcBTU, btuComercial: btuComercial, thermalStatus: thermalStatus,
  };

  // ── self-test (node) ───────────────────────────────────────────────────
  if (typeof window === 'undefined') {
    var assert = function (c, m) { if (!c) { console.error('FAIL:', m); process.exit(1); } };
    assert(estimatePower(60000) === 5714, 'power 60000');
    assert(estimateGas({ btu: 24000, tipo: 'SELF CONTAINED' }).gas === 'R-404A', 'gas self->404');
    assert(estimateGas({ btu: 24000, tipo: 'SELF CONTAINED' }).carga === 1400, 'carga 404 24000');
    assert(lerp(C22, 12000) === 700, 'lerp C22 12000');
    assert(autoCrit({ refrigPermanente: true }) === 'CRÍTICA', 'crit permanente');
    assert(autoCrit({ predio: 'PAIOL EXOCET' }) === 'CRÍTICA', 'crit paiol');
    assert(autoCrit({ funciona: 'NOK' }) === 'ALTA', 'crit nok');
    assert(autoCrit({ estado: 'NOVA' }) === 'MÉDIA', 'crit nova');
    assert(autoCrit({}) === 'BAIXA', 'crit default');
    assert(estTempoServico({ tipo: 'SPLIT' }, 'PREVENTIVA') === 105, 'tempo split prev');
    var c = calcBTU({ area: 20 });
    assert(c.nivel1 === 13200, 'calcBTU nivel1 20m2 (got ' + c.nivel1 + ')');
    assert(btuComercial(13200) === 18000, 'btuComercial 13200');
    var ts = thermalStatus(12000, 13200);
    assert(ts.lbl === 'Adequado', 'thermalStatus adequado');
    var cap = capacidade({ equipes: 2, diasUteis: [1, 2, 3, 4, 5], turnos: [{ horas: 8 }] });
    assert(cap.hAno === 8 * 2 * 5 * 52, 'capacidade hAno');
    assert(horasUsoEstimado('2025-06-26', 8, 5, '2026-06-26') === 2086, 'horasUso 1 ano (got ' + horasUsoEstimado('2025-06-26', 8, 5, '2026-06-26') + ')');
    assert(horasUsoEstimado(null, 8, 5) === null, 'horasUso sem instalação');
    console.log('refrig-engine self-test OK');
    return;
  }

  root.RefrigEngine = API;
})(typeof window !== 'undefined' ? window : globalThis);
