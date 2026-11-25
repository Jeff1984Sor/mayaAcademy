from django.contrib import admin

from .models import AulaGerada, ChamadaLLM, ConfiguracaoIA, Geracao


class ChamadaInline(admin.TabularInline):
    model = ChamadaLLM
    extra = 0
    can_delete = False
    readonly_fields = ["etapa", "referencia", "modelo", "tokens_entrada", "tokens_saida", "custo_usd", "duracao_s", "sucesso", "erro"]


@admin.register(Geracao)
class GeracaoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "status", "curso", "criador", "criado_em"]
    list_filter = ["status"]
    readonly_fields = ["mapa", "ementa"]
    inlines = [ChamadaInline]


@admin.register(AulaGerada)
class AulaGeradaAdmin(admin.ModelAdmin):
    list_display = ["__str__", "geracao", "status", "tentativas"]
    list_filter = ["status"]


@admin.register(ConfiguracaoIA)
class ConfiguracaoIAAdmin(admin.ModelAdmin):
    list_display = ["modelo", "preco_entrada_1m", "preco_saida_1m", "atualizado_em", "atualizado_por"]
    exclude = ["chave_cifrada"]  # a chave só é editada pela tela (Estúdio › Configurar IA)
