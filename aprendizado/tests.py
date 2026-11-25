"""Testes da F3 a F6: aprendizado (N1, N2, N8), prova (N3, N4), certificado (N5), XP/medalhas,
organizações (N6), pagamentos (N7) e catálogo."""
import json
import random
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from aprendizado import regras as apr
from aprendizado.models import Matricula
from avaliacoes import regras as aval
from certificados.models import Certificado
from core.models import AuditLog, Organizacao, Usuario
from cursos.models import Aula, BlocoAula, Curso
from gamificacao import regras as gami
from gamificacao.models import MedalhaAluno
from organizacoes import regras as org_regras
from organizacoes.models import Convite, LicencaOrganizacao
from pagamentos.models import Pedido


@pytest.fixture
def curso(curso_piloto):
    """Curso piloto publicado com 2 aulas (a 2ª é cópia da 1ª)."""
    aula1 = Aula.objects.filter(modulo__curso=curso_piloto).first()
    aula2 = Aula.objects.create(modulo=aula1.modulo, titulo="Segunda aula", ordem=aula1.ordem + 1, xp=50)
    for b in aula1.blocos.all():
        BlocoAula.objects.create(aula=aula2, ordem=b.ordem, tipo=b.tipo, titulo=b.titulo, roteiro=b.roteiro, config=b.config)
    curso_piloto.status = Curso.Status.PUBLICADO
    curso_piloto.save()
    return curso_piloto


def _concluir_todas(matricula):
    for aula in apr.aulas_em_ordem(matricula.curso):
        apr.concluir_aula(matricula, aula, {})


def _responder_certo(tentativa):
    return {str(i): q["correta"] for i, q in enumerate(tentativa.questoes)}


# --- N1 / N8 -------------------------------------------------------------------------

def test_aulas_liberadas_em_ordem_e_progresso_salvo(client, aluno, curso):
    m, _ = apr.matricular(aluno, curso)
    aula1, aula2 = apr.aulas_em_ordem(curso)
    client.force_login(aluno)
    # N1: a 2ª aula redireciona com aviso enquanto a 1ª não é concluída
    r = client.get(reverse("aprendizado:aula", args=[aula2.pk]))
    assert r.status_code == 302 and r.url == reverse("aprendizado:curso", args=[curso.slug])
    assert client.get(reverse("aprendizado:aula", args=[aula1.pk])).status_code == 200

    # N8: progresso a cada bloco
    b1, b2 = list(aula1.blocos.values_list("id", flat=True))[:2]
    r = client.post(reverse("aprendizado:progresso", args=[aula1.pk]),
                    json.dumps({"indice": 2, "concluidos": [b1, b2], "segundos": 30}), content_type="application/json")
    assert r.status_code == 200
    p = m.progressos.get(aula=aula1)
    assert p.ultimo_indice == 2 and set(p.blocos_concluidos) == {b1, b2} and p.tempo_gasto_s == 30
    # retoma de onde parou
    tela = client.get(reverse("aprendizado:aula", args=[aula1.pk])).content.decode()
    assert '"retomar": 2' in tela

    # concluir exige as atividades interativas
    r = client.post(reverse("aprendizado:concluir", args=[aula1.pk]), json.dumps({"concluidos": [b1]}), content_type="application/json")
    assert r.status_code == 400
    todos = list(aula1.blocos.values_list("id", flat=True))
    r = client.post(reverse("aprendizado:concluir", args=[aula1.pk]),
                    json.dumps({"concluidos": todos, "resultados": {str(todos[-1]): {"acertosPrimeira": 2}}}),
                    content_type="application/json")
    assert r.status_code == 200 and r.json()["xp"] > 0
    assert client.get(reverse("aprendizado:aula", args=[aula2.pk])).status_code == 200
    # XP idempotente: concluir de novo não soma
    xp = gami.xp_total(aluno)
    client.post(reverse("aprendizado:concluir", args=[aula1.pk]), json.dumps({"concluidos": todos}), content_type="application/json")
    assert gami.xp_total(aluno) == xp


def test_sem_matricula_nao_ve_aula(client, aluno, curso):
    client.force_login(aluno)
    aula = apr.aulas_em_ordem(curso)[0]
    assert client.get(reverse("aprendizado:aula", args=[aula.pk])).status_code == 403


# --- N2 / N3 / N4 / N5 ---------------------------------------------------------------------

def test_prova_so_com_todas_as_aulas(aluno, curso):
    m, _ = apr.matricular(aluno, curso)
    assert any("Conclua todas as aulas" in p for p in aval.pendencias(m))
    assert aval.iniciar(m) is None
    _concluir_todas(m)
    assert aval.pendencias(m) == []


def test_sorteio_embaralha_e_guarda_snapshot(aluno, curso):
    m, _ = apr.matricular(aluno, curso)
    _concluir_todas(m)
    a = aval.sortear(curso, random.Random(1))
    b = aval.sortear(curso, random.Random(2))
    assert len(a) == curso.questoes_sorteadas
    assert [(q["id"], q["alternativas"]) for q in a] != [(q["id"], q["alternativas"]) for q in b]
    for q in a:  # a correta continua apontando para o texto certo depois de embaralhar
        from cursos.models import Questao

        original = Questao.objects.get(pk=q["id"])
        assert q["alternativas"][q["correta"]] == original.alternativas[original.correta]


def test_tentativas_limitadas_e_liberacao_extra(client, criador, aluno, curso):
    curso.tentativas = 1
    curso.save()
    m, _ = apr.matricular(aluno, curso)
    _concluir_todas(m)
    t = aval.iniciar(m)
    errado = {str(i): (q["correta"] + 1) % len(q["alternativas"]) for i, q in enumerate(t.questoes)}
    aval.finalizar(t, errado)
    assert any("tentativas" in p for p in aval.pendencias(m))
    client.force_login(criador)
    client.post(reverse("estudio:liberar_tentativa", args=[m.pk]))
    m.refresh_from_db()
    assert m.tentativas_extras == 1 and aval.pendencias(m) == []
    assert AuditLog.objects.filter(acao="tentativa_extra").exists()


def test_aprovacao_emite_certificado_valido(client, aluno, curso):
    m, _ = apr.matricular(aluno, curso)
    _concluir_todas(m)
    client.force_login(aluno)
    client.post(reverse("avaliacoes:prova", args=[curso.slug]), {"acao": "iniciar"})
    t = aval.tentativa_aberta(m)
    respostas = {f"q_{k}": v for k, v in _responder_certo(t).items()}
    r = client.post(reverse("avaliacoes:responder", args=[curso.slug]), respostas)
    assert r.status_code == 302
    t.refresh_from_db()
    assert t.aprovado and t.nota == 100
    m.refresh_from_db()
    assert m.status == Matricula.Status.CONCLUIDA
    cert = Certificado.objects.get(matricula=m)
    assert cert.codigo.startswith("MA-")
    # validação pública (sem login) e PDF
    client.logout()
    pagina = client.get(reverse("certificados:validar", args=[cert.codigo]))
    assert pagina.status_code == 200 and "Certificado válido" in pagina.content.decode()
    assert client.get(reverse("certificados:validar", args=["MA-XXXXX-XXXXX"])).status_code == 404
    pdf = client.get(reverse("certificados:baixar", args=[cert.codigo]))
    assert pdf.status_code == 200 and b"".join(pdf.streaming_content).startswith(b"%PDF")
    # medalhas: primeiro certificado e nota 100
    slugs = set(MedalhaAluno.objects.filter(aluno=aluno).values_list("medalha__slug", flat=True))
    assert {"primeiro-certificado", "nota-100", "maratonista"} <= slugs


# --- N6: organizações ------------------------------------------------------------------------

def test_convite_consome_vaga_so_no_aceite(curso, aluno):
    org = Organizacao.objects.create(nome="Empresa X")
    lic = LicencaOrganizacao.objects.create(organizacao=org, curso=curso, vagas=1, validade=timezone.localdate() + timedelta(days=30))
    criados, _, erro = org_regras.enviar_convites(lic, ["a@x.com", "b@x.com", "a@x.com"])
    assert erro is None and len(criados) == 2 and lic.vagas_usadas == 0
    m = org_regras.aceitar(criados[0], aluno)
    assert m.origem == Matricula.Origem.CONVITE_ORG and m.organizacao == org
    assert lic.vagas_usadas == 1 and lic.cheia
    outro = Usuario.objects.create_user("b@x.com", "SenhaForte!2026", nome="B")
    with pytest.raises(org_regras.ConviteInvalido):
        org_regras.aceitar(criados[1], outro)
    _, _, erro = org_regras.enviar_convites(lic, ["c@x.com"])
    assert erro and "cheia" in erro


def test_convite_expira_com_a_licenca(curso, aluno):
    org = Organizacao.objects.create(nome="Empresa Y")
    lic = LicencaOrganizacao.objects.create(organizacao=org, curso=curso, vagas=5, validade=timezone.localdate() + timedelta(days=1))
    convite = Convite.objects.create(licenca=lic, email=aluno.email)
    lic.validade = timezone.localdate() - timedelta(days=1)
    lic.save()
    convite.refresh_from_db()
    assert convite.situacao == "expirado"
    with pytest.raises(org_regras.ConviteInvalido):
        org_regras.aceitar(convite, aluno)


def test_painel_do_gestor_e_csv(client, curso, aluno):
    org = Organizacao.objects.create(nome="Empresa Z")
    gestor = Usuario.objects.create_user("gestor@z.com", "SenhaForte!2026", nome="Gestor", papel="gestor", organizacao=org)
    lic = LicencaOrganizacao.objects.create(organizacao=org, curso=curso, vagas=3, validade=timezone.localdate() + timedelta(days=30))
    client.force_login(gestor)
    r = client.post(reverse("organizacoes:convidar"), {"licenca": lic.pk, "emails": aluno.email})
    assert r.status_code == 302
    convite = Convite.objects.get(email=aluno.email)
    client.force_login(aluno)
    client.post(reverse("organizacoes:convite", args=[convite.token]))
    client.force_login(gestor)
    assert aluno.email in client.get(reverse("organizacoes:painel")).content.decode()
    csv = client.get(reverse("organizacoes:painel") + "?formato=csv")
    assert csv["Content-Type"].startswith("text/csv") and aluno.email in csv.content.decode("utf-8")
    # aluno comum não entra no painel
    client.force_login(aluno)
    assert client.get(reverse("organizacoes:painel")).status_code == 403


# --- N7: pagamentos ---------------------------------------------------------------------------

def test_matricula_paga_so_pelo_webhook_e_idempotente(client, aluno, curso):
    curso.modo_acesso = Curso.Acesso.PAGO
    curso.preco = 197
    curso.save()
    client.force_login(aluno)
    r = client.post(reverse("pagamentos:comprar", args=[curso.slug]))
    pedido = Pedido.objects.get()
    assert r.status_code == 302 and pedido.status == Pedido.Status.PENDENTE
    # o redirect/retorno não matricula
    client.get(reverse("pagamentos:pedido", args=[pedido.pk]))
    assert not Matricula.objects.filter(aluno=aluno).exists()
    corpo = json.dumps({"id_externo": pedido.id_externo, "status": "pago"})
    sem_segredo = client.post(reverse("pagamentos:webhook", args=["manual"]), corpo, content_type="application/json")
    assert sem_segredo.status_code == 400
    for _ in range(2):  # webhook duplicado
        r = client.post(reverse("pagamentos:webhook", args=["manual"]), corpo, content_type="application/json",
                        HTTP_X_WEBHOOK_SEGREDO="segredo-de-teste")
        assert r.status_code == 200
    assert Matricula.objects.filter(aluno=aluno, curso=curso, origem="compra").count() == 1
    pedido.refresh_from_db()
    assert pedido.status == Pedido.Status.PAGO


def test_confirmacao_manual_pelo_criador(client, criador, aluno, curso):
    curso.modo_acesso = Curso.Acesso.PAGO
    curso.save()
    client.force_login(aluno)
    client.post(reverse("pagamentos:comprar", args=[curso.slug]))
    pedido = Pedido.objects.get()
    client.force_login(criador)
    client.post(reverse("pagamentos:confirmar_manual", args=[pedido.pk]), {"acao": "confirmar"})
    assert Matricula.objects.filter(aluno=aluno, curso=curso).exists()
    assert AuditLog.objects.filter(acao="pedido_pago").exists()


# --- catálogo e publicação --------------------------------------------------------------------

def test_catalogo_e_matricula_gratuita(client, aluno, curso):
    home = client.get(reverse("catalogo:home")).content.decode()
    assert curso.titulo in home
    assert client.get(reverse("catalogo:curso", args=[curso.slug])).status_code == 200
    client.force_login(aluno)
    r = client.post(reverse("catalogo:matricular", args=[curso.slug]))
    assert r.status_code == 302 and Matricula.objects.filter(aluno=aluno, curso=curso).exists()
    assert curso.titulo in client.get(reverse("aprendizado:meus_cursos")).content.decode()
    for nome in ("aprendizado:perfil", "certificados:meus"):
        assert client.get(reverse(nome)).status_code == 200


def test_rascunho_nao_aparece_no_catalogo(client, curso_piloto):
    assert client.get(reverse("catalogo:curso", args=[curso_piloto.slug])).status_code == 404


def test_paginas_do_criador_abrem(client, criador, aluno, curso):
    apr.matricular(aluno, curso)
    org = Organizacao.objects.create(nome="Org")
    client.force_login(criador)
    for url in (
        reverse("estudio:alunos", args=[curso.pk]), reverse("estudio:relatorios"),
        reverse("organizacoes:lista"), reverse("organizacoes:detalhe", args=[org.pk]),
        reverse("organizacoes:painel") + f"?org={org.pk}", reverse("pagamentos:painel"),
    ):
        assert client.get(url).status_code == 200, url
