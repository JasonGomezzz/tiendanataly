from django.core.management.base import BaseCommand

from apps.core.roles import setup_roles


class Command(BaseCommand):
    help = "Crea los grupos Administradora y Staff con sus permisos (idempotente)."

    def handle(self, *args, **options):
        setup_roles()
        self.stdout.write(self.style.SUCCESS("Roles listos: Administradora, Staff"))
