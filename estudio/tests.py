import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from conftest import PILOTO
from core.models import AuditLog
from cursos.models import Aula, BlocoAula, Curso


@pytest.fixture
def logado(client, criador):
    client.force_login(criador)
    return client


def test_estudio_exige_criador(client, aluno):
    assert client.get(reverse("estudio:painel")).status_code == 302  # anônimo → login
    client.force_login(aluno)
    assert client.get(reverse("estudio:painel")).status_code == 403


def test_telas_do_estudio_abrem(logado, curso_piloto):
    aula = Aula.objects.get(modulo__curso=curso_piloto)
    bloco = aula.blocos.first()
    for url in [
        reverse("estudio:painel"), reverse("estudio:curso", args=[curso_piloto.pk]),
        reverse("estudio:curso_editar", args=[curso_piloto.pk]), reverse("estudio:aula", args=[aula.pk]),
        reverse("estudio:bloco", args=[bloco.pk]), reverse("estudio:questoes", args=[curso_piloto.pk]),
        reverse("estudio:importar"),
    ]:
        assert logado.get(url).status_code == 200, url


def test_player_permissoes(client, aluno, criador, curso_piloto):
    aula = Aula.objects.get(modulo__curso=curso_piloto)
    url = reverse("aprendizado:aula", args=[aula.pk])
    assert client.get(url).status_code == 403
    client.force_login(criador)
    assert client.get(url).status_code == 200
    # aula de amostra de curso publicado abre para visitante
    client.logout()
    Curso.objects.filter(pk=curso_piloto.pk).update(status="publicado", aula_amostra=aula)
    assert client.get(url).status_code == 200


def test_importar_pela_tela(logado, db):
    arquivo = SimpleUploadedFile("piloto.yaml", PILOTO.read_bytes())
    r = logado.post(reverse("estudio:importar"), {"arquivo": arquivo})
    assert r.status_code == 200 and "Confirmar importação" in r.content.decode()
    r = logado.post(reverse("estudio:importar_confirmar"))
    assert r.status_code == 302
    curso = Curso.objects.get(slug="ia-com-sabedoria")
    assert curso.status == "rascunho"
    assert AuditLog.objects.filter(acao="importar_roteiro").exists()


def test_reordenar_blocos(logado, curso_piloto):
    aula = Aula.objects.get(modulo__curso=curso_piloto)
    ids = list(aula.blocos.values_list("pk", flat=True))[::-1]
    r = logado.post(reverse("estudio:reordenar", args=["blocos"]), json.dumps({"ids": ids, "pai": aula.pk}),
                    content_type="application/json")
    assert r.status_code == 200
    assert list(aula.blocos.order_by("ordem").values_list("pk", flat=True)) == ids


def test_salvar_bloco_com_config_invalida_mostra_erro(logado, curso_piloto):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="quiz_fixacao").first()
    r = logado.post(reverse("estudio:bloco", args=[bloco.pk]), {
        "tipo": "quiz_fixacao", "titulo": "x", "roteiro": "", "texto_tela": "", "config": '{"questoes": []}',
    })
    assert r.status_code == 200
    assert "pelo menos 2" in r.content.decode()


def test_previa_ao_vivo(logado, curso_piloto):
    bloco = BlocoAula.objects.filter(aula__modulo__curso=curso_piloto, tipo="caca_erro").first()
    r = logado.post(reverse("estudio:bloco_previa", args=[bloco.pk]), {
        "tipo": bloco.tipo, "titulo": "Prévia", "roteiro": "", "config": json.dumps(bloco.config),
    })
    assert r.status_code == 200 and "MayaPlayer.montarAula" in r.content.decode()
    r = logado.post(reverse("estudio:bloco_previa", args=[bloco.pk]), {"tipo": bloco.tipo, "config": "{ruim"})
    assert "JSON inválido" in r.content.decode()


def test_publicar_bloqueado_sem_checklist(logado, curso_piloto):
    logado.post(reverse("estudio:curso_publicar", args=[curso_piloto.pk]))
    curso_piloto.refresh_from_db()
    assert curso_piloto.status == "rascunho"


def test_baixar_pacote(logado, curso_piloto):
    r = logado.get(reverse("estudio:curso_pacote", args=[curso_piloto.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "application/zip"


def test_busca_ctrl_k(logado, curso_piloto):
    itens = logado.get(reverse("estudio:busca"), {"q": "alucina"}).json()["itens"]
    assert any(i["tipo"] == "Aula" for i in itens)
