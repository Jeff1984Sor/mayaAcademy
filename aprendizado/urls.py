from django.urls import path

from . import views

app_name = "aprendizado"

urlpatterns = [
    path("", views.meus_cursos, name="meus_cursos"),
    path("perfil/", views.perfil, name="perfil"),
    path("curso/<slug:slug>/", views.curso, name="curso"),
    path("aula/<int:aula_id>/", views.aula_player, name="aula"),
    path("aula/<int:aula_id>/progresso/", views.progresso, name="progresso"),
    path("aula/<int:aula_id>/concluir/", views.concluir, name="concluir"),
]
