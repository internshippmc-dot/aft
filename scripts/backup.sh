#!/usr/bin/env bash
# Nightly encrypted backup — SECURITY.md section 7 & 10.
# Requires `age` installed on the host and BACKUP_AGE_PUBLIC_KEY set in .env
# (generate the keypair once with `age-keygen -o backup.key`; keep backup.key
# somewhere other than this server — it's the only way to decrypt a restore).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)
FILE="backups/aft-$STAMP.sql.age"

docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U aft aft_console | age -r "$BACKUP_AGE_PUBLIC_KEY" > "$FILE"

# 30 daily backups kept locally — TECH_SPEC.md section 10. Push $FILE to
# object storage here too; this script only covers the local half.
find backups -name '*.sql.age' -mtime +30 -delete

echo "Backup written to $FILE"
