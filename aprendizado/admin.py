from django.contrib import admin

from .models import Matricula, ProgressoAula


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ["aluno", "curso", "origem", "status", "organizacao", "criada_em"]
    list_filter = ["status", "origem", "curso"]
    search_fields = ["aluno__email", "aluno__nome"]


@admin.register(ProgressoAula)
class ProgressoAulaAdmin(admin.ModelAdmin):
    list_display = ["matricula", "aula", "concluida_em", "tempo_gasto_s"]
