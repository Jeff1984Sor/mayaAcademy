"""Checklist de publicação (seção 8.1 / regra N9)."""
import math

from django.db import transaction
from django.utils import timezone

from . import blocos as registro
from .models import Curso, Questao
from .roteiro import personagens_usados


def checklist(curso):
    modulos = list(curso.modulos.prefetch_related("aulas__blocos").order_by("ordem"))
    personagens = {p.slug: p for p in curso.personagens.all()}
    aulas = [a for m in modulos for a in m.aulas.all()]
    itens = []

    itens.append({"ok": bool(aulas), "texto": "Curso tem pelo menos uma aula", "detalhes": []})

    estrutura, configs, audios, falta_personagem, revisao = [], [], [], [], []
    for aula in aulas:
        blocos = list(aula.blocos.all())
        for p in aula.problemas_estrutura(blocos):
            estrutura.append(f"{aula.titulo}: {p}")
        if aula.precisa_revisao:
            revisao.append(aula.titulo)
        for b in blocos:
            rotulo = f"{aula.titulo} › bloco {b.ordem} ({b.get_tipo_display()})"
            for erro in registro.validar_bloco(b.tipo, b.config, b.roteiro):
                configs.append(f"{rotulo}: {erro}")
            if b.tem_narracao and not b.audio_em_dia(personagens):
                audios.append(rotulo)
            faltando = set(personagens_usados(b.roteiro)) - set(personagens)
            if faltando:
                falta_personagem.append(f"{rotulo}: {', '.join(sorted(faltando))}")

    itens.append({"ok": not estrutura, "texto": f"Todas as aulas com ≥ {registro.MIN_BLOCOS} blocos e ≥ {registro.MIN_INTERATIVOS} interativos", "detalhes": estrutura})
    itens.append({"ok": not configs, "texto": "Todos os blocos com configuração válida", "detalhes": configs})
    itens.append({"ok": not falta_personagem, "texto": "Todos os personagens dos roteiros cadastrados", "detalhes": falta_personagem})
    itens.append({"ok": not audios, "texto": "Todos os áudios gerados e em dia com o roteiro", "detalhes": audios})
    itens.append({"ok": not revisao, "texto": "Nenhuma aula marcada como \"precisa de revisão\"", "detalhes": revisao})

    minimo = math.ceil(curso.questoes_sorteadas * 1.5)
    prova = curso.questoes.filter(ativa=True, uso__in=[Questao.Uso.PROVA, Questao.Uso.AMBOS]).count()
    itens.append({
        "ok": prova >= minimo,
        "texto": f"Banco com ≥ {minimo} questões de prova ({curso.questoes_sorteadas} sorteadas × 1,5)",
        "detalhes": [] if prova >= minimo else [f"há {prova}; faltam {minimo - prova}"],
    })
    return itens


def pode_publicar(curso):
    return all(item["ok"] for item in checklist(curso))


@transaction.atomic
def publicar(curso):
    """Publica se o checklist estiver completo. Republicar incrementa a versão (8.5)."""
    if not pode_publicar(curso):
        return False
    if curso.publicado_em is not None:
        curso.versao += 1
    curso.status = Curso.Status.PUBLICADO
    curso.publicado_em = timezone.now()
    curso.save(update_fields=["status", "versao", "publicado_em", "atualizado_em"])
    return True
