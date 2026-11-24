from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def criador_required(view):
    """Acesso ao Estúdio: criador ou superadmin."""

    @login_required
    @wraps(view)
    def _view(request, *args, **kwargs):
        if not request.user.eh_criador:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _view


def gestor_required(view):
    @login_required
    @wraps(view)
    def _view(request, *args, **kwargs):
        if not (request.user.eh_gestor or request.user.eh_criador):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _view
