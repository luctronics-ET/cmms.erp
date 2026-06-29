"""Tests for POST /api/auth/login and POST/PUT /api/usuarios — SEC-01/SEC-02.

Covers:
  - test_legacy_djb2_login_success_and_upgrades_hash:
        legacy djb2 account logs in (200) and pw_hash is upgraded to $argon2 in-request.
  - test_second_login_uses_argon2_path:
        after upgrade, second login still returns 200 (argon2 path only).
  - test_service_account_argon2_login:
        pre-existing $argon2 service account logs in, receives token.
  - test_null_pw_hash_returns_401:
        account with NULL pw_hash returns 401 (SEC-02 login boundary, no default fallback).
  - test_empty_pw_hash_returns_401:
        account with empty-string pw_hash returns 401 (no default fallback).
  - test_wrong_password_djb2_returns_401:
        wrong password against djb2-hashed account returns 401.
  - test_wrong_password_argon2_returns_401:
        wrong password against argon2-hashed account returns 401.
  - test_response_shape:
        response keys are exactly {token, expira_em, usuario} and usuario excludes pw_hash.

SEC-02 write-path tests (POST/PUT /api/usuarios):
  - test_create_usuario_with_senha_stores_argon2_and_can_login:
        POST with senha → pw_hash starts with $argon2; account can log in.
  - test_create_usuario_without_senha_stores_empty_hash:
        POST without senha → pw_hash is NULL or "" (never default credential).
  - test_create_usuario_without_senha_cannot_login:
        Freshly created no-senha account returns 401 for any login attempt.
  - test_put_usuario_with_senha_updates_hash_and_can_login:
        PUT with senha → new argon2 hash; account can log in with new password.
  - test_put_usuario_without_senha_preserves_hash:
        PUT without senha → existing pw_hash unchanged.
"""
from __future__ import annotations

import sqlite3


# ──────────────────────────── DB helpers (mirrored from test_manutencao.py) ───


def _query(main, sql, params=()):
    """Synchronous query against the test DB."""
    conn = sqlite3.connect(main.db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _exec(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────── seed helpers ────────────────────────────────────


def _seed_legacy_user(main, mat: str, nome: str, password: str) -> int:
    """Insert a user with a djb2-hashed password (legacy). Returns the user id."""
    pw_hash = main._djb2(password)
    _exec(
        main,
        "INSERT INTO usuarios (nome, mat, pw_hash, role, ativo) VALUES (?, ?, ?, 'admin', 1)",
        (nome, mat, pw_hash),
    )
    rows = _query(main, "SELECT id FROM usuarios WHERE mat = ?", (mat,))
    return rows[0]["id"]


def _seed_argon2_user(main, mat: str, nome: str, password: str) -> int:
    """Insert a user with a pre-existing Argon2id hash. Returns the user id."""
    ph = main._ph
    pw_hash = ph.hash(password)
    _exec(
        main,
        "INSERT INTO usuarios (nome, mat, pw_hash, role, ativo) VALUES (?, ?, ?, 'admin', 1)",
        (nome, mat, pw_hash),
    )
    rows = _query(main, "SELECT id FROM usuarios WHERE mat = ?", (mat,))
    return rows[0]["id"]


def _seed_null_hash_user(main, mat: str, nome: str) -> int:
    """Insert a user with NULL pw_hash (no password set). Returns the user id."""
    _exec(
        main,
        "INSERT INTO usuarios (nome, mat, pw_hash, role, ativo) VALUES (?, ?, NULL, 'admin', 1)",
        (nome, mat),
    )
    rows = _query(main, "SELECT id FROM usuarios WHERE mat = ?", (mat,))
    return rows[0]["id"]


def _seed_empty_hash_user(main, mat: str, nome: str) -> int:
    """Insert a user with empty-string pw_hash (unprovisioned). Returns the user id."""
    _exec(
        main,
        "INSERT INTO usuarios (nome, mat, pw_hash, role, ativo) VALUES (?, ?, '', 'admin', 1)",
        (nome, mat),
    )
    rows = _query(main, "SELECT id FROM usuarios WHERE mat = ?", (mat,))
    return rows[0]["id"]


def _get_pw_hash(main, user_id: int) -> str | None:
    """Fetch the current pw_hash for a user directly from the DB."""
    rows = _query(main, "SELECT pw_hash FROM usuarios WHERE id = ?", (user_id,))
    return rows[0]["pw_hash"] if rows else None


# ──────────────────────────── tests ──────────────────────────────────────────


def test_legacy_djb2_login_success_and_upgrades_hash(app_client):
    """SEC-01: djb2 account logs in (200) and pw_hash becomes $argon2 in the same request."""
    client, main = app_client
    uid = _seed_legacy_user(main, "LEG001", "Legado Teste", "senha123")

    # Confirm the stored hash is djb2 (not $argon2)
    stored_before = _get_pw_hash(main, uid)
    assert stored_before is not None
    assert not stored_before.startswith("$argon2"), (
        f"Expected djb2 hash before login, got: {stored_before!r}"
    )

    resp = client.post("/api/auth/login", json={"mat": "LEG001", "senha": "senha123"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # The lazy upgrade must have written an Argon2id hash into the DB
    stored_after = _get_pw_hash(main, uid)
    assert stored_after is not None
    assert stored_after.startswith("$argon2"), (
        f"Expected $argon2 hash after upgrade, got: {stored_after!r}"
    )


def test_second_login_uses_argon2_path(app_client):
    """After lazy upgrade, a second login verifies via the Argon2 path and still returns 200."""
    client, main = app_client
    uid = _seed_legacy_user(main, "LEG002", "Legado Duplo", "pass456")

    # First login triggers the upgrade
    r1 = client.post("/api/auth/login", json={"mat": "LEG002", "senha": "pass456"})
    assert r1.status_code == 200

    stored_mid = _get_pw_hash(main, uid)
    assert stored_mid is not None and stored_mid.startswith("$argon2"), (
        "Hash should be $argon2 after first login"
    )

    # Second login: must succeed via argon2 path; hash should remain $argon2
    r2 = client.post("/api/auth/login", json={"mat": "LEG002", "senha": "pass456"})
    assert r2.status_code == 200, f"Second login failed: {r2.status_code}: {r2.text}"

    stored_after = _get_pw_hash(main, uid)
    assert stored_after is not None and stored_after.startswith("$argon2"), (
        "Hash should still be $argon2 after second login"
    )


def test_service_account_argon2_login(app_client):
    """Pre-existing $argon2 service account logs in and receives a token (no code change on caller side)."""
    client, main = app_client
    _seed_argon2_user(main, "SVC001", "Serviço xPredial", "servicepass")

    resp = client.post("/api/auth/login", json={"mat": "SVC001", "senha": "servicepass"})
    assert resp.status_code == 200, f"Service account login failed: {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "token" in body
    assert "expira_em" in body


def test_null_pw_hash_returns_401(app_client):
    """SEC-02 (login side): account with NULL pw_hash returns 401 — no default fallback."""
    client, main = app_client
    _seed_null_hash_user(main, "NULL001", "Sem Senha")

    resp = client.post("/api/auth/login", json={"mat": "NULL001", "senha": "1234"})
    assert resp.status_code == 401, (
        f"Expected 401 for NULL pw_hash account, got {resp.status_code}: {resp.text}"
    )


def test_wrong_password_djb2_returns_401(app_client):
    """Wrong password against a djb2-hashed account returns 401."""
    client, main = app_client
    _seed_legacy_user(main, "DJBWRONG", "DJ Errado", "correta")

    resp = client.post("/api/auth/login", json={"mat": "DJBWRONG", "senha": "errada"})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


def test_wrong_password_argon2_returns_401(app_client):
    """Wrong password against an Argon2id-hashed account returns 401."""
    client, main = app_client
    _seed_argon2_user(main, "A2WRONG", "Argon Errado", "correta")

    resp = client.post("/api/auth/login", json={"mat": "A2WRONG", "senha": "errada"})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


def test_response_shape(app_client):
    """Response keys are exactly {token, expira_em, usuario} and usuario never contains pw_hash."""
    client, main = app_client
    _seed_legacy_user(main, "SHAPE001", "Shape Tester", "qualquercoisa")

    resp = client.post("/api/auth/login", json={"mat": "SHAPE001", "senha": "qualquercoisa"})
    assert resp.status_code == 200
    body = resp.json()

    # Mandatory top-level keys
    assert set(body.keys()) == {"token", "expira_em", "usuario"}, (
        f"Unexpected response keys: {set(body.keys())}"
    )
    # usuario must never leak pw_hash
    assert "pw_hash" not in body["usuario"], "pw_hash must not appear in the usuario payload"


def test_empty_pw_hash_returns_401(app_client):
    """SEC-02 (login side): account with empty-string pw_hash returns 401 — no default fallback."""
    client, main = app_client
    _seed_empty_hash_user(main, "EMPTY001", "Sem Senha Vazia")

    resp = client.post("/api/auth/login", json={"mat": "EMPTY001", "senha": "1234"})
    assert resp.status_code == 401, (
        f"Expected 401 for empty pw_hash account, got {resp.status_code}: {resp.text}"
    )
    # Error message must not distinguish empty-hash from wrong-password (no enumeration signal)
    body = resp.json()
    assert "inválidas" in body.get("detail", "").lower() or resp.status_code == 401


# ─────────────────── SEC-02 write-path tests (POST/PUT /api/usuarios) ─────────


def test_create_usuario_with_senha_stores_argon2_and_can_login(app_client):
    """SEC-02: POST /api/usuarios with senha → pw_hash is $argon2 and account can log in."""
    client, main = app_client

    resp = client.post(
        "/api/usuarios",
        json={"nome": "Usuario Argon", "mat": "ARG001", "senha": "minhasenha"},
    )
    assert resp.status_code == 201, f"Create failed: {resp.status_code}: {resp.text}"
    created = resp.json()
    uid = created["id"]

    # Verify pw_hash in DB is Argon2id (not djb2)
    stored = _get_pw_hash(main, uid)
    assert stored is not None, "pw_hash must not be NULL when senha was provided"
    assert stored.startswith("$argon2"), (
        f"Expected Argon2id hash (starts with $argon2), got: {stored!r}"
    )

    # Account must be able to log in with the provided senha
    login_resp = client.post("/api/auth/login", json={"mat": "ARG001", "senha": "minhasenha"})
    assert login_resp.status_code == 200, (
        f"Login failed for newly created account: {login_resp.status_code}: {login_resp.text}"
    )
    assert "token" in login_resp.json()


def test_create_usuario_without_senha_stores_empty_hash(app_client):
    """SEC-02: POST /api/usuarios without senha → pw_hash is NULL or '' (never default credential)."""
    client, main = app_client

    resp = client.post(
        "/api/usuarios",
        json={"nome": "Usuario Sem Senha", "mat": "NOSN001"},
    )
    assert resp.status_code == 201, f"Create failed: {resp.status_code}: {resp.text}"
    uid = resp.json()["id"]

    stored = _get_pw_hash(main, uid)
    # Must be NULL or empty — never a hash of the default credential
    assert stored is None or stored == "", (
        f"Expected NULL/empty pw_hash for no-senha account, got: {stored!r}"
    )


def test_create_usuario_without_senha_cannot_login(app_client):
    """SEC-02: A freshly created no-senha account cannot authenticate — 401 for any password."""
    client, main = app_client

    resp = client.post(
        "/api/usuarios",
        json={"nome": "Sem Senha Nao Login", "mat": "NOSN002"},
    )
    assert resp.status_code == 201, f"Create failed: {resp.status_code}: {resp.text}"

    # Attempt with the old hardcoded default — must now fail
    login_resp = client.post("/api/auth/login", json={"mat": "NOSN002", "senha": "1234"})
    assert login_resp.status_code == 401, (
        f"Expected 401 for no-senha account login, got {login_resp.status_code}: {login_resp.text}"
    )

    # Any other password must also fail
    login_resp2 = client.post("/api/auth/login", json={"mat": "NOSN002", "senha": "qualquer"})
    assert login_resp2.status_code == 401


def test_put_usuario_with_senha_updates_hash_and_can_login(app_client):
    """SEC-02: PUT /api/usuarios with senha → new Argon2 hash stored and login works."""
    client, main = app_client

    # Create with no senha first
    create_resp = client.post(
        "/api/usuarios",
        json={"nome": "Usuario PUT Senha", "mat": "PUT001"},
    )
    assert create_resp.status_code == 201
    uid = create_resp.json()["id"]

    old_hash = _get_pw_hash(main, uid)

    # PUT with a new senha
    put_resp = client.put(
        f"/api/usuarios/{uid}",
        json={"nome": "Usuario PUT Senha", "mat": "PUT001", "senha": "novasenha"},
    )
    assert put_resp.status_code == 200, f"PUT failed: {put_resp.status_code}: {put_resp.text}"

    new_hash = _get_pw_hash(main, uid)
    assert new_hash is not None, "pw_hash must not be NULL after PUT with senha"
    assert new_hash.startswith("$argon2"), (
        f"Expected $argon2 hash after PUT with senha, got: {new_hash!r}"
    )
    assert new_hash != old_hash, "Hash should have changed after PUT with new senha"

    # Login with new password must work
    login_resp = client.post("/api/auth/login", json={"mat": "PUT001", "senha": "novasenha"})
    assert login_resp.status_code == 200, (
        f"Login failed after hash update: {login_resp.status_code}: {login_resp.text}"
    )


def test_put_usuario_without_senha_preserves_hash(app_client):
    """SEC-02: PUT /api/usuarios without senha → existing pw_hash is preserved unchanged."""
    client, main = app_client

    # Create with a password
    create_resp = client.post(
        "/api/usuarios",
        json={"nome": "Usuario Preservar Hash", "mat": "PRES001", "senha": "originalsenha"},
    )
    assert create_resp.status_code == 201
    uid = create_resp.json()["id"]

    original_hash = _get_pw_hash(main, uid)
    assert original_hash is not None and original_hash.startswith("$argon2")

    # PUT without senha — must not change the hash
    put_resp = client.put(
        f"/api/usuarios/{uid}",
        json={"nome": "Usuario Preservar Hash Atualizado", "mat": "PRES001"},
    )
    assert put_resp.status_code == 200, f"PUT failed: {put_resp.status_code}: {put_resp.text}"

    preserved_hash = _get_pw_hash(main, uid)
    assert preserved_hash == original_hash, (
        f"pw_hash changed on PUT without senha: {original_hash!r} -> {preserved_hash!r}"
    )
