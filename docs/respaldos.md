# Respaldos y restauración

## Qué se respalda
- **Base de datos** (pedidos, stock, clientas, pagos): `pg_dump` en formato custom → `db-AAAAMMDD-HHMMSS.dump`.
- **Fotos y comprobantes de pago**: `media-AAAAMMDD-HHMMSS.tar.gz`.

El servicio `backup` del compose de producción hace una copia al arrancar y luego cada 24 h, y borra las de más de `BACKUP_KEEP_DAYS` (14 por defecto). Las copias quedan en el volumen `backups` **del mismo servidor**.

> Un respaldo que vive solo en el servidor no sirve si el servidor se pierde. **Copia `/backups` a otro lugar** (otro proveedor o tu computadora) con un cron diario. Ejemplo con rclone hacia Backblaze B2 o Google Drive:
> ```bash
> docker run --rm -v tiendanataly-prod_backups:/backups:ro -v ~/.config/rclone:/config/rclone rclone/rclone sync /backups remoto:marle-respaldos
> ```

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
