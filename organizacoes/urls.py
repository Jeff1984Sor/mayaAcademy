from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/", views.org_form, name="nova"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.org_form, name="editar"),
    path("<int:pk>/gestor/", views.tornar_gestor, name="tornar_gestor"),
    path("<int:org_pk>/licenca/nova/", views.licenca_form, name="licenca_nova"),
    path("<int:org_pk>/licenca/<int:pk>/", views.licenca_form, name="licenca"),
    path("painel/", views.painel, name="painel"),
    path("painel/convidar/", views.convidar, name="convidar"),
    path("painel/convite/<int:pk>/cancelar/", views.cancelar_convite, name="cancelar_convite"),
    path("painel/ranking/", views.ranking, name="ranking"),
    path("minha/", views.minha_organizacao, name="minha"),
    path("convite/<str:token>/", views.convite, name="convite"),
]
