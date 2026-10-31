#!/bin/sh
# Respaldo de PostgreSQL (formato custom, comprimido) + fotos/comprobantes subidos.
# Opcional: copia FUERA del servidor con rclone y aviso a un monitor (healthchecks.io u otro) al terminar.
#
# Variables: PGHOST PGUSER PGPASSWORD PGDATABASE, BACKUP_DIR (def. /backups), BACKUP_KEEP_DAYS (def. 14),
#            BACKUP_OFFSITE (destino de rclone, p. ej. offsite:marle-respaldos), BACKUP_OFFSITE_KEEP_DAYS (def. 30),
#            BACKUP_PING_URL (se llama al terminar bien; con /fail al final si algo falla)
set -eu

DIR="${BACKUP_DIR:-/backups}"
KEEP="${BACKUP_KEEP_DAYS:-14}"
OFFSITE="${BACKUP_OFFSITE:-}"
OFFSITE_KEEP="${BACKUP_OFFSITE_KEEP_DAYS:-30}"
PING="${BACKUP_PING_URL:-}"
STAMP="$(date +%Y%m%d-%H%M%S)"

ping_monitor() {
  [ -n "$PING" ] || return 0
  wget -q -T 10 -O /dev/null "${PING}${1:-}" 2>/dev/null || echo "AVISO: no se pudo avisar al monitor"
}

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then
    ping_monitor ""
  else
    echo "ERROR: el respaldo falló (código $code)"
    ping_monitor "/fail"
  fi
}
trap finish EXIT

mkdir -p "$DIR"
pg_dump -Fc --no-owner "$PGDATABASE" > "$DIR/db-$STAMP.dump.tmp"
# Un volcado cortado no sirve: comprobar que se puede leer antes de darlo por bueno.
pg_restore -l "$DIR/db-$STAMP.dump.tmp" > /dev/null
mv "$DIR/db-$STAMP.dump.tmp" "$DIR/db-$STAMP.dump"

if [ -d /media ] && [ "$(ls -A /media 2>/dev/null)" ]; then
  tar -czf "$DIR/media-$STAMP.tar.gz" -C /media .
fi

# Retención local: borra respaldos con más de $KEEP días
find "$DIR" -type f \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$KEEP" -delete

echo "Respaldo listo: $DIR/db-$STAMP.dump ($(du -h "$DIR/db-$STAMP.dump" | cut -f1))"

if [ -n "$OFFSITE" ]; then
  command -v rclone > /dev/null 2>&1 || { echo "ERROR: hay BACKUP_OFFSITE pero rclone no está instalado"; exit 1; }
  rclone copy "$DIR" "$OFFSITE" --include 'db-*.dump' --include 'media-*.tar.gz'
  rclone delete "$OFFSITE" --min-age "${OFFSITE_KEEP}d" --include 'db-*.dump' --include 'media-*.tar.gz'
  echo "Copia externa lista: $OFFSITE"
else
  echo "RECUERDA: sin BACKUP_OFFSITE los respaldos viven solo en este servidor (ver docs/respaldos.md)."
fi
