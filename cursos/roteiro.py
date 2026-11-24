"""Parser do roteiro de narração.

Formato (uma fala por linha):

    @maya: Oi! Hoje a gente vai falar de alucinação.
    @narrador: Alucinação é quando a IA inventa algo com toda a confiança.
    Isso continua a fala do narrador.

- `@slug:` troca o personagem; linhas sem prefixo continuam o último personagem.
- Sem nenhum prefixo, a fala é do personagem com slug `narrador`.
- Linhas em branco separam falas do mesmo personagem.
- `[pausa]` ou `[pausa 800ms]` vira uma pausa no áudio.
- `*palavra*` vira ênfase no áudio (e itálico na legenda).
"""
import re

PERSONAGEM_PADRAO = "narrador"
_RE_PREFIXO = re.compile(r"^@([a-z0-9_-]+)\s*:\s*(.*)$", re.IGNORECASE)
_RE_FRASE = re.compile(r"(?<=[.!?…])\s+(?=\S)")
_RE_PAUSA = re.compile(r"\[pausa(?:\s+(\d+)\s*ms)?\]", re.IGNORECASE)


def parse_roteiro(texto):
    """Retorna [{"personagem": slug, "frases": [str, ...]}]."""
    falas = []
    atual = None
    personagem = PERSONAGEM_PADRAO
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha:
            atual = None
            continue
        m = _RE_PREFIXO.match(linha)
        if m:
            personagem = m.group(1).lower()
            linha = m.group(2).strip()
            atual = None
            if not linha:
                continue
        if atual is None:
            atual = {"personagem": personagem, "texto": ""}
            falas.append(atual)
        atual["texto"] = f"{atual['texto']} {linha}".strip()
    return [{"personagem": f["personagem"], "frases": dividir_frases(f["texto"])} for f in falas if f["texto"]]


def dividir_frases(texto):
    return [f.strip() for f in _RE_FRASE.split(texto.strip()) if f.strip()]


def texto_legenda(frase):
    """Frase como aparece na legenda: sem marcações de pausa."""
    return re.sub(r"\s{2,}", " ", _RE_PAUSA.sub("", frase)).strip()


def personagens_usados(texto):
    return sorted({f["personagem"] for f in parse_roteiro(texto)})


def estimar_duracao(frase, velocidade=1.0):
    """Estimativa (s) usada quando não há áudio: ~14 caracteres/s em pt-BR."""
    pausas = sum(int(m.group(1) or 500) for m in _RE_PAUSA.finditer(frase)) / 1000
    return max(1.2, len(texto_legenda(frase)) / (14.0 * max(velocidade, 0.25))) + pausas


def timestamps_estimados(falas, velocidades=None):
    """Timeline sem áudio, no mesmo formato da gerada pelo TTS."""
    velocidades = velocidades or {}
    t = 0.0
    saida = []
    for i, fala in enumerate(falas):
        for j, frase in enumerate(fala["frases"]):
            d = estimar_duracao(frase, velocidades.get(fala["personagem"], 1.0))
            saida.append({
                "fala": i, "frase": j, "personagem": fala["personagem"],
                "texto": texto_legenda(frase), "inicio": round(t, 2), "fim": round(t + d, 2),
            })
            t += d
        t += 0.35
    return saida
