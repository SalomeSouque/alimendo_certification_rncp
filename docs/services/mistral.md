# Service Mistral : installation, accès, monitorage et tests

Ce document décrit le service d'IA Mistral tel qu'il est paramétré dans
Alimendo. Il sert de preuve pour la compétence C8 (critères CR1 à CR5).

Public visé : toute personne qui doit installer, tester ou maintenir le
chatbot d'Alimendo.

## Sommaire

1. [Rôle du service](#1-rôle-du-service)
2. [Gestion des accès](#2-gestion-des-accès)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
5. [Interconnexions avec les autres composants](#5-interconnexions-avec-les-autres-composants)
6. [Données impliquées](#6-données-impliquées)
7. [Monitorage](#7-monitorage)
8. [Procédure de test](#8-procédure-de-test)
9. [Limites connues](#9-limites-connues)
10. [Accessibilité de ce document](#10-accessibilité-de-ce-document)

## 1. Rôle du service

Mistral génère la réponse du chatbot. Il reçoit la question de
l'utilisatrice et les extraits du corpus documentaire retrouvés par ChromaDB,
et répond uniquement à partir de ces extraits.

| Élément | Valeur |
|---|---|
| Fournisseur | Mistral AI (hébergement dans l'Union européenne) |
| Modèle | `mistral-small-2603` (version datée, donc figée) |
| Point d'accès | `POST https://api.mistral.ai/v1/chat/completions` |
| Code qui appelle le service | `backend/app/services/llm_mistral.py` |
| Choix du service | Benchmark détaillé dans le rapport E2 (compétence C7) |

## 2. Gestion des accès

### Qui accède à quoi

| Accès | Qui | Comment |
|---|---|---|
| Console Mistral (création de clé, usage, limites) | La développeuse, seule | Compte Mistral personnel |
| Clé API Mistral | Le backend FastAPI, seul | Variable `MISTRAL_API_KEY` du fichier `.env` |
| Chatbot (route `/ai/chat`) | Utilisatrices connectées | Jeton JWT, voir `docs/securite_owasp.md` |

Le frontend n'appelle jamais Mistral directement et ne connaît pas la clé.

### Créer une clé

1. Se connecter à la console Mistral : <https://console.mistral.ai>.
2. Ouvrir le menu du profil, puis « API Keys ».
3. Cliquer sur « Create new key ». Donner un nom explicite (exemple :
   `alimendo-local`) et une date d'expiration.
4. Copier la clé tout de suite : elle n'est affichée qu'une fois.
5. La coller dans `.env` à la ligne `MISTRAL_API_KEY=`.

![Liste des clés API de la console Mistral : une clé nommée alimendo-local, valeur masquée, date de dernière utilisation et date d'expiration visibles](captures/mistral_cle_api.png)

### Règles de sécurité

- La clé vit uniquement dans `.env`, qui est listé dans `.gitignore`. Seul
  `.env.example`, sans valeur, est versionné.
- La clé n'apparaît jamais dans les logs : le filtre de
  `backend/app/core/logging_config.py` masque les en-têtes `Authorization`.
  Le test `backend/tests/test_llm_mistral.py` le vérifie.
- Rotation : créer une nouvelle clé, la mettre dans `.env`, redémarrer l'API,
  puis supprimer l'ancienne clé dans la console.
- En cas de fuite : supprimer immédiatement la clé dans la console, la clé
  cesse de fonctionner.

## 3. Installation

### Dépendances

| Dépendance | Rôle | Où elle est déclarée |
|---|---|---|
| `httpx` | Client HTTP qui appelle l'API Mistral | `backend/pyproject.toml` |
| `python-dotenv` | Lecture du fichier `.env` | `backend/pyproject.toml` |
| Compte Mistral et clé API | Accès au service | Voir la partie 2 |

Aucun SDK Mistral n'est installé : l'API est une simple API REST, un appel
`httpx` suffit et limite les dépendances.

### Étapes

```bash
# 1. Depuis la racine du dépôt, créer le fichier d'environnement
cp .env.example .env

# 2. Renseigner MISTRAL_API_KEY dans .env (voir partie 2)

# 3. Démarrer la stack
docker compose --profile app up --build -d

# 4. Vérifier que le service répond (voir partie 8)
uv run python scripts/validate_mistral.py
```

## 4. Configuration

Toutes les valeurs sont lues dans `.env` par `backend/app/core/config.py`
(`get_mistral_settings`).

| Variable | Valeur | Pourquoi |
|---|---|---|
| `MISTRAL_API_KEY` | Secret | Authentification auprès de Mistral |
| `MISTRAL_BASE_URL` | `https://api.mistral.ai/v1` | Point d'accès officiel |
| `MISTRAL_MODEL` | `mistral-small-2603` | Version datée : le comportement ne change pas sans décision de notre part |
| `MISTRAL_TEMPERATURE` | `0.15` | Réponses peu créatives, collées aux extraits : on limite les inventions |
| `MISTRAL_MAX_TOKENS` | `800` | Borne la longueur et le coût de chaque réponse |
| `MISTRAL_TIMEOUT_SECONDS` | `30` | Au-delà, l'API renvoie une erreur 503 claire au lieu d'attendre |

Le prompt système (`PROMPT_SYSTEME` dans `llm_mistral.py`) fait partie de la
configuration : il impose de répondre seulement à partir des extraits, sans
diagnostic, sans prescription, et de dire quand l'information manque. Il
reprend les règles de `RAG_medical-guidelines.md`.

## 5. Interconnexions avec les autres composants

Parcours d'une question, dans l'ordre :

1. Client -> `POST /ai/chat` avec le jeton JWT. Le client cible est le
   frontend React ; tant qu'il n'est pas branché sur l'API, les appels se
   font depuis Swagger (`/docs`, en local).
2. FastAPI nettoie la question (`backend/app/schemas/chat.py`).
3. Filet de sécurité puis classifieur d'intention : seule l'intention
   `in_scope` continue. Les quatre autres reçoivent un texte validé, sans
   appel à Mistral.
4. Modèle d'embeddings `multilingual-e5-base` -> recherche dans ChromaDB
   (5 extraits au plus).
5. Si aucun extrait n'est trouvé : texte de repli, sans appel à Mistral.
6. Sinon : appel à Mistral avec le prompt système, les extraits et la question.
7. FastAPI renvoie la réponse, les sources et le disclaimer au client.

| Panne | Comportement |
|---|---|
| Mistral répond une erreur (clé invalide, quota dépassé, erreur serveur) | Réponse 503 « Le service de réponse est temporairement indisponible » |
| Mistral ne répond pas avant 30 secondes | Même réponse 503 |
| Réponse de Mistral au mauvais format | Même réponse 503 |

## 6. Données impliquées

| Donnée | Envoyée à Mistral | Conservée par Alimendo |
|---|---|---|
| Question de l'utilisatrice (nettoyée, 1000 caractères maximum) | Oui, seulement pour l'intention `in_scope` | Non |
| Extraits du corpus documentaire (sources publiques) | Oui | Déjà dans ChromaDB |
| Prompt système | Oui | Dans le code |
| Réponse générée | Reçue | Non |
| Email, identifiant, jeton de l'utilisatrice | Non, jamais | Base `utilisateur` uniquement |
| Statut, latence, nombre de tokens | Non | Oui, dans les logs de l'API |

Point de vigilance : une question peut contenir une donnée de santé. Elle
n'est donc jamais écrite dans les logs. Dans la console Mistral, vérifier
dans « Admin », rubrique « Privacy », que le partage « Anonymous improvement
data » est désactivé, pour que les échanges ne servent pas à entraîner les
modèles. Mistral agit ici comme sous-traitant au sens du RGPD : ce transfert
doit figurer dans le registre des traitements (`docs/rgpd/README.md`).

## 7. Monitorage

Le service est surveillé à deux endroits.

### Monitorage fourni par Mistral

La console Mistral propose une page d'usage (Admin, API, Usage :
<https://admin.mistral.ai/organization/usage>). Elle montre la consommation
par jour et par modèle, en tokens d'entrée et de sortie. La page des limites
(Admin, API, Limits) montre les plafonds de requêtes et de tokens du compte.

![Page Usage de la console Mistral : consommation de tokens d'entrée et de sortie par jour pour le modèle mistral-small-2603](captures/mistral_console_usage.png)

### Logs de l'API Alimendo

Chaque appel à Mistral écrit une ligne de log, sans clé, sans question et
sans réponse :

```text
2026-10-23 10:12:41 | INFO    | app.services.llm_mistral | appel mistral : statut=200 modele=mistral-small-2603 latence_ms=1840 tokens_entree=1290 tokens_sortie=212
2026-10-23 10:15:02 | ERROR   | app.services.llm_mistral | appel mistral en échec : statut=401 latence_ms=310
```

Pour les lire :

```bash
docker compose logs api | grep "appel mistral"
```

Ces logs alimenteront le monitorage du modèle (C11) et de l'application
(C20).

## 8. Procédure de test

### Tests automatisés (sans réseau, lancés par la CI)

```bash
cd backend
uv run pytest tests/test_llm_mistral.py -q
```

Ils vérifient que chaque appel est journalisé (statut, latence, tokens), que
la clé et la question n'apparaissent pas dans les logs, et qu'une erreur de
Mistral devient une erreur propre.

### Tests de validation (vrai service)

```bash
# Depuis la racine du dépôt, avec MISTRAL_API_KEY dans .env
uv run python scripts/validate_mistral.py
```

| Cas | Ce qu'on vérifie |
|---|---|
| `question_connue` | La réponse s'appuie sur l'extrait fourni |
| `hors_extraits` | Le modèle refuse une question sans réponse dans les extraits, au lieu de répondre depuis ses connaissances générales |
| `cle_invalide` | Mistral refuse une clé fausse, l'application lève une erreur propre |
| `service_injoignable` | Sans réponse du service, l'application lève une erreur propre |

Les questions hors sujet (fertilité, traitement, sujet sans rapport) sont
arrêtées avant Mistral par le classifieur d'intention. Ce cas est couvert par
`backend/tests/test_intent_routing.py`.

Résultats : [résultats des tests de validation](resultats_validation_mistral.md).

## 9. Limites connues

- Le contrôle automatique des réponses repose sur un mot-clé : il détecte un
  écart grossier, pas une erreur subtile. Les réponses sont relues à la main.
- Une seule clé pour tous les environnements en phase de projet. En
  production, une clé par environnement serait préférable.
- Pas de nouvelle tentative automatique si Mistral échoue : l'utilisatrice
  reçoit un message et peut reposer sa question.

## 10. Accessibilité de ce document

Ce document suit les recommandations de l'association Valentin Haüy et du
guide AcceDe d'Atalan :

- titres hiérarchisés (un seul titre de niveau 1, puis niveaux 2 et 3) et
  sommaire avec liens ;
- tableaux simples, une ligne d'en-tête, aucune cellule fusionnée ;
- texte alternatif qui décrit le contenu de chaque capture d'écran ;
- liens dont l'intitulé dit où ils mènent ;
- aucune information transmise par la couleur seule ;
- format Markdown, lisible par un lecteur d'écran et convertible en HTML.