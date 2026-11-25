"""Emissão do certificado (N5): automática na aprovação, com código único e QR code de validação."""
import io
import secrets

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from .models import Certificado

# Sem 0/O/1/I para não confundir quem digita o código.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def novo_codigo():
    while True:
        bruto = "".join(secrets.choice(_ALFABETO) for _ in range(10))
        codigo = f"MA-{bruto[:5]}-{bruto[5:]}"
        if not Certificado.objects.filter(codigo=codigo).exists():
            return codigo


def url_validacao(codigo):
    return settings.SITE_URL.rstrip("/") + reverse("certificados:validar", args=[codigo])


def emitir(matricula, nota, manual=False):
    """Cria o certificado (uma vez por matrícula) e agenda o PDF."""
    existente = Certificado.objects.filter(matricula=matricula).first()
    if existente:
        return existente
    curso = matricula.curso
    cert = Certificado.objects.create(
        matricula=matricula, codigo=novo_codigo(), nome_aluno=matricula.aluno.nome or matricula.aluno.email,
        titulo_curso=curso.titulo, carga_horaria=curso.carga_horaria, nota=nota,
        versao_curso=matricula.versao_curso, manual=manual,
    )
    from .tasks import gerar_pdf_certificado_task

    transaction.on_commit(lambda: gerar_pdf_certificado_task.delay(cert.pk))
    return cert


def _qr_png(texto):
    import segno

    buf = io.BytesIO()
    segno.make(texto, error="m").save(buf, kind="png", scale=8, border=2, dark="#1E2D6B")
    return buf.getvalue()


def montar_pdf(cert):
    """Certificado A4 paisagem nas cores MayaCorp (PyMuPDF)."""
    import pymupdf

    doc = pymupdf.open()
    pg = doc.new_page(width=842, height=595)
    navy, amber, indigo = (0.118, 0.176, 0.42), (0.961, 0.651, 0.137), (0.486, 0.561, 1.0)
    pg.draw_rect(pg.rect, color=None, fill=(0.969, 0.973, 0.988))
    pg.draw_rect(pymupdf.Rect(0, 0, 842, 18), color=None, fill=navy)
    pg.draw_rect(pymupdf.Rect(0, 577, 842, 595), color=None, fill=navy)
    pg.draw_rect(pymupdf.Rect(0, 18, 842, 24), color=None, fill=amber)
    pg.draw_rect(pymupdf.Rect(30, 48, 812, 547), color=indigo, width=1.2)

    emitido = timezone.localtime(cert.emitido_em).strftime("%d/%m/%Y")
    nota = f"{cert.nota:.0f}".replace(".", ",")
    html = f"""
    <div class="marca">MayaAcademy</div>
    <h1>CERTIFICADO DE CONCLUSÃO</h1>
    <p class="intro">Certificamos que</p>
    <p class="nome">{escape(cert.nome_aluno)}</p>
    <p class="texto">concluiu o curso <b>{escape(cert.titulo_curso)}</b>, com carga horária de
    <b>{cert.carga_horaria} hora(s)</b>, e foi aprovado(a) na avaliação final com nota <b>{nota}%</b>.</p>
    <p class="data">Emitido em {emitido} · versão {cert.versao_curso} do curso</p>
    """
    css = """
    * { font-family: sans-serif; color: #0F1729; text-align: center; }
    .marca { color: #7C8FFF; font-weight: bold; font-size: 15px; letter-spacing: 2px; }
    h1 { color: #1E2D6B; font-size: 30px; margin: 14px 0 22px 0; letter-spacing: 3px; }
    .intro { font-size: 15px; margin: 0; }
    .nome { color: #1E2D6B; font-size: 34px; font-weight: bold; margin: 10px 0 14px 0; }
    .texto { font-size: 15px; line-height: 1.5; margin: 0 40px; }
    .data { font-size: 12px; color: #555; margin-top: 18px; }
    """
    pg.insert_htmlbox(pymupdf.Rect(70, 70, 772, 440), html, css=css)

    url = url_validacao(cert.codigo)
    pg.insert_image(pymupdf.Rect(70, 440, 160, 530), stream=_qr_png(url))
    rodape = f"""<p>Código de validação: <b>{escape(cert.codigo)}</b><br>Confira em {escape(url)}</p>"""
    pg.insert_htmlbox(pymupdf.Rect(170, 465, 600, 530), rodape,
                      css="* { font-family: sans-serif; font-size: 11px; color: #0F1729; text-align: left; }")
    pg.insert_htmlbox(pymupdf.Rect(600, 470, 772, 530), "<p><b>MayaCorp</b><br>Plataforma MayaAcademy</p>",
                      css="* { font-family: sans-serif; font-size: 12px; color: #1E2D6B; text-align: right; }")
    dados = doc.tobytes(deflate=True)
    doc.close()
    return dados


def gerar_pdf(cert):
    dados = montar_pdf(cert)
    if cert.pdf:
        cert.pdf.delete(save=False)
    cert.pdf.save(f"{cert.codigo}.pdf", ContentFile(dados), save=True)
    return cert
