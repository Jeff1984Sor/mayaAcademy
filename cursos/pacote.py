"""Pacote do curso para download: HTML5 autônomo + SCORM 1.2.

O mesmo .zip serve para:
- abrir direto no computador (index.html, funciona em file://);
- hospedar em qualquer site estático;
- subir em LMS que aceitam SCORM 1.2 (Moodle, LearnWorlds, TalentLMS, etc.).

Conteúdo: index.html, imsmanifest.xml, player/ (JS, CSS, GSAP, Lottie),
dados/curso.js (todas as aulas) e audio/*.mp3.
"""
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from . import bundle
from .player import dados_aula

ESTATICOS = Path(settings.BASE_DIR) / "static"


def _dados_curso(curso):
    personagens = {p.slug: p for p in curso.personagens.all()}
    modulos = curso.modulos.prefetch_related("aulas__blocos").order_by("ordem")
    audios = {}
    saida = []
    for m in modulos:
        aulas = []
        for a in m.aulas.all():
            dados = dados_aula(a, list(a.blocos.all()), personagens)
            for b_dados, b in zip(dados["blocos"], a.blocos.all()):
                if b_dados["audio"] and b.audio:
                    destino = f"audio/bloco-{b.pk}.mp3"
                    audios[destino] = b.audio.name
                    b_dados["audio"] = destino
            aulas.append(dados)
        saida.append({"titulo": m.titulo, "aulas": aulas})
    return {
        "curso": {
            "titulo": curso.titulo, "slug": curso.slug, "subtitulo": curso.subtitulo, "versao": curso.versao,
            "carga_horaria": curso.carga_horaria, "cor_primaria": curso.cor_primaria, "cor_secundaria": curso.cor_secundaria,
        },
        "modulos": saida,
    }, audios


def _manifesto(curso, arquivos):
    ident = f"mayaacademy-{curso.slug}-v{curso.versao}"
    titulo = escape(curso.titulo)
    lista = "\n".join(f'      <file href="{escape(a)}"/>' for a in sorted(arquivos))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="{ident}" version="1.0"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata>
  <organizations default="org1">
    <organization identifier="org1">
      <title>{titulo}</title>
      <item identifier="item1" identifierref="res1">
        <title>{titulo}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="res1" type="webcontent" adlcp:scormtype="sco" href="index.html">
{lista}
    </resource>
  </resources>
</manifest>
"""


def _index(curso):
    titulo = escape(curso.titulo)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{titulo}</title>
<link rel="stylesheet" href="player/fontes.css">
<link rel="stylesheet" href="player/player.css">
<link rel="stylesheet" href="player/pacote.css">
</head>
<body>
<div id="app"></div>
<noscript>Este curso precisa de JavaScript habilitado.</noscript>
<script src="player/gsap.min.js"></script>
<script src="player/lottie_light.min.js"></script>
<script src="dados/curso.js"></script>
<script src="player/player.bundle.js"></script>
<script src="player/pacote.js"></script>
</body>
</html>
"""


def gerar_zip(curso) -> bytes:
    dados, audios = _dados_curso(curso)
    buffer = io.BytesIO()
    arquivos = {}
    arquivos["index.html"] = _index(curso).encode("utf-8")
    arquivos["dados/curso.js"] = ("window.MAYA_CURSO = " + json.dumps(dados, ensure_ascii=False) + ";\n").encode("utf-8")
    arquivos["player/player.bundle.js"] = bundle.montar().encode("utf-8")
    for origem, destino in [
        ("css/fontes.css", "player/fontes.css"),
        ("css/player.css", "player/player.css"),
        ("fonts/dm-sans-latin.woff2", "fonts/dm-sans-latin.woff2"),
        ("fonts/dm-sans-latin-ext.woff2", "fonts/dm-sans-latin-ext.woff2"),
        ("fonts/jetbrains-mono-latin.woff2", "fonts/jetbrains-mono-latin.woff2"),
        ("fonts/LICENSE-DM-Sans.txt", "fonts/LICENSE-DM-Sans.txt"),
        ("fonts/LICENSE-JetBrains-Mono.txt", "fonts/LICENSE-JetBrains-Mono.txt"),
        ("css/pacote.css", "player/pacote.css"),
        ("js/pacote/pacote.js", "player/pacote.js"),
        ("vendor/gsap.min.js", "player/gsap.min.js"),
        ("vendor/lottie_light.min.js", "player/lottie_light.min.js"),
    ]:
        arquivos[destino] = (ESTATICOS / origem).read_bytes()
    for destino, nome in audios.items():
        with default_storage.open(nome, "rb") as f:
            arquivos[destino] = f.read()
    arquivos["imsmanifest.xml"] = _manifesto(curso, list(arquivos)).encode("utf-8")
    arquivos["LEIA-ME.txt"] = (
        f"{curso.titulo} — versão {curso.versao}\n"
        f"Gerado pela MayaAcademy em {timezone.localtime():%d/%m/%Y %H:%M}.\n\n"
        "- Para abrir no computador: descompacte e abra index.html no navegador.\n"
        "- Para um LMS (Moodle, LearnWorlds, TalentLMS...): envie este .zip como pacote SCORM 1.2.\n"
        "- Para um site: publique a pasta descompactada em qualquer hospedagem estática.\n"
    ).encode("utf-8")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            # MP3 já é comprimido: guardar sem recomprimir é mais rápido.
            tipo = zipfile.ZIP_STORED if nome.endswith(".mp3") else zipfile.ZIP_DEFLATED
            z.writestr(nome, conteudo, compress_type=tipo)
    return buffer.getvalue()
