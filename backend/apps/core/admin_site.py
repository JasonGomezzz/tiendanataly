from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django_otp.admin import OTPAdminAuthenticationForm


class TiendaAdminSite(AdminSite):
    """Admin con 2FA TOTP obligatorio cuando ADMIN_REQUIRE_2FA está activo.

    El dispositivo TOTP lo registra el superusuario técnico desde el propio admin
    (Dispositivos TOTP) y le entrega el QR a la persona usuaria.
    """

    site_header = "Administración de la tienda"
    site_title = "Tienda"
    index_title = "Panel"

    def __init__(self, name="admin"):
        super().__init__(name)

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if settings.ADMIN_REQUIRE_2FA:
            return request.user.is_verified()
        return True

    def login(self, request, extra_context=None):
        if settings.ADMIN_REQUIRE_2FA:
            self.login_form = OTPAdminAuthenticationForm
            self.login_template = "otp/admin/login.html"
        else:
            self.login_form = AdminAuthenticationForm
            self.login_template = None
        return super().login(request, extra_context)
