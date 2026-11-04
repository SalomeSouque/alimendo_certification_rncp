# Tests d'intégration de l'API

Ce document décrit les tests d'intégration des points de terminaison de l'API, la façon de les
lancer et l'interprétation de leurs résultats (critères C9-CR5, C9-CR6, C9-CR7, C17-CR9).

## 1. Principe

Chaque test appelle une route par HTTP avec le `TestClient` de FastAPI, comme le ferait le
frontend, puis vérifie le code de réponse et le contenu renvoyé.

Les dépendances extérieures sont remplacées par des doublures, pour que les tests soient
rapides, reproductibles et exécutables dans GitHub Actions sans réseau :

| Dépendance | Remplacée par | Où |
|---|---|---|
| Session PostgreSQL | `AsyncMock` injecté avec `app.dependency_overrides` | fixture `session_factice` (`tests/conftest.py`) |
| Requêtes SQL (repositories) | fonctions simulées avec `monkeypatch` | dans chaque test |
| Classifieur d'intention | `FauxModele` (renvoie toujours la même classe) | `tests/test_intent_classifier.py` |
| Embeddings, ChromaDB, Mistral | fonctions simulées, faux Mistral en `AsyncMock` | `_brancher_un_faux_rag()` (`tests/test_endpoints.py`) |
| Open Food Facts | `recuperer_produit` simulé | `tests/test_score_code_barre.py` |
| Ollama (VLM) | `httpx.MockTransport`, ou `_appeler_vlm` simulé dans les tests de route | `tests/test_vision_service.py`, `tests/test_ai_endpoints.py` |

Ce que ces tests ne couvrent pas, et où c'est vérifié :

- le SQL réel : `scripts/run_extractions.py` sur la base de développement (`docs/requetes.md`) ;
- le vrai Mistral : `scripts/validate_mistral.py` (`docs/services/resultats_validation_mistral.md`) ;
- la conversion des nutriments Open Food Facts : `tests/test_openfoodfacts_service.py`.
- le vrai VLM : `scripts/vlm_curl_test.sh` sur un jeu de photos (`docs/services/ollama.md` § 8) ;

## 2. Lancer les tests

```bash
cd backend
uv run pytest tests -q                       # toute la suite
uv run pytest tests/test_endpoints.py -v     # seulement les tests d'API, un par ligne
```

Dans GitHub Actions, le job `backend` du workflow `ci.yml` lance la même commande à chaque push et
à chaque pull request vers `develop` ou `main`.

## 3. Couverture des points de terminaison

| Route | Accès | Cas testés | Fichier |
|---|---|---|---|
| `GET /health` | public | 200 | `test_api_access.py` |
| `GET /health/detail` | public | 200 même si une dépendance manque | `test_endpoints.py` |
| `POST /auth/register` | public | 201, 409 email déjà pris, 422 mot de passe trop court, 422 sans consentement explicite | `test_endpoints.py` |
| `POST /auth/login` | public | 200, 401 mauvais mot de passe, 422 email mal formé | `test_endpoints.py` |
| `GET /auth/me` | JWT | 200, 401 sans jeton, 401 jeton expiré | `test_endpoints.py` |
| `GET /search/aliments` | public | 200, 422 terme trop court | `test_api_access.py`, `test_endpoints.py` |
| `GET /search/categories` | public | 200 | `test_endpoints.py` |
| `GET /score/aliment/{id}` | public | 200 avec disclaimer, 404, 422 | `test_endpoints.py` |
| `GET /score/code-barre/{code}` | public | 200 avec attribution OFF, 404, 503, 422 | `test_score_code_barre.py` |
| `POST /ai/chat` | JWT | 200 RAG avec sources, 200 hors périmètre, 200 détresse, 401 sans jeton, 401 jeton invalide, 401 clé d'API manquante, 422, 503 Mistral indisponible | `test_ai_endpoints.py`, `test_api_access.py`, `test_endpoints.py` |
| `POST /ai/vision` | JWT | 200 aliment reconnu avec score et disclaimer, 200 photo sans aliment unique avec message, 401, 413 image trop lourde, 415 mauvais format, 422 image illisible, 503 VLM indisponible | `test_ai_endpoints.py`, `test_api_access.py`, `test_endpoints.py` (logique du service : `test_vision_service.py`) |

Les 11 routes de l'API sont couvertes.

**Pourquoi pas de test 403 :** 403 veut dire « connectée mais pas le droit ». Les spécifications ne
prévoient aucune route réservée à un rôle : seules les features IA demandent un compte, quel que
soit le rôle. La fonction `require_role` existe pour une future route d'administration (monitoring),
elle sera testée avec cette route.

## 4. Résultats

| Date | Commande | Résultat |
|---|---|---|
| à compléter | `uv run pytest tests -q` (CI de la PR `feat/data-api`) | à compléter (attendu : 179 passed) |
| 03/11/2026 | `uv run pytest tests -q --cov` (poste de développement, après l'ajout de `test_config_ollama.py`) | ⟨ 1242 passed⟩, couverture ⟨ 84%⟩ |

## 5. Interprétation

- **Tous les tests passent** : les routes répondent avec les codes prévus par les spécifications,
  dans les cas nominaux comme dans les cas d'erreur.
- **Contrôle d'accès** : les routes IA et `/auth/me` refusent un appel sans jeton, avec un jeton
  invalide ou expiré (401). Le message « Session expirée, reconnectez-vous. » est celui que le
  frontend utilisera pour déconnecter l'utilisatrice. Les routes publiques répondent sans jeton.
- **Validation des entrées** : une entrée invalide est refusée en 422 par Pydantic avant
  d'atteindre la base ou un service externe (vérifié pour le code-barre : OFF n'est pas appelé).
- **Pannes des services externes** : Mistral ou Open Food Facts indisponible donne un 503 avec un
  message lisible, jamais une erreur 500.
- **Conformité médicale** : les réponses de score portent le disclaimer validé, les réponses du
  chatbot portent le disclaimer court et citent leurs sources. Mistral reçoit le titre de chaque
  source avec son extrait, pour pouvoir la citer comme le demande le prompt.

**Limites :** les doublures vérifient le contrat HTTP, pas le comportement réel de PostgreSQL, de
ChromaDB ou de Mistral (voir § 1). La couverture de code est mesurée au § 6.

## 6. Couverture de code

La couverture est mesurée avec `pytest-cov` (dépendance du groupe `dev`). La configuration est dans
`backend/pyproject.toml`, section `[tool.coverage]`.

```bash
cd backend
uv run pytest tests -q --cov                          # tableau dans le terminal, avec les lignes manquantes
uv run pytest tests -q --cov --cov-report=html        # rapport détaillé dans backend/htmlcov/index.html
```

**Périmètre mesuré :** tout le paquet `app`, sauf les migrations Alembic (`app/migrations/`). Les
migrations sont des scripts de schéma exécutés une seule fois par `alembic upgrade`, contre une vraie
base PostgreSQL. Les compter ferait baisser le chiffre sans rien dire de la qualité du code
applicatif. Elles sont vérifiées par leur exécution réelle (`docs/acces_base.md`).

| Date | Lignes mesurées | Couverture totale | Sans exclusion des migrations |
|---|---|---|---|
| 03/11/2026 | 1242 | 84% | 78% |

**Interprétation :**

- **Bien couvert (85 % et plus)** : la logique métier du score (`app/domain/score/`,
  `score_service.py`), la sécurité (`core/security.py`), les routes (`app/routers/`), les schémas
  et le client Open Food Facts. C'est là que se trouvent les règles du référentiel et le contrôle d'accès, les
  parties dont une erreur aurait le plus de conséquences.
- **Moins couvert** : les repositories (`aliment_repository.py`, `user_repository.py`,
  `log_vlm_repository.py`), `chroma_service.py`, `embedding_service.py` et
  `alternative_service.py`. C'est un choix assumé, pas un oubli : ces modules parlent à PostgreSQL,
  ChromaDB ou au modèle d'embeddings, que les tests d'API remplacent par des doublures (§ 1). Leurs
  requêtes sont vérifiées contre la vraie base par `scripts/run_extractions.py` (`docs/requetes.md`).
- **`vision_service.py`** était couvert à 54 % quand la route renvoyait encore 501. Avec le
  branchement du VLM et `test_vision_service.py` (reconnu, non reconnu, image invalide, service
  indisponible), il passe à XX %.
- **`core/logging_config.py`** : les motifs de masquage des secrets dans les logs ne sont pas testés
  directement (le test `test_les_logs_ne_contiennent_ni_cle_ni_question` vérifie seulement que le
  client Mistral n'écrit pas la clé). Piste d'amélioration : un test unitaire de ces motifs.

Le chiffre global n'est pas un objectif en soi : une couverture élevée sur des doublures ne prouve
pas que le SQL réel fonctionne. Il sert à repérer les zones jamais exécutées par les tests.