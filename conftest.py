from pathlib import Path

import pytest

from core.models import Usuario
from cursos.roteiro_io import importar, ler

PILOTO = Path(__file__).parent / "conteudo" / "ia-com-sabedoria-piloto.yaml"


@pytest.fixture
def criador(db):
    return Usuario.objects.create_user("criador@teste.local", "SenhaForte!2026", nome="Criador", papel="criador")


@pytest.fixture
def aluno(db):
    return Usuario.objects.create_user("aluno@teste.local", "SenhaForte!2026", nome="Aluno Teste")


@pytest.fixture
def dados_piloto():
    return ler(PILOTO.read_text(encoding="utf-8"))


@pytest.fixture
def curso_piloto(db, dados_piloto):
    return importar(dados_piloto)


class TTSFalso:
    """Provedor de TTS de teste: conta chamadas e devolve um MP3 mínimo."""

    nome = "falso"
    gera_audio = True

    def __init__(self):
        self.chamadas = 0

    def sintetizar(self, ssml, voz, velocidade=1.0, tom=0.0):
        self.chamadas += 1
        n = ssml.count("<mark name=\"f")
        marcas = {f"f{i}": i * 2.0 for i in range(n)}
        marcas["fim"] = n * 2.0
        return b"ID3" + b"\x00" * 64, marcas


@pytest.fixture
def tts_falso():
    return TTSFalso()
