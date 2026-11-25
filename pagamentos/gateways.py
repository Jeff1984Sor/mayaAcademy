"""Interface isolada de gateway (seção 9): criar_cobranca e processar_webhook.

A matrícula paga só nasce do webhook confirmado (N7), nunca do redirect, e o webhook é idempotente.
Enquanto o gateway real não é escolhido, o provedor "manual" faz o papel: o criador confirma o
pagamento no painel, e isso passa pelo MESMO caminho do webhook (confirmar_pagamento).
"""
import hmac
import json
import uuid

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from aprendizado import regras as apr
from aprendizado.models import Matricula

from .models import Pedido


class ErroWebhook(Exception):
    pass


@transaction.atomic
def confirmar_pagamento(id_externo, status, payload):
    """Aplica um evento do gateway. Idempotente: o mesmo evento duas vezes não duplica nada (N7)."""
    pedido = Pedido.objects.select_for_update().filter(id_externo=id_externo).first()
    if pedido is None:
        raise ErroWebhook(f"pedido não encontrado: {id_externo}")
    pedido.payload = payload
    if status == "pago" and pedido.status != Pedido.Status.PAGO:
        pedido.status = Pedido.Status.PAGO
        pedido.pago_em = timezone.now()
        pedido.save(update_fields=["status", "pago_em", "payload"])
        apr.matricular(pedido.aluno, pedido.curso, Matricula.Origem.COMPRA)
    elif status in ("cancelado", "estornado") and pedido.status != status:
        pedido.status = status
        pedido.save(update_fields=["status", "payload"])
        if status == "estornado":
            Matricula.objects.filter(aluno=pedido.aluno, curso=pedido.curso, origem=Matricula.Origem.COMPRA).update(
                status=Matricula.Status.CANCELADA)
    else:
        pedido.save(update_fields=["payload"])
    return pedido


class GatewayManual:
    """Sem cobrança online: o pedido fica aguardando e o criador confirma no painel."""

    nome = "manual"

    def criar_cobranca(self, pedido, request):
        pedido.id_externo = f"manual-{uuid.uuid4().hex}"
        pedido.save(update_fields=["id_externo"])
        return reverse("pagamentos:pedido", args=[pedido.pk])

    def processar_webhook(self, request):
        """Webhook de teste/integração: JSON {id_externo, status} com o segredo no cabeçalho."""
        segredo = settings.PAGAMENTOS_WEBHOOK_SEGREDO
        recebido = request.headers.get("X-Webhook-Segredo", "")
        if not segredo or not hmac.compare_digest(segredo, recebido):
            raise ErroWebhook("assinatura inválida")
        try:
            dados = json.loads(request.body or b"{}")
        except json.JSONDecodeError as erro:
            raise ErroWebhook("JSON inválido") from erro
        return confirmar_pagamento(str(dados.get("id_externo")), str(dados.get("status")), dados)


GATEWAYS = {"manual": GatewayManual}


def gateway(nome=None):
    nome = nome or settings.PAGAMENTOS_GATEWAY
    if nome not in GATEWAYS:
        raise ErroWebhook(f"gateway desconhecido: {nome}")
    return GATEWAYS[nome]()
