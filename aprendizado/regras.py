"""Regras de aprendizado (funções puras sobre o banco, cobertas por testes): N1, N2, N8."""
from django.db import transaction
from django.utils import timezone

from cursos.models import Aula, Curso

from .models import Matricula, ProgressoAula

# Tempo máximo contado por envio de progresso (evita somar a aba esquecida aberta).
MAX_TEMPO_POR_ENVIO = 15 * 60


def aulas_em_ordem(curso):
    return list(Aula.objects.filter(modulo__curso=curso).select_related("modulo").order_by("modulo__ordem", "modulo__id", "ordem", "id"))


def matricula_de(usuario, curso):
    if not usuario.is_authenticated:
        return None
    return Matricula.objects.filter(aluno=usuario, curso=curso).exclude(status=Matricula.Status.CANCELADA).first()


@transaction.atomic
def matricular(aluno, curso, origem=Matricula.Origem.GRATUITA, organizacao=None):
    """Cria (ou reativa) a matrícula. Idempotente."""
    m, criada = Matricula.objects.select_for_update().get_or_create(
        aluno=aluno, curso=curso,
        defaults={"origem": origem, "organizacao": organizacao, "versao_curso": curso.versao},
    )
    if not criada and m.status == Matricula.Status.CANCELADA:
        m.status = Matricula.Status.ATIVA
        m.origem = origem
        m.organizacao = organizacao or m.organizacao
        m.save(update_fields=["status", "origem", "organizacao"])
    elif not criada and organizacao and not m.organizacao_id:
        m.organizacao = organizacao
        m.save(update_fields=["organizacao"])
    return m, criada


def concluidas(matricula):
    return set(matricula.progressos.filter(concluida_em__isnull=False).values_list("aula_id", flat=True))


def situacao_aulas(matricula, aulas=None):
    """Lista de (aula, estado) com estado em: concluida, liberada, bloqueada. N1: em ordem."""
    aulas = aulas if aulas is not None else aulas_em_ordem(matricula.curso)
    feitas = concluidas(matricula)
    saida, anterior_ok = [], True
    for aula in aulas:
        if aula.pk in feitas:
            estado = "concluida"
        elif anterior_ok:
            estado = "liberada"
        else:
            estado = "bloqueada"
        saida.append((aula, estado))
        anterior_ok = aula.pk in feitas
    return saida


def aula_liberada(matricula, aula):
    return any(a.pk == aula.pk and estado != "bloqueada" for a, estado in situacao_aulas(matricula))


def percentual(matricula, aulas=None):
    aulas = aulas if aulas is not None else aulas_em_ordem(matricula.curso)
    if not aulas:
        return 0
    feitas = concluidas(matricula) & {a.pk for a in aulas}
    return round(100 * len(feitas) / len(aulas))


def todas_concluidas(matricula):
    aulas = aulas_em_ordem(matricula.curso)
    return bool(aulas) and {a.pk for a in aulas} <= concluidas(matricula)


def proxima_aula(matricula):
    for aula, estado in situacao_aulas(matricula):
        if estado == "liberada":
            return aula
    return None


def _ids_validos(aula, ids):
    validos = set(aula.blocos.values_list("id", flat=True))
    return sorted({int(i) for i in ids if str(i).isdigit() and int(i) in validos})


def registrar_progresso(matricula, aula, indice=0, concluidos=(), resultados=None, segundos=0):
    """N8: salva a cada bloco concluído (o player chama a cada avanço)."""
    p, _ = ProgressoAula.objects.get_or_create(matricula=matricula, aula=aula)
    p.blocos_concluidos = sorted(set(p.blocos_concluidos) | set(_ids_validos(aula, concluidos)))
    p.ultimo_indice = max(0, int(indice or 0))
    if isinstance(resultados, dict):
        p.resultados = {**p.resultados, **{str(k): v for k, v in resultados.items()}}
    p.tempo_gasto_s += max(0, min(int(segundos or 0), MAX_TEMPO_POR_ENVIO))
    p.save()
    return p


@transaction.atomic
def concluir_aula(matricula, aula, resultados=None, segundos=0):
    """Marca a aula como concluída (uma vez) e dá o XP. Retorna (progresso, xp_ganho)."""
    from gamificacao import regras as gami

    p = registrar_progresso(matricula, aula, concluidos=aula.blocos.values_list("id", flat=True),
                            resultados=resultados, segundos=segundos)
    if p.concluida_em:
        return p, 0
    p.concluida_em = timezone.now()
    p.save(update_fields=["concluida_em"])
    xp = gami.xp_da_aula(matricula, aula, p.resultados)
    gami.avaliar_medalhas(matricula.aluno)
    return p, xp


def cursos_publicados():
    return Curso.objects.filter(status=Curso.Status.PUBLICADO)
