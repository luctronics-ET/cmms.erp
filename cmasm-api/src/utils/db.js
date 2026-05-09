const mysql = require('mysql2/promise')

const pool = mysql.createPool({
  host:               process.env.DB_HOST     || 'localhost',
  port:               parseInt(process.env.DB_PORT || '3306'),
  user:               process.env.DB_USER     || 'root',
  password:           process.env.DB_PASSWORD || '',
  database:           process.env.DB_NAME     || 'cmasm_calibracao',
  waitForConnections: true,
  connectionLimit:    10,
  charset:            'utf8mb4',
  timezone:           '-03:00',
})

pool.getConnection()
  .then(conn => { console.log('✅ MySQL conectado'); conn.release() })
  .catch(err => console.error('❌ MySQL erro:', err.message))

module.exports = pool
