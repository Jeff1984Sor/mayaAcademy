from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "MayaAcademy — administração"
admin.site.site_title = "MayaAcademy"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("conta/", include("core.urls")),
    path("estudio/", include("estudio.urls")),
    path("aprender/", include("aprendizado.urls")),
    path("", include("catalogo.urls")),
]
