const db = require('../utils/db')
const bcrypt = require('bcryptjs')
const jwt = require('jsonwebtoken')
const { asyncHandler, JWT_SECRET } = require('../middleware/auth')

// ════════════════════════════════════════════════════════════════
// AUTH
// ════════════════════════════════════════════════════════════════

exports.login = asyncHandler(async (req, res) => {
  const { email, password } = req.body
  if (!email || !password) return res.status(400).json({ error: 'Email e senha obrigatórios' })

  const [users] = await db.query('SELECT * FROM users WHERE email = ? AND is_active = TRUE', [email])
  if (!users.length) return res.status(401).json({ error: 'Credenciais inválidas' })

  const user = users[0]
  const valid = await bcrypt.compare(password, user.password_hash)
  if (!valid) return res.status(401).json({ error: 'Credenciais inválidas' })

  await db.query('UPDATE users SET last_login = NOW() WHERE id = ?', [user.id])

  const token = jwt.sign(
    { id: user.id, email: user.email, role: user.role, name: user.name },
    JWT_SECRET, { expiresIn: '12h' })

  res.json({
    token,
    user: { id: user.id, name: user.name, email: user.email, role: user.role }
  })
})

exports.me = asyncHandler(async (req, res) => {
  const [users] = await db.query('SELECT id, name, email, role, organization_id FROM users WHERE id = ?', [req.user.id])
  res.json(users[0])
})

// ════════════════════════════════════════════════════════════════
// LABORATORIES
// ════════════════════════════════════════════════════════════════

exports.listLabs = asyncHandler(async (req, res) => {
  const [labs] = await db.query(`
    SELECT l.*,
      COUNT(e.id) AS total_equipamentos
    FROM laboratories l
    LEFT JOIN equipment e ON e.default_laboratory_id = l.id AND e.is_active = TRUE
    WHERE l.is_active = TRUE
    GROUP BY l.id
    ORDER BY
      CASE l.type WHEN 'marinha' THEN 1 WHEN 'pregao' THEN 2 WHEN 'dispensa' THEN 3 ELSE 4 END,
      l.name`)
  res.json(labs)
})

exports.createLab = asyncHandler(async (req, res) => {
  const { code, name, type, accreditation, specialties, contact_email,
          contact_phone, cnpj, address, observations } = req.body
  if (!code || !name || !type) throw Object.assign(new Error('code, name e type obrigatórios'), { name: 'ValidationError' })

  const [r] = await db.query(`
    INSERT INTO laboratories (code, name, type, accreditation, specialties,
      contact_email, contact_phone, cnpj, address, observations)
    VALUES (?,?,?,?,?,?,?,?,?,?)`,
    [code, name, type, accreditation,
     specialties ? JSON.stringify(specialties) : null,
     contact_email, contact_phone, cnpj, address, observations])

  const [lab] = await db.query('SELECT * FROM laboratories WHERE id = ?', [r.insertId])
  res.status(201).json(lab[0])
})

exports.updateLab = asyncHandler(async (req, res) => {
  const allowed = ['name','type','accreditation','specialties','contact_email',
                   'contact_phone','cnpj','address','observations','is_active']
  const fields = Object.keys(req.body).filter(k => allowed.includes(k))
  if (!fields.length) return res.status(422).json({ error: 'Nenhum campo válido' })

  const vals = fields.map(k => k === 'specialties' ? JSON.stringify(req.body[k]) : req.body[k])
  await db.query(
    `UPDATE laboratories SET ${fields.map(f => `${f}=?`).join(',')} WHERE id = ?`,
    [...vals, req.params.id])

  const [lab] = await db.query('SELECT * FROM laboratories WHERE id = ?', [req.params.id])
  res.json(lab[0])
})

// ════════════════════════════════════════════════════════════════
// ORGANIZATIONS (leitura)
// ════════════════════════════════════════════════════════════════

exports.listOrgs = asyncHandler(async (req, res) => {
  const [orgs] = await db.query(`
    SELECT o.*,
      COUNT(e.id) AS total_equipamentos
    FROM organizations o
    LEFT JOIN equipment e ON e.organization_id = o.id AND e.is_active = TRUE
    WHERE o.is_active = TRUE
    GROUP BY o.id
    ORDER BY o.type, o.code`)
  res.json(orgs)
})
