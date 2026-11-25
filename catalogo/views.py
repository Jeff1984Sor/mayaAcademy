from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from aprendizado import regras as apr
from core.models import AuditLog
from cursos.models import Curso


def home(request):
    cursos = (
        Curso.objects.filter(status=Curso.Status.PUBLICADO)
        .annotate(n_aulas=Count("modulos__aulas", distinct=True))
        .order_by("titulo")
    )
    return render(request, "catalogo/home.html", {"cursos": cursos})


def curso(request, slug):
    curso = get_object_or_404(Curso.objects.prefetch_related("modulos__aulas"), slug=slug)
    if curso.status != Curso.Status.PUBLICADO and not (request.user.is_authenticated and request.user.eh_criador):
        raise Http404
    matricula = apr.matricula_de(request.user, curso)
    pedido = None
    if request.user.is_authenticated and curso.modo_acesso == Curso.Acesso.PAGO and not matricula:
        pedido = curso.pedidos.filter(aluno=request.user, status="pendente").first()
    return render(request, "catalogo/curso.html", {
        "curso": curso, "matricula": matricula, "pedido": pedido,
        "n_aulas": sum(len(m.aulas.all()) for m in curso.modulos.all()),
    })


@login_required
@require_POST
def matricular(request, slug):
    """Matrícula gratuita (F4). Pago e convite têm fluxos próprios."""
    curso = get_object_or_404(Curso, slug=slug, status=Curso.Status.PUBLICADO)
    if curso.modo_acesso != Curso.Acesso.GRATUITO:
        messages.error(request, "Este curso não tem matrícula gratuita.")
        return redirect("catalogo:curso", slug)
    matricula, criada = apr.matricular(request.user, curso)
    if criada:
        AuditLog.registrar(request, "matricula_gratuita", matricula, f"Matrícula em {curso.titulo}")
        messages.success(request, f"Matrícula feita! Bom curso, {request.user.get_short_name()}.")
    return redirect("aprendizado:curso", slug)


def saude(request):
    """Health check simples para monitoramento e para o Gate 1."""
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        banco = "ok"
    except Exception:  # noqa: BLE001
        banco = "erro"
    return JsonResponse({"app": "ok", "banco": banco}, status=200 if banco == "ok" else 503)
