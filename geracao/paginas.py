"""Conversão entre listas de páginas e texto ("3-5, 9")."""
import re


def compactar(paginas):
    """[3, 4, 5, 9] -> '3-5, 9'"""
    nums = sorted({int(p) for p in paginas})
    if not nums:
        return ""
    partes = []
    ini = ant = nums[0]
    for n in nums[1:]:
        if n == ant + 1:
            ant = n
            continue
        partes.append(f"{ini}-{ant}" if ant > ini else str(ini))
        ini = ant = n
    partes.append(f"{ini}-{ant}" if ant > ini else str(ini))
    return ", ".join(partes)


class PaginasInvalidas(ValueError):
    pass


def expandir(texto, maximo=None):
    """'3-5, 9' -> [3, 4, 5, 9]. Lança PaginasInvalidas com mensagem clara."""
    paginas = set()
    for parte in re.split(r"[,;\s]+", (texto or "").strip()):
        if not parte:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", parte)
        if not m:
            raise PaginasInvalidas(f"'{parte}' não é uma página nem um intervalo (ex.: 3-5, 9)")
        ini = int(m.group(1))
        fim = int(m.group(2) or ini)
        if fim < ini:
            raise PaginasInvalidas(f"intervalo invertido: {parte}")
        if maximo and fim > maximo:
            raise PaginasInvalidas(f"página {fim} não existe (o material tem {maximo})")
        paginas.update(range(ini, fim + 1))
    return sorted(paginas)
