# Marle Fashion

Tienda web de importación y venta de bolsos, mochilas y fragancias para un negocio familiar en Lima.
Monorepo con **Django + DRF + PostgreSQL** (backend), **Next.js (App Router) + TypeScript + Tailwind** (frontend), Celery + Redis para tareas, y Docker Compose para desarrollo.

> Tienda independiente de importación, no afiliada a Victoria's Secret. Las fotos de producto son propias.

## Estado

Todo el trabajo está unido en `main`. Lo que falta para abrir al público (dominio, servidor, cuentas externas y datos del negocio) está en [docs/checklist-salida.md](docs/checklist-salida.md).

| Etapa | Contenido | Estado |
|---|---|---|
| 1. Base | Monorepo, modelos, seed, API base, admin con roles, auth segura, tests | Hecha |
| 2. Vitrina | Catálogo, producto, bolsa, reserva atómica, WhatsApp, Yape/Plin manual, SEO | Hecha |
| 3. Pagos y estados | Culqi (sin validar contra sandbox), webhooks verificados, n8n, encargos con adelanto | Hecha |
| 4. Panel `/admin` en Next.js | Dashboard, alta de producto con cámara, calculadora, tablero de pedidos | Hecha |
| 5. Endurecimiento y salida | 2FA, IP real tras proxy, CSP, respaldos, CI, carga, compose de producción | Hecha |
| Datos reales | Catálogo con precios y fotos propias (20 productos), logo de la marca, fotos de mesa con fondo quitado | Hecha |
| Ofertas | Oferta «N por S/ X» por producto (aplicada en bolsa, checkout y pedido) | Hecha |
| Medios de pago | Yape, Plin y transferencia (BCP, Interbank) con imagen de referencia y botón de copiar; cuentas editables en el panel | Hecha |
| Producción | Respaldos con copia externa cifrada y aviso, healthchecks, un solo `beat`, Sentry opcional | Hecha; falta crear las cuentas externas |

Documentación: [despliegue](docs/despliegue.md) · [VPS o Vercel](docs/hosting-opciones.md) · [direcciones y envío con Google](docs/direcciones-y-envio.md) · [respaldos](docs/respaldos.md) · [checklist de salida](docs/checklist-salida.md) · [Culqi y n8n](docs/pagos-culqi.md) · [marca](docs/marca.md) · [guía de fotos](docs/guia-fotos.md).

## Levantar el proyecto

Requisitos: Docker Desktop encendido.

```bash
cp .env.example .env        # y edita los valores marcados "cambia"
docker compose up --build
```

Esto arranca Postgres, Redis, el backend (migra y crea los roles solo), el worker y el beat de Celery, y el frontend.

El panel de la administradora está en `/admin` (login con correo, contraseña y código 2FA). Producción: ver [docs/despliegue.md](docs/despliegue.md) y `docker-compose.prod.yml`.

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Admin de Django | `http://localhost:8000/<ADMIN_URL_PATH>` (valor de `.env`) |

Primer uso:

```bash
docker compose exec backend python manage.py seed_inventory      # carga los productos de seed/inventory.yaml
docker compose exec backend python manage.py createsuperuser     # solo el desarrollador es superusuario
```

Yape, Plin y las cuentas bancarias **no están en el repositorio**: se copian `seed/negocio.example.yaml` a `seed/negocio.local.yaml` (ignorado por git), se llenan los datos reales y se corre:

```bash
docker compose exec backend python manage.py load_business_data
```

También se pueden escribir desde `/admin` → Ajustes.

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
