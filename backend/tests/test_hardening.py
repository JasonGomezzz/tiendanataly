from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from tests.factories import PASSWORD

pytestmark = pytest.mark.django_db


def enroll(username, *extra):
    out = StringIO()
    call_command("enroll_2fa", username, *extra, stdout=out)
    return out.getvalue()


def login(api, email, token):
    return api.post("/api/v1/auth/login/", {"email": email, "password": PASSWORD, "otp_token": token}, format="json")


def totp_now(user):
    d = TOTPDevice.objects.get(user=user)
    return str(TOTP(d.bin_key, d.step, d.t0, d.digits, d.drift).token()).zfill(d.digits)


def test_enroll_crea_totp_y_codigos_de_respaldo(admin_role):
    output = enroll(admin_role.username)
    assert "2FA activado" in output and "clave manual" in output
    assert TOTPDevice.objects.filter(user=admin_role, confirmed=True).count() == 1
    assert StaticDevice.objects.get(user=admin_role).token_set.count() == 8


def test_no_se_puede_enrolar_dos_veces_sin_reset(admin_role):
    enroll(admin_role.username)
    with pytest.raises(CommandError, match="--reset"):
        enroll(admin_role.username)
    old = TOTPDevice.objects.get(user=admin_role).pk
    enroll(admin_role.username, "--reset")
    assert TOTPDevice.objects.get(user=admin_role).pk != old


def test_las_clientas_no_pueden_enrolar_2fa(customer_user):
    with pytest.raises(CommandError, match="is_staff"):
        enroll(customer_user.username)


def test_login_con_el_codigo_del_celular(api, admin_role):
    enroll(admin_role.username)
    assert login(api, admin_role.email, totp_now(admin_role)).status_code == 200


def test_un_codigo_de_respaldo_sirve_una_sola_vez(api, admin_role):
    enroll(admin_role.username)
    code = StaticDevice.objects.get(user=admin_role).token_set.first().token
    assert login(api, admin_role.email, code).status_code == 200
    api.post("/api/v1/auth/logout/")
    assert login(api, admin_role.email, code).status_code == 400


def test_el_admin_de_django_exige_2fa_en_produccion(client, admin_role, settings):
    settings.ADMIN_REQUIRE_2FA = True
    client.force_login(admin_role)
    r = client.get("/" + settings.ADMIN_URL_PATH)
    assert r.status_code == 302 and "login" in r.url


def test_los_errores_no_filtran_trazas(api, settings):
    settings.DEBUG = False
    r = api.get("/api/v1/products/no-existe/")
    assert r.status_code == 404 and "Traceback" not in r.content.decode() and "django" not in r.content.decode().lower()


def test_la_api_publica_no_expone_cabeceras_del_servidor(api):
    r = api.get("/health/")
    assert "X-Powered-By" not in r


def test_ip_real_detras_del_proxy_ignora_lo_que_falsifica_el_cliente(rf, settings):
    from apps.core.ip import client_ip

    settings.BEHIND_PROXY = True
    request = rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.9", REMOTE_ADDR="10.0.0.2")
    assert client_ip(request) == "203.0.113.9"  # la que añadió el proxy, no la falsificada
    settings.BEHIND_PROXY = False
    assert client_ip(request) == "10.0.0.2"


def test_el_bloqueo_por_intentos_cuenta_por_ip_real_detras_del_proxy(api, customer_user, settings):
    settings.BEHIND_PROXY = True
    creds = {"email": customer_user.email, "password": "mala-clave-1"}
    for _ in range(5):
        api.post("/api/v1/auth/login/", creds, format="json", HTTP_X_FORWARDED_FOR="9.9.9.9, 198.51.100.7")
    locked = api.post("/api/v1/auth/login/", {**creds, "password": PASSWORD}, format="json", HTTP_X_FORWARDED_FOR="9.9.9.9, 198.51.100.7")
    other = api.post("/api/v1/auth/login/", {**creds, "password": PASSWORD}, format="json", HTTP_X_FORWARDED_FOR="9.9.9.9, 198.51.100.55")
    assert locked.status_code == 429 and other.status_code == 200  # otra IP real no queda bloqueada
