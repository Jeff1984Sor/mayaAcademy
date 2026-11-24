"""Geração de narração por bloco (N10: só chama o TTS se o hash mudou)."""
import io
import logging

from mutagen.mp3 import MP3

from services import storage, tts

from .roteiro import parse_roteiro, texto_legenda, timestamps_estimados

log = logging.getLogger(__name__)


def personagens_do_curso(curso):
    return {p.slug: p for p in curso.personagens.all()}


def caracteres_ssml(bloco, personagens=None):
    """Estimativa de caracteres cobrados pelo TTS (o Google cobra pelo SSML)."""
    return sum(len(tts.montar_ssml(f["frases"])) for f in parse_roteiro(bloco.roteiro))


def _duracao_mp3(dados):
    try:
        return MP3(io.BytesIO(dados)).info.length
    except Exception:  # noqa: BLE001 — mp3 inválido não deve derrubar o lote
        return 0.0


def gerar_audio_bloco(bloco, forcar=False, provedor=None, personagens=None):
    """Retorna 'gerado', 'em_dia', 'sem_narracao' ou 'estimado' (provedor nulo)."""
    personagens = personagens if personagens is not None else personagens_do_curso(bloco.aula.modulo.curso)
    falas = parse_roteiro(bloco.roteiro)
    if not falas:
        return "sem_narracao"
    novo_hash = bloco.calcular_hash(personagens)
    if not forcar and bloco.audio and bloco.hash_roteiro == novo_hash:
        return "em_dia"

    provedor = provedor or tts.provedor()
    faltando = sorted({f["personagem"] for f in falas} - set(personagens))
    if faltando:
        raise tts.ErroTTS(f"Personagem(ns) sem cadastro no curso: {', '.join(faltando)}")

    velocidades = {slug: p.voz_velocidade for slug, p in personagens.items()}
    if not provedor.gera_audio:
        bloco.timestamps = timestamps_estimados(falas, velocidades)
        bloco.duracao = bloco.timestamps[-1]["fim"] if bloco.timestamps else 0
        bloco.caracteres_tts = caracteres_ssml(bloco)
        bloco.save(update_fields=["timestamps", "duracao", "caracteres_tts"])
        return "estimado"

    pedacos, timeline, deslocamento, total_chars = [], [], 0.0, 0
    for i, fala in enumerate(falas):
        p = personagens[fala["personagem"]]
        ssml = tts.montar_ssml(fala["frases"])
        total_chars += len(ssml)
        mp3, marcas = provedor.sintetizar(ssml, p.voz_nome, p.voz_velocidade, p.voz_tom)
        duracao = _duracao_mp3(mp3) or marcas.get("fim", 0) + 0.35
        fim_fala = marcas.get("fim", duracao)
        for j, frase in enumerate(fala["frases"]):
            inicio = marcas.get(f"f{j}", 0.0)
            fim = marcas.get(f"f{j + 1}", fim_fala)
            timeline.append({
                "fala": i, "frase": j, "personagem": fala["personagem"], "texto": texto_legenda(frase),
                "inicio": round(deslocamento + inicio, 2), "fim": round(deslocamento + fim, 2),
            })
        pedacos.append(mp3)
        deslocamento += duracao

    # MP3 é uma sequência de frames: concatenar os trechos gera um arquivo tocável.
    antigo = bloco.audio.name if bloco.audio else None
    caminho = f"audios/curso-{bloco.aula.modulo.curso_id}/bloco-{bloco.pk}-{novo_hash[:10]}.mp3"
    bloco.audio.name = storage.salvar(caminho, b"".join(pedacos))
    if antigo and antigo != bloco.audio.name:
        storage.remover(antigo)
    bloco.timestamps = timeline
    bloco.duracao = round(deslocamento, 2)
    bloco.hash_roteiro = novo_hash
    bloco.caracteres_tts = total_chars
    bloco.save(update_fields=["audio", "timestamps", "duracao", "hash_roteiro", "caracteres_tts"])
    log.info("Áudio gerado: bloco %s (%s caracteres)", bloco.pk, total_chars)
    return "gerado"


def estimativa(blocos, personagens=None):
    """Quantos caracteres seriam enviados ao TTS (só blocos desatualizados)."""
    pendentes = [b for b in blocos if b.tem_narracao and not b.audio_em_dia(personagens)]
    return {"blocos": len(pendentes), "caracteres": sum(caracteres_ssml(b) for b in pendentes)}
