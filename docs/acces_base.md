# Accès direct à la base de données

Ce document explique comment accéder à la base PostgreSQL sans passer par l'API (critère C5) :
pour les scripts de données, l'analyse ou un outil comme DBeaver. Les composants de
l'application, eux, passent toujours par l'API.

## 1. Environnement

| Élément | Valeur |
|---|---|
| SGBD | PostgreSQL 17 (image `postgres:17-alpine`), service `db` du `docker-compose.yml` |
| Base | `POSTGRES_DB` du `.env` (`alimendo` par défaut) |
| Extension | `pg_trgm` (recherche tolérante aux fautes), posée par la migration 001 |
| Schéma | créé et versionné par Alembic (`backend/app/migrations/`), modèle physique en annexe du rapport E1 |
| Exposition | port lié à `127.0.0.1` seulement : la base n'est pas joignable depuis le réseau |

## 2. Adresse de connexion selon l'endroit

| Depuis | Hôte | Port |
|---|---|---|
| le backend, dans Docker | `db` | `5432` |
| la machine hôte (scripts, DBeaver, psql) | `localhost` | `POSTGRES_PORT` du `.env` (`5433` par défaut) |

## 3. Les deux comptes

| Compte | Droits | Usage |
|---|---|---|
| `POSTGRES_USER` du `.env` | tous les droits | le backend, Alembic, le script d'import |
| `alimendo_lecture` | lecture seule sur `aliment`, `categorie`, `log_vlm` | consultation, analyse, captures |

Le compte en lecture seule ne voit pas les tables `utilisateur` et `role` : les données
personnelles ne sortent que par l'API, derrière le JWT (RGPD, minimisation des accès).

## 4. Créer le compte en lecture seule

Une seule fois, base démarrée et migrations appliquées, depuis la racine du dépôt :

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v mdp_lecture="CHOISIR_UN_MOT_DE_PASSE"' < sql/role_lecture.sql
```

Le mot de passe n'est écrit ni dans le dépôt ni dans le `.env` versionné.

## 5. Se connecter

**psql dans le conteneur :**

```bash
docker compose exec db psql -U alimendo_lecture -d alimendo
```

**DBeaver (ou tout client PostgreSQL) :** nouvelle connexion PostgreSQL, hôte `localhost`, port
`POSTGRES_PORT`, base `alimendo`, utilisateur `alimendo_lecture`.

**Python :** les scripts de `scripts/` lisent la connexion dans le `.env`. Pour une requête
d'extraction, `scripts/run_extractions.py` ouvre aussi la connexion en lecture seule
(voir [`requetes.md`](requetes.md)).

## 6. Vérifier les droits

```sql
SELECT count(*) FROM aliment;   -- autorisé : renvoie le nombre d'aliments
SELECT * FROM utilisateur;      -- refusé : permission denied for table utilisateur
DELETE FROM aliment;            -- refusé : cannot execute DELETE in a read-only transaction
```
