from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.home, name="home"),
    path("saude/", views.saude, name="saude"),
    path("curso/<slug:slug>/", views.curso, name="curso"),
    path("curso/<slug:slug>/matricular/", views.matricular, name="matricular"),
]
