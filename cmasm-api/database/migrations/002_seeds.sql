USE cmasm_calibracao;

-- ── Organizações ──────────────────────────────────────────────────────────────
INSERT INTO organizations (code, name, type, parent_id) VALUES
  ('CMASM',        'Centro de Mísseis e Armas Submarinas da Marinha', 'om',         NULL),
  ('DEPT-ARMAS',   'Departamento de Armas',                           'department', 1),
  ('DEPT-INFRA',   'Departamento de Infraestrutura',                  'department', 1),
  ('MK-48',        'Divisão MK-48',                                   'division',   2),
  ('MK-46',        'Divisão MK-46',                                   'division',   2),
  ('F-21',         'Divisão F-21',                                    'division',   2),
  ('EXOCET',       'Divisão EXOCET',                                  'division',   2),
  ('MISTRAL',      'Divisão MISTRAL',                                 'division',   2),
  ('MINAS-BOMBAS', 'Divisão Minas e Bombas',                          'division',   2),
  ('SEASKUA',      'Divisão SEASKUA',                                 'division',   2),
  ('PENGUIN',      'Divisão PENGUIN',                                 'division',   2);

-- ── Laboratórios ──────────────────────────────────────────────────────────────
INSERT INTO laboratories (code, name, type, is_accredited, accreditation, specialties, observations) VALUES
  ('CMS',    'CMS — Centro de Metrologia da Marinha',
   'marinha',   TRUE,  'RBC/INMETRO',
   '["Elétrico","Eletrônico","Dimensional","Temperatura","Resistência"]',
   NULL),

  ('BACS',   'BACS — Base de Abastecimento da Marinha',
   'marinha',   TRUE,  'RBC/INMETRO',
   '["Pressão (água salgada)","Mecânico"]',
   NULL),

  ('MV',     'MV Metrologia',
   'pregao',    TRUE,  'RBC',
   '["Mecânico","Pressão","Torquímetros","Dimensional","Ground Strap","Paquímetros"]',
   NULL),

  ('MQT',    'MQT Metrologia',
   'pregao',    TRUE,  'RBC',
   '["Dimensional","Manômetros","Mecânico","Micrometros"]',
   NULL),

  ('MSMI',   'MSMI — Metrologia e Serviços',
   'pregao',    FALSE, 'Rastreável INMETRO',
   '["Torquímetros","Dimensional","Ground Strap","Paquímetros"]',
   NULL),

  ('LMC',    'LMC — Laboratório de Metrologia e Calibração',
   'pregao',    TRUE,  'RBC',
   '["Temperatura","Pressão digital","Resistência","Termohigrômetros"]',
   NULL),

  ('AMETEK', 'AMETEK Sigton (São Paulo)',
   'autorizada',FALSE, 'Empresa Autorizada AMETEK',
   '["Deadweight Tester","Fontes AMETEK","Equipamentos AMETEK"]',
   'ATENÇÃO: Única empresa autorizada para calibração de equipamentos AMETEK. Fora do pregão padrão. Calibração deve ser solicitada diretamente à AMETEK.'),

  ('IPT',    'IPT São Paulo — NI Certified Center',
   'autorizada',TRUE,  'NI Certified Center',
   '["NI PXI","NI PXIE","National Instruments","Equipamentos NI"]',
   'ATENÇÃO: Único NI Certified Center no Brasil. Obrigatório para equipamentos National Instruments. Não pode ser substituído por laboratório do pregão.');

-- ── Usuários padrão ───────────────────────────────────────────────────────────
-- senha: Admin@2025 (bcrypt hash gerado)
INSERT INTO users (name, email, password_hash, role, organization_id) VALUES
  ('Administrador CMASM',       'admin@cmasm.mb',    '$2a$12$placeholder_admin_hash',   'admin',     1),
  ('Encarregado de Metrologia', 'metro@cmasm.mb',    '$2a$12$placeholder_tecnico_hash', 'tecnico',   1),
  ('Gerente Técnico',           'gerente@cmasm.mb',  '$2a$12$placeholder_gerente_hash', 'gerente',   1);

-- ── Equipamentos reais do PDF (com SN quando disponível) ──────────────────────
-- Nota: serial_number = SN físico do instrumento
-- Onde SN não consta no PDF, deixamos NULL (a ser preenchido no cadastro)

-- == F-21 ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,range_tolerance,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,notes)
VALUES
  -- Differential Probe
  (NULL,'F21-DPROBE-01','ELE','Differential Probe','TESTEC','TT-SI 9001',NULL,
   6,12,'2024-03-12','2025-03-12','CALIBRADO','2142016/2024',1,373.83,NULL),

  -- Fonte DC AMETEK XG — lab MQT
  (NULL,'F21-FDC-AMXG-01','ELE','Fonte DC','AMETEK','XG 300-2.8','300V / 2.8A',
   6,12,'2024-12-12','2025-12-12','CALIBRADO','2142107/2024',4,1164.35,NULL),

  -- Fonte DC BK Precision
  (NULL,'F21-FDC-BK-01','ELE','Fonte DC','BK PRECISION','BK9801',NULL,
   6,12,'2023-05-10','2025-05-10','CALIBRADO','2142034/2023',1,1000.56,NULL),

  -- Fontes DC TDK-Lambda (3 unidades)
  (NULL,'F21-FDC-TDK-01','ELE','Fonte DC','TDK-LAMBDA','Z1020 LAN','10V / 20A',
   6,12,'2023-05-10','2025-05-10','CALIBRADO','2142033/2023',1,1000.56,NULL),
  (NULL,'F21-FDC-TDK-02','ELE','Fonte DC','TDK-LAMBDA','GENH30-25 LAN','30V / 25A',
   6,12,'2023-05-09','2025-05-09','CALIBRADO','2142032/2023',1,1000.56,NULL),
  (NULL,'F21-FDC-TDK-03','ELE','Fonte DC','TDK-LAMBDA','GENH300-2.5 LAN','300V / 2.5A',
   6,12,'2023-05-09','2025-05-09','CALIBRADO','2142031/2023',1,1000.56,NULL),

  -- Fonte DC AMETEK SGA — RESTRIÇÃO ESPECIAL
  (NULL,'F21-FDC-AMSG-01','ELE','Fonte DC','AMETEK','SGA-600625D-1D-AA','600V / 625mA',
   6,12,'2021-01-26',NULL,'DESCALIBRADO',NULL,7,560.75,
   'RESTRIÇÃO: Calibração exclusiva empresa autorizada AMETEK Sigton (SP). Não encaminhar ao CMS ou pregão.'),

  -- Megôhmetros
  (NULL,'F21-MEGA-CA-01','ELE','Megôhmetro','CA','6541',NULL,
   6,12,'2023-10-17','2025-10-17','CALIBRADO','2142103/2023',1,373.83,NULL),
  (NULL,'F21-MEGA-FL-01','ELE','Megôhmetro','FLUKE','1507','0.01MΩ–10GΩ',
   6,12,'2024-10-03','2025-10-03','CALIBRADO','MQT31184/24',4,373.83,NULL),
  (NULL,'F21-MEGA-SE-01','ELE','Megôhmetro','SEFELEC','MXS500','50kΩ–200GΩ',
   6,12,'2023-06-28','2025-06-28','CALIBRADO','E-0422/2023',4,150.00,NULL),

  -- Multímetros FACOM 711B (4 unidades)
  (NULL,'F21-MMT-FC-01','ELE','Multímetro','FACOM','711B',NULL,
   6,12,'2024-12-12','2025-12-12','CALIBRADO','2142109/2024',1,1164.35,NULL),
  (NULL,'F21-MMT-FC-02','ELE','Multímetro','FACOM','711B',NULL,
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,1,776.23,'Ferramenta não utilizada'),
  (NULL,'F21-MMT-FC-03','ELE','Multímetro','FACOM','711B',NULL,
   6,12,'2023-09-27','2025-09-27','CALIBRADO','2142093/2023',1,776.23,NULL),
  (NULL,'F21-MMT-FC-04','ELE','Multímetro','FACOM','711B',NULL,
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,1,776.23,'Ferramenta não utilizada'),

  -- Multímetros FLUKE 17B+ (3 unidades)
  (NULL,'F21-MMT-FL17-01','ELE','Multímetro','FLUKE','17B+',NULL,
   6,12,'2024-07-08','2025-07-08','CALIBRADO','2142044/2023',1,667.04,NULL),
  (NULL,'F21-MMT-FL17-02','ELE','Multímetro','FLUKE','17B+',NULL,
   6,12,'2025-02-04','2026-02-04','CALIBRADO','2142004/2025',1,776.23,NULL),
  (NULL,'F21-MMT-FL17-03','ELE','Multímetro','FLUKE','17B+',NULL,
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,1,776.23,'Ferramenta não utilizada'),

  -- Multímetros 6 Dígitos KEYSIGHT 34461A (2 unidades)
  (NULL,'F21-M6D-KY-01','ELE','Multímetro 6 Dígitos','KEYSIGHT','34461A',NULL,
   6,12,'2023-05-12','2025-05-12','CALIBRADO','2142036/2023',1,667.04,NULL),
  (NULL,'F21-M6D-KY-02','ELE','Multímetro 6 Dígitos','KEYSIGHT','34461A',NULL,
   6,12,'2023-05-12','2025-05-12','CALIBRADO','2142037/2023',1,667.04,NULL),

  -- NI PXIE-4080 — RESTRIÇÃO ESPECIAL
  (NULL,'F21-NI-DMM-01','ELE','Multímetro Digital NI','NATIONAL INSTRUMENTS','PXIE-4080',NULL,
   6,24,'2020-08-03',NULL,'DESCALIBRADO',NULL,8,560.75,
   'RESTRIÇÃO: Calibração somente NI Certified Center — IPT São Paulo.'),

  -- NI PXI-5122 — RESTRIÇÃO ESPECIAL
  (NULL,'F21-NI-OSC-01','ELE','Osciloscópio PXI NI','NATIONAL INSTRUMENTS','NI-PXI-5122',NULL,
   6,24,'2022-09-27',NULL,'DESCALIBRADO',NULL,8,776.23,
   'RESTRIÇÃO: Calibração somente NI Certified Center — IPT São Paulo.'),

  -- Ohmímetros AOIP (3 unidades)
  (NULL,'F21-OHM-01','ELE','Ohmímetro','AOIP','RN5306',NULL,
   6,12,'2023-09-14','2025-09-14','CALIBRADO','2142089/2023',1,776.23,NULL),
  (NULL,'F21-OHM-02','ELE','Ohmímetro','AOIP','RN5306',NULL,
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,1,776.23,'Ferramenta não utilizada'),
  (NULL,'F21-OHM-03','ELE','Ohmímetro','AOIP','RN5306',NULL,
   6,12,'2025-02-11','2026-02-11','CALIBRADO','2142012/2025',1,776.23,NULL),

  -- Termohigrômetro
  (NULL,'F21-THG-01','ELE','Termohigrômetro','OMEGA','HH314A',NULL,
   6,12,'2024-10-03','2025-10-03','CALIBRADO','CMASM-IDE-F21-034',6,80.00,NULL),

  -- Micrometros de profundidade FACOM 806.F (4 unidades)
  (NULL,'F21-MMP-01','MEC','Micrometro de Profundidade','FACOM','806.F','0,01 mm',
   6,12,'2024-09-30','2025-09-30','CALIBRADO','MQT31051/24',4,84.33,NULL),
  (NULL,'F21-MMP-02','MEC','Micrometro de Profundidade','FACOM','806.F','0,01 mm',
   6,12,'2024-10-01','2025-10-01','CALIBRADO','MQT31050/24',4,84.33,NULL),
  (NULL,'F21-MMP-03','MEC','Micrometro de Profundidade','FACOM','806.F','0,01 mm',
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,4,84.33,'Ferramenta não utilizada'),
  (NULL,'F21-MMP-04','MEC','Micrometro de Profundidade','FACOM','806.F','0,01 mm',
   6,12,NULL,NULL,'NAO_UTILIZADO',NULL,4,84.33,'Ferramenta não utilizada'),

  -- Paquímetros FACOM 805.1 (4 unidades)
  (NULL,'F21-PAQ-01','MEC','Paquímetro','FACOM','805.1',NULL,
   6,12,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,84.33,'MSMI LOTE 01 — falta certificado'),
  (NULL,'F21-PAQ-02','MEC','Paquímetro','FACOM','805.1',NULL,
   6,12,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,84.33,'MSMI LOTE 01 — falta certificado'),
  (NULL,'F21-PAQ-03','MEC','Paquímetro','FACOM','805.1',NULL,
   6,12,NULL,NULL,'DESCALIBRADO',NULL,3,84.33,NULL),
  (NULL,'F21-PAQ-04','MEC','Paquímetro','FACOM','805.1',NULL,
   6,12,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,84.33,'MSMI LOTE 01 — falta certificado'),

  -- Manômetro Analógico 400 Bar
  (NULL,'F21-MAN-01','MEC','Manômetro Analógico',NULL,'400 Bar','400 Bar',
   6,12,NULL,NULL,'DESCALIBRADO',NULL,4,90.00,NULL),

  -- Dinamômetro Digital YALE
  (NULL,'F21-DIN-01','MEC','Dinamômetro Digital','YALE','TMC 1500','1500 kg',
   6,12,'2024-10-01','2025-10-01','CALIBRADO','MQT31199/24',4,338.69,NULL);

-- == EXOCET ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,range_tolerance,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,notes)
VALUES
  (NULL,'EXO-AESP-01','ELE','Analisador de Espectro','ROHDE&SCHWARZ','FSL18','3Hz–18GHz',
   7,12,'2024-09-13','2025-09-13','CALIBRADO','2142090/2024',1,3104.95,NULL),
  (NULL,'EXO-GFN-01','ELE','Gerador de Funções','AGILENT','33220A','20MHz',
   7,12,'2024-09-10','2025-09-10','CALIBRADO','2142088/2024',1,1552.47,NULL),
  (NULL,'EXO-MMT-01','ELE','Multímetro','FLUKE','179',NULL,
   7,12,'2023-10-27','2025-10-27','CALIBRADO','2142110/2023',1,560.75,NULL),
  (NULL,'EXO-MMT-02','ELE','Multímetro','FLUKE','73',NULL,
   7,12,'2023-11-01','2025-11-01','CALIBRADO','2142112/2023',1,560.75,NULL),
  (NULL,'EXO-MMT-03','ELE','Multímetro','FLUKE','73',NULL,
   7,12,'2025-04-11','2026-04-11','CALIBRADO','2142141/2023',1,776.23,NULL),
  (NULL,'EXO-M6D-01','ELE','Multímetro 6 Dígitos','AGILENT','34401A',NULL,
   7,12,'2025-02-05','2026-02-05','CALIBRADO','64435-B/2025',1,1164.35,NULL),
  (NULL,'EXO-OSC-01','ELE','Osciloscópio','TEKTRONIX','TDS210','60MHz',
   7,12,'2023-11-10','2025-11-10','CALIBRADO','2142116/2023',1,747.66,NULL),
  (NULL,'EXO-OSC-02','ELE','Osciloscópio','TEKTRONIX','TBS1102B','100MHz',
   7,12,'2023-11-10','2025-11-10','CALIBRADO','2142115/2023',1,747.66,NULL),
  (NULL,'EXO-OHM-01','ELE','Ohmímetro','AGI','1681A',NULL,
   7,12,'2024-11-12','2025-11-12','SEM_CERTIFICADO',NULL,3,776.23,'MSMI LOTE 02 — falta certificado'),
  (NULL,'EXO-OHM-02','ELE','Ohmímetro','SEFELEC','MR46',NULL,
   7,12,'2024-11-12','2025-11-12','SEM_CERTIFICADO',NULL,3,270.00,'MSMI LOTE 02 — falta certificado');

-- == MK-46 ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,range_tolerance,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,notes)
VALUES
  (NULL,'T46-CNT-HP-01','ELE','Contador','HP','5328B','1GHz',
   5,12,'2023-08-10','2025-08-10','CALIBRADO','2142076/2023',1,1552.47,NULL),
  (NULL,'T46-CNT-HP-02','ELE','Contador','HP','5328B','1GHz',
   5,12,NULL,NULL,'DESCALIBRADO',NULL,1,4269.30,NULL),
  (NULL,'T46-CNT-HP-03','ELE','Contador','HP','5328B','1GHz',
   5,12,NULL,NULL,'EM_REPARO',NULL,1,1552.47,'Em reparo CMS'),
  (NULL,'T46-CNT-HP-04','ELE','Contador','HP','5328B','1GHz',
   5,12,'2023-11-14','2025-11-14','CALIBRADO','2142118/2023',1,1552.47,NULL),
  (NULL,'T46-CNT-HP-05','ELE','Contador','HP','5328B','1GHz',
   5,12,'2023-11-14','2025-11-14','CALIBRADO','2142119/2023',1,1552.47,NULL),
  (NULL,'T46-CNT-AS-01','ELE','Contador','ASTRONICS','2461-CD',NULL,
   5,12,NULL,NULL,'DESCALIBRADO',NULL,4,1552.47,'Não foi possível calibrar — verificar viabilidade'),
  (NULL,'T46-CNT-AS-02','ELE','Contador','ASTRONICS','2461-CD',NULL,
   5,12,NULL,NULL,'DESCALIBRADO',NULL,4,1552.47,'Não foi possível calibrar — verificar viabilidade'),
  (NULL,'T46-GFN-HP-01','ELE','Gerador de Funções','HP','3325B','21MHz',
   5,12,'2023-11-14','2025-11-14','CALIBRADO','2142012/2024',1,1869.16,NULL),
  (NULL,'T46-GFN-RC-01','ELE','Gerador de Funções','RACAL','3152B VXI',NULL,
   5,12,NULL,NULL,'DESCALIBRADO',NULL,4,1552.47,'CMS NÃO CALIBRA — encaminhar para empresa externa'),
  (NULL,'T46-GFN-RC-02','ELE','Gerador de Funções','RACAL','3152B VXI',NULL,
   5,12,NULL,NULL,'DESCALIBRADO',NULL,4,1552.47,'CMS NÃO CALIBRA — encaminhar para empresa externa'),
  (NULL,'T46-MMT-FL-01','ELE','Multímetro','FLUKE','87 V',NULL,
   5,12,'2024-08-08','2025-08-08','CALIBRADO','2142069/2024',1,1164.35,NULL),
  (NULL,'T46-MMT-FL-02','ELE','Multímetro','FLUKE','87',NULL,
   5,12,'2024-08-08','2025-08-08','CALIBRADO','2142068/2024',1,1164.35,NULL),
  (NULL,'T46-MMT-FL-03','ELE','Multímetro','FLUKE','87',NULL,
   5,12,'2023-11-20','2025-11-20','CALIBRADO','2142109/2023',1,560.75,NULL),
  (NULL,'T46-MMT-IC-01','ELE','Multímetro','ICEL','6300',NULL,
   5,12,'2024-08-13','2025-08-13','CALIBRADO','2142075/2024',1,1164.35,NULL),
  (NULL,'T46-MMT-IC-02','ELE','Multímetro','ICEL','6300',NULL,
   5,12,'2025-04-02','2026-04-02','CALIBRADO','2142037/2023',1,776.23,NULL),
  (NULL,'T46-MMT-IC-03','ELE','Multímetro','ICEL','MA-60',NULL,
   5,12,NULL,NULL,'DESCALIBRADO',NULL,1,776.23,NULL),
  (NULL,'T46-M6D-HP-01','ELE','Multímetro 6 Dígitos','HP','3456A',NULL,
   5,12,'2025-02-11','2026-02-11','CALIBRADO','2142013/2025',1,1164.35,NULL),
  (NULL,'T46-M6D-HP-02','ELE','Multímetro 6 Dígitos','HP','3456A',NULL,
   5,12,'2025-02-11','2026-02-11','CALIBRADO','2142014/2025',1,1164.35,NULL),
  (NULL,'T46-OSC-KY-01','ELE','Osciloscópio','KEYSIGHT','DSO5034A','350MHz',
   5,12,'2023-08-15','2025-08-15','CALIBRADO','2142078/2023',1,1552.47,NULL),
  (NULL,'T46-OSC-KY-02','ELE','Osciloscópio','KEYSIGHT','DSO5034A','350MHz',
   5,12,'2023-10-20','2025-10-20','CALIBRADO','2142107/2023',1,747.66,NULL),
  (NULL,'T46-MAN-MS-01','MEC','Manômetro Analógico','MENSOR','2780','800 PSI',
   5,12,'2024-10-01','2025-10-01','CALIBRADO','MQT31196/24',4,90.00,NULL);

-- == MK-48 ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,range_tolerance,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,max_cost_repair,notes,
   has_special_restriction,special_restriction_detail)
VALUES
  (NULL,'T48-CMF-FL-01','ELE','Calibrador Multifunção','FLUKE','5100B','7 fontes',
   4,12,'2025-01-10','2026-01-10','CALIBRADO','2142002/2025',1,3104.95,0,NULL,FALSE,NULL),
  (NULL,'T48-CMF-FL-02','ELE','Calibrador Multifunção','FLUKE','5100B','7 fontes',
   4,12,'2024-11-08','2025-11-08','CALIBRADO',NULL,1,3104.95,0,NULL,FALSE,NULL),
  (NULL,'T48-CMF-FL-03','ELE','Calibrador Multifunção','FLUKE','5100B','7 fontes',
   4,12,'2023-01-19','2025-01-19','DESCALIBRADO',NULL,1,3104.95,0,NULL,FALSE,NULL),
  (NULL,'T48-AMP-FL-01','ELE','Amplificador Transcondutância','FLUKE','5220A','32A',
   4,12,'2023-11-24','2025-11-24','CALIBRADO','2142130/2023',1,776.23,0,NULL,FALSE,NULL),
  (NULL,'T48-AMP-FL-02','ELE','Amplificador Transcondutância','FLUKE','5220A','32A',
   4,12,'2024-06-12','2026-06-12','CALIBRADO','2142048/2023',1,373.86,0,NULL,FALSE,NULL),
  (NULL,'T48-MEG-TG-01','ELE','Megôhmetro','TEGAM','R1M-A','36MΩ',
   4,12,'2025-02-07','2026-02-07','CALIBRADO','2142010/2025',1,674.72,0,NULL,FALSE,NULL),
  (NULL,'T48-MMT-SI-01','ELE','Multímetro','SIMPSON','260-6XLPM','20kΩ/V',
   4,20,'2024-11-21','2025-11-21','CALIBRADO','2142103/2024',1,776.23,0,NULL,FALSE,NULL),
  (NULL,'T48-MMT-FL-01','ELE','Multímetro','FLUKE','77','36A',
   4,36,'2024-03-21','2025-03-21','DESCALIBRADO',NULL,1,776.23,0,'PS 036/2023',FALSE,NULL),
  (NULL,'T48-MMT-FL-02','ELE','Multímetro','FLUKE','83-V','36A',
   4,36,'2024-03-25','2025-03-25','DESCALIBRADO',NULL,1,560.75,0,'PS 035/2023',FALSE,NULL),
  (NULL,'T48-OSC-TK-01','ELE','Osciloscópio','TEKTRONIX','THS730A','200MHz',
   4,12,'2022-08-18','2024-08-18','DESCALIBRADO',NULL,1,747.66,0,'PS 046/2023',FALSE,NULL),
  (NULL,'T48-OSC-TK-02','ELE','Osciloscópio','TEKTRONIX','TBS1102B','100MHz',
   4,12,'2024-04-08','2025-04-08','DESCALIBRADO',NULL,1,747.66,0,'PS 047/2023',FALSE,NULL),
  (NULL,'T48-GST-01','ELE','Ground Strap Tester',NULL,'253A',NULL,
   4,12,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,0,0,'MSMI LOTE 01 — falta certificado',FALSE,NULL),
  (NULL,'T48-ICT-01','ELE','Igniter Circuit Test',NULL,'101-5BFAA','36A',
   4,36,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,776.23,0,'MSMI LOTE 01 — falta certificado',FALSE,NULL),
  (NULL,'T48-ICT-02','ELE','Igniter Circuit Test',NULL,'101-5BFAA','36A',
   4,36,'2024-10-22','2025-10-22','SEM_CERTIFICADO',NULL,3,776.23,0,'MSMI LOTE 01 — falta certificado',FALSE,NULL),
  (NULL,'T48-ICT-03','ELE','Igniter Circuit Test',NULL,'101-5BFAA','36A',
   4,36,'2022-05-26',NULL,'DESCALIBRADO',NULL,3,776.23,0,'Não calibrar em 2024',FALSE,NULL),
  (NULL,'T48-ICT-04','ELE','Igniter Circuit Test',NULL,'101-5BFAA','36A',
   4,36,'2023-02-24',NULL,'DESCALIBRADO',NULL,3,776.23,0,'Não calibrar em 2024',FALSE,NULL),
  (NULL,'T48-TMP-01','ELE','Termômetro Digital','OMEGA','HH11B','750°C',
   4,12,'2024-10-03','2025-10-03','CALIBRADO','CMASM-IDM-T48-062',6,84.33,0,NULL,FALSE,NULL),
  -- Hydraulic Deadweight Tester AMETEK — RESTRIÇÃO ESPECIAL
  (NULL,'T48-DWT-01','MEC','Hydraulic Deadweight Tester','AMETEK','DM-T-100/C','15000 PSI',
   4,24,'2017-10-18',NULL,'DESCALIBRADO',NULL,7,84.33,0,NULL,TRUE,
   'Calibração exclusiva empresa autorizada AMETEK Sigton (SP). Não pode ser encaminhado ao CMS ou pregão.'),
  (NULL,'T48-DWT-02','MEC','Hydraulic Deadweight Tester','AMETEK','DM-T-100/C','15000 PSI',
   4,24,'2017-04-04',NULL,'DESCALIBRADO',NULL,7,84.33,0,NULL,TRUE,
   'Calibração exclusiva empresa autorizada AMETEK Sigton (SP). Não pode ser encaminhado ao CMS ou pregão.');

-- == MISTRAL ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,notes)
VALUES
  (NULL,'MST-FDC-01','ELE','Fonte DC','HP','6255A',
   8,12,'2024-12-18','2025-12-18','CALIBRADO','2142110/2024',1,560.75,NULL),
  (NULL,'MST-M6D-01','ELE','Multímetro 6 Dígitos','KEYSIGHT','34461A',
   8,12,'2017-10-05',NULL,'EM_REPARO',NULL,1,776.23,
   'Em reparo CMS desde 2017 (>7 anos sem retorno)');

-- == MINAS E BOMBAS ==
INSERT INTO equipment
  (serial_number,internal_code,category,asset_type,manufacturer,model,range_tolerance,
   organization_id,calibration_interval_months,last_calibration_date,next_calibration_date,
   status,last_certificate_number,default_laboratory_id,max_cost_calibration,notes)
VALUES
  (NULL,'MB-MMT-01','ELE','Multímetro','FLUKE','77DMM',NULL,
   9,12,'2023-11-09','2025-11-09','CALIBRADO','2142113/2023',1,776.23,NULL),
  (NULL,'MB-MAN-01','MEC','Manômetro Analógico','FAMABRAS','0-3 kgf/cm²','3 kgf/cm²',
   9,24,'2024-01-24','2026-01-24','CALIBRADO','P-006396',4,90.00,NULL),
  (NULL,'MB-MAN-02','MEC','Manômetro Analógico','FAMABRAS','0-30 kgf/cm²','30 kgf/cm²',
   9,24,'2024-01-24','2026-01-24','CALIBRADO','P-006397',4,90.00,NULL);

-- ── PS iniciais baseados no PDF (histórico existente) ─────────────────────────
-- Inserimos manualmente para preservar numeração histórica

-- Desabilitar trigger de autonumeração para inserção histórica
SET @trigger_disabled = TRUE;

INSERT INTO service_orders
  (ps_number, equipment_id, service_type, laboratory_id, issue_date, calibration_date,
   status, certificate_number, max_value, executed_value, issued_by)
SELECT
  'PS-CMS-25-001', e.id, 'calibracao_rotina', 1, '2025-03-05', '2024-03-12',
  'CONCLUIDO', '2142016/2024', 373.83, 373.83, 1
FROM equipment e WHERE e.internal_code = 'F21-DPROBE-01';

INSERT INTO service_orders
  (ps_number, equipment_id, service_type, laboratory_id, issue_date, calibration_date,
   status, certificate_number, max_value, executed_value, issued_by)
SELECT
  'PS-CMS-25-006', e.id, 'calibracao_rotina', 4, '2025-08-23', '2024-12-12',
  'CONCLUIDO', '2142107/2024', 1164.35, 1164.35, 1
FROM equipment e WHERE e.internal_code = 'F21-FDC-AMXG-01';

-- Atualizar contador de PS para 2025 (já usamos até 006)
INSERT INTO ps_counter (year, counter) VALUES (2025, 6)
  ON DUPLICATE KEY UPDATE counter = 6;
INSERT INTO ps_counter (year, counter) VALUES (2026, 0);
