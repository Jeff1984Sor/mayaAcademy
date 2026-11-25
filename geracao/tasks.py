from celery import shared_task

from . import pipeline


@shared_task(time_limit=2 * 60 * 60, soft_time_limit=2 * 60 * 60 - 60)
def preparar_geracao_task(geracao_id):
    """Extração, mapa e ementa (para na ementa, aguardando o criador)."""
    pipeline.preparar(geracao_id)


@shared_task(time_limit=45 * 60, soft_time_limit=45 * 60 - 30)
def gerar_aula_task(aula_gerada_id, instrucao_extra=""):
    pipeline.gerar_aula(aula_gerada_id, instrucao_extra)
