"""Testes do gerador por PDF: N11 (gate da ementa), N12 (origem ou selo), N13 (falha isolada), correção, custo."""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.models import AuditLog
from cursos.models import BlocoAula, Curso, Questao
from geracao import pipeline
from geracao.falso import LLMFalso
from geracao.models import AulaGerada, ChamadaLLM, Geracao
from geracao.paginas import PaginasInvalidas, compactar, expandir
from services.llm import ErroLLM, RespostaLLM


def pdf_de_teste(paginas=6):
    import pymupdf as fitz

    doc = fitz.open()
    for i in range(paginas):
        pg = doc.new_page()
        pg.insert_text((72, 72), f"Pagina {i + 1}. O metodo trabalha respiracao, centro e controle do movimento.")
    dados = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("material.pdf", dados, content_type="application/pdf")


@pytest.fixture
def logado(client, criador):
    client.force_login(criador)
    return client


def _enviar(client, **extra):
    dados = {
        "titulo": "Pilates teste", "publico": "instrutores", "nivel": "iniciante", "tom": "leve",
        "duracao_horas": 2, "n_modulos": 2, "narrador_nome": "Narrador", "mascote_nome": "Maya", "idioma": "pt-BR",
        "declaracao": "on", "pdfs": pdf_de_teste(), **extra,
    }
    return client.post(reverse("geracao:nova"), dados)


def test_paginas_compactar_e_expandir():
    assert compactar([3, 4, 5, 9, 11, 12]) == "3-5, 9, 11-12"
    assert expandir("3-5, 9") == [3, 4, 5, 9]
    with pytest.raises(PaginasInvalidas):
        expandir("9-3")
    with pytest.raises(PaginasInvalidas):
        expandir("1-50", maximo=10)


def test_exige_declaracao_de_direito_de_uso(logado):
    r = _enviar(logado, declaracao="")
    assert r.status_code == 200
    assert not Geracao.objects.exists()


def test_fluxo_completo_para_na_ementa_e_so_gera_apos_aprovacao(logado):
    r = _enviar(logado)
    g = Geracao.objects.get()
    assert r.status_code == 302
    assert AuditLog.objects.filter(acao="pdf_direito_de_uso").exists()
    g.refresh_from_db()
    # N11: para na ementa, sem curso e sem aulas
    assert g.status == Geracao.Status.EMENTA, g.erro
    assert g.paginas.count() == 6
    assert g.curso is None and not Curso.objects.exists()
    assert g.chamadas.filter(etapa="mapa").exists() and g.chamadas.filter(etapa="ementa").exists()

    tela = logado.get(reverse("geracao:detalhe", args=[g.pk]))
    assert "Aprovar e gerar aulas" in tela.content.decode()

    ementa = json.loads(json.dumps(g.ementa))
    for m in ementa["modulos"]:
        for a in m["aulas"]:
            a["paginas_txt"] = compactar(a.pop("paginas"))
    ementa["titulo"] = "Pilates para iniciantes"
    r = logado.post(reverse("geracao:ementa_salvar", args=[g.pk]), {"ementa": json.dumps(ementa), "acao": "gerar"})
    assert r.status_code == 302
    g.refresh_from_db()
    assert g.status == Geracao.Status.PRONTO
    curso = g.curso
    assert curso.titulo == "Pilates para iniciantes" and curso.status == Curso.Status.RASCUNHO
    assert set(curso.personagens.values_list("slug", flat=True)) == {"narrador", "maya"}
    assert g.aulas_geradas.filter(status=AulaGerada.Status.OK).count() == g.aulas_geradas.count() == 4
    # N12: todo bloco e questão com página de origem (ou selo)
    blocos = BlocoAula.objects.filter(aula__modulo__curso=curso)
    assert blocos.count() == 16
    assert all(b.paginas_origem or b.alem_do_pdf for b in blocos)
    assert all(q.paginas_origem for q in Questao.objects.filter(curso=curso))
    rel = pipeline.relatorio(g)
    assert rel["cobertura_n12"] == 100
    assert rel["questoes_prova"] >= rel["questoes_necessarias"]
    assert rel["custo_ia_usd"] > 0

    # ver trecho do PDF
    b = blocos.first()
    trecho = logado.get(reverse("geracao:trecho_bloco", args=[b.pk]))
    assert f"Página {b.paginas_origem[0]}" in trecho.content.decode()


def test_ementa_sem_paginas_nao_gera(logado):
    _enviar(logado)
    g = Geracao.objects.get()
    ementa = {"titulo": "X", "modulos": [{"titulo": "M", "aulas": [{"titulo": "A", "objetivo": "", "paginas_txt": "", "duracao_min": 10}]}]}
    logado.post(reverse("geracao:ementa_salvar", args=[g.pk]), {"ementa": json.dumps(ementa), "acao": "gerar"})
    g.refresh_from_db()
    assert g.status == Geracao.Status.EMENTA and g.curso is None


class LLMComFalhas(LLMFalso):
    """1ª aula: config inválida e depois corrigida; 2ª aula: a API falha sempre."""

    def __init__(self, estado):
        super().__init__()
        self.estado = estado

    def gerar_json(self, mensagens, schema, nome, contexto=None):
        if nome == "aula":
            titulo = (contexto or {}).get("titulo")
            if titulo == "Aula 1.2":
                raise ErroLLM("Erro da OpenAI (HTTP 500).")
            if titulo == "Aula 1.1" and not self.estado.get("corrigido"):
                self.estado["corrigido"] = True
                r = super().gerar_json(mensagens, schema, nome, contexto)
                r.dados["blocos"][2]["config_json"] = '{"instrucao": "x", "trechos": []}'
                return r
        return super().gerar_json(mensagens, schema, nome, contexto)


def test_correcao_e_falha_isolada(logado, monkeypatch):
    estado = {}
    monkeypatch.setattr(pipeline, "provedor", lambda: LLMComFalhas(estado))
    _enviar(logado)
    g = Geracao.objects.get()
    g.refresh_from_db()
    ementa = json.loads(json.dumps(g.ementa))
    for m in ementa["modulos"]:
        for a in m["aulas"]:
            a["paginas_txt"] = compactar(a.pop("paginas"))
    logado.post(reverse("geracao:ementa_salvar", args=[g.pk]), {"ementa": json.dumps(ementa), "acao": "gerar"})
    g.refresh_from_db()
    assert g.status == Geracao.Status.PRONTO
    a11 = g.aulas_geradas.get(modulo_num=1, aula_num=1)
    a12 = g.aulas_geradas.get(modulo_num=1, aula_num=2)
    assert a11.status == AulaGerada.Status.OK and a11.tentativas == 2   # corrigida na 2ª chamada
    assert a12.status == AulaGerada.Status.ERRO                         # N13: falhou sozinha
    assert a12.aula.precisa_revisao
    assert g.aulas_geradas.filter(status=AulaGerada.Status.OK).count() == 3
    assert ChamadaLLM.objects.filter(geracao=g, sucesso=False).exists()


def test_bloco_sem_pagina_recebe_selo():
    blocos, _, problemas = pipeline.converter_aula(
        {"blocos": [{"tipo": "texto_apoio", "titulo": "t", "roteiro": "", "texto_tela": "Oi", "config_json": "{}",
                     "paginas_origem": [999], "alem_do_pdf": False}], "questoes": []},
        ["narrador"], {1, 2, 3},
    )
    assert blocos[0]["alem_do_pdf"] is True and blocos[0]["paginas_origem"] == []
    assert any("mínimo" in p for p in problemas)


def test_gerar_de_novo_substitui_conteudo(logado):
    _enviar(logado)
    g = Geracao.objects.get()
    ementa = json.loads(json.dumps(g.ementa))
    for m in ementa["modulos"]:
        for a in m["aulas"]:
            a["paginas_txt"] = compactar(a.pop("paginas"))
    logado.post(reverse("geracao:ementa_salvar", args=[g.pk]), {"ementa": json.dumps(ementa), "acao": "gerar"})
    ag = g.aulas_geradas.first()
    questoes_antes = Questao.objects.filter(curso=g.curso).count()
    r = logado.post(reverse("geracao:aula_de_novo", args=[ag.pk]), {"instrucao": "mais leve"})
    assert r.status_code == 302
    ag.refresh_from_db()
    assert ag.status == AulaGerada.Status.OK and ag.instrucao_extra == "mais leve"
    assert ag.aula.blocos.count() == 4
    assert Questao.objects.filter(curso=g.curso).count() == questoes_antes


def test_custo_calculado_pelos_precos_do_env():
    r = RespostaLLM({}, 1_000_000, 500_000, "m", 1.0)
    assert float(r.custo_usd) == pytest.approx(2.0 + 4.0)


def test_aluno_nao_acessa_gerador(client, aluno):
    client.force_login(aluno)
    assert client.get(reverse("geracao:lista")).status_code in (302, 403)


# --- Configurar IA pela tela ------------------------------------------------------------

def test_config_ia_pela_tela_cifra_a_chave_e_vale_mais_que_o_env(logado, settings):
    from geracao import config_ia
    from geracao.models import ConfiguracaoIA

    settings.OPENAI_API_KEY = "sk-do-env-0000000000000"
    settings.OPENAI_MODEL = "modelo-do-env"
    r = logado.post(reverse("geracao:config_ia"), {
        "chave": "sk-teste-1234567890abcdef", "modelo": "gpt-6.1-sol", "preco_entrada_1m": "2", "preco_saida_1m": "10", "tts_provedor": "nulo", "tts_modelo": "gpt-4o-mini-tts", "voz_narrador": "cedar", "voz_mascote": "marin",
    })
    assert r.status_code == 302
    salvo = ConfiguracaoIA.atual()
    assert "sk-teste" not in salvo.chave_cifrada  # criptografada
    c = config_ia.atual()
    assert (c.chave, c.modelo, c.origem) == ("sk-teste-1234567890abcdef", "gpt-6.1-sol", "tela")
    assert AuditLog.objects.filter(acao="config_ia_alterada").exists()
    tela = logado.get(reverse("geracao:config_ia")).content.decode()
    assert "sk-tes…cdef" in tela and "sk-teste-1234567890abcdef" not in tela
    # salvar de novo sem chave mantém a anterior
    logado.post(reverse("geracao:config_ia"), {"chave": "", "modelo": "outro", "preco_entrada_1m": "1", "preco_saida_1m": "5", "tts_provedor": "nulo", "tts_modelo": "gpt-4o-mini-tts", "voz_narrador": "cedar", "voz_mascote": "marin"})
    assert config_ia.atual().chave == "sk-teste-1234567890abcdef"
    # o custo passa a usar o preço da tela
    assert float(RespostaLLM({}, 1_000_000, 1_000_000, "m", 1).custo_usd) == pytest.approx(6.0)


def test_config_ia_rejeita_chave_estranha(logado):
    r = logado.post(reverse("geracao:config_ia"), {"chave": "minha senha", "modelo": "x", "preco_entrada_1m": "1", "preco_saida_1m": "1", "tts_provedor": "nulo", "tts_modelo": "gpt-4o-mini-tts", "voz_narrador": "cedar", "voz_mascote": "marin"})
    assert r.status_code == 200 and "não parece uma chave" in r.content.decode()


def test_listar_modelos_filtra_e_marca_sugestao(logado, monkeypatch):
    from geracao import config_ia

    class _M:
        def __init__(self, i):
            self.id = i

    class _Cliente:
        def __init__(self, **kw):
            self.models = self

        def list(self):
            return type("R", (), {"data": [_M("gpt-6.1-sol"), _M("gpt-6-luna"), _M("gpt-realtime"), _M("text-embedding-3")]})()

    monkeypatch.setattr("openai.OpenAI", _Cliente)
    r = logado.post(reverse("geracao:config_ia_modelos"), json.dumps({"chave": "sk-x-123456789012345"}), content_type="application/json")
    ids = [m["id"] for m in r.json()["modelos"]]
    assert ids == ["gpt-6-luna", "gpt-6.1-sol"]
    assert config_ia.sugestao_para("gpt-6.1-sol")["entrada"] == "2"


def test_gerador_avisa_quando_ia_nao_configurada(logado, settings):
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = ""
    assert "IA ainda não está configurada" in logado.get(reverse("geracao:lista")).content.decode()


# --- narração pela OpenAI ---------------------------------------------------------------

def _mp3(segundos):
    """MP3 válido (frames de silêncio) com a duração aproximada pedida."""
    quadro = bytes.fromhex("fffb9064") + b"\x00" * 413  # MPEG1 Layer3 128kbps 44.1kHz: 417 bytes, ~26 ms
    return quadro * max(1, round(segundos / 0.026122))


def test_frases_do_ssml_volta_ao_texto():
    from services.tts import _frases_do_ssml, montar_ssml

    ssml = montar_ssml(["Oi!", "Respire [pausa] e *solte*.", "Fim & pronto."])
    assert _frases_do_ssml(ssml) == [("f0", "Oi!"), ("f1", "Respire e solte."), ("f2", "Fim & pronto.")]


def test_openai_tts_mede_cada_frase(monkeypatch):
    from services import tts

    chamadas = []

    class _Resp:
        def __init__(self, dados):
            self.dados = dados

        def read(self):
            return self.dados

    class _Cliente:
        def __init__(self, **kw):
            self.audio = self
            self.speech = self

        def create(self, **kw):
            chamadas.append(kw)
            return _Resp(_mp3(1.0 if kw["input"] == "Oi!" else 2.0))

    monkeypatch.setattr("openai.OpenAI", _Cliente)
    p = tts.OpenAITTS("sk-x-1234567890")
    mp3, marcas = p.sintetizar(tts.montar_ssml(["Oi!", "Tudo bem com você?"]), "marin")
    assert marcas["f0"] == 0 and 0.9 < marcas["f1"] < 1.1 and 2.9 < marcas["fim"] < 3.1
    assert len(chamadas) == 2 and chamadas[0]["voice"] == "marin" and "instructions" in chamadas[0]


def test_voz_escolhida_na_tela_liga_a_narracao(db, settings):
    from cursos.models import Personagem
    from geracao import config_ia
    from geracao.models import ConfiguracaoIA
    from services import tts

    settings.TTS_PROVIDER = "nulo"
    ConfiguracaoIA.objects.create(pk=1, chave_cifrada=config_ia.cifrar("sk-x-1234567890abc"), modelo="m",
                                  tts_provedor="openai", voz_narrador="ash", voz_mascote="coral")
    p = tts.provedor()
    assert p.nome == "openai" and p.gera_audio
    assert p.voz_para(Personagem(papel="mascote", voz_nome="pt-BR-Neural2-C")) == "coral"
    assert p.voz_para(Personagem(papel="narrador", voz_nome="onyx")) == "onyx"
