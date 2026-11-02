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

Ce que ces tests ne couvrent pas, et où c'est vérifié :

- le SQL réel : `scripts/run_extractions.py` sur la base de développement (`docs/requetes.md`) ;
- le vrai Mistral : `scripts/validate_mistral.py` (`docs/services/resultats_validation_mistral.md`) ;
- la conversion des nutriments Open Food Facts : `tests/test_openfoodfacts_service.py`.

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
| `POST /auth/register` | public | 201, 409 email déjà pris, 422 mot de passe trop court | `test_endpoints.py` |
| `POST /auth/login` | public | 200, 401 mauvais mot de passe, 422 email mal formé | `test_endpoints.py` |
| `GET /auth/me` | JWT | 200, 401 sans jeton, 401 jeton expiré | `test_endpoints.py` |
| `GET /search/aliments` | public | 200, 422 terme trop court | `test_api_access.py`, `test_endpoints.py` |
| `GET /search/categories` | public | 200 | `test_endpoints.py` |
| `GET /score/aliment/{id}` | public | 200 avec disclaimer, 404, 422 | `test_endpoints.py` |
| `GET /score/code-barre/{code}` | public | 200 avec attribution OFF, 404, 503, 422 | `test_score_code_barre.py` |
| `POST /ai/chat` | JWT | 200 RAG avec sources, 200 hors périmètre, 200 détresse, 401 sans jeton, 401 jeton invalide, 401 clé d'API manquante, 422, 503 Mistral indisponible | `test_ai_endpoints.py`, `test_api_access.py`, `test_endpoints.py` |
| `POST /ai/vision` | JWT | 401, 413 image trop lourde, 415 mauvais format, 501 VLM pas encore branché | `test_api_access.py`, `test_ai_endpoints.py`, `test_endpoints.py` |

Les 11 routes de l'API sont couvertes.

**Pourquoi pas de test 403 :** 403 veut dire « connectée mais pas le droit ». Les spécifications ne
prévoient aucune route réservée à un rôle : seules les features IA demandent un compte, quel que
soit le rôle. La fonction `require_role` existe pour une future route d'administration (monitoring),
elle sera testée avec cette route.

## 4. Résultats

| Date | Commande | Résultat |
|---|---|---|
| à compléter | `uv run pytest tests -q` (CI de la PR `feat/data-api`) | à compléter (attendu : 179 passed) |

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
ChromaDB ou de Mistral (voir § 1). La couverture de code n'est pas encore mesurée.
