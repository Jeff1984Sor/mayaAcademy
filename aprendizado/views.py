import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from avaliacoes import regras as aval
from cursos.models import Aula, Curso
from cursos.player import dados_aula
from gamificacao import regras as gami

from . import regras
from .models import Matricula


def _acesso(request, aula):
    """Retorna (pode_ver, matricula, eh_previa). N1: aula só abre na ordem."""
    curso = aula.modulo.curso
    usuario = request.user
    if usuario.is_authenticated and usuario.eh_criador:
        return True, regras.matricula_de(usuario, curso), True
    matricula = regras.matricula_de(usuario, curso)
    if matricula and curso.status != Curso.Status.RASCUNHO and regras.aula_liberada(matricula, aula):
        return True, matricula, False
    if curso.status == Curso.Status.PUBLICADO and curso.aula_amostra_id == aula.pk:
        return True, None, False
    return False, matricula, False


def aula_player(request, aula_id):
    aula = get_object_or_404(Aula.objects.select_related("modulo__curso"), pk=aula_id)
    pode, matricula, previa = _acesso(request, aula)
    if not pode:
        if matricula:
            messages.warning(request, "Esta aula ainda está bloqueada: conclua as aulas anteriores primeiro.")
            return redirect("aprendizado:curso", aula.modulo.curso.slug)
        raise PermissionDenied
    blocos = list(aula.blocos.all())
    curso = aula.modulo.curso
    personagens = {p.slug: p for p in curso.personagens.all()}
    progresso = matricula.progressos.filter(aula=aula).first() if matricula else None
    estado = {
        "salvar": bool(matricula),
        "retomar": progresso.ultimo_indice if progresso and not progresso.concluida_em else 0,
        "concluidos": progresso.blocos_concluidos if progresso else [],
        "url_progresso": reverse("aprendizado:progresso", args=[aula.pk]) if matricula else "",
        "url_concluir": reverse("aprendizado:concluir", args=[aula.pk]) if matricula else "",
    }
    sair = request.GET.get("voltar", "")
    if not sair and matricula:
        sair = reverse("aprendizado:curso", args=[curso.slug])
    return render(request, "aprendizado/player.html", {
        "aula": aula,
        "dados": dados_aula(aula, blocos, personagens),
        "estado": estado,
        "previa": previa,
        "sair_url": sair if sair.startswith("/") else "",
    })


def _json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _matricula_da_aula(request, aula_id):
    aula = get_object_or_404(Aula.objects.select_related("modulo__curso"), pk=aula_id)
    matricula = regras.matricula_de(request.user, aula.modulo.curso)
    if not matricula or not regras.aula_liberada(matricula, aula):
        raise PermissionDenied
    return aula, matricula


@login_required
@require_POST
def progresso(request, aula_id):
    """N8: chamado pelo player a cada bloco concluído."""
    aula, matricula = _matricula_da_aula(request, aula_id)
    d = _json(request)
    p = regras.registrar_progresso(matricula, aula, d.get("indice"), d.get("concluidos") or [], d.get("resultados"), d.get("segundos"))
    return JsonResponse({"ok": True, "concluidos": p.blocos_concluidos})


@login_required
@require_POST
def concluir(request, aula_id):
    aula, matricula = _matricula_da_aula(request, aula_id)
    d = _json(request)
    blocos = aula.blocos.count()
    p = matricula.progressos.filter(aula=aula).first()
    feitos = set(p.blocos_concluidos) if p else set()
    feitos |= {int(i) for i in d.get("concluidos") or [] if str(i).isdigit()}
    interativos = {b.pk for b in aula.blocos.all() if b.interativo}
    if blocos and not interativos <= feitos:
        return JsonResponse({"ok": False, "erro": "Conclua todas as atividades da aula."}, status=400)
    _, xp = regras.concluir_aula(matricula, aula, d.get("resultados"), d.get("segundos"))
    proxima = regras.proxima_aula(matricula)
    return JsonResponse({
        "ok": True, "xp": xp,
        "proxima": reverse("aprendizado:aula", args=[proxima.pk]) if proxima else "",
        "curso": reverse("aprendizado:curso", args=[aula.modulo.curso.slug]),
    })


@login_required
def meus_cursos(request):
    matriculas = list(
        Matricula.objects.filter(aluno=request.user).exclude(status=Matricula.Status.CANCELADA).select_related("curso")
    )
    for m in matriculas:
        m.percentual = regras.percentual(m)
        m.proxima = regras.proxima_aula(m)
    return render(request, "aprendizado/meus_cursos.html", {"matriculas": matriculas, "xp": gami.xp_total(request.user)})


@login_required
def curso(request, slug):
    curso = get_object_or_404(Curso, slug=slug)
    matricula = regras.matricula_de(request.user, curso)
    if not matricula:
        if request.user.eh_criador:
            messages.info(request, "Você não está matriculado(a) neste curso. Use “Pré-visualizar” no Estúdio.")
            return redirect("estudio:curso", curso.pk)
        return redirect("catalogo:curso", slug)
    aulas = regras.aulas_em_ordem(curso)
    situacao = regras.situacao_aulas(matricula, aulas)
    modulos = []
    for aula, estado in situacao:
        if not modulos or modulos[-1]["modulo"].pk != aula.modulo_id:
            modulos.append({"modulo": aula.modulo, "aulas": []})
        modulos[-1]["aulas"].append({"aula": aula, "estado": estado})
    return render(request, "aprendizado/curso.html", {
        "curso": curso,
        "matricula": matricula,
        "modulos": modulos,
        "percentual": regras.percentual(matricula, aulas),
        "proxima": regras.proxima_aula(matricula),
        "pendencias_prova": aval.pendencias(matricula),
        "aprovada": aval.aprovada(matricula),
        "tentativas": aval.finalizadas(matricula),
        "tentativas_permitidas": aval.tentativas_permitidas(matricula),
        "certificado": getattr(matricula, "certificado", None),
    })


@login_required
def perfil(request):
    usuario = request.user
    if request.method == "POST":
        usuario.anonimo_no_ranking = bool(request.POST.get("anonimo"))
        usuario.save(update_fields=["anonimo_no_ranking"])
        messages.success(request, "Preferência salva.")
        return redirect("aprendizado:perfil")
    from django.contrib.auth import get_user_model

    from gamificacao.models import Medalha

    ranking = []
    org = usuario.organizacao
    if org and org.ranking_ativo:
        ranking = gami.ranking(get_user_model().objects.filter(organizacao=org))
    return render(request, "aprendizado/perfil.html", {
        "xp": gami.xp_total(usuario),
        "eventos": usuario.xp_eventos.select_related("curso")[:15],
        "conquistas": usuario.medalhas.select_related("medalha"),
        "todas": Medalha.objects.filter(ativa=True, curso__isnull=True).exclude(conquistas__aluno=usuario),
        "ranking": ranking,
        "organizacao": org,
    })
