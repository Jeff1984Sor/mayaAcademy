import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Organizacao
from cursos.models import Curso


def _token():
    return secrets.token_urlsafe(24)


class LicencaOrganizacao(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE, related_name="licencas")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="licencas")
    vagas = models.PositiveIntegerField()
    validade = models.DateField(help_text="Último dia em que os convites podem ser aceitos")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "licença de organização"
        verbose_name_plural = "licenças de organização"

    def __str__(self):
        return f"{self.organizacao} · {self.curso} ({self.vagas} vagas)"

    @property
    def vagas_usadas(self):
        """N6: a vaga só é consumida no aceite."""
        return self.convites.filter(status=Convite.Status.ACEITO).count()

    @property
    def vagas_livres(self):
        return max(0, self.vagas - self.vagas_usadas)

    @property
    def vencida(self):
        return timezone.localdate() > self.validade

    @property
    def cheia(self):
        return self.vagas_usadas >= self.vagas


class Convite(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ACEITO = "aceito", "Aceito"
        CANCELADO = "cancelado", "Cancelado"

    licenca = models.ForeignKey(LicencaOrganizacao, on_delete=models.CASCADE, related_name="convites")
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, default=_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    enviado_em = models.DateTimeField(auto_now_add=True)
    aceito_em = models.DateTimeField(null=True, blank=True)
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="convites_aceitos")

    class Meta:
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"{self.email} · {self.licenca}"

    @property
    def situacao(self):
        """Pendente de licença vencida aparece como expirado (N6)."""
        if self.status == self.Status.PENDENTE and self.licenca.vencida:
            return "expirado"
        return self.status
