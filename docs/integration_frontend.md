# Intégration de l'API dans le frontend

Tableau de correspondance entre les points de terminaison de l'API (voir `openapi.json`) et les écrans React (preuve C10-CR4). Les composants n'appellent jamais `fetch` : ils passent par un service de `frontend/src/services/`, qui utilise `api.js` (jeton JWT, gestion centrale du 401, erreurs typées).

| Endpoint | Accès | Service | Écran | Tests d'intégration |
|---|---|---|---|---|
| `POST /auth/register` | public | `auth.js` → `register` | `/inscription` | `Authentification.test.jsx` |
| `POST /auth/login` | public | `auth.js` → `login` | `/connexion` | `Authentification.test.jsx` |
| `GET /auth/me` | JWT | `auth.js` → `fetchCurrentUser` | démarrage de l'app (`AuthProvider`) | `Authentification.test.jsx`, `AuthProvider.test.jsx` |
| `POST /ai/chat` | JWT | `chat.js` → `askChatbot` | `/chatbot` | `Chatbot.test.jsx` |
| `GET /search/aliments` | public | `score.js` → `searchFoods` | `/analyser` (formulaire) → `/recherche?q=` | `Recherche.test.jsx`, `score.test.js` |
| `GET /search/categories` | public | `score.js` → `getCategories` (mis en cache) | `/aliment/:id` (libellé de catégorie) | `Aliment.test.jsx`, `score.test.js` |
| `GET /score/aliment/{id}` | public | `score.js` → `getFoodScore` | `/aliment/:id` | `Aliment.test.jsx`, `score.test.js` |
| `GET /score/code-barre/{code}` | public | `score.js` → `getBarcodeScore` | `/produit-emballe` (saisie) → `/produit/:code` | `Aliment.test.jsx`, `ProduitEmballe.test.jsx`, `score.test.js` |
| `POST /ai/vision` | JWT | à venir (étape 4) | `/aliment-frais` | à venir |

Endpoints non exploités par le frontend : `GET /health` et `GET /health/detail` (sondes pour Docker et le monitorage).

## Gestion des erreurs, commune à tous les écrans

| Cas | Comportement |
|---|---|
| 401 sur un appel authentifié | jeton effacé, redirection vers `/connexion` avec « Votre session a expiré », retour à la page d'origine après connexion |
| 404 | état « non trouvé » propre à l'écran (aliment, code-barre) |
| 422 | message reformulé en français |
| 5xx, 503 | message de l'API, ou « Le service est momentanément indisponible » |
| serveur injoignable | « Le serveur est injoignable. Vérifiez votre connexion puis réessayez. » |
| erreur d'affichage React | `ErrorBoundary` : page « Une erreur est survenue » au lieu d'un écran vide |

## Textes médicaux

Le frontend n'écrit aucune formulation médicale. Les libellés de score, badges, disclaimers, citation de source et titre des alternatives viennent de l'API (`backend/app/core/disclaimers.py`, transcription de `score_medical-guidelines.md`). Le seul texte fixe côté frontend est le disclaimer long du chatbot (§7.7), copié mot pour mot dans `frontend/src/content/chatbotTexts.js`.
