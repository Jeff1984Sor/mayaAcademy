"""Provedor de IA (LLM) isolado e trocável (seção 8.4).

Interface única: `gerar_json(mensagens, schema, nome, contexto=None) -> RespostaLLM`.
`mensagens` é a lista no formato de chat ({"role": "system"|"user"|"assistant", "content": str}).
A saída é sempre JSON validado contra `schema` (saída estruturada estrita do provedor).

Provedores:
- "openai": API da OpenAI (Chat Completions com response_format json_schema estrito).
  Modelo em OPENAI_MODEL; preço por 1 milhão de tokens em LLM_PRECO_ENTRADA_1M / LLM_PRECO_SAIDA_1M (US$).
- "falso": respostas determinísticas sem rede (testes e demonstração local), em geracao/falso.py.
"""
import json
import time
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings


class ErroLLM(Exception):
    pass


@dataclass
class RespostaLLM:
    dados: dict
    tokens_entrada: int
    tokens_saida: int
    modelo: str
    duracao_s: float

    @property
    def custo_usd(self):
        return custo_usd(self.tokens_entrada, self.tokens_saida)


def custo_usd(tokens_entrada, tokens_saida):
    entrada = Decimal(str(settings.LLM_PRECO_ENTRADA_1M)) * tokens_entrada / 1_000_000
    saida = Decimal(str(settings.LLM_PRECO_SAIDA_1M)) * tokens_saida / 1_000_000
    return (entrada + saida).quantize(Decimal("0.0001"))


class OpenAILLM:
    nome = "openai"

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ErroLLM("OPENAI_API_KEY não configurada no .env do servidor.")
        if not settings.OPENAI_MODEL:
            raise ErroLLM("OPENAI_MODEL não configurado no .env do servidor.")
        from openai import OpenAI

        self.modelo = settings.OPENAI_MODEL
        self.cliente = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=900, max_retries=3)

    def gerar_json(self, mensagens, schema, nome, contexto=None):
        import openai

        inicio = time.monotonic()
        try:
            resposta = self.cliente.chat.completions.create(
                model=self.modelo,
                messages=mensagens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": nome, "strict": True, "schema": schema},
                },
            )
        except openai.AuthenticationError as erro:
            raise ErroLLM("Chave da OpenAI inválida (OPENAI_API_KEY).") from erro
        except openai.NotFoundError as erro:
            raise ErroLLM(f"Modelo '{self.modelo}' não encontrado na sua conta OpenAI (OPENAI_MODEL).") from erro
        except openai.RateLimitError as erro:
            raise ErroLLM("Limite de uso da OpenAI atingido (saldo ou taxa). Tente de novo mais tarde.") from erro
        except openai.BadRequestError as erro:
            raise ErroLLM(f"A OpenAI recusou a requisição: {erro.message}") from erro
        except openai.APIConnectionError as erro:
            raise ErroLLM("Sem conexão com a OpenAI.") from erro
        except openai.APIStatusError as erro:
            raise ErroLLM(f"Erro da OpenAI (HTTP {erro.status_code}).") from erro

        escolha = resposta.choices[0]
        uso = resposta.usage
        entrada = getattr(uso, "prompt_tokens", 0) or 0
        saida = getattr(uso, "completion_tokens", 0) or 0
        if getattr(escolha.message, "refusal", None):
            raise ErroLLMComUso(f"A IA recusou: {escolha.message.refusal}", entrada, saida, self.modelo)
        if escolha.finish_reason == "length":
            raise ErroLLMComUso("A resposta da IA foi cortada (limite de tamanho).", entrada, saida, self.modelo)
        try:
            dados = json.loads(escolha.message.content or "")
        except json.JSONDecodeError as erro:
            raise ErroLLMComUso("A IA devolveu um JSON inválido.", entrada, saida, self.modelo) from erro
        return RespostaLLM(dados, entrada, saida, resposta.model or self.modelo, time.monotonic() - inicio)


class ErroLLMComUso(ErroLLM):
    """Falha depois que a chamada foi cobrada: guarda os tokens para o painel de custo."""

    def __init__(self, mensagem, tokens_entrada, tokens_saida, modelo):
        super().__init__(mensagem)
        self.tokens_entrada = tokens_entrada
        self.tokens_saida = tokens_saida
        self.modelo = modelo


def _falso():
    from geracao.falso import LLMFalso

    return LLMFalso()


PROVEDORES = {"openai": OpenAILLM, "falso": _falso}


def provedor():
    nome = settings.LLM_PROVIDER
    if nome not in PROVEDORES:
        raise ErroLLM(f"LLM_PROVIDER desconhecido: {nome} (use: {', '.join(PROVEDORES)})")
    return PROVEDORES[nome]()
