from django.contrib import admin

from .models import Certificado


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome_aluno", "titulo_curso", "nota", "emitido_em", "manual"]
    search_fields = ["codigo", "nome_aluno"]
