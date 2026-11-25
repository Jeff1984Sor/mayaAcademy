"""Settings comuns. Todo valor sensível vem do .env (R5)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env(nome, padrao=None):
    return os.environ.get(nome, padrao)


def env_bool(nome, padrao=False):
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


def env_list(nome, padrao=""):
    return [v.strip() for v in env(nome, padrao).split(",") if v.strip()]


SECRET_KEY = env("SECRET_KEY")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
SITE_URL = env("SITE_URL", "http://localhost")
# "hml" (homologação) ou "prod". Em hml aparece a faixa vermelha e nada sai para fora (e-mails reais, cobranças).
AMBIENTE = env("AMBIENTE", "prod")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "cursos",
    "estudio",
    "aprendizado",
    "catalogo",
    "geracao",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.contexto.shell",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "mayaacademy"),
        "USER": env("DB_USER", "mayaacademy"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "core.Usuario"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:inicio"
LOGOUT_REDIRECT_URL = "catalogo:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(env("STATIC_ROOT", BASE_DIR / "staticfiles"))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Upload de roteiro/PDF
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# Cache (usado também no rate limit de login)
CACHE_URL = env("CACHE_URL")
if CACHE_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": CACHE_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6380/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 15 * 60

# E-mail
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "MayaAcademy <nao-responda@localhost>")

# Serviços plugáveis
TTS_PROVIDER = env("TTS_PROVIDER", "nulo")
GOOGLE_TTS_API_KEY = env("GOOGLE_TTS_API_KEY", "")
# Custo do TTS para o relatório (US$ por 1 milhão de caracteres). REVISAR na tabela do provedor.
TTS_PRECO_1M_CARACTERES = float(env("TTS_PRECO_1M_CARACTERES", "16"))

# IA do gerador de curso por PDF (F2.5): "openai" ou "falso" (sem rede, para testes)
LLM_PROVIDER = env("LLM_PROVIDER", "openai")
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", "")
# Preço do modelo escolhido, em US$ por 1 milhão de tokens (só para o painel de custo). REVISAR.
LLM_PRECO_ENTRADA_1M = float(env("LLM_PRECO_ENTRADA_1M", "0"))
LLM_PRECO_SAIDA_1M = float(env("LLM_PRECO_SAIDA_1M", "0"))
PDF_LIMITE_PAGINAS = int(env("PDF_LIMITE_PAGINAS", "300"))

# Rate limit de login: tentativas por janela (segundos), por IP + e-mail
LOGIN_RATE_LIMIT = (5, 15 * 60)

# Logs em arquivo próprio com rotação
LOG_DIR = Path(env("LOG_DIR", BASE_DIR / "logs"))
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"padrao": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "padrao"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
