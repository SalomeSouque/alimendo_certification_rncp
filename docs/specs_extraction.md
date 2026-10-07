# Spécifications techniques : extraction et agrégation des données

Ce document couvre l'ensemble des moyens techniques mis en oeuvre pour extraire les données
d'Alimendo puis les rassembler dans le jeu de données final (critère C1-CR3). Il sert aussi de
tableau des sources (C1-CR7).

## 1. Deux modes d'extraction

| Mode | Sources | Principe |
|---|---|---|
| **Par script** (collecte automatisée, rejouable) | CIQUAL 2020, corpus RAG | Un script télécharge, lit, filtre et sauvegarde. Le résultat alimente PostgreSQL ou ChromaDB. |
| **À la demande** (temps réel) | Open Food Facts | Le backend interroge l'API au moment où l'utilisatrice saisit un code-barre. Rien n'est stocké. |

Le périmètre de l'extraction **par script** est donc : **corpus RAG + CIQUAL**. Toutes les données
visées par ce périmètre sont récupérées à l'exécution des scripts (C1-CR4).

## 2. Vue d'ensemble du pipeline

```
EXTRACTION PAR SCRIPT

CIQUAL 2020 (fichier .xls)    -> scripts/ciqual_clean.py      -> CSV nettoyé
                                 (téléchargement, lecture,       -> scripts/import_aliments.py
                                  conversion, rejets, rapport)   -> PostgreSQL (tables categorie, aliment)

Corpus RAG (PDF + pages HTML) -> rag/collecte.py (téléchargement)  -> rag/chunking.py -> rag/ingestion.py
                                 rag/extraction.py (parsing HTML      -> ChromaDB (index vectoriel)
                                 par trafilatura, PDF par pdfplumber)

EXTRACTION À LA DEMANDE

Code-barre saisi              -> backend/app/services/openfoodfacts_service.py
                                 (requête HTTP, filtrage des champs, conversion des unités)
                                 -> profil nutritionnel -> calcul du score (non stocké)

REQUÊTES SUR LA BASE

PostgreSQL                    -> backend/app/repositories/ (+ requêtes SQL du lot C2)
                                 -> API REST du projet
```

Le **jeu de données final** est double, par nature des données :

- données structurées (aliments et valeurs nutritionnelles) : **PostgreSQL**, alimenté par CIQUAL ;
- données documentaires (corpus du chatbot) : **ChromaDB**.

## 3. Tableau des sources

| # | Type de source (référentiel) | Source | Format / accès | Code qui la traite | Sortie |
|---|---|---|---|---|---|
| 1 | Fichier de données | CIQUAL 2020, ANSES | `.xls` téléchargé depuis data.gouv.fr | `scripts/ciqual_clean.py` | `data/ciqual/clean/*.csv` puis PostgreSQL |
| 2 | Service web (API REST) | Open Food Facts | API v2 JSON, HTTPS, à la demande | `backend/app/services/openfoodfacts_service.py` | Profil nutritionnel en mémoire |
| 3 | Scraping | Pages HTML du corpus RAG (PMC, sites associatifs) | HTML téléchargé puis parsé | `rag/collecte.py` + `rag/extraction.py` | `rag/data/processed/*.txt` |
| 4 | Base de données | PostgreSQL du projet | SQL via SQLAlchemy / psycopg | `backend/app/repositories/` (+ `sql/` du lot C2) | Réponses de l'API |
| 5 | Système big data | (aucun) | - | - | **Écarté**, voir § 6 |

## 4. Spécifications par source

### 4.1 CIQUAL 2020 (fichier)

| Élément | Spécification |
|---|---|
| Accès | URL stable data.gouv.fr, `requests`, User-Agent identifié, timeout 60 s |
| Licence | Licence Ouverte / Etalab 2.0. Citation : *Anses. 2020. Table de composition nutritionnelle des aliments Ciqual.* |
| Volume | 3 186 aliments, 76 colonnes |
| Traitement | Conversion des formats (« - » -> NULL, « traces » et « < X » -> 0), doublons, catégories, 5 règles d'entrée corrompue |
| Import | `scripts/import_aliments.py`, une transaction, relançable sans doublon (clé `code_ciqual`) |
| Documentation | `scripts/README.md` (règles et chiffres), README racine (import), notebook 03 du dépôt data science (justification) |

### 4.2 Open Food Facts (API REST, à la demande)

| Élément | Spécification |
|---|---|
| Endpoint | `GET https://world.openfoodfacts.org/api/v2/product/{code}` |
| Paramètres | `fields=code,product_name,product_name_fr,image_front_small_url,nutriments` : seuls les champs utiles sont demandés |
| Contraintes d'usage | User-Agent personnalisé obligatoire ; **15 requêtes/min** par IP pour la lecture produit (dépassement = blocage) |
| Licence | Base sous ODbL, contenus sous Database Contents License, images CC BY-SA. Attribution « Open Food Facts » obligatoire |
| Unités | Les valeurs `<nutriment>_100g` sont toutes en **grammes** : conversion vers mg ou µg selon le référentiel |
| Valeurs manquantes | Absente, non numérique ou négative -> non renseignée (None), jamais 0 |
| Glucides | Comme dans CIQUAL, les glucides de l'étiquetage UE incluent les polyols : aucune correction |
| Erreurs | Code-barre mal formé refusé avant tout appel ; 404 ou `status: 0` -> produit inconnu ; timeout, 429, 5xx -> erreur « service indisponible » |
| Configuration | `.env` : `OFF_BASE_URL`, `OFF_USER_AGENT`, `OFF_TIMEOUT_SECONDS` |
| Limite | Vitamine A en équivalent rétinol (OFF) contre rétinol (CIQUAL) ; micronutriments rarement renseignés, beaucoup de produits seront « score indisponible » |

### 4.3 Corpus RAG (fichiers documents et scraping)

Spécifié dans `rag/README.md` et piloté par `rag/corpus_manifest.csv` : chaque source porte son statut
légal (`acces`). Les pages HTML en accès intégral sont téléchargées puis le texte utile est extrait par
`trafilatura` (scraping) ; les sources protégées ne sont pas scrapées.

### 4.4 Base de données PostgreSQL

Requêtes d'extraction SQL (sélections, filtres, jointures) développées dans le lot C2 et dans
`backend/app/repositories/`. Connexion via SQLAlchemy et le pilote `psycopg`.

## 5. Pourquoi Open Food Facts est interrogé à la demande

- **Parcours utilisateur** : l'utilisatrice scanne un produit précis parmi plusieurs millions ; un
  échantillon stocké en base ne couvrirait pas ses scans.
- **Conditions d'usage** : OFF déconseille l'aspiration en lot par l'API.
- **Fraîcheur** : la composition d'un produit peut changer ; l'appel direct renvoie la version à jour.
- **Contrepartie** : l'agrégation en un jeu final porte sur CIQUAL (PostgreSQL) et le corpus RAG
  (ChromaDB). Les produits OFF passent par la même conversion d'unités que le référentiel, ce qui
  rend leur score comparable à celui des aliments CIQUAL.

## 6. Big data : écarté

Aucune source du projet n'a un volume ou une vélocité qui justifie un système big data (Hive,
Spark…) : CIQUAL compte 3 186 lignes, le corpus RAG une dizaine de documents, OFF est interrogé
produit par produit. Mettre en place un tel système ajouterait de l'infrastructure sans besoin réel.
Choix validé avec le formateur, à argumenter à l'oral.

## 7. Exécution et traçabilité

| Code | Lancement | Traces produites |
|---|---|---|
| CIQUAL | `uv run --group data python scripts/ciqual_clean.py` | log, rapport JSON (SHA-256 de la source), rejets |
| Import | `uv run --group data python scripts/import_aliments.py` | log avec comptages avant / après |
| RAG | voir `rag/README.md` | `_collecte_log.csv`, `_extraction_log.csv` |
| OFF | appelé par le backend (route code-barre, lot API) | logs applicatifs du backend |
