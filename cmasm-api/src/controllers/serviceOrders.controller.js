const db = require('../utils/db')
const { asyncHandler } = require('../middleware/auth')

// ── GET /service-orders — listagem geral com filtros ─────────────────────────
exports.list = asyncHandler(async (req, res) => {
  const { status, divisao, laboratorio, tipo, search, page = 1, limit = 50 } = req.query
  const offset = (page - 1) * limit
  const where = []
  const params = []

  if (status)     { where.push('so.status = ?');          params.push(status) }
  if (divisao)    { where.push('o.code = ?');             params.push(divisao) }
  if (laboratorio){ where.push('l.code = ?');             params.push(laboratorio) }
  if (tipo)       { where.push('so.service_type = ?');    params.push(tipo) }
  if (search) {
    where.push('(so.ps_number LIKE ? OR e.asset_type LIKE ? OR e.model LIKE ? OR e.serial_number LIKE ? OR so.certificate_number LIKE ?)')
    const q = `%${search}%`
    params.push(q, q, q, q, q)
  }

  const wClause = where.length ? `WHERE ${where.join(' AND ')}` : ''

  const [rows] = await db.query(`
    SELECT
      so.id, so.ps_number, so.service_type, so.status,
      so.issue_date, so.sent_date, so.calibration_date, so.return_date,
      so.certificate_number, so.result,
      so.max_value, so.executed_value, so.invoice_number, so.contract_ref,
      so.notes, so.approved_by_name, so.lab_representative,
      -- Equipamento
      e.id AS eq_id, e.serial_number, e.internal_code,
      e.category, e.asset_type, e.manufacturer, e.model,
      e.has_special_restriction, e.special_restriction_detail,
      -- Divisão
      o.code AS divisao, o.name AS divisao_nome,
      -- Laboratório
      l.id AS lab_id, l.code AS lab_code, l.name AS lab_nome, l.type AS lab_tipo,
      -- Quem emitiu
      u.name AS issued_by_name
    FROM service_orders so
    JOIN equipment      e  ON so.equipment_id  = e.id
    LEFT JOIN organizations o ON e.organization_id   = o.id
    LEFT JOIN laboratories  l ON so.laboratory_id    = l.id
    LEFT JOIN users         u ON so.issued_by        = u.id
    ${wClause}
    ORDER BY so.issue_date DESC, so.id DESC
    LIMIT ? OFFSET ?`,
    [...params, parseInt(limit), parseInt(offset)])

  const [[cnt]] = await db.query(
    `SELECT COUNT(*) AS total FROM service_orders so
     JOIN equipment e ON so.equipment_id = e.id
     LEFT JOIN organizations o ON e.organization_id = o.id
     LEFT JOIN laboratories  l ON so.laboratory_id  = l.id
     ${wClause}`, params)

  res.json({ data: rows, total: cnt.total, page: +page, limit: +limit })
})

// ── GET /service-orders/:id — PS individual com dados completos ───────────────
exports.get = asyncHandler(async (req, res) => {
  const [rows] = await db.query(`
    SELECT so.*,
      e.serial_number, e.internal_code, e.category, e.asset_type,
      e.manufacturer, e.model, e.range_tolerance, e.calibration_interval_months,
      e.has_special_restriction, e.special_restriction_detail,
      o.code AS divisao, o.name AS divisao_nome,
      l.name AS lab_nome, l.type AS lab_tipo, l.accreditation,
      u.name AS issued_by_name
    FROM service_orders so
    JOIN equipment     e  ON so.equipment_id  = e.id
    LEFT JOIN organizations o ON e.organization_id = o.id
    LEFT JOIN laboratories  l ON so.laboratory_id  = l.id
    LEFT JOIN users         u ON so.issued_by      = u.id
    WHERE so.id = ?`, [req.params.id])

  if (!rows.length) return res.status(404).json({ error: 'PS não encontrado' })

  const ps = rows[0]

  // Calibração técnica vinculada (se existir)
  const [cals] = await db.query(`
    SELECT c.*, mp.id AS mp_id, mp.parameter_name, mp.nominal_value,
           mp.measured_value, mp.unit, mp.tolerance, mp.uncertainty, mp.pass_fail
    FROM calibrations c
    LEFT JOIN measurement_parameters mp ON mp.calibration_id = c.id
    WHERE c.service_order_id = ?`, [ps.id])

  // Reagrupar parâmetros de medição
  const calibracao = cals.length ? {
    id: cals[0].id, calibration_date: cals[0].calibration_date,
    calibration_method: cals[0].calibration_method,
    env_temperature: cals[0].env_temperature, env_humidity: cals[0].env_humidity,
    env_pressure: cals[0].env_pressure, pass_fail: cals[0].pass_fail,
    results_summary: cals[0].results_summary, performed_by_name: cals[0].performed_by_name,
    parametros: cals.filter(r => r.mp_id).map(r => ({
      id: r.mp_id, parameter_name: r.parameter_name, nominal_value: r.nominal_value,
      measured_value: r.measured_value, unit: r.unit, tolerance: r.tolerance,
      uncertainty: r.uncertainty, pass_fail: r.pass_fail,
    }))
  } : null

  res.json({ ...ps, calibracao })
})

// ── GET /equipment/:id/service-orders — histórico completo de PS de um equip. ─
exports.listByEquipment = asyncHandler(async (req, res) => {
  const { id } = req.params

  // aceita id numérico ou serial_number
  const idField = isNaN(id) ? 'e.serial_number' : 'e.id'
  const [rows] = await db.query(`
    SELECT
      so.id, so.ps_number, so.service_type, so.status,
      so.issue_date, so.sent_date, so.calibration_date, so.return_date,
      so.certificate_number, so.result, so.max_value, so.executed_value,
      so.notes, so.approved_by_name,
      l.name AS lab_nome, l.type AS lab_tipo,
      u.name AS issued_by_name
    FROM service_orders so
    JOIN equipment e ON so.equipment_id = e.id
    LEFT JOIN laboratories l ON so.laboratory_id = l.id
    LEFT JOIN users        u ON so.issued_by      = u.id
    WHERE ${idField} = ?
    ORDER BY so.issue_date DESC, so.id DESC`, [id])

  res.json({ data: rows, total: rows.length })
})

// ── POST /service-orders — emitir novo PS ────────────────────────────────────
// O número PS-CMS-AA-NNN é gerado pelo trigger do banco
exports.create = asyncHandler(async (req, res) => {
  const {
    equipment_id, service_type = 'calibracao_rotina', laboratory_id,
    issue_date, max_value, contract_ref, notes,
    approved_by_name, lab_representative,
  } = req.body

  if (!equipment_id || !laboratory_id)
    throw Object.assign(new Error('equipment_id e laboratory_id são obrigatórios'), { name: 'ValidationError' })

  // Verificar que o equipamento existe
  const [eq] = await db.query('SELECT id, asset_type, model, status FROM equipment WHERE id = ? AND is_active = TRUE', [equipment_id])
  if (!eq.length) return res.status(404).json({ error: 'Equipamento não encontrado' })

  // Inserir PS — o trigger cria o ps_number automaticamente
  const [result] = await db.query(`
    INSERT INTO service_orders
      (equipment_id, service_type, laboratory_id, issue_date, max_value,
       contract_ref, notes, approved_by_name, lab_representative,
       issued_by, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'EMITIDO')`,
    [equipment_id, service_type, laboratory_id,
     issue_date || new Date().toISOString().slice(0,10),
     max_value || 0, contract_ref, notes,
     approved_by_name, lab_representative, req.user?.id || null])

  const [ps] = await db.query(`
    SELECT so.*, l.name AS lab_nome, e.asset_type, e.model, e.serial_number
    FROM service_orders so
    JOIN laboratories l ON so.laboratory_id = l.id
    JOIN equipment    e ON so.equipment_id  = e.id
    WHERE so.id = ?`, [result.insertId])

  res.status(201).json(ps[0])
})

// ── PATCH /service-orders/:id — atualizar status/dados do PS ─────────────────
// Transições permitidas:
//   EMITIDO → ENVIADO → EM_CALIBRACAO → CONCLUIDO | CANCELADO
//   CONCLUIDO dispara trigger que atualiza o equipamento
exports.updateStatus = asyncHandler(async (req, res) => {
  const { id } = req.params
  const {
    status, sent_date, calibration_date, return_date,
    certificate_number, result, executed_value, invoice_number,
    approved_by_name, lab_representative, notes, contract_ref,
  } = req.body

  const [current] = await db.query('SELECT * FROM service_orders WHERE id = ?', [id])
  if (!current.length) return res.status(404).json({ error: 'PS não encontrado' })

  // Validar transição de status
  const TRANSITIONS = {
    RASCUNHO:      ['EMITIDO','CANCELADO'],
    EMITIDO:       ['ENVIADO','CANCELADO'],
    ENVIADO:       ['EM_CALIBRACAO','EMITIDO','CANCELADO'],
    EM_CALIBRACAO: ['CONCLUIDO','ENVIADO','CANCELADO'],
    CONCLUIDO:     [],
    CANCELADO:     [],
  }
  const cur = current[0].status
  if (status && status !== cur && !TRANSITIONS[cur]?.includes(status))
    return res.status(422).json({ error: `Transição inválida: ${cur} → ${status}` })

  // Montar update dinâmico
  const fields = { status, sent_date, calibration_date, return_date,
    certificate_number, result, executed_value, invoice_number,
    approved_by_name, lab_representative, notes, contract_ref }

  const toUpdate = Object.fromEntries(Object.entries(fields).filter(([,v]) => v !== undefined))
  if (!Object.keys(toUpdate).length) return res.status(422).json({ error: 'Nenhum campo para atualizar' })

  const sets   = Object.keys(toUpdate).map(k => `${k} = ?`).join(', ')
  const values = Object.values(toUpdate)
  await db.query(`UPDATE service_orders SET ${sets} WHERE id = ?`, [...values, id])

  // Ao concluir PS de calibração: atualizar equipamento (o trigger faz isso,
  // mas garantimos aqui também para robustez)
  if (status === 'CONCLUIDO') {
    const ps = current[0]
    if (['calibracao_rotina','calibracao_inicial','verificacao'].includes(ps.service_type)) {
      const calDate = calibration_date || ps.calibration_date
      const certNum = certificate_number || ps.certificate_number

      const [[eq]] = await db.query('SELECT calibration_interval_months FROM equipment WHERE id = ?', [ps.equipment_id])
      const nextDate = calDate ? new Date(calDate) : null
      if (nextDate) nextDate.setMonth(nextDate.getMonth() + eq.calibration_interval_months)

      await db.query(`
        UPDATE equipment SET
          status                = 'CALIBRADO',
          last_calibration_date  = ?,
          last_certificate_number= ?,
          next_calibration_date  = ?,
          updated_at             = NOW()
        WHERE id = ?`,
        [calDate || null, certNum || null,
         nextDate ? nextDate.toISOString().slice(0,10) : null,
         ps.equipment_id])
    }

    if (ps.service_type === 'reparo') {
      await db.query(
        `UPDATE equipment SET status = 'AGUARDANDO_CALIBRACAO', updated_at = NOW() WHERE id = ?`,
        [ps.equipment_id])
    }
  }

  const [updated] = await db.query(`
    SELECT so.*, l.name AS lab_nome, e.asset_type, e.model, e.serial_number,
           o.code AS divisao
    FROM service_orders so
    JOIN equipment e ON so.equipment_id = e.id
    LEFT JOIN laboratories  l ON so.laboratory_id = l.id
    LEFT JOIN organizations o ON e.organization_id = o.id
    WHERE so.id = ?`, [id])

  res.json(updated[0])
})

// ── DELETE /service-orders/:id — cancelar (não deleta) ───────────────────────
exports.cancel = asyncHandler(async (req, res) => {
  const [ps] = await db.query('SELECT status FROM service_orders WHERE id = ?', [req.params.id])
  if (!ps.length) return res.status(404).json({ error: 'PS não encontrado' })
  if (ps[0].status === 'CONCLUIDO') return res.status(409).json({ error: 'PS concluído não pode ser cancelado' })

  await db.query(`UPDATE service_orders SET status = 'CANCELADO' WHERE id = ?`, [req.params.id])
  res.json({ message: 'PS cancelado' })
})
