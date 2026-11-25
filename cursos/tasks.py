import logging

from celery import shared_task

from .audio import gerar_audio_bloco, personagens_do_curso
from .models import BlocoAula

log = logging.getLogger(__name__)


def _gerar_lote(blocos, forcar):
    resumo = {}
    personagens_cache = {}
    for bloco in blocos:
        curso_id = bloco.aula.modulo.curso_id
        if curso_id not in personagens_cache:
            personagens_cache[curso_id] = personagens_do_curso(bloco.aula.modulo.curso)
        try:
            r = gerar_audio_bloco(bloco, forcar=forcar, personagens=personagens_cache[curso_id])
        except Exception as erro:  # noqa: BLE001 — um bloco com erro não para os outros
            log.exception("Falha ao gerar áudio do bloco %s", bloco.pk)
            r = f"erro: {erro}"
        resumo[bloco.pk] = r
    return resumo


def _blocos(**filtro):
    return BlocoAula.objects.filter(**filtro).select_related("aula__modulo__curso").order_by(
        "aula__modulo__ordem", "aula__ordem", "ordem"
    )


@shared_task
def gerar_audio_bloco_task(bloco_id, forcar=False):
    return _gerar_lote(_blocos(pk=bloco_id), forcar)


@shared_task(time_limit=60 * 60, soft_time_limit=60 * 60 - 30)
def gerar_audios_aula_task(aula_id, forcar=False):
    return _gerar_lote(_blocos(aula_id=aula_id), forcar)


@shared_task
def gerar_audios_curso_task(curso_id, forcar=False):
    """Uma tarefa por aula: o curso inteiro não cabe no limite de tempo de uma tarefa só."""
    from .models import Aula

    ids = list(Aula.objects.filter(modulo__curso_id=curso_id).order_by("modulo__ordem", "ordem").values_list("id", flat=True))
    for aula_id in ids:
        gerar_audios_aula_task.delay(aula_id, forcar)
    return {"aulas": len(ids)}
