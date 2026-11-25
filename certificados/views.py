from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Certificado
from .regras import gerar_pdf


def validar(request, codigo=None):
    """Validação pública: /certificado/<codigo>/ (ou busca pelo formulário)."""
    codigo = (codigo or request.GET.get("codigo") or "").strip().upper()
    if not codigo:
        return render(request, "certificados/validar.html", {})
    if request.GET.get("codigo"):
        return redirect("certificados:validar", codigo)
    cert = Certificado.objects.filter(codigo=codigo).select_related("matricula").first()
    return render(request, "certificados/validar.html", {"codigo": codigo, "cert": cert}, status=200 if cert else 404)


def baixar(request, codigo):
    cert = get_object_or_404(Certificado, codigo=codigo.upper())
    if not cert.pdf:
        gerar_pdf(cert)  # o PDF ainda não ficou pronto na fila: gera na hora
    try:
        arquivo = cert.pdf.open("rb")
    except FileNotFoundError as erro:
        raise Http404 from erro
    return FileResponse(arquivo, content_type="application/pdf", filename=f"certificado-{cert.codigo}.pdf")


@login_required
def meus(request):
    certs = Certificado.objects.filter(matricula__aluno=request.user).select_related("matricula__curso")
    return render(request, "certificados/meus.html", {"certificados": certs})
