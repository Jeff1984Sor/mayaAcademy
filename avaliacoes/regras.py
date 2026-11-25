"""Prova final: N2 (só com 100% das aulas), N3 (sorteio + embaralhamento + snapshot), N4 (nota mínima e tentativas)."""
import random
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from aprendizado import regras as apr
from aprendizado.models import Matricula
from cursos.models import Questao

from .models import TentativaProva


def tentativas_permitidas(matricula):
    return matricula.curso.tentativas + matricula.tentativas_extras


def finalizadas(matricula):
    return matricula.tentativas.filter(finalizada_em__isnull=False)


def aprovada(matricula):
    return finalizadas(matricula).filter(aprovado=True).first()


def tentativa_aberta(matricula):
    return matricula.tentativas.filter(finalizada_em__isnull=True).first()


def pendencias(matricula):
    """Lista do que falta para liberar a prova (vazia = pode fazer)."""
    motivos = []
    if aprovada(matricula):
        motivos.append("Você já foi aprovado(a) nesta prova.")
        return motivos
    aulas = apr.aulas_em_ordem(matricula.curso)
    feitas = apr.concluidas(matricula)
    faltam = [a for a in aulas if a.pk not in feitas]
    if faltam:
        motivos.append(f"Conclua todas as aulas: faltam {len(faltam)} ({', '.join(a.titulo for a in faltam[:3])}{'…' if len(faltam) > 3 else ''}).")
    usadas = finalizadas(matricula).count()
    if usadas >= tentativas_permitidas(matricula):
        motivos.append(f"Você usou as {usadas} tentativas. Peça ao responsável pelo curso para liberar uma nova.")
    banco = questoes_do_banco(matricula.curso).count()
    if banco == 0:
        motivos.append("O curso ainda não tem questões de prova.")
    return motivos


def questoes_do_banco(curso):
    return Questao.objects.filter(curso=curso, ativa=True, uso__in=[Questao.Uso.PROVA, Questao.Uso.AMBOS])


def sortear(curso, rng=None):
    """Sorteia N questões e embaralha as alternativas, recalculando o índice da correta."""
    rng = rng or random.SystemRandom()
    banco = list(questoes_do_banco(curso))
    escolhidas = rng.sample(banco, min(curso.questoes_sorteadas, len(banco)))
    snapshot = []
    for q in escolhidas:
        ordem = list(range(len(q.alternativas)))
        rng.shuffle(ordem)
        snapshot.append({
            "id": q.pk,
            "enunciado": q.enunciado,
            "alternativas": [q.alternativas[i] for i in ordem],
            "correta": ordem.index(q.correta),
            "explicacao": q.explicacao,
        })
    return snapshot


@transaction.atomic
def iniciar(matricula, ip=None, rng=None):
    """Retoma a tentativa aberta ou cria uma nova (se não houver pendências)."""
    Matricula.objects.select_for_update().get(pk=matricula.pk)
    aberta = tentativa_aberta(matricula)
    if aberta:
        return aberta
    if pendencias(matricula):
        return None
    numero = (matricula.tentativas.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
    return TentativaProva.objects.create(matricula=matricula, numero=numero, questoes=sortear(matricula.curso, rng), ip=ip)


def calcular_nota(questoes, respostas):
    if not questoes:
        return Decimal("0")
    acertos = sum(1 for i, q in enumerate(questoes) if str(respostas.get(str(i))) == str(q["correta"]))
    return (Decimal(100) * acertos / len(questoes)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def finalizar(tentativa, respostas):
    """Corrige, registra e, se aprovado, conclui o curso e emite o certificado (N5)."""
    from certificados import regras as cert
    from gamificacao import regras as gami
    from gamificacao.models import XPEvento

    tentativa = TentativaProva.objects.select_for_update().get(pk=tentativa.pk)
    if tentativa.finalizada_em:
        return tentativa
    limpas = {str(k): str(v) for k, v in (respostas or {}).items() if str(k).isdigit()}
    tentativa.respostas = limpas
    tentativa.nota = calcular_nota(tentativa.questoes, limpas)
    matricula = tentativa.matricula
    tentativa.aprovado = tentativa.nota >= matricula.curso.nota_minima
    tentativa.finalizada_em = timezone.now()
    tentativa.save()
    if tentativa.aprovado:
        matricula.status = Matricula.Status.CONCLUIDA
        matricula.concluida_em = timezone.now()
        matricula.save(update_fields=["status", "concluida_em"])
        gami.dar_xp(matricula.aluno, 200, XPEvento.Origem.CURSO, f"curso:{matricula.curso_id}", matricula.curso)
        cert.emitir(matricula, tentativa.nota)
        gami.avaliar_medalhas(matricula.aluno)
    return tentativa
