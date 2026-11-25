from django.urls import path

from . import views

app_name = "geracao"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("configurar-ia/", views.config_ia, name="config_ia"),
    path("configurar-ia/modelos/", views.config_ia_modelos, name="config_ia_modelos"),
    path("configurar-ia/testar/", views.config_ia_testar, name="config_ia_testar"),
    path("novo/", views.nova, name="nova"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/situacao/", views.situacao, name="situacao"),
    path("<int:pk>/ementa/", views.ementa_salvar, name="ementa_salvar"),
    path("<int:pk>/repetir/", views.reprocessar, name="reprocessar"),
    path("aula/<int:pk>/de-novo/", views.aula_de_novo, name="aula_de_novo"),
    path("trecho/bloco/<int:pk>/", views.trecho_bloco, name="trecho_bloco"),
]
