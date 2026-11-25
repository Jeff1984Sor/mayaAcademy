from celery import shared_task

from .models import Certificado
from .regras import gerar_pdf


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=10)
def gerar_pdf_certificado_task(certificado_id):
    gerar_pdf(Certificado.objects.get(pk=certificado_id))
