"""Configuração efetiva da IA: o que foi salvo na tela vale mais que o .env."""
import base64
import hashlib
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

# Sugestões de preço (US$ por 1M tokens) por linha de modelo, conferidas em 25/11/2026 em agregadores.
# São só atalhos na tela: o criador confirma na página oficial de preços da OpenAI.
SUGESTOES_PRECO = [
    {"linha": "luna", "rotulo": "Luna (mais barato)", "entrada": "0.10", "saida": "0.50"},
    {"linha": "terra", "rotulo": "Terra (econômico)", "entrada": "1", "saida": "5"},
    {"linha": "sol", "rotulo": "Sol (recomendado)", "entrada": "2", "saida": "10"},
    {"linha": "astra", "rotulo": "Astra (topo de linha)", "entrada": "8", "saida": "40"},
]

# Modelos que não servem para gerar texto estruturado.
_FORA = ("audio", "realtime", "image", "tts", "transcribe", "whisper", "embedding", "moderation", "search", "dall-e", "sora", "computer")


def _fernet():
    from cryptography.fernet import Fernet

    chave = base64.urlsafe_b64encode(hashlib.sha256(("mayaacademy-ia:" + settings.SECRET_KEY).encode()).digest())
    return Fernet(chave)


def cifrar(texto):
    return _fernet().encrypt(texto.encode()).decode() if texto else ""


def decifrar(texto):
    if not texto:
        return ""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(texto.encode()).decode()
    except InvalidToken:
        return ""  # SECRET_KEY mudou: a chave precisa ser cadastrada de novo


def mascarar(chave):
    return f"{chave[:6]}…{chave[-4:]}" if len(chave) > 12 else ("••••" if chave else "")


@dataclass
class ConfigIA:
    chave: str
    modelo: str
    preco_entrada_1m: Decimal
    preco_saida_1m: Decimal
    origem: str  # "tela" ou ".env"

    @property
    def completa(self):
        return bool(self.chave and self.modelo)


def atual():
    from .models import ConfiguracaoIA

    salvo = ConfiguracaoIA.atual()
    chave_tela = decifrar(salvo.chave_cifrada) if salvo else ""
    if salvo and (chave_tela or salvo.modelo):
        return ConfigIA(
            chave=chave_tela or settings.OPENAI_API_KEY,
            modelo=salvo.modelo or settings.OPENAI_MODEL,
            preco_entrada_1m=salvo.preco_entrada_1m,
            preco_saida_1m=salvo.preco_saida_1m,
            origem="tela",
        )
    return ConfigIA(
        chave=settings.OPENAI_API_KEY, modelo=settings.OPENAI_MODEL,
        preco_entrada_1m=Decimal(str(settings.LLM_PRECO_ENTRADA_1M)),
        preco_saida_1m=Decimal(str(settings.LLM_PRECO_SAIDA_1M)), origem=".env",
    )


def sugestao_para(modelo):
    nome = (modelo or "").lower()
    return next((s for s in SUGESTOES_PRECO if s["linha"] in nome), None)


def listar_modelos(chave):
    """IDs de modelos de texto disponíveis na conta (para o seletor da tela)."""
    from openai import OpenAI

    ids = [m.id for m in OpenAI(api_key=chave, timeout=30, max_retries=1).models.list().data]
    uteis = [i for i in ids if not any(p in i.lower() for p in _FORA)]
    return sorted(uteis, key=lambda i: (sugestao_para(i) is None, i))
