"""Empacota static/js/player/*.js (ES modules) num único script clássico.

Módulos ES não carregam em file://, e o curso baixado precisa abrir direto do
disco ou dentro de um LMS. Este empacotador é propositalmente simples: aceita
só `import { a, b as c } from "./x.js";` e `export function|const|class nome`.
Qualquer outra sintaxe de import/export gera erro (para não falhar em silêncio).
"""
import re
from pathlib import Path

from django.conf import settings

RAIZ = Path(settings.BASE_DIR) / "static" / "js" / "player"
ENTRADA = "main.js"
SAIDA = Path(settings.BASE_DIR) / "static" / "js" / "player.bundle.js"

_RE_IMPORT = re.compile(r"""^import\s*\{([^}]*)\}\s*from\s*["']([^"']+)["'];?[ \t]*$""", re.MULTILINE)
_RE_EXPORT = re.compile(r"^export\s+(async\s+function|function|const|let|class)\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
_RE_SOBRA = re.compile(r"^\s*(import|export)\b", re.MULTILINE)


class ErroBundle(Exception):
    pass


def _resolver(base: Path, caminho: str) -> Path:
    if not caminho.startswith("."):
        raise ErroBundle(f"{base.name}: só imports relativos são suportados ({caminho})")
    return (base.parent / caminho).resolve()


def _transformar(arquivo: Path, ids: dict):
    fonte = arquivo.read_text(encoding="utf-8")
    deps = []

    def troca_import(m):
        alvo = _resolver(arquivo, m.group(2))
        deps.append(alvo)
        nomes = []
        for parte in m.group(1).split(","):
            parte = parte.strip()
            if not parte:
                continue
            if " as " in parte:
                original, apelido = [p.strip() for p in parte.split(" as ")]
                nomes.append(f"{original}: {apelido}")
            else:
                nomes.append(parte)
        return f"const {{ {', '.join(nomes)} }} = __m[{ids.setdefault(alvo, len(ids))}];"

    corpo = _RE_IMPORT.sub(troca_import, fonte)
    exportados = [m.group(2) for m in _RE_EXPORT.finditer(corpo)]
    corpo = _RE_EXPORT.sub(lambda m: f"{m.group(1)} {m.group(2)}", corpo)
    sobra = _RE_SOBRA.search(corpo)
    if sobra:
        linha = corpo[: sobra.start()].count("\n") + 1
        raise ErroBundle(f"{arquivo.relative_to(RAIZ)}:{linha}: sintaxe de import/export não suportada")
    return corpo, exportados, deps


def montar() -> str:
    ids = {}
    modulos = {}
    ordem = []

    def visitar(arquivo: Path, pilha=()):
        if arquivo in modulos:
            return
        if arquivo in pilha:
            raise ErroBundle(f"import circular: {' → '.join(p.name for p in pilha)} → {arquivo.name}")
        if not arquivo.exists():
            raise ErroBundle(f"arquivo não encontrado: {arquivo}")
        ids.setdefault(arquivo, len(ids))
        corpo, exportados, deps = _transformar(arquivo, ids)
        for d in deps:
            visitar(d, pilha + (arquivo,))
        modulos[arquivo] = (corpo, exportados)
        ordem.append(arquivo)

    visitar((RAIZ / ENTRADA).resolve())
    partes = ["/* MayaAcademy player — gerado por `manage.py montar_player`. Não edite. */", "(function () {", '"use strict";', "const __m = {};"]
    for arquivo in ordem:
        corpo, exportados = modulos[arquivo]
        partes.append(f"/* --- {arquivo.relative_to(RAIZ).as_posix()} --- */")
        partes.append(f"__m[{ids[arquivo]}] = (function () {{\n{corpo}\nreturn {{ {', '.join(exportados)} }};\n}})();")
    partes.append("})();")
    return "\n".join(partes) + "\n"


def gravar(destino: Path = SAIDA) -> Path:
    destino.write_text(montar(), encoding="utf-8")
    return destino
