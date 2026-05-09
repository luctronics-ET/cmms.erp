require('dotenv').config()
const express    = require('express')
const cors       = require('cors')
const helmet     = require('helmet')
const morgan     = require('morgan')
const compression= require('compression')
const routes     = require('./routes/index')
const { errorHandler } = require('./middleware/auth')

const app  = express()
const PORT = process.env.PORT || 3001

app.use(helmet())
app.use(compression())
app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }))
app.use(express.json({ limit: '5mb' }))
app.use(morgan('dev'))

app.use('/api/v1', routes)

// 404
app.use((req, res) => res.status(404).json({ error: `Rota não encontrada: ${req.method} ${req.path}` }))

// Erros
app.use(errorHandler)

app.listen(PORT, () => {
  console.log(`\n🚀 CMASM API rodando em http://localhost:${PORT}/api/v1`)
  console.log(`   Health: http://localhost:${PORT}/api/v1/health\n`)
})
