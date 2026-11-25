from django.contrib import admin

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["pk", "aluno", "curso", "valor", "status", "gateway", "criado_em", "pago_em"]
    list_filter = ["status", "gateway"]
