from django.urls import path

from . import views

app_name = "estudio"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("busca/", views.busca, name="busca"),
    path("curso/novo/", views.curso_novo, name="curso_novo"),
    path("curso/<int:pk>/", views.curso, name="curso"),
    path("curso/<int:pk>/editar/", views.curso_editar, name="curso_editar"),
    path("curso/<int:pk>/publicar/", views.curso_publicar, name="curso_publicar"),
    path("curso/<int:pk>/arquivar/", views.curso_arquivar, name="curso_arquivar"),
    path("curso/<int:pk>/exportar/", views.curso_exportar, name="curso_exportar"),
    path("curso/<int:pk>/pacote/", views.curso_pacote, name="curso_pacote"),
    path("curso/<int:curso_pk>/personagem/novo/", views.personagem_form, name="personagem_novo"),
    path("curso/<int:curso_pk>/personagem/<int:pk>/", views.personagem_form, name="personagem"),
    path("curso/<int:curso_pk>/personagem/<int:pk>/excluir/", views.personagem_excluir, name="personagem_excluir"),
    path("curso/<int:curso_pk>/modulo/novo/", views.modulo_form, name="modulo_novo"),
    path("curso/<int:curso_pk>/modulo/<int:pk>/", views.modulo_form, name="modulo"),
    path("curso/<int:curso_pk>/modulo/<int:pk>/excluir/", views.modulo_excluir, name="modulo_excluir"),
    path("curso/<int:curso_pk>/questoes/", views.questoes, name="questoes"),
    path("curso/<int:curso_pk>/questoes/nova/", views.questao_form, name="questao_nova"),
    path("curso/<int:curso_pk>/questoes/<int:pk>/", views.questao_form, name="questao"),
    path("modulo/<int:modulo_pk>/aula/nova/", views.aula_nova, name="aula_nova"),
    path("aula/<int:pk>/", views.aula, name="aula"),
    path("aula/<int:pk>/excluir/", views.aula_excluir, name="aula_excluir"),
    path("aula/<int:aula_pk>/bloco/novo/", views.bloco_novo, name="bloco_novo"),
    path("bloco/<int:pk>/", views.bloco, name="bloco"),
    path("bloco/<int:pk>/excluir/", views.bloco_excluir, name="bloco_excluir"),
    path("bloco/<int:pk>/duplicar/", views.bloco_duplicar, name="bloco_duplicar"),
    path("bloco/<int:pk>/previa/", views.bloco_previa, name="bloco_previa"),
    path("reordenar/<str:tipo>/", views.reordenar, name="reordenar"),
    path("audio/<str:escopo>/<int:pk>/", views.gerar_audio, name="gerar_audio"),
    path("importar/", views.importar_roteiro, name="importar"),
    path("importar/confirmar/", views.importar_confirmar, name="importar_confirmar"),
]
