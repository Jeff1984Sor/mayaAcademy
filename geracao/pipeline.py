"""Pipeline do gerador de curso por PDF (seção 8.4).

1. extrair  — texto por página (OCR nas páginas sem texto, se o Tesseract estiver instalado)
2. mapear   — IA mapeia temas, conceitos, glossário e exemplos (por trechos)
3. ementa   — IA propõe módulos e aulas  → GATE do criador (N11: nada de aula antes da aprovação)
4. aulas    — uma chamada por aula, só com o trecho de origem; validação + até 2 correções;
              se ainda falhar, a aula fica "precisa de revisão" sem travar as outras (N13)
5. questões — junto com cada aula (fixação + prova), sempre com página de origem (N12)
6. relatório — aulas, problemas, páginas não aproveitadas, custo de IA e de TTS
"""
import json
import logging
import math

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from cursos import blocos as registro
from cursos.audio import estimativa, personagens_do_curso
from cursos.models import Aula, BlocoAula, Curso, Modulo, Personagem, Questao
from cursos.roteiro import personagens_usados
from services.llm import ErroLLM, ErroLLMComUso, custo_usd, provedor

from . import ia
from .models import AulaGerada, ChamadaLLM, Geracao, PaginaPDF
from .paginas import compactar

log = logging.getLogger(__name__)

LIMITE_TRECHO_MAPA = 60_000      # caracteres por chamada do mapa
LIMITE_TEXTO_AULA = 120_000      # caracteres de material por aula
MIN_TEXTO_PAGINA = 30            # abaixo disso a página é tratada como "sem texto" (tenta OCR)
TENTATIVAS_CORRECAO = 2          # reenvios à IA com os erros de validação


# --- 1. extração -------------------------------------------------------------------

def _ocr(pagina):
    try:
        tp = pagina.get_textpage_ocr(language="por", dpi=200, full=True)
        return pagina.get_text("text", textpage=tp).strip()
    except Exception:  # noqa: BLE001 — Tesseract ausente ou falha: a página fica "sem texto"
        return ""


def _limpar(texto):
    linhas = [" ".join(linha.split()) for linha in texto.splitlines()]
    saida, vazias = [], 0
    for linha in linhas:
        vazias = vazias + 1 if not linha else 0
        if vazias <= 1:
            saida.append(linha)
    return "\n".join(saida).strip()


def extrair(geracao):
    import pymupdf as fitz

    geracao.paginas.all().delete()
    numero = 1
    for arq in geracao.arquivos.all():
        with arq.arquivo.open("rb") as f:
            doc = fitz.open(stream=f.read(), filetype="pdf")
        arq.primeira_pagina = numero
        arq.paginas = len(doc)
        arq.save(update_fields=["primeira_pagina", "paginas"])
        novas = []
        for pagina in doc:
            texto = _limpar(pagina.get_text("text"))
            ocr = False
            if len(texto) < MIN_TEXTO_PAGINA:
                lido = _limpar(_ocr(pagina))
                if len(lido) >= MIN_TEXTO_PAGINA:
                    texto, ocr = lido, True
            novas.append(PaginaPDF(
                geracao=geracao, arquivo=arq, numero=numero, texto=texto, ocr=ocr,
                sem_texto=len(texto) < MIN_TEXTO_PAGINA,
            ))
            numero += 1
        PaginaPDF.objects.bulk_create(novas)
        doc.close()
    return numero - 1


def _texto_paginas(paginas):
    return "\n\n".join(f"[página {p.numero}]\n{p.texto}" for p in paginas if not p.sem_texto)


# --- chamada à IA com log de custo ----------------------------------------------------

def _chamar(geracao, llm, etapa, referencia, mensagens, schema, nome, contexto=None):
    try:
        r = llm.gerar_json(mensagens, schema, nome, contexto=contexto)
    except ErroLLMComUso as erro:
        ChamadaLLM.objects.create(
            geracao=geracao, etapa=etapa, referencia=referencia, modelo=erro.modelo,
            tokens_entrada=erro.tokens_entrada, tokens_saida=erro.tokens_saida,
            custo_usd=custo_usd(erro.tokens_entrada, erro.tokens_saida), sucesso=False, erro=str(erro),
        )
        raise
    except ErroLLM as erro:
        ChamadaLLM.objects.create(geracao=geracao, etapa=etapa, referencia=referencia, sucesso=False, erro=str(erro))
        raise
    ChamadaLLM.objects.create(
        geracao=geracao, etapa=etapa, referencia=referencia, modelo=r.modelo,
        tokens_entrada=r.tokens_entrada, tokens_saida=r.tokens_saida, custo_usd=r.custo_usd, duracao_s=r.duracao_s,
    )
    return r


# --- 2. mapa do conteúdo ------------------------------------------------------------

def _trechos(paginas):
    atual, tamanho = [], 0
    for p in paginas:
        if p.sem_texto:
            continue
        if atual and tamanho + len(p.texto) > LIMITE_TRECHO_MAPA:
            yield atual
            atual, tamanho = [], 0
        atual.append(p)
        tamanho += len(p.texto)
    if atual:
        yield atual


def mapear(geracao, llm):
    paginas = list(geracao.paginas.all())
    trechos = list(_trechos(paginas))
    if not trechos:
        raise ErroLLM("Nenhuma página com texto legível (se o PDF é escaneado, instale o OCR no servidor).")
    mapa = {"temas": [], "conceitos": [], "glossario": [], "exemplos": [], "paginas_sem_conteudo": []}
    validas = {p.numero for p in paginas}
    for i, trecho in enumerate(trechos, 1):
        geracao.marcar(etapa=f"Mapeando o conteúdo (trecho {i} de {len(trechos)})", progresso=10 + int(50 * (i - 1) / len(trechos)))
        intervalo = f"{trecho[0].numero} a {trecho[-1].numero}"
        msgs = ia.mensagens("mapa", titulo=geracao.titulo, parte=i, partes=len(trechos), intervalo=intervalo,
                            texto=_texto_paginas(trecho))
        r = _chamar(geracao, llm, ChamadaLLM.Etapa.MAPA, f"trecho {i} (p. {intervalo})", msgs, ia.SCHEMA_MAPA, "mapa",
                    contexto={"paginas": [p.numero for p in trecho]})
        for chave in ("temas", "conceitos", "glossario", "exemplos"):
            for item in r.dados.get(chave) or []:
                item["paginas"] = sorted({p for p in item.get("paginas") or [] if p in validas})
                mapa[chave].append(item)
        mapa["paginas_sem_conteudo"] += [p for p in r.dados.get("paginas_sem_conteudo") or [] if p in validas]
    mapa["paginas_sem_conteudo"] = sorted(set(mapa["paginas_sem_conteudo"]) | {p.numero for p in paginas if p.sem_texto})
    geracao.mapa = mapa
    geracao.save(update_fields=["mapa"])
    return mapa


# --- 3. ementa -------------------------------------------------------------------------

def normalizar_ementa(dados, total_paginas):
    """Garante a estrutura e só páginas existentes."""
    modulos = []
    for m in dados.get("modulos") or []:
        aulas = []
        for a in m.get("aulas") or []:
            paginas = sorted({int(p) for p in a.get("paginas") or [] if 1 <= int(p) <= total_paginas})
            aulas.append({
                "titulo": (a.get("titulo") or "").strip()[:200],
                "objetivo": (a.get("objetivo") or "").strip(),
                "paginas": paginas,
                "duracao_min": max(3, min(int(a.get("duracao_min") or 10), 60)),
            })
        if aulas:
            modulos.append({"titulo": (m.get("titulo") or "").strip()[:200], "aulas": aulas})
    return {
        "titulo": (dados.get("titulo") or "").strip()[:200],
        "subtitulo": (dados.get("subtitulo") or "").strip()[:300],
        "descricao": (dados.get("descricao") or "").strip(),
        "categoria": (dados.get("categoria") or "").strip()[:80],
        "modulos": modulos,
    }


def problemas_ementa(ementa):
    erros = []
    if not ementa.get("titulo"):
        erros.append("O curso precisa de um título.")
    if not ementa.get("modulos"):
        erros.append("A ementa precisa de pelo menos um módulo com uma aula.")
    for mi, m in enumerate(ementa.get("modulos") or [], 1):
        if not m.get("titulo"):
            erros.append(f"Módulo {mi}: falta o título.")
        if not m.get("aulas"):
            erros.append(f"Módulo {mi}: não tem aulas.")
        for ai, a in enumerate(m.get("aulas") or [], 1):
            if not a.get("titulo"):
                erros.append(f"Aula {mi}.{ai}: falta o título.")
            if not a.get("paginas"):
                erros.append(f"Aula {mi}.{ai} \"{a.get('titulo', '')}\": informe as páginas de origem.")
    return erros


def propor_ementa(geracao, llm):
    geracao.marcar(etapa="Propondo a ementa", progresso=70)
    total = geracao.paginas.count()
    msgs = ia.mensagens(
        "ementa", titulo=geracao.titulo, total_paginas=total, n_modulos=geracao.n_modulos,
        duracao_horas=geracao.duracao_horas, publico=geracao.publico, nivel=geracao.get_nivel_display(),
        tom=geracao.get_tom_display(), idioma=geracao.idioma, mapa=json.dumps(geracao.mapa, ensure_ascii=False),
    )
    r = _chamar(geracao, llm, ChamadaLLM.Etapa.EMENTA, "ementa", msgs, ia.SCHEMA_EMENTA, "ementa",
                contexto={"paginas": list(geracao.paginas.filter(sem_texto=False).values_list("numero", flat=True)),
                          "n_modulos": geracao.n_modulos})
    geracao.ementa = normalizar_ementa(r.dados, total)
    geracao.save(update_fields=["ementa"])
    return geracao.ementa


def preparar(geracao_id):
    """Etapas 1 a 3. Termina na ementa, aguardando o criador."""
    geracao = Geracao.objects.get(pk=geracao_id)
    try:
        geracao.marcar(status=Geracao.Status.EXTRAINDO, etapa="Extraindo o texto do PDF", progresso=2, erro="")
        total = extrair(geracao)
        ocr = geracao.paginas.filter(ocr=True).count()
        geracao.marcar(status=Geracao.Status.MAPEANDO, etapa=f"{total} páginas lidas ({ocr} por OCR)", progresso=10)
        llm = provedor()
        mapear(geracao, llm)
        geracao.marcar(status=Geracao.Status.PROPONDO)
        propor_ementa(geracao, llm)
        geracao.marcar(status=Geracao.Status.EMENTA, etapa="Ementa pronta para sua revisão", progresso=100)
    except ErroLLM as erro:
        geracao.marcar(status=Geracao.Status.ERRO, etapa="Parou com erro", erro=str(erro))
    except Exception as erro:  # noqa: BLE001
        log.exception("Falha na geração %s", geracao_id)
        geracao.marcar(status=Geracao.Status.ERRO, etapa="Parou com erro", erro=f"Erro inesperado: {erro}")


# --- 4. aulas ------------------------------------------------------------------------

def _slug_unico(titulo):
    base = slugify(titulo)[:180] or "curso"
    slug, n = base, 2
    while Curso.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def questoes_prova_por_aula(curso, n_aulas):
    necessarias = math.ceil(curso.questoes_sorteadas * 1.5)
    return max(2, min(4, math.ceil(necessarias / max(n_aulas, 1)) + 1))


@transaction.atomic
def criar_rascunho(geracao):
    """Depois da aprovação da ementa: cria o curso (rascunho), personagens, módulos e aulas vazias."""
    e = geracao.ementa
    total_min = sum(a["duracao_min"] for m in e["modulos"] for a in m["aulas"])
    curso = Curso.objects.create(
        titulo=e["titulo"], slug=_slug_unico(e["titulo"]), subtitulo=e.get("subtitulo", ""),
        descricao=e.get("descricao", ""), categoria=e.get("categoria", ""), nivel=geracao.nivel,
        carga_horaria=max(1, round(total_min / 60)), status=Curso.Status.RASCUNHO,
    )
    slug_mascote = slugify(geracao.mascote_nome)[:40] or "maya"
    if slug_mascote == "narrador":
        slug_mascote = "mascote"
    Personagem.objects.create(curso=curso, slug="narrador", nome=geracao.narrador_nome or "Narrador",
                              papel="narrador", voz_nome="pt-BR-Neural2-B", avatar_padrao="coruja", cor="#1A8F5E")
    Personagem.objects.create(curso=curso, slug=slug_mascote, nome=geracao.mascote_nome or "Maya",
                              papel="mascote", voz_nome="pt-BR-Neural2-C", avatar_padrao="maya", cor="#7C8FFF")
    geracao.aulas_geradas.all().delete()
    for mi, m in enumerate(e["modulos"], 1):
        modulo = Modulo.objects.create(curso=curso, titulo=m["titulo"], ordem=mi)
        for ai, a in enumerate(m["aulas"], 1):
            aula = Aula.objects.create(modulo=modulo, titulo=a["titulo"], objetivo=a.get("objetivo", ""),
                                       duracao_min=a["duracao_min"], ordem=ai, precisa_revisao=True)
            AulaGerada.objects.create(geracao=geracao, aula=aula, modulo_num=mi, aula_num=ai,
                                      titulo=a["titulo"], paginas=a["paginas"])
    geracao.curso = curso
    geracao.save(update_fields=["curso"])
    geracao.marcar(status=Geracao.Status.GERANDO, etapa="Gerando as aulas", progresso=0)
    return curso


def _ementa_resumida(ementa):
    linhas = []
    for mi, m in enumerate(ementa["modulos"], 1):
        linhas.append(f"Módulo {mi}: {m['titulo']}")
        for ai, a in enumerate(m["aulas"], 1):
            linhas.append(f"  {mi}.{ai} {a['titulo']} — {a.get('objetivo', '')}")
    return "\n".join(linhas)


def converter_aula(dados, slugs, paginas_validas):
    """Resposta da IA → blocos e questões no formato do banco + lista de problemas."""
    problemas, blocos, questoes = [], [], []
    for i, b in enumerate(dados.get("blocos") or [], 1):
        tipo = b.get("tipo")
        rotulo = f"bloco {i} ({tipo})"
        try:
            config = json.loads(b.get("config_json") or "{}")
        except json.JSONDecodeError as erro:
            problemas.append(f"{rotulo}: config_json não é um JSON válido ({erro.msg}, posição {erro.pos})")
            continue
        roteiro = (b.get("roteiro") or "").strip()
        erros = registro.validar_bloco(tipo, config, roteiro)
        faltando = set(personagens_usados(roteiro)) - set(slugs) if roteiro else set()
        if faltando:
            erros.append(f"roteiro usa personagem que não existe: {', '.join(sorted(faltando))} (use só: {', '.join(slugs)})")
        paginas = sorted({p for p in b.get("paginas_origem") or [] if p in paginas_validas})
        item = {
            "tipo": tipo, "titulo": (b.get("titulo") or "")[:200], "roteiro": roteiro,
            "texto_tela": (b.get("texto_tela") or "").strip(), "config": config, "paginas_origem": paginas,
            # N12: sem página de origem válida, o bloco recebe o selo "além do PDF"
            "alem_do_pdf": bool(b.get("alem_do_pdf")) or not paginas,
            "valido": not erros,
        }
        problemas += [f"{rotulo}: {e}" for e in erros]
        blocos.append(item)
    problemas += [f"aula: {p}" for p in registro.problemas_da_aula([b["tipo"] for b in blocos])]

    for i, q in enumerate(dados.get("questoes") or [], 1):
        alts = [a.strip() for a in q.get("alternativas") or [] if a and a.strip()]
        paginas = sorted({p for p in q.get("paginas_origem") or [] if p in paginas_validas})
        erros = []
        if not (q.get("enunciado") or "").strip():
            erros.append("enunciado vazio")
        if len(alts) < 2:
            erros.append("precisa de pelo menos 2 alternativas")
        if not isinstance(q.get("correta"), int) or not 0 <= q["correta"] < len(alts):
            erros.append("'correta' deve ser o índice de uma alternativa")
        if not paginas:
            erros.append("sem página de origem válida")
        problemas += [f"questão {i}: {e}" for e in erros]
        if not erros:
            questoes.append({
                "enunciado": q["enunciado"].strip(), "alternativas": alts, "correta": q["correta"],
                "explicacao": (q.get("explicacao") or "").strip(), "dificuldade": q.get("dificuldade") or "media",
                "uso": q.get("uso") if q.get("uso") in ("fixacao", "prova") else "prova", "paginas_origem": paginas,
            })
    return blocos, questoes, problemas


def _finalizar_se_terminou(geracao_id):
    geracao = Geracao.objects.get(pk=geracao_id)
    total = geracao.aulas_geradas.count()
    pendentes = geracao.aulas_geradas.filter(status__in=[AulaGerada.Status.PENDENTE, AulaGerada.Status.GERANDO]).count()
    if pendentes == 0:
        geracao.marcar(status=Geracao.Status.PRONTO, etapa="Rascunho pronto para revisão", progresso=100)
    else:
        feitas = total - pendentes
        geracao.marcar(etapa=f"Gerando as aulas ({feitas} de {total} prontas)", progresso=int(100 * feitas / max(total, 1)))


def gerar_aula(aula_gerada_id, instrucao_extra=""):
    ag = AulaGerada.objects.select_related("geracao", "aula__modulo__curso").get(pk=aula_gerada_id)
    geracao, aula = ag.geracao, ag.aula
    if aula is None:  # a aula foi excluída no Estúdio
        ag.status, ag.problemas = AulaGerada.Status.ERRO, ["a aula foi excluída do curso"]
        ag.save(update_fields=["status", "problemas"])
        return _finalizar_se_terminou(geracao.pk)
    curso = aula.modulo.curso
    ag.status = AulaGerada.Status.GERANDO
    ag.instrucao_extra = instrucao_extra or ""
    ag.save(update_fields=["status", "instrucao_extra"])

    avisos = []
    paginas = list(geracao.paginas.filter(numero__in=ag.paginas, sem_texto=False))
    texto = _texto_paginas(paginas)
    if len(texto) > LIMITE_TEXTO_AULA:
        texto = texto[:LIMITE_TEXTO_AULA]
        avisos.append("material desta aula é muito longo; só o início foi usado (divida a aula na ementa)")
    if not texto:
        avisos.append("as páginas desta aula não têm texto legível")
    paginas_validas = set(geracao.paginas.values_list("numero", flat=True))
    personagens = list(curso.personagens.all())
    slugs = [p.slug for p in personagens]
    n_prova = questoes_prova_por_aula(curso, geracao.aulas_geradas.count())
    ementa_aula = next(
        (a for mi, m in enumerate(geracao.ementa.get("modulos") or [], 1) if mi == ag.modulo_num
         for ai, a in enumerate(m["aulas"], 1) if ai == ag.aula_num),
        {"objetivo": aula.objetivo, "duracao_min": aula.duracao_min},
    )
    msgs = ia.mensagens(
        "aula",
        personagens="\n".join(f"- @{p.slug}: {p.nome} ({p.get_papel_display().lower()})" for p in personagens),
        n_prova=n_prova, formato=ia.formato_blocos(), curso=curso.titulo, publico=geracao.publico,
        nivel=geracao.get_nivel_display(), tom=geracao.get_tom_display(), ementa=_ementa_resumida(geracao.ementa),
        modulo_num=ag.modulo_num, aula_num=ag.aula_num, aula_titulo=aula.titulo,
        aula_objetivo=aula.objetivo or ementa_aula.get("objetivo", ""), aula_duracao=aula.duracao_min,
        aula_paginas=compactar(ag.paginas),
        instrucao_extra=f"INSTRUÇÃO EXTRA DO CRIADOR: {instrucao_extra}\n" if instrucao_extra else "",
        texto=texto or "(sem texto)",
    )
    contexto = {"paginas": [p.numero for p in paginas], "slugs": slugs, "n_prova": n_prova, "titulo": aula.titulo}

    melhor = None
    try:
        llm = provedor()
        for tentativa in range(1 + TENTATIVAS_CORRECAO):
            ag.tentativas = tentativa + 1
            r = _chamar(geracao, llm, ChamadaLLM.Etapa.AULA, f"aula {ag.modulo_num}.{ag.aula_num}"
                        + (f" (correção {tentativa})" if tentativa else ""), msgs, ia.SCHEMA_AULA, "aula", contexto)
            blocos, questoes, problemas = converter_aula(r.dados, slugs, paginas_validas)
            if melhor is None or len(problemas) <= len(melhor[2]):
                melhor = (blocos, questoes, problemas)
            if not problemas:
                break
            msgs = msgs + [
                {"role": "assistant", "content": json.dumps(r.dados, ensure_ascii=False)},
                *ia.mensagens("correcao", problemas="\n".join(f"- {p}" for p in problemas)),
            ]
    except ErroLLM as erro:
        if melhor is None:
            ag.status, ag.problemas = AulaGerada.Status.ERRO, avisos + [str(erro)]
            ag.save(update_fields=["status", "problemas", "tentativas"])
            return _finalizar_se_terminou(geracao.pk)
        avisos.append(f"a correção foi interrompida: {erro}")
    except Exception as erro:  # noqa: BLE001 — N13: uma aula com erro não derruba as outras
        log.exception("Falha ao gerar a aula %s", aula_gerada_id)
        ag.status, ag.problemas = AulaGerada.Status.ERRO, [f"erro inesperado: {erro}"]
        ag.save(update_fields=["status", "problemas", "tentativas"])
        return _finalizar_se_terminou(geracao.pk)

    blocos, questoes, problemas = melhor
    validos = [b for b in blocos if b["valido"]]
    if validos:
        with transaction.atomic():
            aula.blocos.all().delete()
            Questao.objects.filter(pk__in=ag.questoes_ids).delete()
            BlocoAula.objects.bulk_create([
                BlocoAula(aula=aula, ordem=i, tipo=b["tipo"], titulo=b["titulo"], roteiro=b["roteiro"],
                          texto_tela=b["texto_tela"], config=b["config"], paginas_origem=b["paginas_origem"],
                          alem_do_pdf=b["alem_do_pdf"])
                for i, b in enumerate(validos, 1)
            ])
            criadas = [
                Questao.objects.create(curso=curso, modulo=aula.modulo, **q) for q in questoes
            ]
            ag.questoes_ids = [q.pk for q in criadas]
            if len(validos) < len(blocos):
                avisos.append(f"{len(blocos) - len(validos)} bloco(s) inválido(s) foram descartados")
            aula.precisa_revisao = bool(problemas)
            aula.save(update_fields=["precisa_revisao"])
    else:
        avisos.append("nenhum bloco válido; o conteúdo anterior da aula foi mantido")
    ag.problemas = avisos + problemas
    ag.status = AulaGerada.Status.OK if validos and not problemas else AulaGerada.Status.REVISAO
    ag.save(update_fields=["status", "problemas", "tentativas", "questoes_ids"])
    return _finalizar_se_terminou(geracao.pk)


# --- 6. relatório ---------------------------------------------------------------------

def relatorio(geracao):
    aulas = list(geracao.aulas_geradas.all())
    curso = geracao.curso
    blocos = list(BlocoAula.objects.filter(aula__modulo__curso=curso)) if curso else []
    questoes = list(Questao.objects.filter(curso=curso, ativa=True)) if curso else []

    paginas = list(geracao.paginas.values("numero", "ocr", "sem_texto"))
    com_texto = {p["numero"] for p in paginas if not p["sem_texto"]}
    sem_conteudo = set((geracao.mapa or {}).get("paginas_sem_conteudo") or [])
    usadas = set()
    for item in [*blocos, *questoes]:
        usadas |= set(item.paginas_origem or [])
    if not curso:  # antes de gerar as aulas, vale o que a ementa cobre
        for m in (geracao.ementa or {}).get("modulos") or []:
            for a in m["aulas"]:
                usadas |= set(a["paginas"])
    nao_aproveitadas = sorted(com_texto - usadas - sem_conteudo)

    etapas = {}
    for c in geracao.chamadas.all():
        e = etapas.setdefault(c.etapa, {"rotulo": c.get_etapa_display(), "chamadas": 0, "falhas": 0,
                                        "tokens_entrada": 0, "tokens_saida": 0, "custo_usd": 0, "duracao_s": 0})
        e["chamadas"] += 1
        e["falhas"] += 0 if c.sucesso else 1
        e["tokens_entrada"] += c.tokens_entrada
        e["tokens_saida"] += c.tokens_saida
        e["custo_usd"] += float(c.custo_usd)
        e["duracao_s"] += c.duracao_s
    custo_ia = sum(e["custo_usd"] for e in etapas.values())

    tts = {"caracteres": 0, "blocos": 0, "custo_usd": 0.0}
    if curso:
        est = estimativa(blocos, personagens_do_curso(curso))
        tts = {**est, "custo_usd": est["caracteres"] / 1_000_000 * settings.TTS_PRECO_1M_CARACTERES}

    prova = sum(1 for q in questoes if q.uso in ("prova", "ambos"))
    return {
        "aulas_total": len(aulas),
        "aulas_ok": sum(1 for a in aulas if a.status == AulaGerada.Status.OK),
        "aulas_revisao": [a for a in aulas if a.status in (AulaGerada.Status.REVISAO, AulaGerada.Status.ERRO)],
        "blocos": len(blocos),
        "blocos_com_origem": sum(1 for b in blocos if b.paginas_origem),
        "blocos_alem_pdf": sum(1 for b in blocos if b.alem_do_pdf),
        "cobertura_n12": 100 if not blocos else round(
            100 * sum(1 for b in blocos if b.paginas_origem or b.alem_do_pdf) / len(blocos)),
        "questoes_prova": prova,
        "questoes_fixacao": sum(1 for q in questoes if q.uso == "fixacao"),
        "questoes_necessarias": math.ceil(curso.questoes_sorteadas * 1.5) if curso else 0,
        "paginas_total": len(paginas),
        "paginas_ocr": compactar(p["numero"] for p in paginas if p["ocr"]),
        "paginas_sem_texto": compactar(p["numero"] for p in paginas if p["sem_texto"]),
        "paginas_nao_aproveitadas": compactar(nao_aproveitadas),
        "n_nao_aproveitadas": len(nao_aproveitadas),
        "etapas": list(etapas.values()),
        "custo_ia_usd": custo_ia,
        "tts": tts,
        "custo_total_usd": custo_ia + tts["custo_usd"],
    }
