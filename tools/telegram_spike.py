#!/usr/bin/env python3
"""Bot Telegram p/ Ordens de Serviço: notifica responsável + botões de status.

Loop ponta-a-ponta sem infra: long-polling (getUpdates), sem URL pública.
Só stdlib — nada de novas deps.

    # 1. crie um bot no @BotFather, pegue o token, exporte (ou ponha no .env):
    export TELEGRAM_BOT_TOKEN=123456:ABC...
    # 2. descubra chat_ids de quem mandou msg pro bot:
    python tools/telegram_spike.py whoami
    # 3. vincule um chat_id a uma matrícula (autoria no histórico + notificações):
    python tools/telegram_spike.py link <chat_id> <matricula>
    # 4. notifique o responsável de uma OS (manda card + botões de status):
    python tools/telegram_spike.py notify <os_id>
    #    ...ou envie pra um chat_id avulso:
    python tools/telegram_spike.py send <chat_id> <os_id>
    # 5. fique ouvindo; clicar num botão muda ordens_servico.status e grava
    #    os_historico (status_de→status_para + autor resolvido pelo chat_id):
    python tools/telegram_spike.py listen

ponytail: grava direto no core.db via sqlite3 (zero auth/servidor). Na versão
real, trocar set_status()/notificar por POST /api/os/{id}/status autenticado.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"
CB_PREFIX = "os:"  # callback_data = "os:<status>:<os_id>"

# Botões oferecidos -> status alvo no ciclo (aberta → em_andamento → concluida|cancelada).
ACOES = [("▶️ Iniciar", "em_andamento"), ("✅ Concluir", "concluida"), ("✖️ Cancelar", "cancelada")]
STATUS_VALIDOS = {s for _, s in ACOES}


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
    """Monta sendMessage com uma linha de botões de status p/ a OS."""
    row = [{"text": label, "callback_data": f"{CB_PREFIX}{status}:{os_id}"} for label, status in ACOES]
    return {"chat_id": chat_id, "text": text, "reply_markup": json.dumps({"inline_keyboard": [row]})}


def parse_callback(data: str) -> tuple[str, str] | None:
    """Extrai (status, os_id) de 'os:<status>:<os_id>'. None se inválido."""
    if not data or not data.startswith(CB_PREFIX):
        return None
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[1] not in STATUS_VALIDOS or not parts[2]:
        return None
    return parts[1], parts[2]


def card_os(codigo: str, titulo: str, status: str, prioridade: str) -> str:
    """Texto do card de OS enviado ao responsável."""
    return f"🔧 OS {codigo}: {titulo}\nStatus: {status} · Prioridade: {prioridade}"


# ── persistência (spike: sqlite direto) ───────────────────────────────────────

def ensure_schema(db_path: str) -> None:
    """Migração aditiva: garante usuarios.telegram_chat_id (PRAGMA antes do ALTER)."""
    conn = sqlite3.connect(db_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(usuarios)")}
        if "telegram_chat_id" not in cols:
            conn.execute("ALTER TABLE usuarios ADD COLUMN telegram_chat_id TEXT")
            conn.commit()
    finally:
        conn.close()


def link_chat(db_path: str, chat_id: str, matricula: str) -> str | None:
    """Vincula chat_id à matrícula. Retorna o nome do usuário, ou None se não existe."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT id, nome FROM usuarios WHERE mat=?", (matricula,)).fetchone()
        if not row:
            return None
        conn.execute("UPDATE usuarios SET telegram_chat_id=? WHERE id=?", (str(chat_id), row[0]))
        conn.commit()
        return row[1]
    finally:
        conn.close()


def _user_id(conn: sqlite3.Connection, chat_id: str | int) -> int | None:
    row = conn.execute("SELECT id FROM usuarios WHERE telegram_chat_id=?", (str(chat_id),)).fetchone()
    return row[0] if row else None


def set_status(db_path: str, os_id: str, novo: str, chat_id: str | int) -> tuple[str, str] | None:
    """Transiciona a OS p/ `novo` e grava os_historico (autor resolvido pelo chat_id).
    Retorna (status_de, status_para), ou None se a OS não existe."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT status FROM ordens_servico WHERE id=?", (os_id,)).fetchone()
        if not row:
            return None
        de = row[0]
        if de == novo:
            return de, novo  # idempotente: sem update/histórico
        concl = ", data_conclusao=date('now')" if novo == "concluida" else ""
        conn.execute(
            f"UPDATE ordens_servico SET status=?, atualizado_em=CURRENT_TIMESTAMP{concl} WHERE id=?",
            (novo, os_id),
        )
        conn.execute(
            "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) "
            "VALUES (?,?,?,?,?)",
            (os_id, de, novo, "via Telegram", _user_id(conn, chat_id)),
        )
        conn.commit()
        return de, novo
    finally:
        conn.close()


def fetch_os_destino(db_path: str, os_id: str) -> tuple | None:
    """Dados da OS + chat_id do responsável p/ notificar. None se OS não existe."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT o.codigo, o.titulo, o.status, o.prioridade, u.telegram_chat_id "
            "FROM ordens_servico o LEFT JOIN usuarios u ON u.id=o.responsavel_id "
            "WHERE o.id=?",
            (os_id,),
        ).fetchone()
    finally:
        conn.close()


# ── anexos: técnico responde ao card com texto ou foto ────────────────────────

def codigo_do_reply(msg: dict) -> str | None:
    """Extrai o código da OS do card respondido ('🔧 OS <codigo>: ...')."""
    rep = msg.get("reply_to_message") or {}
    m = re.search(r"OS (\S+):", rep.get("text", "") or rep.get("caption", ""))
    return m.group(1) if m else None


def os_id_por_codigo(db_path: str, codigo: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT id FROM ordens_servico WHERE codigo=?", (codigo,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def anexar_etapa(db_path: str, os_id: str, titulo: str) -> int:
    """Grava uma etapa (nota/foto) na OS. Retorna o id."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("INSERT INTO os_etapas (os_id, titulo) VALUES (?,?)", (os_id, titulo))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def baixar_foto(db_path: str, file_id: str, codigo: str) -> str:
    """Baixa a foto do Telegram p/ data/os_anexos/<codigo>/. Retorna o caminho relativo."""
    info = call("getFile", {"file_id": file_id})
    fpath = info["result"]["file_path"]  # ex: photos/file_42.jpg
    url = f"https://api.telegram.org/file/bot{_token()}/{fpath}"
    base = os.path.join(os.path.dirname(db_path) or ".", "os_anexos", codigo)
    os.makedirs(base, exist_ok=True)
    dest = os.path.join(base, os.path.basename(fpath))
    with urllib.request.urlopen(url, timeout=40) as r, open(dest, "wb") as fh:
        fh.write(r.read())
    return dest


def handle_message(db_path: str, msg: dict) -> str | None:
    """Trata texto/foto respondendo ao card de uma OS. Retorna resposta ao usuário, ou None."""
    codigo = codigo_do_reply(msg)
    if not codigo:
        return None  # não é resposta a um card de OS — ignora
    os_id = os_id_por_codigo(db_path, codigo)
    if not os_id:
        return f"OS {codigo} não encontrada."
    foto = msg.get("photo")
    legenda = msg.get("caption") or msg.get("text") or ""
    if foto:
        dest = baixar_foto(db_path, foto[-1]["file_id"], codigo)  # [-1] = maior resolução
        anexar_etapa(db_path, os_id, f"📷 Foto: {os.path.basename(dest)}" + (f" — {legenda}" if legenda else ""))
        return f"Foto anexada à {codigo} ✅"
    if legenda:
        anexar_etapa(db_path, os_id, f"📝 {legenda}")
        return f"Nota anexada à {codigo} ✅"
    return None


# ── comandos ──────────────────────────────────────────────────────────────────

def cmd_send(chat_id: str, os_id: str, text: str | None = None) -> None:
    res = call("sendMessage", build_send_params(chat_id, text or f"OS {os_id}", os_id))
    print("OK" if res.get("ok") else f"FALHOU: {res}")


def cmd_notify(db_path: str, os_id: str) -> None:
    row = fetch_os_destino(db_path, os_id)
    if not row:
        sys.exit(f"OS {os_id} não encontrada.")
    codigo, titulo, status, prioridade, chat_id = row
    if not chat_id:
        sys.exit(f"OS {os_id}: responsável sem telegram_chat_id. Use 'link' antes.")
    cmd_send(chat_id, os_id, card_os(codigo, titulo, status, prioridade))


def cmd_link(db_path: str, chat_id: str, matricula: str) -> None:
    nome = link_chat(db_path, chat_id, matricula)
    print(f"Vinculado: {nome} ({matricula}) -> chat_id {chat_id}" if nome
          else f"Matrícula {matricula} não encontrada.")


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
            msg = u.get("message")
            if msg:  # texto/foto respondendo ao card -> anexa à OS
                resp = handle_message(db_path, msg)
                if resp:
                    ack("sendMessage", {"chat_id": msg["chat"]["id"], "text": resp,
                                        "reply_to_message_id": msg["message_id"]})
                    print(resp)
                continue
            cq = u.get("callback_query")
            if not cq:
                continue
            parsed = parse_callback(cq.get("data", ""))
            if not parsed:
                continue
            novo, os_id = parsed
            chat_id = cq["message"]["chat"]["id"]
            r = set_status(db_path, os_id, novo, chat_id)
            if not r:
                ack("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "OS não encontrada"})
                print(f"OS {os_id}: não encontrada")
                continue
            de, para = r
            nota = f"status: {para}" if de != para else f"já estava {para}"
            ack("answerCallbackQuery", {"callback_query_id": cq["id"], "text": f"OK — {nota} ✅"})
            base = cq["message"]["text"].split("\n\n☑")[0]  # tira marcador antigo (sem empilhar)
            edit = {
                "chat_id": chat_id,
                "message_id": cq["message"]["message_id"],
                "text": base + f"\n\n☑ {para} (registrado)",
            }
            # reanexa botões enquanto não-terminal; em concluida/cancelada deixa sem teclado
            if para not in ("concluida", "cancelada"):
                edit["reply_markup"] = build_send_params(str(chat_id), "", os_id)["reply_markup"]
            ack("editMessageText", edit)
            print(f"OS {os_id}: {de} -> {para}")


def selftest() -> None:
    p = build_send_params("42", "oi", "os-9")
    assert p["chat_id"] == "42"
    kb = json.loads(p["reply_markup"])
    botoes = {b["callback_data"] for b in kb["inline_keyboard"][0]}
    assert botoes == {"os:em_andamento:os-9", "os:concluida:os-9", "os:cancelada:os-9"}, botoes
    assert parse_callback("os:concluida:os-9") == ("concluida", "os-9")
    assert parse_callback("os:em_andamento:5") == ("em_andamento", "5")
    assert parse_callback("os:ruido:5") is None       # status inválido
    assert parse_callback("os:concluida:") is None     # sem os_id
    assert parse_callback("done:os-9") is None          # formato velho
    assert parse_callback("") is None
    assert "OS A-1" in card_os("A-1", "Trocar filtro", "aberta", "alta")
    card = card_os("OS-2026-007", "Trocar filtro", "aberta", "alta")
    assert codigo_do_reply({"reply_to_message": {"text": card}}) == "OS-2026-007"
    assert codigo_do_reply({"text": "oi"}) is None              # sem reply
    assert codigo_do_reply({"reply_to_message": {"text": "x"}}) is None  # reply sem OS
    print("selftest OK")


def main(argv: list[str]) -> None:
    _load_dotenv()
    db_path = os.environ.get("DB_PATH", "./data/core.db")
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "send" and len(argv) in (4, 5):
        cmd_send(argv[2], argv[3], argv[4] if len(argv) == 5 else None)
    elif cmd == "notify" and len(argv) == 3:
        ensure_schema(db_path)
        cmd_notify(db_path, argv[2])
    elif cmd == "link" and len(argv) == 4:
        ensure_schema(db_path)
        cmd_link(db_path, argv[2], argv[3])
    elif cmd == "whoami":
        cmd_whoami()
    elif cmd == "listen":
        ensure_schema(db_path)
        cmd_listen(db_path)
    elif cmd == "selftest":
        selftest()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
