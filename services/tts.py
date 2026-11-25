"""Text-to-speech com provedor trocável.

Provedores:
- "google": Google Cloud Text-to-Speech (REST v1beta1, API key), SSML com
  <mark> antes de cada frase para obter o tempo exato de cada uma.
- "openai": OpenAI (audio/speech). Sem marcas SSML: cada frase é sintetizada à parte e
  o tempo dela é medido no próprio MP3, então a sincronia continua exata por frase.
- "nulo":   não gera áudio. O player usa legendas cronometradas por estimativa.

O provedor escolhido na tela (Estúdio › Configurar IA) vale mais que o TTS_PROVIDER do .env.

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


VOZES_OPENAI = ["marin", "cedar", "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"]
INSTRUCOES_VOZ = ("Fale em português do Brasil, com sotaque brasileiro natural, tom caloroso e didático, "
                  "como um professor conversando com o aluno. Ritmo tranquilo e pronúncia clara.")


def _frases_do_ssml(ssml):
    """Desfaz o SSML de montar_ssml: [(marca, texto puro)] na ordem, sem a marca 'fim'."""
    partes = re.split(r'<mark name="([^"]+)"/>', ssml)
    saida = []
    for i in range(1, len(partes), 2):
        marca, trecho = partes[i], partes[i + 1] if i + 1 < len(partes) else ""
        if marca == "fim":
            continue
        trecho = re.sub(r"<break[^>]*/>", " ", trecho)
        trecho = html.unescape(re.sub(r"<[^>]+>", "", trecho))
        saida.append((marca, " ".join(trecho.split())))
    return saida


def _duracao(mp3):
    import io

    from mutagen.mp3 import MP3

    try:
        return MP3(io.BytesIO(mp3)).info.length
    except Exception:  # noqa: BLE001
        return 0.0


class OpenAITTS(ProvedorTTS):
    nome = "openai"
    PAUSA_ENTRE_FRASES = 0.0

    def __init__(self, chave, modelo="gpt-4o-mini-tts", voz_narrador="cedar", voz_mascote="marin"):
        if not chave:
            raise ErroTTS("A chave da OpenAI não foi cadastrada. Vá em Estúdio › Configurar IA.")
        from openai import OpenAI

        self.cliente = OpenAI(api_key=chave, timeout=120, max_retries=3)
        self.modelo = modelo or "gpt-4o-mini-tts"
        self.voz_narrador = voz_narrador or "cedar"
        self.voz_mascote = voz_mascote or "marin"

    def voz_para(self, personagem):
        """A voz do personagem, se for uma voz da OpenAI; senão, a padrão do papel."""
        if personagem.voz_nome in VOZES_OPENAI:
            return personagem.voz_nome
        return self.voz_mascote if personagem.papel == "mascote" else self.voz_narrador

    def _uma(self, texto, voz, velocidade):
        import openai

        params = {"model": self.modelo, "voice": voz, "input": texto, "response_format": "mp3",
                  "speed": max(0.25, min(4.0, velocidade or 1.0))}
        if "tts-1" not in self.modelo:
            params["instructions"] = INSTRUCOES_VOZ
        try:
            return self.cliente.audio.speech.create(**params).read()
        except openai.AuthenticationError as erro:
            raise ErroTTS("A OpenAI recusou a chave. Confira em Estúdio › Configurar IA.") from erro
        except openai.NotFoundError as erro:
            raise ErroTTS(f"Modelo de voz '{self.modelo}' não disponível na sua conta.") from erro
        except openai.RateLimitError as erro:
            raise ErroTTS("Limite de uso da OpenAI atingido (saldo ou taxa).") from erro
        except openai.APIError as erro:
            raise ErroTTS(f"Erro da OpenAI no áudio: {erro}") from erro

    def sintetizar(self, ssml, voz, velocidade=1.0, tom=0.0):
        from concurrent.futures import ThreadPoolExecutor

        frases = _frases_do_ssml(ssml)
        with ThreadPoolExecutor(max_workers=4) as pool:
            audios = list(pool.map(lambda f: self._uma(f[1], voz, velocidade) if f[1] else b"", frases))
        marcas, pedacos, t = {}, [], 0.0
        for (marca, _), mp3 in zip(frases, audios):
            marcas[marca] = round(t, 3)
            if mp3:
                pedacos.append(mp3)
                t += _duracao(mp3)
        marcas["fim"] = round(t, 3)
        return b"".join(pedacos), marcas

    def amostra(self, voz, texto):
        return self._uma(texto, voz, 1.0)


def _config_tela():
    try:
        from geracao.models import ConfiguracaoIA

        return ConfiguracaoIA.atual()
    except Exception:  # noqa: BLE001 — banco indisponível (ex.: antes das migrations)
        return None


def _openai():
    from geracao.config_ia import atual

    c = _config_tela()
    return OpenAITTS(atual().chave, *( (c.tts_modelo, c.voz_narrador, c.voz_mascote) if c else ()))


PROVEDORES = {"google": lambda: GoogleTTS(settings.GOOGLE_TTS_API_KEY), "nulo": TTSNulo, "openai": _openai}


def nome_provedor():
    c = _config_tela()
    return (c.tts_provedor if c and c.tts_provedor else None) or settings.TTS_PROVIDER


def provedor():
    nome = nome_provedor()
    if nome not in PROVEDORES:
        raise ErroTTS(f"TTS_PROVIDER desconhecido: {nome}")
    return PROVEDORES[nome]()
