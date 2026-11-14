# Déploiement d'Alimendo

Ce document décrit comment Alimendo est mis en ligne, mis à jour, ramené à une version
précédente et sauvegardé (critères C15 et C19). Les valeurs marquées `À COMPLÉTER` sont
relevées sur le serveur. Le dépôt étant public, ce document ne contient ni adresse IP, ni
nom d'utilisateur, ni valeur de secret.

## 1. Vue d'ensemble

Alimendo tourne sur un serveur Linux fourni par un hébergeur, derrière son reverse proxy
Traefik, qui gère le HTTPS. Pour la certification, cet environnement sert de
**pré-production** (C15-CR4).

```
Internet ──HTTPS──► Traefik (hébergeur)
                      ├── /api/...          ──► api (FastAPI) ──► db (PostgreSQL)
                      │   préfixe retiré                      ├──► chromadb
                      │                                       ├──► Mistral (API externe)
                      │                                       └──► Open Food Facts (API externe)
                      ├── /                 ──► frontend (nginx, bundle React)
                      └── tout le reste,    ──► maintenance (nginx, page 503)
                          ou app arrêtée
```

| Élément | Valeur |
|---|---|
| URL publique | `https://DOMAINE` (À COMPLÉTER) |
| API | `https://DOMAINE/api/...` |
| Fichier compose | `docker-compose.prod.yml` |
| Configuration | `.env` sur le serveur, créé à partir de `.env.prod.example` |
| Images | `ghcr.io/salomesouque/alimendo-api` et `alimendo-frontend`, tag `sha-<commit>` |

Choix de structure :

- **Deux réseaux Docker.** `db`, `chromadb` et `ollama` ne sont que sur le réseau privé
  `internal` : ni Traefik ni les autres projets du serveur ne les voient. `api` est sur les
  deux réseaux, `frontend` et `maintenance` seulement sur celui de Traefik.
- **Aucun port public.** Seuls PostgreSQL et ChromaDB publient un port, sur la boucle locale
  du serveur (`127.0.0.1`), pour les sauvegardes et l'import par tunnel SSH.
- **Page de maintenance de repli.** Elle tourne en permanence avec une priorité Traefik
  minimale : elle ne répond que si l'application est arrêtée ou en cours de redémarrage.
- **Réglages de production** : `/docs` désactivé (`ENVIRONMENT=prod`), CORS limité au
  domaine, requêtes de plus de 6 Mo coupées par Traefik, `/api/health/detail` non routé
  publiquement, rotation des logs Docker (3 fichiers de 10 Mo par conteneur).

## 2. Rôles

| Qui | Responsabilité |
|---|---|
| Hébergeur | Serveur, OS, Docker, Traefik (configuration globale, certificats), DNS, pare-feu |
| Moi | Fichiers de déploiement, conteneurs Alimendo, données, sauvegardes, comptes |

La configuration Traefik de l'hébergeur n'est jamais modifiée : Alimendo ne déclare ses
routes que par les labels de ses propres conteneurs.

## 3. Prérequis du serveur

Relevés du 14/11/2026 (date) :

| Ressource | Valeur |
|---|---|
| OS / noyau | Debian GNU/Linux 12 (bookworm) 6.1.0-54-amd64 |
| CPU | Intel(R) Xeon(R) CPU           X5570  @ 2.93GHz |
| RAM | 15Gi |
| Disque libre (racine Docker) | 35G |
| GPU | pas de GPU |
| Docker / Compose | 27.3.1 / Docker Compose version v2.29.7 |
| Traefik : réseau, entrypoint HTTPS, certresolver | fournis par l'hébergeur, renseignés dans le `.env` |

Mon utilisateur appartient au groupe `docker` (nécessaire au cron de sauvegarde).

## 4. Premier déploiement

Toutes les commandes se lancent à la racine du dépôt cloné sur le serveur. Raccourci utilisé :

```bash
DC="docker compose -f docker-compose.prod.yml"
```

**1. Configuration.**

```bash
cp .env.prod.example .env && chmod 600 .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" .env
sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" .env
vi .env                                   # clé Mistral de prod, domaine, noms Traefik, CORS
grep -n CHANGE_ME .env || echo "plus aucun CHANGE_ME"
$DC config --quiet && echo "compose OK"
```

Le mot de passe PostgreSQL n'est pris en compte qu'à la création du volume : il doit être
défini avant le premier démarrage.

**2. Page de maintenance, puis application.**

```bash
$DC up -d maintenance
./deploy/deploy.sh local          # avant la première publication sur GHCR : build sur le serveur
```

`deploy.sh` démarre la base et ChromaDB, applique les migrations (`alembic upgrade head`),
attend que l'API soit saine, puis enregistre la version déployée.

**3. Données.** Les scripts d'import tournent depuis un poste de développement, à travers un
tunnel SSH vers les ports locaux du serveur : le serveur n'a besoin ni d'`uv`, ni des
bibliothèques de données, ni du modèle d'embeddings.

```bash
# Poste de développement, terminal 1 : tunnel, laissé ouvert
ssh -N -L 15433:127.0.0.1:5433 -L 18001:127.0.0.1:8001 UTILISATEUR@SERVEUR

# Poste de développement, terminal 2, à la racine du dépôt
 POSTGRES_USER=alimendo POSTGRES_DB=alimendo POSTGRES_PASSWORD='MOT_DE_PASSE_PROD' \
  uv run --group data python scripts/import_aliments.py --host localhost --port 15433
CHROMA_HOST=localhost CHROMA_PORT=18001 uv run --group ingestion python rag/ingestion.py
```

Résultat attendu : 3 184 aliments, 11 catégories, et une réponse avec sources à une question
de test sur le chatbot.

**4. Vérifications.**

```bash
curl -s https://DOMAINE/api/health                                              # 200
curl -s -o /dev/null -w '%{http_code}\n' https://DOMAINE/api/docs               # 404
curl -s -o /dev/null -w '%{http_code}\n' https://DOMAINE/api/health/detail      # 503
```

Test de la limite de taille (attendu : 413) :

```bash
head -c 7000000 /dev/zero > /tmp/gros.bin
curl -s -o /dev/null -w '%{http_code}\n' -F "image=@/tmp/gros.bin" https://DOMAINE/api/ai/vision
rm /tmp/gros.bin
```

Premier déploiement réalisé le À COMPLÉTER.

## 5. Mise à jour

À chaque push sur `develop` ou `main`, une fois le lint et les tests passés, GitHub Actions
publie les deux images sur GHCR avec le tag `sha-<7 premiers caractères du commit>`
(`.github/workflows/cd.yml`, appelé par `ci.yml`). Une pull request teste le code mais ne
publie rien. Les packages GHCR sont publics : le serveur les télécharge sans authentification.

```bash
git pull                              # fichiers de déploiement à jour
./deploy/deploy.sh sha-XXXXXXX        # tag visible sur la page du package GHCR
```

Pendant le redémarrage, la page de maintenance prend le relais quelques secondes. Le
déploiement automatique sur le serveur n'est pas en place : il dépend d'un accès SSH à
convenir avec l'hébergeur.

Première mise à jour avec migration (lot 36, migration 0004) : À COMPLÉTER (date, tag).

## 6. Retour arrière

```bash
cat ~/.alimendo-deploy/history.log                         # versions déployées
./deploy/deploy.sh "$(cat ~/.alimendo-deploy/previous)"     # version précédente
```

Limite : revenir à des images plus anciennes ne défait pas une migration. Si la version
annulée contenait une migration incompatible avec l'ancien code, il faut lancer
`alembic downgrade <révision>` **avant** le retour arrière, avec la version récente encore en
place. La migration 0004 (colonne `acces_ia`) est compatible : l'ancien code ignore la colonne.

Retour arrière testé le À COMPLÉTER (de `sha-…` vers `sha-…` puis retour) : À COMPLÉTER.

## 7. Sauvegarde et restauration

| Élément | Choix |
|---|---|
| Outil | `pg_dump` au format custom (`deploy/backup_db.sh`) |
| Fréquence | Tous les jours à 3 h 15 (cron de mon utilisateur) |
| Rétention | 7 jours, les dumps plus anciens sont supprimés par le script |
| Emplacement | `~/backups/alimendo/`, lisible par mon utilisateur seulement (les dumps contiennent des emails et des empreintes de mots de passe) |
| Journal | `~/backups/alimendo/backup.log` |
| Copie hors du serveur | À COMPLÉTER (réponse de l'hébergeur) |

```
15 3 * * * /CHEMIN/DU/DEPOT/deploy/backup_db.sh >> $HOME/backups/alimendo/backup.log 2>&1
```

ChromaDB n'est pas sauvegardé : son contenu se reconstruit à l'identique avec l'ingestion
(§ 4, étape 3).

**Test de restauration**, dans une base temporaire, sans toucher à la production :

```bash
./deploy/backup_db.sh
./deploy/restore_db.sh ~/backups/alimendo/alimendo_AAAAMMJJ_HHMMSS.dump alimendo_restore_test
$DC exec db sh -c 'psql -U "$POSTGRES_USER" -d alimendo_restore_test -tc "SELECT count(*) FROM aliment;"'
$DC exec db sh -c 'dropdb -U "$POSTGRES_USER" alimendo_restore_test'
```

Restauration testée le À COMPLÉTER : À COMPLÉTER aliments retrouvés.

Restaurer la production (avec confirmation) : `./deploy/restore_db.sh <fichier.dump>`.

## 8. Gestion des comptes

L'accès aux outils IA est ouvert compte par compte par une admin, depuis la page `/admin` du
site ou avec le script d'administration :

```bash
$DC exec api python -m app.cli lister
$DC exec api python -m app.cli promouvoir-admin EMAIL     # rôle admin + accès IA
$DC exec api python -m app.cli ouvrir-ia EMAIL
$DC exec api python -m app.cli fermer-ia EMAIL            # effet immédiat
```

Le script ne sait pas encore retirer le rôle admin ni supprimer un compte. Suppression en SQL :

```bash
$DC exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM utilisateur WHERE email = '\''EMAIL'\'';"'
```

Le détail de l'état de l'application, non routé publiquement, se lit depuis le serveur :

```bash
$DC exec api python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health/detail').read().decode())"
```

## 9. Page de maintenance

Avant l'ouverture publique, le domaine ne doit afficher que la page de maintenance.
`deploy.sh` redémarre toujours l'application : après chaque déploiement de test, on l'arrête.

```bash
$DC --profile app stop api frontend          # le domaine répond 503
$DC --profile app start api frontend         # l'application reprend la main
```

La base et ChromaDB continuent de tourner, les sauvegardes aussi.

## 10. Secrets

| Secret | Où il vit | Comment le régénérer | Effet d'un changement |
|---|---|---|---|
| `POSTGRES_PASSWORD` | `.env` du serveur + gestionnaire de mots de passe | `openssl rand -hex 24` | Pris en compte seulement à la création du volume : un changement demande `ALTER USER` dans PostgreSQL |
| `JWT_SECRET_KEY` | `.env` du serveur + gestionnaire | `openssl rand -hex 32` | Toutes les sessions sont déconnectées |
| `MISTRAL_API_KEY` | `.env` du serveur ; clé dédiée à la production, avec plafond de dépense | Console Mistral | Aucun, après redéploiement |
| Mot de passe du compte admin | Gestionnaire de mots de passe | Changement par le site | — |

Le `.env` du serveur a les droits `600`. Aucun secret n'est dans le dépôt, ni dans les images.

## 11. Dépannage

**Le site répond 504 Gateway Timeout.** Traefik n'arrive pas à joindre le conteneur : le nom
du réseau dans `TRAEFIK_NETWORK` est probablement faux. Vérifier avec `docker network ls`.

**La page de maintenance s'affiche sans logo ni trait jaune.** Diagnostic :

```bash
curl -sI https://DOMAINE/_maintenance/Logo.svg | grep -iE '^HTTP|content-type'
$DC exec maintenance ls -l /usr/share/nginx/maintenance-assets/
```

Si le dossier est vide dans le conteneur, le montage a été créé avant que le dossier existe sur
le serveur : `$DC up -d --force-recreate maintenance`. Si le serveur renvoie bien l'image,
c'est le cache du navigateur : rechargement forcé.

**`deploy.sh` échoue au `pull` avec `unauthorized` ou `denied`.** Les packages GHCR ne sont pas
publics (premier build) : les passer en public depuis GitHub (Package settings).

**L'import par tunnel échoue à la connexion.** Vérifier que le terminal du tunnel est toujours
ouvert, et que `POSTGRES_PASSWORD` passé en ligne de commande est bien celui de production.

**Un `git switch` ou un `git pull` refuse d'écraser des fichiers.** Sur le serveur, le dépôt ne
doit jamais être modifié à la main : supprimer ou restaurer les fichiers signalés, puis
relancer la commande.