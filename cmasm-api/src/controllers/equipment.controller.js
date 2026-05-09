const db = require('../utils/db')
const { asyncHandler } = require('../middleware/auth')

// ── GET /equipment — listagem com filtros ─────────────────────────────────────
exports.list = asyncHandler(async (req, res) => {
  const { divisao, status, laboratorio, search, page = 1, limit = 50 } = req.query
  const offset = (page - 1) * limit
  const where = ['e.is_active = TRUE']
  const params = []

  if (divisao)     { where.push('o.code = ?');    params.push(divisao) }
  if (status)      { where.push('e.status = ?');  params.push(status) }
  if (laboratorio) { where.push('l.code = ?');    params.push(laboratorio) }
  if (search) {
    where.push('(e.asset_type LIKE ? OR e.manufacturer LIKE ? OR e.model LIKE ? OR e.serial_number LIKE ? OR e.internal_code LIKE ?)')
    const q = `%${search}%`
    params.push(q, q, q, q, q)
  }

  const sql = `
    SELECT
      e.id, e.serial_number, e.internal_code,
      e.category, e.asset_type, e.manufacturer, e.model, e.range_tolerance,
      e.status, e.calibration_interval_months,
      e.last_calibration_date, e.next_calibration_date, e.last_certificate_number,
      e.max_cost_calibration, e.max_cost_repair,
      e.has_special_restriction, e.special_restriction_detail, e.notes,
      o.code  AS divisao_code, o.name AS divisao_nome,
      l.id    AS lab_id,       l.code AS lab_code, l.name AS lab_nome, l.type AS lab_tipo,
      DATEDIFF(e.next_calibration_date, CURDATE()) AS dias_para_vencer,
      (SELECT COUNT(*) FROM service_orders so WHERE so.equipment_id = e.id) AS total_ps,
      (SELECT COUNT(*) FROM service_orders so
        WHERE so.equipment_id = e.id
        AND so.status NOT IN ('CONCLUIDO','CANCELADO')) AS ps_abertos
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id = o.id
    LEFT JOIN laboratories  l ON e.default_laboratory_id = l.id
    WHERE ${where.join(' AND ')}
    ORDER BY
      CASE e.status
        WHEN 'DESCALIBRADO'         THEN 1
        WHEN 'EM_REPARO'            THEN 2
        WHEN 'AGUARDANDO_CALIBRACAO'THEN 3
        WHEN 'SEM_CERTIFICADO'      THEN 4
        WHEN 'CALIBRADO'            THEN 5
        WHEN 'NAO_UTILIZADO'        THEN 6
        ELSE 7
      END,
      e.next_calibration_date ASC
    LIMIT ? OFFSET ?`

  params.push(parseInt(limit), parseInt(offset))
  const [rows] = await db.query(sql, params)

  // total para paginação
  const [cnt] = await db.query(
    `SELECT COUNT(*) AS total FROM equipment e
     LEFT JOIN organizations o ON e.organization_id = o.id
     LEFT JOIN laboratories  l ON e.default_laboratory_id = l.id
     WHERE ${where.join(' AND ')}`,
    params.slice(0, -2)
  )

  res.json({ data: rows, total: cnt[0].total, page: +page, limit: +limit })
})

// ── GET /equipment/:id — detalhe com histórico de PS ─────────────────────────
exports.get = asyncHandler(async (req, res) => {
  const { id } = req.params

  // Busca por ID ou por SN
  const idField = isNaN(id) ? 'e.serial_number' : 'e.id'
  const [rows] = await db.query(`
    SELECT e.*,
      o.code AS divisao_code, o.name AS divisao_nome,
      l.code AS lab_code, l.name AS lab_nome, l.type AS lab_tipo,
      l.accreditation AS lab_accreditation, l.specialties AS lab_specialties,
      l.observations AS lab_observations
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id = o.id
    LEFT JOIN laboratories  l ON e.default_laboratory_id = l.id
    WHERE ${idField} = ? AND e.is_active = TRUE`, [id])

  if (!rows.length) return res.status(404).json({ error: 'Equipamento não encontrado' })

  const eq = rows[0]

  // Histórico completo de PS — mais recente primeiro
  const [ps] = await db.query(`
    SELECT so.*,
      l.name AS lab_nome, l.type AS lab_tipo,
      u.name AS issued_by_name
    FROM service_orders so
    LEFT JOIN laboratories l ON so.laboratory_id = l.id
    LEFT JOIN users        u ON so.issued_by = u.id
    WHERE so.equipment_id = ?
    ORDER BY so.issue_date DESC, so.id DESC`, [eq.id])

  res.json({ ...eq, historico_ps: ps })
})

// ── POST /equipment — criar equipamento ───────────────────────────────────────
exports.create = asyncHandler(async (req, res) => {
  const {
    serial_number, internal_code, category, asset_type, manufacturer, model,
    range_tolerance, organization_id, location_detail, default_laboratory_id,
    calibration_interval_months = 12, last_calibration_date, next_calibration_date,
    status = 'DESCALIBRADO', max_cost_calibration = 0, max_cost_repair = 0,
    has_special_restriction = false, special_restriction_detail, notes,
  } = req.body

  if (!asset_type || !model) throw Object.assign(new Error('asset_type e model são obrigatórios'), { name: 'ValidationError' })

  const [result] = await db.query(`
    INSERT INTO equipment
      (serial_number, internal_code, category, asset_type, manufacturer, model,
       range_tolerance, organization_id, location_detail, default_laboratory_id,
       calibration_interval_months, last_calibration_date, next_calibration_date,
       status, max_cost_calibration, max_cost_repair,
       has_special_restriction, special_restriction_detail, notes, created_by)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
    [serial_number, internal_code, category, asset_type, manufacturer, model,
     range_tolerance, organization_id, location_detail, default_laboratory_id,
     calibration_interval_months, last_calibration_date || null, next_calibration_date || null,
     status, max_cost_calibration, max_cost_repair,
     has_special_restriction, special_restriction_detail, notes,
     req.user?.id || null])

  const [eq] = await db.query('SELECT * FROM equipment WHERE id = ?', [result.insertId])
  res.status(201).json(eq[0])
})

// ── PUT /equipment/:id — atualizar equipamento ────────────────────────────────
exports.update = asyncHandler(async (req, res) => {
  const { id } = req.params
  const allowed = [
    'serial_number','internal_code','category','asset_type','manufacturer','model',
    'range_tolerance','organization_id','location_detail','default_laboratory_id',
    'calibration_interval_months','last_calibration_date','next_calibration_date',
    'status','max_cost_calibration','max_cost_repair',
    'has_special_restriction','special_restriction_detail','notes',
  ]
  const fields = Object.keys(req.body).filter(k => allowed.includes(k))
  if (!fields.length) return res.status(422).json({ error: 'Nenhum campo válido' })

  const sets = fields.map(f => `${f} = ?`).join(', ')
  const vals = fields.map(f => req.body[f] ?? null)
  await db.query(`UPDATE equipment SET ${sets} WHERE id = ?`, [...vals, id])

  const [eq] = await db.query('SELECT * FROM equipment WHERE id = ?', [id])
  res.json(eq[0])
})

// ── DELETE /equipment/:id — inativar (soft delete) ────────────────────────────
exports.remove = asyncHandler(async (req, res) => {
  const { id } = req.params

  // Verificar se há PS em aberto
  const [open] = await db.query(
    `SELECT COUNT(*) AS cnt FROM service_orders
     WHERE equipment_id = ? AND status NOT IN ('CONCLUIDO','CANCELADO')`, [id])

  if (open[0].cnt > 0)
    return res.status(409).json({ error: 'Equipamento tem PS em aberto — cancele antes de inativar' })

  await db.query('UPDATE equipment SET is_active = FALSE WHERE id = ?', [id])
  res.json({ message: 'Equipamento inativado' })
})

// ── GET /equipment/kpis — KPIs para o dashboard ───────────────────────────────
exports.kpis = asyncHandler(async (req, res) => {
  const [[summary]]  = await db.query(`CALL sp_kpis_dashboard()`)
  const [byDivisao]  = await db.query('SELECT * FROM v_dashboard_by_division')
  const [vencendo]   = await db.query(`
    SELECT e.id, e.asset_type, e.manufacturer, e.model, o.code AS divisao,
           e.next_calibration_date,
           DATEDIFF(e.next_calibration_date, CURDATE()) AS dias
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id = o.id
    WHERE e.is_active = TRUE
      AND e.next_calibration_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 60 DAY)
    ORDER BY e.next_calibration_date ASC
    LIMIT 20`)
  const [restricoes] = await db.query(`
    SELECT e.id, e.asset_type, e.manufacturer, e.model, e.status,
           o.code AS divisao, e.special_restriction_detail, l.name AS lab_nome
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id = o.id
    LEFT JOIN laboratories  l ON e.default_laboratory_id = l.id
    WHERE e.is_active = TRUE AND e.has_special_restriction = TRUE`)

  res.json({ summary: summary[0], por_divisao: byDivisao, vencendo, restricoes })
})
