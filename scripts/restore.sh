#!/usr/bin/env bash
# scripts/restore.sh — EngCAD PostgreSQL restore from backup
# ──────────────────────────────────────────────────────────────
# Uso: bash scripts/restore.sh --file /var/backups/engcad/pg_20240101_020000.sql.gz
#      bash scripts/restore.sh --latest
#
# AVISO: Faz DROP e recria o banco. Use apenas em manutenção!

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/engcad}"
DUMP_FILE=""
USE_LATEST=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)   DUMP_FILE="$2"; shift 2 ;;
    --latest) USE_LATEST=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ $USE_LATEST -eq 1 ]]; then
  DUMP_FILE=$(ls -t "${BACKUP_DIR}"/pg_*.sql.gz 2>/dev/null | head -1)
  if [[ -z "${DUMP_FILE}" ]]; then
    echo "[ERRO] Nenhum backup encontrado em ${BACKUP_DIR}"
    exit 1
  fi
fi

if [[ -z "${DUMP_FILE}" ]]; then
  echo "Uso: $0 --file <path.sql.gz> | --latest"
  exit 1
fi

if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "[ERRO] Arquivo não encontrado: ${DUMP_FILE}"
  exit 1
fi

echo "[$(date -Iseconds)] Restaurando de: ${DUMP_FILE}"
echo "  Banco: ${DB_NAME:-engcad} @ ${DB_HOST:-postgres-primary}"

# Confirmação interativa (skip com FORCE=1)
if [[ "${FORCE:-0}" != "1" ]]; then
  read -rp "  ATENÇÃO: Isso APAGARÁ todos os dados atuais. Confirmar? [s/N] " confirm
  if [[ "${confirm}" != "s" && "${confirm}" != "S" ]]; then
    echo "Operação cancelada."
    exit 0
  fi
fi

# Drop + recreate db
PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST:-postgres-primary}" \
  -U "${DB_USER:-engcad}" \
  -d postgres \
  -c "DROP DATABASE IF EXISTS \"${DB_NAME:-engcad}\"; CREATE DATABASE \"${DB_NAME:-engcad}\";"

# Restore
zcat "${DUMP_FILE}" | PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST:-postgres-primary}" \
  -U "${DB_USER:-engcad}" \
  -d "${DB_NAME:-engcad}"

echo "[$(date -Iseconds)] Restauração concluída."
