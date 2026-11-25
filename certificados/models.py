from django.db import models

from aprendizado.models import Matricula


class Certificado(models.Model):
    """Dados copiados no momento da emissão: o certificado não muda se o curso mudar depois."""

    matricula = models.OneToOneField(Matricula, on_delete=models.PROTECT, related_name="certificado")
    codigo = models.CharField("código de validação", max_length=20, unique=True)
    nome_aluno = models.CharField(max_length=150)
    titulo_curso = models.CharField(max_length=200)
    carga_horaria = models.PositiveIntegerField()
    nota = models.DecimalField(max_digits=5, decimal_places=2)
    versao_curso = models.PositiveIntegerField(default=1)
    emitido_em = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(upload_to="certificados/", blank=True)
    manual = models.BooleanField(default=False, help_text="Emitido manualmente pelo criador")

    class Meta:
        ordering = ["-emitido_em"]

    def __str__(self):
        return f"{self.codigo} · {self.nome_aluno}"
