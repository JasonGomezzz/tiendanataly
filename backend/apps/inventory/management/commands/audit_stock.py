from django.core.management.base import BaseCommand, CommandError

from apps.inventory.services import audit_stock


class Command(BaseCommand):
    help = "Verifica que el stock de cada variante coincida con el libro de movimientos."

    def handle(self, *args, **options):
        problems = audit_stock()
        if problems:
            for p in problems:
                self.stderr.write(p)
            raise CommandError(f"{len(problems)} variante(s) con discrepancias")
        self.stdout.write(self.style.SUCCESS("Stock consistente con los movimientos."))
