-- seed_locais_cmasm.sql
-- Locais do CMASM com IDs originais preservados (id=151 como raiz)
-- Gerado a partir de: docs/arvore_locais_cmasm.md
-- Área funcional: ADM=Administrativa · OPE=Operacional · APA=Apoio

-- ── RAIZ ────────────────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(151,'CMASM-ROOT','ROOT','Centro de Mísseis e Armas Submarinas (CMASM)',
 'organizacao_raiz','OPE','militar',NULL);

-- ── LOCALIZAÇÕES E ÁREAS EXTERNAS ───────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(230,'CMASM-LOC-01','LOC-01','Ilha do Engenho - São Gonçalo/RJ','localizacao','OPE','militar',151),
(231,'CMASM-LOC-02','LOC-02','Cais Administrativo','area_externa','ADM','militar',151),
(232,'CMASM-LOC-03','LOC-03','Campo de Futebol','area_externa','APA','civil',151),
(233,'CMASM-LOC-04','LOC-04','Quadra de Vôlei','area_externa','APA','civil',151),
(234,'CMASM-LOC-05','LOC-05','Casa de Bombas','infraestrutura','OPE','militar',151);

-- ── COMPLEXO DE PAIÓIS ───────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(235,'CMASM-PAIOIS','PAIOIS','Complexo de Paióis de Armamento','complexo_paiol','OPE','reservado',151);

INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(236,'CMASM-PAIOL-01','PAIOL-01','Paiol de Armamento 01','paiol','OPE','reservado',235),
(237,'CMASM-PAIOL-02','PAIOL-02','Paiol de Armamento 02','paiol','OPE','reservado',235),
(238,'CMASM-PAIOL-03','PAIOL-03','Paiol de Armamento 03','paiol','OPE','reservado',235),
(239,'CMASM-PAIOL-04','PAIOL-04','Paiol de Armamento 04','paiol','OPE','reservado',235),
(240,'CMASM-PAIOL-05','PAIOL-05','Paiol de Armamento 05','paiol','OPE','reservado',235),
(241,'CMASM-PAIOL-06','PAIOL-06','Paiol de Armamento 06','paiol','OPE','reservado',235),
(242,'CMASM-PAIOL-07','PAIOL-07','Paiol de Armamento 07','paiol','OPE','reservado',235),
(243,'CMASM-PAIOL-08','PAIOL-08','Paiol de Armamento 08','paiol','OPE','reservado',235),
(244,'CMASM-PAIOL-09','PAIOL-09','Paiol de Armamento 09','paiol','OPE','reservado',235),
(245,'CMASM-PAIOL-10','PAIOL-10','Paiol de Armamento 10','paiol','OPE','reservado',235),
(246,'CMASM-PAIOL-11','PAIOL-11','Paiol de Armamento 11','paiol','OPE','reservado',235),
(247,'CMASM-PAIOL-12','PAIOL-12','Paiol de Armamento 12','paiol','OPE','reservado',235),
(248,'CMASM-PAIOL-13','PAIOL-13','Paiol de Armamento 13','paiol','OPE','reservado',235),
(249,'CMASM-PAIOL-14','PAIOL-14','Paiol de Armamento 14','paiol','OPE','reservado',235),
(250,'CMASM-PAIOL-15','PAIOL-15','Paiol de Armamento 15','paiol','OPE','reservado',235),
(251,'CMASM-PAIOL-16','PAIOL-16','Paiol de Armamento 16','paiol','OPE','reservado',235),
(252,'CMASM-PAIOL-17','PAIOL-17','Paiol de Armamento 17','paiol','OPE','reservado',235),
(253,'CMASM-PAIOL-18','PAIOL-18','Paiol de Armamento 18','paiol','OPE','reservado',235),
(254,'CMASM-PAIOL-19','PAIOL-19','Paiol de Armamento 19','paiol','OPE','reservado',235),
(255,'CMASM-PAIOL-20','PAIOL-20','Paiol de Armamento 20','paiol','OPE','reservado',235),
(256,'CMASM-PAIOL-21','PAIOL-21','Paiol de Armamento 21','paiol','OPE','reservado',235),
(257,'CMASM-PAIOL-22','PAIOL-22','Paiol de Armamento 22','paiol','OPE','reservado',235),
(258,'CMASM-PAIOL-23','PAIOL-23','Paiol de Armamento 23','paiol','OPE','reservado',235),
(259,'CMASM-PAIOL-24','PAIOL-24','Paiol de Armamento 24','paiol','OPE','reservado',235),
(260,'CMASM-PAIOL-25','PAIOL-25','Paiol de Armamento 25','paiol','OPE','reservado',235),
(261,'CMASM-PAIOL-26','PAIOL-26','Paiol de Armamento 26','paiol','OPE','reservado',235),
(262,'CMASM-PAIOL-27','PAIOL-27','Paiol de Armamento 27','paiol','OPE','reservado',235),
(263,'CMASM-PAIOL-28','PAIOL-28','Paiol de Armamento 28','paiol','OPE','reservado',235),
(264,'CMASM-PAIOL-29','PAIOL-29','Paiol de Armamento 29','paiol','OPE','reservado',235),
(265,'CMASM-PAIOL-30','PAIOL-30','Paiol de Armamento 30','paiol','OPE','reservado',235),
(266,'CMASM-PAIOL-31','PAIOL-31','Paiol de Armamento 31','paiol','OPE','reservado',235),
(267,'CMASM-PAIOL-32','PAIOL-32','Paiol de Armamento 32','paiol','OPE','reservado',235),
(268,'CMASM-PAIOL-33','PAIOL-33','Paiol de Armamento 33','paiol','OPE','reservado',235),
(269,'CMASM-PAIOL-34','PAIOL-34','Paiol de Armamento 34','paiol','OPE','reservado',235),
(270,'CMASM-PAIOL-35','PAIOL-35','Paiol de Armamento 35','paiol','OPE','reservado',235),
(271,'CMASM-PAIOL-36','PAIOL-36','Paiol de Armamento 36','paiol','OPE','reservado',235),
(272,'CMASM-PAIOL-37','PAIOL-37','Paiol de Armamento 37','paiol','OPE','reservado',235),
(273,'CMASM-PAIOL-38','PAIOL-38','Paiol de Armamento 38','paiol','OPE','reservado',235),
(274,'CMASM-PAIOL-39','PAIOL-39','Paiol de Armamento 39','paiol','OPE','reservado',235),
(275,'CMASM-PAIOL-40','PAIOL-40','Paiol de Armamento 40','paiol','OPE','reservado',235),
(276,'CMASM-PAIOL-41','PAIOL-41','Paiol de Armamento 41','paiol','OPE','reservado',235),
(277,'CMASM-PAIOL-42','PAIOL-42','Paiol de Armamento 42','paiol','OPE','reservado',235),
(278,'CMASM-PAIOL-43','PAIOL-43','Paiol de Armamento 43','paiol','OPE','reservado',235),
(279,'CMASM-PAIOL-44','PAIOL-44','Paiol de Armamento 44','paiol','OPE','reservado',235),
(280,'CMASM-PAIOL-45','PAIOL-45','Paiol de Armamento 45','paiol','OPE','reservado',235),
(281,'CMASM-PAIOL-46','PAIOL-46','Paiol de Armamento 46','paiol','OPE','reservado',235),
(282,'CMASM-PAIOL-47','PAIOL-47','Paiol de Armamento 47','paiol','OPE','reservado',235),
(283,'CMASM-PAIOL-48','PAIOL-48','Paiol de Armamento 48','paiol','OPE','reservado',235),
(284,'CMASM-PAIOL-49','PAIOL-49','Paiol de Armamento 49','paiol','OPE','reservado',235),
(285,'CMASM-PAIOL-50','PAIOL-50','Paiol de Armamento 50','paiol','OPE','reservado',235),
(286,'CMASM-PAIOL-51','PAIOL-51','Paiol de Armamento 51','paiol','OPE','reservado',235),
(287,'CMASM-PAIOL-52','PAIOL-52','Paiol de Armamento 52','paiol','OPE','reservado',235),
(288,'CMASM-PAIOL-53','PAIOL-53','Paiol de Armamento 53','paiol','OPE','reservado',235),
(289,'CMASM-PAIOL-54','PAIOL-54','Paiol de Armamento 54','paiol','OPE','reservado',235),
(290,'CMASM-PAIOL-55','PAIOL-55','Paiol de Armamento 55','paiol','OPE','reservado',235),
(291,'CMASM-PAIOL-56','PAIOL-56','Paiol de Armamento 56','paiol','OPE','reservado',235),
(292,'CMASM-PAIOL-57','PAIOL-57','Paiol de Armamento 57','paiol','OPE','reservado',235),
(293,'CMASM-PAIOL-58','PAIOL-58','Paiol de Armamento 58','paiol','OPE','reservado',235),
(294,'CMASM-PAIOL-59','PAIOL-59','Paiol de Armamento 59','paiol','OPE','reservado',235),
(295,'CMASM-PAIOL-60','PAIOL-60','Paiol de Armamento 60','paiol','OPE','reservado',235),
(296,'CMASM-PAIOL-61','PAIOL-61','Paiol de Armamento 61','paiol','OPE','reservado',235),
(297,'CMASM-PAIOL-62','PAIOL-62','Paiol de Armamento 62','paiol','OPE','reservado',235),
(298,'CMASM-PAIOL-63','PAIOL-63','Paiol de Armamento 63','paiol','OPE','reservado',235),
(299,'CMASM-PAIOL-64','PAIOL-64','Paiol de Armamento 64','paiol','OPE','reservado',235),
(300,'CMASM-PAIOL-65','PAIOL-65','Paiol de Armamento 65','paiol','OPE','reservado',235);

-- ── DIREÇÃO ─────────────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(152,'CMASM-01','01','Direção (CMASM-01)','direcao','ADM','militar',151),
(153,'CMASM-01.1','01.1','Gabinete do Diretor(a)','chefe_gabinete','ADM','militar',152),
(154,'CMASM-01.2','01.2','Assessoria de Inteligência','assessor','ADM','secreto',152),
(155,'CMASM-01.3','01.3','Assessoria Jurídica','assessor','ADM','militar',152),
(156,'CMASM-01.4','01.4','OSIC – Of. Segurança das Informações e Comunicações','assessor','ADM','reservado',152);

-- ── VICE-DIREÇÃO ─────────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(157,'CMASM-02','02','Vice-Direção (CMASM-02)','vice_direcao','ADM','militar',151),
(158,'CMASM-02.1','02.1','Gabinete do Vice-Diretor(a)','chefe_gabinete','ADM','militar',157),
(159,'CMASM-SECOM','SECOM','Secretaria e Comunicações (SECOM)','encarregado_servico','ADM','militar',151),
(160,'CMASM-SECOM.1','SECOM.1','Seção de Mensagens','encarregado_secao','ADM','reservado',159),
(161,'CMASM-SECOM.2','SECOM.2','Seção de Expedientes','encarregado_secao','ADM','militar',159);

-- ── SPD ─────────────────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(162,'CMASM-SPD','SPD','Serviço de Processamento de Dados (SPD)','encarregado_servico','ADM','militar',157),
(163,'CMASM-SPD.1','SPD.1','Seção de Infraestrutura de Rede','encarregado_secao','ADM','militar',162),
(164,'CMASM-SPD.2','SPD.2','Seção de Manutenção de Hardware','encarregado_secao','ADM','militar',162),
(165,'CMASM-SPD.3','SPD.3','Seção de Telefonia e Enlace Rádio','encarregado_secao','ADM','militar',162);

-- ── DEPTO INFRAESTRUTURA ─────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(166,'CMASM-DINF','DINF','Departamento de Infraestrutura','chefe_departamento','ADM','militar',151),
(167,'CMASM-DINF.S','DINF.S','Secretário(a) do Depto de Infraestrutura','secretario_depto','ADM','militar',166);

-- ── DIVISÃO DE PREFEITURA ────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(168,'CMASM-DPREF','DPREF','Divisão de Prefeitura','encarregado_divisao','APA','militar',151),
(169,'CMASM-DPREF.1','DPREF.1','Seção de Infraestrutura e Serviços Gerais','encarregado_secao','APA','militar',168),
(170,'CMASM-DPREF.2','DPREF.2','Seção de Transportes','encarregado_secao','APA','militar',168);

-- ── DIVISÃO DE SEGURANÇA ─────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(171,'CMASM-DSEG','DSEG','Divisão de Segurança','encarregado_divisao','OPE','militar',151),
(172,'CMASM-DSEG.1','DSEG.1','Seção de Segurança de Área e Instalações','encarregado_secao','OPE','militar',171),
(173,'CMASM-DSEG.2','DSEG.2','Seção de Escoteria','encarregado_secao','OPE','militar',171),
(174,'CMASM-DSEG.3','DSEG.3','Seção de Controle de Avarias','encarregado_secao','OPE','militar',171);

-- ── DIVISÃO DE MANUTENÇÃO ESPECIALIZADA (CMASM-13) ──────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(175,'CMASM-13','13','Divisão de Manutenção Especializada','encarregado_divisao','OPE','militar',151),
(176,'CMASM-13.1','13.1','Seção de Apoio Industrial','encarregado_secao','OPE','militar',175),
(177,'CMASM-13.2','13.2','Seção de Eletrônica','encarregado_secao','OPE','militar',175);

-- ── DEPTO DE ARMAS ───────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(178,'CMASM-DARM','DARM','Departamento de Armas','chefe_departamento','OPE','reservado',151),
(179,'CMASM-DARM.S','DARM.S','Secretário(a) do Depto de Armas','secretario_depto','OPE','reservado',178);

-- ── GRUPO DE APOIO À MUNIÇÃO INTELIGENTE ────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(180,'CMASM-GAMI','GAMI','Grupo de Apoio à Munição Inteligente','encarregado_grupo','OPE','reservado',151),
(181,'CMASM-GAMI.DMC','GAMI.DMC','Divisão de Material Controlado','encarregado_divisao','OPE','reservado',180),
(182,'CMASM-GAMI.DMC.1','GAMI.DMC.1','Seção de Controle de Material Explosivo','encarregado_secao','OPE','proibido',181),
(183,'CMASM-GAMI.DMC.2','GAMI.DMC.2','Seção de Sobressalentes Inertes','encarregado_secao','OPE','reservado',181),
(184,'CMASM-GAMI.DCE','GAMI.DCE','Divisão de Controle e Expedição','encarregado_divisao','OPE','reservado',180),
(185,'CMASM-GAMI.DCE.1','GAMI.DCE.1','Seção de Controle','encarregado_secao','OPE','reservado',184),
(186,'CMASM-GAMI.DCE.2','GAMI.DCE.2','Seção de Expedição','encarregado_secao','OPE','reservado',184);

-- ── GRUPO DE ARMAS SUBMARINAS ────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(187,'CMASM-GAS','GAS','Grupo de Armas Submarinas','encarregado_grupo','OPE','secreto',151),
-- Torpedos Leves
(188,'CMASM-GAS.DTL','GAS.DTL','Divisão de Torpedos Leves','encarregado_divisao','OPE','secreto',187),
(189,'CMASM-GAS.DTL.1','GAS.DTL.1','Seção de Eletrônica MK-46','encarregado_secao','OPE','secreto',188),
(190,'CMASM-GAS.DTL.2','GAS.DTL.2','Seção de Mecânica MK-46','encarregado_secao','OPE','secreto',188),
-- Torpedos Pesados
(191,'CMASM-GAS.DTP','GAS.DTP','Divisão de Torpedos Pesados','encarregado_divisao','OPE','secreto',187),
(192,'CMASM-GAS.DTP.1','GAS.DTP.1','Seção de Acessórios MK-48','encarregado_secao','OPE','secreto',191),
(193,'CMASM-GAS.DTP.2','GAS.DTP.2','Seção de Eletrônica MK-48','encarregado_secao','OPE','secreto',191),
(194,'CMASM-GAS.DTP.3','GAS.DTP.3','Seção de Tanque MK-48','encarregado_secao','OPE','secreto',191),
(195,'CMASM-GAS.DTP.4','GAS.DTP.4','Seção de Propulsão MK-48','encarregado_secao','OPE','secreto',191),
(196,'CMASM-GAS.DTP.5','GAS.DTP.5','Seção de Mecânica F21','encarregado_secao','OPE','secreto',191),
(197,'CMASM-GAS.DTP.6','GAS.DTP.6','Seção de Eletrônica F21','encarregado_secao','OPE','secreto',191),
(198,'CMASM-GAS.DTP.7','GAS.DTP.7','Seção de Qualidade','encarregado_secao','OPE','secreto',191),
-- Minas e Bombas
(199,'CMASM-GAS.DMB','GAS.DMB','Divisão de Minas e Bombas','encarregado_divisao','OPE','secreto',187),
(200,'CMASM-GAS.DMB.1','GAS.DMB.1','Seção de Minas Mecânicas e Bombas','encarregado_secao','OPE','secreto',199),
(201,'CMASM-GAS.DMB.2','GAS.DMB.2','Seção de Minas Eletrônicas','encarregado_secao','OPE','secreto',199);

-- ── GRUPO DE MÍSSEIS ─────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(202,'CMASM-GM','GM','Grupo de Mísseis','encarregado_grupo','OPE','secreto',151),
(203,'CMASM-GM.DMEF','GM.DMEF','Divisão de Mísseis Especiais e Foguetes','encarregado_divisao','OPE','secreto',202),
(204,'CMASM-GM.DMEF.1','GM.DMEF.1','Seção de Mísseis Especiais','encarregado_secao','OPE','secreto',203),
(205,'CMASM-GM.DMEF.2','GM.DMEF.2','Seção de Foguetes','encarregado_secao','OPE','secreto',203),
(206,'CMASM-GM.DME','GM.DME','Divisão de Mísseis Exocet','encarregado_divisao','OPE','secreto',202),
(207,'CMASM-GM.DME.1','GM.DME.1','Seção de Mísseis Exocet MM-40','encarregado_secao','OPE','secreto',206),
(208,'CMASM-GM.DME.2','GM.DME.2','Seção de Mísseis Exocet AM-39 e SM-39','encarregado_secao','OPE','secreto',206);

-- ── DEPTO DE ADMINISTRAÇÃO ───────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(209,'CMASM-DADM','DADM','Departamento de Administração','chefe_departamento','ADM','militar',151),
(210,'CMASM-DADM.S','DADM.S','Secretário(a) do Depto de Administração','secretario_depto','ADM','militar',209);

-- ── DIVISÃO DE PESSOAL ───────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(211,'CMASM-DPES','DPES','Divisão de Pessoal','encarregado_divisao','ADM','militar',151),
(212,'CMASM-DPES.1','DPES.1','Seção de Pessoal Militar','encarregado_secao','ADM','militar',211),
(213,'CMASM-DPES.2','DPES.2','Seção de Pessoal Civil','encarregado_secao','ADM','militar',211),
(214,'CMASM-DPES.3','DPES.3','Seção de Adestramento','encarregado_secao','ADM','militar',211),
(215,'CMASM-DPES.4','DPES.4','Seção de Direitos Pecuniários','encarregado_secao','ADM','militar',211);

-- ── DIVISÃO DE EXECUÇÃO FINANCEIRA ──────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(216,'CMASM-DEF','DEF','Divisão de Execução Financeira','encarregado_divisao','ADM','militar',151),
(217,'CMASM-DEF.1','DEF.1','Seção de Gestão Financeira e Operação SIAFI','encarregado_secao','ADM','militar',216);

-- ── DIVISÃO DE MUNICIAMENTO ──────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(218,'CMASM-DMUN','DMUN','Divisão de Municiamento','encarregado_divisao','OPE','militar',151),
(219,'CMASM-DMUN.1','DMUN.1','Seção de Subsistência','encarregado_secao','OPE','militar',218),
(220,'CMASM-DMUN.2','DMUN.2','Seção de Armazenagem de Gêneros','encarregado_secao','OPE','militar',218);

-- ── DIVISÃO DE MATERIAL ──────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(221,'CMASM-DMAT','DMAT','Divisão de Material','encarregado_divisao','OPE','militar',151),
(222,'CMASM-DMAT.1','DMAT.1','Seção de Controle Patrimonial','encarregado_secao','OPE','militar',221),
(223,'CMASM-DMAT.2','DMAT.2','Seção de Almoxarifado','encarregado_secao','OPE','militar',221),
(224,'CMASM-DMAT.3','DMAT.3','Seção de Combustíveis, Lubrificantes e Graxas','encarregado_secao','OPE','militar',221);

-- ── DIVISÃO DE OBTENÇÃO ──────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(225,'CMASM-DOB','DOB','Divisão de Obtenção','encarregado_divisao','ADM','militar',151),
(226,'CMASM-DOB.1','DOB.1','Seção de Licitações e Contratos','encarregado_secao','ADM','militar',225);

-- ── DIVISÃO DE SAÚDE ─────────────────────────────────────────
INSERT OR IGNORE INTO locais (id,codigo,neo,nome,tipo,area,restricao,parent_id) VALUES
(227,'CMASM-DSAU','DSAU','Divisão de Saúde','encarregado_divisao','APA','militar',151),
(228,'CMASM-DSAU.1','DSAU.1','Seção Médica','encarregado_secao','APA','militar',227),
(229,'CMASM-DSAU.2','DSAU.2','Seção Odontológica','encarregado_secao','APA','militar',227);
