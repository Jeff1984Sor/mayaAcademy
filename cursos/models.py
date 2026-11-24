import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from . import blocos as registro
from .roteiro import parse_roteiro


class Curso(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        PUBLICADO = "publicado", "Publicado"
        ARQUIVADO = "arquivado", "Arquivado"

    class Acesso(models.TextChoices):
        GRATUITO = "gratuito", "Gratuito"
        PAGO = "pago", "Pago"
        CONVITE = "convite", "Só por convite"

    class Nivel(models.TextChoices):
        INICIANTE = "iniciante", "Iniciante"
        INTERMEDIARIO = "intermediario", "Intermediário"
        AVANCADO = "avancado", "Avançado"

    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    subtitulo = models.CharField(max_length=300, blank=True)
    descricao = models.TextField("descrição longa", blank=True)
    capa = models.ImageField(upload_to="cursos/capas/", blank=True)
    trailer_audio = models.FileField(upload_to="cursos/trailers/", blank=True)
    trailer_lottie = models.FileField(upload_to="cursos/trailers/", blank=True)
    carga_horaria = models.PositiveIntegerField("carga horária (h)", default=1)
    nivel = models.CharField(max_length=20, choices=Nivel.choices, default=Nivel.INICIANTE)
    categoria = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    modo_acesso = models.CharField(max_length=20, choices=Acesso.choices, default=Acesso.GRATUITO)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nota_minima = models.PositiveSmallIntegerField("nota mínima da prova (%)", default=70)
    tentativas = models.PositiveSmallIntegerField("nº de tentativas da prova", default=3)
    questoes_sorteadas = models.PositiveSmallIntegerField("nº de questões sorteadas", default=10)
    versao = models.PositiveIntegerField(default=1)
    publicado_em = models.DateTimeField(null=True, blank=True)
    aula_amostra = models.ForeignKey(
        "Aula", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cor_primaria = models.CharField(max_length=7, default="#1E2D6B", help_text="Padrão MayaCorp: Navy #1E2D6B")
    cor_secundaria = models.CharField(max_length=7, default="#F5A623", help_text="Padrão MayaCorp: Amber #F5A623")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["titulo"]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)[:200]
        super().save(*args, **kwargs)

    @property
    def publicado(self):
        return self.status == self.Status.PUBLICADO


class Personagem(models.Model):
    class Papel(models.TextChoices):
        NARRADOR = "narrador", "Narrador"
        MASCOTE = "mascote", "Mascote"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="personagens")
    slug = models.SlugField(
        max_length=40, help_text="Identificador usado no roteiro, ex.: @maya: Olá!"
    )
    nome = models.CharField(max_length=80)
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.NARRADOR)
    voz_nome = models.CharField(
        "voz TTS", max_length=80, default="pt-BR-Neural2-C",
        help_text="Nome da voz no provedor de TTS",
    )
    voz_velocidade = models.FloatField(default=1.0)
    voz_tom = models.FloatField(default=0.0)
    avatar = models.FileField(upload_to="personagens/", blank=True, help_text="SVG ou Lottie JSON")
    avatar_padrao = models.CharField(
        max_length=40, default="maya",
        help_text="Avatar embutido usado quando não há arquivo (maya, coruja)",
    )
    cor = models.CharField(max_length=7, default="#7C8FFF")
    estados = models.JSONField(
        default=registro.estados_padrao, blank=True,
        help_text="Estados disponíveis: neutro, falando, pensando, comemorando, alerta",
    )

    class Meta:
        unique_together = [("curso", "slug")]
        ordering = ["papel", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.curso})"

    def config_voz(self):
        return {"voz": self.voz_nome, "velocidade": self.voz_velocidade, "tom": self.voz_tom}


class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="modulos")
    titulo = models.CharField(max_length=200)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["curso", "ordem", "id"]
        verbose_name = "módulo"

    def __str__(self):
        return f"{self.ordem}. {self.titulo}"


class Aula(models.Model):
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="aulas")
    titulo = models.CharField(max_length=200)
    objetivo = models.TextField("objetivo de aprendizagem", blank=True)
    duracao_min = models.PositiveIntegerField("duração estimada (min)", default=10)
    ordem = models.PositiveIntegerField(default=0)
    xp = models.PositiveIntegerField(default=100)
    material = models.FileField("material complementar", upload_to="aulas/material/", blank=True)
    precisa_revisao = models.BooleanField(default=False)

    class Meta:
        ordering = ["modulo__ordem", "ordem", "id"]

    def __str__(self):
        return self.titulo

    @property
    def curso(self):
        return self.modulo.curso

    def problemas_estrutura(self, blocos=None):
        """Regra da seção 6: ≥ 4 blocos, ≥ 2 interativos, nunca só texto."""
        blocos = list(self.blocos.all()) if blocos is None else blocos
        return registro.problemas_da_aula([b.tipo for b in blocos])


class BlocoAula(models.Model):
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="blocos")
    ordem = models.PositiveIntegerField(default=0)
    tipo = models.CharField(max_length=30, choices=registro.CHOICES)
    titulo = models.CharField(max_length=200, blank=True)
    roteiro = models.TextField(
        "roteiro de narração", blank=True,
        help_text="Uma fala por linha: '@slug: texto'. Linhas sem @ seguem o último personagem.",
    )
    texto_tela = models.TextField("texto de tela", blank=True)
    config = models.JSONField(default=dict, blank=True)

    audio = models.FileField(upload_to="audios/", blank=True)
    duracao = models.FloatField(default=0)
    timestamps = models.JSONField(default=list, blank=True)
    hash_roteiro = models.CharField(max_length=64, blank=True)
    caracteres_tts = models.PositiveIntegerField(default=0)

    # Origem (gerador por PDF — F2.5)
    paginas_origem = models.JSONField(default=list, blank=True)
    alem_do_pdf = models.BooleanField("conteúdo além do PDF", default=False)

    class Meta:
        ordering = ["aula", "ordem", "id"]
        verbose_name = "bloco da aula"
        verbose_name_plural = "blocos da aula"

    def __str__(self):
        return f"{self.aula} · {self.ordem} · {self.get_tipo_display()}"

    @property
    def interativo(self):
        return registro.eh_interativo(self.tipo)

    def falas(self):
        return parse_roteiro(self.roteiro)

    def calcular_hash(self, personagens=None):
        """Hash do roteiro + vozes usadas: só regera áudio quando isso muda (N10)."""
        if personagens is None:
            personagens = {p.slug: p for p in self.aula.modulo.curso.personagens.all()}
        vozes = {}
        for fala in self.falas():
            p = personagens.get(fala["personagem"])
            if p:
                vozes[p.slug] = p.config_voz()
        base = json.dumps({"roteiro": self.roteiro.strip(), "vozes": vozes}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @property
    def tem_narracao(self):
        return bool(self.roteiro.strip())

    def audio_em_dia(self, personagens=None):
        if not self.tem_narracao:
            return True
        return bool(self.audio) and self.hash_roteiro == self.calcular_hash(personagens)

    def clean(self):
        erros = registro.validar_config(self.tipo, self.config)
        if erros:
            raise ValidationError({"config": erros})


class Questao(models.Model):
    class Uso(models.TextChoices):
        FIXACAO = "fixacao", "Fixação"
        PROVA = "prova", "Prova"
        AMBOS = "ambos", "Ambos"

    class Dificuldade(models.TextChoices):
        FACIL = "facil", "Fácil"
        MEDIA = "media", "Média"
        DIFICIL = "dificil", "Difícil"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="questoes")
    modulo = models.ForeignKey(Modulo, null=True, blank=True, on_delete=models.SET_NULL, related_name="questoes")
    enunciado = models.TextField()
    alternativas = models.JSONField(help_text="Lista de textos")
    correta = models.PositiveSmallIntegerField(help_text="Índice (0, 1, 2...) da alternativa correta")
    explicacao = models.TextField("explicação", blank=True)
    dificuldade = models.CharField(max_length=10, choices=Dificuldade.choices, default=Dificuldade.MEDIA)
    uso = models.CharField(max_length=10, choices=Uso.choices, default=Uso.PROVA)
    ativa = models.BooleanField(default=True)
    paginas_origem = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "questão"
        verbose_name_plural = "questões"

    def __str__(self):
        return self.enunciado[:80]

    def clean(self):
        if not isinstance(self.alternativas, list) or len(self.alternativas) < 2:
            raise ValidationError({"alternativas": "Informe pelo menos 2 alternativas."})
        if self.correta is None or self.correta >= len(self.alternativas):
            raise ValidationError({"correta": "Índice da correta fora das alternativas."})
