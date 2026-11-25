"""Usado só pelo pytest (no servidor). Banco SQLite em memória, nada de produção é tocado."""
from .base import *  # noqa: F401,F403

SECRET_KEY = "chave-apenas-para-testes"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
TTS_PROVIDER = "nulo"
LLM_PROVIDER = "falso"
LLM_PRECO_ENTRADA_1M = 2.0
LLM_PRECO_SAIDA_1M = 8.0
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PAGAMENTOS_WEBHOOK_SEGREDO = "segredo-de-teste"
SITE_URL = "https://academy.teste"
