#!/usr/bin/env bash
# Déploie une version d'Alimendo sur le serveur, ou revient à une version précédente.
#
# Usage (depuis n'importe où, sur le serveur) :
#   ./deploy/deploy.sh sha-1a2b3c4   # image publiée par la CD pour ce commit
#   ./deploy/deploy.sh develop       # dernière image de la branche develop
#   ./deploy/deploy.sh local         # construit les images sur le serveur (avant la CD)
#   ./deploy/deploy.sh "$(cat ~/.alimendo-deploy/previous)"   # retour arrière
#
# Étapes : récupération (ou build) des images -> redémarrage -> migrations -> attente
# du healthcheck de l'API -> mémorisation de la version dans .env et dans l'historique.
# Pendant le redémarrage, la page de maintenance prend le relais toute seule.
#
# ATTENTION retour arrière : revenir à des images plus anciennes ne défait pas une
# migration. Si la version annulée contenait une migration, lancer d'abord
# `alembic downgrade <révision>` AVEC la version récente encore en place.

set -euo pipefail

TAG="${1:?usage : deploy/deploy.sh <tag>  (ex. sha-1a2b3c4, develop, local)}"
# Le tag finit dans .env et dans des noms d'image : on n'accepte que des caractères sûrs.
if [[ ! "$TAG" =~ ^[A-Za-z0-9._-]{1,64}$ ]]; then
  echo "Tag refusé : '$TAG'" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
[[ -f .env ]] || { echo "Fichier .env absent (cp .env.prod.example .env)" >&2; exit 1; }

COMPOSE=(docker compose -f docker-compose.prod.yml --profile app)
STATE_DIR="${HOME}/.alimendo-deploy"
mkdir -p "$STATE_DIR"
CURRENT="$(cat "$STATE_DIR/current" 2>/dev/null || echo aucune)"

echo "==> Déploiement de '$TAG' (version actuelle : $CURRENT)"
export IMAGE_TAG="$TAG"

if [[ "$TAG" == "local" ]]; then
  "${COMPOSE[@]}" build api frontend
else
  "${COMPOSE[@]}" pull api frontend
fi

"${COMPOSE[@]}" up -d --remove-orphans

echo "==> Migrations"
"${COMPOSE[@]}" exec -T api uv run alembic upgrade head

echo "==> Attente du healthcheck de l'API (90 s max)"
API_ID="$("${COMPOSE[@]}" ps -q api)"
for _ in $(seq 1 30); do
  STATUS="$(docker inspect -f '{{.State.Health.Status}}' "$API_ID" 2>/dev/null || echo inconnu)"
  [[ "$STATUS" == "healthy" ]] && break
  sleep 3
done
if [[ "$STATUS" != "healthy" ]]; then
  echo "L'API n'est pas saine (état : $STATUS). Logs : docker compose -f docker-compose.prod.yml logs api" >&2
  echo "Retour arrière possible : ./deploy/deploy.sh $CURRENT" >&2
  exit 1
fi

# La version déployée devient celle par défaut : un `up -d` manuel ne change pas de version.
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${TAG}/" .env
[[ "$CURRENT" != "aucune" && "$CURRENT" != "$TAG" ]] && echo "$CURRENT" > "$STATE_DIR/previous"
echo "$TAG" > "$STATE_DIR/current"
echo "$(date -Iseconds) $TAG (avant : $CURRENT)" >> "$STATE_DIR/history.log"

echo "==> OK : '$TAG' en ligne."
