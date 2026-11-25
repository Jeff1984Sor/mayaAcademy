from django.urls import path

from . import views

app_name = "avaliacoes"

urlpatterns = [
    path("<slug:slug>/", views.prova, name="prova"),
    path("<slug:slug>/responder/", views.responder, name="responder"),
    path("<slug:slug>/resultado/<int:numero>/", views.resultado, name="resultado"),
]
