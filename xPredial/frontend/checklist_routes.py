"""
checklist_routes.py
===================
Rotas adicionais para o módulo de Checklist com Matriz GUT.
Registrar no backend/main.py:

    from checklist_routes import router as checklist_router
    app.include_router(checklist_router, prefix="/api/v1")

Depende de: backend/db_predial.py (PredialDB)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os

router = APIRouter(tags=["checklist"])

DB_PATH = os.environ.get("PREDIAL_DB", "data/predial.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schemas ────────────────────────────────────────────────────────────────────

class ItemGUTUpdate(BaseModel):
    g: int = 0            # Gravidade  1|3|6|8|10
    u: int = 0            # Urgência   1|3|6|8|10
    t: int = 0            # Tendência  1|3|6|8|10
    presente: int = 0     # 0=não verificado, 1=conforme, 2=não conforme
    local_ref: Optional[str] = None
    foto_ref: Optional[str] = None
    observacao: Optional[str] = None
    condicao: Optional[str] = None   # ok|atencao|critico (derivado ou manual)


class ItemCopiarTemplate(BaseModel):
    template_id: int
    sistemas: Optional[List[str]] = None   # None = todos os sistemas


# ── Helpers ────────────────────────────────────────────────────────────────────

def gut_to_condicao(gut_total: int) -> str:
    if gut_total == 0:
        return "ok"
    if gut_total <= 100:
        return "ok"
    if gut_total <= 400:
        return "atencao"
    return "critico"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/checklist/templates")
def list_templates(tipo_local: Optional[str] = None):
    """Lista todos os templates de checklist disponíveis."""
    conn = get_conn()
    try:
        if tipo_local:
            rows = conn.execute(
                "SELECT * FROM checklist_templates WHERE ativo=1 AND (tipo_local=? OR tipo_local IS NULL)",
                (tipo_local,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM checklist_templates WHERE ativo=1"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/checklist/templates/{template_id}/itens")
def list_template_itens(
    template_id: int,
    sistema: Optional[str] = None
):
    """Lista itens de um template, opcionalmente filtrando por sistema."""
    conn = get_conn()
    try:
        if sistema:
            rows = conn.execute(
                "SELECT * FROM checklist_template_items WHERE template_id=? AND sistema=? ORDER BY sistema, subsistema, ordem",
                (template_id, sistema)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY sistema, subsistema, ordem",
                (template_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/checklist/templates/{template_id}/sistemas")
def list_sistemas(template_id: int):
    """Retorna a lista de sistemas disponíveis num template."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT DISTINCT sistema, COUNT(*) as total
               FROM checklist_template_items
               WHERE template_id=?
               GROUP BY sistema ORDER BY sistema""",
            (template_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/inspecoes/{inspecao_id}/copiar-template")
def copiar_template_para_inspecao(inspecao_id: int, body: ItemCopiarTemplate):
    """
    Copia itens do template para a inspeção.
    Se sistemas=['estrutura','cobertura'], copia somente esses.
    Seguro para re-executar: usa INSERT OR IGNORE por (inspecao_id, template_item_id).
    """
    conn = get_conn()
    try:
        # Verificar se inspeção existe
        insp = conn.execute("SELECT id, status FROM inspecoes WHERE id=?", (inspecao_id,)).fetchone()
        if not insp:
            raise HTTPException(404, f"Inspeção {inspecao_id} não encontrada")
        if insp["status"] not in ("planejada", "em_execucao"):
            raise HTTPException(400, f"Inspeção com status '{insp['status']}' não aceita novos itens")

        # Verificar se template existe
        tpl = conn.execute("SELECT id FROM checklist_templates WHERE id=?", (body.template_id,)).fetchone()
        if not tpl:
            raise HTTPException(404, f"Template {body.template_id} não encontrado")

        # Buscar itens do template
        if body.sistemas:
            placeholders = ",".join("?" * len(body.sistemas))
            itens = conn.execute(
                f"SELECT * FROM checklist_template_items WHERE template_id=? AND sistema IN ({placeholders}) ORDER BY sistema, subsistema, ordem",
                [body.template_id, *body.sistemas]
            ).fetchall()
        else:
            itens = conn.execute(
                "SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY sistema, subsistema, ordem",
                (body.template_id,)
            ).fetchall()

        # Verificar se inspecao_itens tem colunas GUT
        info = conn.execute("PRAGMA table_info(inspecao_itens)").fetchall()
        colunas = {row[1] for row in info}
        has_gut = "g" in colunas

        inseridos = 0
        ignorados = 0
        for item in itens:
            # Montar descricao da condição no formato do sistema
            descricao = item["descricao"]
            if item["subsistema"]:
                descricao = f"[{item['subsistema'].upper()}] {descricao}"
            categoria = f"{item['sistema']}"

            try:
                if has_gut:
                    conn.execute("""
                        INSERT INTO inspecao_itens
                            (inspecao_id, descricao, categoria, condicao, g, u, t, gut_total, presente, item_origem)
                        VALUES (?, ?, ?, 'ok', 0, 0, 0, 0, 0, 'template')
                    """, (inspecao_id, descricao, categoria))
                else:
                    conn.execute("""
                        INSERT INTO inspecao_itens (inspecao_id, descricao, categoria, condicao)
                        VALUES (?, ?, ?, 'ok')
                    """, (inspecao_id, descricao, categoria))
                inseridos += 1
            except sqlite3.IntegrityError:
                ignorados += 1

        conn.commit()
        return {
            "inspecao_id": inspecao_id,
            "template_id": body.template_id,
            "inseridos": inseridos,
            "ignorados": ignorados,
        }
    finally:
        conn.close()


@router.put("/inspecoes/{inspecao_id}/itens/{item_id}/gut")
def update_item_gut(inspecao_id: int, item_id: int, body: ItemGUTUpdate):
    """Atualiza os valores GUT de um item de inspeção."""
    conn = get_conn()
    try:
        item = conn.execute(
            "SELECT id FROM inspecao_itens WHERE id=? AND inspecao_id=?",
            (item_id, inspecao_id)
        ).fetchone()
        if not item:
            raise HTTPException(404, "Item não encontrado")

        gut_total = body.g * body.u * body.t
        condicao = body.condicao or gut_to_condicao(gut_total)

        conn.execute("""
            UPDATE inspecao_itens SET
                g=?, u=?, t=?, gut_total=?, presente=?,
                local_ref=?, foto_ref=?, condicao=?
            WHERE id=? AND inspecao_id=?
        """, (body.g, body.u, body.t, gut_total, body.presente,
              body.local_ref, body.foto_ref, condicao,
              item_id, inspecao_id))
        conn.commit()
        return {"id": item_id, "gut_total": gut_total, "condicao": condicao}
    finally:
        conn.close()


@router.get("/inspecoes/{inspecao_id}/prioridades")
def get_prioridades(inspecao_id: int):
    """
    Retorna itens da inspeção ordenados por GUT total (maior = mais crítico).
    Exclui itens com GUT=0 (não inspecionados ou conformes sem problema).
    """
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, descricao, categoria, condicao,
                   g, u, t, gut_total, local_ref, foto_ref, presente, observacao
            FROM inspecao_itens
            WHERE inspecao_id=? AND gut_total > 0
            ORDER BY gut_total DESC
        """, (inspecao_id,)).fetchall()

        total_critico = sum(1 for r in rows if r["condicao"] == "critico")
        total_atencao = sum(1 for r in rows if r["condicao"] == "atencao")

        return {
            "inspecao_id": inspecao_id,
            "total_nao_conformes": len(rows),
            "total_critico": total_critico,
            "total_atencao": total_atencao,
            "itens": [dict(r) for r in rows],
        }
    finally:
        conn.close()
