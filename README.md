# Certification RNCP37827 projet Alimendo
Application web d'aide aux choix alimentaires pour les personnes atteintes
d'endométriose : score d'inflammation par photo, code-barre ou recherche
textuelle, et chatbot documentaire sourcé.

> **Projet étudiant.** Cette application est réalisée dans le cadre d'un projet
> de fin d'études. Elle ne délivre aucun conseil médical et ne remplace pas
> l'avis d'un professionnel de santé.

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose v2
  (inclus dans Docker Desktop)

Aucune autre installation n'est nécessaire : Python, Node et PostgreSQL
tournent dans des conteneurs.

## Démarrage

```bash
git clone <url>
cd certification_RNCP_37827
cp .env.example .env
docker compose up -d
```

Vérifier que les services sont démarrés :

```bash
docker compose ps
```

Le service `db` doit passer en `healthy` après une dizaine de secondes.

### Configuration

Toutes les variables sont documentées dans `.env.example`. Le fichier `.env`
n'est jamais versionné : il contient les identifiants et les clés d'API.

Les ports hôte sont configurables — utile si un service occupe déjà le port
par défaut sur votre machine :

```bash
POSTGRES_PORT=5434
```

## Services

| Service    | Rôle                          | Port hôte (défaut) | Profil |
|------------|-------------------------------|--------------------|--------|
| `db`       | PostgreSQL — données métier    | 5432               | —      |
| `chromadb` | Base vectorielle — corpus RAG  | 8001               | —      |
| `api`      | Backend FastAPI                | 8000               | `app`  |
| `frontend` | Frontend React                 | 3000               | `app`  |
| `ollama`   | Inférence VLM locale (Qwen)    | 11434              | `ai`   |

Les services sans profil démarrent avec `docker compose up`. Les autres
doivent être demandés explicitement :

```bash
docker compose --profile app up -d    # + api et frontend
docker compose --profile ai up -d     # + ollama
```

**Note :** les services `api`, `frontend` et `ollama` sont déclarés mais ne
peuvent pas encore démarrer — leurs Dockerfiles seront ajoutés en S3–S4.

## Architecture

Aucun appel direct depuis le frontend vers la base de données ou les services
d'IA : tout transite par le backend.

```
Navigateur → frontend (React)
           → api (FastAPI)
               ├── db        PostgreSQL — aliments, scores, signaux
               ├── chromadb  recherche sémantique dans le corpus
               ├── ollama    reconnaissance d'aliment par photo
               └── APIs externes (Open Food Facts, OpenRouter)
```

Les conteneurs communiquent entre eux par leur **nom de service** sur le
réseau interne créé par Compose, sur leur port interne : le backend joint la
base à `db:5432`, quel que soit le port publié sur la machine hôte. Les ports
déclarés dans `docker-compose.yml` ne servent qu'à l'accès depuis la machine
de développement.

## Commandes utiles

```bash
docker compose config          # valide le fichier et affiche la config résolue
docker compose logs -f db      # suit les logs d'un service
docker compose exec db psql -U alimendo   # ouvre un client SQL
docker compose down            # arrête et supprime les conteneurs
```

> `docker compose down -v` supprime également les volumes, donc **toutes les
> données** : base PostgreSQL, corpus vectoriel et modèles Ollama téléchargés.

## Tests

À venir — S3 pour les composants métier, S5 pour le classificateur d'intention.

## Stack

React · FastAPI · PostgreSQL · ChromaDB · Qwen2.5-VL via Ollama ·
DeepSeek R1 via OpenRouter · Docker Compose · GitHub Actions

