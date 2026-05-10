PRAGMA foreign_keys = ON;

-- Instrumentos que requerem calibração
CREATE TABLE IF NOT EXISTS instrumentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT UNIQUE NOT NULL, -- Ex: CAL-001, MAN-05
    nome TEXT NOT NULL,
    modelo TEXT,
    fabricante TEXT,
    num_serie TEXT,
    faixa_medicao TEXT,
    precisao TEXT,
    periodicidade_meses INTEGER DEFAULT 12,
    status TEXT DEFAULT 'ativo', -- ativo, inativo, em_calibracao, condenado
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Histórico de Certificados de Calibração
CREATE TABLE IF NOT EXISTS certificados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id) ON DELETE CASCADE,
    numero_certificado TEXT NOT NULL,
    data_calibracao TEXT NOT NULL,
    data_vencimento TEXT NOT NULL,
    laboratorio TEXT,
    resultado TEXT CHECK (resultado IN ('aprovado', 'aprovado_restricao', 'reprovado')),
    arquivo_path TEXT, -- Caminho para o PDF
    observacoes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Alertas de vencimento próximos
CREATE VIEW IF NOT EXISTS v_vencimentos_proximos AS
SELECT 
    i.tag, 
    i.nome, 
    c.data_vencimento,
    julianday(c.data_vencimento) - julianday('now') as dias_para_vencer
FROM instrumentos i
JOIN certificados c ON c.instrumento_id = i.id
WHERE c.id = (SELECT id FROM certificados WHERE instrumento_id = i.id ORDER BY data_vencimento DESC LIMIT 1)
AND i.status = 'ativo';

CREATE INDEX IF NOT EXISTS idx_certificados_vencimento ON certificados(data_vencimento);
