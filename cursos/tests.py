import io
import zipfile

import pytest

from cursos import blocos as registro
from cursos import publicacao
from cursos.audio import estimativa, gerar_audio_bloco
from cursos.bundle import montar
from cursos.exemplos import EXEMPLOS
from cursos.models import BlocoAula
from cursos.pacote import gerar_zip
from cursos.roteiro import parse_roteiro, timestamps_estimados
from cursos.roteiro_io import exportar, importar, ler, validar
from services.tts import montar_ssml


# ---------------------------------------------------------------- roteiro

def test_parse_roteiro_personagens_e_frases():
    falas = parse_roteiro("@maya: Oi! Tudo bem?\nContinua a Maya.\n@narrador: Agora eu.\n\nOutra fala do narrador.")
    assert [f["personagem"] for f in falas] == ["maya", "narrador", "narrador"]
    assert falas[0]["frases"] == ["Oi!", "Tudo bem?", "Continua a Maya."]


def test_roteiro_sem_prefixo_e_do_narrador():
    assert parse_roteiro("Uma frase.")[0]["personagem"] == "narrador"


def test_timestamps_estimados_crescentes():
    t = timestamps_estimados(parse_roteiro("@a: Um. Dois. Três."))
    assert [x["frase"] for x in t] == [0, 1, 2]
    assert all(t[i]["fim"] <= t[i + 1]["inicio"] for i in range(len(t) - 1))


def test_ssml_tem_mark_por_frase_e_pausa():
    ssml = montar_ssml(["Olá [pausa 800ms] mundo.", "Tchau *agora*."])
    assert '<mark name="f0"/>' in ssml and '<mark name="f1"/>' in ssml and '<mark name="fim"/>' in ssml
    assert '<break time="800ms"/>' in ssml and "<emphasis" in ssml


# ---------------------------------------------------------------- schemas dos blocos

@pytest.mark.parametrize("tipo", list(registro.TIPOS))
def test_exemplo_de_cada_tipo_e_valido(tipo):
    ex = EXEMPLOS[tipo]
    assert registro.validar_bloco(tipo, ex["config"], ex.get("roteiro", "")) == []


def test_quiz_correta_fora_das_alternativas():
    cfg = {"questoes": [{"enunciado": "a", "alternativas": ["x", "y"], "correta": 3, "explicacao": "e"}] * 2}
    assert any("correta" in e for e in registro.validar_config("quiz_fixacao", cfg))


def test_cenario_destino_inexistente():
    cfg = {"inicio": "a", "nos": [{"id": "a", "texto": "t", "escolhas": [{"texto": "x", "consequencia": "c", "vai_para": "zz"}]}]}
    erros = registro.validar_config("cenario_ramificado", cfg)
    assert any("zz" in e for e in erros)


def test_cena_narrada_visual_aponta_frase_inexistente():
    erros = registro.validar_bloco("cena_narrada", {"visuais": [{"frase": 5, "tipo": "titulo"}]}, "@n: Uma só.")
    assert any("frase" in e for e in erros)


def test_regra_da_aula_minimo_4_blocos_2_interativos():
    assert registro.problemas_da_aula(["cena_narrada", "quiz_fixacao", "caca_erro", "dialogo"]) == []
    assert registro.problemas_da_aula(["cena_narrada", "quiz_fixacao", "dialogo", "texto_apoio"])
    assert registro.problemas_da_aula(["texto_apoio"] * 4)


# ---------------------------------------------------------------- importador / exportador

def test_piloto_valida_sem_erros(db, dados_piloto):
    rel = validar(dados_piloto)
    assert rel.ok, rel.erros


def test_exemplo_da_documentacao_e_valido(db):
    """O exemplo completo de docs/formato-roteiro.md precisa continuar importável."""
    from pathlib import Path

    doc = (Path(__file__).resolve().parent.parent / "docs" / "formato-roteiro.md").read_text(encoding="utf-8")
    secao = doc.split("## 4. Exemplo completo de uma aula", 1)[1]
    yaml_exemplo = secao.split("```yaml", 1)[1].split("```", 1)[0]
    dados = ler(yaml_exemplo)
    rel = validar(dados)
    assert rel.ok, rel.erros
    curso = importar(dados)
    assert BlocoAula.objects.filter(aula__modulo__curso=curso).count() == 4


def test_importa_piloto_como_rascunho(curso_piloto):
    assert curso_piloto.status == "rascunho"
    assert BlocoAula.objects.filter(aula__modulo__curso=curso_piloto).count() == 7
    assert curso_piloto.questoes.count() == 8


def test_erro_de_importacao_informa_linha(db):
    dados = ler("curso:\n  titulo: X\nmodulos:\n  - titulo: M\n    aulas:\n      - titulo: A\n        blocos:\n          - tipo: nao_existe\n")
    rel = validar(dados)
    assert not rel.ok
    erro = next(e for e in rel.erros if "nao_existe" in e["mensagem"])
    assert erro["linha"] == 8


def test_exportar_e_reimportar(curso_piloto):
    texto = exportar(curso_piloto).replace("slug: ia-com-sabedoria", "slug: ia-com-sabedoria-copia")
    dados = ler(texto)
    rel = validar(dados)
    assert rel.ok, rel.erros
    copia = importar(dados)
    assert BlocoAula.objects.filter(aula__modulo__curso=copia).count() == 7


# ---------------------------------------------------------------- áudio (N10)

def test_n10_audio_so_regera_quando_roteiro_muda(curso_piloto, tts_falso):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="dialogo").first()
    assert gerar_audio_bloco(bloco, provedor=tts_falso) == "gerado"
    chamadas = tts_falso.chamadas
    assert chamadas > 0
    bloco.refresh_from_db()
    assert gerar_audio_bloco(bloco, provedor=tts_falso) == "em_dia"
    assert tts_falso.chamadas == chamadas  # nenhuma chamada nova à API
    bloco.roteiro += "\n@maya: Frase nova."
    bloco.save()
    assert gerar_audio_bloco(bloco, provedor=tts_falso) == "gerado"
    assert tts_falso.chamadas > chamadas


def test_trocar_voz_desatualiza_audio(curso_piloto, tts_falso):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="dialogo").first()
    gerar_audio_bloco(bloco, provedor=tts_falso)
    bloco.refresh_from_db()
    assert bloco.audio_em_dia()
    curso_piloto.personagens.filter(slug="maya").update(voz_nome="pt-BR-Wavenet-A")
    assert not bloco.audio_em_dia()


def test_timeline_do_audio_usa_marcas(curso_piloto, tts_falso):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="cena_narrada").first()
    gerar_audio_bloco(bloco, provedor=tts_falso)
    bloco.refresh_from_db()
    total_frases = sum(len(f["frases"]) for f in bloco.falas())
    assert len(bloco.timestamps) == total_frases
    assert bloco.timestamps[0]["inicio"] == 0


def test_estimativa_conta_so_desatualizados(curso_piloto, tts_falso):
    blocos = list(BlocoAula.objects.filter(aula__modulo__curso=curso_piloto))
    antes = estimativa(blocos)
    assert antes["blocos"] == 3  # cena, diálogo e chat têm narração
    gerar_audio_bloco(blocos[0], provedor=tts_falso)
    blocos = list(BlocoAula.objects.filter(aula__modulo__curso=curso_piloto))
    assert estimativa(blocos)["blocos"] == 2


# ---------------------------------------------------------------- publicação (N9) e versão

def test_n9_nao_publica_sem_audio(curso_piloto, settings):
    settings.TTS_PROVIDER = "google"
    settings.GOOGLE_TTS_API_KEY = "chave-falsa"
    assert not publicacao.pode_publicar(curso_piloto)
    itens = {i["texto"]: i for i in publicacao.checklist(curso_piloto)}
    assert not itens["Todos os áudios gerados e em dia com o roteiro"]["ok"]
    assert not publicacao.publicar(curso_piloto)


def test_sem_provedor_de_voz_legendas_bastam(curso_piloto):
    itens = {i["texto"]: i for i in publicacao.checklist(curso_piloto)}
    assert itens["Narração por legendas cronometradas (voz desligada: TTS_PROVIDER=nulo)"]["ok"]


def test_publica_e_republica_incrementa_versao(curso_piloto, tts_falso):
    for b in BlocoAula.objects.filter(aula__modulo__curso=curso_piloto):
        gerar_audio_bloco(b, provedor=tts_falso)
    assert publicacao.publicar(curso_piloto), publicacao.checklist(curso_piloto)
    assert curso_piloto.versao == 1
    assert publicacao.publicar(curso_piloto)
    assert curso_piloto.versao == 2


# ---------------------------------------------------------------- player e pacote

def test_bundle_tem_todos_os_componentes():
    js = montar()
    for tipo in registro.TIPOS:
        assert f"{tipo} = {{" in js or f"const {tipo} = " in js, tipo
    assert "window.MayaPlayer" in js
    assert "\nimport " not in js and "\nexport " not in js


def test_pacote_scorm(curso_piloto, tts_falso):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="dialogo").first()
    gerar_audio_bloco(bloco, provedor=tts_falso)
    z = zipfile.ZipFile(io.BytesIO(gerar_zip(curso_piloto)))
    nomes = set(z.namelist())
    for esperado in ("index.html", "imsmanifest.xml", "dados/curso.js", "player/player.bundle.js", "player/pacote.js",
                     "player/gsap.min.js", "fonts/dm-sans-latin.woff2", f"audio/bloco-{bloco.pk}.mp3"):
        assert esperado in nomes, esperado
    manifesto = z.read("imsmanifest.xml").decode()
    assert "<schemaversion>1.2</schemaversion>" in manifesto
    assert f'href="audio/bloco-{bloco.pk}.mp3"' in manifesto
    assert f'"audio": "audio/bloco-{bloco.pk}.mp3"' in z.read("dados/curso.js").decode()
