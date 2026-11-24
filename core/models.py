from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Organizacao(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField("CNPJ", max_length=18, blank=True)
    logo = models.ImageField(upload_to="organizacoes/logos/", blank=True)
    contato_nome = models.CharField(max_length=150, blank=True)
    contato_email = models.EmailField(blank=True)
    contato_telefone = models.CharField(max_length=30, blank=True)
    ranking_ativo = models.BooleanField(
        default=False, help_text="Se ligado, alunos desta organização aparecem no ranking (podem ficar anônimos)."
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "organização"
        verbose_name_plural = "organizações"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError("E-mail é obrigatório")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("papel", Usuario.Papel.SUPERADMIN)
        return self._criar(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Papel(models.TextChoices):
        ALUNO = "aluno", "Aluno"
        GESTOR = "gestor", "Gestor de organização"
        CRIADOR = "criador", "Criador"
        SUPERADMIN = "superadmin", "Superadmin"

    email = models.EmailField("e-mail", unique=True)
    nome = models.CharField(max_length=150)
    organizacao = models.ForeignKey(
        Organizacao, null=True, blank=True, on_delete=models.SET_NULL, related_name="usuarios"
    )
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.ALUNO)
    anonimo_no_ranking = models.BooleanField(default=False)
    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("acesso ao admin", default=False)
    date_joined = models.DateTimeField("cadastrado em", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return f"{self.nome} <{self.email}>"

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split(" ")[0] if self.nome else self.email

    @property
    def eh_criador(self):
        return self.is_superuser or self.papel in (self.Papel.CRIADOR, self.Papel.SUPERADMIN)

    @property
    def eh_gestor(self):
        return self.papel == self.Papel.GESTOR and self.organizacao_id is not None


class AuditoriaImutavel(Exception):
    pass


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditoriaImutavel("Registros de auditoria não podem ser alterados.")

    def delete(self):
        raise AuditoriaImutavel("Registros de auditoria não podem ser excluídos.")


class AuditLog(models.Model):
    objects = AuditLogQuerySet.as_manager()

    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    acao = models.CharField(max_length=80, db_index=True)
    descricao = models.TextField(blank=True)
    objeto_tipo = models.CharField(max_length=80, blank=True)
    objeto_id = models.CharField(max_length=40, blank=True)
    dados = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "registro de auditoria"
        verbose_name_plural = "auditoria"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.criado_em:%d/%m/%Y %H:%M} {self.acao}"

    # Auditoria é imutável (padrão MayaCorp): só inserção.
    def save(self, *args, **kwargs):
        if self.pk is not None and not kwargs.get("force_insert"):
            raise AuditoriaImutavel("Registros de auditoria não podem ser alterados.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditoriaImutavel("Registros de auditoria não podem ser excluídos.")

    @classmethod
    def registrar(cls, request, acao, objeto=None, descricao="", **dados):
        usuario = getattr(request, "user", None) if request else None
        return cls.objects.create(
            usuario=usuario if usuario is not None and usuario.is_authenticated else None,
            acao=acao,
            descricao=descricao,
            objeto_tipo=objeto._meta.label if objeto is not None else "",
            objeto_id=str(objeto.pk) if objeto is not None else "",
            dados=dados,
            ip=ip_do_request(request) if request else None,
        )


def ip_do_request(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
