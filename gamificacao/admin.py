from django.contrib import admin

from .models import Medalha, MedalhaAluno, XPEvento


@admin.register(Medalha)
class MedalhaAdmin(admin.ModelAdmin):
    list_display = ["__str__", "criterio", "parametro", "curso", "xp_bonus", "ativa"]


admin.site.register(MedalhaAluno)


@admin.register(XPEvento)
class XPEventoAdmin(admin.ModelAdmin):
    list_display = ["aluno", "pontos", "origem", "referencia", "criado_em"]
    list_filter = ["origem"]
