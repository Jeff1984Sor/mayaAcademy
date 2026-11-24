from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "core"

urlpatterns = [
    path("entrar/", views.entrar, name="login"),
    path("cadastro/", views.cadastrar, name="cadastro"),
    path("sair/", views.sair, name="logout"),
    path("inicio/", views.inicio, name="inicio"),
    path(
        "senha/recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="core/senha_recuperar.html",
            email_template_name="core/email_senha.txt",
            subject_template_name="core/email_senha_assunto.txt",
            success_url=reverse_lazy("core:senha_enviada"),
        ),
        name="senha_recuperar",
    ),
    path(
        "senha/enviada/",
        auth_views.PasswordResetDoneView.as_view(template_name="core/senha_enviada.html"),
        name="senha_enviada",
    ),
    path(
        "senha/nova/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/senha_nova.html", success_url=reverse_lazy("core:senha_ok")
        ),
        name="senha_nova",
    ),
    path(
        "senha/ok/",
        auth_views.PasswordResetCompleteView.as_view(template_name="core/senha_ok.html"),
        name="senha_ok",
    ),
]
