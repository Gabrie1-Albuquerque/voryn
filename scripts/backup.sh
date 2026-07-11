#!/usr/bin/env bash
# Daily Postgres backup -- "Backup diário" is named explicitly in the source
# spec's Infraestrutura Inicial list, alongside "VPS, Docker Compose, Nginx"
# (the initial, pre-managed-services scale tier). Dumps the whole database
# (schema + data, all tenants) via pg_dump inside the running postgres
# container, gzipped, timestamped, with old backups pruned locally.
#
# Usage: ./scripts/backup.sh [destination-dir]
# Schedule with cron, e.g. (crontab -e):
#   0 3 * * * cd /path/to/Projeto_agendamento && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# This is a local-disk backup, not an offsite one -- for a real production
# deployment, also copy $DEST_DIR's contents somewhere off the same VPS
# (object storage, another host) so a disk failure doesn't take the backups
# down with the database.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

DEST_DIR="${1:-backups}"
mkdir -p "$DEST_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-app}"
POSTGRES_USER="${POSTGRES_USER:-app}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$DEST_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

COMPOSE_FILE="docker-compose.yml"
if [ "${2:-}" = "prod" ]; then
  COMPOSE_FILE="docker-compose.prod.yml"
fi

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$OUT_FILE"

echo "Backup salvo em $OUT_FILE"

# Keeps the last 14 daily backups locally; adjust to taste.
find "$DEST_DIR" -name "${POSTGRES_DB}_*.sql.gz" -mtime +14 -delete
