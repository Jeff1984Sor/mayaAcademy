"""Context processor do shell (menu lateral no padrão MayaCorp)."""
from django.conf import settings
from django.urls import reverse

# Itens com "em_breve" aparecem desabilitados até a fase correspondente.
NAV = [
    {
        "titulo": "Estúdio",
        "criador": True,
        "itens": [
            {"rotulo": "Cursos", "icone": "📚", "url": "estudio:painel", "prefixo": "/estudio/"},
            {"rotulo": "Importar roteiro", "icone": "⬆", "url": "estudio:importar", "prefixo": "/estudio/importar/"},
            {"rotulo": "Curso a partir de PDF", "icone": "📄", "url": "geracao:lista", "prefixo": "/estudio/pdf/"},
            {"rotulo": "Relatórios", "icone": "📊", "url": "estudio:relatorios", "prefixo": "/estudio/relatorios/"},
        ],
    },
    {
        "titulo": "Aprendizado",
        "itens": [
            {"rotulo": "Meus cursos", "icone": "🎓", "url": "aprendizado:meus_cursos", "prefixo": "/aprender/"},
            {"rotulo": "Certificados", "icone": "🏅", "url": "certificados:meus", "prefixo": "/certificado/"},
            {"rotulo": "XP e medalhas", "icone": "⭐", "url": "aprendizado:perfil", "prefixo": "/aprender/perfil/"},
            {"rotulo": "Catálogo", "icone": "🔎", "url": "catalogo:home", "prefixo": "/curso/"},
        ],
    },
    {
        "titulo": "Minha organização",
        "gestor": True,
        "itens": [
            {"rotulo": "Painel do gestor", "icone": "🏢", "url": "organizacoes:painel", "prefixo": "/organizacao/painel/"},
        ],
    },
    {
        "titulo": "Gestão",
        "criador": True,
        "itens": [
            {"rotulo": "Organizações", "icone": "🏢", "url": "organizacoes:lista", "prefixo": "/organizacao/"},
            {"rotulo": "Pagamentos", "icone": "💳", "url": "pagamentos:painel", "prefixo": "/pagamentos/"},
            {"rotulo": "Administração", "icone": "⚙", "url": "admin:index", "prefixo": "/admin/", "superuser": True},
        ],
    },
]


def shell(request):
    usuario = getattr(request, "user", None)
    grupos = []
    if usuario is not None and usuario.is_authenticated:
        caminho = request.path
        for g in NAV:
            if g.get("criador") and not usuario.eh_criador:
                continue
            if g.get("gestor") and not (usuario.eh_gestor and not usuario.eh_criador):
                continue
            itens = []
            for i in g["itens"]:
                if i.get("superuser") and not usuario.is_superuser:
                    continue
                item = dict(i)
                item["href"] = reverse(i["url"]) if i.get("url") else ""
                itens.append(item)
            # o item ativo é o de prefixo mais longo que casa com a URL atual
            candidatos = [i for i in itens if i.get("prefixo") and caminho.startswith(i["prefixo"])]
            if candidatos:
                max(candidatos, key=lambda i: len(i["prefixo"]))["ativo"] = True
            if itens:
                grupos.append({"titulo": g["titulo"], "itens": itens})
    return {
        "AMBIENTE": settings.AMBIENTE,
        "EH_HML": settings.AMBIENTE == "hml",
        "nav_grupos": grupos,
    }
