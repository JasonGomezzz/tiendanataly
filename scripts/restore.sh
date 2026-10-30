#!/bin/sh
# Restaura un respaldo de PostgreSQL en la base indicada (por defecto, una base NUEVA de prueba).
# Uso: sh restore.sh /backups/db-YYYYMMDD-HHMMSS.dump [base_destino]
# Variables: PGHOST PGUSER PGPASSWORD
set -eu

FILE="${1:?Indica el archivo .dump}"
TARGET="${2:-restauracion_prueba}"

dropdb --if-exists "$TARGET"
createdb "$TARGET"
pg_restore --no-owner --exit-on-error -d "$TARGET" "$FILE"
echo "Restaurado en la base «$TARGET»."
echo "Verifica: psql -d $TARGET -c 'select count(*) from catalog_product;'"
