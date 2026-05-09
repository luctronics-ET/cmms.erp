const jwt = require('jsonwebtoken')

const JWT_SECRET = process.env.JWT_SECRET || 'cmasm_secret_dev_2025'

// ── Autenticação JWT ──────────────────────────────────────────────────────────
function auth(req, res, next) {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer '))
    return res.status(401).json({ error: 'Token não fornecido' })

  try {
    const token = header.slice(7)
    req.user = jwt.verify(token, JWT_SECRET)
    next()
  } catch {
    res.status(401).json({ error: 'Token inválido ou expirado' })
  }
}

// ── Verificação de papel ──────────────────────────────────────────────────────
function requireRole(...roles) {
  return (req, res, next) => {
    if (!roles.includes(req.user?.role))
      return res.status(403).json({ error: 'Sem permissão' })
    next()
  }
}

// ── Handler de erros async ────────────────────────────────────────────────────
function asyncHandler(fn) {
  return (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)
}

// ── Middleware global de erro ─────────────────────────────────────────────────
function errorHandler(err, req, res, next) {
  console.error('API Error:', err)

  if (err.code === 'ER_DUP_ENTRY')
    return res.status(409).json({ error: 'Registro duplicado', detail: err.sqlMessage })

  if (err.code === 'ER_ROW_IS_REFERENCED_2')
    return res.status(409).json({ error: 'Registro em uso — não pode ser excluído' })

  if (err.name === 'ValidationError')
    return res.status(422).json({ error: err.message, fields: err.fields })

  res.status(500).json({ error: 'Erro interno do servidor', detail: err.message })
}

module.exports = { auth, requireRole, asyncHandler, errorHandler, JWT_SECRET }
