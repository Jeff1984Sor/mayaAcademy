"""Licenças e convites (N6): o convite consome vaga só no aceite; licença cheia ou vencida bloqueia."""
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from aprendizado import regras as apr
from aprendizado.models import Matricula

from .models import Convite, LicencaOrganizacao


class ConviteInvalido(Exception):
    pass


def link_convite(convite):
    return settings.SITE_URL.rstrip("/") + reverse("organizacoes:convite", args=[convite.token])


def enviar_convites(licenca, emails):
    """Cria convites para os e-mails (ignora repetidos). Retorna (criados, ignorados, erro)."""
    if licenca.vencida:
        return [], [], "A licença venceu. Peça a renovação ao responsável pela plataforma."
    if licenca.cheia:
        return [], [], f"A licença está cheia ({licenca.vagas} vagas usadas). Não é possível enviar novos convites."
    criados, ignorados = [], []
    ja_convidados = set(licenca.convites.exclude(status=Convite.Status.CANCELADO).values_list("email", flat=True))
    for email in emails:
        email = email.strip().lower()
        if not email or email in ja_convidados:
            ignorados.append(email)
            continue
        convite = Convite.objects.create(licenca=licenca, email=email)
        ja_convidados.add(email)
        criados.append(convite)
        _enviar_email(convite)
    return criados, ignorados, None


def _enviar_email(convite):
    licenca = convite.licenca
    corpo = (
        f"Olá!\n\n{licenca.organizacao.nome} convidou você para o curso \"{licenca.curso.titulo}\" na MayaAcademy.\n\n"
        f"Para aceitar, acesse: {link_convite(convite)}\n\n"
        f"O convite vale até {licenca.validade:%d/%m/%Y}.\n\nMayaAcademy · MayaCorp"
    )
    send_mail(f"Convite: {licenca.curso.titulo}", corpo, None, [convite.email], fail_silently=True)


@transaction.atomic
def aceitar(convite, usuario):
    """Aceite: confere validade e vagas (com trava), matricula e vincula à organização."""
    licenca = LicencaOrganizacao.objects.select_for_update().get(pk=convite.licenca_id)
    convite = Convite.objects.select_for_update().get(pk=convite.pk)
    if convite.status == Convite.Status.ACEITO:
        if convite.aluno_id == usuario.pk:
            return apr.matricula_de(usuario, licenca.curso)
        raise ConviteInvalido("Este convite já foi usado.")
    if convite.status == Convite.Status.CANCELADO:
        raise ConviteInvalido("Este convite foi cancelado.")
    if licenca.vencida:
        raise ConviteInvalido("Este convite expirou junto com a licença da organização.")
    if licenca.cheia:
        raise ConviteInvalido("Todas as vagas desta licença já foram usadas. Fale com o gestor da sua organização.")
    matricula, _ = apr.matricular(usuario, licenca.curso, Matricula.Origem.CONVITE_ORG, licenca.organizacao)
    convite.status = Convite.Status.ACEITO
    convite.aceito_em = timezone.now()
    convite.aluno = usuario
    convite.save(update_fields=["status", "aceito_em", "aluno"])
    if not usuario.organizacao_id:
        usuario.organizacao = licenca.organizacao
        usuario.save(update_fields=["organizacao"])
    return matricula
