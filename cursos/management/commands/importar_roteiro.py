from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cursos.models import Curso
from cursos.roteiro_io import ErroLeitura, importar, ler, resumo, validar


class Command(BaseCommand):
    help = "Valida e importa um roteiro YAML/JSON (cria o curso como rascunho)."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")
        parser.add_argument("--curso", help="slug de um curso existente para importar só módulos")
        parser.add_argument("--validar", action="store_true", dest="so_validar", help="Só valida, não importa")

    def handle(self, arquivo, curso, so_validar, **opts):
        caminho = Path(arquivo)
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {arquivo}")
        destino = None
        if curso:
            destino = Curso.objects.filter(slug=curso).first()
            if destino is None:
                raise CommandError(f"Curso '{curso}' não existe")
        try:
            dados = ler(caminho.read_text(encoding="utf-8"))
        except ErroLeitura as erro:
            raise CommandError(str(erro)) from erro

        rel = validar(dados, destino)
        for a in rel.avisos:
            self.stdout.write(self.style.WARNING(f"aviso  linha {a['linha']}: {a['local']}: {a['mensagem']}"))
        if not rel.ok:
            for e in rel.erros:
                self.stdout.write(self.style.ERROR(f"erro   linha {e['linha']}: {e['local']}: {e['mensagem']}"))
            raise CommandError(f"{len(rel.erros)} erro(s); nada foi importado.")
        r = resumo(dados)
        self.stdout.write(f"Válido: {r['modulos']} módulo(s), {r['aulas']} aula(s), {r['blocos']} bloco(s), {r['questoes']} questão(ões).")
        if so_validar:
            return
        criado = importar(dados, destino)
        self.stdout.write(self.style.SUCCESS(f"Importado como rascunho: {criado.titulo} (slug: {criado.slug})"))
