-- ============================================================
-- CMASM — Sistema de Calibração
-- Schema v3.0 — Modelo correto
--
-- Regras de negócio implementadas:
--   • Equipamento identificado pelo serial_number (SN) — chave natural única
--   • PS é entidade independente: um equipamento tem N PS
--   • PS pode ser de calibração (rotina/inicial) ou reparo
--   • Cada PS tem ciclo de vida próprio: emitido → enviado → retornado → concluído
--   • Ao concluir PS de calibração: atualiza datas e status do equipamento
--   • Ao concluir PS de reparo: status vira AGUARDANDO_CALIBRACAO
--   • Número do PS gerado automaticamente: PS-CMS-AA-NNN
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP DATABASE IF EXISTS cmasm_calibracao;
CREATE DATABASE cmasm_calibracao
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE cmasm_calibracao;

-- ── 1. ORGANIZATIONS (hierarquia: OM > Depto > Divisão > Seção) ──────────────
CREATE TABLE organizations (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  code                VARCHAR(30)  NOT NULL UNIQUE  COMMENT 'MK-46, F-21, EXOCET...',
  name                VARCHAR(200) NOT NULL,
  type                ENUM('om','department','division','section') NOT NULL,
  parent_id           INT NULL,
  responsible_officer VARCHAR(100),
  is_active           BOOLEAN DEFAULT TRUE,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (parent_id) REFERENCES organizations(id) ON DELETE SET NULL,
  INDEX idx_type(type),
  INDEX idx_parent(parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Estrutura hierárquica: CMASM > Depto > Divisão > Seção';

-- ── 2. LABORATORIES ───────────────────────────────────────────────────────────
CREATE TABLE laboratories (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  code            VARCHAR(30)  NOT NULL UNIQUE,
  name            VARCHAR(200) NOT NULL,
  -- marinha = CMS/BACS (Marinha do Brasil)
  -- pregao  = contratado via licitação/pregão
  -- dispensa= contratado via dispensa de licitação
  -- autorizada = empresa exclusiva do fabricante (AMETEK, NI...)
  type            ENUM('marinha','pregao','dispensa','autorizada') NOT NULL DEFAULT 'pregao',
  accreditation   VARCHAR(150) COMMENT 'Ex: RBC/INMETRO, NI Certified Center',
  specialties     JSON         COMMENT '["Torquímetros","Dimensional","Pressão"]',
  contact_email   VARCHAR(150),
  contact_phone   VARCHAR(30),
  cnpj            VARCHAR(20),
  address         TEXT,
  -- Observações de restrição (ex: único lab no Brasil para NI)
  observations    TEXT,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_type(type),
  INDEX idx_active(is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3. USERS ──────────────────────────────────────────────────────────────────
CREATE TABLE users (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(100) NOT NULL,
  email           VARCHAR(150) NOT NULL UNIQUE,
  password_hash   VARCHAR(255) NOT NULL,
  role            ENUM('admin','tecnico','gerente','visualizador') DEFAULT 'tecnico',
  organization_id INT NULL     COMMENT 'Divisão/setor do usuário',
  is_active       BOOLEAN DEFAULT TRUE,
  last_login      DATETIME,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
  INDEX idx_email(email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 4. EQUIPMENT ──────────────────────────────────────────────────────────────
--
--  IDENTIFICAÇÃO ÚNICA: serial_number (SN)
--  Um equipamento existe uma única vez no sistema.
--  Seu histórico de calibrações/reparos são os PS vinculados a ele.
--
CREATE TABLE equipment (
  id                          INT AUTO_INCREMENT PRIMARY KEY,

  -- ── Identificação (SN é a chave natural) ────────────────────────────────
  serial_number               VARCHAR(100) COMMENT 'Número de série — identificador único do instrumento',
  internal_code               VARCHAR(50)  COMMENT 'Código patrimônio/CADBEM interno CMASM',

  -- ── Classificação ────────────────────────────────────────────────────────
  category                    ENUM('ELE','MEC') NOT NULL DEFAULT 'ELE'
                                COMMENT 'ELE=Elétrico/Eletrônico, MEC=Mecânico/Dimensional',
  asset_type                  VARCHAR(100) NOT NULL
                                COMMENT 'Tipo: Multímetro, Osciloscópio, Torquímetro...',
  manufacturer                VARCHAR(100),
  model                       VARCHAR(100) NOT NULL,
  range_tolerance             VARCHAR(150)
                                COMMENT 'Faixa e tolerância: ex "0-1000V / 0.01%"',

  -- ── Localização ──────────────────────────────────────────────────────────
  organization_id             INT          COMMENT 'FK divisão (MK-46, F-21...)',
  location_detail             VARCHAR(200) COMMENT 'Localização física específica',

  -- ── Laboratório padrão de calibração ─────────────────────────────────────
  -- O laboratório pode ser sobrescrito em cada PS individualmente
  default_laboratory_id       INT          COMMENT 'Lab responsável padrão',

  -- ── Configuração de calibração ────────────────────────────────────────────
  calibration_interval_months INT NOT NULL DEFAULT 12
                                COMMENT 'Periodicidade: 12, 24, 36 meses',

  -- ── Datas (calculadas/atualizadas ao concluir PS de calibração) ───────────
  last_calibration_date       DATE         COMMENT 'Atualizado ao concluir PS de calibração',
  next_calibration_date       DATE         COMMENT 'Calculado: last_cal + intervalo',
  last_certificate_number     VARCHAR(100) COMMENT 'Último certificado emitido',

  -- ── Status atual ─────────────────────────────────────────────────────────
  -- Atualizado automaticamente via trigger ao fechar PS
  status                      ENUM(
                                'CALIBRADO',           -- ok, dentro da validade
                                'DESCALIBRADO',        -- prazo vencido ou nunca calibrado
                                'EM_REPARO',           -- PS de reparo em aberto
                                'AGUARDANDO_CALIBRACAO',-- reparo concluído, aguarda cal.
                                'SEM_CERTIFICADO',     -- calibrado mas cert. não chegou
                                'NAO_UTILIZADO',       -- ferramenta fora de uso
                                'DESCARTADO'           -- baixado do inventário
                              ) NOT NULL DEFAULT 'DESCALIBRADO',

  -- ── Financeiro ───────────────────────────────────────────────────────────
  max_cost_calibration        DECIMAL(10,2) DEFAULT 0.00
                                COMMENT 'Valor máximo para calibração (pregão)',
  max_cost_repair             DECIMAL(10,2) DEFAULT 0.00
                                COMMENT 'Valor estimado para reparo',

  -- ── Restrição especial ────────────────────────────────────────────────────
  -- Equipamentos que só podem ser calibrados em empresa específica
  has_special_restriction     BOOLEAN DEFAULT FALSE,
  special_restriction_detail  TEXT
                                COMMENT 'Ex: Somente AMETEK Sigton SP. Fora do pregão.',

  -- ── Notas ────────────────────────────────────────────────────────────────
  notes                       TEXT,

  -- ── Controle ─────────────────────────────────────────────────────────────
  is_active                   BOOLEAN DEFAULT TRUE,
  created_by                  INT NULL,
  created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  -- SN é único quando preenchido
  UNIQUE KEY uq_serial(serial_number),

  FOREIGN KEY (organization_id)       REFERENCES organizations(id) ON DELETE SET NULL,
  FOREIGN KEY (default_laboratory_id) REFERENCES laboratories(id)  ON DELETE SET NULL,
  FOREIGN KEY (created_by)            REFERENCES users(id)         ON DELETE SET NULL,

  INDEX idx_status(status),
  INDEX idx_next_cal(next_calibration_date),
  INDEX idx_org(organization_id),
  INDEX idx_lab(default_laboratory_id),
  FULLTEXT idx_ft(asset_type, manufacturer, model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Inventário de instrumentos. Identificado pelo serial_number.';

-- ── 5. SERVICE_ORDERS (Pedidos de Serviço) ────────────────────────────────────
--
--  RELAÇÃO: equipment (1) ──── (N) service_orders
--
--  Um equipamento acumula PS ao longo do tempo:
--    - 1 PS de calibração por ano (rotina)
--    - PS de reparo quando necessário
--    - PS de calibração inicial
--
--  Número gerado por trigger: PS-CMS-AA-NNN (sequencial por ano)
--
CREATE TABLE service_orders (
  id                  INT AUTO_INCREMENT PRIMARY KEY,

  -- ── Número sequencial ─────────────────────────────────────────────────────
  ps_number           VARCHAR(30)  NOT NULL UNIQUE
                        COMMENT 'PS-CMS-26-001 — gerado por trigger',

  -- ── Vínculo com equipamento ───────────────────────────────────────────────
  equipment_id        INT NOT NULL COMMENT 'FK equipment.id — SN identifica o equip.',

  -- ── Tipo do PS ────────────────────────────────────────────────────────────
  service_type        ENUM('calibracao_rotina','calibracao_inicial','reparo','verificacao')
                        NOT NULL DEFAULT 'calibracao_rotina',

  -- ── Laboratório executor (pode diferir do padrão do equipamento) ──────────
  laboratory_id       INT NOT NULL,

  -- ── Ciclo de vida: emissão → envio → calibração → retorno → conclusão ─────
  issue_date          DATE NOT NULL                COMMENT 'Data de emissão do PS',
  sent_date           DATE                         COMMENT 'Data de envio ao laboratório',
  calibration_date    DATE                         COMMENT 'Data em que a calibração foi realizada',
  return_date         DATE                         COMMENT 'Data de retorno do instrumento',

  -- ── Resultado ────────────────────────────────────────────────────────────
  certificate_number  VARCHAR(100)                 COMMENT 'Número do certificado emitido',
  result              ENUM('aprovado','reprovado','sem_resultado') DEFAULT 'sem_resultado',

  -- ── Financeiro ───────────────────────────────────────────────────────────
  max_value           DECIMAL(10,2) DEFAULT 0.00   COMMENT 'Valor máximo contratado',
  executed_value      DECIMAL(10,2)                COMMENT 'Valor efetivamente pago',
  invoice_number      VARCHAR(50)                  COMMENT 'NF / NE',
  contract_ref        VARCHAR(100)                 COMMENT 'ATA / Contrato de referência',

  -- ── Responsáveis ─────────────────────────────────────────────────────────
  issued_by           INT NULL                     COMMENT 'FK users — quem emitiu',
  approved_by_name    VARCHAR(100)                 COMMENT 'Nome do aprovador',
  lab_representative  VARCHAR(100)                 COMMENT 'Representante do laboratório',

  -- ── Status do PS ─────────────────────────────────────────────────────────
  status              ENUM(
                        'RASCUNHO',
                        'EMITIDO',          -- emitido, aguardando envio
                        'ENVIADO',          -- instrumento enviado ao lab
                        'EM_CALIBRACAO',    -- lab confirmou recebimento
                        'CONCLUIDO',        -- retornou calibrado com certificado
                        'CANCELADO'
                      ) NOT NULL DEFAULT 'EMITIDO',

  notes               TEXT,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (equipment_id)  REFERENCES equipment(id)    ON DELETE RESTRICT,
  FOREIGN KEY (laboratory_id) REFERENCES laboratories(id) ON DELETE RESTRICT,
  FOREIGN KEY (issued_by)     REFERENCES users(id)        ON DELETE SET NULL,

  INDEX idx_equipment(equipment_id),
  INDEX idx_status(status),
  INDEX idx_issue_date(issue_date),
  INDEX idx_ps_number(ps_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='PS: pedido de serviço (calibração ou reparo). Um equipamento tem N PS.';

-- ── 6. CALIBRATIONS (registro técnico de cada calibração) ────────────────────
--
--  Vinculado ao PS de calibração concluído.
--  Guarda os parâmetros técnicos medidos.
--
CREATE TABLE calibrations (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  service_order_id      INT NOT NULL UNIQUE   COMMENT 'FK PS — 1 calibração por PS',
  equipment_id          INT NOT NULL,
  laboratory_id         INT NULL,
  calibration_date      DATE NOT NULL,
  calibration_method    VARCHAR(150)          COMMENT 'Norma/método: ABNT, IEC...',
  env_temperature       VARCHAR(30),
  env_humidity          VARCHAR(30),
  env_pressure          VARCHAR(30),
  pass_fail             BOOLEAN               COMMENT 'TRUE=aprovado, FALSE=reprovado',
  certificate_number    VARCHAR(100),
  results_summary       TEXT,
  notes                 TEXT,
  performed_by_name     VARCHAR(100),
  created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (service_order_id) REFERENCES service_orders(id) ON DELETE CASCADE,
  FOREIGN KEY (equipment_id)     REFERENCES equipment(id)       ON DELETE CASCADE,
  FOREIGN KEY (laboratory_id)    REFERENCES laboratories(id)    ON DELETE SET NULL,
  INDEX idx_equipment(equipment_id),
  INDEX idx_date(calibration_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 7. MEASUREMENT_PARAMETERS (parâmetros medidos em cada calibração) ─────────
CREATE TABLE measurement_parameters (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  calibration_id  INT NOT NULL,
  parameter_name  VARCHAR(100) NOT NULL,
  nominal_value   VARCHAR(50),
  measured_value  VARCHAR(50),
  unit            VARCHAR(30),
  tolerance       VARCHAR(50),
  uncertainty     VARCHAR(50),
  pass_fail       BOOLEAN,
  sort_order      TINYINT DEFAULT 0,
  FOREIGN KEY (calibration_id) REFERENCES calibrations(id) ON DELETE CASCADE,
  INDEX idx_cal(calibration_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 8. CERTIFICATES ───────────────────────────────────────────────────────────
CREATE TABLE certificates (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  certificate_number  VARCHAR(100) NOT NULL UNIQUE,
  calibration_id      INT NOT NULL,
  equipment_id        INT NOT NULL,
  issue_date          DATE NOT NULL,
  validity_from       DATE,
  validity_to         DATE,
  status              ENUM('draft','issued','expired','cancelled') DEFAULT 'issued',
  file_path           VARCHAR(500) COMMENT 'Caminho do PDF',
  executed_by         VARCHAR(100),
  approved_by         VARCHAR(100),
  notes               TEXT,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (calibration_id) REFERENCES calibrations(id)  ON DELETE CASCADE,
  FOREIGN KEY (equipment_id)   REFERENCES equipment(id)      ON DELETE CASCADE,
  INDEX idx_equipment(equipment_id),
  INDEX idx_validity(validity_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 9. PS_COUNTER (sequencial anual para número do PS) ────────────────────────
CREATE TABLE ps_counter (
  year    SMALLINT NOT NULL,
  counter INT      NOT NULL DEFAULT 0,
  PRIMARY KEY (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 10. AUDIT_LOG ─────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  table_name  VARCHAR(50)  NOT NULL,
  record_id   INT          NOT NULL,
  action      ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  user_id     INT NULL,
  changed_fields JSON,
  ip_address  VARCHAR(45),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_table_record(table_name, record_id),
  INDEX idx_created(created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 11. NOTIFICATIONS ─────────────────────────────────────────────────────────
CREATE TABLE notifications (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  type          ENUM('calibracao_vencendo','calibracao_vencida','ps_emitido',
                     'ps_retornado','certificado_pendente') NOT NULL,
  title         VARCHAR(200) NOT NULL,
  message       TEXT,
  equipment_id  INT NULL,
  ps_id         INT NULL,
  is_read       BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)     REFERENCES users(id)          ON DELETE CASCADE,
  FOREIGN KEY (equipment_id) REFERENCES equipment(id)     ON DELETE SET NULL,
  FOREIGN KEY (ps_id)        REFERENCES service_orders(id) ON DELETE SET NULL,
  INDEX idx_user_unread(user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;


-- ════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ════════════════════════════════════════════════════════════════

DELIMITER $$

-- Gera número PS automaticamente antes do INSERT
CREATE TRIGGER trg_ps_auto_number
BEFORE INSERT ON service_orders
FOR EACH ROW
BEGIN
  DECLARE v_year  SMALLINT;
  DECLARE v_seq   INT;
  SET v_year = YEAR(IFNULL(NEW.issue_date, CURDATE()));
  INSERT INTO ps_counter (year, counter) VALUES (v_year, 1)
    ON DUPLICATE KEY UPDATE counter = counter + 1;
  SELECT counter INTO v_seq FROM ps_counter WHERE year = v_year;
  SET NEW.ps_number = CONCAT('PS-CMS-', RIGHT(v_year, 2), '-', LPAD(v_seq, 3, '0'));
END $$

-- Ao concluir PS de calibração: atualiza equipment
CREATE TRIGGER trg_ps_concluded_update_equipment
AFTER UPDATE ON service_orders
FOR EACH ROW
BEGIN
  IF NEW.status = 'CONCLUIDO' AND OLD.status != 'CONCLUIDO' THEN
    -- PS de calibração: atualiza datas e status
    IF NEW.service_type IN ('calibracao_rotina','calibracao_inicial','verificacao') THEN
      UPDATE equipment
        SET
          status                  = IF(NEW.certificate_number IS NOT NULL AND NEW.certificate_number != '',
                                       'CALIBRADO', 'SEM_CERTIFICADO'),
          last_calibration_date   = NEW.calibration_date,
          last_certificate_number = IFNULL(NEW.certificate_number, last_certificate_number),
          next_calibration_date   = DATE_ADD(
                                      IFNULL(NEW.calibration_date, CURDATE()),
                                      INTERVAL calibration_interval_months MONTH
                                    ),
          updated_at              = NOW()
      WHERE id = NEW.equipment_id;

    -- PS de reparo: equipamento fica aguardando calibração
    ELSEIF NEW.service_type = 'reparo' THEN
      UPDATE equipment
        SET status = 'AGUARDANDO_CALIBRACAO', updated_at = NOW()
      WHERE id = NEW.equipment_id;
    END IF;
  END IF;
END $$

-- Audit: registra alterações em equipment
CREATE TRIGGER trg_audit_equipment
AFTER UPDATE ON equipment
FOR EACH ROW
BEGIN
  IF NEW.status != OLD.status
     OR NEW.next_calibration_date != OLD.next_calibration_date
     OR NEW.last_certificate_number != OLD.last_certificate_number
  THEN
    INSERT INTO audit_log (table_name, record_id, action, changed_fields)
    VALUES ('equipment', NEW.id, 'UPDATE', JSON_OBJECT(
      'status',                 JSON_ARRAY(OLD.status, NEW.status),
      'last_calibration_date',  JSON_ARRAY(OLD.last_calibration_date, NEW.last_calibration_date),
      'next_calibration_date',  JSON_ARRAY(OLD.next_calibration_date, NEW.next_calibration_date),
      'last_certificate_number',JSON_ARRAY(OLD.last_certificate_number, NEW.last_certificate_number)
    ));
  END IF;
END $$

DELIMITER ;


-- ════════════════════════════════════════════════════════════════
-- STORED PROCEDURES
-- ════════════════════════════════════════════════════════════════

DELIMITER $$

-- KPIs do dashboard
CREATE PROCEDURE sp_kpis_dashboard()
BEGIN
  SELECT
    COUNT(*)                                                              AS total_equipamentos,
    SUM(status = 'CALIBRADO')                                            AS calibrados,
    SUM(status = 'DESCALIBRADO')                                         AS descalibrados,
    SUM(status = 'EM_REPARO')                                            AS em_reparo,
    SUM(status = 'AGUARDANDO_CALIBRACAO')                                AS aguardando_cal,
    SUM(status = 'SEM_CERTIFICADO')                                      AS sem_certificado,
    SUM(status = 'NAO_UTILIZADO')                                        AS nao_utilizados,
    SUM(DATEDIFF(next_calibration_date, CURDATE()) BETWEEN 0 AND 30)     AS vencendo_30d,
    SUM(next_calibration_date < CURDATE()
        AND status = 'CALIBRADO')                                        AS vencidos,
    SUM(has_special_restriction = TRUE)                                  AS com_restricao,
    ROUND(SUM(max_cost_calibration), 2)                                  AS custo_estimado_total
  FROM equipment
  WHERE is_active = TRUE;
END $$

-- Histórico completo de PS de um equipamento (por SN ou ID)
CREATE PROCEDURE sp_historico_ps(IN p_serial_number VARCHAR(100))
BEGIN
  SELECT
    so.ps_number,
    so.service_type,
    so.issue_date,
    so.calibration_date,
    so.return_date,
    so.status,
    so.certificate_number,
    so.executed_value,
    l.name AS laboratorio,
    l.type AS lab_tipo
  FROM service_orders so
  JOIN equipment  e ON so.equipment_id  = e.id
  JOIN laboratories l ON so.laboratory_id = l.id
  WHERE e.serial_number = p_serial_number
  ORDER BY so.issue_date DESC;
END $$

DELIMITER ;


-- ════════════════════════════════════════════════════════════════
-- VIEWS ANALÍTICAS
-- ════════════════════════════════════════════════════════════════

-- Visão completa de cada equipamento com status calculado
CREATE VIEW v_equipment_full AS
SELECT
  e.id,
  e.serial_number,
  e.internal_code,
  e.category,
  e.asset_type,
  e.manufacturer,
  e.model,
  e.range_tolerance,
  o.code                        AS divisao,
  o.name                        AS divisao_nome,
  l.name                        AS laboratorio_padrao,
  l.type                        AS lab_tipo,
  e.calibration_interval_months AS periodicidade_meses,
  e.status,
  e.last_calibration_date,
  e.next_calibration_date,
  e.last_certificate_number,
  e.max_cost_calibration,
  e.has_special_restriction,
  e.special_restriction_detail,
  -- PS mais recente
  (SELECT so.ps_number FROM service_orders so
   WHERE so.equipment_id = e.id
   ORDER BY so.issue_date DESC LIMIT 1)         AS ultimo_ps,
  -- Total de PS emitidos
  (SELECT COUNT(*) FROM service_orders so
   WHERE so.equipment_id = e.id)                AS total_ps,
  -- Dias para vencer (negativo = já vencido)
  DATEDIFF(e.next_calibration_date, CURDATE())  AS dias_para_vencer,
  -- Status enriquecido
  CASE
    WHEN e.status = 'CALIBRADO'
         AND e.next_calibration_date < CURDATE()       THEN 'VENCIDO'
    WHEN e.status = 'CALIBRADO'
         AND DATEDIFF(e.next_calibration_date, CURDATE()) <= 30 THEN 'VENCENDO_30D'
    WHEN e.status = 'CALIBRADO'
         AND DATEDIFF(e.next_calibration_date, CURDATE()) <= 90 THEN 'VENCENDO_90D'
    ELSE e.status
  END AS status_calculado
FROM equipment e
LEFT JOIN organizations o ON e.organization_id       = o.id
LEFT JOIN laboratories  l ON e.default_laboratory_id = l.id
WHERE e.is_active = TRUE;

-- PS em aberto com dados completos
CREATE VIEW v_ps_abertos AS
SELECT
  so.ps_number,
  so.service_type,
  so.status         AS ps_status,
  so.issue_date,
  so.sent_date,
  so.calibration_date,
  so.max_value,
  e.serial_number,
  e.category,
  e.asset_type,
  e.manufacturer,
  e.model,
  o.code            AS divisao,
  l.name            AS laboratorio,
  l.type            AS lab_tipo,
  e.has_special_restriction,
  e.special_restriction_detail,
  DATEDIFF(CURDATE(), so.issue_date) AS dias_em_aberto
FROM service_orders so
JOIN equipment      e ON so.equipment_id  = e.id
LEFT JOIN organizations o ON e.organization_id = o.id
LEFT JOIN laboratories  l ON so.laboratory_id  = l.id
WHERE so.status NOT IN ('CONCLUIDO','CANCELADO')
ORDER BY so.issue_date DESC;

-- Dashboard por divisão
CREATE VIEW v_dashboard_divisao AS
SELECT
  o.code                                                       AS divisao,
  COUNT(e.id)                                                  AS total,
  SUM(e.status IN ('CALIBRADO','SEM_CERTIFICADO'))             AS ok,
  SUM(e.status = 'DESCALIBRADO')                               AS descalibrados,
  SUM(e.status IN ('EM_REPARO','AGUARDANDO_CALIBRACAO'))       AS em_atencao,
  ROUND(SUM(e.max_cost_calibration), 2)                        AS custo_estimado,
  ROUND(SUM(e.status IN ('CALIBRADO','SEM_CERTIFICADO'))
        / NULLIF(COUNT(e.id),0) * 100, 1)                     AS pct_conformidade
FROM organizations o
JOIN equipment e ON e.organization_id = o.id AND e.is_active = TRUE
WHERE o.type = 'division'
GROUP BY o.id, o.code
ORDER BY total DESC;
