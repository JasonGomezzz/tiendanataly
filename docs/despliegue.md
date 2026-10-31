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

### Datos del negocio (Yape, Plin y cuentas bancarias)
Tres formas, a elección: (1) en `/admin` → Ajustes, (2) en el admin de Django → *Cuentas bancarias*, o (3) copiando `seed/negocio.local.yaml` (parte de `seed/negocio.example.yaml`) al servidor y corriendo `$P exec backend python manage.py load_business_data`. Ese archivo está en `.gitignore`: los números de cuenta nunca se suben a GitHub.

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
- Dependabot (`.github/dependabot.yml`) avisa de actualizaciones y vulnerabilidades, y la CI (`.github/workflows/ci.yml`) corre en cada cambio.
- **Sentry (opcional, plan gratuito):** crea un proyecto de Django, copia su DSN a `SENTRY_DSN` en `.env.prod` y reinicia el backend. Reporta errores del sitio y de las tareas de Celery **sin** datos personales (sin IP, cookies ni cuerpos de peticiones). El frontend aún no reporta a Sentry: ante un fallo en la tienda mira `logs frontend`.
- **Aviso de respaldos:** `BACKUP_PING_URL` (ver `docs/respaldos.md`).

## 6. Lista de producción (resumen)

| Punto | Estado |
|---|---|
| Respaldo diario de PostgreSQL y fotos | Hecho; verifica cada volcado y se restaura (ver `docs/respaldos.md`) |
| Copia **fuera** del servidor, cifrada | Hecho en el código; falta crear la cuenta del almacenamiento y llenar `.env.offsite` |
| Aviso si un respaldo falla o no llega | Hecho en el código; falta crear el monitor y poner `BACKUP_PING_URL` |
| `db` y `redis` sin puertos publicados | Hecho: solo los ve la red interna de Docker; el firewall deja pasar solo 22, 80 y 443 |
| Secretos en variables de entorno | Hecho: `.env.prod` y `.env.offsite` fuera de git; en el servidor `chmod 600 .env.prod .env.offsite` |
| `restart: unless-stopped` y healthchecks | Hecho en todos los servicios; healthcheck en base, Redis, backend y tienda |
| gunicorn en vez de `runserver` | Hecho (3 workers) |
| Una sola instancia de `beat` | Hecho; no escalar `beat` (el worker sí se puede escalar) |
| Avisos de errores (Sentry) | Hecho en el backend, apagado hasta poner `SENTRY_DSN`; falta el frontend |
