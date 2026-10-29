# Pagos con Culqi y avisos con n8n

El lanzamiento usa **Yape/Plin manual** (`PAYMENTS_PROVIDER=manual_yape_plin`). Culqi se activa con el feature flag
`PAYMENTS_PROVIDER=culqi` **y** llaves configuradas; si falta alguna, la tienda sigue ofreciendo Yape/Plin manual.

## Qué se verificó en la documentación oficial de Culqi

Fuente: <https://docs.culqi.com> (consultada durante el desarrollo).

- Llaves pública y secreta desde CulqiPanel → Desarrollo → API Keys; llaves de integración (`pk_test_`, `sk_test_`) para pruebas.
- Culqi Checkout entrega un token (`Culqi.token.id`) que el navegador envía al backend; el cargo se crea desde el servidor con ese token en `source_id`.
- Script de Checkout v4: `https://checkout.culqi.com/js/v4`. **La documentación avisa que v4 dejará de estar disponible pronto** y recomienda migrar a *Checkout Custom*. Hay que planificar esa migración (afecta solo `frontend/src/components/CulqiPay.tsx`).
- Órdenes de pago (billeteras, PagoEfectivo, Cuotéalo): se crean con `confirm: false` y **el webhook es obligatorio**, evento `order.status.changed` (pagada o expirada).
- Webhooks se registran en CulqiPanel → Eventos → Webhooks → Añadir. Eventos de cargos, órdenes, devoluciones, etc.
- Tarjetas de prueba (solo ambiente de integración): venta exitosa Visa `4111 1111 1111 1111` 09/30 CVV 123; error de fondos `4000 0400 0000 0008` 03/30 CVV 295; Yape de prueba: celular `900 000 001` con cualquier código de 6 dígitos.

## Qué NO se pudo verificar (confirmar con llaves de sandbox)

La documentación técnica de la API no cargó en el entorno de desarrollo, por lo que estos puntos están implementados según la convención de Culqi pero **sin comprobar**:

1. **URL base** de la API: `CULQI_API_BASE=https://api.culqi.com/v2`.
2. **Unidad del monto**: se envía en **céntimos** (S/ 180.50 → `18050`), también en `Culqi.settings({ amount })`.
3. **Nombres de campos** del cargo (`amount`, `currency_code`, `email`, `source_id`, `description`, `metadata`) y de la orden (`order_number`, `client_details`, `expiration_date`, `confirm`), y el resultado exitoso `outcome.type == "venta_exitosa"`.
4. **Autenticación y formato de los webhooks**: no se encontró cómo se firman. El diseño no depende de eso (ver abajo).
5. Estados de orden (`paid`, `expired`…) y si `data` llega como texto JSON u objeto (se aceptan ambos).

Todo está concentrado en `backend/apps/payments/providers/culqi_client.py`, `culqi.py` y `webhooks.py`. Cómo validarlo:
1. Poner `PAYMENTS_PROVIDER=culqi` y las llaves `sk_test_`/`pk_test_` en `.env`.
2. Hacer un pedido y pagar con la tarjeta de prueba; verificar que el pedido pase a `PAGADO`.
3. Probar tarjeta con error de fondos y confirmar que el pedido queda pendiente.
4. Registrar el webhook (ver abajo) y revisar `Eventos de pago` en el admin.

## Modelo de seguridad

- La clave secreta (`CULQI_SECRET_KEY`) solo existe en el backend; a la API pública solo llega la llave pública.
- El servidor nunca recibe datos de tarjeta (SAQ-A): solo el token. El payload guardado se limpia (sin `source`, tarjetas ni metadatos).
- El **monto lo calcula el servidor** a partir del pedido; el que mande el cliente se ignora.
- **Idempotencia**: cada intento lleva `idempotency_key` (única en base de datos); reintentar no vuelve a cobrar. Los eventos de webhook se guardan una vez (`proveedor + id`), reprocesarlos no duplica nada.
- **Webhook**: URL con secreto `…/api/v1/webhooks/culqi/<CULQI_WEBHOOK_SECRET>/` (y Basic Auth opcional si se activa "autenticación" al registrarlo). Aun así **no se confía en el cuerpo**: se consulta a Culqi el cargo/orden real, se compara monto y moneda, y solo entonces se aprueba. Un evento falso no aprueba nada. Si Culqi no responde, el endpoint contesta 503 y Culqi reintenta.
- Un pago aprobado cuando la reserva ya venció intenta reservar de nuevo; si ya no hay stock queda `requiere_revision` (reembolso manual).

## Registrar el webhook

CulqiPanel → Eventos → Webhooks → Añadir, URL: `https://TU-DOMINIO/api/v1/webhooks/culqi/<CULQI_WEBHOOK_SECRET>/`, eventos `charge.creation.succeeded` y `order.status.changed`.

## Comisiones

Aproximadamente 3.3 % a 4.2 % + IGV según tarjeta y pasarela (confirmar con el contrato). Se configura en el admin → Configuración de la tienda → *Comisión de pasarela*; la calculadora de precio la incorpora (`apps/pricing`).

## Pedidos por encargo

`Product.tipo_venta = por_encargo`: el checkout cobra el **adelanto** (`% de adelanto` en la configuración) y guarda el saldo. El pedido pasa a `PAGADO` con el adelanto. Cuando llega a Lima (`EN_LIMA`) la clienta ve "Falta pagar tu saldo" en su seguimiento y paga el resto (Yape/Plin o tarjeta). No se mezclan productos en stock con productos por encargo en un mismo pedido.

## Avisos por WhatsApp con n8n

Cada cambio importante escribe un evento en la tabla `WebhookOutbox` (patrón outbox, misma transacción) y una tarea de Celery los entrega a `N8N_WEBHOOK_URL` con firma HMAC-SHA256 en el encabezado `X-Signature` (clave `N8N_WEBHOOK_SECRET`), con reintentos.

| Evento | Cuándo | Datos |
|---|---|---|
| `order.created` | se crea un pedido | `pedido`, `token`, `total`, `tipo_venta` |
| `order.status_changed` | cambia el estado | `pedido`, `token`, `anterior`, `nuevo`, `cliente`, `telefono`, `total`, `tipo_venta`, `saldo_pendiente` |
| `payment.proof_uploaded` | la clienta sube un comprobante Yape/Plin | `pedido`, `pago`, `monto` |

Flujo sugerido en n8n: Webhook → verificar HMAC → Switch por `evento` → enviar WhatsApp (Cloud API de Meta o proveedor) con el enlace `https://TU-DOMINIO/pedido/<token>`. Mientras `N8N_WEBHOOK_URL` esté vacío no se envía nada.
