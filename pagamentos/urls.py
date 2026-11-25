from django.urls import path

from . import views

app_name = "pagamentos"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("comprar/<slug:slug>/", views.comprar, name="comprar"),
    path("pedido/<int:pk>/", views.pedido, name="pedido"),
    path("pedido/<int:pk>/manual/", views.confirmar_manual, name="confirmar_manual"),
    path("webhook/<str:nome>/", views.webhook, name="webhook"),
]
