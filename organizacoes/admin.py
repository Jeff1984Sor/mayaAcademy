from django.contrib import admin

from .models import Convite, LicencaOrganizacao


@admin.register(LicencaOrganizacao)
class LicencaAdmin(admin.ModelAdmin):
    list_display = ["organizacao", "curso", "vagas", "validade"]


@admin.register(Convite)
class ConviteAdmin(admin.ModelAdmin):
    list_display = ["email", "licenca", "status", "enviado_em", "aceito_em"]
    list_filter = ["status"]
