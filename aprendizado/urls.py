from django.urls import path

from . import views

app_name = "aprendizado"

urlpatterns = [
    path("", views.meus_cursos, name="meus_cursos"),
    path("aula/<int:aula_id>/", views.aula_player, name="aula"),
]
