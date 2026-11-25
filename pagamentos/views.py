from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from aprendizado import regras as apr
from core.models import AuditLog
from core.permissoes import criador_required
from cursos.models import Curso

from .gateways import ErroWebhook, confirmar_pagamento, gateway
from .models import Pedido


@login_required
@require_POST
def comprar(request, slug):
    curso = get_object_or_404(Curso, slug=slug, status=Curso.Status.PUBLICADO, modo_acesso=Curso.Acesso.PAGO)
    if apr.matricula_de(request.user, curso):
        return redirect("aprendizado:curso", slug)
    pedido = Pedido.objects.filter(aluno=request.user, curso=curso, status=Pedido.Status.PENDENTE).first()
    if pedido is None:
        gw = gateway()
        pedido = Pedido.objects.create(aluno=request.user, curso=curso, valor=curso.preco, gateway=gw.nome)
        AuditLog.registrar(request, "pedido_criado", pedido, f"Pedido de {curso.titulo}", valor=str(curso.preco))
        return redirect(gw.criar_cobranca(pedido, request))
    return redirect("pagamentos:pedido", pedido.pk)


@login_required
def pedido(request, pk):
    """Página de retorno. Não matricula ninguém: só o webhook confirmado faz isso (N7)."""
    p = get_object_or_404(Pedido.objects.select_related("curso"), pk=pk)
    if p.aluno_id != request.user.pk and not request.user.eh_criador:
        raise Http404
    return render(request, "pagamentos/pedido.html", {"p": p})


@csrf_exempt
@require_POST
def webhook(request, nome):
    try:
        p = gateway(nome).processar_webhook(request)
    except ErroWebhook as erro:
        return JsonResponse({"ok": False, "erro": str(erro)}, status=400)
    return JsonResponse({"ok": True, "pedido": p.pk, "status": p.status})


@criador_required
def painel(request):
    status = request.GET.get("status") or ""
    pedidos = Pedido.objects.select_related("aluno", "curso")
    if status:
        pedidos = pedidos.filter(status=status)
    receita = Pedido.objects.filter(status=Pedido.Status.PAGO).aggregate(t=Sum("valor"))["t"] or 0
    return render(request, "pagamentos/painel.html", {
        "pedidos": pedidos[:200], "status": status, "receita": receita, "Status": Pedido.Status,
        "pendentes": Pedido.objects.filter(status=Pedido.Status.PENDENTE).count(),
    })


@criador_required
@require_POST
def confirmar_manual(request, pk):
    """Provedor manual: o criador confirma o recebimento; passa pelo mesmo caminho do webhook."""
    p = get_object_or_404(Pedido, pk=pk, gateway="manual")
    acao = request.POST.get("acao")
    status = {"confirmar": "pago", "cancelar": "cancelado"}.get(acao)
    if not status:
        return redirect("pagamentos:painel")
    confirmar_pagamento(p.id_externo, status, {"origem": "painel", "por": request.user.email})
    AuditLog.registrar(request, f"pedido_{status}", p, f"Pedido {p.pk} marcado como {status} manualmente")
    messages.success(request, f"Pedido {p.pk}: {'pagamento confirmado e matrícula liberada' if status == 'pago' else 'cancelado'}.")
    return redirect("pagamentos:painel")
