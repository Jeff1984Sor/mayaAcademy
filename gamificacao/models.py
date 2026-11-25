from django.conf import settings
from django.db import models

from cursos.models import Curso


class XPEvento(models.Model):
    class Origem(models.TextChoices):
        AULA = "aula", "Aula concluída"
        QUIZ = "quiz", "Quiz acertado de primeira"
        INTERACAO = "interacao", "Interação completada"
        CURSO = "curso", "Curso concluído"
        MEDALHA = "medalha", "Medalha"

    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_eventos")
    pontos = models.IntegerField()
    origem = models.CharField(max_length=20, choices=Origem.choices)
    referencia = models.CharField(max_length=100, help_text="Evita contar o mesmo evento duas vezes")
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("aluno", "origem", "referencia")]
        ordering = ["-criado_em"]
        verbose_name = "evento de XP"
        verbose_name_plural = "eventos de XP"


class Medalha(models.Model):
    class Criterio(models.TextChoices):
        PRIMEIRO_CERTIFICADO = "primeiro_certificado", "Primeiro certificado"
        NOTA_100 = "nota_100", "Nota 100 na prova"
        MARATONISTA = "maratonista", "Curso concluído em até N dias"
        CURSO_CONCLUIDO = "curso_concluido", "Concluir o curso"
        XP_TOTAL = "xp_total", "Atingir N de XP"

    slug = models.SlugField(max_length=60, unique=True)
    nome = models.CharField(max_length=80)
    descricao = models.CharField(max_length=200)
    icone = models.CharField(max_length=8, default="🏅")
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.CASCADE, related_name="medalhas",
                              help_text="Vazio = medalha global")
    criterio = models.CharField(max_length=30, choices=Criterio.choices)
    parametro = models.PositiveIntegerField(default=0, help_text="Dias (maratonista) ou XP (xp_total)")
    xp_bonus = models.PositiveIntegerField(default=50)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "medalhas"

    def __str__(self):
        return f"{self.icone} {self.nome}"


class MedalhaAluno(models.Model):
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medalhas")
    medalha = models.ForeignKey(Medalha, on_delete=models.CASCADE, related_name="conquistas")
    conquistada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("aluno", "medalha")]
        ordering = ["-conquistada_em"]
        verbose_name = "medalha do aluno"
        verbose_name_plural = "medalhas dos alunos"
