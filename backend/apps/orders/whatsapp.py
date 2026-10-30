from urllib.parse import quote

from apps.core.models import StoreSettings


def order_message(order):
    """Mensaje prearmado con el detalle del pedido para enviar a la tienda por WhatsApp."""
    lines = [f"Hola, quiero confirmar mi pedido #{order.pk} en {StoreSettings.load().nombre_tienda}:"]
    for item in order.items.all():
        lines.append(f"• {item.cantidad} × {item.nombre_snapshot} — S/ {item.subtotal:.2f}")
    if order.descuento_pen:
        lines.append(f"Oferta aplicada: −S/ {order.descuento_pen:.2f}")
    if order.envio_pen:
        lines.append(f"Envío: S/ {order.envio_pen:.2f}")
    lines.append(f"Total: S/ {order.total_pen:.2f}")
    if order.tipo_venta == "por_encargo":
        lines.append(f"Adelanto: S/ {order.adelanto_pen:.2f} · Saldo: S/ {order.saldo_pen:.2f}")
    lines.append(f"Nombre: {order.cliente.nombre}")
    return "\n".join(lines)


def whatsapp_url(text, number=None):
    number = (number or StoreSettings.load().whatsapp or "").strip().lstrip("+")
    if not number:
        return None
    return f"https://wa.me/{number}?text={quote(text)}"


def order_whatsapp(order):
    text = order_message(order)
    return {"text": text, "url": whatsapp_url(text)}
