from django.core.management.base import BaseCommand, CommandError

from cursos.models import Curso
from cursos.roteiro_io import exportar


class Command(BaseCommand):
    help = "Exporta um curso no formato de roteiro YAML (backup/reaproveitamento)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("-o", "--saida", help="Arquivo de saída (padrão: stdout)")

    def handle(self, slug, saida, **opts):
        curso = Curso.objects.filter(slug=slug).first()
        if curso is None:
            raise CommandError(f"Curso '{slug}' não existe")
        texto = exportar(curso)
        if saida:
            with open(saida, "w", encoding="utf-8") as f:
                f.write(texto)
            self.stdout.write(self.style.SUCCESS(f"Exportado para {saida}"))
        else:
            self.stdout.write(texto)
