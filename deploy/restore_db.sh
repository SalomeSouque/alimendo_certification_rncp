#!/usr/bin/env bash
# Restaure un dump produit par backup_db.sh.
#
# Usage :
#   ./deploy/restore_db.sh <fichier.dump> alimendo_restore_test   # TEST : base temporaire
#   ./deploy/restore_db.sh <fichier.dump>                         # PROD : écrase la base
#
# Pour un test, la base cible est créée si elle n'existe pas. Pense à la supprimer après :
#   docker compose -f docker-compose.prod.yml exec db sh -c 'dropdb -U "$POSTGRES_USER" alimendo_restore_test'

set -euo pipefail

FILE="${1:?usage : deploy/restore_db.sh <fichier.dump> [base_cible]}"
TARGET="${2:-}"
[[ -f "$FILE" ]] || { echo "Fichier introuvable : $FILE" >&2; exit 1; }

cd "$(dirname "$0")/.."
DC=(docker compose -f docker-compose.prod.yml exec -T db)

if [[ -z "$TARGET" ]]; then
  read -r -p "Écraser la base de PRODUCTION avec $FILE ? Tape 'oui' : " ANSWER
  [[ "$ANSWER" == "oui" ]] || { echo "Annulé."; exit 1; }
  "${DC[@]}" sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$FILE"
else
  [[ "$TARGET" =~ ^[a-z0-9_]+$ ]] || { echo "Nom de base refusé : $TARGET" >&2; exit 1; }
  "${DC[@]}" sh -c "createdb -U \"\$POSTGRES_USER\" $TARGET 2>/dev/null || true"
  "${DC[@]}" sh -c "pg_restore -U \"\$POSTGRES_USER\" -d $TARGET --clean --if-exists --no-owner" < "$FILE"
fi

echo "Restauration terminée."
