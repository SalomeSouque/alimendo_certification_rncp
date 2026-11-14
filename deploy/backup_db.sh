#!/usr/bin/env bash
# Sauvegarde de la base de production (format custom de pg_dump), avec rotation.
#
# Usage :   ./deploy/backup_db.sh
# Cron :    15 3 * * * /CHEMIN/DU/DEPOT/deploy/backup_db.sh >> $HOME/backups/alimendo/backup.log 2>&1
#
# Variables optionnelles : BACKUP_DIR (défaut ~/backups/alimendo), KEEP_DAYS (défaut 7).
# Les dumps contiennent des e-mails et des empreintes de mots de passe (RGPD) :
# dossier lisible par toi seule, et durée de conservation limitée.

set -euo pipefail
umask 077

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/alimendo}"
KEEP_DAYS="${KEEP_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/alimendo_$(date +%Y%m%d_%H%M%S).dump"

# Fichier temporaire puis renommage : un dump interrompu ne ressemble jamais à un dump valide.
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"

find "$BACKUP_DIR" -name 'alimendo_*.dump' -mtime +"$KEEP_DAYS" -delete

echo "$(date -Iseconds) sauvegarde OK : $FILE ($(du -h "$FILE" | cut -f1))"
