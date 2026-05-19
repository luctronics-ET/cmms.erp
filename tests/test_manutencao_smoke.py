"""Smoke tests para a refatoração da página manutencao."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ──────────────────────── verificações no cmasm_erp.html ────────────────────────

def _erp_html() -> str:
    return (ROOT / "cmasm_erp.html").read_text(encoding="utf-8")


def test_erp_inclui_pmoc_engine_css():
    assert 'assets/pmoc-engine.css' in _erp_html()


def test_erp_inclui_pmoc_engine_js():
    assert 'assets/pmoc-engine.js' in _erp_html()


def test_erp_inclui_erp_manutencao_mocks_js():
    assert 'assets/erp-manutencao-mocks.js' in _erp_html()


def test_erp_inclui_erp_manutencao_js():
    assert 'assets/erp-manutencao.js' in _erp_html()


# ──────────────────── verificações de sintaxe nos JS ─────────────────────

def _check_braces(path: Path) -> tuple[dict[str, int], list[tuple[int, str]]]:
    """Verifica balanço de chaves/parênteses/colchetes ignorando strings e comentários.

    Limitações conhecidas (smoke test, não parser completo):
    - Não reconhece regex literais. Código como `var r = /\\{/g;` produz falso positivo.
      Evite literais de regex que contenham `{`, `(` ou `[` sem o par correspondente.
      Para validação real de JS, use ESLint.
    - Não reconhece expressões em template literals (`${ ... }`) — assume que estão
      bem-formadas dentro da string.

    Retorna (depth_final, erros). Tudo zerado e sem erros = sintaticamente plausível.
    """
    src = path.read_text(encoding="utf-8")
    depth = {"{": 0, "(": 0, "[": 0}
    inv = {"}": "{", ")": "(", "]": "["}
    state = "code"  # code | line_cmt | blk_cmt | dq | sq | tq
    errors: list[tuple[int, str]] = []
    line = 1
    i = 0
    while i < len(src):
        c = src[i]
        nx = src[i + 1] if i + 1 < len(src) else ""
        if c == "\n":
            line += 1
        if state == "code":
            if c == "/" and nx == "/": state = "line_cmt"; i += 2; continue
            if c == "/" and nx == "*": state = "blk_cmt";  i += 2; continue
            if c == '"': state = "dq"
            elif c == "'": state = "sq"
            elif c == "`": state = "tq"
            elif c in "{([": depth[c] += 1
            elif c in "})]":
                o = inv[c]
                depth[o] -= 1
                if depth[o] < 0:
                    errors.append((line, c))
        elif state == "line_cmt":
            if c == "\n": state = "code"
        elif state == "blk_cmt":
            if c == "*" and nx == "/": state = "code"; i += 2; continue
        elif state == "dq":
            if c == "\\": i += 2; continue
            if c == '"': state = "code"
        elif state == "sq":
            if c == "\\": i += 2; continue
            if c == "'": state = "code"
        elif state == "tq":
            if c == "\\": i += 2; continue
            if c == "`": state = "code"
        i += 1
    return depth, errors


def test_erp_manutencao_js_sintaxe_balanceada():
    depth, errors = _check_braces(ROOT / "assets/erp-manutencao.js")
    assert errors == [], f"chaves não-balanceadas: {errors[:5]}"
    assert all(v == 0 for v in depth.values()), f"saldo final: {depth}"


def test_erp_manutencao_mocks_js_sintaxe_balanceada():
    depth, errors = _check_braces(ROOT / "assets/erp-manutencao-mocks.js")
    assert errors == [], f"chaves não-balanceadas: {errors[:5]}"
    assert all(v == 0 for v in depth.values()), f"saldo final: {depth}"
