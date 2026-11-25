"""XP e medalhas (seção 7.3). Tudo idempotente: o mesmo evento nunca conta duas vezes."""
from django.db import IntegrityError, transaction
from django.db.models import Sum

from cursos import blocos as registro

from .models import Medalha, MedalhaAluno, XPEvento

XP_QUIZ_PRIMEIRA = 10
XP_INTERACAO = 5


def dar_xp(aluno, pontos, origem, referencia, curso=None):
    if pontos <= 0:
        return 0
    try:
        with transaction.atomic():
            XPEvento.objects.create(aluno=aluno, pontos=pontos, origem=origem, referencia=str(referencia)[:100], curso=curso)
    except IntegrityError:
        return 0
    return pontos


def xp_total(aluno):
    return aluno.xp_eventos.aggregate(t=Sum("pontos"))["t"] or 0


def xp_da_aula(matricula, aula, resultados):
    """XP por aula concluída + quiz acertado de primeira + interações completadas."""
    aluno, curso = matricula.aluno, matricula.curso
    total = dar_xp(aluno, aula.xp, XPEvento.Origem.AULA, f"aula:{aula.pk}", curso)
    acertos = 0
    interacoes = 0
    tipos = dict(aula.blocos.values_list("id", "tipo"))
    for bloco_id, r in (resultados or {}).items():
        if not isinstance(r, dict):
            continue
        acertos += int(r.get("acertosPrimeira") or 0)
        try:
            if registro.eh_interativo(tipos.get(int(bloco_id))):
                interacoes += 1
        except (TypeError, ValueError):
            continue
    total += dar_xp(aluno, acertos * XP_QUIZ_PRIMEIRA, XPEvento.Origem.QUIZ, f"quiz:{aula.pk}", curso)
    total += dar_xp(aluno, interacoes * XP_INTERACAO, XPEvento.Origem.INTERACAO, f"interacao:{aula.pk}", curso)
    return total


def _conquistou(medalha, aluno):
    from aprendizado.models import Matricula
    from avaliacoes.models import TentativaProva
    from certificados.models import Certificado

    concluidas = Matricula.objects.filter(aluno=aluno, status=Matricula.Status.CONCLUIDA)
    if medalha.curso_id:
        concluidas = concluidas.filter(curso_id=medalha.curso_id)
    c = medalha.Criterio
    if medalha.criterio == c.PRIMEIRO_CERTIFICADO:
        return Certificado.objects.filter(matricula__aluno=aluno).exists()
    if medalha.criterio == c.CURSO_CONCLUIDO:
        return concluidas.exists()
    if medalha.criterio == c.NOTA_100:
        q = TentativaProva.objects.filter(matricula__aluno=aluno, nota__gte=100)
        return (q.filter(matricula__curso_id=medalha.curso_id) if medalha.curso_id else q).exists()
    if medalha.criterio == c.MARATONISTA:
        dias = medalha.parametro or 7
        return any(m.concluida_em and (m.concluida_em - m.criada_em).days < dias for m in concluidas)
    if medalha.criterio == c.XP_TOTAL:
        return xp_total(aluno) >= (medalha.parametro or 1000)
    return False


def avaliar_medalhas(aluno):
    """Confere as medalhas ativas que o aluno ainda não tem. Retorna as novas."""
    novas = []
    ja_tem = set(aluno.medalhas.values_list("medalha_id", flat=True))
    for medalha in Medalha.objects.filter(ativa=True).exclude(pk__in=ja_tem):
        if _conquistou(medalha, aluno):
            _, criada = MedalhaAluno.objects.get_or_create(aluno=aluno, medalha=medalha)
            if criada:
                novas.append(medalha)
                dar_xp(aluno, medalha.xp_bonus, XPEvento.Origem.MEDALHA, f"medalha:{medalha.pk}", medalha.curso)
    return novas


def ranking(alunos_qs, limite=20):
    """Lista (posição, nome exibido, xp) — respeita quem pediu para ficar anônimo."""
    linhas = (
        alunos_qs.annotate(xp=Sum("xp_eventos__pontos")).filter(xp__gt=0).order_by("-xp", "id")[:limite]
    )
    return [
        (i, "Aluno anônimo" if u.anonimo_no_ranking else u.get_short_name(), u.xp or 0, u.pk)
        for i, u in enumerate(linhas, 1)
    ]
