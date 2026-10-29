# Tienda Nataly

Tienda web de importación y venta de bolsos, mochilas y fragancias para un negocio familiar en Lima.
Monorepo con **Django + DRF + PostgreSQL** (backend), **Next.js (App Router) + TypeScript + Tailwind** (frontend), Celery + Redis para tareas, y Docker Compose para desarrollo.

> Tienda independiente de importación, no afiliada a Victoria's Secret. Las fotos de producto son propias.

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 1. Base | Monorepo, modelos, seed, API base, admin con roles, auth segura, tests | Hecha (pendiente de revisión) |
| 2. Vitrina | Catálogo, producto, carrito, reserva, WhatsApp, Yape/Plin manual, SEO | Pendiente |
| 3. Pagos y estados | Culqi (sandbox), webhooks, n8n, pre-order | Pendiente |
| 4. Panel `/admin` en Next.js | Dashboard y alta de producto desde el celular | Pendiente |
| 5. Endurecimiento y salida | Carga, backups, despliegue, checklist | Pendiente |

## Levantar el proyecto

Requisitos: Docker Desktop encendido.

```bash
cp .env.example .env        # y edita los valores marcados "cambia"
docker compose up --build
```

Esto arranca Postgres, Redis, el backend (migra y crea los roles solo), el worker y el beat de Celery, y el frontend.

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Admin de Django | `http://localhost:8000/<ADMIN_URL_PATH>` (valor de `.env`) |

Primer uso:

```bash
docker compose exec backend python manage.py seed_inventory      # carga los 9 productos (borrador, sin precios)
docker compose exec backend python manage.py createsuperuser     # solo el desarrollador es superusuario
```

### Usuarias del admin

La dueña y el staff **no son superusuarios**. Se crean desde el admin (como superusuario) y se les asigna el grupo `Administradora` o `Staff`, con `is_staff` activo. Los grupos los crea `python manage.py setup_roles` (corre solo al iniciar el backend).

| Rol | Puede | No puede |
|---|---|---|
| Administradora | productos, precios y costos, pedidos, pagos, clientas, configuración, tipo de cambio, auditoría | usuarios, grupos, dispositivos 2FA |
| Staff | productos (sin costos ni precios) y pedidos | finanzas, pagos, clientas, configuración, auditoría, borrar productos |
| Superusuario | todo | — |

### 2FA

Con `ADMIN_REQUIRE_2FA=true` (siempre activo en producción) el admin exige un código TOTP, y el login por API de cuentas `is_staff` también. Para activarlo a una usuaria: en el admin, *Dispositivos TOTP → Añadir*, elegir la usuaria, marcar *confirmado* y entregarle el QR/clave para su app de autenticación.

## Tests

```bash
docker compose run --rm backend pytest
```

Incluyen permisos por rol, IDOR, auth/CSRF/lockout/rate limit, reservas y descuento de stock, **concurrencia de la última unidad** (requiere PostgreSQL), cálculo de precios, estados de pedido y expiración, y seed.

Sin Docker se puede correr casi todo sobre SQLite (el test de concurrencia se omite):

```bash
cd backend && pip install -r requirements-dev.txt
TEST_DB=sqlite pytest
```

Auditoría de stock (compara contadores con el libro de movimientos):

```bash
docker compose exec backend python manage.py audit_stock
```

## Arquitectura en una mirada

- **Stock**: `ProductVariant.stock_disponible` (físico) y `stock_reservado`, solo modificables por `apps/inventory/services.py` (bloqueo de fila con `select_for_update`, un `InventoryMovement` por cambio). Reservas con expiración configurable (`StoreSettings.minutos_reserva`); el job de Celery libera y pasa el pedido a `EXPIRADO`.
- **Precios**: `apps/pricing/services.py`, función pura con `Decimal`: `(precio_usd + envío + impuestos) × tipo de cambio + margen`, con la comisión de pasarela incorporada y redondeo comercial hacia arriba.
- **Pedidos**: máquina de estados en `apps/orders/services.py` con historial y eventos al outbox (n8n, fase 3). El cliente consulta por `public_token` (UUID), no por id.
- **Pagos**: interfaz `PaymentProvider` + adaptadores. Hoy `manual_yape_plin`; `culqi` se activa con `PAYMENTS_PROVIDER` en la fase 3.
- **Sesión**: cookies `HttpOnly`, `SameSite=Lax`, CSRF activo. El frontend habla solo con Next, que reenvía `/api/v1/*` al backend.
- **Autorización**: siempre en Django. Los endpoints privados filtran por propietaria.

## Variables de entorno

Todas están documentadas en [`.env.example`](.env.example). Los secretos solo viven en `.env` (ignorado por git).

## Pendientes de negocio

Precios de compra y venta, reparto de los 5 splash clásicos por fragancia, línea exacta de la crema (`crema-corporal-cucumber`), nombre/logo/colores/WhatsApp definitivos, RUC y pasarela, zonas y costos de envío, dominio y hosting. Todo se edita desde el admin; nada está fijo en código.

## Backups (resumen; se completa en la fase 5)

```bash
docker compose exec db pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB > backups/tienda.dump
docker compose exec -T db pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean < backups/tienda.dump
```
