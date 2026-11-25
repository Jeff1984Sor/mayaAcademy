from django.db import models

from aprendizado.models import Matricula


class TentativaProva(models.Model):
    """Snapshot das questões sorteadas (com alternativas na ordem mostrada) e das respostas (N3)."""

    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name="tentativas")
    numero = models.PositiveSmallIntegerField()
    questoes = models.JSONField(default=list, help_text="[{id, enunciado, alternativas, correta, explicacao}]")
    respostas = models.JSONField(default=dict, blank=True)
    nota = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    aprovado = models.BooleanField(null=True)
    iniciada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = [("matricula", "numero")]
        ordering = ["matricula", "numero"]
        verbose_name = "tentativa de prova"
        verbose_name_plural = "tentativas de prova"

    def __str__(self):
        return f"{self.matricula} · tentativa {self.numero}"

    @property
    def aberta(self):
        return self.finalizada_em is None
