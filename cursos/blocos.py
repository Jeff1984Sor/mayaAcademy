"""Registro dos tipos de bloco (seção 6).

Cada tipo declara: rótulo, se é interativo, o JSON Schema da `config` e,
opcionalmente, uma validação extra (regras que JSON Schema não expressa bem,
como "o índice da correta existe" ou "o nó de destino existe").

Para criar um tipo novo: adicione uma entrada em TIPOS e um componente em
static/js/player/blocos/<tipo>.js. Nada mais precisa mudar.
"""
from jsonschema import Draft202012Validator

MIN_BLOCOS = 4
MIN_INTERATIVOS = 2

ESTADOS_PERSONAGEM = ["neutro", "falando", "pensando", "comemorando", "alerta"]


def estados_padrao():
    return list(ESTADOS_PERSONAGEM)


_TEXTO = {"type": "string", "minLength": 1}
_TEXTO_OPC = {"type": "string"}
_ESTADO = {"enum": ESTADOS_PERSONAGEM}


def _lista(item, minimo=1, maximo=None):
    s = {"type": "array", "items": item, "minItems": minimo}
    if maximo:
        s["maxItems"] = maximo
    return s


def _obj(props, obrigatorios=(), extra=False):
    return {"type": "object", "properties": props, "required": list(obrigatorios), "additionalProperties": extra}


_QUESTAO = _obj(
    {
        "enunciado": _TEXTO,
        "alternativas": _lista(_TEXTO, 2, 6),
        "correta": {"type": "integer", "minimum": 0},
        "explicacao": _TEXTO,
        "paginas_origem": _lista({"type": "integer"}, 0),
    },
    ["enunciado", "alternativas", "correta", "explicacao"],
)


def _checar_questoes(questoes, prefixo="questoes"):
    erros = []
    for i, q in enumerate(questoes):
        if q.get("correta", 0) >= len(q.get("alternativas", [])):
            erros.append(f"{prefixo}[{i}].correta: índice {q.get('correta')} não existe nas alternativas")
    return erros


# --- validações extras -------------------------------------------------------

def _extra_quiz(cfg):
    return _checar_questoes(cfg.get("questoes", []))


def _extra_missao(cfg):
    return _checar_questoes(cfg.get("passos", []), "passos")


def _extra_arrastar(cfg):
    ids = {c["id"] for c in cfg.get("categorias", [])}
    erros = []
    for i, item in enumerate(cfg.get("itens", [])):
        if item.get("categoria") not in ids:
            erros.append(f"itens[{i}].categoria: '{item.get('categoria')}' não é uma categoria definida ({', '.join(sorted(ids))})")
    return erros


def _extra_caca(cfg):
    if not any(t.get("erro") for t in cfg.get("trechos", [])):
        return ["trechos: marque pelo menos um trecho com \"erro\": true"]
    erros = []
    for i, t in enumerate(cfg.get("trechos", [])):
        if t.get("erro") and not t.get("explicacao"):
            erros.append(f"trechos[{i}].explicacao: todo trecho com erro precisa de explicação")
    return erros


def _extra_cenario(cfg):
    nos = cfg.get("nos", [])
    ids = [n.get("id") for n in nos]
    erros = []
    if len(set(ids)) != len(ids):
        erros.append("nos: há ids repetidos")
    if cfg.get("inicio") not in ids:
        erros.append(f"inicio: nó '{cfg.get('inicio')}' não existe")
    tem_final = False
    for i, no in enumerate(nos):
        if not no.get("escolhas"):
            tem_final = True
        for j, e in enumerate(no.get("escolhas", [])):
            destino = e.get("vai_para")
            if destino and destino not in ids:
                erros.append(f"nos[{i}].escolhas[{j}].vai_para: nó '{destino}' não existe")
            if not destino:
                tem_final = True
    if not tem_final:
        erros.append("nos: o cenário precisa de pelo menos um final (nó sem escolhas ou escolha sem vai_para)")
    return erros


def _extra_montador(cfg):
    if not any(not p.get("distrator") for p in cfg.get("pecas", [])):
        return ["pecas: é preciso pelo menos uma peça que não seja distrator"]
    return []


# --- tipos -------------------------------------------------------------------

_VISUAL = _obj(
    {
        "frase": {"type": "integer", "minimum": 0, "description": "Índice global da frase do roteiro que dispara o visual"},
        "tipo": {"enum": ["titulo", "cartao", "lista", "icone", "alerta", "citacao", "numero"]},
        "texto": _TEXTO_OPC,
        "itens": _lista(_TEXTO, 0),
        "icone": _TEXTO_OPC,
        "estado": _ESTADO,
    },
    ["frase", "tipo"],
)

TIPOS = {
    "cena_narrada": {
        "rotulo": "Cena narrada",
        "interativo": False,
        "narracao": "obrigatoria",
        "schema": _obj(
            {
                "personagem": _TEXTO_OPC,
                "fundo": {"enum": ["palco", "quadro", "escritorio", "espaco"]},
                "lottie": _TEXTO_OPC,
                "visuais": _lista(_VISUAL, 1),
            },
            ["visuais"],
        ),
    },
    "dialogo": {
        "rotulo": "Diálogo (podcast)",
        "interativo": False,
        "narracao": "obrigatoria",
        "schema": _obj({"titulo": _TEXTO_OPC, "fundo": {"enum": ["estudio", "palco"]}}),
    },
    "chat_simulado": {
        "rotulo": "Chat simulado",
        "interativo": False,
        "narracao": "opcional",
        "schema": _obj(
            {
                "titulo": _TEXTO_OPC,
                "nome_usuario": _TEXTO_OPC,
                "nome_ia": _TEXTO_OPC,
                "mensagens": _lista(
                    _obj(
                        {
                            "de": {"enum": ["usuario", "ia", "sistema"]},
                            "texto": _TEXTO,
                            "nota": _TEXTO_OPC,
                            "nota_tipo": {"enum": ["alerta", "ok", "info"]},
                        },
                        ["de", "texto"],
                    ),
                    2,
                ),
            },
            ["mensagens"],
        ),
    },
    "antes_depois": {
        "rotulo": "Antes × depois",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {
                "rotulo_antes": _TEXTO,
                "rotulo_depois": _TEXTO,
                "antes": _TEXTO,
                "depois": _TEXTO,
                "comentario": _TEXTO_OPC,
            },
            ["rotulo_antes", "rotulo_depois", "antes", "depois"],
        ),
    },
    "arrastar_soltar": {
        "rotulo": "Arrastar e soltar",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {
                "instrucao": _TEXTO,
                "categorias": _lista(_obj({"id": _TEXTO, "nome": _TEXTO}, ["id", "nome"]), 2, 4),
                "itens": _lista(
                    _obj({"texto": _TEXTO, "categoria": _TEXTO, "feedback": _TEXTO_OPC}, ["texto", "categoria"]), 2
                ),
            },
            ["instrucao", "categorias", "itens"],
        ),
        "extra": _extra_arrastar,
    },
    "montador": {
        "rotulo": "Montador",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {
                "instrucao": _TEXTO,
                "objetivo": _TEXTO_OPC,
                "pecas": _lista(
                    _obj(
                        {
                            "rotulo": _TEXTO,
                            "texto": _TEXTO,
                            "peso": {"type": "integer", "minimum": 0, "maximum": 100},
                            "distrator": {"type": "boolean"},
                            "feedback": _TEXTO_OPC,
                        },
                        ["rotulo", "texto"],
                    ),
                    2,
                ),
                "mensagem_final": _TEXTO_OPC,
            },
            ["instrucao", "pecas"],
        ),
        "extra": _extra_montador,
    },
    "caca_erro": {
        "rotulo": "Caça ao erro",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {
                "instrucao": _TEXTO,
                "contexto": _TEXTO_OPC,
                "trechos": _lista(
                    _obj({"texto": _TEXTO, "erro": {"type": "boolean"}, "explicacao": _TEXTO_OPC}, ["texto"]), 2
                ),
            },
            ["instrucao", "trechos"],
        ),
        "extra": _extra_caca,
    },
    "cenario_ramificado": {
        "rotulo": "Cenário ramificado",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {
                "titulo": _TEXTO_OPC,
                "inicio": _TEXTO,
                "nos": _lista(
                    _obj(
                        {
                            "id": _TEXTO,
                            "texto": _TEXTO,
                            "escolhas": _lista(
                                _obj(
                                    {
                                        "texto": _TEXTO,
                                        "consequencia": _TEXTO,
                                        "tipo": {"enum": ["bom", "ruim", "neutro"]},
                                        "vai_para": _TEXTO_OPC,
                                    },
                                    ["texto", "consequencia"],
                                ),
                                0,
                            ),
                        },
                        ["id", "texto"],
                    ),
                    1,
                ),
            },
            ["inicio", "nos"],
        ),
        "extra": _extra_cenario,
    },
    "flashcards": {
        "rotulo": "Flashcards",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj({"cartoes": _lista(_obj({"frente": _TEXTO, "verso": _TEXTO}, ["frente", "verso"]), 2)}, ["cartoes"]),
    },
    "quiz_fixacao": {
        "rotulo": "Quiz de fixação",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj({"questoes": _lista(_QUESTAO, 2, 4)}, ["questoes"]),
        "extra": _extra_quiz,
    },
    "missao": {
        "rotulo": "Missão",
        "interativo": True,
        "narracao": "opcional",
        "schema": _obj(
            {"titulo": _TEXTO, "contexto": _TEXTO, "passos": _lista(_QUESTAO, 2), "recompensa": _TEXTO_OPC},
            ["titulo", "contexto", "passos"],
        ),
        "extra": _extra_missao,
    },
    "texto_apoio": {
        "rotulo": "Texto de apoio",
        "interativo": False,
        "narracao": "opcional",
        "schema": _obj({"destaque": _TEXTO_OPC, "icone": _TEXTO_OPC}),
    },
}

CHOICES = [(chave, t["rotulo"]) for chave, t in TIPOS.items()]
_VALIDADORES = {chave: Draft202012Validator(t["schema"]) for chave, t in TIPOS.items()}


def eh_interativo(tipo):
    return TIPOS.get(tipo, {}).get("interativo", False)


def _caminho(erro):
    partes = []
    for p in erro.absolute_path:
        partes.append(f"[{p}]" if isinstance(p, int) else (f".{p}" if partes else str(p)))
    return "".join(partes) or "(raiz)"


def _traduzir(erro):
    v = erro.validator
    if v == "required":
        campo = erro.message.split("'")[1] if "'" in erro.message else erro.message
        return f"campo obrigatório ausente: '{campo}'"
    if v == "additionalProperties":
        return f"campo não reconhecido ({erro.message.split('(')[-1].rstrip(')')})"
    if v == "minItems":
        return f"precisa de pelo menos {erro.validator_value} item(ns)"
    if v == "maxItems":
        return f"aceita no máximo {erro.validator_value} item(ns)"
    if v == "minLength":
        return "não pode ficar vazio"
    if v == "type":
        nomes = {"string": "texto", "integer": "número inteiro", "boolean": "verdadeiro/falso", "array": "lista", "object": "objeto"}
        return f"deveria ser {nomes.get(erro.validator_value, erro.validator_value)}"
    if v == "enum":
        return f"valor inválido; use um de: {', '.join(map(str, erro.validator_value))}"
    return erro.message


def validar_config(tipo, config):
    """Retorna lista de mensagens de erro (vazia = válido)."""
    if tipo not in TIPOS:
        return [f"tipo de bloco desconhecido: '{tipo}'. Tipos válidos: {', '.join(TIPOS)}"]
    if not isinstance(config, dict):
        return ["config deve ser um objeto"]
    erros = [
        f"{_caminho(e)}: {_traduzir(e)}"
        for e in sorted(_VALIDADORES[tipo].iter_errors(config), key=lambda e: list(e.absolute_path))
    ]
    if not erros and TIPOS[tipo].get("extra"):
        erros = TIPOS[tipo]["extra"](config)
    return erros


def validar_bloco(tipo, config, roteiro):
    erros = validar_config(tipo, config)
    if TIPOS.get(tipo, {}).get("narracao") == "obrigatoria" and not (roteiro or "").strip():
        erros.append("roteiro: este tipo de bloco exige narração")
    if tipo == "cena_narrada" and not erros:
        from .roteiro import parse_roteiro

        total = sum(len(f["frases"]) for f in parse_roteiro(roteiro))
        for i, vis in enumerate(config.get("visuais", [])):
            if vis["frase"] >= total:
                erros.append(f"visuais[{i}].frase: o roteiro só tem {total} frase(s) (índices 0 a {total - 1})")
    return erros


def problemas_da_aula(tipos):
    problemas = []
    if len(tipos) < MIN_BLOCOS:
        problemas.append(f"tem {len(tipos)} bloco(s); mínimo {MIN_BLOCOS}")
    interativos = sum(1 for t in tipos if eh_interativo(t))
    if interativos < MIN_INTERATIVOS:
        problemas.append(f"tem {interativos} bloco(s) interativo(s); mínimo {MIN_INTERATIVOS}")
    if tipos and all(t == "texto_apoio" for t in tipos):
        problemas.append("só tem texto de apoio")
    return problemas


def catalogo_para_js():
    return {chave: {"rotulo": t["rotulo"], "interativo": t["interativo"]} for chave, t in TIPOS.items()}
