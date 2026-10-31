# Respaldos y restauración

## Qué se respalda
- **Base de datos** (pedidos, stock, clientas, pagos): `pg_dump` en formato custom → `db-AAAAMMDD-HHMMSS.dump`.
- **Fotos y comprobantes de pago**: `media-AAAAMMDD-HHMMSS.tar.gz`.

El servicio `backup` del compose de producción hace una copia al arrancar y luego cada 24 h, y borra las de más de `BACKUP_KEEP_DAYS` (14 por defecto). Las copias quedan en el volumen `backups` **del mismo servidor**.

Cada respaldo se **verifica al crearse** (`pg_restore -l`): un volcado cortado no se da por bueno.

## Copia fuera del servidor (lo más importante)

Un respaldo que vive solo en el servidor no sirve si el servidor se pierde. El servicio `backup` ya sabe copiar cada respaldo a otro lugar con rclone, **cifrado** (los respaldos tienen datos personales de las clientas):

1. Crea una cuenta en un almacenamiento externo (Backblaze B2, Cloudflare R2 o similar; revisa en su página el plan gratuito vigente) y una llave de acceso solo para ese bucket.
2. En el servidor: `cp .env.offsite.example .env.offsite`, completa los valores y `chmod 600 .env.offsite`. La frase de cifrado se guarda **también fuera del servidor**: sin ella no se puede restaurar.
3. En `.env.prod`: `BACKUP_OFFSITE=offsite:marle-respaldos` (y `BACKUP_OFFSITE_KEEP_DAYS`, 30 por defecto).
4. `$P up -d` y revisa `$P logs backup`: debe decir *Copia externa lista*. Comprueba el contenido con `$P exec backup rclone ls offsite:marle-respaldos`.

Probado con un destino local cifrado: los nombres de archivo salen ilegibles en el destino y `rclone ls` los muestra descifrados.

## Aviso si el respaldo falla o deja de llegar

Pon en `.env.prod` `BACKUP_PING_URL` con la dirección de un monitor gratuito (por ejemplo healthchecks.io: crea un chequeo diario y copia su URL de «ping»). El servicio la llama al terminar bien, y le agrega `/fail` si algo falla; si un día no llega ningún aviso, el monitor te escribe. Así te enteras tú antes que la dueña.

## Respaldo manual
```bash
P="docker compose -f docker-compose.prod.yml --env-file .env.prod"
$P exec backup sh /scripts/backup.sh
$P exec backup ls -la /backups
```

## Restaurar (probado)

**1. Probar la restauración en una base de prueba** (no toca la real; hazlo cada mes):
```bash
$P exec backup sh /scripts/restore.sh /backups/db-AAAAMMDD-HHMMSS.dump restauracion_prueba
$P exec backup psql -d restauracion_prueba -c "select count(*) from catalog_product;"
$P exec backup dropdb restauracion_prueba
```
Resultado de la prueba hecha en desarrollo: 12 productos, 10 movimientos de inventario y 0 pedidos en el original = lo mismo en la base restaurada.

**2. Restaurar de verdad (desastre):**
```bash
$P stop backend worker beat frontend            # la base queda sin uso
$P exec backup sh /scripts/restore.sh /backups/db-AAAAMMDD-HHMMSS.dump marle
$P up -d
$P exec backend python manage.py audit_stock    # confirma que el stock coincide con los movimientos
```
(`marle` = valor de `POSTGRES_DB`; `restore.sh` borra y recrea esa base.) Fotos: `tar -xzf media-AAAAMMDD-HHMMSS.tar.gz -C <volumen media>`.

## Reglas
- Prueba la restauración al menos una vez al mes y antes de cada actualización grande.
- Los respaldos contienen datos personales: protégelos igual que la base (Ley 29733).
