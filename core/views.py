from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CadastroForm, LoginForm


def _destino_seguro(request, padrao="core:inicio"):
    destino = request.POST.get("next") or request.GET.get("next")
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return destino
    return padrao


def entrar(request):
    if request.user.is_authenticated:
        return redirect("core:inicio")
    form = LoginForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.usuario)
        return redirect(_destino_seguro(request))
    return render(request, "core/login.html", {"form": form, "next": request.GET.get("next", "")})


def cadastrar(request):
    if request.user.is_authenticated:
        return redirect("core:inicio")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Bem-vindo(a), {usuario.get_short_name()}!")
        return redirect(_destino_seguro(request))
    return render(request, "core/cadastro.html", {"form": form})


@require_POST
def sair(request):
    logout(request)
    return redirect("catalogo:home")


@login_required
def inicio(request):
    """Redireciona cada perfil para a sua área."""
    if request.user.eh_criador:
        return redirect("estudio:painel")
    return redirect("aprendizado:meus_cursos")
