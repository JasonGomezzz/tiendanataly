import io

import qrcode
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

BACKUP_CODES = 8


class Command(BaseCommand):
    help = (
        "Activa el 2FA TOTP de una usuaria del panel: crea el dispositivo, muestra el QR para su app de "
        "autenticación y genera códigos de respaldo. Con --reset reemplaza el dispositivo anterior."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Correo/usuario de la cuenta (el mismo con el que inicia sesión)")
        parser.add_argument("--reset", action="store_true", help="Reemplaza el 2FA existente (p. ej. si perdió el celular)")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"].strip().lower())
        except User.DoesNotExist:
            raise CommandError("No existe esa usuaria.")
        if not user.is_staff:
            raise CommandError("Solo las cuentas del panel (is_staff) usan 2FA.")

        existing = TOTPDevice.objects.filter(user=user)
        if existing.exists() and not options["reset"]:
            raise CommandError("Ya tiene 2FA. Usa --reset para reemplazarlo.")
        existing.delete()
        StaticDevice.objects.filter(user=user).delete()

        device = TOTPDevice.objects.create(user=user, name="Celular", confirmed=True)
        backup = StaticDevice.objects.create(user=user, name="Códigos de respaldo", confirmed=True)
        codes = [StaticToken.random_token() for _ in range(BACKUP_CODES)]
        StaticToken.objects.bulk_create([StaticToken(device=backup, token=c) for c in codes])

        url = device.config_url
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        buf = io.StringIO()
        qr.print_ascii(out=buf, invert=True)

        self.stdout.write(self.style.SUCCESS(f"2FA activado para {user.username}"))
        self.stdout.write("\nEscanea este QR con Google Authenticator, Authy o similar:\n")
        self.stdout.write(buf.getvalue())
        self.stdout.write(f"\nSi no puede escanear, la clave manual es: {url.split('secret=')[1].split('&')[0]}")
        self.stdout.write("\nCódigos de respaldo (cada uno sirve una sola vez; guárdalos en un lugar seguro):")
        for c in codes:
            self.stdout.write(f"  {c}")
