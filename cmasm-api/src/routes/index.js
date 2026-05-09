const express = require('express')
const router  = express.Router()

const eq   = require('../controllers/equipment.controller')
const so   = require('../controllers/serviceOrders.controller')
const misc = require('../controllers/misc.controller')
const { auth } = require('../middleware/auth')

// ── Auth (público) ────────────────────────────────────────────────────────────
router.post('/auth/login', misc.login)
router.get ('/auth/me',    auth, misc.me)

// ── Equipamentos ─────────────────────────────────────────────────────────────
router.get   ('/equipment/kpis',    auth, eq.kpis)
router.get   ('/equipment',         auth, eq.list)
router.get   ('/equipment/:id',     auth, eq.get)
router.post  ('/equipment',         auth, eq.create)
router.put   ('/equipment/:id',     auth, eq.update)
router.delete('/equipment/:id',     auth, eq.remove)

// PS de um equipamento específico (histórico 1 equip → N PS)
router.get('/equipment/:id/service-orders', auth, so.listByEquipment)

// ── Pedidos de Serviço ────────────────────────────────────────────────────────
router.get   ('/service-orders',      auth, so.list)
router.get   ('/service-orders/:id',  auth, so.get)
router.post  ('/service-orders',      auth, so.create)
router.patch ('/service-orders/:id',  auth, so.updateStatus)
router.delete('/service-orders/:id',  auth, so.cancel)

// ── Laboratórios ─────────────────────────────────────────────────────────────
router.get ('/laboratories',       auth, misc.listLabs)
router.post('/laboratories',       auth, misc.createLab)
router.put ('/laboratories/:id',   auth, misc.updateLab)

// ── Organizações / Divisões ───────────────────────────────────────────────────
router.get('/organizations', auth, misc.listOrgs)

// ── Health check ─────────────────────────────────────────────────────────────
router.get('/health', (req, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }))

module.exports = router

// ── Relatórios ────────────────────────────────────────────────────────────────
const reports = require('../controllers/reports.controller')
router.get('/reports/conformidade', auth, reports.conformidade)
router.get('/reports/certificados', auth, reports.certificados)

// ── Importação ────────────────────────────────────────────────────────────────
router.post('/import/equipment', auth, reports.importEquipment)
