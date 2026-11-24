from django.core.management.base import BaseCommand, CommandError

from cursos.bundle import ErroBundle, gravar


class Command(BaseCommand):
    help = "Gera static/js/player.bundle.js a partir dos módulos do player (rodar antes do collectstatic)."

    def handle(self, **opts):
        try:
            destino = gravar()
        except ErroBundle as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write(self.style.SUCCESS(f"Player empacotado em {destino}"))
