# Tests d'intégration du frontend

Projet Alimendo, compétence C10 (intégration de l'API dans l'application), critères C10-CR6 à CR8. Ce document complète `tests_api.md`, qui porte sur le backend.

## 1. Principe

Les tests vérifient que chaque écran **appelle le bon point de terminaison avec le bon contrat**, puis **réagit correctement à chaque réponse possible** : succès, jeton expiré (401) et erreur serveur, plus les cas propres à l'endpoint (404, 413, 503, validation).

- **Outils :** Vitest (exécution), Testing Library (rendu React et interactions comme une utilisatrice : saisie, clic, envoi de fichier), jsdom (navigateur simulé).
- **Réseau simulé :** `fetch` est remplacé par un mock (`src/test/mockFetch.js`) qui renvoie des réponses construites d'après `docs/openapi.json` (`src/test/fixtures.js`). Les tests ne dépendent donc ni du backend, ni d'Ollama, ni de Mistral, et la CI reste rapide et reproductible. La communication réelle avec l'API est vérifiée séparément, de bout en bout (captures, preuve C10-CR2).
- **Ce qui est vérifié à chaque fois :**
  - l'URL appelée ;
  - la méthode ;
  - le corps envoyé (JSON ou multipart) ;
  - l'en-tête `Authorization` ;
  - ce qui s'affiche ;
  - l'accessibilité utile (rôles `alert` et `status`, champ en erreur relié à son message).

## 2. Lancer les tests

```bash
cd frontend
npm run test            # les 70 tests (c'est ce que lance la CI)
npm run test:coverage   # avec la couverture de code (rapport texte + coverage/index.html)
```

## 3. Couverture des points de terminaison exploités

| Endpoint | Succès | 401 | Erreur serveur | Autres cas testés | Fichiers |
|---|---|---|---|---|---|
| `POST /auth/login` | ✓ jeton stocké, retour à la page | ✓ mauvais mot de passe : message, pas de redirection | ✓ 500 | email invalide, aucun appel | `Authentification.test.jsx` |
| `POST /auth/register` | ✓ `consentement: true` envoyé | sans objet (public) | ✓ via `api.test.js` (5xx) | 409 compte existant ; mot de passe < 8 ou case non cochée, aucun appel | `Authentification.test.jsx` |
| `GET /auth/me` | ✓ session restaurée | ✓ jeton expiré au démarrage : effacé sans redirection | ✓ via `api.test.js` | accès refusé aux features IA sans session | `Authentification.test.jsx`, `AuthGate.test.jsx` |
| `POST /ai/chat` | ✓ paragraphes, sources dédoublonnées, disclaimer | ✓ redirection vers `/connexion` | ✓ 503 + « Réessayer » | chargement, `REDIRECT_SCAN`, détresse sans disclaimer, question < 3 caractères | `Chatbot.test.jsx` |
| `POST /ai/vision` | ✓ aliment reconnu et score | ✓ redirection | ✓ 503 ; 413 refusé par l'API | non rapproché, échec, mauvais format et > 5 Mo refusés avant l'envoi, glisser-déposer, multipart sans `Content-Type` manuel, délai dépassé | `AlimentFrais.test.jsx`, `vision.test.js` |
| `GET /search/aliments` | ✓ résultats et liens | sans objet (public) | ✓ 500 | aucun résultat, terme < 2 caractères, encodage de l'URL | `Recherche.test.jsx`, `score.test.js` |
| `GET /search/categories` | ✓ libellé de catégorie | sans objet | ✓ indisponible : le score reste affiché | mise en cache | `Aliment.test.jsx`, `score.test.js` |
| `GET /score/aliment/{id}` | ✓ score, badges, disclaimers, alternatives | sans objet | ✓ 500 | 404, score indisponible | `Aliment.test.jsx`, `score.test.js` |
| `GET /score/code-barre/{code}` | ✓ produit Open Food Facts | sans objet | ✓ 503 Open Food Facts | 404, code invalide sans appel, espaces retirés, image cassée remplacée par le pictogramme ; code lu par la caméra ou sur une photo (lecture simulée), caméra refusée, caméra absente | `Aliment.test.jsx`, `ProduitEmballe.test.jsx`, `BarcodeScanner.test.jsx`, `score.test.js` |

Le transport commun (`api.js`) a ses propres tests : jeton ajouté, `FormData` sans `Content-Type`, 401 avec ou sans jeton, 422 lisible, 5xx, serveur injoignable. Le 401 « en cours de session », avec redirection et retour à la page d'origine, est testé dans `AuthProvider.test.jsx`.

**Endpoints non exploités par le frontend :** `GET /health` et `/health/detail` (sondes Docker et monitorage). Ils sont testés côté backend.

## 4. Résultats

Exécution du 06/11/2026 (`npm run test:coverage`) : **70 tests, 15 fichiers, 70 réussis, 0 échec, 0 ignoré**. Le lint et le build passent.

Couverture de code (instructions exécutées par les tests) :

| Mesure | Valeur |
|---|---|
| Lignes | 88,6 % (421 / 475) |
| Instructions | 87,5 % |
| Branches | 85,1 % |
| Fonctions | 82,8 % |

Les services (`api.js`, `chat.js`, `score.js`, `vision.js`) et les écrans branchés sur l'API (connexion, chatbot, recherche, aliment, photo) sont couverts entre 93 et 100 % des lignes.

## 5. Interprétation

**Ce que les résultats permettent d'affirmer.** Tous les endpoints exploités ont au moins un test de succès et un test d'erreur serveur, et tous les endpoints protégés ont un test 401 (C10-CR6). Les 70 tests s'exécutent en entier sans erreur ni test ignoré : aucun bug dans les tests eux-mêmes (C10-CR7).

Les tests et la recette ont aussi permis de trouver de vrais défauts pendant le développement :

- un écran vide du chatbot quand une réponse n'avait pas de paragraphes ;
- un test qui recopiait un texte au lieu de le lire depuis sa source ;
- un rôle ARIA qui masquait un titre (`role="status"` sur un `h2`) ;
- une zone photo inaccessible au clavier.

**Ce qu'ils ne permettent pas d'affirmer.**

- **Le réseau est simulé.** Un écart entre le mock et le vrai backend, par exemple un champ renommé, ne serait pas détecté ici. La parade : les réponses simulées suivent `openapi.json`, régénéré à chaque changement de schéma, et un parcours de bout en bout est fait à la main, stack lancée.
- **La qualité des réponses IA n'est pas testée ici.** Pertinence du chatbot, justesse de la reconnaissance photo et du routage d'intention relèvent du monitorage et des tests du modèle (C11, C12). Par exemple, le mauvais routage des questions générales a été trouvé en recette manuelle, pas par ces tests.
- **La couverture mesure ce qui est exécuté, pas ce qui est juste.** Un taux élevé ne garantit pas que chaque comportement attendu soit vérifié par une assertion.

**Parties non couvertes, et pourquoi.**

| Fichier | Couverture | Raison |
|---|---|---|
| `Home.jsx`, `EnSavoirPlus.jsx` | 0 % | pages de contenu statique, sans appel à l'API |
| `App.jsx`, `ScrollTop.jsx` | 0 % | table des routes et défilement, vérifiés par la navigation des autres tests et en manuel |
| `auth.js` | 74 % | les lignes manquantes sont celles du mode simulé (`VITE_AUTH_MOCK=true`), désactivé en usage normal |
| `useApiResource.js` | 50 % des branches | branche « requête obsolète ignorée », difficile à provoquer en test unitaire |
| `barcode.js` | 21 % | enveloppe de la bibliothèque ZXing : jsdom n'a ni caméra ni décodage d'image. Le composant qui l'utilise est testé avec une lecture simulée, et la lecture réelle a été vérifiée dans Chromium avec un code EAN-13 généré : photo importée et caméra simulée (`--use-file-for-fake-video-capture`), les deux mènent à `/produit/3017620422003` |

**Pistes d'amélioration :**

- un test de bout en bout automatisé (Playwright), contre la stack Docker, sur les parcours principaux ;
- un test de contrat qui compare les fixtures à `openapi.json` ;
- un seuil de couverture minimal en CI.