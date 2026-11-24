from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    # Catálogo completo entra na F4. Por ora: página "em construção" (Gate 1).
    return render(request, "catalogo/em_construcao.html")


def saude(request):
    """Health check simples para monitoramento e para o Gate 1."""
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        banco = "ok"
    except Exception:  # noqa: BLE001
        banco = "erro"
    return JsonResponse({"app": "ok", "banco": banco}, status=200 if banco == "ok" else 503)
