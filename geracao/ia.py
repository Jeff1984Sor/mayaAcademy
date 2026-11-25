"""Prompts (arquivos em estudio/prompts/) e schemas de saída estruturada da IA.

Os schemas seguem as regras da saída estrita: todo objeto com additionalProperties=false e
todos os campos em "required". A config de cada bloco vai como TEXTO JSON (config_json),
porque cada tipo tem um schema diferente; ela é validada depois pelo registro de blocos.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from string import Template

from django.conf import settings

from cursos import blocos as registro

PASTA_PROMPTS = Path(settings.BASE_DIR) / "estudio" / "prompts"
DOC_FORMATO = Path(settings.BASE_DIR) / "docs" / "formato-roteiro.md"


@lru_cache
def _arquivo(nome):
    return (PASTA_PROMPTS / f"{nome}.md").read_text(encoding="utf-8")


def _secoes(nome):
    """Separa o arquivo de prompt em {'sistema': ..., 'usuario': ...}."""
    partes = {}
    atual = None
    for linha in _arquivo(nome).splitlines(keepends=True):
        m = re.match(r"^## (sistema|usuario)\s*$", linha)
        if m:
            atual = m.group(1)
            partes[atual] = ""
        elif atual:
            partes[atual] += linha
    return {k: v.strip() for k, v in partes.items()}


def mensagens(nome, **valores):
    valores.setdefault("fidelidade", _arquivo("_fidelidade").strip())
    saida = []
    for papel, chave in (("system", "sistema"), ("user", "usuario")):
        texto = _secoes(nome).get(chave)
        if texto:
            saida.append({"role": papel, "content": Template(texto).safe_substitute(valores)})
    return saida


@lru_cache
def formato_blocos():
    """Trecho da documentação do formato (roteiro + tipos + exemplo) e o schema exato de cada tipo."""
    doc = DOC_FORMATO.read_text(encoding="utf-8")
    inicio = doc.find("## 3.")
    fim = doc.find("## 5.")
    trecho = doc[inicio:fim if fim > 0 else None].strip()
    schemas = {
        tipo: {"interativo": t["interativo"], "narracao": t["narracao"], "schema_config": t["schema"]}
        for tipo, t in registro.TIPOS.items()
    }
    return trecho + "\n\nSCHEMA EXATO DA CONFIG DE CADA TIPO (JSON Schema):\n" + json.dumps(schemas, ensure_ascii=False)


# --- schemas de saída ------------------------------------------------------------

def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_TXT = {"type": "string"}
_PAGINAS = {"type": "array", "items": {"type": "integer"}}

SCHEMA_MAPA = _obj({
    "temas": {"type": "array", "items": _obj({"nome": _TXT, "resumo": _TXT, "paginas": _PAGINAS})},
    "conceitos": {"type": "array", "items": _obj({"termo": _TXT, "definicao": _TXT, "paginas": _PAGINAS})},
    "glossario": {"type": "array", "items": _obj({"termo": _TXT, "definicao": _TXT, "paginas": _PAGINAS})},
    "exemplos": {"type": "array", "items": _obj({"descricao": _TXT, "paginas": _PAGINAS})},
    "paginas_sem_conteudo": _PAGINAS,
})

SCHEMA_EMENTA = _obj({
    "titulo": _TXT,
    "subtitulo": _TXT,
    "descricao": _TXT,
    "categoria": _TXT,
    "modulos": {"type": "array", "items": _obj({
        "titulo": _TXT,
        "aulas": {"type": "array", "items": _obj({
            "titulo": _TXT, "objetivo": _TXT, "paginas": _PAGINAS, "duracao_min": {"type": "integer"},
        })},
    })},
})

SCHEMA_AULA = _obj({
    "blocos": {"type": "array", "items": _obj({
        "tipo": {"type": "string", "enum": list(registro.TIPOS)},
        "titulo": _TXT,
        "roteiro": _TXT,
        "texto_tela": _TXT,
        "config_json": {"type": "string", "description": "Config do bloco como texto JSON (objeto), no schema do tipo"},
        "paginas_origem": _PAGINAS,
        "alem_do_pdf": {"type": "boolean"},
    })},
    "questoes": {"type": "array", "items": _obj({
        "enunciado": _TXT,
        "alternativas": {"type": "array", "items": _TXT},
        "correta": {"type": "integer"},
        "explicacao": _TXT,
        "dificuldade": {"type": "string", "enum": ["facil", "media", "dificil"]},
        "uso": {"type": "string", "enum": ["fixacao", "prova"]},
        "paginas_origem": _PAGINAS,
    })},
})
