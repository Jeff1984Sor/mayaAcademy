from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from cursos.models import Aula, Curso
from cursos.player import dados_aula


def _pode_ver(request, aula):
    curso = aula.modulo.curso
    if request.user.is_authenticated and request.user.eh_criador:
        return True
    # Aula de amostra de curso publicado é aberta a qualquer visitante.
    if curso.status == Curso.Status.PUBLICADO and curso.aula_amostra_id == aula.pk:
        return True
    # Matrícula e liberação em ordem entram na F3.
    return False


def aula_player(request, aula_id):
    aula = get_object_or_404(Aula.objects.select_related("modulo__curso"), pk=aula_id)
    if not _pode_ver(request, aula):
        raise PermissionDenied
    blocos = list(aula.blocos.all())
    personagens = {p.slug: p for p in aula.modulo.curso.personagens.all()}
    return render(request, "aprendizado/player.html", {
        "aula": aula,
        "dados": dados_aula(aula, blocos, personagens),
        "previa": request.user.is_authenticated and request.user.eh_criador,
        "sair_url": request.GET.get("voltar", ""),
    })


@login_required
def meus_cursos(request):
    return render(request, "aprendizado/meus_cursos.html")
