"""Gerador de curso a partir de PDF (seção 8.4)."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from cursos.models import Aula, Curso


class Geracao(models.Model):
    class Status(models.TextChoices):
        NA_FILA = "na_fila", "Na fila"
        EXTRAINDO = "extraindo", "Extraindo o texto do PDF"
        MAPEANDO = "mapeando", "Mapeando o conteúdo"
        PROPONDO = "propondo", "Propondo a ementa"
        EMENTA = "ementa", "Ementa aguardando sua revisão"
        GERANDO = "gerando", "Gerando as aulas"
        PRONTO = "pronto", "Rascunho pronto"
        ERRO = "erro", "Erro"

    class Tom(models.TextChoices):
        LEVE = "leve", "Leve"
        FORMAL = "formal", "Formal"
        TECNICO = "tecnico", "Técnico"

    EM_ANDAMENTO = {Status.NA_FILA, Status.EXTRAINDO, Status.MAPEANDO, Status.PROPONDO, Status.GERANDO}

    criador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    titulo = models.CharField("nome de trabalho", max_length=200)
    publico = models.CharField("público-alvo", max_length=300)
    nivel = models.CharField(max_length=20, choices=Curso.Nivel.choices, default=Curso.Nivel.INICIANTE)
    tom = models.CharField(max_length=20, choices=Tom.choices, default=Tom.LEVE)
    duracao_horas = models.PositiveSmallIntegerField("duração-alvo (h)", default=4)
    n_modulos = models.PositiveSmallIntegerField("nº aproximado de módulos", default=4)
    idioma = models.CharField(max_length=10, default="pt-BR")
    narrador_nome = models.CharField("nome do narrador", max_length=80, default="Narrador")
    mascote_nome = models.CharField("nome do mascote", max_length=80, default="Maya")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NA_FILA, db_index=True)
    etapa = models.CharField(max_length=200, blank=True)
    progresso = models.PositiveSmallIntegerField(default=0)
    erro = models.TextField(blank=True)

    mapa = models.JSONField(default=dict, blank=True)
    ementa = models.JSONField(default=dict, blank=True)
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.SET_NULL, related_name="geracoes")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "geração por PDF"
        verbose_name_plural = "gerações por PDF"

    def __str__(self):
        return self.titulo

    @property
    def em_andamento(self):
        return self.status in self.EM_ANDAMENTO

    def marcar(self, status=None, etapa=None, progresso=None, erro=None):
        campos = ["atualizado_em"]
        for nome, valor in (("status", status), ("etapa", etapa), ("progresso", progresso), ("erro", erro)):
            if valor is not None:
                setattr(self, nome, valor)
                campos.append(nome)
        self.save(update_fields=campos)

    def custo_total(self):
        return self.chamadas.aggregate(t=Sum("custo_usd"))["t"] or Decimal("0")


class ArquivoPDF(models.Model):
    geracao = models.ForeignKey(Geracao, on_delete=models.CASCADE, related_name="arquivos")
    arquivo = models.FileField(upload_to="geracao/pdfs/")
    nome = models.CharField(max_length=255)
    paginas = models.PositiveIntegerField(default=0)
    primeira_pagina = models.PositiveIntegerField(default=1, help_text="Número global da 1ª página deste arquivo")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nome


class PaginaPDF(models.Model):
    """Texto de uma página. O número é global (somando os PDFs na ordem do envio)."""

    geracao = models.ForeignKey(Geracao, on_delete=models.CASCADE, related_name="paginas")
    arquivo = models.ForeignKey(ArquivoPDF, on_delete=models.CASCADE, related_name="paginas_extraidas")
    numero = models.PositiveIntegerField()
    texto = models.TextField(blank=True)
    ocr = models.BooleanField(default=False)
    sem_texto = models.BooleanField(default=False)

    class Meta:
        ordering = ["numero"]
        unique_together = [("geracao", "numero")]

    def __str__(self):
        return f"p. {self.numero}"


class AulaGerada(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Na fila"
        GERANDO = "gerando", "Gerando"
        OK = "ok", "Gerada"
        REVISAO = "revisao", "Precisa de revisão"
        ERRO = "erro", "Erro"

    geracao = models.ForeignKey(Geracao, on_delete=models.CASCADE, related_name="aulas_geradas")
    aula = models.OneToOneField(Aula, null=True, blank=True, on_delete=models.SET_NULL, related_name="geracao_info")
    modulo_num = models.PositiveSmallIntegerField()
    aula_num = models.PositiveSmallIntegerField()
    titulo = models.CharField(max_length=200)
    paginas = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    tentativas = models.PositiveSmallIntegerField(default=0)
    problemas = models.JSONField(default=list, blank=True)
    instrucao_extra = models.CharField(max_length=500, blank=True)
    questoes_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["modulo_num", "aula_num"]

    def __str__(self):
        return f"{self.modulo_num}.{self.aula_num} {self.titulo}"


class ChamadaLLM(models.Model):
    """Log de cada chamada à IA: etapa, tokens, custo e duração (painel de custo)."""

    class Etapa(models.TextChoices):
        MAPA = "mapa", "Mapa do conteúdo"
        EMENTA = "ementa", "Ementa"
        AULA = "aula", "Aula"

    geracao = models.ForeignKey(Geracao, on_delete=models.CASCADE, related_name="chamadas")
    etapa = models.CharField(max_length=20, choices=Etapa.choices)
    referencia = models.CharField(max_length=200, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    custo_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    duracao_s = models.FloatField(default=0)
    sucesso = models.BooleanField(default=True)
    erro = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]
        verbose_name = "chamada à IA"
        verbose_name_plural = "chamadas à IA"
