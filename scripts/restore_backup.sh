#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
DEFAULT_BACKUP="$PROJECT_DIR/backups/vvildan_20260822_184104.dump"
BACKUP_PATH=${1:-$DEFAULT_BACKUP}

if [ ! -f "$BACKUP_PATH" ]; then
    echo "Backup not found: $BACKUP_PATH" >&2
    exit 1
fi

cd "$PROJECT_DIR"

if ! docker compose ps --status running --services | grep -qx db; then
    echo "The PostgreSQL container is not running." >&2
    echo "Start it with: docker compose up -d db" >&2
    exit 1
fi

DATABASE_NAME=$(docker compose exec -T db sh -c 'printf "%s" "$POSTGRES_DB"')

printf "Restore %s into database '%s'? Existing objects will be replaced. [y/N] " \
    "$BACKUP_PATH" "$DATABASE_NAME"
read -r CONFIRMATION

case "$CONFIRMATION" in
    y|Y|yes|YES)
        ;;
    *)
        echo "Restore cancelled."
        exit 0
        ;;
esac

echo "Restoring backup..."
docker compose exec -T db sh -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    exec pg_restore \
        --host=127.0.0.1 \
        --username="$POSTGRES_USER" \
        --dbname="$POSTGRES_DB" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        --exit-on-error
' < "$BACKUP_PATH"

echo "Restore completed successfully."
