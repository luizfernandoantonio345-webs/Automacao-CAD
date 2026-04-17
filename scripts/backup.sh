#!/usr/bin/env env bash
# scripts/backup.sh — EngCAD PostgreSQL + Redis backup
# ──────────────────────────────────────────────────────
# Cria dump comprimido do PostgreSQL e snapshot RDB do Redis.
# Mantém apenas os últimos N backups (padrão: 7).
#
# Uso: bash scripts/backup.sh [--keep N]
# Cron: 0 2 * * * /app/scripts/backup.sh >> /var/log/engcad_backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/engcad}"
KEEP="${KEEP:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PG_DUMP_FILE="${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"
REDIS_DUMP_FILE="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep) KEEP="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Starting backup (keep=${KEEP})"

# ── PostgreSQL dump ────────────────────────────────────────────
if command -v pg_dump &>/dev/null; then
  echo "  [PG] Dumping ${DB_NAME:-engcad}..."
  PGPASSWORD="${DB_PASS}" pg_dump \
    -h "${DB_HOST:-postgres-primary}" \
    -U "${DB_USER:-engcad}" \
    -d "${DB_NAME:-engcad}" \
    --no-password \
    | gzip -9 > "${PG_DUMP_FILE}"
  echo "  [PG] Saved: ${PG_DUMP_FILE} ($(du -sh "${PG_DUMP_FILE}" | cut -f1))"
else
  echo "  [PG] pg_dump not found, trying docker..."
  docker exec cad-pg-primary sh -c \
    "PGPASSWORD=${DB_PASS} pg_dump -U ${DB_USER:-engcad} ${DB_NAME:-engcad}" \
    | gzip -9 > "${PG_DUMP_FILE}"
  echo "  [PG] Saved via docker: ${PG_DUMP_FILE}"
fi

# ── Redis snapshot ─────────────────────────────────────────────
echo "  [Redis] Triggering BGSAVE..."
if command -v redis-cli &>/dev/null; then
  redis-cli -h "${REDIS_HOST:-redis-1}" -a "${REDIS_PASS:-}" BGSAVE 2>/dev/null || true
  sleep 2
  RDB_SRC=$(redis-cli -h "${REDIS_HOST:-redis-1}" -a "${REDIS_PASS:-}" CONFIG GET dir 2>/dev/null | tail -1)
  RDB_FILE="${RDB_SRC}/dump.rdb"
  if [[ -f "${RDB_FILE}" ]]; then
    cp "${RDB_FILE}" "${REDIS_DUMP_FILE}"
    echo "  [Redis] Saved: ${REDIS_DUMP_FILE}"
  fi
else
  echo "  [Redis] redis-cli not found, skipping Redis backup."
fi

# ── Rotate old backups ─────────────────────────────────────────
echo "  [Rotate] Keeping last ${KEEP} backups per type..."
ls -t "${BACKUP_DIR}"/pg_*.sql.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -v
ls -t "${BACKUP_DIR}"/redis_*.rdb 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -v

echo "[$(date -Iseconds)] Backup complete."
