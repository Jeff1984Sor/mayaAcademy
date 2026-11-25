from django.contrib import admin

from .models import TentativaProva


@admin.register(TentativaProva)
class TentativaProvaAdmin(admin.ModelAdmin):
    list_display = ["matricula", "numero", "nota", "aprovado", "iniciada_em", "finalizada_em", "ip"]
    list_filter = ["aprovado"]
    readonly_fields = ["questoes", "respostas"]
