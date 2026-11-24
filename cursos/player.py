"""Monta os dados que o player JS consome (um JSON por aula)."""
from services import storage

from . import blocos as registro
from .roteiro import parse_roteiro, timestamps_estimados


def dados_personagem(p):
    return {
        "slug": p.slug, "nome": p.nome, "papel": p.papel, "cor": p.cor,
        "avatar": storage.url(p.avatar.name) if p.avatar else "", "avatar_padrao": p.avatar_padrao,
    }


def dados_bloco(bloco, personagens):
    em_dia = bloco.audio_em_dia(personagens)
    if bloco.tem_narracao and em_dia and bloco.audio:
        audio, timeline, duracao = storage.url(bloco.audio.name), bloco.timestamps, bloco.duracao
    else:
        audio = ""
        velocidades = {s: p.voz_velocidade for s, p in personagens.items()}
        timeline = timestamps_estimados(parse_roteiro(bloco.roteiro), velocidades)
        duracao = timeline[-1]["fim"] if timeline else 0
    return {
        "id": bloco.pk, "ordem": bloco.ordem, "tipo": bloco.tipo, "titulo": bloco.titulo,
        "interativo": registro.eh_interativo(bloco.tipo), "texto_tela": bloco.texto_tela, "config": bloco.config,
        "audio": audio, "duracao": duracao, "timeline": timeline, "alem_do_pdf": bloco.alem_do_pdf,
    }


def dados_aula(aula, blocos=None, personagens=None):
    curso = aula.modulo.curso
    if personagens is None:
        personagens = {p.slug: p for p in curso.personagens.all()}
    blocos = list(aula.blocos.all()) if blocos is None else blocos
    return {
        "aula": {"id": aula.pk, "titulo": aula.titulo, "xp": aula.xp, "objetivo": aula.objetivo},
        "curso": {"titulo": curso.titulo, "slug": curso.slug, "cor_primaria": curso.cor_primaria, "cor_secundaria": curso.cor_secundaria},
        "personagens": {s: dados_personagem(p) for s, p in personagens.items()},
        "blocos": [dados_bloco(b, personagens) for b in blocos],
    }
