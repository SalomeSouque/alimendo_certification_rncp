# Documentation de l'API REST

Ce document complète la spécification OpenAPI générée par FastAPI (critères C5-CR1, C5-CR2,
C5-CR3). La référence complète des routes, des paramètres et des schémas de réponse est dans
[`openapi.json`](openapi.json).

## 1. Où lire la documentation

| Support | Accès | Quand |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | en développement (`ENVIRONMENT=local`), désactivé ailleurs : il expose la carte complète de l'API |
| Fichier OpenAPI 3.1 | [`docs/openapi.json`](openapi.json) | toujours, versionné dans Git, lisible dans [Swagger Editor](https://editor.swagger.io) |

Le fichier se régénère après chaque changement de route ou de schéma :

```bash
# Depuis backend/, sans base ni service démarré
uv run python ../scripts/export_openapi.py
```

## 2. Points de terminaison

| Méthode | Route | Accès | Rôle | Données servies |
|---|---|---|---|---|
| GET | `/health` | public | Sonde de vivacité | |
| GET | `/health/detail` | public | État de chaque dépendance | |
| POST | `/auth/register` | public | Créer un compte, renvoie un jeton. Corps : `email`, `password` (8 caractères min.), `consentement: true` obligatoire | table `utilisateur` |
| POST | `/auth/login` | public | Se connecter, renvoie un jeton | |
| GET | `/auth/me` | JWT | Utilisatrice du jeton | table `utilisateur` |
| GET | `/search/aliments?q=` | public | Recherche tolérante aux fautes | CIQUAL (table `aliment`) |
| GET | `/search/categories` | public | Liste des catégories | table `categorie` |
| GET | `/score/aliment/{id}` | public | Score, badges et alternatives | CIQUAL + référentiel de score |
| GET | `/score/code-barre/{code}` | public | Score d'un produit scanné | API Open Food Facts, à la demande |
| POST | `/ai/chat` | JWT | Chatbot RAG | corpus RAG (ChromaDB) + Mistral |
| POST | `/ai/vision` | JWT | Reconnaissance photo, puis score de l'aliment reconnu | VLM Qwen3-VL (Ollama, local) + CIQUAL + référentiel de score |

## 3. Règles d'authentification et d'autorisation

**Périmètre.** Les données aliments sont des données ouvertes (CIQUAL, Open Food Facts) : leur
consultation est publique, sans compte. Seules les features IA et les données de l'utilisatrice
(`/auth/me`) demandent une authentification.

**Obtenir un jeton.** `POST /auth/login` (ou `/auth/register`) renvoie :

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer", "user": { "id": 1, "email": "lea@example.com", "role": "user" } }
```

**Utiliser le jeton.** Chaque appel à une route protégée porte l'en-tête :

```
Authorization: Bearer eyJhbGciOi...
```

| Règle | Valeur | Configuration |
|---|---|---|
| Format du jeton | JWT signé HS256, contient `sub` (id), `email`, `role`, `exp` | `JWT_ALGORITHM` |
| Durée de validité | 60 minutes, pas de renouvellement automatique : l'utilisatrice se reconnecte | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Clé de signature | secrète, jamais dans le code | `JWT_SECRET_KEY` (`.env`) |
| Mots de passe | hachés avec bcrypt, 8 caractères minimum | `BCRYPT_ROUNDS` |
| Garde-fou supplémentaire | en-tête `X-API-Key` exigé sur `/ai` si la variable est renseignée | `ALIMENDO_API_KEY` |
| Rôles | `user` à l'inscription ; aucune route n'est réservée à un rôle pour l'instant | table `role` |

**Réponses en cas de refus.**

| Code | Cas | Message |
|---|---|---|
| 401 | jeton absent | « Authentification requise. » |
| 401 | jeton expiré | « Session expirée, reconnectez-vous. » |
| 401 | jeton invalide ou mal signé | « Jeton d'authentification invalide. » |
| 401 | mauvais identifiants au login | « Email ou mot de passe incorrect. » (même message que l'email existe ou non) |
| 401 | clé d'API absente ou fausse | « Clé d'API manquante ou invalide. » |

## 4. Autres codes de réponse

| Code | Signification |
|---|---|
| 404 | Aliment ou produit introuvable |
| 409 | Email déjà utilisé à l'inscription |
| 413 / 415 | Photo trop lourde (5 Mo maximum) ou format non supporté |
| 422 | Entrée refusée par la validation (terme de recherche trop court, code-barre qui n'est pas fait de 8 à 14 chiffres, email mal formé, photo illisible...) |
| 503 | Service externe indisponible (Open Food Facts, Mistral, ChromaDB, Ollama) |

Les erreurs ont toujours la forme `{ "detail": "message" }`, ce que lit le frontend
(`frontend/src/services/api.js`).

## 5. Sécurité

Mesures prises face au Top 10 OWASP API : voir [`securite_owasp.md`](securite_owasp.md).
Accès direct à la base, hors API : voir [`acces_base.md`](acces_base.md).
## 6. Couverture des besoins en données

Correspondance entre les données que le projet doit mettre à disposition (spécifications :
[`specs_extraction.md`](specs_extraction.md) § 3 et 4, user stories) et les routes qui les servent
(critère C5-CR5). Le frontend consomme chacune de ces routes : voir
[`integration_frontend.md`](integration_frontend.md).

| Besoin (spécification) | Source | Route | Données renvoyées | Preuve |
|---|---|---|---|---|
| Trouver un aliment par son nom, même mal orthographié | CIQUAL 2020, en base (3 184 aliments importés) | `GET /search/aliments?q=` | id, nom, catégorie | capture Swagger « pome » |
| Parcourir les catégories | CIQUAL, en base | `GET /search/categories` | id, nom, image | capture Swagger |
| Score d'un aliment, badges fer / magnésium, alternatives de la même catégorie | CIQUAL + référentiel de score | `GET /score/aliment/{id}` | `AlimentDetail` : score, badges, alternatives, disclaimer, citation | capture Swagger + page `/aliment/:id` |
| Score d'un produit emballé à partir de son code-barre | API Open Food Facts, à la demande, sans stockage | `GET /score/code-barre/{code}` | `AlimentDetail` : nom, image (vignette de face, avec repli), score calculé depuis les nutriments | capture de la route avec un vrai code + page `/produit/:code` |
| Réponses documentaires sourcées sur l'endométriose et l'alimentation | Corpus RAG, index ChromaDB | `POST /ai/chat` (JWT) | réponse, sources (titre, URL), disclaimer | page `/chatbot` |
| Score d'un aliment brut identifié sur une photo | VLM Qwen3-VL + CIQUAL | `POST /ai/vision` (JWT) | label reconnu, `AlimentDetail` | page `/aliment-frais` |
| Compte de l'utilisatrice | table `utilisateur` | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | jeton, id, email, rôle | `test_endpoints.py`, page `/connexion` |

**Limites connues.** Beaucoup de produits Open Food Facts ont des micronutriments non renseignés :
leur score est alors « indisponible », ce qui est le comportement prévu (`specs_extraction.md` § 4.2).
La recherche par nom utilise `similarity()`, qui n'exploite pas l'index trigramme : la lenteur
qui en découle est traitée comme incident technique (lot C21), volontairement pas corrigée ici.