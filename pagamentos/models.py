from django.conf import settings
from django.db import models

from cursos.models import Curso


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Aguardando pagamento"
        PAGO = "pago", "Pago"
        CANCELADO = "cancelado", "Cancelado"
        ESTORNADO = "estornado", "Estornado"

    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="pedidos")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE, db_index=True)
    gateway = models.CharField(max_length=30)
    id_externo = models.CharField(max_length=120, null=True, blank=True, unique=True)
    payload = models.JSONField(default=dict, blank=True, help_text="Último webhook recebido")
    criado_em = models.DateTimeField(auto_now_add=True)
    pago_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido {self.pk} · {self.aluno} · {self.curso}"
