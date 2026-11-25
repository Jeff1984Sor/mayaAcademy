"""Estúdio: alunos de um curso e painel geral do criador (F3)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from aprendizado import regras as apr
from aprendizado.models import Matricula, ProgressoAula
from avaliacoes import regras as aval
from avaliacoes.models import TentativaProva
from certificados import regras as cert
from core.models import AuditLog
from core.permissoes import criador_required
from cursos.models import Curso
from pagamentos.models import Pedido

Usuario = get_user_model()


@criador_required
def alunos(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    aulas = apr.aulas_em_ordem(curso)
    linhas = []
    for m in curso.matriculas.select_related("aluno", "organizacao").order_by("-criada_em"):
        finalizadas = aval.finalizadas(m)
        melhor = finalizadas.order_by("-nota").first()
        linhas.append({
            "m": m, "percentual": apr.percentual(m, aulas), "tentativas": finalizadas.count(),
            "permitidas": aval.tentativas_permitidas(m), "nota": melhor.nota if melhor else None,
            "aprovado": bool(aval.aprovada(m)), "certificado": getattr(m, "certificado", None),
        })
    return render(request, "estudio/alunos.html", {"curso": curso, "linhas": linhas})


@criador_required
@require_POST
def matricular_manual(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    email = (request.POST.get("email") or "").strip().lower()
    usuario = Usuario.objects.filter(email__iexact=email).first()
    if not usuario:
        messages.error(request, "Não há conta com esse e-mail. Peça para a pessoa se cadastrar primeiro.")
        return redirect("estudio:alunos", pk)
    m, criada = apr.matricular(usuario, curso, Matricula.Origem.MANUAL)
    AuditLog.registrar(request, "matricula_manual", m, f"Matrícula manual em {curso.titulo}", email=email)
    messages.success(request, "Matrícula feita." if criada else "A pessoa já estava matriculada (matrícula reativada se cancelada).")
    return redirect("estudio:alunos", pk)


@criador_required
@require_POST
def liberar_tentativa(request, pk):
    """N4: depois da última reprovação, só o criador libera nova tentativa (com AuditLog)."""
    m = get_object_or_404(Matricula, pk=pk)
    m.tentativas_extras += 1
    m.save(update_fields=["tentativas_extras"])
    AuditLog.registrar(request, "tentativa_extra", m, f"Tentativa extra liberada para {m.aluno.email}",
                       total_extras=m.tentativas_extras)
    messages.success(request, f"Nova tentativa liberada para {m.aluno.nome or m.aluno.email}.")
    return redirect("estudio:alunos", m.curso_id)


@criador_required
@require_POST
def emitir_certificado(request, pk):
    """Emissão manual (ex.: aprovação fora da plataforma). Registrada no AuditLog."""
    m = get_object_or_404(Matricula, pk=pk)
    if hasattr(m, "certificado"):
        messages.info(request, "Este aluno já tem certificado.")
        return redirect("estudio:alunos", m.curso_id)
    melhor = aval.finalizadas(m).order_by("-nota").first()
    nota = melhor.nota if melhor else Decimal(request.POST.get("nota") or "100")
    c = cert.emitir(m, nota, manual=True)
    if m.status != Matricula.Status.CONCLUIDA:
        m.status, m.concluida_em = Matricula.Status.CONCLUIDA, timezone.now()
        m.save(update_fields=["status", "concluida_em"])
    AuditLog.registrar(request, "certificado_manual", c, f"Certificado manual {c.codigo} para {m.aluno.email}")
    messages.success(request, f"Certificado {c.codigo} emitido.")
    return redirect("estudio:alunos", m.curso_id)


@criador_required
def relatorios(request):
    """Painel geral: matrículas, conclusão, onde o pessoal abandona, nota média e receita."""
    cursos = []
    for curso in Curso.objects.exclude(status=Curso.Status.ARQUIVADO).order_by("titulo"):
        mats = curso.matriculas.exclude(status=Matricula.Status.CANCELADA)
        total = mats.count()
        concluidas = mats.filter(status=Matricula.Status.CONCLUIDA).count()
        nota = TentativaProva.objects.filter(matricula__curso=curso, finalizada_em__isnull=False).aggregate(m=Avg("nota"))["m"]
        receita = Pedido.objects.filter(curso=curso, status=Pedido.Status.PAGO).aggregate(t=Sum("valor"))["t"] or 0
        # "Abandono": aula iniciada e não concluída, entre alunos sem atividade de conclusão depois dela.
        paradas = (
            ProgressoAula.objects.filter(matricula__curso=curso, concluida_em__isnull=True,
                                         matricula__status=Matricula.Status.ATIVA)
            .values("aula__titulo").annotate(n=Count("id")).order_by("-n")[:3]
        )
        cursos.append({
            "curso": curso, "matriculas": total, "concluidas": concluidas,
            "taxa": round(100 * concluidas / total) if total else 0, "nota_media": nota, "receita": receita,
            "paradas": list(paradas),
            "por_origem": dict(mats.values_list("origem").annotate(n=Count("id")).values_list("origem", "n")),
        })
    totais = {
        "matriculas": sum(c["matriculas"] for c in cursos),
        "concluidas": sum(c["concluidas"] for c in cursos),
        "receita": sum((c["receita"] for c in cursos), Decimal("0")),
        "alunos": Usuario.objects.filter(matriculas__isnull=False).distinct().count(),
        "certificados": Matricula.objects.filter(certificado__isnull=False).count(),
        "aprovacoes_7d": TentativaProva.objects.filter(
            aprovado=True, finalizada_em__gte=timezone.now() - timedelta(days=7)).count(),
    }
    return render(request, "estudio/relatorios.html", {"cursos": cursos, "totais": totais})
