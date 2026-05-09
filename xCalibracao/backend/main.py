import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db_calibracao import CalibracaoDB

# --- Configuração ---
XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")
db = CalibracaoDB()
CERTIFICADOS_DIR = Path(__file__).resolve().parent / "certificados"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    CERTIFICADOS_DIR.mkdir(exist_ok=True)
    yield

app = FastAPI(title="xCalibracao API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos ---

class InstrumentoCreate(BaseModel):
    tag: str
    nome: str
    modelo: Optional[str] = None
    fabricante: Optional[str] = None
    num_serie: Optional[str] = None
    faixa_medicao: Optional[str] = None
    precisao: Optional[str] = None
    periodicidade_meses: int = 12

class CertificadoCreate(BaseModel):
    instrumento_id: int
    numero_certificado: str
    data_calibracao: str
    data_vencimento: str
    laboratorio: Optional[str] = None
    resultado: str = "aprovado"
    observacoes: Optional[str] = None

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok", "module": "xCalibracao"}

# --- Instrumentos ---

@app.get("/api/v1/instrumentos")
async def list_instrumentos():
    return await db.fetch_all("SELECT * FROM instrumentos")

@app.post("/api/v1/instrumentos")
async def create_instrumento(payload: InstrumentoCreate):
    try:
        instr_id = await db.execute(
            "INSERT INTO instrumentos (tag, nome, modelo, fabricante, num_serie, faixa_medicao, precisao, periodicidade_meses) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (payload.tag, payload.nome, payload.modelo, payload.fabricante, payload.num_serie, payload.faixa_medicao, payload.precisao, payload.periodicidade_meses)
        )
        return {"id": instr_id, **payload.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Certificados ---

@app.get("/api/v1/instrumentos/{instrumento_id}/certificados")
async def list_certificados(instrumento_id: int):
    return await db.fetch_all(
        "SELECT * FROM certificados WHERE instrumento_id = ? ORDER BY data_calibracao DESC",
        (instrumento_id,)
    )

@app.post("/api/v1/certificados")
async def create_certificado(payload: CertificadoCreate):
    try:
        cert_id = await db.execute(
            "INSERT INTO certificados (instrumento_id, numero_certificado, data_calibracao, data_vencimento, laboratorio, resultado, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (payload.instrumento_id, payload.numero_certificado, payload.data_calibracao, payload.data_vencimento, payload.laboratorio, payload.resultado, payload.observacoes)
        )
        return {"id": cert_id, **payload.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/vencimentos")
async def list_vencimentos():
    """Retorna instrumentos com calibração vencendo nos próximos 30 dias."""
    return await db.fetch_all("SELECT * FROM v_vencimentos_proximos WHERE dias_para_vencer < 30")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
