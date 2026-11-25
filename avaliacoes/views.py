from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from aprendizado import regras as apr
from core.models import ip_do_request
from cursos.models import Curso

from . import regras
from .models import TentativaProva


def _matricula(request, slug):
    curso = get_object_or_404(Curso, slug=slug)
    matricula = apr.matricula_de(request.user, curso)
    if not matricula:
        messages.error(request, "Você não está matriculado(a) neste curso.")
        return curso, None
    return curso, matricula


@login_required
def prova(request, slug):
    curso, matricula = _matricula(request, slug)
    if not matricula:
        return redirect("catalogo:curso", slug)
    tentativa = regras.tentativa_aberta(matricula)
    if request.method == "POST" and request.POST.get("acao") == "iniciar":
        tentativa = regras.iniciar(matricula, ip=ip_do_request(request))
        if not tentativa:
            for p in regras.pendencias(matricula):
                messages.error(request, p)
            return redirect("aprendizado:curso", slug)
        return redirect("avaliacoes:prova", slug)
    return render(request, "avaliacoes/prova.html", {
        "curso": curso, "matricula": matricula, "tentativa": tentativa,
        "pendencias": regras.pendencias(matricula) if not tentativa else [],
        "usadas": regras.finalizadas(matricula).count(),
        "permitidas": regras.tentativas_permitidas(matricula),
    })


@login_required
@require_POST
def responder(request, slug):
    curso, matricula = _matricula(request, slug)
    if not matricula:
        return redirect("catalogo:curso", slug)
    tentativa = regras.tentativa_aberta(matricula)
    if not tentativa:
        return redirect("avaliacoes:prova", slug)
    respostas = {k[2:]: v for k, v in request.POST.items() if k.startswith("q_")}
    if len(respostas) < len(tentativa.questoes):
        messages.error(request, "Responda todas as questões antes de enviar.")
        return redirect("avaliacoes:prova", slug)
    tentativa = regras.finalizar(tentativa, respostas)
    return redirect("avaliacoes:resultado", slug, tentativa.numero)


@login_required
def resultado(request, slug, numero):
    curso, matricula = _matricula(request, slug)
    if not matricula:
        return redirect("catalogo:curso", slug)
    tentativa = get_object_or_404(TentativaProva, matricula=matricula, numero=numero, finalizada_em__isnull=False)
    itens = [
        {**q, "resposta": int(tentativa.respostas.get(str(i), -1)), "acertou": str(tentativa.respostas.get(str(i))) == str(q["correta"])}
        for i, q in enumerate(tentativa.questoes)
    ]
    return render(request, "avaliacoes/resultado.html", {
        "curso": curso, "matricula": matricula, "tentativa": tentativa, "itens": itens,
        "restam": max(0, regras.tentativas_permitidas(matricula) - regras.finalizadas(matricula).count()),
        "certificado": getattr(matricula, "certificado", None),
    })
