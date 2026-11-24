"""Camada de armazenamento de mídia.

Hoje usa o storage padrão do Django (MEDIA_ROOT no servidor). Para migrar
para um bucket depois, troque o backend em STORAGES["default"] no settings;
o resto do código só chama estas funções.
"""
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def salvar(caminho, conteudo: bytes) -> str:
    if default_storage.exists(caminho):
        default_storage.delete(caminho)
    return default_storage.save(caminho, ContentFile(conteudo))


def remover(caminho):
    if caminho and default_storage.exists(caminho):
        default_storage.delete(caminho)


def url(caminho):
    return default_storage.url(caminho) if caminho else ""
