import json
import uuid

from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissoes import criador_required
from cursos import blocos as registro
from cursos import pacote, publicacao
from cursos.audio import estimativa
from cursos.exemplos import EXEMPLOS
from cursos.models import Aula, BlocoAula, Curso, Modulo, Personagem, Questao
from cursos.player import dados_aula, dados_bloco
from cursos.roteiro_io import ErroLeitura, exportar, importar, ler, resumo, validar
from cursos.tasks import gerar_audio_bloco_task, gerar_audios_aula_task, gerar_audios_curso_task

from .forms import AulaForm, BlocoForm, CursoForm, ImportarForm, ModuloForm, PersonagemForm, QuestaoForm


def _curso_completo(pk):
    return get_object_or_404(
        Curso.objects.prefetch_related(
            "personagens",
            Prefetch("modulos", queryset=Modulo.objects.order_by("ordem").prefetch_related(
                Prefetch("aulas", queryset=Aula.objects.order_by("ordem").prefetch_related("blocos"))
            )),
        ),
        pk=pk,
    )


# ---------------------------------------------------------------- painel / curso

@criador_required
def painel(request):
    cursos = Curso.objects.annotate(
        n_modulos=Count("modulos", distinct=True),
        n_aulas=Count("modulos__aulas", distinct=True),
        n_questoes=Count("questoes", filter=Q(questoes__ativa=True), distinct=True),
    ).order_by("status", "titulo")
    return render(request, "estudio/painel.html", {"cursos": cursos})


@criador_required
def curso_novo(request):
    form = CursoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        curso = form.save(commit=False)
        curso.slug = form.cleaned_data.get("slug") or slugify(curso.titulo)
        curso.save()
        Personagem.objects.create(curso=curso, slug="narrador", nome="Narrador", papel="narrador", voz_nome="pt-BR-Neural2-B", avatar_padrao="coruja", cor="#1A8F5E")
        Personagem.objects.create(curso=curso, slug="maya", nome="Maya", papel="mascote", voz_nome="pt-BR-Neural2-C", cor="#7C8FFF")
        messages.success(request, "Curso criado como rascunho.")
        return redirect("estudio:curso", curso.pk)
    return render(request, "estudio/curso_form.html", {"form": form})


@criador_required
def curso(request, pk):
    c = _curso_completo(pk)
    personagens = {p.slug: p for p in c.personagens.all()}
    blocos = [b for m in c.modulos.all() for a in m.aulas.all() for b in a.blocos.all()]
    return render(request, "estudio/curso.html", {
        "curso": c,
        "checklist": publicacao.checklist(c),
        "estimativa": estimativa(blocos, personagens),
        "pode_publicar": publicacao.pode_publicar(c),
        "n_questoes": c.questoes.filter(ativa=True).count(),
    })


@criador_required
def curso_editar(request, pk):
    c = get_object_or_404(Curso, pk=pk)
    form = CursoForm(request.POST or None, request.FILES or None, instance=c)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Curso atualizado.")
        return redirect("estudio:curso", c.pk)
    return render(request, "estudio/curso_form.html", {"form": form, "curso": c})


@criador_required
@require_POST
def curso_publicar(request, pk):
    c = get_object_or_404(Curso, pk=pk)
    if publicacao.publicar(c):
        AuditLog.registrar(request, "publicar_curso", c, f"Publicado na versão {c.versao}", versao=c.versao)
        messages.success(request, f"Curso publicado (versão {c.versao}).")
    else:
        messages.error(request, "O curso ainda não cumpre o checklist de publicação.")
    return redirect("estudio:curso", c.pk)


@criador_required
@require_POST
def curso_arquivar(request, pk):
    c = get_object_or_404(Curso, pk=pk)
    c.status = Curso.Status.ARQUIVADO if c.status != Curso.Status.ARQUIVADO else Curso.Status.RASCUNHO
    c.save(update_fields=["status", "atualizado_em"])
    AuditLog.registrar(request, "arquivar_curso" if c.status == Curso.Status.ARQUIVADO else "desarquivar_curso", c)
    messages.success(request, "Curso arquivado." if c.status == Curso.Status.ARQUIVADO else "Curso voltou para rascunho.")
    return redirect("estudio:curso", c.pk)


@criador_required
def curso_exportar(request, pk):
    c = get_object_or_404(Curso, pk=pk)
    resp = HttpResponse(exportar(c), content_type="application/x-yaml; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{c.slug}.yaml"'
    return resp


@criador_required
def curso_pacote(request, pk):
    c = get_object_or_404(Curso, pk=pk)
    conteudo = pacote.gerar_zip(c)
    AuditLog.registrar(request, "baixar_pacote_curso", c, versao=c.versao)
    resp = HttpResponse(conteudo, content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{c.slug}-v{c.versao}-scorm.zip"'
    return resp


@criador_required
def busca(request):
    """Busca da paleta de comandos (Ctrl+K): cursos e aulas."""
    q = (request.GET.get("q") or "").strip()
    itens = []
    if len(q) >= 2:
        for c in Curso.objects.filter(titulo__icontains=q).order_by("titulo")[:6]:
            itens.append({"tipo": "Curso", "rotulo": c.titulo, "detalhe": c.get_status_display(),
                          "url": reverse("estudio:curso", args=[c.pk])})
        for a in Aula.objects.filter(titulo__icontains=q).select_related("modulo__curso").order_by("titulo")[:8]:
            itens.append({"tipo": "Aula", "rotulo": a.titulo, "detalhe": a.modulo.curso.titulo,
                          "url": reverse("estudio:aula", args=[a.pk])})
    return JsonResponse({"itens": itens})


# ---------------------------------------------------------------- personagens

@criador_required
def personagem_form(request, curso_pk, pk=None):
    c = get_object_or_404(Curso, pk=curso_pk)
    p = get_object_or_404(Personagem, pk=pk, curso=c) if pk else Personagem(curso=c)
    form = PersonagemForm(request.POST or None, request.FILES or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Personagem salvo. Áudios com a voz antiga aparecem como desatualizados.")
        return redirect("estudio:curso", c.pk)
    return render(request, "estudio/form_simples.html", {"form": form, "curso": c, "titulo": "Personagem"})


@criador_required
@require_POST
def personagem_excluir(request, curso_pk, pk):
    p = get_object_or_404(Personagem, pk=pk, curso_id=curso_pk)
    p.delete()
    messages.success(request, "Personagem removido.")
    return redirect("estudio:curso", curso_pk)


# ---------------------------------------------------------------- módulos e aulas

@criador_required
def modulo_form(request, curso_pk, pk=None):
    c = get_object_or_404(Curso, pk=curso_pk)
    m = get_object_or_404(Modulo, pk=pk, curso=c) if pk else Modulo(curso=c, ordem=c.modulos.count() + 1)
    form = ModuloForm(request.POST or None, instance=m)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("estudio:curso", c.pk)
    return render(request, "estudio/form_simples.html", {"form": form, "curso": c, "titulo": "Módulo"})


@criador_required
@require_POST
def modulo_excluir(request, curso_pk, pk):
    m = get_object_or_404(Modulo, pk=pk, curso_id=curso_pk)
    if m.aulas.exists():
        messages.error(request, "Exclua ou mova as aulas antes de excluir o módulo.")
    else:
        m.delete()
    return redirect("estudio:curso", curso_pk)


@criador_required
def aula_nova(request, modulo_pk):
    m = get_object_or_404(Modulo.objects.select_related("curso"), pk=modulo_pk)
    form = AulaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        aula = form.save(commit=False)
        aula.modulo = m
        aula.ordem = m.aulas.count() + 1
        aula.save()
        return redirect("estudio:aula", aula.pk)
    return render(request, "estudio/form_simples.html", {"form": form, "curso": m.curso, "titulo": f"Nova aula em “{m.titulo}”"})


@criador_required
def aula(request, pk):
    a = get_object_or_404(Aula.objects.select_related("modulo__curso"), pk=pk)
    curso = a.modulo.curso
    personagens = {p.slug: p for p in curso.personagens.all()}
    blocos = list(a.blocos.all())
    for b in blocos:
        b.aula = a
        b.erros = registro.validar_bloco(b.tipo, b.config, b.roteiro)
        b.audio_ok = b.audio_em_dia(personagens)
    form = AulaForm(request.POST or None, request.FILES or None, instance=a)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Aula atualizada.")
        return redirect("estudio:aula", a.pk)
    return render(request, "estudio/aula.html", {
        "aula": a, "curso": curso, "blocos": blocos, "form": form,
        "problemas": a.problemas_estrutura(blocos),
        "tipos": registro.TIPOS,
        "estimativa": estimativa(blocos, personagens),
    })


@criador_required
@require_POST
def aula_excluir(request, pk):
    a = get_object_or_404(Aula.objects.select_related("modulo"), pk=pk)
    curso_pk = a.modulo.curso_id
    a.delete()
    messages.success(request, "Aula excluída.")
    return redirect("estudio:curso", curso_pk)


@criador_required
@require_POST
def reordenar(request, tipo):
    """Recebe {"ids": [...], "pai": id} e grava a nova ordem (arrastar e soltar)."""
    try:
        corpo = json.loads(request.body)
        ids = [int(i) for i in corpo["ids"]]
        pai = int(corpo["pai"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "erro": "dados inválidos"}, status=400)
    modelos = {
        "modulos": (Modulo, "curso_id"),
        "aulas": (Aula, "modulo_id"),
        "blocos": (BlocoAula, "aula_id"),
    }
    if tipo not in modelos:
        return JsonResponse({"ok": False}, status=404)
    modelo, campo_pai = modelos[tipo]
    with transaction.atomic():
        objetos = {o.pk: o for o in modelo.objects.filter(pk__in=ids)}
        if len(objetos) != len(ids):
            return JsonResponse({"ok": False, "erro": "itens não encontrados"}, status=400)
        for ordem, pk in enumerate(ids, 1):
            o = objetos[pk]
            o.ordem = ordem
            setattr(o, campo_pai, pai)  # permite mover aula entre módulos
        modelo.objects.bulk_update(objetos.values(), ["ordem", campo_pai])
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------- blocos

@criador_required
@require_POST
def bloco_novo(request, aula_pk):
    a = get_object_or_404(Aula, pk=aula_pk)
    tipo = request.POST.get("tipo")
    if tipo not in registro.TIPOS:
        messages.error(request, "Tipo de bloco inválido.")
        return redirect("estudio:aula", a.pk)
    ex = EXEMPLOS.get(tipo, {})
    b = BlocoAula.objects.create(
        aula=a, tipo=tipo, ordem=a.blocos.count() + 1, titulo=registro.TIPOS[tipo]["rotulo"],
        roteiro=ex.get("roteiro", ""), texto_tela=ex.get("texto_tela", ""), config=ex.get("config", {}),
    )
    return redirect("estudio:bloco", b.pk)


@criador_required
def bloco(request, pk):
    b = get_object_or_404(BlocoAula.objects.select_related("aula__modulo__curso"), pk=pk)
    curso = b.aula.modulo.curso
    form = BlocoForm(request.POST or None, instance=b)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Bloco salvo.")
        if "salvar_voltar" in request.POST:
            return redirect("estudio:aula", b.aula_id)
        return redirect("estudio:bloco", b.pk)
    personagens = {p.slug: p for p in curso.personagens.all()}
    return render(request, "estudio/bloco.html", {
        "bloco": b, "aula": b.aula, "curso": curso, "form": form,
        "schemas": {k: t["schema"] for k, t in registro.TIPOS.items()},
        "personagens": list(personagens.values()),
        "audio_ok": b.audio_em_dia(personagens),
    })


@criador_required
@require_POST
def bloco_excluir(request, pk):
    b = get_object_or_404(BlocoAula, pk=pk)
    aula_pk = b.aula_id
    b.delete()
    messages.success(request, "Bloco excluído.")
    return redirect("estudio:aula", aula_pk)


@criador_required
@require_POST
def bloco_duplicar(request, pk):
    b = get_object_or_404(BlocoAula, pk=pk)
    BlocoAula.objects.filter(aula=b.aula, ordem__gt=b.ordem).update(ordem=F("ordem") + 1)
    b.pk = None
    b.ordem += 1
    b.audio = ""
    b.hash_roteiro = ""
    b.save()
    return redirect("estudio:aula", b.aula_id)


@criador_required
@require_POST
def bloco_previa(request, pk):
    """Pré-visualização ao vivo: renderiza o player com os dados ainda não salvos."""
    original = get_object_or_404(BlocoAula.objects.select_related("aula__modulo__curso"), pk=pk)
    curso = original.aula.modulo.curso
    personagens = {p.slug: p for p in curso.personagens.all()}
    temp = BlocoAula(
        pk=original.pk, aula=original.aula, ordem=1, tipo=request.POST.get("tipo", original.tipo),
        titulo=request.POST.get("titulo", ""), roteiro=request.POST.get("roteiro", ""),
        texto_tela=request.POST.get("texto_tela", ""), audio=original.audio, hash_roteiro=original.hash_roteiro,
        timestamps=original.timestamps, duracao=original.duracao, alem_do_pdf=bool(request.POST.get("alem_do_pdf")),
    )
    erros = []
    try:
        temp.config = json.loads(request.POST.get("config") or "{}")
        erros = registro.validar_bloco(temp.tipo, temp.config, temp.roteiro)
    except json.JSONDecodeError as erro:
        temp.config = {}
        erros = [f"JSON inválido: {erro.msg} (linha {erro.lineno})"]
    dados = dados_aula(original.aula, [], personagens)
    dados["blocos"] = [] if erros else [dados_bloco(temp, personagens)]
    return render(request, "estudio/previa.html", {"dados": dados, "erros": erros})


# ---------------------------------------------------------------- áudio

@criador_required
@require_POST
def gerar_audio(request, escopo, pk):
    forcar = bool(request.POST.get("forcar"))
    tarefas = {
        "bloco": (gerar_audio_bloco_task, BlocoAula, lambda o: reverse("estudio:bloco", args=[o.pk])),
        "aula": (gerar_audios_aula_task, Aula, lambda o: reverse("estudio:aula", args=[o.pk])),
        "curso": (gerar_audios_curso_task, Curso, lambda o: reverse("estudio:curso", args=[o.pk])),
    }
    if escopo not in tarefas:
        return HttpResponse(status=404)
    tarefa, modelo, destino = tarefas[escopo]
    obj = get_object_or_404(modelo, pk=pk)
    try:
        tarefa.delay(obj.pk, forcar)
        messages.success(request, "Geração de áudio enviada para a fila. Atualize a página em instantes.")
    except Exception:  # noqa: BLE001 — fila fora do ar não pode derrubar a página
        messages.error(request, "Não foi possível falar com a fila (Celery/Redis). Verifique o serviço mayaacademy-celery.")
    return redirect(destino(obj))


# ---------------------------------------------------------------- questões

@criador_required
def questoes(request, curso_pk):
    c = get_object_or_404(Curso, pk=curso_pk)
    lista = c.questoes.select_related("modulo").order_by("modulo__ordem", "id")
    return render(request, "estudio/questoes.html", {"curso": c, "questoes": lista})


@criador_required
def questao_form(request, curso_pk, pk=None):
    c = get_object_or_404(Curso, pk=curso_pk)
    q = get_object_or_404(Questao, pk=pk, curso=c) if pk else Questao(curso=c)
    form = QuestaoForm(request.POST or None, instance=q, curso=c)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if obj.correta >= len(obj.alternativas):
            form.add_error("correta", "Índice fora das alternativas.")
        else:
            obj.save()
            messages.success(request, "Questão salva.")
            return redirect("estudio:questoes", c.pk)
    return render(request, "estudio/form_simples.html", {"form": form, "curso": c, "titulo": "Questão"})


# ---------------------------------------------------------------- importador

_CHAVE_IMPORT = "estudio_importacao"


@criador_required
def importar_roteiro(request):
    form = ImportarForm(request.POST or None, request.FILES or None)
    contexto = {"form": form}
    if request.method == "POST" and form.is_valid():
        conteudo = form.cleaned_data["arquivo"].read().decode("utf-8", errors="replace")
        destino = form.cleaned_data.get("curso_destino")
        contexto["nome_arquivo"] = form.cleaned_data["arquivo"].name
        try:
            dados = ler(conteudo)
        except ErroLeitura as erro:
            contexto["erro_leitura"] = str(erro)
            return render(request, "estudio/importar.html", contexto)
        rel = validar(dados, destino)
        contexto.update({"relatorio": rel, "resumo": resumo(dados), "destino": destino})
        if rel.ok:
            caminho = default_storage.save(f"importacoes/{uuid.uuid4().hex}.yaml", ContentFile(conteudo.encode("utf-8")))
            request.session[_CHAVE_IMPORT] = {"arquivo": caminho, "destino": destino.pk if destino else None}
    return render(request, "estudio/importar.html", contexto)


@criador_required
@require_POST
def importar_confirmar(request):
    info = request.session.pop(_CHAVE_IMPORT, None)
    if not info or not default_storage.exists(info["arquivo"]):
        messages.error(request, "Importação expirada. Envie o arquivo de novo.")
        return redirect("estudio:importar")
    with default_storage.open(info["arquivo"], "rb") as f:
        conteudo = f.read().decode("utf-8")
    default_storage.delete(info["arquivo"])
    destino = Curso.objects.filter(pk=info["destino"]).first() if info["destino"] else None
    dados = ler(conteudo)
    rel = validar(dados, destino)  # revalida: o banco pode ter mudado
    if not rel.ok:
        messages.error(request, "O arquivo deixou de ser válido (ex.: slug já usado). Envie de novo.")
        return redirect("estudio:importar")
    curso = importar(dados, destino)
    AuditLog.registrar(request, "importar_roteiro", curso, "Importação de roteiro", parcial=bool(destino))
    messages.success(request, f"Importado como rascunho: {curso.titulo}.")
    return redirect("estudio:curso", curso.pk)
