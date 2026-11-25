from django.urls import path

from . import views

app_name = "certificados"

urlpatterns = [
    path("", views.validar, name="buscar"),
    path("meus/", views.meus, name="meus"),
    path("<str:codigo>/", views.validar, name="validar"),
    path("<str:codigo>/pdf/", views.baixar, name="baixar"),
]
