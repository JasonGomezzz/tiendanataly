#!/bin/sh
# Respaldo de PostgreSQL (formato custom, comprimido) + fotos/comprobantes subidos.
# Variables: PGHOST PGUSER PGPASSWORD PGDATABASE, BACKUP_DIR (def. /backups), BACKUP_KEEP_DAYS (def. 14)
set -eu

DIR="${BACKUP_DIR:-/backups}"
KEEP="${BACKUP_KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DIR"
pg_dump -Fc --no-owner "$PGDATABASE" > "$DIR/db-$STAMP.dump.tmp"
mv "$DIR/db-$STAMP.dump.tmp" "$DIR/db-$STAMP.dump"

if [ -d /media ] && [ "$(ls -A /media 2>/dev/null)" ]; then
  tar -czf "$DIR/media-$STAMP.tar.gz" -C /media .
fi

# Retención: borra respaldos con más de $KEEP días
find "$DIR" -type f \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$KEEP" -delete

echo "Respaldo listo: $DIR/db-$STAMP.dump ($(du -h "$DIR/db-$STAMP.dump" | cut -f1))"
echo "RECUERDA: copia $DIR a un lugar FUERA del servidor (ver docs/respaldos.md)."
