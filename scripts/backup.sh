#!/usr/bin/env bash
# Encrypted database backup — SECURITY.md section 7 & 10.
#
# Works against any Postgres reachable via DATABASE_URL — a local
# docker-compose db, or Railway's managed Postgres (use the connection
# string from Railway's Postgres service -> Connect tab). Requires `age`
# and `pg_dump`/`psql` (the postgresql-client package, matching the
# server's major version) installed wherever this runs.
#
# Requires BACKUP_AGE_PUBLIC_KEY set in .env (generate the keypair once
# with `age-keygen -o backup.key`; keep backup.key somewhere other than
# this server/host — it's the only way to decrypt a restore).
#
# THIS SCRIPT DOES NOT SCHEDULE ITSELF. Nothing in this repo runs it
# automatically. Options to actually get nightly backups running:
#   - A cron entry on a host that stays up (e.g. `0 2 * * * cd /path/to/Dashboard && ./scripts/backup.sh`)
#   - A scheduled GitHub Action, if this repo is on GitHub
#   - Railway's own Postgres backup/PITR feature (check your plan) — the
#     managed option, and worth using instead of/alongside this script
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

if [ -z "${BACKUP_AGE_PUBLIC_KEY:-}" ]; then
  echo "BACKUP_AGE_PUBLIC_KEY is not set in .env — refusing to write an unencrypted backup." >&2
  exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set — point it at the Postgres instance to back up (local or Railway)." >&2
  exit 1
fi

# pg_dump doesn't understand SQLAlchemy's "+psycopg" driver suffix.
PG_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)
FILE="backups/aft-$STAMP.sql.age"

pg_dump "$PG_URL" | age -r "$BACKUP_AGE_PUBLIC_KEY" > "$FILE"

# 30 daily backups kept locally — TECH_SPEC.md section 10. Push $FILE to
# object storage here too; this script only covers the local half.
find backups -name '*.sql.age' -mtime +30 -delete

echo "Backup written to $FILE"
