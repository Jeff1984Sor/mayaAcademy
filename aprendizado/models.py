from django.conf import settings
from django.db import models

from core.models import Organizacao
from cursos.models import Aula, Curso


class Matricula(models.Model):
    class Origem(models.TextChoices):
        GRATUITA = "gratuita", "Gratuita"
        COMPRA = "compra", "Compra"
        CONVITE_ORG = "convite_org", "Convite de organização"
        MANUAL = "manual", "Manual (criador)"

    class Status(models.TextChoices):
        ATIVA = "ativa", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matriculas")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="matriculas")
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.GRATUITA)
    organizacao = models.ForeignKey(Organizacao, null=True, blank=True, on_delete=models.SET_NULL, related_name="matriculas")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVA, db_index=True)
    versao_curso = models.PositiveIntegerField(default=1)
    tentativas_extras = models.PositiveSmallIntegerField(default=0, help_text="Tentativas de prova liberadas pelo criador")
    criada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("aluno", "curso")]
        ordering = ["-criada_em"]
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"

    def __str__(self):
        return f"{self.aluno} · {self.curso}"

    @property
    def ativa(self):
        return self.status in (self.Status.ATIVA, self.Status.CONCLUIDA)


class ProgressoAula(models.Model):
    """Progresso salvo a cada bloco concluído (N8)."""

    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name="progressos")
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="progressos")
    blocos_concluidos = models.JSONField(default=list, blank=True)
    ultimo_indice = models.PositiveIntegerField(default=0)
    resultados = models.JSONField(default=dict, blank=True)
    tempo_gasto_s = models.PositiveIntegerField(default=0)
    iniciada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("matricula", "aula")]
        verbose_name = "progresso na aula"
        verbose_name_plural = "progressos nas aulas"

    def __str__(self):
        return f"{self.matricula} · {self.aula}"
