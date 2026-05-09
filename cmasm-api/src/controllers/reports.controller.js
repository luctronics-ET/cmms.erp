const db = require('../utils/db')
const { asyncHandler } = require('../middleware/auth')

// ── GET /reports/conformidade — relatório ISO/IEC 17025 ───────────────────────
exports.conformidade = asyncHandler(async (req, res) => {
  const { divisao, ano = new Date().getFullYear() } = req.query

  // Resumo geral
  const [[summary]] = await db.query(`
    SELECT
      COUNT(*) AS total,
      SUM(status='CALIBRADO') AS calibrados,
      SUM(status='DESCALIBRADO') AS descalibrados,
      SUM(status='EM_REPARO') AS em_reparo,
      SUM(status='AGUARDANDO_CALIBRACAO') AS aguardando,
      SUM(status='SEM_CERTIFICADO') AS sem_certificado,
      SUM(status='NAO_UTILIZADO') AS nao_utilizados,
      ROUND(SUM(status='CALIBRADO')/COUNT(*)*100,1) AS pct_conformidade,
      SUM(max_cost_calibration) AS custo_estimado_total
    FROM equipment WHERE is_active=TRUE ${divisao ? 'AND organization_id=(SELECT id FROM organizations WHERE code=?)' : ''}`,
    divisao ? [divisao] : [])

  // Por divisão
  const [porDivisao] = await db.query(`
    SELECT
      o.code AS divisao, o.name AS divisao_nome,
      COUNT(e.id) AS total,
      SUM(e.status='CALIBRADO') AS calibrados,
      SUM(e.status='DESCALIBRADO') AS descalibrados,
      SUM(e.status='SEM_CERTIFICADO') AS sem_certificado,
      SUM(e.status IN('EM_REPARO','AGUARDANDO_CALIBRACAO')) AS em_reparo,
      SUM(e.max_cost_calibration) AS custo_estimado,
      ROUND(SUM(e.status='CALIBRADO')/COUNT(e.id)*100,1) AS pct_conformidade
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id=o.id
    WHERE e.is_active=TRUE
    GROUP BY o.id, o.code, o.name
    ORDER BY pct_conformidade ASC`)

  // PS do ano
  const [psAno] = await db.query(`
    SELECT
      COUNT(*) AS total_ps,
      SUM(status='CONCLUIDO') AS concluidos,
      SUM(status IN('EMITIDO','ENVIADO','EM_CALIBRACAO')) AS em_aberto,
      SUM(status='CANCELADO') AS cancelados,
      COALESCE(SUM(executed_value),0) AS custo_executado,
      COALESCE(SUM(max_value),0) AS custo_contratado
    FROM service_orders
    WHERE YEAR(issue_date)=?`, [ano])

  // Instrumentos descalibrados (ordenados por dias fora)
  const [descalibrados] = await db.query(`
    SELECT e.id, e.serial_number, e.internal_code, e.asset_type,
           e.manufacturer, e.model, e.status,
           o.code AS divisao, l.name AS lab_nome, l.type AS lab_tipo,
           e.next_calibration_date,
           DATEDIFF(CURDATE(), e.next_calibration_date) AS dias_vencido,
           e.has_special_restriction, e.special_restriction_detail
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id=o.id
    LEFT JOIN laboratories  l ON e.default_laboratory_id=l.id
    WHERE e.is_active=TRUE AND e.status IN('DESCALIBRADO','SEM_CERTIFICADO','AGUARDANDO_CALIBRACAO')
    ORDER BY dias_vencido DESC`)

  // Restrições especiais
  const [restricoes] = await db.query(`
    SELECT e.id, e.serial_number, e.internal_code, e.asset_type,
           e.manufacturer, e.model, e.status,
           o.code AS divisao, l.name AS lab_nome,
           e.special_restriction_detail,
           e.last_calibration_date
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id=o.id
    LEFT JOIN laboratories  l ON e.default_laboratory_id=l.id
    WHERE e.is_active=TRUE AND e.has_special_restriction=TRUE
    ORDER BY e.status, o.code`)

  // Vencendo nos próximos 60 dias
  const [vencendo] = await db.query(`
    SELECT e.id, e.asset_type, e.manufacturer, e.model,
           o.code AS divisao, e.next_calibration_date,
           DATEDIFF(e.next_calibration_date, CURDATE()) AS dias
    FROM equipment e
    LEFT JOIN organizations o ON e.organization_id=o.id
    WHERE e.is_active=TRUE
      AND e.next_calibration_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 60 DAY)
    ORDER BY e.next_calibration_date`)

  res.json({
    gerado_em: new Date().toISOString(),
    ano,
    summary: summary[0],
    por_divisao: porDivisao,
    ps_ano: psAno[0],
    descalibrados,
    restricoes,
    vencendo,
  })
})

// ── GET /reports/certificados — listagem de certificados ──────────────────────
exports.certificados = asyncHandler(async (req, res) => {
  const { divisao, laboratorio, ano } = req.query
  const where = ["so.status='CONCLUIDO'", "so.certificate_number IS NOT NULL"]
  const params = []

  if (divisao)    { where.push('o.code = ?');              params.push(divisao) }
  if (laboratorio){ where.push('l.code = ?');              params.push(laboratorio) }
  if (ano)        { where.push('YEAR(so.calibration_date)=?'); params.push(ano) }

  const [rows] = await db.query(`
    SELECT
      so.certificate_number, so.ps_number, so.calibration_date,
      so.result, so.executed_value, so.invoice_number,
      e.id AS eq_id, e.asset_type, e.manufacturer, e.model,
      e.serial_number, e.internal_code,
      o.code AS divisao,
      l.code AS lab_code, l.name AS lab_nome, l.type AS lab_tipo
    FROM service_orders so
    JOIN equipment e ON so.equipment_id=e.id
    LEFT JOIN organizations o ON e.organization_id=o.id
    LEFT JOIN laboratories  l ON so.laboratory_id=l.id
    WHERE ${where.join(' AND ')}
    ORDER BY so.calibration_date DESC, so.certificate_number DESC`, params)

  res.json({ data: rows, total: rows.length })
})

// ── POST /import/equipment — importar equipamentos de CSV/JSON ────────────────
// Body: { equipamentos: [...] }
// Cada item deve ter: asset_type, model + campos opcionais
exports.importEquipment = asyncHandler(async (req, res) => {
  const { equipamentos } = req.body
  if (!Array.isArray(equipamentos) || !equipamentos.length)
    return res.status(422).json({ error: 'Array "equipamentos" obrigatório' })

  const results = { inserted: 0, updated: 0, errors: [] }
  const conn = await db.getConnection()

  try {
    await conn.beginTransaction()

    for (const [idx, item] of equipamentos.entries()) {
      try {
        // Resolver organization_id pelo code
        let orgId = null
        if (item.divisao) {
          const [[org]] = await conn.query('SELECT id FROM organizations WHERE code=?', [item.divisao])
          orgId = org?.id || null
        }
        // Resolver laboratory_id pelo code
        let labId = null
        if (item.laboratorio) {
          const [[lab]] = await conn.query('SELECT id FROM laboratories WHERE code=?', [item.laboratorio])
          labId = lab?.id || null
        }

        // Upsert por serial_number (se fornecido) ou por internal_code
        let existing = null
        if (item.serial_number) {
          const [[eq]] = await conn.query('SELECT id FROM equipment WHERE serial_number=?', [item.serial_number])
          existing = eq
        } else if (item.internal_code) {
          const [[eq]] = await conn.query('SELECT id FROM equipment WHERE internal_code=?', [item.internal_code])
          existing = eq
        }

        if (existing) {
          // Update
          await conn.query(`
            UPDATE equipment SET
              asset_type=COALESCE(?,asset_type), manufacturer=COALESCE(?,manufacturer),
              model=COALESCE(?,model), range_tolerance=COALESCE(?,range_tolerance),
              organization_id=COALESCE(?,organization_id), default_laboratory_id=COALESCE(?,default_laboratory_id),
              calibration_interval_months=COALESCE(?,calibration_interval_months),
              last_calibration_date=COALESCE(?,last_calibration_date),
              next_calibration_date=COALESCE(?,next_calibration_date),
              last_certificate_number=COALESCE(?,last_certificate_number),
              max_cost_calibration=COALESCE(?,max_cost_calibration),
              status=COALESCE(?,status), notes=COALESCE(?,notes),
              has_special_restriction=COALESCE(?,has_special_restriction),
              special_restriction_detail=COALESCE(?,special_restriction_detail)
            WHERE id=?`,
            [item.asset_type||null, item.manufacturer||null, item.model||null,
             item.range_tolerance||null, orgId, labId,
             item.calibration_interval_months||null,
             item.last_calibration_date||null, item.next_calibration_date||null,
             item.last_certificate_number||null, item.max_cost_calibration||null,
             item.status||null, item.notes||null,
             item.has_special_restriction!=null ? item.has_special_restriction : null,
             item.special_restriction_detail||null,
             existing.id])
          results.updated++
        } else {
          // Insert
          await conn.query(`
            INSERT INTO equipment
              (serial_number,internal_code,category,asset_type,manufacturer,model,
               range_tolerance,organization_id,default_laboratory_id,
               calibration_interval_months,last_calibration_date,next_calibration_date,
               last_certificate_number,status,max_cost_calibration,
               has_special_restriction,special_restriction_detail,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
            [item.serial_number||null, item.internal_code||null,
             item.category||'ELE', item.asset_type, item.manufacturer||null, item.model,
             item.range_tolerance||null, orgId, labId,
             item.calibration_interval_months||12,
             item.last_calibration_date||null, item.next_calibration_date||null,
             item.last_certificate_number||null,
             item.status||'DESCALIBRADO',
             item.max_cost_calibration||0,
             item.has_special_restriction||false,
             item.special_restriction_detail||null,
             item.notes||null])
          results.inserted++
        }
      } catch (err) {
        results.errors.push({ linha: idx + 1, erro: err.message, item })
      }
    }

    await conn.commit()
    res.json({
      message: `Importação concluída: ${results.inserted} inseridos, ${results.updated} atualizados`,
      ...results
    })
  } catch (err) {
    await conn.rollback()
    throw err
  } finally {
    conn.release()
  }
})
