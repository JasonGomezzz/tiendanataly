import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.core.models import StoreSettings
from apps.payments.models import BankAccount, Payment
from tests.factories import make_order, make_product

pytestmark = pytest.mark.django_db
A = "/api/v1/admin/bank-accounts/"


def png():
    buf = io.BytesIO()
    Image.new("RGB", (6, 6), "pink").save(buf, "PNG")
    return SimpleUploadedFile("c.png", buf.getvalue(), content_type="image/png")


def account(**kw):
    data = {"banco": "bcp", "etiqueta": "Soles", "numero": "19100000000001", "cci": "00219100000000000152"}
    return BankAccount.objects.create(**{**data, **kw})


def test_la_tienda_publica_solo_las_cuentas_activas(api):
    account(orden=2)
    account(banco="interbank", numero="1003000000002", cci="00310000000000000052", orden=1)
    account(banco="bbva", numero="999", activa=False)
    cuentas = api.get("/api/v1/store-settings/public/").json()["cuentas"]
    assert [c["banco"] for c in cuentas] == ["interbank", "bcp"]
    assert "activa" not in cuentas[0]


def test_comprobante_por_transferencia_guarda_el_banco_y_el_monto_del_servidor(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    r = api.post(
        f"/api/v1/orders/{order.public_token}/payments/manual/",
        {"comprobante": png(), "metodo": "transferencia", "banco": "BCP"}, format="multipart",
    )
    assert r.status_code == 201 and r.json()["estado"] == "en_revision"
    p = Payment.objects.get()
    assert p.metodo == "transferencia" and p.nota == "Transferencia BCP" and p.monto == order.total_pen


def test_metodo_de_pago_invalido_se_rechaza(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    r = api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "bitcoin"}, format="multipart")
    assert r.status_code == 400


def test_la_administradora_gestiona_cuentas_desde_el_panel_y_el_staff_no(api, admin_role, staff_role):
    api.force_authenticate(admin_role)
    created = api.post(A, {"banco": "bcp", "numero": "123", "cci": "456", "titular": "Titular"}, format="json")
    assert created.status_code == 201
    pk = created.json()["id"]
    assert api.patch(f"{A}{pk}/", {"activa": False}, format="json").json()["activa"] is False
    assert len(api.get(A).json()) == 1
    assert api.delete(f"{A}{pk}/").status_code == 204
    api.force_authenticate(staff_role)
    assert api.get(A).status_code == 403
    assert api.post(A, {"banco": "bcp", "numero": "1"}, format="json").status_code == 403


def test_load_business_data_carga_yape_plin_y_cuentas_sin_duplicar(tmp_path):
    f = tmp_path / "negocio.yaml"
    f.write_text(
        'tienda:\n  yape_numero: "999111222"\n  plin_numero: "999111222"\n'
        'cuentas:\n  - {banco: bcp, numero: "19100000000001", cci: "00219100000000000152"}\n'
        '  - {banco: interbank, numero: "1003000000002", cci: "00310000000000000052"}\n',
        encoding="utf-8",
    )
    call_command("load_business_data", file=str(f), verbosity=0)
    call_command("load_business_data", file=str(f), verbosity=0)
    assert StoreSettings.load().yape_numero == "999111222" and StoreSettings.load().plin_numero == "999111222"
    assert BankAccount.objects.count() == 2


def test_load_business_data_rechaza_campos_desconocidos(tmp_path):
    from django.core.management import CommandError

    f = tmp_path / "n.yaml"
    f.write_text("tienda:\n  inventado: 1\n", encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("load_business_data", file=str(f), verbosity=0)
