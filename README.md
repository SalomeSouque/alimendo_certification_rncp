# Alimendo

> **Projet étudiant à but pédagogique**, réalisé dans le cadre de la certification
> *Développeur en intelligence artificielle* (RNCP37827). Ce service n'a pas vocation
> à être utilisé comme outil de santé et ne remplace en aucun cas l'avis d'un
> professionnel. Aucun régime alimentaire spécifique ne peut à ce jour être
> recommandé dans l'endométriose.

Alimendo est une application web destinée aux personnes atteintes d'endométriose.
Elle attribue à chaque aliment un **score d'inflammation indicatif**, inspiré du
*Dietary Inflammatory Index* (Shivappa et al., 2014), et met à disposition un
**chatbot documentaire (RAG)** qui répond uniquement à partir d'un corpus restreint
de sources sélectionnées.

## Stack technique

| Couche | Technologie |
|---|---|
| Frontend | React (Vite), servi par nginx en conteneur |
| Backend | FastAPI, Python ≥ 3.13, gestion des dépendances avec `uv` |
| Base de données | PostgreSQL 17 (extension `pg_trgm` pour la recherche floue) |
| ORM / migrations | SQLAlchemy 2.0 (async, driver psycopg 3) + Alembic |
| Base vectorielle | ChromaDB 1.5.9 (service conteneurisé, accès HTTP) |
| Embeddings | `intfloat/multilingual-e5-base` |
| LLM (chatbot RAG) | Mistral Small (`mistral-small-2603`), via l'API Mistral |
| Routage d'intention | Classifieur scikit-learn (TF-IDF + régression logistique), 5 classes, avec filet de sécurité déterministe |
| Qualité | `ruff`, `pytest`, CI GitHub Actions (frontend + backend) |

**Prochaine étape (non branchée) :** reconnaissance d'aliments par photo via un
VLM Qwen3-VL 4B servi par Ollama (service `ollama`, profil `ai`).

## Architecture du backend

Quatre couches, des routes vers le domaine métier pur :

```
routers -> services -> repositories -> domain
```

Le SQL reste dans les `repositories` ; le `domain` (calcul du score, badges) ne
dépend ni de la base, ni du réseau, ni de FastAPI, ce qui le rend testable sans
infrastructure. Le score est **recalculé à la volée et jamais stocké** : seule
la règle (référentiel v1.0) est figée, et chaque réponse expose
`version_referentiel`. Toutes les formulations à caractère médical sont
centralisées dans `app/core/disclaimers.py` (transcription littérale des
guidelines) et ne sont jamais générées par le code ni par le LLM.

## Prérequis

- Docker et Docker Compose
- (optionnel, pour travailler le backend hors conteneur) `uv`

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/SalomeSouque/alimendo_certification_rncp.git
cd alimendo_certification_rncp

# 2. Créer le fichier d'environnement et le compléter
cp .env.example .env
#   Renseigner au minimum : JWT_SECRET_KEY (chaîne longue et aléatoire)
#                           MISTRAL_API_KEY

# 3. Construire et démarrer la stack applicative
#     Le profil « app » est nécessaire : sans lui, seuls db et chromadb
#    démarrent (api et frontend sont sous profils).
docker compose --profile app up --build -d

# 4. Appliquer les migrations (création du schéma dans PostgreSQL)
docker compose exec api uv run alembic upgrade head
```

Services disponibles une fois la stack démarrée :

| Service | URL par défaut |
|---|---|
| API (FastAPI) | http://localhost:8000 — documentation : http://localhost:8000/docs |
| Santé détaillée | http://localhost:8000/health/detail |
| Frontend | http://localhost:3000 |

## Migrations de base de données

```bash
# Appliquer les migrations
docker compose exec api uv run alembic upgrade head

# Générer une nouvelle migration après modification des modèles ORM
docker compose exec api uv run alembic revision --autogenerate -m "description"

# Vérifier la réversibilité (down puis up)
docker compose exec api uv run alembic downgrade base
docker compose exec api uv run alembic upgrade head
```

## Import des données

Remplit PostgreSQL (tables `categorie` et `aliment`) avec la table CIQUAL 2020 nettoyée.
Les spécifications de toutes les sources sont dans [`docs/specs_extraction.md`](docs/specs_extraction.md),
le détail des règles de nettoyage dans [`scripts/README.md`](scripts/README.md).

### Prérequis

| Élément | Détail |
|---|---|
| Python | 3.13 ou plus (`.python-version`) |
| Gestionnaire | [`uv`](https://docs.astral.sh/uv/) |
| Bibliothèques | groupe `data` du `pyproject.toml` racine : `pandas`, `numpy`, `xlrd`, `openpyxl`, `requests` ; dépendances principales : `sqlalchemy`, `psycopg`, `python-dotenv` |
| Base | service `db` du `docker-compose.yml` démarré, migrations appliquées jusqu'à `0002` |
| Configuration | fichier `.env` à la racine : `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` |
| Réseau | accès à data.gouv.fr (téléchargement de CIQUAL au premier lancement) |

### Commandes

Depuis la racine du dépôt :

```bash
# 1. Installer les dépendances des scripts
uv sync --group data --group dev

# 2. Démarrer la stack et appliquer les migrations (jusqu'à 0002)
docker compose --profile app up -d --build   # --build : embarque la migration 0002
docker compose exec api uv run alembic upgrade head

# 3. Produire le jeu nettoyé (télécharge CIQUAL si absent)
uv run --group data python scripts/ciqual_clean.py

# 4. Importer dans PostgreSQL (relançable sans créer de doublon)
uv run --group data python scripts/import_aliments.py

# 5. Vérifier les comptages (utilisateur et base du .env)
docker compose exec db psql -U alimendo -d alimendo -c "SELECT count(*) FROM aliment;"
```

| Option de `import_aliments.py` | Défaut | Effet |
|---|---|---|
| `--csv` | `data/ciqual/clean/aliments_ciqual_2020_clean.csv` | Fichier à importer |
| `--host` | `localhost` | Hôte PostgreSQL vu depuis ta machine |
| `--port` | `POSTGRES_PORT` du `.env` | Port publié par Docker |

**Fonctionnement** : une seule transaction (en cas d'erreur, rien n'est écrit) ; catégories insérées
avant les aliments (clé étrangère) ; aliments insérés ou mis à jour selon `code_ciqual`
(`INSERT ... ON CONFLICT DO UPDATE`), donc une relance ne crée aucun doublon. Le log affiche les
comptages avant et après. Codes de sortie : `0` succès, `1` erreur (CSV absent ou invalide, base
injoignable, migration manquante).

Résultat attendu sur CIQUAL 2020 : **3 184 aliments** et **11 catégories**.

### Open Food Facts

Open Food Facts n'est pas importé : le backend interroge l'API à la demande, par code-barre
(`backend/app/services/openfoodfacts_service.py`). Voir [`docs/specs_extraction.md`](docs/specs_extraction.md), § 5.

## Tests et qualité

```bash
# Lint (depuis backend/, sans installer tout le projet)
uvx ruff check

# Tests dans le conteneur
docker compose exec api uv run pytest -q

# ou en local (backend/), si l'environnement uv est synchronisé
uv run pytest -q
```

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute lint + tests pour le
frontend et le backend à chaque push et pull request. Les tests du backend
portent sur le domaine métier pur (score, badges), le routage d'intention à 5
classes, la conformité des formulations médicales et le contrôle d'accès — aucun
ne nécessite de base de données.

## Variables d'environnement

Toutes les variables sont décrites dans `.env.example`. Les principales :

| Variable | Rôle |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Accès PostgreSQL |
| `POSTGRES_PORT` | Port **hôte** de PostgreSQL (le conteneur reste sur 5432) |
| `JWT_SECRET_KEY` | Clé de signature des jetons JWT (secret, jamais commité) |
| `MISTRAL_API_KEY` | Clé de l'API Mistral (chatbot RAG) |
| `BCRYPT_ROUNDS` | Coût du hachage bcrypt |
| `CHROMADB_PORT`, `FRONTEND_PORT`, `FASTAPI_PORT`, `OLLAMA_PORT` | Ports hôte des services |

Aucun secret ne doit figurer dans le code ou les commits : seul `.env.example`
(sans valeurs sensibles) est versionné.

## Dépannage

**`docker compose up` ne démarre que `db` et `chromadb`.** C'est normal : `api`
et `frontend` sont sous le profil `app`. Utilise `docker compose --profile app up`.

**`[Errno 98] address already in use` sur le port 8000.** Le conteneur `api`
occupe déjà ce port. Inutile de lancer `uvicorn` en local en plus — l'API tourne
dans Docker. Pour un `uvicorn` local, arrête d'abord la stack ou choisis un autre
port (`--port 8010`).

**`Bind for 0.0.0.0:5432 failed: port is already allocated`.** Un autre
PostgreSQL (autre projet) occupe le port. Change `POSTGRES_PORT` dans `.env` ; le
port interne du conteneur, lui, reste 5432.

**`psql: role "root" does not exist`.** Les variables `$POSTGRES_USER` /
`$POSTGRES_DB` doivent être évaluées **dans** le conteneur, pas dans ton shell :

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

## Sources et références

- Score : approche inspirée du *Dietary Inflammatory Index* (Shivappa N. et al.,
  *Public Health Nutrition*, 2014). Les coefficients officiels du DII étant
  propriétaires, ce score n'en est pas une reproduction.
- Données de composition : table **CIQUAL 2020** (ANSES) et base **Open Food Facts**.
- Badges nutritionnels fer et magnésium : seuils du Règlement **UE 1169/2011**
  (annexe XIII).
