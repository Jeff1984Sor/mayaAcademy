from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Organizacao, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "nome", "papel", "organizacao", "is_active"]
    list_filter = ["papel", "organizacao", "is_active", "is_staff"]
    search_fields = ["email", "nome"]
    list_select_related = ["organizacao"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados", {"fields": ("nome", "organizacao", "papel", "anonimo_no_ranking")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nome", "papel", "password1", "password2")}),
    )


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "contato_email", "ativa"]
    list_filter = ["ativa"]
    search_fields = ["nome", "cnpj"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["criado_em", "acao", "usuario", "objeto_tipo", "objeto_id", "ip"]
    list_filter = ["acao"]
    search_fields = ["descricao", "objeto_id", "usuario__email"]
    list_select_related = ["usuario"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
