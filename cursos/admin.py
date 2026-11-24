from django.contrib import admin

from .models import Aula, BlocoAula, Curso, Modulo, Personagem, Questao


class PersonagemInline(admin.TabularInline):
    model = Personagem
    extra = 0


class ModuloInline(admin.TabularInline):
    model = Modulo
    extra = 0


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "status", "modo_acesso", "versao", "carga_horaria"]
    list_filter = ["status", "modo_acesso", "nivel"]
    search_fields = ["titulo", "slug"]
    prepopulated_fields = {"slug": ["titulo"]}
    inlines = [PersonagemInline, ModuloInline]
    raw_id_fields = ["aula_amostra"]


class AulaInline(admin.TabularInline):
    model = Aula
    extra = 0
    fields = ["ordem", "titulo", "duracao_min", "xp"]


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ["titulo", "curso", "ordem"]
    list_filter = ["curso"]
    list_select_related = ["curso"]
    inlines = [AulaInline]


class BlocoInline(admin.StackedInline):
    model = BlocoAula
    extra = 0
    fields = ["ordem", "tipo", "titulo", "roteiro", "texto_tela", "config"]


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "modulo", "ordem", "precisa_revisao"]
    list_filter = ["modulo__curso", "precisa_revisao"]
    list_select_related = ["modulo__curso"]
    inlines = [BlocoInline]


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "curso", "uso", "dificuldade", "ativa"]
    list_filter = ["curso", "uso", "dificuldade", "ativa"]
    list_select_related = ["curso"]
    search_fields = ["enunciado"]
