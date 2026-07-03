from __future__ import annotations

import csv
import io
import os
import secrets
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi import Request, Response
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError

from .db_core import CoreDB
from .catalogo import router as catalogo_router
from .grama import router as grama_router, init_grama
from .sync import router as sync_router
from .manutencao import router as manutencao_router
from .docs import router as docs_router

# ── Config ────────────────────────────────────────────────────────────────────
from tools.telegram_spike import _load_dotenv as _load_env  # noqa: E402
_load_env()  # carrega .env (TELEGRAM_BOT_TOKEN, DB_PATH, etc.) antes dos os.getenv abaixo
DB_PATH   = os.getenv("DB_PATH",   os.path.join(os.path.dirname(__file__), "..", "data", "core.db"))
TOKEN_TTL = int(os.getenv("TOKEN_TTL_HOURS", "8"))
XPREDIAL_URL   = os.getenv("XPREDIAL_URL",   "http://127.0.0.1:8002").rstrip("/")
XAGUADA_URL    = os.getenv("XAGUADA_URL",    "http://127.0.0.1:8001").rstrip("/")
XPAIOL_URL     = os.getenv("XPAIOL_URL",     "http://127.0.0.1:8003").rstrip("/")
XCALIBRACAO_URL = os.getenv("XCALIBRACAO_URL", "http://127.0.0.1:8004").rstrip("/")

_SATELLITES = [
    {"id": "xpredial",   "name": "xPredial",   "url": XPREDIAL_URL,   "port": 8002},
    {"id": "xaguada",    "name": "xAguada",     "url": XAGUADA_URL,    "port": 8001},
    {"id": "xpaiol",     "name": "xPaiol",      "url": XPAIOL_URL,     "port": 8003},
    {"id": "xcalibracao","name": "xCalibracao", "url": XCALIBRACAO_URL,"port": 8004},
]

_COLAB_SEED_EVENTS = [
    {
        "id": "ev1",
        "title": "Treinamento NR-10",
        "type": "training",
        "event_date": "2026-06-03",
        "location": "Auditorio Principal",
        "attendees": 25,
        "description": "Reciclagem obrigatoria para equipes tecnicas.",
    },
    {
        "id": "ev2",
        "title": "Reuniao de Alinhamento Operacional",
        "type": "meeting",
        "event_date": "2026-06-05",
        "location": "Sala CMASM-01",
        "attendees": 14,
        "description": "Alinhamento semanal de metas entre divisoes.",
    },
    {
        "id": "ev3",
        "title": "Palestra de Seguranca da Informacao",
        "type": "company_event",
        "event_date": "2026-06-10",
        "location": "Auditorio Principal",
        "attendees": 80,
        "description": "Boas praticas e requisitos de protecao de dados.",
    },
    {
        "id": "ev4",
        "title": "Escala Especial de Fim de Semana",
        "type": "shift",
        "event_date": "2026-06-14",
        "location": "Base Operacional",
        "attendees": 12,
        "description": "Cobertura operacional programada.",
    },
]

_COLAB_SEED_POLICIES = [
    {
        "id": "po1",
        "title": "Politica de Trabalho Presencial",
        "category": "hr",
        "version": "2.1",
        "description": "Define jornadas, controle de presenca e regras de justificativa para ausencias.",
        "owner": "Divisao de Pessoal",
        "created_date": "2026-02-02",
        "updated_date": "2026-04-10",
    },
    {
        "id": "po2",
        "title": "Politica de Seguranca da Informacao",
        "category": "security",
        "version": "3.0",
        "description": "Classificacao da informacao, uso de credenciais e resposta a incidentes ciberneticos.",
        "owner": "Secao de Seguranca",
        "created_date": "2025-11-01",
        "updated_date": "2026-03-25",
    },
    {
        "id": "po3",
        "title": "Politica de Uso de Recursos de TI",
        "category": "it",
        "version": "1.4",
        "description": "Uso aceitavel de equipamentos, redes e servicos corporativos.",
        "owner": "Divisao de Comunicacoes",
        "created_date": "2026-01-18",
        "updated_date": "2026-05-02",
    },
]

_COLAB_SEED_EXECUTIVES = [
    {
        "id": "ex1",
        "full_name": "Ana Valeria Greco de Sousa",
        "position": "Diretora",
        "department": "Direcao",
        "email": "ana.valeria@marinha.mil.br",
        "phone": "(21) 99999-0101",
        "office_location": "Gabinete CMASM-01",
        "years_with_company": 11,
        "bio": "Responsavel pela direcao estrategica e governanca do CMASM.",
    },
    {
        "id": "ex2",
        "full_name": "Luciana Santana Pires",
        "position": "Vice-Diretora",
        "department": "Vice-Direcao",
        "email": "luciana.pires@marinha.mil.br",
        "phone": "(21) 99999-0202",
        "office_location": "Gabinete CMASM-02",
        "years_with_company": 9,
        "bio": "Coordena integracao operacional entre departamentos e projetos criticos.",
    },
    {
        "id": "ex3",
        "full_name": "Marcos Paulo Ferreira",
        "position": "Chefe de Infraestrutura",
        "department": "Infraestrutura",
        "email": "marcos.ferreira@marinha.mil.br",
        "phone": "(21) 99999-0303",
        "office_location": "CMASM-10",
        "years_with_company": 8,
        "bio": "Lidera servicos de manutencao, logistica e instalacoes.",
    },
]

_COLAB_SEED_ANNOUNCEMENTS = [
    {
        "id": "an1",
        "title": "Atualizacao de Procedimentos de Acesso",
        "content": "A partir de 03/06, todos os acessos administrativos exigirao autenticacao multifator no primeiro login do dia.",
        "priority": "high",
        "author": "Secao de Seguranca",
        "created_date": "2026-05-28T08:30:00Z",
    },
    {
        "id": "an2",
        "title": "Revisao do Cronograma de Treinamentos",
        "content": "O calendario do 2o semestre foi atualizado com novas turmas para NR-10 e combate a incendio.",
        "priority": "medium",
        "author": "Divisao de Pessoal",
        "created_date": "2026-05-25T13:10:00Z",
    },
    {
        "id": "an3",
        "title": "Manutencao Preventiva da Rede",
        "content": "Janela de manutencao prevista para sabado, das 22h as 23h30, com indisponibilidade intermitente.",
        "priority": "low",
        "author": "Divisao de Comunicacoes",
        "created_date": "2026-05-22T10:00:00Z",
    },
]

_MANUT_TIPOS_PLANOS = {
    "FS220": {
        "nome": "Rocadeira STIHL FS 220",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 25, "n": "Limpar filtro de ar", "its": ["Filtro de ar FS220"]},
            {"id": "p03", "iv": 25, "n": "Lubrificar caixa de transmissao", "its": ["Graxa STIHL engrenagem"]},
            {"id": "p04", "iv": 25, "n": "Inspecionar/trocar nylon ou lamina", "its": ["Carretel nylon", "Lamina 2 pontas"]},
            {"id": "p05", "iv": 100, "n": "Trocar vela de ignicao", "its": ["Vela NGK BPMR7A"]},
            {"id": "p06", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p07", "iv": 300, "n": "Verificar/trocar mangueira combustivel", "its": ["Mangueira combustivel"]},
            {"id": "p08", "iv": 500, "n": "Revisao geral do motor", "its": ["Kit juntas", "Kit pistao/aneis"]},
        ],
    },
    "GAR": {
        "nome": "Cortador Garthen PRO-3500S",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 50, "n": "Trocar oleo do motor 4T", "its": ["Oleo SAE 30 / 10W-30"]},
            {"id": "p03", "iv": 50, "n": "Limpar filtro de ar", "its": ["Filtro de ar Garthen"]},
            {"id": "p04", "iv": 100, "n": "Trocar vela de ignicao", "its": ["Vela NGK Cg420"]},
            {"id": "p05", "iv": 100, "n": "Trocar filtro de oleo", "its": ["Filtro de oleo"]},
            {"id": "p06", "iv": 100, "n": "Inspecionar laminas e rodas", "its": ["Lamina 2 pontas", "Roda dianteira", "Roda traseira"]},
            {"id": "p07", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p08", "iv": 500, "n": "Revisao geral", "its": ["Kit juntas motor"]},
        ],
    },
    "MS650": {
        "nome": "Motosserra STIHL MS650",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral", "its": []},
            {"id": "p02", "iv": 25, "n": "Limpar filtro de ar", "its": ["Filtro de ar MS650"]},
            {"id": "p03", "iv": 25, "n": "Lubrificar corrente (oleo corrente)", "its": ["Oleo corrente motosserra"]},
            {"id": "p04", "iv": 50, "n": "Afiar ou trocar corrente", "its": ["Corrente 36 RM 63cm", "Lima afiar"]},
            {"id": "p05", "iv": 100, "n": "Trocar vela de ignicao", "its": ["Vela NGK MS650"]},
            {"id": "p06", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p07", "iv": 500, "n": "Revisao geral do motor", "its": ["Kit juntas", "Carburador"]},
        ],
    },
    "COY": {
        "nome": "Tobata Coyote CT151",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 50, "n": "Trocar oleo do motor", "its": ["Oleo SAE 30"]},
            {"id": "p03", "iv": 50, "n": "Limpar filtro de ar", "its": ["Filtro de ar Coyote"]},
            {"id": "p04", "iv": 100, "n": "Trocar vela + filtro de oleo", "its": ["Vela de ignicao", "Filtro de oleo"]},
            {"id": "p05", "iv": 100, "n": "Inspecionar correias", "its": ["Correia principal Tobata"]},
            {"id": "p06", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p07", "iv": 200, "n": "Trocar correia principal", "its": ["Correia principal Tobata"]},
            {"id": "p08", "iv": 500, "n": "Revisao geral", "its": ["Kit carburador", "Filtro hidraulico"]},
        ],
    },
    "LGT": {
        "nome": "Husqvarna LGT2654",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 50, "n": "Trocar oleo + filtro de oleo", "its": ["Oleo SAE 30", "Filtro de oleo LGT"]},
            {"id": "p03", "iv": 50, "n": "Limpar filtro de ar", "its": ["Filtro de ar LGT2654"]},
            {"id": "p04", "iv": 100, "n": "Trocar velas (2 cilindros)", "its": ["Vela de ignicao x2"]},
            {"id": "p05", "iv": 150, "n": "Trocar correia do deck", "its": ["Correia deck LGT2654"]},
            {"id": "p06", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p07", "iv": 250, "n": "Trocar correia de transmissao", "its": ["Correia transmissao LGT2654"]},
            {"id": "p08", "iv": 500, "n": "Revisao geral", "its": ["Kit carburador", "Mola governador"]},
        ],
    },
    "TS114": {
        "nome": "Husqvarna TS114",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 25, "n": "Limpar filtro de ar", "its": ["Filtro de ar LTH1738"]},
            {"id": "p03", "iv": 25, "n": "Lubrificar pontos de graxeiro (4 pts.)", "its": ["Graxa NLGI 2"]},
            {"id": "p04", "iv": 25, "n": "Inspecionar/afiar ou trocar lamina", "its": ["Lamina de corte Husqvarna TS114"]},
            {"id": "p05", "iv": 50, "n": "Trocar oleo do motor (~0,6 L)", "its": ["Oleo SAE 30"]},
            {"id": "p06", "iv": 50, "n": "Trocar filtro de ar", "its": ["Filtro de ar LTH1738"]},
            {"id": "p07", "iv": 100, "n": "Trocar vela de ignicao", "its": ["Vela HQT-9"]},
            {"id": "p08", "iv": 100, "n": "Inspecionar correias (visual)", "its": []},
            {"id": "p09", "iv": 100, "n": "Revisao geral + aperto de torque", "its": []},
            {"id": "p10", "iv": 150, "n": "Trocar filtro de combustivel", "its": ["Filtro combustivel"]},
            {"id": "p11", "iv": 200, "n": "Trocar correia de deck", "its": ["Correia A-78"]},
            {"id": "p12", "iv": 250, "n": "Trocar correia de transmissao", "its": ["Correia A-78"]},
            {"id": "p13", "iv": 300, "n": "Kit reparo carburador (membranas)", "its": ["Kit carburador HS452AE"]},
            {"id": "p14", "iv": 500, "n": "Trocar rolamentos de roda", "its": ["Rolamento 6202-2RS"]},
        ],
    },
    "SOL": {
        "nome": "Trator Agricola Solis 90",
        "categoria": "maquinas_corte",
        "plano": [
            {"id": "p01", "iv": 8, "n": "Inspecao geral + nivel de oleo", "its": []},
            {"id": "p02", "iv": 50, "n": "Trocar oleo + filtro de oleo (diesel)", "its": ["Oleo 15W-40 diesel", "Filtro oleo Solis"]},
            {"id": "p03", "iv": 50, "n": "Limpar filtro de ar primario", "its": ["Filtro ar primario Solis"]},
            {"id": "p04", "iv": 150, "n": "Trocar filtro de combustivel diesel", "its": ["Filtro combustivel diesel"]},
            {"id": "p05", "iv": 250, "n": "Trocar filtro hidraulico", "its": ["Filtro hidraulico Solis"]},
            {"id": "p06", "iv": 250, "n": "Trocar filtro de ar completo", "its": ["Filtro ar primario Solis", "Filtro ar safety"]},
            {"id": "p07", "iv": 500, "n": "Trocar correia alternador", "its": ["Correia alternador Solis"]},
            {"id": "p08", "iv": 500, "n": "Trocar filtro de transmissao", "its": ["Filtro transmissao Solis"]},
            {"id": "p09", "iv": 1000, "n": "Revisao geral motor diesel", "its": ["Kit juntas cabecote", "Glow plugs x4"]},
        ],
    },
    # ── Fonoclama (sistema de aviso sonoro) — legado de xFonoclama/fonoclama.html ──
    "AMPLIFICADOR": {
        "nome": "Amplificador", "categoria": "fonoclama",
        "plano": [
            {"id": "am01", "iv": 180, "n": "Inspecao de ventilacao e conexoes", "its": ["Conector P10", "Terminal de audio"]},
            {"id": "am02", "iv": 720, "n": "Teste de potencia e distorcao", "its": ["Fusivel", "Cooler 12V"]},
        ],
    },
    "CONSOLE": {
        "nome": "Console / microfone", "categoria": "fonoclama",
        "plano": [
            {"id": "co01", "iv": 180, "n": "Teste funcional de acionamento", "its": ["Cabo XLR", "Conector XLR"]},
            {"id": "co02", "iv": 720, "n": "Revisao de cabeamento e contatos", "its": ["Limpador de contato"]},
        ],
    },
    "ALTO_FALANTE": {
        "nome": "Alto-falante / corneta", "categoria": "fonoclama",
        "plano": [
            {"id": "af01", "iv": 240, "n": "Inspecao de fixacao e resposta sonora", "its": ["Suporte metalico", "Conector de linha"]},
        ],
    },
    "LINHA_70V": {
        "nome": "Linha 70V / distribuicao", "categoria": "fonoclama",
        "plano": [
            {"id": "l701", "iv": 360, "n": "Teste de continuidade e isolacao", "its": ["Cabo 2x1,5mm", "Conector de linha"]},
        ],
    },
    "SIRENE": {
        "nome": "Sirene / aviso sonoro", "categoria": "fonoclama",
        "plano": [
            {"id": "si01", "iv": 180, "n": "Teste de acionamento e intensidade", "its": ["Fusivel", "Rele"]},
        ],
    },
}

app = FastAPI(title="xCore API", version="1.0.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

db = CoreDB(DB_PATH)
app.include_router(grama_router)
app.include_router(sync_router)
app.include_router(catalogo_router)
app.include_router(manutencao_router)
app.include_router(docs_router)

# Serve xCore frontend files (HTMLs, JS, CSS, assets)
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..")
_SHARED_ASSETS_DIR = os.path.join(_FRONTEND_DIR, "assets")
_PMOC_DIR = os.path.join(_FRONTEND_DIR, "pmoc")
app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
app.mount("/assets", StaticFiles(directory=_SHARED_ASSETS_DIR), name="assets")
if os.path.isdir(_PMOC_DIR):
    app.mount("/pmoc", StaticFiles(directory=_PMOC_DIR, html=True), name="pmoc")


@app.middleware("http")
async def _no_cache_html_js(request, call_next):
    """Evita servir HTML/JS velho do cache do browser (fim dos hard-refresh em dev)."""
    resp = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".css")):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


async def _seed_colab_if_empty() -> None:
    checks = {
        "events": await db.fetch_one("SELECT COUNT(*) AS n FROM colab_events"),
        "policies": await db.fetch_one("SELECT COUNT(*) AS n FROM colab_policies"),
        "executives": await db.fetch_one("SELECT COUNT(*) AS n FROM colab_executives"),
        "announcements": await db.fetch_one("SELECT COUNT(*) AS n FROM colab_announcements"),
    }
    if any((checks[k] or {}).get("n", 0) > 0 for k in checks):
        return

    await db.executemany(
        "INSERT INTO colab_events (id, title, type, event_date, location, attendees, description) VALUES (?,?,?,?,?,?,?)",
        [
            (
                item["id"],
                item["title"],
                item["type"],
                item["event_date"],
                item.get("location"),
                item.get("attendees", 0),
                item.get("description"),
            )
            for item in _COLAB_SEED_EVENTS
        ],
    )
    await db.executemany(
        "INSERT INTO colab_policies (id, title, category, version, description, owner, created_date, updated_date) VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                item["id"],
                item["title"],
                item["category"],
                item.get("version"),
                item.get("description"),
                item.get("owner"),
                item.get("created_date"),
                item.get("updated_date"),
            )
            for item in _COLAB_SEED_POLICIES
        ],
    )
    await db.executemany(
        "INSERT INTO colab_executives (id, full_name, position, department, email, phone, office_location, years_with_company, bio, linkedin_url, photo_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                item["id"],
                item["full_name"],
                item["position"],
                item.get("department"),
                item.get("email"),
                item.get("phone"),
                item.get("office_location"),
                item.get("years_with_company", 0),
                item.get("bio"),
                item.get("linkedin_url"),
                item.get("photo_url"),
            )
            for item in _COLAB_SEED_EXECUTIVES
        ],
    )
    await db.executemany(
        "INSERT INTO colab_announcements (id, title, content, priority, author, created_date) VALUES (?,?,?,?,?,?)",
        [
            (
                item["id"],
                item["title"],
                item["content"],
                item.get("priority", "medium"),
                item.get("author"),
                item.get("created_date"),
            )
            for item in _COLAB_SEED_ANNOUNCEMENTS
        ],
    )


def _derive_catalogo_seed() -> tuple[list[tuple], list[tuple]]:
    servicos: list[tuple] = []
    planos: list[tuple] = []
    for tipo_codigo, tipo in _MANUT_TIPOS_PLANOS.items():
        for plano in tipo["plano"]:
            servico_id = f"svc-plano-{tipo_codigo.lower()}-{plano['id']}"
            servicos.append(
                (
                    servico_id,
                    f"{tipo_codigo}_{plano['id'].upper()}",
                    plano["n"],
                    f"Plano preventivo por horimetro para {tipo['nome']}.",
                    "central",
                    1,
                    None,
                    max(30, 20 + len(plano.get("its", [])) * 15),
                    None,
                    '{"categorias":["%s"],"tipos":["%s"]}' % (tipo["categoria"], tipo_codigo),
                    "manutencao",
                )
            )
            planos.append(
                (
                    f"plan-{tipo_codigo.lower()}-{plano['id']}",
                    servico_id,
                    None,
                    None,
                    tipo_codigo,
                    '{"tipo":"por_uso","valor":%s,"unidade":"h"}' % plano["iv"],
                    None,
                    None,
                    None,
                    None,
                    "manutencao",
                    f"Plano derivado automaticamente de {tipo['nome']}.",
                    "manutencao",
                )
            )
    return servicos, planos


async def _seed_catalogo_manut_if_empty() -> None:
    servicos, _planos_legado = _derive_catalogo_seed()  # planos_manutencao APOSENTADO (catalogo_planos é a fonte)
    await db.executemany(
        "INSERT OR IGNORE INTO catalogo_servicos (id, codigo, nome, descricao, escopo, versao, pop_doc_id, tempo_estimado_min, servico_pai_id, aplicavel_a, criado_por_modulo) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        servicos,
    )

    await db.execute(
        "DELETE FROM catalogo_servico_materiais WHERE servico_id LIKE 'svc-plano-%'"
    )

    materiais_rows = []
    for tipo_codigo, tipo in _MANUT_TIPOS_PLANOS.items():
        for plano in tipo["plano"]:
            servico_id = f"svc-plano-{tipo_codigo.lower()}-{plano['id']}"
            for material in plano.get("its", []):
                materiais_rows.append((
                    servico_id,
                    None,
                    material,
                    1,
                    "un",
                    1,
                    None,
                ))
    if materiais_rows:
        await db.executemany(
            "INSERT OR IGNORE INTO catalogo_servico_materiais (servico_id, material_id, nome_livre, qtd, unidade, obrigatorio, obs) VALUES (?,?,?,?,?,?,?)",
            materiais_rows,
        )
    # planos_manutencao NÃO é mais seedado — catalogo_planos é a fonte única.


async def _migrate_catalogo_planos_cols() -> None:
    """Migração aditiva: colunas de disparo no plano nomeado (PRAGMA antes de ALTER)."""
    pcols = {c["name"] for c in await db.fetch_all("PRAGMA table_info(catalogo_planos)")}
    if "frequencia" not in pcols:
        await db.execute("ALTER TABLE catalogo_planos ADD COLUMN frequencia TEXT")
    if "aplicavel_tipos" not in pcols:
        await db.execute("ALTER TABLE catalogo_planos ADD COLUMN aplicavel_tipos TEXT")
    icols = {c["name"] for c in await db.fetch_all("PRAGMA table_info(catalogo_plano_itens)")}
    if "frequencia" not in icols:
        await db.execute("ALTER TABLE catalogo_plano_itens ADD COLUMN frequencia TEXT")
    # Disparo default dos planos de climatização (ATA2 não trouxe intervalo) = 90 dias.
    # Preserva o comportamento do antigo planos_manutencao no sync do PMOC.
    await db.execute(
        "UPDATE catalogo_planos SET frequencia = ? "
        "WHERE categoria = 'climatizacao' AND (frequencia IS NULL OR frequencia = '')",
        ('{"tipo": "por_tempo", "valor": 90, "unidade": "dias"}',),
    )


async def _seed_grama_if_empty() -> None:
    """Seed inicial de Controle Vegetal (máquinas + áreas) se as tabelas estiverem
    vazias. Conjunto modesto e editável — base p/ o módulo não nascer vazio."""
    row = await db.fetch_one("SELECT COUNT(*) AS n FROM grama_maquinas")
    if not row or row["n"] == 0:
        maquinas = [
            ("gmaq-fs220-1", "Roçadeira FS220 #1", "FS220", "roçadeira", "Stihl", 142.5),
            ("gmaq-fs220-2", "Roçadeira FS220 #2", "FS220", "roçadeira", "Stihl", 198.2),
            ("gmaq-fs220-3", "Roçadeira FS220 #3", "FS220", "roçadeira", "Stihl", 76.0),
            ("gmaq-fs220-4", "Roçadeira FS220 #4", "FS220", "roçadeira", "Stihl", 33.5),
            ("gmaq-fs220-5", "Roçadeira FS220 #5", "FS220", "roçadeira", "Stihl", 12.0),
            ("gmaq-gar-1", "Cortador GAR #1", "GAR-53", "cortador_grama", "Garthen", 85.4),
            ("gmaq-gar-2", "Cortador GAR #2", "GAR-53", "cortador_grama", "Garthen", 60.1),
            ("gmaq-gar-3", "Cortador GAR #3", "GAR-53", "cortador_grama", "Garthen", 25.0),
            ("gmaq-ms650", "Motosserra MS650", "MS650", "motosserra", "Stihl", 42.0),
            ("gmaq-sopra-1", "Soprador BR600", "BR600", "soprador", "Stihl", 18.0),
            ("gmaq-ts114-1", "Cortadora concreto TS114", "TS114", "altra", "Stihl", 30.0),
            ("gmaq-sol", "Trator de corte SOL", "SOL-1200", "altra", "Solaris", 220.1),
        ]
        for mid, nome, modelo, tipo, fab, horas in maquinas:
            await db.execute(
                "INSERT OR IGNORE INTO grama_maquinas (id, nome, modelo, tipo, fabricante, horas_uso, status) "
                "VALUES (?,?,?,?,?,?, 'operacional')",
                (mid, nome, modelo, tipo, fab, horas),
            )
    row = await db.fetch_one("SELECT COUNT(*) AS n FROM grama_areas")
    if not row or row["n"] == 0:
        areas = [
            ("garea-cais-norte", "Cais Norte", "jardim", 1200.0, "gramado", "plano"),
            ("garea-campo-honra", "Campo de Honra", "jardim", 3500.0, "gramado", "plano"),
            ("garea-entrada", "Entrada Principal", "canteiro", 800.0, "gramado", "moderado"),
            ("garea-estac", "Estacionamentos", "area_recreativa", 2400.0, "gramado", "plano"),
            ("garea-desportivo", "Campo Desportivo", "area_recreativa", 6000.0, "gramado", "plano"),
            ("garea-bosque", "Bosque Interno", "bosque", 4200.0, "mata_fechada", "acentuado"),
        ]
        for aid, nome, tipo, m2, flora, inclin in areas:
            await db.execute(
                "INSERT OR IGNORE INTO grama_areas (id, nome, tipo, area_m2, flora, inclinacao, limpeza, ativa) "
                "VALUES (?,?,?,?,?,?, 'media', 1)",
                (aid, nome, tipo, m2, flora, inclin),
            )


async def _migrate_modulo_transportes_categorias() -> None:
    """Corrige registro pmoc_transportes: categorias reais dos ativos são
    'viaturas'/'embarcacoes' (não 'frota_terrestre'/'frota_naval'). Sem essa
    correção o manifest do PMOC transportes retorna 0 ativos/serviços."""
    await db.execute(
        "UPDATE modulos_registrados SET categorias_atend = ? "
        "WHERE nome = 'pmoc_transportes' AND categorias_atend = ?",
        ('["viaturas","embarcacoes"]', '["frota_terrestre","frota_naval"]'),
    )


async def _migrate_catalogo_servicos_taxon() -> None:
    """Migração aditiva: taxonomia de serviço (categoria/subcategoria) em
    catalogo_servicos + backfill a partir de aplicavel_a (categoria de ativo legada)."""
    import json
    cols = {c["name"] for c in await db.fetch_all("PRAGMA table_info(catalogo_servicos)")}
    if "categoria" not in cols:
        await db.execute("ALTER TABLE catalogo_servicos ADD COLUMN categoria TEXT")
    if "subcategoria" not in cols:
        await db.execute("ALTER TABLE catalogo_servicos ADD COLUMN subcategoria TEXT")
    _MAP = {
        "climatizacao": ("MANUTENCAO", "REFRIGERACAO"), "eletrica": ("MANUTENCAO", "ELETRICA"),
        "predial": ("MANUTENCAO", "EDIFICACAO"), "instrumentos": ("MANUTENCAO", "ELETRONICA"),
        "frota_terrestre": ("TRANSPORTE", ""), "frota_naval": ("TRANSPORTE", ""),
        "viaturas": ("TRANSPORTE", ""), "embarcacoes": ("TRANSPORTE", ""),
        "maquinas_corte": ("CONTROLE VEGETAL", ""),
    }
    rows = await db.fetch_all(
        "SELECT id, aplicavel_a FROM catalogo_servicos WHERE categoria IS NULL OR categoria = ''"
    )
    for r in rows:
        try:
            cats = (json.loads(r["aplicavel_a"] or "{}").get("categorias")) or []
        except (ValueError, TypeError):
            cats = []
        m = _MAP.get(cats[0]) if cats else None
        if not m:
            continue
        await db.execute(
            "UPDATE catalogo_servicos SET categoria = ?, subcategoria = ? WHERE id = ?",
            (m[0], m[1], r["id"]),
        )


async def _seed_catalogo_planos_from_tipos() -> None:
    """Migra os planos hardcoded (_MANUT_TIPOS_PLANOS: corte + fonoclama) para o
    modelo nomeado catalogo_planos + catalogo_plano_itens. Disparo por serviço
    (frequencia no item). Idempotente. Climatização já vem do import ATA2."""
    import json
    for tipo_codigo, tipo in _MANUT_TIPOS_PLANOS.items():
        if tipo["categoria"] == "maquinas_corte":
            cat = "maquinas_corte"
        elif tipo["categoria"] == "fonoclama":
            cat = "fonoclama"
        else:
            continue  # climatização tem seu próprio import
        plano_id = f"plano-{tipo_codigo.lower()}"
        await db.execute(
            "INSERT OR IGNORE INTO catalogo_planos (id, codigo, nome, categoria, tipo_codigo, aplicavel_tipos, fonte, ativo) "
            "VALUES (?,?,?,?,?,?,?,1)",
            (plano_id, tipo_codigo, f"Plano {tipo['nome']}", cat, tipo_codigo,
             json.dumps([tipo_codigo]), "Migrado de _MANUT_TIPOS_PLANOS"),
        )
        for seq, step in enumerate(tipo["plano"]):
            servico_id = f"svc-plano-{tipo_codigo.lower()}-{step['id']}"
            freq = json.dumps({"tipo": "por_uso", "valor": step["iv"], "unidade": "h"})
            await db.execute(
                "INSERT OR IGNORE INTO catalogo_plano_itens (plano_id, servico_id, seq, classe, frequencia) "
                "VALUES (?,?,?, 'prev', ?)",
                (plano_id, servico_id, seq, freq),
            )


# Planos padrão de transportes (km/h) — fonte: Regras de Negócio e Fluxos.md
_TRANSP_PLANOS = {
    "VTR_PICKUP": {"nome": "Viatura de passeio/pickup", "cat": "viaturas", "un": "km", "plano": [
        {"id": "p01", "iv": 5000,  "n": "Troca de óleo + filtro",      "its": ["Óleo 5W-30 sintético 4L", "Filtro de óleo"]},
        {"id": "p02", "iv": 10000, "n": "Inspeção/troca de freios",    "its": ["Pastilhas de freio"]},
        {"id": "p03", "iv": 10000, "n": "Rodízio de pneus",            "its": []},
        {"id": "p04", "iv": 15000, "n": "Troca filtro de ar e combustível", "its": ["Filtro de ar", "Filtro de combustível"]},
        {"id": "p05", "iv": 40000, "n": "Revisão geral + correias",    "its": ["Correia dentada", "Kit tensor"]},
    ]},
    "VTR_CARGA": {"nome": "Viatura de carga/caminhão", "cat": "viaturas", "un": "km", "plano": [
        {"id": "p01", "iv": 10000, "n": "Troca óleo + filtro (diesel)", "its": ["Óleo 15W-40 diesel", "Filtro de óleo"]},
        {"id": "p02", "iv": 20000, "n": "Inspeção freios + lonas",      "its": ["Lona/pastilha de freio"]},
        {"id": "p03", "iv": 20000, "n": "Troca filtro combustível diesel", "its": ["Filtro combustível diesel"]},
        {"id": "p04", "iv": 50000, "n": "Revisão geral",                "its": ["Kit revisão pesada"]},
    ]},
    "EMB_LANCHA": {"nome": "Lancha / embarcação", "cat": "embarcacoes", "un": "h", "plano": [
        {"id": "p01", "iv": 50,  "n": "Troca de óleo do motor de popa", "its": ["Óleo náutico", "Filtro de óleo"]},
        {"id": "p02", "iv": 100, "n": "Limpeza/inspeção de casco",      "its": []},
        {"id": "p03", "iv": 200, "n": "Troca do rotor da bomba d'água", "its": ["Rotor/impeller"]},
        {"id": "p04", "iv": 300, "n": "Inspeção hélice + ânodos",       "its": ["Ânodo de zinco"]},
        {"id": "p05", "iv": 500, "n": "Revisão geral do motor",         "its": ["Kit junta", "Velas náuticas"]},
    ]},
}


async def _seed_planos_transportes_if_empty() -> None:
    """Cria serviços + materiais + planos nomeados (km/h) para viaturas e
    embarcações. Idempotente (INSERT OR IGNORE)."""
    import json
    for tipo_codigo, t in _TRANSP_PLANOS.items():
        plano_id = f"plano-{tipo_codigo.lower()}"
        await db.execute(
            "INSERT OR IGNORE INTO catalogo_planos (id, codigo, nome, categoria, tipo_codigo, aplicavel_tipos, fonte, ativo) "
            "VALUES (?,?,?,?,?,?,?,1)",
            (plano_id, tipo_codigo, f"Plano {t['nome']}", t["cat"], tipo_codigo,
             json.dumps([tipo_codigo]), "Regras de Negócio e Fluxos.md"),
        )
        for seq, step in enumerate(t["plano"]):
            servico_id = f"svc-transp-{tipo_codigo.lower()}-{step['id']}"
            await db.execute(
                "INSERT OR IGNORE INTO catalogo_servicos (id, codigo, nome, descricao, escopo, versao, aplicavel_a, criado_por_modulo) "
                "VALUES (?,?,?,?, 'central', 1, ?, 'manutencao')",
                (servico_id, f"{tipo_codigo}_{step['id'].upper()}", step["n"],
                 f"Serviço preventivo de {t['nome']}.",
                 json.dumps({"categorias": [t["cat"]], "tipos": [tipo_codigo]})),
            )
            for mat in step["its"]:
                await db.execute(
                    "INSERT OR IGNORE INTO catalogo_servico_materiais (servico_id, material_id, nome_livre, qtd, unidade, obrigatorio) "
                    "VALUES (?, NULL, ?, 1, 'un', 1)",
                    (servico_id, mat),
                )
            freq = json.dumps({"tipo": "por_uso", "valor": step["iv"], "unidade": t["un"]})
            await db.execute(
                "INSERT OR IGNORE INTO catalogo_plano_itens (plano_id, servico_id, seq, classe, frequencia) "
                "VALUES (?,?,?, 'prev', ?)",
                (plano_id, servico_id, seq, freq),
            )


@app.get("/")
async def root():
    return FileResponse(os.path.join(_FRONTEND_DIR, "cmasm_erp.html"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/assets/favicon.svg", status_code=307)


@app.get("/{filename:path}.html")
async def serve_html(filename: str):
    if filename == "cmasm-erp":
        alias_path = os.path.join(_FRONTEND_DIR, "cmasm_erp.html")
        if os.path.isfile(alias_path):
            return FileResponse(alias_path)
    path = os.path.join(_FRONTEND_DIR, f"{filename}.html")
    if os.path.isfile(path):
        return FileResponse(path)
    raise HTTPException(404, "Página não encontrada")


async def _proxy_xpredial(path: str, request: Request) -> Response:
    target_path = path.lstrip("/")
    target_url = f"{XPREDIAL_URL}/{target_path}" if target_path else XPREDIAL_URL
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            upstream = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body or None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"xPredial indisponível: {exc}") from exc

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in {"content-length", "connection", "transfer-encoding", "content-encoding"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.api_route("/api/predial", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_xpredial_root(request: Request):
    return await _proxy_xpredial("", request)


@app.api_route("/api/predial/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_xpredial(path: str, request: Request):
    return await _proxy_xpredial(path, request)


@app.get("/api/satellites")
async def list_satellites():
    """Status de saúde dos satélites FastAPI (xPredial, xAguada, xPaiol, xCalibracao)."""
    results = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for sat in _SATELLITES:
            try:
                r = await client.get(f"{sat['url']}/health")
                status = "online" if r.status_code == 200 else "error"
            except Exception:
                status = "offline"
            results.append({**sat, "status": status})
    return results


@app.get("/api/modulos")
async def list_modulos():
    """Lista PMOCs registrados (modulos_registrados) com categorias atendidas."""
    import json as _json
    rows = await db.fetch_all(
        "SELECT nome, descricao, url_navegacao, categorias_atend, ativo, criado_em "
        "FROM modulos_registrados WHERE ativo=1 ORDER BY nome"
    )
    for row in rows:
        try:
            row["categorias_atend"] = _json.loads(row["categorias_atend"] or "[]")
        except (ValueError, TypeError):
            row["categorias_atend"] = []
    return rows


@app.get("/api/admin/integridade")
async def relatorio_integridade(authorization: str | None = Header(None)):
    """CON-06 (D-05): auditoria contínua de conectividade — substitui scripts pontuais.
    Gated por role='admin' (_require_admin). Todas as queries usam apenas literais
    fixas/parâmetros validados — nenhuma interpolação de input de usuário (T-10-15).
    Agrupa inconsistências de FK/órfãos por categoria para o painel admin consumir."""
    user = await _require_auth(authorization)
    _require_admin(user)

    categorias: list[dict] = []

    # 1. Locais sem estrutura_id (órfãos do backfill CON-01 — D-04)
    locais_itens = await db.fetch_all(
        "SELECT id, codigo, nome FROM locais WHERE estrutura_id IS NULL ORDER BY codigo"
    )
    categorias.append({
        "chave": "locais_sem_estrutura",
        "titulo": "Locais sem estrutura_id",
        "total": len(locais_itens),
        "itens": locais_itens,
    })

    # 2. Itens de estoque sem local_id
    estoque_itens = await db.fetch_all(
        "SELECT id, codigo, nome FROM estoque WHERE local_id IS NULL ORDER BY codigo"
    )
    categorias.append({
        "chave": "estoque_sem_local",
        "titulo": "Itens de estoque sem local_id",
        "total": len(estoque_itens),
        "itens": estoque_itens,
    })

    # 3. Ativos "meio migrados" — loc (texto legado) preenchido mas local_id nulo
    ativos_loc_itens = await db.fetch_all(
        "SELECT id, nome, loc FROM ativos WHERE loc IS NOT NULL AND loc != '' AND local_id IS NULL ORDER BY id"
    )
    categorias.append({
        "chave": "ativos_loc_sem_local_id",
        "titulo": "Ativos com localização em texto (loc) sem local_id",
        "total": len(ativos_loc_itens),
        "itens": ativos_loc_itens,
    })

    # 4. OS com ativo_id não resolvido
    os_ativo_itens = await db.fetch_all(
        "SELECT id, codigo FROM ordens_servico WHERE ativo_id IS NOT NULL "
        "AND ativo_id NOT IN (SELECT id FROM ativos) ORDER BY codigo"
    )
    categorias.append({
        "chave": "os_ativo_nao_resolvido",
        "titulo": "OS com ativo_id inválido",
        "total": len(os_ativo_itens),
        "itens": os_ativo_itens,
    })

    # 5. OS com servico_id não resolvido
    os_servico_itens = await db.fetch_all(
        "SELECT id, codigo FROM ordens_servico WHERE servico_id IS NOT NULL "
        "AND servico_id NOT IN (SELECT id FROM catalogo_servicos) ORDER BY codigo"
    )
    categorias.append({
        "chave": "os_servico_nao_resolvido",
        "titulo": "OS com servico_id inválido",
        "total": len(os_servico_itens),
        "itens": os_servico_itens,
    })

    # 6. Planos órfãos (CON-05) — sem tipo aplicável, ainda marcados ativos
    planos_itens = await db.fetch_all(
        "SELECT id, codigo, nome FROM catalogo_planos "
        "WHERE (aplicavel_tipos IS NULL OR aplicavel_tipos = '[]') AND ativo = 1 ORDER BY codigo"
    )
    categorias.append({
        "chave": "planos_orfaos",
        "titulo": "Planos sem tipo aplicável",
        "total": len(planos_itens),
        "itens": planos_itens,
    })

    # 7. Máquinas de corte (CON-04) sem link a grama_maquinas (metadados legados)
    maquinas_itens = await db.fetch_all(
        "SELECT id, nome, tipo FROM ativos WHERE categoria='maquinas_corte' "
        "AND grama_maquina_id IS NULL ORDER BY id"
    )
    categorias.append({
        "chave": "maquinas_corte_sem_grama_maquina_id",
        "titulo": "Máquinas de corte sem vínculo a grama_maquinas",
        "total": len(maquinas_itens),
        "itens": maquinas_itens,
    })

    return {
        "gerado_em": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "categorias": categorias,
    }


@app.on_event("startup")
async def startup():
    await db.init()
    # Migração aditiva: usuarios.telegram_chat_id (PRAGMA antes do ALTER — nunca DROP)
    cols = {c["name"] for c in await db.fetch_all("PRAGMA table_info(usuarios)")}
    if "telegram_chat_id" not in cols:
        await db.execute("ALTER TABLE usuarios ADD COLUMN telegram_chat_id TEXT")
    init_grama(db)
    await _seed_colab_if_empty()
    await _seed_catalogo_manut_if_empty()
    await _migrate_catalogo_planos_cols()
    await _migrate_catalogo_servicos_taxon()
    await _migrate_modulo_transportes_categorias()
    await _seed_grama_if_empty()
    await _seed_catalogo_planos_from_tipos()
    await _seed_planos_transportes_if_empty()
    await _seed_fonoclama_if_empty()
    await _seed_pmoc_frota_corte_if_empty()
    # Catálogo de climatização vem de tools/import_ata2_climatizacao.py (serviços +
    # catalogo_planos/itens a partir do HTML da ATA2). Import manual, não no boot.


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _djb2(pw: str) -> str:
    """Mesmo algoritmo do ERP_core (hashPw) para compatibilidade.
    LEGADO — use apenas como verificador de hashes antigos. Nunca gere novos hashes djb2.
    """
    h = 0
    for ch in pw:
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return format(h, "x") if h >= 0 else format(h & 0xFFFFFFFF, "x")


# Instância singleton do PasswordHasher Argon2id (parâmetros default da lib são seguros).
# Usada em todo o ciclo de vida do processo — thread-safe, sem estado mutável.
_ph = PasswordHasher()

# Hash constante usado no caminho "usuário não encontrado" para equalizar o tempo de resposta
# com o caminho "senha incorreta" (ambos executam _ph.verify). Sem isso, a ausência do
# usuário retorna em ~0ms enquanto senha errada leva ~100ms — enumeração por timing.
_DUMMY_HASH: str = _ph.hash("dummy-constant-time-placeholder")


async def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await db.fetch_one(
        "SELECT s.usuario_id, u.nome, u.role FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise HTTPException(401, "Token inválido ou expirado")
    return row


def _require_escrita(user: dict) -> None:
    """RES-05: lança 403 se role == 'visualizador'. Chamar APÓS _require_auth.
    Padrão espelhado de backend/manutencao.py:724-726."""
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não têm permissão de escrita")


def _require_admin(user: dict) -> None:
    """CON-06 (D-05): só role='admin' acessa rotas administrativas (ex.: relatório
    de integridade). Chamar APÓS _require_auth, espelhando o padrão de _require_escrita."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores")


# ── Models ────────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    mat: str
    senha: str


class UsuarioIn(BaseModel):
    nome: str
    posto: Optional[str] = None
    mat: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    tipo: str = "militar"
    role: str = "operador"
    senha: Optional[str] = None


class SyncIn(BaseModel):
    """Payload do backup JSON exportado pelo ERP_core (botão 'Backup completo')."""
    users: list[dict]
    cargos: dict
    estrutura: list[dict]


class AtivosIn(BaseModel):
    """Payload do backup de gestao-ativos.html."""
    unidades: list[dict]


class AtivoIn(BaseModel):
    tipo: str
    categoria: str
    nome: str
    pat: Optional[str] = None
    placa: Optional[str] = None
    subtipo: Optional[str] = None   # vtr_int | vtr_ext | emb_rot | emb_pat
    loc: Optional[str] = None
    obs: Optional[str] = None
    uso_atual: float = 0
    unidade_uso: str = "h"


# ── Locais ────────────────────────────────────────────────────────────────────
class LocalIn(BaseModel):
    codigo: Optional[str] = None
    neo: Optional[str] = None
    nome: str
    tipo: str = "sala"
    area: str = "OPE"
    restricao: Optional[str] = None
    parent_id: Optional[int] = None
    estrutura_id: Optional[str] = None
    descricao: Optional[str] = None
    area_m2: Optional[float] = None
    altura_m: Optional[float] = None


# ── Ordens de Serviço ─────────────────────────────────────────────────────────
class OSIn(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: str = "corretiva"
    prioridade: str = "media"
    modulo_origem: Optional[str] = None
    solicitante_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    local_id: Optional[int] = None
    data_prevista: Optional[str] = None
    custo_estimado: Optional[float] = None
    observacoes: Optional[str] = None
    # RES-02 — lotação/departamento; opcional; GET auto-retorna via SELECT o.*
    departamento: Optional[str] = None
    # CON-02 (D-03) — override opcional da lotação (estrutura); se ausente,
    # create_os auto-deriva via cargos.usuario_id -> cargos.unidade_id do solicitante.
    lotacao_id: Optional[str] = None


class OSStatusIn(BaseModel):
    para_status: str
    obs: Optional[str] = None
    usuario_id: Optional[int] = None


class EtapaIn(BaseModel):
    titulo: str
    ordem: int = 0


# ── Estoque ───────────────────────────────────────────────────────────────────
class EstoqueIn(BaseModel):
    codigo: Optional[str] = None
    nome: str
    categoria: str = "material"
    unidade: str = "un"
    qtd_atual: float = 0
    qtd_minima: float = 0
    preco_unitario: float = 0
    local_id: Optional[int] = None
    obs: Optional[str] = None


class MovimentoIn(BaseModel):
    tipo: str   # entrada | saida | ajuste
    quantidade: float
    os_id: Optional[str] = None
    usuario_id: Optional[int] = None
    obs: Optional[str] = None
    documento: Optional[str] = None   # NF, requisição, nº doc
    fornecedor: Optional[str] = None  # fornecedor (entrada) ou requisitante (saída)


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(body: LoginIn):
    # Aceita login por matrícula OU por nome (compatibilidade ERP)
    user = await db.fetch_one(
        "SELECT * FROM usuarios WHERE (mat = ? OR nome = ?) AND ativo = 1",
        (body.mat, body.mat),
    )
    if not user:
        # Dummy verify equaliza o tempo de resposta com o caminho de senha incorreta,
        # impedindo enumeração de usuários por medição de latência (timing oracle).
        try:
            _ph.verify(_DUMMY_HASH, body.senha)
        except Exception:
            pass
        raise HTTPException(401, "Credenciais inválidas")

    stored = user.get("pw_hash")

    # SEC-02 (login side): conta sem hash não autentica — sem fallback de senha default.
    if not stored:
        raise HTTPException(401, "Credenciais inválidas")

    if stored.startswith("$argon2"):
        # Caminho Argon2id: verificação moderna.
        try:
            _ph.verify(stored, body.senha)
        except (VerificationError, InvalidHash):
            # VerificationError covers VerifyMismatchError (wrong password) and
            # decode/structural failures (malformed/truncated $argon2 hash). Both → 401.
            raise HTTPException(401, "Credenciais inválidas")
        # Re-hash se os parâmetros do PasswordHasher mudaram (future-proof).
        if _ph.check_needs_rehash(stored):
            new_hash = _ph.hash(body.senha)
            await db.execute(
                "UPDATE usuarios SET pw_hash = ? WHERE id = ?",
                (new_hash, user["id"]),
            )
    else:
        # Caminho legado djb2: verificar e fazer upgrade lazy para Argon2id.
        if _djb2(body.senha) != stored:
            raise HTTPException(401, "Credenciais inválidas")
        # Upgrade lazy: re-hash para Argon2id e persistir na mesma requisição.
        new_hash = _ph.hash(body.senha)
        await db.execute(
            "UPDATE usuarios SET pw_hash = ? WHERE id = ?",
            (new_hash, user["id"]),
        )

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(hours=TOKEN_TTL)
    await db.execute(
        "INSERT INTO sessoes (token, usuario_id, expira_em) VALUES (?, ?, ?)",
        (token, user["id"], expira.isoformat()),
    )
    return {
        "token": token,
        "expira_em": expira.isoformat(),
        "usuario": {k: v for k, v in user.items() if k != "pw_hash"},
    }


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        await db.execute("DELETE FROM sessoes WHERE token = ?", (authorization[7:],))
    return {"ok": True}


@app.get("/api/auth/me")
async def me(authorization: str | None = Header(None)):
    sess = await _require_auth(authorization)
    user = await db.fetch_one(
        "SELECT id, nome, posto, mat, email, tel, tipo, role FROM usuarios WHERE id = ?",
        (sess["usuario_id"],),
    )
    return user


@app.get("/health")
async def health():
    # Retorna contagem de usuários e ativos para o portal
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute("SELECT COUNT(*) FROM usuarios") as cur:
            usuarios = (await cur.fetchone())[0]
        async with db_conn.execute("SELECT COUNT(*) FROM ativos") as cur:
            ativos = (await cur.fetchone())[0]
    return {"status": "ok", "usuarios": usuarios, "ativos": ativos}


# ── Usuários ──────────────────────────────────────────────────────────────────
@app.get("/api/usuarios")
async def list_usuarios(ativo: int = 1):
    return await db.fetch_all(
        "SELECT id, nome, posto, mat, email, tel, tipo, role, ativo FROM usuarios WHERE ativo = ?",
        (ativo,),
    )


@app.get("/api/usuarios/{uid}")
async def get_usuario(uid: int):
    row = await db.fetch_one(
        "SELECT id, nome, posto, mat, email, tel, tipo, role, ativo FROM usuarios WHERE id = ?",
        (uid,),
    )
    if not row:
        raise HTTPException(404, "Usuário não encontrado")
    return row


@app.post("/api/usuarios", status_code=201)
async def create_usuario(body: UsuarioIn):
    # SEC-02: quando senha informada usa Argon2id; sem senha armazena "" (conta não autentica).
    pw = _ph.hash(body.senha) if body.senha else ""
    uid = await db.execute(
        "INSERT INTO usuarios (nome, posto, mat, email, tel, tipo, role, pw_hash) VALUES (?,?,?,?,?,?,?,?)",
        (body.nome, body.posto, body.mat, body.email, body.tel, body.tipo, body.role, pw),
    )
    return await get_usuario(uid)


@app.put("/api/usuarios/{uid}")
async def update_usuario(uid: int, body: UsuarioIn):
    await get_usuario(uid)  # valida existência; 404 se não encontrado
    # SEC-02: preservar o hash atual ao atualizar sem fornecer senha.
    # get_usuario não retorna pw_hash (campo sensível), buscar direto do DB.
    existing = await db.fetch_one(
        "SELECT pw_hash FROM usuarios WHERE id = ?", (uid,)
    )
    existing_hash = (existing or {}).get("pw_hash") or ""
    # Quando senha fornecida: Argon2id; quando ausente: preservar hash existente.
    pw = _ph.hash(body.senha) if body.senha else existing_hash
    await db.execute(
        "UPDATE usuarios SET nome=?, posto=?, mat=?, email=?, tel=?, tipo=?, role=?, pw_hash=? WHERE id=?",
        (body.nome, body.posto, body.mat, body.email, body.tel, body.tipo, body.role, pw, uid),
    )
    return await get_usuario(uid)


# ── Estrutura / Organograma ───────────────────────────────────────────────────
@app.get("/api/estrutura")
async def list_estrutura():
    return await db.fetch_all("SELECT * FROM estrutura ORDER BY id")


@app.get("/api/unidades")
async def list_unidades():
    """Estrutura enriquecida com ocupante atual."""
    rows = await db.fetch_all(
        """SELECT e.*, c.usuario_id, u.nome AS ocupante_nome, u.posto AS ocupante_posto
           FROM estrutura e
           LEFT JOIN cargos c ON c.unidade_id = e.id
           LEFT JOIN usuarios u ON u.id = c.usuario_id
           ORDER BY e.id""",
    )
    return rows


# ── Ativos ────────────────────────────────────────────────────────────────────
@app.get("/api/ativos")
async def list_ativos(categoria: str | None = None, ativo: int = 1):
    if categoria:
        return await db.fetch_all(
            "SELECT * FROM ativos WHERE categoria = ? AND ativo = ? ORDER BY nome",
            (categoria, ativo),
        )
    return await db.fetch_all("SELECT * FROM ativos WHERE ativo = ? ORDER BY categoria, nome", (ativo,))


@app.get("/api/pmoc/refrigeracao")
async def list_refrigeracao():
    """Dados ricos de refrigeração: pmoc_refrigeracao + ativo + local/ambiente.
    Consumido pela página Refrigeração do módulo Manutenção."""
    return await db.fetch_all(
        """
        SELECT p.*,
               a.nome  AS ativo_nome,  a.tipo AS ativo_tipo, a.pat AS ativo_pat,
               a.loc   AS loc_txt,     a.ativo AS ativo_ativo,
               l.nome  AS local_nome,  l.area AS local_area,
               l.area_m2 AS local_area_m2, l.altura_m AS local_altura_m,
               lp.nome AS predio_nome
        FROM pmoc_refrigeracao p
        JOIN ativos a       ON a.id = p.ativo_id
        LEFT JOIN locais l  ON l.id = p.local_id
        LEFT JOIN locais lp ON lp.id = l.parent_id
        ORDER BY a.nome
        """
    )


_PMOC_EDIT = {
    "funciona", "estado_conservacao", "est_idade", "obs", "permanencia", "criticidade",
    "critico", "horas_dia", "dias_semana", "tensao_nominal", "tensao_medida",
    "corrente_nominal", "corrente_medida", "potencia_kw", "quadro", "disjuntor", "cabo",
    "gas_tipo", "carga_g", "pressao_padrao", "pressao_medida", "temp_evaporadora",
    "temp_evaporadora_m", "temp_centro", "temp_longe", "patrimonio", "data_instalacao",
    "ultima_manutencao", "fabricante", "btu", "funcao", "automacao", "prioridade",
    "risco", "estado_operacional",
}
_ATIVO_EDIT = {"nome", "obs", "pat", "loc", "local_id"}


@app.put("/api/pmoc/refrigeracao/{ativo_id}")
async def update_refrigeracao(ativo_id: str, body: dict, authorization: str | None = Header(None)):
    """Edita a ficha de uma máquina de refrigeração: campos de pmoc_refrigeracao
    e/ou ativos. Whitelist por segurança."""
    user = await _require_auth(authorization)
    _require_escrita(user)
    row = await db.fetch_one("SELECT ativo_id FROM pmoc_refrigeracao WHERE ativo_id = ?", (ativo_id,))
    if not row:
        raise HTTPException(404, "Refrigeração não encontrada")
    pmoc = [(k, v) for k, v in body.items() if k in _PMOC_EDIT]
    if pmoc:
        sets = ", ".join(f"{k} = ?" for k, _ in pmoc)
        await db.execute(
            f"UPDATE pmoc_refrigeracao SET {sets}, atualizado_em = CURRENT_TIMESTAMP WHERE ativo_id = ?",
            [v for _, v in pmoc] + [ativo_id],
        )
    ativo = [(k, v) for k, v in body.items() if k in _ATIVO_EDIT]
    if ativo:
        sets = ", ".join(f"{k} = ?" for k, _ in ativo)
        await db.execute(
            f"UPDATE ativos SET {sets} WHERE id = ?",
            [v for _, v in ativo] + [ativo_id],
        )
    return await db.fetch_one(
        """SELECT p.*, a.nome AS ativo_nome, a.loc AS loc_txt
           FROM pmoc_refrigeracao p JOIN ativos a ON a.id = p.ativo_id
           WHERE p.ativo_id = ?""",
        (ativo_id,),
    )


@app.post("/api/pmoc/refrigeracao/{ativo_id}/os-preventiva", status_code=201)
async def gerar_os_preventiva(ativo_id: str, authorization: str | None = Header(None)):
    """Cria OS preventiva PMOC ligada a um plano de climatização (catalogo_planos),
    resolvido pelo tipo do ativo (fallback: 1º plano de climatização). Etapas =
    serviços preventivos do plano; servico_id = 1º (débito de estoque pelo #1)."""
    user = await _require_auth(authorization)
    _require_escrita(user)
    import json
    ativo = await db.fetch_one("SELECT id, nome, tipo, local_id FROM ativos WHERE id = ?", (ativo_id,))
    if not ativo:
        raise HTTPException(404, "Ativo não encontrado")
    planos = await db.fetch_all(
        "SELECT id, aplicavel_tipos, tipo_codigo FROM catalogo_planos "
        "WHERE categoria = 'climatizacao' AND ativo = 1 ORDER BY codigo"
    )
    chosen = None
    for p in planos:
        tipos = []
        try:
            tipos = json.loads(p["aplicavel_tipos"] or "[]")
        except Exception:
            tipos = []
        if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
            tipos.append(p["tipo_codigo"])
        if ativo["tipo"] in tipos:
            chosen = p; break
    if not chosen and planos:
        chosen = planos[0]  # fallback: tipos sem plano próprio (AC_JANELA/PISO_TETO/SELF)
    if not chosen:
        raise HTTPException(400, "Sem plano de climatização cadastrado")
    itens = await db.fetch_all(
        "SELECT s.id AS servico_id, s.nome FROM catalogo_plano_itens i "
        "JOIN catalogo_servicos s ON s.id = i.servico_id "
        "WHERE i.plano_id = ? AND i.classe = 'prev' ORDER BY i.seq",
        (chosen["id"],),
    )
    if not itens:
        raise HTTPException(400, "Plano sem serviços preventivos")
    pm = await db.fetch_one("SELECT criticidade, local_id FROM pmoc_refrigeracao WHERE ativo_id = ?", (ativo_id,)) or {}
    crit = {"CRÍTICA": "critica", "ALTA": "alta", "MÉDIA": "media", "BAIXA": "baixa"}.get(
        (pm.get("criticidade") or "").upper(), "media")
    local_id = ativo["local_id"] or pm.get("local_id")
    oid = str(uuid.uuid4())
    codigo = await _gen_os_codigo()
    await db.execute(
        """INSERT INTO ordens_servico
           (id, codigo, titulo, descricao, tipo, prioridade, modulo_origem,
            local_id, ativo_id, servico_id)
           VALUES (?,?,?,?, 'preventiva', ?, 'refrigeracao', ?, ?, ?)""",
        (oid, codigo, f"Preventiva PMOC — {ativo['nome']}", itens[0]["nome"], crit,
         local_id, ativo_id, itens[0]["servico_id"]),
    )
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs) VALUES (?,?,?,?)",
        (oid, None, "aberta", "OS preventiva gerada de plano de climatização"),
    )
    for i, it in enumerate(itens):
        await db.execute("INSERT INTO os_etapas (os_id, titulo, ordem) VALUES (?,?,?)", (oid, it["nome"], i))
    return await get_os(oid)


@app.get("/api/equipe/refrigeracao")
async def equipe_refrigeracao():
    """Técnicos de refrigeração = pessoas lotadas na subárvore da Divisão de
    Manutenção Especializada (CMASM-13). G2 do design: equipe via estrutura/cargos."""
    return await db.fetch_all(
        """
        WITH RECURSIVE sub(id) AS (
            SELECT id FROM estrutura WHERE id = 'CMASM-13'
            UNION ALL
            SELECT e.id FROM estrutura e JOIN sub ON e.pai = sub.id
        )
        SELECT u.id, u.nome, u.posto, e.nome AS setor, e.cargo
        FROM cargos cg
        JOIN sub        ON sub.id = cg.unidade_id
        JOIN usuarios u ON u.id   = cg.usuario_id
        JOIN estrutura e ON e.id  = cg.unidade_id
        WHERE u.ativo = 1
        ORDER BY u.nome
        """
    )


@app.get("/api/ativos/{aid}")
async def get_ativo(aid: str):
    row = await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    return row


@app.post("/api/ativos", status_code=201)
async def create_ativo(body: AtivoIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    aid = str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO ativos (id, tipo, categoria, nome, pat, placa, subtipo, loc, obs, uso_atual, unidade_uso, ativo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (aid, body.tipo, body.categoria, body.nome, body.pat, body.placa, body.subtipo,
         body.loc, body.obs, body.uso_atual, body.unidade_uso),
    )
    return await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))


@app.put("/api/ativos/{aid}")
async def update_ativo(aid: str, body: AtivoIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute(
        "UPDATE ativos SET tipo=?, categoria=?, nome=?, pat=?, placa=?, subtipo=?, "
        "loc=?, obs=?, uso_atual=?, unidade_uso=? WHERE id=?",
        (body.tipo, body.categoria, body.nome, body.pat, body.placa, body.subtipo,
         body.loc, body.obs, body.uso_atual, body.unidade_uso, aid),
    )
    return await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))


@app.patch("/api/ativos/{aid}/arquivar")
async def arquivar_ativo(aid: str):
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute("UPDATE ativos SET ativo = 0 WHERE id = ?", (aid,))
    return {"ok": True}


@app.patch("/api/ativos/{aid}/restaurar")
async def restaurar_ativo(aid: str):
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute("UPDATE ativos SET ativo = 1 WHERE id = ?", (aid,))
    return {"ok": True}


@app.post("/api/ativos/importar-csv")
async def importar_ativos_csv(body: dict):
    """
    Recebe {csv: "<conteudo>"} e faz bulk upsert.
    Colunas obrigatórias: nome, tipo, categoria
    Colunas opcionais: pat, loc, obs, uso_atual, unidade_uso, id
    """
    raw = body.get("csv", "")
    if not raw:
        raise HTTPException(400, "Campo 'csv' ausente")
    reader = csv.DictReader(io.StringIO(raw))
    inserted = 0
    for row in reader:
        nome = row.get("nome", "").strip()
        tipo = row.get("tipo", "").strip()
        categoria = row.get("categoria", "").strip()
        if not nome or not tipo or not categoria:
            continue
        aid = row.get("id", "").strip() or str(uuid.uuid4())[:8]
        pat = row.get("pat", "").strip() or None
        loc = row.get("loc", "").strip() or None
        obs = row.get("obs", "").strip() or None
        try:
            uso_atual = float(row.get("uso_atual", 0) or 0)
        except ValueError:
            uso_atual = 0
        unidade_uso = row.get("unidade_uso", "h").strip() or "h"
        if unidade_uso not in ("h", "km", "meses"):
            unidade_uso = "h"
        await db.execute(
            "INSERT OR REPLACE INTO ativos (id, tipo, categoria, nome, pat, loc, obs, uso_atual, unidade_uso, ativo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (aid, tipo, categoria, nome, pat, loc, obs, uso_atual, unidade_uso),
        )
        inserted += 1
    return {"ok": True, "inseridos": inserted}


@app.get("/api/ativos/exportar/csv")
async def exportar_ativos_csv(categoria: str | None = None, ativo: int = 1):
    if categoria:
        rows = await db.fetch_all(
            "SELECT * FROM ativos WHERE categoria = ? AND ativo = ? ORDER BY nome",
            (categoria, ativo),
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM ativos WHERE ativo = ? ORDER BY categoria, nome", (ativo,)
        )
    buf = io.StringIO()
    cols = ["id", "tipo", "categoria", "nome", "pat", "loc", "obs", "uso_atual", "unidade_uso"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in cols if k in r})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ativos.csv"},
    )


# ── Sync: importa backup do ERP_core ─────────────────────────────────────────
@app.post("/api/sync/erp")
async def sync_erp(body: SyncIn):
    """
    Recebe o JSON exportado pelo botão 'Backup completo' do cmasm-erp.html
    e sincroniza usuários, estrutura e cargos no SQLite.
    Não destrói dados existentes — usa INSERT OR REPLACE.
    """
    # Usuários
    for u in body.users:
        await db.execute(
            """INSERT OR REPLACE INTO usuarios (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (u["id"], u.get("nome",""), u.get("posto",""), u.get("mat",""),
             u.get("email",""), u.get("tel",""), u.get("tipo","militar"),
             u.get("role","operador"), u.get("pw_hash","")),
        )

    # Estrutura (organograma)
    for e in body.estrutura:
        await db.execute(
            "INSERT OR REPLACE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
            (e["id"], e.get("tipo",""), e.get("nome",""), e.get("pai"),
             e.get("cargo",""), e.get("ct","")),
        )

    # Cargos
    for unidade_id, c in body.cargos.items():
        uid = c.get("usuario_id")
        obs = c.get("obs","")
        await db.execute(
            "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id, obs) VALUES (?,?,?)",
            (unidade_id, uid, obs),
        )

    return {"ok": True, "usuarios": len(body.users), "estrutura": len(body.estrutura), "cargos": len(body.cargos)}


@app.post("/api/sync/ativos")
async def sync_ativos(body: AtivosIn):
    """
    Recebe o JSON exportado pelo gestao-ativos.html e sincroniza ativos.
    """
    # TIPOS → categoria (duplica lógica do gestao-ativos-data.js)
    CAT_MAP = {
        "FS220":"maquinas_corte","GAR":"maquinas_corte","MS650":"maquinas_corte",
        "TS114":"maquinas_corte","SOL":"maquinas_corte",
        "VTR_PICKUP":"viaturas","VTR_CARGA":"viaturas",
        "EMB_LANCHA":"embarcacoes","EMB_BOTE":"embarcacoes",
        "AC_SPLIT":"climatizacao","AC_CENTRAL":"climatizacao",
        "GERADOR":"eletrica",
    }
    UNIT_MAP = {"FS220":"h","GAR":"h","MS650":"h","TS114":"h","SOL":"h",
                "VTR_PICKUP":"km","VTR_CARGA":"km",
                "EMB_LANCHA":"h","EMB_BOTE":"h",
                "AC_SPLIT":"meses","AC_CENTRAL":"meses","GERADOR":"h"}

    for u in body.unidades:
        tid  = u.get("tipo","")
        cat  = CAT_MAP.get(tid, "outros")
        unit = UNIT_MAP.get(tid, "h")
        await db.execute(
            """INSERT OR REPLACE INTO ativos (id, tipo, categoria, nome, pat, loc, obs, ativo, unidade_uso)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (u["id"], tid, cat, u.get("nome",""), u.get("pat",""),
             u.get("loc",""), u.get("obs",""), 1 if u.get("ativo",True) else 0, unit),
        )

    return {"ok": True, "ativos": len(body.unidades)}


# ── Shared (compatibilidade ERP_core localStorage) ────────────────────────────
@app.get("/api/shared")
async def shared():
    """Retorna o mesmo formato que o ERP_core publica em localStorage.cmasm_shared."""
    users = await db.fetch_all(
        "SELECT id, nome, posto, mat, email, tel, tipo, role FROM usuarios WHERE ativo = 1"
    )
    cargos_rows = await db.fetch_all("SELECT unidade_id, usuario_id, obs FROM cargos")
    estrutura   = await db.fetch_all("SELECT id, tipo, nome, pai, cargo, ct FROM estrutura")
    cargos = {r["unidade_id"]: {"usuario_id": r["usuario_id"], "obs": r["obs"]} for r in cargos_rows}
    return {
        "v": 2,
        "ts": int(datetime.utcnow().timestamp() * 1000),
        "org": "CMASM",
        "users": users,
        "cargos": cargos,
        "estrutura": estrutura,
    }


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    n_users = await db.fetch_one("SELECT COUNT(*) AS n FROM usuarios")
    n_ativos = await db.fetch_one("SELECT COUNT(*) AS n FROM ativos")
    return {"status": "ok", "usuarios": n_users["n"], "ativos": n_ativos["n"]}


# ── Portal do Colaborador (CompanyHub incorporado) ─────────────────────────
@app.get("/api/colab/bootstrap")
async def colab_bootstrap():
    events = await db.fetch_all(
        "SELECT id, title, type, event_date, location, attendees, description FROM colab_events ORDER BY event_date"
    )
    policies = await db.fetch_all(
        "SELECT id, title, category, version, description, owner, created_date, updated_date FROM colab_policies ORDER BY updated_date DESC"
    )
    executives = await db.fetch_all(
        "SELECT id, full_name, position, department, email, phone, office_location, years_with_company, bio, linkedin_url, photo_url FROM colab_executives ORDER BY full_name"
    )
    announcements = await db.fetch_all(
        "SELECT id, title, content, priority, author, created_date FROM colab_announcements ORDER BY created_date DESC"
    )
    tickets = await db.fetch_all(
        "SELECT id, subject, description, category, priority, status, requester_name, requester_email, department, assigned_to, resolution_notes, due_date, created_date FROM colab_tickets ORDER BY created_date DESC"
    )
    timeoff = await db.fetch_all(
        "SELECT id, type, start_date, end_date, reason, total_days, status, employee_name, employee_email, department, manager_email, manager_notes, approval_date, created_date FROM colab_timeoff ORDER BY created_date DESC"
    )
    return {
        "events": events,
        "policies": policies,
        "executives": executives,
        "announcements": announcements,
        "tickets": tickets,
        "timeoff": timeoff,
    }


@app.post("/api/colab/events", status_code=201)
async def colab_create_event(payload: dict):
    event_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_events (id, title, type, event_date, location, attendees, description) VALUES (?,?,?,?,?,?,?)",
        (
            event_id,
            payload.get("title") or "",
            payload.get("type") or "event",
            payload.get("event_date") or "",
            payload.get("location"),
            _to_int(payload.get("attendees"), 0),
            payload.get("description"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, title, type, event_date, location, attendees, description FROM colab_events WHERE id = ?",
        (event_id,),
    )


@app.delete("/api/colab/events/{event_id}")
async def colab_delete_event(event_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_events WHERE id = ?", (event_id,))
    if not exists:
        raise HTTPException(404, "Evento não encontrado")
    await db.execute("DELETE FROM colab_events WHERE id = ?", (event_id,))
    return {"ok": True, "id": event_id}


@app.post("/api/colab/policies", status_code=201)
async def colab_create_policy(payload: dict):
    policy_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_policies (id, title, category, version, description, owner, created_date, updated_date) VALUES (?,?,?,?,?,?,?,?)",
        (
            policy_id,
            payload.get("title") or "",
            payload.get("category") or "general",
            payload.get("version"),
            payload.get("description"),
            payload.get("owner"),
            payload.get("created_date"),
            payload.get("updated_date"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, title, category, version, description, owner, created_date, updated_date FROM colab_policies WHERE id = ?",
        (policy_id,),
    )


@app.delete("/api/colab/policies/{policy_id}")
async def colab_delete_policy(policy_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_policies WHERE id = ?", (policy_id,))
    if not exists:
        raise HTTPException(404, "Política não encontrada")
    await db.execute("DELETE FROM colab_policies WHERE id = ?", (policy_id,))
    return {"ok": True, "id": policy_id}


@app.post("/api/colab/executives", status_code=201)
async def colab_create_executive(payload: dict):
    executive_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_executives (id, full_name, position, department, email, phone, office_location, years_with_company, bio, linkedin_url, photo_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            executive_id,
            payload.get("full_name") or "",
            payload.get("position") or "",
            payload.get("department"),
            payload.get("email"),
            payload.get("phone"),
            payload.get("office_location"),
            _to_int(payload.get("years_with_company"), 0),
            payload.get("bio"),
            payload.get("linkedin_url"),
            payload.get("photo_url"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, full_name, position, department, email, phone, office_location, years_with_company, bio, linkedin_url, photo_url FROM colab_executives WHERE id = ?",
        (executive_id,),
    )


@app.delete("/api/colab/executives/{executive_id}")
async def colab_delete_executive(executive_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_executives WHERE id = ?", (executive_id,))
    if not exists:
        raise HTTPException(404, "Executivo não encontrado")
    await db.execute("DELETE FROM colab_executives WHERE id = ?", (executive_id,))
    return {"ok": True, "id": executive_id}


@app.post("/api/colab/announcements", status_code=201)
async def colab_create_announcement(payload: dict):
    announcement_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_announcements (id, title, content, priority, author, created_date) VALUES (?,?,?,?,?,?)",
        (
            announcement_id,
            payload.get("title") or "",
            payload.get("content") or "",
            payload.get("priority") or "medium",
            payload.get("author"),
            payload.get("created_date"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, title, content, priority, author, created_date FROM colab_announcements WHERE id = ?",
        (announcement_id,),
    )


@app.delete("/api/colab/announcements/{announcement_id}")
async def colab_delete_announcement(announcement_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_announcements WHERE id = ?", (announcement_id,))
    if not exists:
        raise HTTPException(404, "Comunicado não encontrado")
    await db.execute("DELETE FROM colab_announcements WHERE id = ?", (announcement_id,))
    return {"ok": True, "id": announcement_id}


@app.post("/api/colab/tickets", status_code=201)
async def colab_create_ticket(payload: dict):
    ticket_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_tickets (id, subject, description, category, priority, status, requester_name, requester_email, department, assigned_to, resolution_notes, due_date, created_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            ticket_id,
            payload.get("subject") or "",
            payload.get("description") or "",
            payload.get("category") or "other",
            payload.get("priority") or "medium",
            payload.get("status") or "open",
            payload.get("requester_name"),
            payload.get("requester_email"),
            payload.get("department"),
            payload.get("assigned_to"),
            payload.get("resolution_notes"),
            payload.get("due_date"),
            payload.get("created_date"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, subject, description, category, priority, status, requester_name, requester_email, department, assigned_to, resolution_notes, due_date, created_date FROM colab_tickets WHERE id = ?",
        (ticket_id,),
    )


@app.patch("/api/colab/tickets/{ticket_id}")
async def colab_patch_ticket(ticket_id: str, payload: dict):
    exists = await db.fetch_one("SELECT id FROM colab_tickets WHERE id = ?", (ticket_id,))
    if not exists:
        raise HTTPException(404, "Chamado não encontrado")
    await db.execute(
        "UPDATE colab_tickets SET status = ?, assigned_to = ?, resolution_notes = ?, due_date = ? WHERE id = ?",
        (
            payload.get("status") or "open",
            payload.get("assigned_to"),
            payload.get("resolution_notes"),
            payload.get("due_date"),
            ticket_id,
        ),
    )
    return await db.fetch_one(
        "SELECT id, subject, description, category, priority, status, requester_name, requester_email, department, assigned_to, resolution_notes, due_date, created_date FROM colab_tickets WHERE id = ?",
        (ticket_id,),
    )


@app.delete("/api/colab/tickets/{ticket_id}")
async def colab_delete_ticket(ticket_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_tickets WHERE id = ?", (ticket_id,))
    if not exists:
        raise HTTPException(404, "Chamado não encontrado")
    await db.execute("DELETE FROM colab_tickets WHERE id = ?", (ticket_id,))
    return {"ok": True, "id": ticket_id}


@app.post("/api/colab/timeoff", status_code=201)
async def colab_create_timeoff(payload: dict):
    timeoff_id = payload.get("id") or str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO colab_timeoff (id, type, start_date, end_date, reason, total_days, status, employee_name, employee_email, department, manager_email, manager_notes, approval_date, created_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            timeoff_id,
            payload.get("type") or "vacation",
            payload.get("start_date") or "",
            payload.get("end_date") or "",
            payload.get("reason"),
            _to_int(payload.get("total_days"), 0),
            payload.get("status") or "pending",
            payload.get("employee_name"),
            payload.get("employee_email"),
            payload.get("department"),
            payload.get("manager_email"),
            payload.get("manager_notes"),
            payload.get("approval_date"),
            payload.get("created_date"),
        ),
    )
    return await db.fetch_one(
        "SELECT id, type, start_date, end_date, reason, total_days, status, employee_name, employee_email, department, manager_email, manager_notes, approval_date, created_date FROM colab_timeoff WHERE id = ?",
        (timeoff_id,),
    )


@app.patch("/api/colab/timeoff/{timeoff_id}")
async def colab_patch_timeoff(timeoff_id: str, payload: dict):
    exists = await db.fetch_one("SELECT id FROM colab_timeoff WHERE id = ?", (timeoff_id,))
    if not exists:
        raise HTTPException(404, "Solicitação de folga não encontrada")
    await db.execute(
        "UPDATE colab_timeoff SET status = ?, manager_notes = ?, manager_email = ?, approval_date = ? WHERE id = ?",
        (
            payload.get("status") or "pending",
            payload.get("manager_notes"),
            payload.get("manager_email"),
            payload.get("approval_date"),
            timeoff_id,
        ),
    )
    return await db.fetch_one(
        "SELECT id, type, start_date, end_date, reason, total_days, status, employee_name, employee_email, department, manager_email, manager_notes, approval_date, created_date FROM colab_timeoff WHERE id = ?",
        (timeoff_id,),
    )


@app.delete("/api/colab/timeoff/{timeoff_id}")
async def colab_delete_timeoff(timeoff_id: str):
    exists = await db.fetch_one("SELECT id FROM colab_timeoff WHERE id = ?", (timeoff_id,))
    if not exists:
        raise HTTPException(404, "Solicitação de folga não encontrada")
    await db.execute("DELETE FROM colab_timeoff WHERE id = ?", (timeoff_id,))
    return {"ok": True, "id": timeoff_id}


@app.put("/api/colab/events")
async def colab_put_events(payload: list[dict]):
    await db.execute("DELETE FROM colab_events")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("title") or "",
                item.get("type") or "event",
                item.get("event_date") or "",
                item.get("location"),
                _to_int(item.get("attendees"), 0),
                item.get("description"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_events (id, title, type, event_date, location, attendees, description) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


@app.put("/api/colab/policies")
async def colab_put_policies(payload: list[dict]):
    await db.execute("DELETE FROM colab_policies")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("title") or "",
                item.get("category") or "general",
                item.get("version"),
                item.get("description"),
                item.get("owner"),
                item.get("created_date"),
                item.get("updated_date"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_policies (id, title, category, version, description, owner, created_date, updated_date) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


@app.put("/api/colab/executives")
async def colab_put_executives(payload: list[dict]):
    await db.execute("DELETE FROM colab_executives")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("full_name") or "",
                item.get("position") or "",
                item.get("department"),
                item.get("email"),
                item.get("phone"),
                item.get("office_location"),
                _to_int(item.get("years_with_company"), 0),
                item.get("bio"),
                item.get("linkedin_url"),
                item.get("photo_url"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_executives (id, full_name, position, department, email, phone, office_location, years_with_company, bio, linkedin_url, photo_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


@app.put("/api/colab/announcements")
async def colab_put_announcements(payload: list[dict]):
    await db.execute("DELETE FROM colab_announcements")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("title") or "",
                item.get("content") or "",
                item.get("priority") or "medium",
                item.get("author"),
                item.get("created_date"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_announcements (id, title, content, priority, author, created_date) VALUES (?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


@app.put("/api/colab/tickets")
async def colab_put_tickets(payload: list[dict]):
    await db.execute("DELETE FROM colab_tickets")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("subject") or "",
                item.get("description") or "",
                item.get("category") or "other",
                item.get("priority") or "medium",
                item.get("status") or "open",
                item.get("requester_name"),
                item.get("requester_email"),
                item.get("department"),
                item.get("assigned_to"),
                item.get("resolution_notes"),
                item.get("due_date"),
                item.get("created_date"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_tickets (id, subject, description, category, priority, status, requester_name, requester_email, department, assigned_to, resolution_notes, due_date, created_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


@app.put("/api/colab/timeoff")
async def colab_put_timeoff(payload: list[dict]):
    await db.execute("DELETE FROM colab_timeoff")
    rows = []
    for item in payload:
        rows.append(
            (
                item.get("id") or str(uuid.uuid4())[:8],
                item.get("type") or "vacation",
                item.get("start_date") or "",
                item.get("end_date") or "",
                item.get("reason"),
                _to_int(item.get("total_days"), 0),
                item.get("status") or "pending",
                item.get("employee_name"),
                item.get("employee_email"),
                item.get("department"),
                item.get("manager_email"),
                item.get("manager_notes"),
                item.get("approval_date"),
                item.get("created_date"),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO colab_timeoff (id, type, start_date, end_date, reason, total_days, status, employee_name, employee_email, department, manager_email, manager_notes, approval_date, created_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"ok": True, "count": len(rows)}


# ── Locais ────────────────────────────────────────────────────────────────────
@app.get("/api/locais")
async def list_locais(parent_id: int | None = None, tipo: str | None = None):
    clauses, params = ["l.ativo = 1"], []
    if parent_id is not None:
        clauses.append("l.parent_id = ?")
        params.append(parent_id)
    if tipo:
        clauses.append("l.tipo = ?")
        params.append(tipo)
    where = " AND ".join(clauses)
    return await db.fetch_all(
        f"""SELECT l.*,
                   e.nome AS estrutura_nome,
                   c.usuario_id AS ocupante_id,
                   u.nome AS ocupante_nome,
                   u.role AS ocupante_role,
                   (SELECT COUNT(*) FROM ativos a WHERE a.loc = l.codigo OR a.loc = l.nome) AS ativos_count,
                   (SELECT COUNT(*) FROM ordens_servico o WHERE o.local_id = l.id) AS os_count
            FROM locais l
            LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)
            LEFT JOIN cargos c ON c.unidade_id = COALESCE(l.estrutura_id, l.codigo)
            LEFT JOIN usuarios u ON u.id = c.usuario_id
            WHERE {where}
            ORDER BY l.codigo, l.nome""",
        tuple(params),
    )


@app.get("/api/locais/{lid}")
async def get_local(lid: int):
    row = await db.fetch_one(
        """SELECT l.*,
                  e.nome AS estrutura_nome,
                  c.usuario_id AS ocupante_id,
                  u.nome AS ocupante_nome,
                  u.role AS ocupante_role,
                  (SELECT COUNT(*) FROM ativos a WHERE a.loc = l.codigo OR a.loc = l.nome) AS ativos_count,
                  (SELECT COUNT(*) FROM ordens_servico o WHERE o.local_id = l.id) AS os_count
           FROM locais l
           LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)
           LEFT JOIN cargos c ON c.unidade_id = COALESCE(l.estrutura_id, l.codigo)
           LEFT JOIN usuarios u ON u.id = c.usuario_id
           WHERE l.id = ?""",
        (lid,),
    )
    if not row:
        raise HTTPException(404, "Local não encontrado")
    filhos = await db.fetch_all(
        "SELECT id, codigo, neo, nome, tipo, area, restricao, estrutura_id FROM locais WHERE parent_id = ? AND ativo = 1 ORDER BY codigo, nome",
        (lid,),
    )
    return {**row, "filhos": filhos}


@app.post("/api/locais", status_code=201)
async def create_local(body: LocalIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    lid = await db.execute(
        "INSERT INTO locais (codigo, neo, nome, tipo, area, restricao, parent_id, estrutura_id, descricao, area_m2, altura_m) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (body.codigo, body.neo, body.nome, body.tipo, body.area, body.restricao, body.parent_id, body.estrutura_id, body.descricao, body.area_m2, body.altura_m),
    )
    return await get_local(lid)


@app.put("/api/locais/{lid}")
async def update_local(lid: int, body: LocalIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    await get_local(lid)
    await db.execute(
        "UPDATE locais SET codigo=?, neo=?, nome=?, tipo=?, area=?, restricao=?, parent_id=?, estrutura_id=?, descricao=?, area_m2=?, altura_m=? WHERE id=?",
        (body.codigo, body.neo, body.nome, body.tipo, body.area, body.restricao, body.parent_id, body.estrutura_id, body.descricao, body.area_m2, body.altura_m, lid),
    )
    return await get_local(lid)


# ── Ordens de Serviço ─────────────────────────────────────────────────────────
async def _gen_os_codigo() -> str:
    ano = datetime.utcnow().year
    row = await db.fetch_one(
        "SELECT COUNT(*) AS n FROM ordens_servico WHERE codigo LIKE ?", (f"OS-{ano}-%",)
    )
    return f"OS-{ano}-{(row['n'] + 1):03d}"


@app.get("/api/os/kpis")
async def os_kpis(modulo: str | None = None):
    params: list = []
    where = ""
    if modulo:
        where = "WHERE modulo_origem = ?"
        params.append(modulo)
    rows = await db.fetch_all(
        f"SELECT status, COUNT(*) AS n FROM ordens_servico {where} GROUP BY status", tuple(params)
    )
    return {r["status"]: r["n"] for r in rows}


@app.get("/api/os/kanban")
async def os_kanban(modulo: str | None = None):
    """Retorna OS agrupadas por status para view kanban."""
    colunas = ["aberta", "em_andamento", "aguardando", "concluida", "cancelada"]
    params: list = []
    where = ""
    if modulo:
        where = "WHERE modulo_origem = ?"
        params.append(modulo)
    rows = await db.fetch_all(
        f"""SELECT o.*, l.nome AS local_nome,
                   u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
            FROM ordens_servico o
            LEFT JOIN locais l ON l.id = o.local_id
            LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
            LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
            {where} ORDER BY o.criado_em DESC""",
        tuple(params),
    )
    result = {col: [] for col in colunas}
    for row in rows:
        col = row.get("status", "aberta")
        if col not in result:
            result[col] = []
        result[col].append(row)
    return result


@app.get("/api/os")
async def list_os(
    status: str | None = None,
    modulo: str | None = None,
    local_id: int | None = None,
    limit: int = Query(50, le=200),
):
    clauses, params = [], []
    if status:
        clauses.append("o.status = ?"); params.append(status)
    if modulo:
        clauses.append("o.modulo_origem = ?"); params.append(modulo)
    if local_id is not None:
        clauses.append("o.local_id = ?"); params.append(local_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    return await db.fetch_all(
        f"""SELECT o.*, l.nome AS local_nome,
                   u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
            FROM ordens_servico o
            LEFT JOIN locais l ON l.id = o.local_id
            LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
            LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
            {where} ORDER BY o.criado_em DESC LIMIT ?""",
        tuple(params),
    )


@app.get("/api/os/{oid}")
async def get_os(oid: str):
    row = await db.fetch_one(
        """SELECT o.*, l.nome AS local_nome,
                  u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
           FROM ordens_servico o
           LEFT JOIN locais l ON l.id = o.local_id
           LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
           LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
           WHERE o.id = ?""",
        (oid,),
    )
    if not row:
        raise HTTPException(404, "OS não encontrada")
    etapas = await db.fetch_all("SELECT * FROM os_etapas WHERE os_id = ? ORDER BY ordem", (oid,))
    historico = await db.fetch_all(
        "SELECT h.*, u.nome AS usuario_nome FROM os_historico h LEFT JOIN usuarios u ON u.id = h.usuario_id WHERE h.os_id = ? ORDER BY h.criado_em",
        (oid,),
    )
    return {**row, "etapas": etapas, "historico": historico}


@app.post("/api/os", status_code=201)
async def create_os(body: OSIn, authorization: str | None = Header(None)):
    # RES-05: autenticação CONDICIONAL — veja MODULOS_EXTERNOS.md.
    # Módulos externos (aguada-web, xSeguranca, etc.) enviam modulo_origem sem token
    # de usuário interativo. Quando modulo_origem está presente, o path externo é
    # permitido sem auth. Quando ausente (usuário ERP), exige auth + guard de escrita.
    if not body.modulo_origem:
        user = await _require_auth(authorization)
        _require_escrita(user)
    oid = str(uuid.uuid4())
    codigo = await _gen_os_codigo()
    # CON-02 (D-03): lotação = override explícito do corpo; se ausente, deriva
    # da unidade do cargo do solicitante (cargos.usuario_id -> cargos.unidade_id),
    # espelhando o padrão já usado em list_unidades (main.py:1130-1137).
    lotacao_id = body.lotacao_id
    if not lotacao_id and body.solicitante_id:
        cargo = await db.fetch_one(
            "SELECT unidade_id FROM cargos WHERE usuario_id = ?", (body.solicitante_id,)
        )
        lotacao_id = cargo["unidade_id"] if cargo else None
    await db.execute(
        """INSERT INTO ordens_servico
           (id, codigo, titulo, descricao, tipo, prioridade, modulo_origem,
            solicitante_id, responsavel_id, local_id, data_prevista, custo_estimado, observacoes,
            departamento, lotacao_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (oid, codigo, body.titulo, body.descricao, body.tipo, body.prioridade,
         body.modulo_origem, body.solicitante_id, body.responsavel_id,
         body.local_id, body.data_prevista, body.custo_estimado, body.observacoes,
         body.departamento, lotacao_id),
    )
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs) VALUES (?,?,?,?)",
        (oid, None, "aberta", "OS criada"),
    )
    await _notify_os_responsavel(oid)
    return await get_os(oid)


async def _notify_os_responsavel(oid: str) -> None:
    """Best-effort: avisa o responsável no Telegram (card + botões de status).
    Silencioso se faltar token, chat_id ou der erro de rede — nunca quebra a OS."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    row = await db.fetch_one(
        "SELECT o.codigo, o.titulo, o.status, o.prioridade, u.telegram_chat_id AS chat "
        "FROM ordens_servico o LEFT JOIN usuarios u ON u.id = o.responsavel_id WHERE o.id = ?",
        (oid,),
    )
    if not row or not row["chat"]:
        return
    from tools.telegram_spike import build_send_params, card_os
    texto = card_os(row["codigo"], row["titulo"], row["status"], row["prioridade"])
    params = build_send_params(row["chat"], texto, oid)
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            await cli.post(f"https://api.telegram.org/bot{token}/sendMessage", data=params)
    except httpx.HTTPError as e:
        print(f"  (notify Telegram OS {oid} ignorado: {e})")


@app.put("/api/os/{oid}/status")
async def update_os_status(oid: str, body: OSStatusIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    row = await db.fetch_one("SELECT status FROM ordens_servico WHERE id = ?", (oid,))
    if not row:
        raise HTTPException(404, "OS não encontrada")
    extra: dict = {}
    if body.para_status == "concluida":
        extra["data_conclusao"] = date_now = datetime.utcnow().strftime("%Y-%m-%d")
    updates = "status = ?, atualizado_em = CURRENT_TIMESTAMP"
    params: list = [body.para_status]
    if extra.get("data_conclusao"):
        updates += ", data_conclusao = ?"
        params.append(extra["data_conclusao"])
    params.append(oid)
    await db.execute(f"UPDATE ordens_servico SET {updates} WHERE id = ?", tuple(params))
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) VALUES (?,?,?,?,?)",
        (oid, row["status"], body.para_status, body.obs, body.usuario_id),
    )
    # Debita estoque ao concluir (regra de negócio). Só na transição p/ concluída,
    # evita débito duplo se status já era concluída.
    if body.para_status == "concluida" and row["status"] != "concluida":
        await _debitar_estoque_os(oid, body.usuario_id)
    return await get_os(oid)


async def _debitar_estoque_os(oid: str, usuario_id: int | None) -> None:
    """Baixa do estoque os materiais do serviço da OS (catálogo). Idempotência:
    chamado só na transição p/ concluída. Materiais sem item de estoque (nome
    livre) são ignorados. Estoque insuficiente debita o disponível e anota a falta."""
    os_row = await db.fetch_one("SELECT servico_id FROM ordens_servico WHERE id = ?", (oid,))
    if not os_row or not os_row["servico_id"]:
        return
    materiais = await db.fetch_all(
        "SELECT material_id, qtd FROM catalogo_servico_materiais "
        "WHERE servico_id = ? AND material_id IS NOT NULL AND qtd > 0",
        (os_row["servico_id"],),
    )
    for m in materiais:
        item = await db.fetch_one("SELECT qtd_atual FROM estoque WHERE id = ?", (m["material_id"],))
        if not item:
            continue
        pedido = m["qtd"]
        debita = min(pedido, item["qtd_atual"])
        if debita <= 0:
            continue
        falta = pedido - debita
        obs = f"Consumo OS {oid}" + (f" (estoque insuficiente: faltaram {falta})" if falta else "")
        await db.execute("UPDATE estoque SET qtd_atual = qtd_atual - ? WHERE id = ?", (debita, m["material_id"]))
        await db.execute(
            "INSERT INTO estoque_movimentos (item_id, tipo, quantidade, os_id, usuario_id, obs) "
            "VALUES (?, 'saida', ?, ?, ?, ?)",
            (m["material_id"], debita, oid, usuario_id, obs),
        )


@app.post("/api/os/{oid}/etapas", status_code=201)
async def add_etapa(oid: str, body: EtapaIn):
    row = await db.fetch_one("SELECT id FROM ordens_servico WHERE id = ?", (oid,))
    if not row:
        raise HTTPException(404, "OS não encontrada")
    eid = await db.execute(
        "INSERT INTO os_etapas (os_id, titulo, ordem) VALUES (?,?,?)",
        (oid, body.titulo, body.ordem),
    )
    return await db.fetch_one("SELECT * FROM os_etapas WHERE id = ?", (eid,))


@app.patch("/api/os/{oid}/etapas/{eid}")
async def toggle_etapa(oid: str, eid: int, concluida: int = Query(..., ge=0, le=1)):
    row = await db.fetch_one("SELECT id FROM os_etapas WHERE id = ? AND os_id = ?", (eid, oid))
    if not row:
        raise HTTPException(404, "Etapa não encontrada")
    await db.execute("UPDATE os_etapas SET concluida = ? WHERE id = ?", (concluida, eid))
    return await db.fetch_one("SELECT * FROM os_etapas WHERE id = ?", (eid,))


# ── Estoque ───────────────────────────────────────────────────────────────────
@app.get("/api/estoque")
async def list_estoque(categoria: str | None = None, abaixo_minimo: int = 0):
    clauses, params = ["ativo = 1"], []
    if categoria:
        clauses.append("categoria = ?"); params.append(categoria)
    if abaixo_minimo:
        clauses.append("qtd_atual < qtd_minima")
    where = " AND ".join(clauses)
    return await db.fetch_all(f"SELECT * FROM estoque WHERE {where} ORDER BY categoria, nome", tuple(params))


@app.get("/api/estoque/{iid}")
async def get_estoque_item(iid: int):
    row = await db.fetch_one("SELECT * FROM estoque WHERE id = ?", (iid,))
    if not row:
        raise HTTPException(404, "Item não encontrado")
    movs = await db.fetch_all(
        "SELECT m.*, u.nome AS usuario_nome FROM estoque_movimentos m LEFT JOIN usuarios u ON u.id = m.usuario_id WHERE m.item_id = ? ORDER BY m.criado_em DESC LIMIT 50",
        (iid,),
    )
    return {**row, "movimentos": movs}


@app.post("/api/estoque", status_code=201)
async def create_estoque(body: EstoqueIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    iid = await db.execute(
        "INSERT INTO estoque (codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco_unitario, local_id, obs) VALUES (?,?,?,?,?,?,?,?,?)",
        (body.codigo, body.nome, body.categoria, body.unidade, body.qtd_atual, body.qtd_minima, body.preco_unitario, body.local_id, body.obs),
    )
    return await get_estoque_item(iid)


@app.put("/api/estoque/{iid}")
async def update_estoque(iid: int, body: EstoqueIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    await get_estoque_item(iid)
    await db.execute(
        "UPDATE estoque SET codigo=?, nome=?, categoria=?, unidade=?, qtd_minima=?, preco_unitario=?, local_id=?, obs=? WHERE id=?",
        (body.codigo, body.nome, body.categoria, body.unidade, body.qtd_minima, body.preco_unitario, body.local_id, body.obs, iid),
    )
    return await get_estoque_item(iid)


@app.get("/api/estoque/exportar/csv")
async def exportar_estoque_csv():
    rows = await db.fetch_all("SELECT * FROM estoque WHERE ativo = 1 ORDER BY categoria, nome")
    buf = io.StringIO()
    cols = ["id","codigo","nome","categoria","unidade","qtd_atual","qtd_minima","preco_unitario","obs"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k,"") for k in cols})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=estoque.csv"},
    )


# ── PMOC Refrigeração ─────────────────────────────────────────────────────────
class PmocRefrigIn(BaseModel):
    estado_operacional: str = "OP"
    obs: Optional[str] = None
    permanencia: int = 0
    criticidade: str = "MÉDIA"
    horas_dia: Optional[float] = None
    dias_semana: Optional[int] = None
    tensao_medida: Optional[float] = None
    corrente_medida: Optional[float] = None
    potencia_kw: Optional[float] = None
    quadro: Optional[str] = None
    disjuntor: Optional[str] = None
    cabo: Optional[str] = None
    gas_tipo: Optional[str] = None
    carga_g: Optional[float] = None
    pressao_medida: Optional[str] = None
    pressao_data: Optional[str] = None
    temp_evaporadora_m: Optional[str] = None
    temp_centro: Optional[str] = None
    temp_longe: Optional[str] = None
    ultima_manutencao: Optional[str] = None


class PmocRefrigCreateIn(PmocRefrigIn):
    ativo_id: Optional[str] = None     # se vazio, cria novo ativo
    local_id: Optional[int] = None
    # Campos para criar ativo novo quando ativo_id ausente
    ativo_tipo: str = "AC_SPLIT"        # AC_SPLIT | AC_JANELA | AC_PISO_TETO
    ativo_marca: Optional[str] = None
    ativo_nome: Optional[str] = None    # default: derivado de marca+btu+local
    ativo_pat: Optional[str] = None
    # Campos estruturais (não estão em PmocRefrigIn pois são imutáveis pós-import)
    est_idade: Optional[str] = None     # NOVA | SEMI | VELHA
    tensao_nominal: Optional[float] = None
    corrente_nominal: Optional[float] = None
    pressao_padrao: Optional[str] = None
    temp_evaporadora: Optional[str] = None
    temp_longe_padrao: Optional[str] = None
    patrimonio: Optional[str] = None
    data_instalacao: Optional[str] = None


_PMOC_REFRIG_SELECT = """
    SELECT p.*,
           a.nome AS ativo_nome, a.tipo AS ativo_tipo, a.subtipo AS ativo_marca,
           a.pat AS ativo_pat, a.uso_atual,
           l.nome AS local_nome, l.codigo AS local_codigo, l.area_m2,
           lp.nome AS predio_nome, lp.id AS predio_id,
           lz.nome AS zona_nome, lz.id AS zona_id
    FROM pmoc_refrigeracao p
    LEFT JOIN ativos a ON a.id = p.ativo_id
    LEFT JOIN locais l ON l.id = p.local_id
    LEFT JOIN locais lp ON lp.id = l.parent_id
    LEFT JOIN locais lz ON lz.id = lp.parent_id
"""


@app.get("/api/pmoc/refrigeracao/kpis")
async def pmoc_refrig_kpis():
    total = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao")
    op    = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao WHERE estado_operacional = 'OP'")
    inop  = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao WHERE estado_operacional = 'INOP'")
    crits = await db.fetch_all("SELECT criticidade, COUNT(*) AS n FROM pmoc_refrigeracao GROUP BY criticidade ORDER BY n DESC")
    return {
        "total": total["n"],
        "op": op["n"],
        "inop": inop["n"],
        "por_criticidade": {r["criticidade"]: r["n"] for r in crits},
    }


@app.get("/api/pmoc/refrigeracao")
async def list_pmoc_refrig(
    estado: str | None = None,
    criticidade: str | None = None,
    local_id: int | None = None,
    inop: int = 0,
):
    clauses, params = [], []
    if estado:
        clauses.append("p.estado_operacional = ?"); params.append(estado)
    elif inop:
        clauses.append("p.estado_operacional = 'INOP'")
    if criticidade:
        clauses.append("p.criticidade = ?"); params.append(criticidade)
    if local_id is not None:
        clauses.append("p.local_id = ?"); params.append(local_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return await db.fetch_all(
        f"{_PMOC_REFRIG_SELECT} {where} ORDER BY l.nome, a.nome",
        tuple(params),
    )


@app.get("/api/pmoc/refrigeracao/{pid}")
async def get_pmoc_refrig(pid: int):
    row = await db.fetch_one(
        f"{_PMOC_REFRIG_SELECT} WHERE p.id = ?", (pid,)
    )
    if not row:
        raise HTTPException(404, "Registro PMOC não encontrado")
    return row


@app.put("/api/pmoc/refrigeracao/{pid}")
async def update_pmoc_refrig(pid: int, body: PmocRefrigIn):
    row = await db.fetch_one("SELECT id, ativo_id FROM pmoc_refrigeracao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Registro PMOC não encontrado")
    await db.execute(
        """UPDATE pmoc_refrigeracao SET
               estado_operacional=?, obs=?, permanencia=?, criticidade=?,
               horas_dia=?, dias_semana=?,
               tensao_medida=?, corrente_medida=?, potencia_kw=?,
               quadro=?, disjuntor=?, cabo=?,
               gas_tipo=?, carga_g=?, pressao_medida=?, pressao_data=?,
               temp_evaporadora_m=?, temp_centro=?, temp_longe=?,
               ultima_manutencao=?, atualizado_em=CURRENT_TIMESTAMP
           WHERE id=?""",
        (
            body.estado_operacional, body.obs, body.permanencia, body.criticidade,
            body.horas_dia, body.dias_semana,
            body.tensao_medida, body.corrente_medida, body.potencia_kw,
            body.quadro, body.disjuntor, body.cabo,
            body.gas_tipo, body.carga_g, body.pressao_medida, body.pressao_data,
            body.temp_evaporadora_m, body.temp_centro, body.temp_longe,
            body.ultima_manutencao, pid,
        ),
    )
    if row["ativo_id"]:
        await db.execute(
            "UPDATE ativos SET ativo = ? WHERE id = ?",
            (1 if body.estado_operacional == "OP" else 0, row["ativo_id"]),
        )
    return await get_pmoc_refrig(pid)


@app.post("/api/pmoc/refrigeracao", status_code=201)
async def create_pmoc_refrig(body: PmocRefrigCreateIn):
    ativo_id = body.ativo_id
    if ativo_id:
        exists = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (ativo_id,))
        if not exists:
            raise HTTPException(400, f"ativo_id '{ativo_id}' não encontrado")
    else:
        row = await db.fetch_one(
            "SELECT id FROM ativos WHERE id LIKE 'hvac-%' ORDER BY CAST(SUBSTR(id, 6) AS INTEGER) DESC LIMIT 1"
        )
        next_seq = 1
        if row and row["id"]:
            try:
                next_seq = int(row["id"].split("-")[1]) + 1
            except (ValueError, IndexError):
                next_seq = 1
        ativo_id = f"hvac-{next_seq:03d}"
        while await db.fetch_one("SELECT 1 FROM ativos WHERE id = ?", (ativo_id,)):
            next_seq += 1
            ativo_id = f"hvac-{next_seq:03d}"

        nome_default = body.ativo_nome
        if not nome_default:
            partes = ["AC", body.ativo_marca or "", body.ativo_tipo.replace("AC_", "")]
            nome_default = " ".join(p for p in partes if p).strip()
        await db.execute(
            "INSERT INTO ativos (id, tipo, subtipo, categoria, nome, pat, ativo, unidade_uso)"
            " VALUES (?, ?, ?, 'climatizacao', ?, ?, ?, 'meses')",
            (
                ativo_id, body.ativo_tipo, body.ativo_marca,
                nome_default, body.ativo_pat,
                1 if body.estado_operacional == "OP" else 0,
            ),
        )

    cur = await db.execute(
        """INSERT INTO pmoc_refrigeracao
           (ativo_id, local_id, estado_operacional, est_idade, obs,
            permanencia, criticidade, horas_dia, dias_semana,
            tensao_nominal, tensao_medida, corrente_nominal, corrente_medida, potencia_kw,
            quadro, disjuntor, cabo,
            gas_tipo, carga_g, pressao_padrao, pressao_medida, pressao_data,
            temp_evaporadora, temp_evaporadora_m, temp_centro, temp_longe,
            patrimonio, data_instalacao, ultima_manutencao)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ativo_id, body.local_id, body.estado_operacional, body.est_idade, body.obs,
            body.permanencia, body.criticidade, body.horas_dia, body.dias_semana,
            body.tensao_nominal, body.tensao_medida, body.corrente_nominal, body.corrente_medida, body.potencia_kw,
            body.quadro, body.disjuntor, body.cabo,
            body.gas_tipo, body.carga_g, body.pressao_padrao, body.pressao_medida, body.pressao_data,
            body.temp_evaporadora, body.temp_evaporadora_m, body.temp_centro, body.temp_longe,
            body.patrimonio, body.data_instalacao, body.ultima_manutencao,
        ),
    )
    return await get_pmoc_refrig(cur)


@app.delete("/api/pmoc/refrigeracao/{pid}")
async def delete_pmoc_refrig(pid: int, arquivar_ativo: int = 0):
    row = await db.fetch_one("SELECT ativo_id FROM pmoc_refrigeracao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Registro PMOC não encontrado")
    await db.execute("DELETE FROM pmoc_refrigeracao WHERE id = ?", (pid,))
    if arquivar_ativo and row["ativo_id"]:
        await db.execute("UPDATE ativos SET ativo = 0 WHERE id = ?", (row["ativo_id"],))
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# PMOC genérico: Transportes (viaturas+embarcações) e Corte (máquinas de corte)
# Mesmo molde de refrigeração: ficha de detalhe 1:1 com ativos, editável (whitelist).
# OS preventiva usa o fluxo genérico POST /api/os (servico_id) + débito ao concluir.
# ════════════════════════════════════════════════════════════════════════════
_TRANSP_EDIT = {
    "estado_operacional", "est_idade", "criticidade", "obs", "renavam",
    "licenciamento_ate", "seguro_ate", "registro_naval", "combustivel", "tanque_l",
    "oleo_ultima_uso", "pneus_estado", "bateria_estado", "casco_estado",
    "motor_obs", "data_aquisicao", "ultima_manutencao",
}
_CORTE_EDIT = {
    "estado_operacional", "est_idade", "criticidade", "obs", "motor_tempos",
    "combustivel", "oleo_tipo", "oleo_ultima_uso", "ferramenta_corte",
    "data_aquisicao", "ultima_manutencao",
}
_FONO_EDIT = {
    "estado_operacional", "est_idade", "criticidade", "obs", "potencia_w",
    "impedancia", "tensao_linha", "data_instalacao", "ultima_manutencao",
}


async def _pmoc_ficha_list(tabela: str) -> list[dict]:
    """Lista fichas PMOC de uma categoria (detalhe + ativo + local). Mesmo shape
    do list_refrigeracao para a página de Manutenção consumir."""
    return await db.fetch_all(
        f"""
        SELECT p.*,
               a.nome AS ativo_nome, a.tipo AS ativo_tipo, a.subtipo AS ativo_subtipo,
               a.categoria AS ativo_categoria, a.pat AS ativo_pat, a.placa AS ativo_placa,
               a.loc AS loc_txt, a.uso_atual, a.unidade_uso, a.ativo AS ativo_ativo,
               l.nome AS local_nome
        FROM {tabela} p
        JOIN ativos a      ON a.id = p.ativo_id
        LEFT JOIN locais l ON l.id = p.local_id
        ORDER BY a.nome
        """
    )


async def _pmoc_ficha_edit(tabela: str, whitelist: set, ativo_id: str, body: dict) -> dict:
    """Edita ficha PMOC (campos da tabela detalhe + subset de ativos). Whitelist."""
    row = await db.fetch_one(f"SELECT ativo_id FROM {tabela} WHERE ativo_id = ?", (ativo_id,))
    if not row:
        raise HTTPException(404, "Ficha não encontrada")
    det = [(k, v) for k, v in body.items() if k in whitelist]
    if det:
        sets = ", ".join(f"{k} = ?" for k, _ in det)
        await db.execute(
            f"UPDATE {tabela} SET {sets}, atualizado_em = CURRENT_TIMESTAMP WHERE ativo_id = ?",
            [v for _, v in det] + [ativo_id],
        )
    ativo = [(k, v) for k, v in body.items() if k in _ATIVO_EDIT]
    if ativo:
        sets = ", ".join(f"{k} = ?" for k, _ in ativo)
        await db.execute(
            f"UPDATE ativos SET {sets} WHERE id = ?", [v for _, v in ativo] + [ativo_id]
        )
    return await db.fetch_one(
        f"SELECT p.*, a.nome AS ativo_nome FROM {tabela} p JOIN ativos a ON a.id = p.ativo_id WHERE p.ativo_id = ?",
        (ativo_id,),
    )


@app.get("/api/pmoc/transportes")
async def list_transportes():
    return await _pmoc_ficha_list("pmoc_transportes")


@app.put("/api/pmoc/transportes/{ativo_id}")
async def update_transportes(ativo_id: str, body: dict):
    return await _pmoc_ficha_edit("pmoc_transportes", _TRANSP_EDIT, ativo_id, body)


@app.get("/api/pmoc/corte")
async def list_corte():
    return await _pmoc_ficha_list("pmoc_corte")


@app.put("/api/pmoc/corte/{ativo_id}")
async def update_corte(ativo_id: str, body: dict):
    return await _pmoc_ficha_edit("pmoc_corte", _CORTE_EDIT, ativo_id, body)


@app.get("/api/pmoc/fonoclama")
async def list_fonoclama():
    return await _pmoc_ficha_list("pmoc_fonoclama")


@app.put("/api/pmoc/fonoclama/{ativo_id}")
async def update_fonoclama(ativo_id: str, body: dict):
    return await _pmoc_ficha_edit("pmoc_fonoclama", _FONO_EDIT, ativo_id, body)


# ── Vencimentos: o que está por vencer (plano↔tipo + uso_atual do ativo) ────────
@app.get("/api/manutencao/vencimentos")
async def manutencao_vencimentos(categoria: str | None = None):
    """Para cada ativo, resolve o plano pelo tipo (aplicavel_tipos) e calcula o
    próximo vencimento por uso (h/km) e por tempo (dias). Disparo por_tempo usa
    MAX(data) de manut_registros como base; sem registro, nenhum alerta é emitido.
    Plano↔tipo É a atribuição (decisão do modelo)."""
    import json, math
    planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
    plano_by_tipo: dict[str, list] = {}
    for p in planos:
        tipos = []
        try:
            tipos = json.loads(p["aplicavel_tipos"] or "[]")
        except Exception:
            tipos = []
        if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
            tipos.append(p["tipo_codigo"])
        for t in tipos:
            plano_by_tipo.setdefault(t, []).append(p)
    q = "SELECT id, nome, tipo, categoria, uso_atual, unidade_uso FROM ativos WHERE ativo = 1"
    params: list = []
    if categoria:
        q += " AND categoria = ?"; params.append(categoria)
    ativos = await db.fetch_all(q, tuple(params))
    out: list[dict] = []
    for a in ativos:
        for p in plano_by_tipo.get(a["tipo"], []):
            itens = await db.fetch_all(
                "SELECT i.frequencia, i.servico_id, s.nome FROM catalogo_plano_itens i "
                "JOIN catalogo_servicos s ON s.id = i.servico_id WHERE i.plano_id = ? ORDER BY i.seq",
                (p["id"],),
            )
            for it in itens:
                raw = it["frequencia"] or p["frequencia"]
                if not raw:
                    continue
                try:
                    f = json.loads(raw)
                except Exception:
                    continue
                if f.get("tipo") == "por_tempo":
                    valor = f.get("valor")
                    if not valor:
                        continue
                    ultima = await db.fetch_one(
                        "SELECT MAX(data) AS d FROM manut_registros WHERE ativo_id = ?",
                        (a["id"],),
                    )
                    ultima_data = ultima["d"] if ultima and ultima["d"] else None
                    if not ultima_data:
                        continue  # sem base de data → sem alerta
                    try:
                        dt_ultima = date.fromisoformat(ultima_data)
                    except ValueError:
                        continue
                    dt_prox = dt_ultima + timedelta(days=int(valor))
                    falta_dias = (dt_prox - date.today()).days
                    if falta_dias <= int(valor) * 0.15:
                        out.append({
                            "ativo_id": a["id"], "ativo_nome": a["nome"], "tipo": a["tipo"],
                            "categoria": a["categoria"], "plano_id": p["id"], "plano_nome": p["nome"],
                            "servico_id": it["servico_id"], "servico": it["nome"],
                            "intervalo": int(valor), "unidade": "dias",
                            "uso_atual": None, "proximo": dt_prox.isoformat(),
                            "falta": falta_dias, "pct": None, "status": "warn",
                        })
                    continue  # por_tempo never falls into por_uso path
                elif f.get("tipo") != "por_uso" or not f.get("valor"):
                    continue
                iv = f["valor"]; uso = a["uso_atual"] or 0
                prox = (math.floor(uso / iv) + 1) * iv
                falta = prox - uso
                st = "warn" if falta <= iv * 0.15 else "ok"
                out.append({
                    "ativo_id": a["id"], "ativo_nome": a["nome"], "tipo": a["tipo"],
                    "categoria": a["categoria"], "plano_id": p["id"], "plano_nome": p["nome"],
                    "servico_id": it["servico_id"], "servico": it["nome"],
                    "intervalo": iv, "unidade": f.get("unidade"), "uso_atual": uso,
                    "proximo": prox, "falta": falta, "pct": round((uso % iv) / iv * 100),
                    "status": st,
                })
    out.sort(key=lambda x: x["falta"])
    return out


@app.post("/api/manutencao/os-preventiva", status_code=201)
async def gerar_os_servico(body: dict, authorization: str | None = Header(None)):
    """Gera OS preventiva para (ativo, serviço) — usada pela tela de Vencimentos.
    Liga servico_id (débito de estoque ao concluir vem do #1). Etapas = descrição."""
    user = await _require_auth(authorization)
    _require_escrita(user)
    ativo_id = body.get("ativo_id"); servico_id = body.get("servico_id")
    if not ativo_id or not servico_id:
        raise HTTPException(400, "ativo_id e servico_id obrigatórios")
    ativo = await db.fetch_one("SELECT id, nome, local_id FROM ativos WHERE id = ?", (ativo_id,))
    if not ativo:
        raise HTTPException(404, "Ativo não encontrado")
    servico = await db.fetch_one("SELECT id, nome, descricao FROM catalogo_servicos WHERE id = ?", (servico_id,))
    if not servico:
        raise HTTPException(404, "Serviço não encontrado")
    oid = str(uuid.uuid4())
    codigo = await _gen_os_codigo()
    await db.execute(
        "INSERT INTO ordens_servico (id, codigo, titulo, descricao, tipo, prioridade, modulo_origem, local_id, ativo_id, servico_id) "
        "VALUES (?,?,?,?, 'preventiva', 'media', 'manutencao', ?, ?, ?)",
        (oid, codigo, f"Preventiva — {servico['nome']} · {ativo['nome']}",
         servico["nome"], ativo.get("local_id"), ativo_id, servico_id),
    )
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs) VALUES (?,?,?,?)",
        (oid, None, "aberta", "OS preventiva gerada de vencimento"),
    )
    desc = (servico.get("descricao") or "")
    for i, t in enumerate([x.strip() for x in desc.split(" ; ") if x.strip()]):
        await db.execute("INSERT INTO os_etapas (os_id, titulo, ordem) VALUES (?,?,?)", (oid, t, i))
    return await get_os(oid)


async def _seed_pmoc_frota_corte_if_empty() -> None:
    """Backfill: cria fichas pmoc_transportes/pmoc_corte para ativos existentes
    que ainda não têm ficha. Idempotente (só insere o que falta)."""
    # Transportes: viaturas + embarcações
    novos = await db.fetch_all(
        "SELECT id FROM ativos WHERE categoria IN ('viaturas','embarcacoes','frota_terrestre','frota_naval') "
        "AND id NOT IN (SELECT ativo_id FROM pmoc_transportes WHERE ativo_id IS NOT NULL)"
    )
    for a in novos:
        await db.execute("INSERT INTO pmoc_transportes (ativo_id) VALUES (?)", (a["id"],))
    # Corte: máquinas de corte
    novos_c = await db.fetch_all(
        "SELECT id FROM ativos WHERE categoria = 'maquinas_corte' "
        "AND id NOT IN (SELECT ativo_id FROM pmoc_corte WHERE ativo_id IS NOT NULL)"
    )
    for a in novos_c:
        await db.execute("INSERT INTO pmoc_corte (ativo_id) VALUES (?)", (a["id"],))
    # Fonoclama
    novos_f = await db.fetch_all(
        "SELECT id FROM ativos WHERE categoria = 'fonoclama' "
        "AND id NOT IN (SELECT ativo_id FROM pmoc_fonoclama WHERE ativo_id IS NOT NULL)"
    )
    for a in novos_f:
        await db.execute("INSERT INTO pmoc_fonoclama (ativo_id) VALUES (?)", (a["id"],))
    if novos or novos_c or novos_f:
        print(f"  seed PMOC: +{len(novos)} transportes, +{len(novos_c)} corte, +{len(novos_f)} fonoclama")


# Inventário inicial fonoclama (legado de xFonoclama/fonoclama.html)
_FONOCLAMA_ATIVOS = [
    ("fono01", "AMPLIFICADOR", "AMP-CPD-01", "Rack da central de sonorização — CPD"),
    ("fono02", "AMPLIFICADOR", "AMP-COM-02", "Amplificador redundante — Centro de operações"),
    ("fono03", "CONSOLE", "CON-MESA-01", "Console principal de avisos gerais"),
    ("fono04", "CONSOLE", "MIC-DESP-01", "Microfone de despacho — sala de serviço"),
    ("fono05", "ALTO_FALANTE", "AF-CORR-01", "Corneta corredor bloco administrativo"),
    ("fono06", "ALTO_FALANTE", "AF-PATIO-02", "Corneta pátio operacional"),
    ("fono07", "ALTO_FALANTE", "AF-CAIS-03", "Corneta área do cais"),
    ("fono08", "LINHA_70V", "L70-SETOR-A", "Linha de distribuição 70V setor administrativo"),
    ("fono09", "LINHA_70V", "L70-SETOR-B", "Linha de distribuição 70V setor operacional"),
    ("fono10", "SIRENE", "SIR-EMG-01", "Sirene de emergência do pátio principal"),
]
_FONOCLAMA_PECAS = [
    ("Conector XLR", "un", "audio"), ("Cabo XLR", "m", "audio"),
    ("Terminal de audio", "un", "audio"), ("Limpador de contato", "un", "quimico"),
    ("Fusivel", "un", "eletric"), ("Cooler 12V", "un", "eletric"),
    ("Cabo 2x1,5mm", "m", "audio"), ("Rele", "un", "eletric"),
    ("Suporte metalico", "un", "fixacao"), ("Conector de linha", "un", "audio"),
]


async def _seed_fonoclama_if_empty() -> None:
    """Cria ativos e peças de fonoclama se ainda não existirem (idempotente).
    Os planos preventivos já vêm do catálogo (_MANUT_TIPOS_PLANOS)."""
    existe = await db.fetch_one("SELECT 1 FROM ativos WHERE categoria = 'fonoclama' LIMIT 1")
    if not existe:
        for aid, tipo, nome, obs in _FONOCLAMA_ATIVOS:
            await db.execute(
                "INSERT OR IGNORE INTO ativos (id, tipo, categoria, nome, obs, uso_atual, unidade_uso, ativo) "
                "VALUES (?, ?, 'fonoclama', ?, ?, 0, 'h', 1)",
                (aid, tipo, nome, obs),
            )
        print(f"  seed fonoclama: +{len(_FONOCLAMA_ATIVOS)} ativos")
    for nome, un, cat in _FONOCLAMA_PECAS:
        ja = await db.fetch_one("SELECT 1 FROM estoque WHERE nome = ? LIMIT 1", (nome,))
        if not ja:
            await db.execute(
                "INSERT INTO estoque (nome, categoria, unidade, qtd_atual, qtd_minima, ativo) "
                "VALUES (?, 'consumivel', ?, 0, 1, 1)",
                (nome, un),
            )


@app.post("/api/estoque/{iid}/movimentos", status_code=201)
async def create_movimento(iid: int, body: MovimentoIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    item = await db.fetch_one("SELECT qtd_atual FROM estoque WHERE id = ?", (iid,))
    if not item:
        raise HTTPException(404, "Item não encontrado")
    if body.tipo == "entrada":
        nova_qtd = item["qtd_atual"] + body.quantidade
    elif body.tipo == "saida":
        nova_qtd = item["qtd_atual"] - body.quantidade
        if nova_qtd < 0:
            raise HTTPException(400, "Quantidade insuficiente em estoque")
    else:  # ajuste
        nova_qtd = body.quantidade
    await db.execute("UPDATE estoque SET qtd_atual = ? WHERE id = ?", (nova_qtd, iid))
    mid = await db.execute(
        "INSERT INTO estoque_movimentos (item_id, tipo, quantidade, os_id, usuario_id, obs, documento, fornecedor) VALUES (?,?,?,?,?,?,?,?)",
        (iid, body.tipo, body.quantidade, body.os_id, body.usuario_id, body.obs, body.documento, body.fornecedor),
    )
    return await db.fetch_one("SELECT * FROM estoque_movimentos WHERE id = ?", (mid,))
