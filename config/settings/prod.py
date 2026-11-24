"""Produção (único ambiente — R2). DEBUG nunca é ligado aqui."""
from .base import *  # noqa: F401,F403
from .base import LOG_DIR

from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY ausente no .env")
if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("ALLOWED_HOSTS ausente no .env")

# Segurança (atrás do Nginx com HTTPS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "SAMEORIGIN"  # o Estúdio pré-visualiza o player em iframe do mesmo domínio

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"padrao": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "app": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "padrao",
        },
        "celery": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "celery.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "padrao",
        },
    },
    "root": {"handlers": ["app"], "level": "INFO"},
    "loggers": {
        "celery": {"handlers": ["celery"], "level": "INFO", "propagate": False},
        "cursos.tasks": {"handlers": ["celery"], "level": "INFO", "propagate": False},
    },
}
