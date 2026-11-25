import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissoes import criador_required
from cursos.models import BlocoAula

from . import pipeline
from .forms import NovaGeracaoForm
from .models import ArquivoPDF, AulaGerada, Geracao
from .paginas import PaginasInvalidas, compactar, expandir
from .tasks import gerar_aula_task, preparar_geracao_task


@criador_required
def lista(request):
    return render(request, "geracao/lista.html", {"geracoes": Geracao.objects.select_related("curso")[:50]})


@criador_required
def nova(request):
    form = NovaGeracaoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        geracao = form.save(commit=False)
        geracao.criador = request.user
        geracao.save()
        for f in form.cleaned_data["pdfs"]:
            ArquivoPDF.objects.create(geracao=geracao, arquivo=f, nome=f.name[:255])
        AuditLog.registrar(
            request, "pdf_direito_de_uso", geracao,
            "Declarou ter direito de uso do material para criar cursos",
            arquivos=[f.name for f in form.cleaned_data["pdfs"]], paginas=form.total_paginas,
        )
        preparar_geracao_task.delay(geracao.pk)
        messages.success(request, "PDF recebido. A leitura e a proposta de ementa rodam em segundo plano.")
        return redirect("geracao:detalhe", geracao.pk)
    return render(request, "geracao/nova.html", {"form": form})


def _ementa_para_tela(ementa):
    return {
        **ementa,
        "modulos": [
            {**m, "aulas": [{**a, "paginas_txt": compactar(a["paginas"])} for a in m["aulas"]]}
            for m in ementa.get("modulos") or []
        ],
    }


@criador_required
def detalhe(request, pk):
    geracao = get_object_or_404(Geracao.objects.select_related("curso"), pk=pk)
    contexto = {
        "g": geracao,
        "arquivos": geracao.arquivos.all(),
        "aulas": geracao.aulas_geradas.select_related("aula"),
        "chamadas": geracao.chamadas.all(),
        "rel": pipeline.relatorio(geracao),
    }
    if geracao.status == Geracao.Status.EMENTA:
        contexto["ementa_json"] = _ementa_para_tela(geracao.ementa)
        contexto["total_paginas"] = geracao.paginas.count()
    return render(request, "geracao/detalhe.html", contexto)


@criador_required
def situacao(request, pk):
    g = get_object_or_404(Geracao, pk=pk)
    return JsonResponse({"status": g.status, "rotulo": g.get_status_display(), "etapa": g.etapa,
                         "progresso": g.progresso, "em_andamento": g.em_andamento})


@criador_required
@require_POST
def ementa_salvar(request, pk):
    """Recebe a ementa editada (JSON montado pelo editor) e, se pedido, gera as aulas (gate N11)."""
    geracao = get_object_or_404(Geracao, pk=pk)
    if geracao.status != Geracao.Status.EMENTA:
        messages.error(request, "Esta ementa não está mais em revisão.")
        return redirect("geracao:detalhe", pk)
    total = geracao.paginas.count()
    try:
        bruto = json.loads(request.POST.get("ementa") or "{}")
        for m in bruto.get("modulos") or []:
            for a in m.get("aulas") or []:
                a["paginas"] = expandir(a.pop("paginas_txt", ""), maximo=total)
    except (json.JSONDecodeError, AttributeError, TypeError):
        messages.error(request, "Não foi possível ler a ementa enviada. Recarregue a página e tente de novo.")
        return redirect("geracao:detalhe", pk)
    except PaginasInvalidas as erro:
        messages.error(request, f"Páginas inválidas: {erro}.")
        return redirect("geracao:detalhe", pk)
    ementa = pipeline.normalizar_ementa(bruto, total)
    geracao.ementa = ementa
    geracao.save(update_fields=["ementa"])
    if request.POST.get("acao") != "gerar":
        messages.success(request, "Ementa salva.")
        return redirect("geracao:detalhe", pk)
    problemas = pipeline.problemas_ementa(ementa)
    if problemas:
        for p in problemas[:6]:
            messages.error(request, p)
        return redirect("geracao:detalhe", pk)
    curso = pipeline.criar_rascunho(geracao)
    AuditLog.registrar(request, "ementa_aprovada", geracao, "Ementa aprovada; geração das aulas iniciada",
                       curso=curso.pk, aulas=geracao.aulas_geradas.count())
    for ag in geracao.aulas_geradas.all():
        gerar_aula_task.delay(ag.pk)
    messages.success(request, f"Ementa aprovada. Gerando {geracao.aulas_geradas.count()} aula(s) do curso “{curso.titulo}” (rascunho).")
    return redirect("geracao:detalhe", pk)


@criador_required
@require_POST
def reprocessar(request, pk):
    """Preparação que parou com erro: roda de novo a extração, o mapa e a ementa."""
    geracao = get_object_or_404(Geracao, pk=pk)
    if geracao.status != Geracao.Status.ERRO or geracao.curso_id:
        messages.error(request, "Só dá para repetir a preparação de uma geração que parou com erro.")
        return redirect("geracao:detalhe", pk)
    geracao.marcar(status=Geracao.Status.NA_FILA, etapa="Na fila", progresso=0, erro="")
    preparar_geracao_task.delay(geracao.pk)
    return redirect("geracao:detalhe", pk)


@criador_required
@require_POST
def aula_de_novo(request, pk):
    """"Gerar de novo esta aula", com instrução extra opcional."""
    ag = get_object_or_404(AulaGerada.objects.select_related("geracao"), pk=pk)
    if ag.status in (AulaGerada.Status.PENDENTE, AulaGerada.Status.GERANDO):
        messages.info(request, "Esta aula já está sendo gerada.")
        return redirect("geracao:detalhe", ag.geracao_id)
    instrucao = (request.POST.get("instrucao") or "").strip()[:500]
    ag.status = AulaGerada.Status.PENDENTE
    ag.save(update_fields=["status"])
    ag.geracao.marcar(status=Geracao.Status.GERANDO, etapa=f"Gerando de novo a aula {ag.modulo_num}.{ag.aula_num}")
    AuditLog.registrar(request, "aula_gerar_de_novo", ag.aula, "Gerar de novo a aula pela IA", instrucao=instrucao)
    gerar_aula_task.delay(ag.pk, instrucao)
    messages.success(request, f"Gerando de novo: {ag.titulo}. O conteúdo atual é substituído quando terminar.")
    destino = request.POST.get("voltar")
    if destino == "aula" and ag.aula_id:
        return redirect("estudio:aula", ag.aula_id)
    return redirect("geracao:detalhe", ag.geracao_id)


@criador_required
def trecho_bloco(request, pk):
    """Botão "ver trecho do PDF" do bloco: mostra o texto das páginas de origem."""
    bloco = get_object_or_404(BlocoAula.objects.select_related("aula__modulo__curso"), pk=pk)
    geracao = bloco.aula.modulo.curso.geracoes.order_by("-criado_em").first()
    paginas = geracao.paginas.filter(numero__in=bloco.paginas_origem) if geracao else []
    return render(request, "geracao/trecho.html", {"bloco": bloco, "geracao": geracao, "paginas": paginas,
                                                    "curso": bloco.aula.modulo.curso})
