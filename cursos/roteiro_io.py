"""Importação e exportação de cursos no formato de roteiro (docs/formato-roteiro.md)."""
import json
import math

import yaml
from django.db import transaction
from django.utils.text import slugify

from . import blocos as registro
from .models import Aula, BlocoAula, Curso, Modulo, Personagem, Questao
from .roteiro import personagens_usados

FORMATO = "mayaacademy/v1"

CAMPOS_CURSO = [
    "titulo", "slug", "subtitulo", "descricao", "carga_horaria", "nivel", "categoria", "modo_acesso",
    "preco", "nota_minima", "tentativas", "questoes_sorteadas", "cor_primaria", "cor_secundaria",
]


# --- leitura com número de linha ----------------------------------------------

class _Mapa(dict):
    linha = None


class _Lista(list):
    linha = None


class _Loader(yaml.SafeLoader):
    pass


def _mapa(loader, no):
    loader.flatten_mapping(no)
    m = _Mapa(loader.construct_pairs(no, deep=True))
    m.linha = no.start_mark.line + 1
    return m


def _seq(loader, no):
    s = _Lista(loader.construct_sequence(no, deep=True))
    s.linha = no.start_mark.line + 1
    return s


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapa)
_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, _seq)


class ErroLeitura(Exception):
    pass


def ler(conteudo: str):
    """Lê YAML ou JSON (JSON é YAML válido) preservando a linha de cada objeto."""
    try:
        dados = yaml.load(conteudo, Loader=_Loader)  # noqa: S506 — Loader derivado do SafeLoader
    except yaml.YAMLError as erro:
        marca = getattr(erro, "problem_mark", None)
        linha = f"linha {marca.line + 1}: " if marca else ""
        raise ErroLeitura(f"{linha}arquivo não é YAML/JSON válido ({getattr(erro, 'problem', erro)})") from erro
    if not isinstance(dados, dict):
        raise ErroLeitura("o arquivo deve começar com um objeto (chaves 'curso', 'personagens', 'modulos'...)")
    return dados


def _puro(valor):
    """Remove as subclasses com número de linha antes de gravar no banco."""
    return json.loads(json.dumps(valor, ensure_ascii=False))


# --- validação ------------------------------------------------------------------

class Relatorio:
    def __init__(self):
        self.erros = []
        self.avisos = []

    def erro(self, obj, local, msg):
        self.erros.append({"linha": getattr(obj, "linha", None), "local": local, "mensagem": msg})

    def aviso(self, obj, local, msg):
        self.avisos.append({"linha": getattr(obj, "linha", None), "local": local, "mensagem": msg})

    @property
    def ok(self):
        return not self.erros


def validar(dados, curso_destino=None):
    """Valida o documento inteiro. Com `curso_destino`, aceita só módulos (importação parcial)."""
    r = Relatorio()
    if dados.get("formato") not in (None, FORMATO):
        r.erro(dados, "formato", f"formato '{dados.get('formato')}' não suportado; use '{FORMATO}'")

    curso = dados.get("curso")
    if curso_destino is None:
        if not isinstance(curso, dict):
            r.erro(dados, "curso", "bloco 'curso' obrigatório (ou escolha um curso de destino para importar só módulos)")
            curso = {}
        else:
            if not curso.get("titulo"):
                r.erro(curso, "curso.titulo", "obrigatório")
            slug = curso.get("slug") or slugify(curso.get("titulo", ""))
            if slug and Curso.objects.filter(slug=slug).exists():
                r.erro(curso, "curso.slug", f"já existe um curso com slug '{slug}'; troque o slug no arquivo")
            desconhecidos = set(curso) - set(CAMPOS_CURSO)
            if desconhecidos:
                r.erro(curso, "curso", f"campo(s) não reconhecido(s): {', '.join(sorted(desconhecidos))}")
            for campo, opcoes in (("nivel", Curso.Nivel.values), ("modo_acesso", Curso.Acesso.values)):
                if campo in curso and curso[campo] not in opcoes:
                    r.erro(curso, f"curso.{campo}", f"use um de: {', '.join(opcoes)}")

    slugs = set(curso_destino.personagens.values_list("slug", flat=True)) if curso_destino else set()
    for i, p in enumerate(dados.get("personagens") or []):
        local = f"personagens[{i}]"
        if not isinstance(p, dict) or not p.get("slug") or not p.get("nome"):
            r.erro(p, local, "cada personagem precisa de 'slug' e 'nome'")
            continue
        if p.get("papel", "narrador") not in Personagem.Papel.values:
            r.erro(p, f"{local}.papel", "use 'narrador' ou 'mascote'")
        slugs.add(p["slug"].lower())

    modulos = dados.get("modulos")
    if not isinstance(modulos, list) or not modulos:
        r.erro(dados, "modulos", "informe pelo menos um módulo")
        modulos = []
    for mi, mod in enumerate(modulos, 1):
        lm = f"módulo {mi}"
        if not isinstance(mod, dict) or not mod.get("titulo"):
            r.erro(mod, lm, "módulo precisa de 'titulo'")
            continue
        aulas = mod.get("aulas") or []
        if not aulas:
            r.erro(mod, lm, "módulo sem aulas")
        for ai, aula in enumerate(aulas, 1):
            la = f"{lm} › aula {ai}"
            if not isinstance(aula, dict) or not aula.get("titulo"):
                r.erro(aula, la, "aula precisa de 'titulo'")
                continue
            la = f"{lm} › aula {ai} \"{aula['titulo']}\""
            tipos = []
            for bi, bloco in enumerate(aula.get("blocos") or [], 1):
                lb = f"{la} › bloco {bi}"
                if not isinstance(bloco, dict):
                    r.erro(bloco, lb, "bloco deve ser um objeto")
                    continue
                tipo = bloco.get("tipo")
                lb = f"{lb} ({tipo})"
                tipos.append(tipo)
                for msg in registro.validar_bloco(tipo, bloco.get("config") or {}, bloco.get("roteiro") or ""):
                    r.erro(bloco.get("config") or bloco, lb, msg)
                faltando = set(personagens_usados(bloco.get("roteiro") or "")) - slugs
                if faltando:
                    r.erro(bloco, lb, f"roteiro usa personagem não cadastrado: {', '.join(sorted(faltando))}")
            for problema in registro.problemas_da_aula(tipos):
                r.erro(aula, la, problema)

    for qi, q in enumerate(dados.get("questoes") or [], 1):
        lq = f"questão {qi}"
        if not isinstance(q, dict) or not q.get("enunciado"):
            r.erro(q, lq, "questão precisa de 'enunciado'")
            continue
        alts = q.get("alternativas") or []
        if len(alts) < 2:
            r.erro(q, lq, "precisa de pelo menos 2 alternativas")
        if not isinstance(q.get("correta"), int) or q["correta"] >= len(alts) or q["correta"] < 0:
            r.erro(q, lq, "'correta' deve ser o índice (0, 1, 2...) de uma alternativa")
        if q.get("uso", "prova") not in Questao.Uso.values:
            r.erro(q, lq, "uso deve ser fixacao, prova ou ambos")
        if "modulo" in q and not (isinstance(q["modulo"], int) and 1 <= q["modulo"] <= len(modulos)):
            r.erro(q, lq, f"'modulo' deve ser o número do módulo (1 a {len(modulos)})")

    if curso_destino is None and isinstance(curso, dict):
        sorteadas = curso.get("questoes_sorteadas", 10)
        prova = sum(1 for q in dados.get("questoes") or [] if isinstance(q, dict) and q.get("uso", "prova") in ("prova", "ambos"))
        minimo = math.ceil(sorteadas * 1.5)
        if prova < minimo:
            r.aviso(dados, "questoes", f"{prova} questão(ões) de prova; para publicar são necessárias {minimo}")
    return r


def resumo(dados):
    modulos = dados.get("modulos") or []
    aulas = [a for m in modulos if isinstance(m, dict) for a in (m.get("aulas") or []) if isinstance(a, dict)]
    blocos = [b for a in aulas for b in (a.get("blocos") or []) if isinstance(b, dict)]
    return {
        "titulo": (dados.get("curso") or {}).get("titulo"),
        "personagens": len(dados.get("personagens") or []),
        "modulos": len(modulos),
        "aulas": len(aulas),
        "blocos": len(blocos),
        "questoes": len(dados.get("questoes") or []),
        "estrutura": [
            {"titulo": m.get("titulo"), "aulas": [
                {"titulo": a.get("titulo"), "tipos": [b.get("tipo") for b in a.get("blocos") or [] if isinstance(b, dict)]}
                for a in m.get("aulas") or [] if isinstance(a, dict)
            ]}
            for m in modulos if isinstance(m, dict)
        ],
    }


# --- importação -----------------------------------------------------------------

@transaction.atomic
def importar(dados, curso_destino=None):
    """Cria (ou completa) o curso. Sempre como rascunho. Valide antes."""
    dados = _puro(dados)
    if curso_destino is None:
        c = dados["curso"]
        curso = Curso(**{k: v for k, v in c.items() if k in CAMPOS_CURSO})
        curso.slug = c.get("slug") or slugify(c["titulo"])[:200]
        curso.status = Curso.Status.RASCUNHO
        curso.save()
    else:
        curso = curso_destino

    for p in dados.get("personagens") or []:
        Personagem.objects.update_or_create(
            curso=curso, slug=p["slug"].lower(),
            defaults={
                "nome": p["nome"], "papel": p.get("papel", "narrador"),
                "voz_nome": p.get("voz", "pt-BR-Neural2-C"), "voz_velocidade": p.get("velocidade", 1.0),
                "voz_tom": p.get("tom", 0.0), "avatar_padrao": p.get("avatar", "maya"), "cor": p.get("cor", "#7C8FFF"),
            },
        )

    base_ordem = (curso.modulos.order_by("-ordem").values_list("ordem", flat=True).first() or 0) if curso_destino else 0
    modulos_criados = []
    for mi, m in enumerate(dados["modulos"], 1):
        modulo = Modulo.objects.create(curso=curso, titulo=m["titulo"], ordem=base_ordem + mi)
        modulos_criados.append(modulo)
        for ai, a in enumerate(m.get("aulas") or [], 1):
            aula = Aula.objects.create(
                modulo=modulo, titulo=a["titulo"], objetivo=a.get("objetivo", ""),
                duracao_min=a.get("duracao_min", 10), xp=a.get("xp", 100), ordem=ai,
            )
            BlocoAula.objects.bulk_create([
                BlocoAula(
                    aula=aula, ordem=bi, tipo=b["tipo"], titulo=b.get("titulo", ""),
                    roteiro=b.get("roteiro", "") or "", texto_tela=b.get("texto_tela", "") or "",
                    config=b.get("config") or {}, paginas_origem=b.get("paginas_origem") or [],
                    alem_do_pdf=bool(b.get("alem_do_pdf")),
                )
                for bi, b in enumerate(a.get("blocos") or [], 1)
            ])

    Questao.objects.bulk_create([
        Questao(
            curso=curso,
            modulo=modulos_criados[q["modulo"] - 1] if q.get("modulo") else None,
            enunciado=q["enunciado"], alternativas=q["alternativas"], correta=q["correta"],
            explicacao=q.get("explicacao", ""), dificuldade=q.get("dificuldade", "media"),
            uso=q.get("uso", "prova"), paginas_origem=q.get("paginas_origem") or [],
        )
        for q in dados.get("questoes") or []
    ])
    return curso


# --- exportação -----------------------------------------------------------------

class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, valor):
    estilo = "|" if "\n" in valor else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", valor, style=estilo)


_Dumper.add_representer(str, _str)


def exportar(curso):
    modulos = curso.modulos.prefetch_related("aulas__blocos").order_by("ordem")
    indice_modulo = {}
    saida_modulos = []
    for i, m in enumerate(modulos, 1):
        indice_modulo[m.pk] = i
        saida_modulos.append({
            "titulo": m.titulo,
            "aulas": [
                {
                    "titulo": a.titulo, "objetivo": a.objetivo, "duracao_min": a.duracao_min, "xp": a.xp,
                    "blocos": [
                        _sem_vazios({
                            "tipo": b.tipo, "titulo": b.titulo, "roteiro": b.roteiro, "texto_tela": b.texto_tela,
                            "config": b.config, "paginas_origem": b.paginas_origem, "alem_do_pdf": b.alem_do_pdf or None,
                        })
                        for b in a.blocos.all()
                    ],
                }
                for a in m.aulas.all()
            ],
        })
    doc = {
        "formato": FORMATO,
        "curso": _sem_vazios({k: (float(getattr(curso, k)) if k == "preco" else getattr(curso, k)) for k in CAMPOS_CURSO}),
        "personagens": [
            {"slug": p.slug, "nome": p.nome, "papel": p.papel, "voz": p.voz_nome, "velocidade": p.voz_velocidade,
             "tom": p.voz_tom, "avatar": p.avatar_padrao, "cor": p.cor}
            for p in curso.personagens.all()
        ],
        "modulos": saida_modulos,
        "questoes": [
            _sem_vazios({
                "modulo": indice_modulo.get(q.modulo_id), "enunciado": q.enunciado, "alternativas": q.alternativas,
                "correta": q.correta, "explicacao": q.explicacao, "dificuldade": q.dificuldade, "uso": q.uso,
                "paginas_origem": q.paginas_origem,
            })
            for q in curso.questoes.filter(ativa=True)
        ],
    }
    return yaml.dump(doc, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=100)


def _sem_vazios(d):
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}
