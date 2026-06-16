#!/usr/bin/env python3
"""Spike: comunicado via Telegram + botão de feedback que grava etapa na OS.

Prova o loop ponta-a-ponta sem infra: long-polling (getUpdates), sem URL pública.
Só stdlib — nada de novas deps.

    # 1. crie um bot no @BotFather, pegue o token, e exporte (ou ponha no .env):
    export TELEGRAM_BOT_TOKEN=123456:ABC...
    # 2. descubra seu chat_id: mande qualquer msg pro bot, então:
    python tools/telegram_spike.py whoami
    # 3. envie um comunicado amarrado a uma OS, com botão "Concluí":
    python tools/telegram_spike.py send <chat_id> <os_id> "Trocar filtro do AC-12"
    # 4. fique ouvindo; ao clicar no botão, grava etapa concluida=1 na OS:
    python tools/telegram_spike.py listen

ponytail: o botão grava direto no core.db via sqlite3 (zero auth/servidor).
Na versão real, trocar record_etapa() por POST /api/os/{id}/etapas autenticado,
e mapear chat_id -> matrícula numa coluna usuarios.telegram_chat_id.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"
CB_PREFIX = "done:"  # callback_data = "done:<os_id>"


def _load_dotenv(path: str = ".env") -> None:
    """Carrega KEY=VAL do .env se existir (sem dep externa)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _token() -> str:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        sys.exit("ERRO: defina TELEGRAM_BOT_TOKEN (export ou .env).")
    return tok


def call(method: str, params: dict) -> dict:
    """POST à Telegram Bot API. Retorna o JSON decodificado."""
    url = API.format(token=_token(), method=method)
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=40) as r:
        return json.loads(r.read())


def ack(method: str, params: dict) -> None:
    """Call best-effort: ACKs de UI (answerCallbackQuery/editMessageText) podem
    dar 400 (query velha, texto idêntico) — não devem derrubar o listener."""
    try:
        call(method, params)
    except urllib.error.HTTPError as e:
        print(f"  (ack {method} ignorado: {e})")


# ── helpers puros (testáveis sem rede) ────────────────────────────────────────

def build_send_params(chat_id: str, text: str, os_id: str) -> dict:
    """Monta o payload de sendMessage com botão inline de feedback."""
    keyboard = {"inline_keyboard": [[{"text": "✅ Concluí", "callback_data": CB_PREFIX + os_id}]]}
    return {"chat_id": chat_id, "text": text, "reply_markup": json.dumps(keyboard)}


def parse_callback(data: str) -> str | None:
    """Extrai o os_id de um callback_data 'done:<os_id>', senão None."""
    if data and data.startswith(CB_PREFIX):
        return data[len(CB_PREFIX):]
    return None


# ── persistência (spike: sqlite direto) ───────────────────────────────────────

def record_etapa(db_path: str, os_id: str) -> int | None:
    """Insere etapa concluída na OS. Retorna o id, ou None se a OS não existe."""
    conn = sqlite3.connect(db_path)
    try:
        if not conn.execute("SELECT 1 FROM ordens_servico WHERE id=?", (os_id,)).fetchone():
            return None
        cur = conn.execute(
            "INSERT INTO os_etapas (os_id, titulo, concluida) VALUES (?,?,1)",
            (os_id, "Concluído via Telegram"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── comandos ──────────────────────────────────────────────────────────────────

def cmd_send(chat_id: str, os_id: str, text: str) -> None:
    res = call("sendMessage", build_send_params(chat_id, text, os_id))
    print("OK" if res.get("ok") else f"FALHOU: {res}")


def cmd_whoami() -> None:
    """Mostra chat_ids de quem mandou msg recente pro bot."""
    res = call("getUpdates", {"timeout": 0})
    seen = {}
    for u in res.get("result", []):
        msg = u.get("message") or u.get("callback_query", {}).get("message", {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            seen[chat["id"]] = chat.get("first_name") or chat.get("title") or "?"
    if not seen:
        print("Nenhuma msg recente. Mande algo pro bot e rode de novo.")
    for cid, nome in seen.items():
        print(f"chat_id={cid}  ({nome})")


def cmd_listen(db_path: str) -> None:
    print(f"Ouvindo... (Ctrl-C p/ sair) DB={db_path}")
    offset = None
    while True:
        params = {"timeout": 25}
        if offset is not None:
            params["offset"] = offset
        res = call("getUpdates", params)
        for u in res.get("result", []):
            offset = u["update_id"] + 1
            cq = u.get("callback_query")
            if not cq:
                continue
            os_id = parse_callback(cq.get("data", ""))
            if not os_id:
                continue
            eid = record_etapa(db_path, os_id)
            if eid:
                ack("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "Feedback registrado ✅"})
                ack("editMessageText", {
                    "chat_id": cq["message"]["chat"]["id"],
                    "message_id": cq["message"]["message_id"],
                    "text": cq["message"]["text"] + "\n\n☑ Concluído (registrado)",
                })
                print(f"OS {os_id}: etapa {eid} gravada")
            else:
                ack("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "OS não encontrada"})
                print(f"OS {os_id}: não encontrada")


def selftest() -> None:
    p = build_send_params("42", "oi", "os-9")
    assert p["chat_id"] == "42"
    kb = json.loads(p["reply_markup"])
    assert kb["inline_keyboard"][0][0]["callback_data"] == "done:os-9"
    assert parse_callback("done:os-9") == "os-9"
    assert parse_callback("ruido") is None
    assert parse_callback("") is None
    print("selftest OK")


def main(argv: list[str]) -> None:
    _load_dotenv()
    db_path = os.environ.get("DB_PATH", "./data/core.db")
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "send" and len(argv) == 5:
        cmd_send(argv[2], argv[3], argv[4])
    elif cmd == "whoami":
        cmd_whoami()
    elif cmd == "listen":
        cmd_listen(db_path)
    elif cmd == "selftest":
        selftest()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
