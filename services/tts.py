"""Text-to-speech com provedor trocável.

Provedores:
- "google": Google Cloud Text-to-Speech (REST v1beta1, API key), SSML com
  <mark> antes de cada frase para obter o tempo exato de cada uma.
- "nulo":   não gera áudio. O player usa legendas cronometradas por estimativa.

Para adicionar outro provedor, implemente `ProvedorTTS` e registre em PROVEDORES.
"""
import base64
import html
import logging
import re

import requests
from django.conf import settings

from cursos.roteiro import _RE_PAUSA

log = logging.getLogger(__name__)


class ErroTTS(Exception):
    pass


def frase_para_ssml(frase):
    texto = html.escape(frase, quote=False)
    texto = _RE_PAUSA.sub(lambda m: f'<break time="{int(m.group(1) or 500)}ms"/>', texto)
    texto = re.sub(r"\*([^*]+)\*", r'<emphasis level="moderate">\1</emphasis>', texto)
    return texto


def montar_ssml(frases, prefixo="f"):
    """Um <mark name="{prefixo}{i}"/> antes de cada frase e um 'fim' no final."""
    partes = [f'<mark name="{prefixo}{i}"/>{frase_para_ssml(f)}' for i, f in enumerate(frases)]
    return "<speak>" + " ".join(partes) + '<mark name="fim"/><break time="350ms"/></speak>'


class ProvedorTTS:
    nome = "base"
    gera_audio = True

    def sintetizar(self, ssml, voz, velocidade=1.0, tom=0.0):
        """Retorna (mp3: bytes, marcas: {nome: segundos})."""
        raise NotImplementedError


class GoogleTTS(ProvedorTTS):
    nome = "google"
    URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"

    def __init__(self, api_key):
        if not api_key:
            raise ErroTTS("GOOGLE_TTS_API_KEY não configurada no .env")
        self.api_key = api_key

    def sintetizar(self, ssml, voz, velocidade=1.0, tom=0.0):
        idioma = "-".join(voz.split("-")[:2]) if voz.count("-") >= 2 else "pt-BR"
        corpo = {
            "input": {"ssml": ssml},
            "voice": {"languageCode": idioma, "name": voz},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": velocidade, "pitch": tom},
            "enableTimePointing": ["SSML_MARK"],
        }
        try:
            resp = requests.post(self.URL, params={"key": self.api_key}, json=corpo, timeout=90)
        except requests.RequestException as erro:
            raise ErroTTS(f"Falha de rede no TTS: {erro}") from erro
        if resp.status_code != 200:
            raise ErroTTS(f"TTS respondeu {resp.status_code}: {resp.text[:300]}")
        dados = resp.json()
        marcas = {tp["markName"]: float(tp.get("timeSeconds", 0)) for tp in dados.get("timepoints", [])}
        return base64.b64decode(dados["audioContent"]), marcas


class TTSNulo(ProvedorTTS):
    nome = "nulo"
    gera_audio = False

    def sintetizar(self, ssml, voz, velocidade=1.0, tom=0.0):
        return None, {}


PROVEDORES = {"google": lambda: GoogleTTS(settings.GOOGLE_TTS_API_KEY), "nulo": TTSNulo}


def provedor():
    nome = settings.TTS_PROVIDER
    if nome not in PROVEDORES:
        raise ErroTTS(f"TTS_PROVIDER desconhecido: {nome}")
    return PROVEDORES[nome]()
