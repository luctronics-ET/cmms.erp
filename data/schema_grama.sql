-- ============================================
-- GRAMA — Schema de Controle Vegetal
-- Portado de xGrama/controle-vegetal/database/schema.sql
-- Aplicado aditivamente via executescript no startup do xCore
-- ============================================

-- ÁREAS DE SERVIÇO (vegetação)
CREATE TABLE IF NOT EXISTS grama_areas (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  descricao TEXT,
  tipo TEXT CHECK (tipo IN ('jardim','horta','bosque','canteiro','area_recreativa')) NOT NULL,
  area_m2 REAL NOT NULL,
  localizacao_gps TEXT,
  coords_json TEXT,
  flora TEXT CHECK (flora IN ('gramado','capim_colonial','mata_fechada')),
  inclinacao TEXT CHECK (inclinacao IN ('plano','moderado','acentuado')),
  limpeza TEXT CHECK (limpeza IN ('limpa','media','densa')),
  maquinas_compativeis TEXT,
  grupo_nome TEXT,
  visivel INTEGER DEFAULT 1,
  cor_hex TEXT,
  opacidade REAL DEFAULT 0.24,
  ativa INTEGER DEFAULT 1,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- MÁQUINAS E EQUIPAMENTOS DE VEGETAÇÃO
CREATE TABLE IF NOT EXISTS grama_maquinas (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  modelo TEXT NOT NULL,
  tipo TEXT CHECK (tipo IN ('cortador_grama','roçadeira','motosserra','soprador','altra')) NOT NULL,
  numero_serie TEXT UNIQUE,
  fabricante TEXT,
  ano_fabricacao INTEGER,
  status TEXT CHECK (status IN ('operacional','em_manutencao','inativo','aposentada')) DEFAULT 'operacional',
  localizacao_gps TEXT,
  combustivel_tipo TEXT,
  combustivel_capacidade REAL,
  combustivel_atual REAL DEFAULT 0,
  horas_uso REAL DEFAULT 0,
  km_uso REAL,
  valor_aquisicao REAL,
  data_aquisicao DATE,
  observacoes TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- PROCEDIMENTOS OPERACIONAIS PADRÃO (POP)
CREATE TABLE IF NOT EXISTS grama_manutencoes_pop (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  descricao TEXT,
  tipo_maquina TEXT NOT NULL,
  frequencia_horas INTEGER,
  frequencia_dias INTEGER,
  tempo_estimado_minutos INTEGER,
  materiais_necessarios TEXT,
  procedimento TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- OPERAÇÕES DE MANUTENÇÃO
CREATE TABLE IF NOT EXISTS grama_operacoes_manutencao (
  id TEXT PRIMARY KEY,
  maquina_id TEXT NOT NULL,
  tipo TEXT CHECK (tipo IN ('preventiva','corretiva','emergencial')) DEFAULT 'preventiva',
  pop_id TEXT,
  usuario_id TEXT,
  descricao TEXT,
  status TEXT CHECK (status IN ('agendada','em_progresso','concluida','cancelada')) DEFAULT 'agendada',
  data_agendada DATE NOT NULL,
  data_inicio DATETIME,
  data_conclusao DATETIME,
  horas_utilizadas REAL,
  combustivel_utilizado REAL,
  materiais_utilizados TEXT,
  custo_estimado REAL,
  custo_real REAL,
  observacoes TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (maquina_id) REFERENCES grama_maquinas(id),
  FOREIGN KEY (pop_id) REFERENCES grama_manutencoes_pop(id)
);

-- OPERAÇÕES DE SERVIÇO (uso de máquina em área)
CREATE TABLE IF NOT EXISTS grama_operacoes_servico (
  id TEXT PRIMARY KEY,
  maquina_id TEXT NOT NULL,
  area_id TEXT NOT NULL,
  usuario_id TEXT,
  tipo_servico TEXT CHECK (tipo_servico IN ('corte_grama','poda_arvore','corte_localizado','limpeza')) NOT NULL,
  status TEXT CHECK (status IN ('agendado','em_progresso','concluido','cancelado')) DEFAULT 'agendado',
  data_agendada DATE NOT NULL,
  data_inicio DATETIME,
  data_conclusao DATETIME,
  horas_utilizadas REAL,
  combustivel_utilizado REAL,
  observacoes TEXT,
  localizacao_gps_inicio TEXT,
  localizacao_gps_fim TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (maquina_id) REFERENCES grama_maquinas(id),
  FOREIGN KEY (area_id) REFERENCES grama_areas(id)
);

-- COMBUSTÍVEL — Histórico de abastecimento
CREATE TABLE IF NOT EXISTS grama_combustivel_log (
  id TEXT PRIMARY KEY,
  maquina_id TEXT NOT NULL,
  data DATETIME DEFAULT CURRENT_TIMESTAMP,
  tipo TEXT NOT NULL,
  quantidade_adicionada REAL NOT NULL,
  custo REAL,
  usuario_id TEXT,
  observacoes TEXT,
  FOREIGN KEY (maquina_id) REFERENCES grama_maquinas(id)
);

-- PLANEJAMENTO DE ROTINAS POR ÁREA (estilo PMOC Vegetal)
CREATE TABLE IF NOT EXISTS grama_planos_area (
  id TEXT PRIMARY KEY,
  area_id TEXT NOT NULL,
  nome TEXT NOT NULL,
  periodicidade_dias INTEGER NOT NULL,
  prioridade TEXT CHECK (prioridade IN ('baixa','media','alta','critica')) DEFAULT 'media',
  servicos_json TEXT NOT NULL,
  materiais_json TEXT,
  custo_estimado_ciclo REAL DEFAULT 0,
  custo_estimado_mensal REAL DEFAULT 0,
  ativo INTEGER DEFAULT 1,
  observacoes TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (area_id) REFERENCES grama_areas(id)
);

-- HISTÓRICO DE EXECUÇÕES DOS PLANOS
CREATE TABLE IF NOT EXISTS grama_planos_execucoes (
  id TEXT PRIMARY KEY,
  plano_id TEXT NOT NULL,
  area_id TEXT NOT NULL,
  os_id TEXT,
  usuario_id TEXT,
  materiais_json TEXT,
  custo_real_materiais REAL DEFAULT 0,
  data_execucao DATETIME DEFAULT CURRENT_TIMESTAMP,
  observacoes TEXT,
  FOREIGN KEY (plano_id) REFERENCES grama_planos_area(id),
  FOREIGN KEY (area_id) REFERENCES grama_areas(id)
);

-- KANBAN — Board de tarefas de vegetação
CREATE TABLE IF NOT EXISTS grama_kanban_tarefas (
  id TEXT PRIMARY KEY,
  titulo TEXT NOT NULL,
  descricao TEXT,
  coluna TEXT CHECK (coluna IN ('backlog','agendado','em_progresso','concluido','bloqueado')) DEFAULT 'backlog',
  prioridade TEXT CHECK (prioridade IN ('baixa','media','alta','critica')) DEFAULT 'media',
  usuario_id TEXT,
  maquina_id TEXT,
  area_id TEXT,
  data_vencimento DATE,
  ordem_display INTEGER DEFAULT 0,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (maquina_id) REFERENCES grama_maquinas(id),
  FOREIGN KEY (area_id) REFERENCES grama_areas(id)
);

-- CALENDÁRIO — Eventos agendados
CREATE TABLE IF NOT EXISTS grama_calendario_eventos (
  id TEXT PRIMARY KEY,
  titulo TEXT NOT NULL,
  descricao TEXT,
  tipo TEXT CHECK (tipo IN ('manutencao','servico','reuniao','outro')) NOT NULL,
  data_inicio DATETIME NOT NULL,
  data_fim DATETIME,
  local TEXT,
  usuarios_envolvidos TEXT,
  maquina_id TEXT,
  area_id TEXT,
  data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (maquina_id) REFERENCES grama_maquinas(id),
  FOREIGN KEY (area_id) REFERENCES grama_areas(id)
);

-- ÍNDICES
CREATE INDEX IF NOT EXISTS idx_grama_maquinas_status ON grama_maquinas(status);
CREATE INDEX IF NOT EXISTS idx_grama_op_manut_status ON grama_operacoes_manutencao(status);
CREATE INDEX IF NOT EXISTS idx_grama_op_manut_data ON grama_operacoes_manutencao(data_agendada);
CREATE INDEX IF NOT EXISTS idx_grama_op_serv_status ON grama_operacoes_servico(status);
CREATE INDEX IF NOT EXISTS idx_grama_op_serv_data ON grama_operacoes_servico(data_agendada);
CREATE INDEX IF NOT EXISTS idx_grama_kanban_coluna ON grama_kanban_tarefas(coluna);
CREATE INDEX IF NOT EXISTS idx_grama_cal_data ON grama_calendario_eventos(data_inicio);
CREATE INDEX IF NOT EXISTS idx_grama_planos_area ON grama_planos_area(area_id, ativo);
CREATE INDEX IF NOT EXISTS idx_grama_exec_plano ON grama_planos_execucoes(plano_id, data_execucao);
