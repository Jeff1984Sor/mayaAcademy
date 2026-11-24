from django.core.management.base import BaseCommand, CommandError

from cursos.audio import estimativa
from cursos.models import BlocoAula, Curso
from cursos.tasks import _gerar_lote


class Command(BaseCommand):
    help = "Gera a narração de todos os blocos de um curso (só os que mudaram, a não ser com --forcar)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--forcar", action="store_true", help="Regera mesmo sem mudança no roteiro")
        parser.add_argument("--estimar", action="store_true", help="Só mostra quantos caracteres seriam enviados")

    def handle(self, slug, forcar, estimar, **opts):
        try:
            curso = Curso.objects.get(slug=slug)
        except Curso.DoesNotExist as erro:
            raise CommandError(f"Curso '{slug}' não existe") from erro
        blocos = list(
            BlocoAula.objects.filter(aula__modulo__curso=curso)
            .select_related("aula__modulo__curso")
            .order_by("aula__modulo__ordem", "aula__ordem", "ordem")
        )
        personagens = {p.slug: p for p in curso.personagens.all()}
        est = estimativa(blocos, personagens)
        self.stdout.write(f"{est['blocos']} bloco(s) desatualizado(s), ~{est['caracteres']} caracteres de SSML.")
        if estimar:
            return
        resumo = _gerar_lote(blocos, forcar)
        for bloco_id, r in resumo.items():
            self.stdout.write(f"  bloco {bloco_id}: {r}")
        self.stdout.write(self.style.SUCCESS("Concluído."))
