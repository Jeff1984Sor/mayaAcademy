import pytest
from django.urls import reverse

from core.models import AuditLog, AuditoriaImutavel


def test_login_por_email(client, aluno):
    r = client.post(reverse("core:login"), {"email": "ALUNO@teste.local", "senha": "SenhaForte!2026"})
    assert r.status_code == 302


def test_rate_limit_de_login(client, aluno):
    for _ in range(5):
        client.post(reverse("core:login"), {"email": "aluno@teste.local", "senha": "errada"})
    r = client.post(reverse("core:login"), {"email": "aluno@teste.local", "senha": "SenhaForte!2026"})
    assert r.status_code == 200
    assert "Muitas tentativas" in r.content.decode()


def test_cadastro_cria_aluno(client, db):
    r = client.post(reverse("core:cadastro"), {
        "nome": "Nova Pessoa", "email": "nova@teste.local", "senha1": "UmaSenhaBoa!77", "senha2": "UmaSenhaBoa!77",
    })
    assert r.status_code == 302
    from core.models import Usuario
    assert Usuario.objects.get(email="nova@teste.local").papel == "aluno"


def test_auditoria_imutavel(db, criador):
    log = AuditLog.objects.create(usuario=criador, acao="teste")
    log.descricao = "mudou"
    with pytest.raises(AuditoriaImutavel):
        log.save()
    with pytest.raises(AuditoriaImutavel):
        log.delete()
    with pytest.raises(AuditoriaImutavel):
        AuditLog.objects.filter(pk=log.pk).update(acao="x")
    with pytest.raises(AuditoriaImutavel):
        AuditLog.objects.all().delete()


def test_saude(client, db):
    r = client.get(reverse("catalogo:saude"))
    assert r.status_code == 200 and r.json()["banco"] == "ok"


def test_home_em_construcao(client, db):
    assert "Em construção" in client.get("/").content.decode()
