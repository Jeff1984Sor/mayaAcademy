import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from aprendizado import regras as apr
from aprendizado.models import Matricula
from avaliacoes import regras as aval
from core.models import AuditLog, Organizacao
from core.permissoes import criador_required, gestor_required
from gamificacao import regras as gami

from . import regras
from .forms import ConvitesForm, GestorForm, LicencaForm, OrganizacaoForm
from .models import Convite, LicencaOrganizacao

Usuario = get_user_model()


# --- criador ----------------------------------------------------------------------

@criador_required
def lista(request):
    orgs = Organizacao.objects.prefetch_related("licencas__curso").order_by("nome")
    return render(request, "organizacoes/lista.html", {"orgs": orgs})


@criador_required
def org_form(request, pk=None):
    org = get_object_or_404(Organizacao, pk=pk) if pk else None
    form = OrganizacaoForm(request.POST or None, request.FILES or None, instance=org)
    if request.method == "POST" and form.is_valid():
        org = form.save()
        AuditLog.registrar(request, "organizacao_salva", org, f"Organização {org.nome}")
        messages.success(request, "Organização salva.")
        return redirect("organizacoes:detalhe", org.pk)
    return render(request, "organizacoes/form.html", {"form": form, "titulo": org.nome if org else "Nova organização", "org": org})


@criador_required
def detalhe(request, pk):
    org = get_object_or_404(Organizacao, pk=pk)
    return render(request, "organizacoes/detalhe.html", {
        "org": org,
        "licencas": org.licencas.select_related("curso"),
        "gestores": org.usuarios.filter(papel=Usuario.Papel.GESTOR),
        "gestor_form": GestorForm(),
    })


@criador_required
def licenca_form(request, org_pk, pk=None):
    org = get_object_or_404(Organizacao, pk=org_pk)
    licenca = get_object_or_404(LicencaOrganizacao, pk=pk, organizacao=org) if pk else None
    antes = {"vagas": licenca.vagas, "validade": str(licenca.validade)} if licenca else {}
    form = LicencaForm(request.POST or None, instance=licenca)
    if request.method == "POST" and form.is_valid():
        licenca = form.save(commit=False)
        licenca.organizacao = org
        licenca.save()
        AuditLog.registrar(request, "licenca_alterada" if antes else "licenca_criada", licenca,
                           f"Licença {licenca.curso.titulo} para {org.nome}", antes=antes,
                           depois={"vagas": licenca.vagas, "validade": str(licenca.validade)})
        messages.success(request, "Licença salva.")
        return redirect("organizacoes:detalhe", org.pk)
    return render(request, "organizacoes/form.html", {"form": form, "titulo": "Licença de curso", "org": org})


@criador_required
@require_POST
def tornar_gestor(request, pk):
    org = get_object_or_404(Organizacao, pk=pk)
    form = GestorForm(request.POST)
    if form.is_valid():
        usuario = Usuario.objects.filter(email__iexact=form.cleaned_data["email"]).first()
        if not usuario:
            messages.error(request, "Não há conta com esse e-mail. Peça para a pessoa se cadastrar primeiro.")
        elif usuario.eh_criador:
            messages.error(request, "Esse usuário é criador; o papel dele não foi alterado.")
        else:
            usuario.papel = Usuario.Papel.GESTOR
            usuario.organizacao = org
            usuario.save(update_fields=["papel", "organizacao"])
            AuditLog.registrar(request, "gestor_definido", usuario, f"Gestor de {org.nome}")
            messages.success(request, f"{usuario.nome or usuario.email} agora é gestor(a) de {org.nome}.")
    return redirect("organizacoes:detalhe", pk)


# --- gestor -------------------------------------------------------------------------

def _org_do_gestor(request):
    if request.user.eh_criador:
        pk = request.GET.get("org") or request.POST.get("org")
        if pk:
            return get_object_or_404(Organizacao, pk=pk)
        if request.user.organizacao_id:
            return request.user.organizacao
        raise PermissionDenied
    if not request.user.eh_gestor:
        raise PermissionDenied
    return request.user.organizacao


def _linhas_alunos(org, curso_id=None, situacao=None):
    matriculas = Matricula.objects.filter(organizacao=org).select_related("aluno", "curso").order_by("curso__titulo", "aluno__nome")
    if curso_id:
        matriculas = matriculas.filter(curso_id=curso_id)
    linhas = []
    for m in matriculas:
        aprovada = aval.aprovada(m)
        ultima = aval.finalizadas(m).order_by("-numero").first()
        cert = getattr(m, "certificado", None)
        linha = {
            "m": m, "aluno": m.aluno, "curso": m.curso, "percentual": apr.percentual(m),
            "nota": (aprovada or ultima).nota if (aprovada or ultima) else None,
            "situacao": "aprovado" if aprovada else ("concluiu aulas" if apr.todas_concluidas(m) else "em andamento"),
            "certificado": cert,
        }
        if situacao and linha["situacao"] != situacao:
            continue
        linhas.append(linha)
    return linhas


@gestor_required
def painel(request):
    org = _org_do_gestor(request)
    curso_id = request.GET.get("curso") or None
    situacao = request.GET.get("situacao") or None
    linhas = _linhas_alunos(org, curso_id, situacao)
    if request.GET.get("formato") == "csv":
        resposta = HttpResponse(content_type="text/csv; charset=utf-8")
        resposta["Content-Disposition"] = f'attachment; filename="alunos-{timezone.localdate():%Y%m%d}.csv"'
        resposta.write("﻿")
        w = csv.writer(resposta, delimiter=";")
        w.writerow(["Aluno", "E-mail", "Curso", "Progresso (%)", "Situação", "Nota", "Certificado", "Matrícula"])
        for linha in linhas:
            w.writerow([
                linha["aluno"].nome, linha["aluno"].email, linha["curso"].titulo, linha["percentual"], linha["situacao"],
                str(linha["nota"]).replace(".", ",") if linha["nota"] is not None else "",
                linha["certificado"].codigo if linha["certificado"] else "", f"{linha['m'].criada_em:%d/%m/%Y}",
            ])
        return resposta
    licencas = org.licencas.select_related("curso")
    form = ConvitesForm(organizacao=org)
    convites = list(Convite.objects.filter(licenca__organizacao=org).select_related("licenca__curso", "aluno")[:100])
    for c in convites:
        c.link = regras.link_convite(c)
    return render(request, "organizacoes/painel.html", {
        "org": org, "licencas": licencas, "linhas": linhas, "form": form, "convites": convites,
        "cursos": sorted({lic.curso for lic in licencas}, key=lambda c: c.titulo),
        "filtro_curso": curso_id, "filtro_situacao": situacao,
        "ranking": gami.ranking(Usuario.objects.filter(organizacao=org)) if org.ranking_ativo else [],
        "consulta_org": f"?org={org.pk}" if request.user.eh_criador else "",
    })


@gestor_required
@require_POST
def convidar(request):
    org = _org_do_gestor(request)
    form = ConvitesForm(request.POST, organizacao=org)
    if form.is_valid():
        criados, ignorados, erro = regras.enviar_convites(form.cleaned_data["licenca"], form.cleaned_data["emails"])
        if erro:
            messages.error(request, erro)
        else:
            AuditLog.registrar(request, "convites_enviados", form.cleaned_data["licenca"], f"{len(criados)} convite(s)",
                               emails=[c.email for c in criados])
            messages.success(request, f"{len(criados)} convite(s) enviado(s)." + (f" {len(ignorados)} já convidado(s)." if ignorados else ""))
    else:
        for erros in form.errors.values():
            for e in erros:
                messages.error(request, e)
    destino = reverse("organizacoes:painel")
    return redirect(destino + (f"?org={org.pk}" if request.user.eh_criador else ""))


@gestor_required
@require_POST
def cancelar_convite(request, pk):
    org = _org_do_gestor(request)
    convite = get_object_or_404(Convite, pk=pk, licenca__organizacao=org, status=Convite.Status.PENDENTE)
    convite.status = Convite.Status.CANCELADO
    convite.save(update_fields=["status"])
    messages.success(request, f"Convite para {convite.email} cancelado.")
    return redirect(reverse("organizacoes:painel") + (f"?org={org.pk}" if request.user.eh_criador else ""))


@gestor_required
@require_POST
def ranking(request):
    org = _org_do_gestor(request)
    org.ranking_ativo = request.POST.get("ativo") == "1"
    org.save(update_fields=["ranking_ativo"])
    AuditLog.registrar(request, "ranking_organizacao", org, "Ranking " + ("ligado" if org.ranking_ativo else "desligado"))
    return redirect(reverse("organizacoes:painel") + (f"?org={org.pk}" if request.user.eh_criador else ""))


# --- aceite do convite (aluno) ---------------------------------------------------------

def convite(request, token):
    c = get_object_or_404(Convite.objects.select_related("licenca__curso", "licenca__organizacao"), token=token)
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('core:login')}?next={request.path}")
        try:
            regras.aceitar(c, request.user)
        except regras.ConviteInvalido as erro:
            messages.error(request, str(erro))
            return redirect("organizacoes:convite", token)
        AuditLog.registrar(request, "convite_aceito", c, f"Convite aceito: {c.licenca.curso.titulo}")
        messages.success(request, "Convite aceito! Você já pode começar o curso.")
        return redirect("aprendizado:curso", c.licenca.curso.slug)
    return render(request, "organizacoes/convite.html", {"c": c})


@login_required
def minha_organizacao(request):
    if request.user.eh_gestor:
        return redirect("organizacoes:painel")
    if request.user.eh_criador:
        return redirect("organizacoes:lista")
    raise PermissionDenied
