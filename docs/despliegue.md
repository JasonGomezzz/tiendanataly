# Despliegue en un VPS con Docker

Arquitectura de producción (`docker-compose.prod.yml`):

```
Internet ─► Caddy (80/443, HTTPS automático)
              ├─ /media/*, /static/*  → archivos desde disco
              ├─ /api/*, /health/, /<ADMIN_URL_PATH>  → backend (gunicorn)
              └─ todo lo demás         → frontend (Next.js standalone)
backend ─► PostgreSQL 17, Redis (cache, rate limit, Celery) · worker y beat (expiración de reservas, n8n)
backup  ─► pg_dump + fotos cada 24 h, retención configurable
```

Probado localmente con este mismo compose: HTTPS, CSP, HSTS, enrutamiento, optimizador de imágenes, respaldo y restauración,
bloqueo por IP real detrás del proxy y prueba de carga (ver `docs/checklist-salida.md`).

## 1. Servidor

- VPS Linux (Ubuntu 24.04 LTS), mínimo 2 vCPU / 2 GB RAM / 40 GB de disco.
- Acceso solo con **llave SSH** (desactiva contraseña y login de root).
- Firewall: permitir solo 22 (idealmente limitado a tu IP), 80 y 443.
  ```bash
  sudo ufw default deny incoming && sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw enable
  ```
- Instala Docker Engine y el plugin Compose (guía oficial de Docker para Ubuntu). Activa actualizaciones automáticas de seguridad (`unattended-upgrades`).
- DNS: registro `A` del dominio (y `www` si quieres) apuntando a la IP del VPS **antes** del primer arranque, para que Caddy obtenga el certificado.

## 2. Primer despliegue

```bash
git clone https://github.com/JasonGomezzz/tiendanataly.git && cd tiendanataly
cp .env.prod.example .env.prod      # completa TODOS los valores marcados GENERA/tu-dominio
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod ps     # todo "Up (healthy)"
```

El backend migra la base y crea los grupos de roles solo al arrancar. Después:

```bash
P="docker compose -f docker-compose.prod.yml --env-file .env.prod"
$P exec backend python manage.py createsuperuser            # SOLO el desarrollador
$P exec backend python manage.py seed_inventory             # opcional: carga el inventario inicial
```

### Usuarias del panel y 2FA

1. Entra al admin de Django (`https://TU-DOMINIO/<ADMIN_URL_PATH>`) con el superusuario → *Usuarios* → crea a la administradora: `is_staff` activo, **sin** superusuario, grupo `Administradora`. Usa su correo como nombre de usuario. Para el personal, grupo `Staff`.
2. Activa su 2FA (obligatorio) y entrégale el QR y los códigos de respaldo:
   ```bash
   $P exec backend python manage.py enroll_2fa correo@ejemplo.com
   ```
   Si pierde el celular: `enroll_2fa correo@ejemplo.com --reset`.
3. Ella entra al panel en `https://TU-DOMINIO/admin` con correo, contraseña y el código de su app.

### Datos de la tienda
En `/admin` → Ajustes: WhatsApp, Yape/Plin, tipo de cambio, margen y comisión, minutos de reserva. En el admin de Django → *Zonas de envío*: costos reales.

## 3. Actualizar

```bash
git pull && $P up -d --build          # migra solo; las reservas y pedidos no se pierden
```
Antes de actualizar, haz un respaldo manual (`$P exec backup sh /scripts/backup.sh`). Si algo sale mal: `git checkout <commit anterior>` y `up -d --build`; si hubo migraciones destructivas, restaura el respaldo (ver `docs/respaldos.md`).

## 4. Imágenes (decisión)

Las fotos y comprobantes viven en el disco del VPS (volumen `media`), se sirven con Caddy y entran en el respaldo diario. Para el volumen de este negocio es suficiente y barato. Cloudinary/S3 **no está integrado**; si el catálogo crece mucho o quieres CDN, es un cambio acotado de `STORAGES` en `settings`.

## 5. Monitoreo mínimo

- `docker compose ... ps` y `logs -f backend` ante cualquier reclamo.
- Un chequeo externo gratuito (UptimeRobot o similar) a `https://TU-DOMINIO/health/`.
- Revisa `/admin` → pedidos "Pendiente de pago" con comprobante: es la tarea diaria de la administradora.
- Dependabot y CI (`.github/`) avisan de actualizaciones y vulnerabilidades.
