# Service Ollama (Qwen3-VL 4B) : installation, accès, monitorage et tests

Ce document décrit le VLM de reconnaissance photo tel qu'il est installé et
paramétré dans Alimendo. Il sert de preuve pour la compétence C8 (critères
CR1 à CR5), au même titre que [la documentation du service Mistral](mistral.md).

Public visé : toute personne qui doit installer, tester ou maintenir la
reconnaissance d'aliment par photo.

> **État du document.** Toutes les parties sont rédigées.
> installation). Les parties 5 à 9 seront complétées quand le service sera
> branché sur le backend (étapes 3 et suivantes).

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

## 1. Rôle du service

Ollama sert le modèle de vision Qwen3-VL en local. Le backend lui envoie la
photo d'un aliment brut et reçoit le nom de l'aliment reconnu, avec un score
de confiance. Ce nom est ensuite rapproché d'un aliment de la table CIQUAL.

| Élément | Valeur |
|---|---|
| Moteur d'inférence | Ollama, image Docker `ollama/ollama:0.40.12` (version épinglée) |
| Modèle | `qwen3-vl:4b-instruct-q4_K_M` (digest `84f7ed8042fa`, 3,3 Go) |
| Hébergement | Local, service `ollama` du `docker-compose.yml` (profil `ai`) |
| Point d'accès | `POST http://ollama:11434/api/chat` (réseau Docker) |
| Code qui appelle le service | `backend/app/services/vision_service.py` |
| Choix du service | Benchmark détaillé dans le rapport E2 (compétence C7) |

### Pourquoi cette version d'Ollama

La page officielle du modèle indique : « Qwen3-VL models require Ollama
0.12.7 » (<https://ollama.com/library/qwen3-vl>). Les notes de version
v0.12.7 confirment l'arrivée de Qwen3-VL
(<https://github.com/ollama/ollama/releases/tag/v0.12.7>). L'ancienne image
`0.6.2` ne pouvait donc pas charger le modèle.

L'image est épinglée sur `0.40.12`, la dernière version stable publiée au
moment de l'installation (27/10/2026). On n'utilise jamais `latest` : une mise
à jour silencieuse pourrait changer le comportement du modèle entre deux
démonstrations.

### Pourquoi ce tag de modèle

Dans la bibliothèque Ollama (<https://ollama.com/library/qwen3-vl/tags>), le
tag court `qwen3-vl:4b` a le même digest (`a1b29c246319`) que
`qwen3-vl:4b-thinking`. C'est donc la variante qui produit une trace de
raisonnement avant de répondre : plus lente, et gênante pour obtenir une sortie
JSON stricte.

On utilise la variante **instruct**, avec la quantification écrite dans le
nom (`q4_K_M`). Le modèle installé est ainsi figé, comme la version datée de
Mistral (`mistral-small-2603`).

| Tag | Taille | Variante | Retenu |
|---|---|---|---|
| `qwen3-vl:4b` | 3,3 Go | thinking | Non |
| `qwen3-vl:4b-instruct-q4_K_M` | 3,3 Go | instruct, 4 bits | **Oui** |
| `qwen3-vl:4b-instruct-q8_0` | 5,1 Go | instruct, 8 bits | Non : trop juste pour 6 Go de VRAM avec l'image |

## 2. Gestion des accès

| Accès | Qui | Comment |
|---|---|---|
| API Ollama (port 11434) | Le backend FastAPI, par le réseau Docker | `OLLAMA_BASE_URL=http://ollama:11434` |
| API Ollama depuis la machine hôte | La développeuse, pour les tests (curl) | Port publié sur `127.0.0.1` seulement |
| Reconnaissance photo (route `/ai/vision`) | Utilisatrices connectées | Jeton JWT, voir `docs/securite_owasp.md` |

Ollama n'a pas d'authentification intégrée. Il ne doit donc jamais être
exposé sur le réseau. Dans le `docker-compose.yml`, le port est publié sur
`127.0.0.1` uniquement. Le frontend n'appelle jamais Ollama directement.

Aucune clé ni aucun compte n'est nécessaire : le modèle est téléchargé depuis
la bibliothèque publique d'Ollama.

## 3. Installation

### Prérequis

| Élément | Exigence | Poste de développement |
|---|---|---|
| Système | Linux avec Docker Engine (Docker Desktop ne donne accès au GPU que sous Windows/WSL2) | Linux, Docker Engine Community |
| GPU NVIDIA | 6 Go de VRAM minimum | GeForce RTX 3060, 6 144 Mio |
| Pilote NVIDIA | Installé sur l'hôte, `nvidia-smi` fonctionnel | 580.178.04 (CUDA 13.0) |
| NVIDIA Container Toolkit | Version épinglée `1.20.1-1` | 1.20.1-1 |
| RAM | 16 Go | 16 Go |
| Disque | Environ 4 Go pour le modèle | — |

Le pilote permet à l'hôte d'utiliser la carte graphique. Le NVIDIA Container
Toolkit permet aux conteneurs Docker d'y accéder. Les deux sont nécessaires.

### Étape 1 : vérifier le pilote sur l'hôte

```bash
nvidia-smi
```

Le tableau doit afficher la carte graphique et la mémoire disponible. Si cette
commande échoue, le problème vient du pilote et doit être réglé avant la suite.

### Étape 2 : installer le NVIDIA Container Toolkit

Procédure officielle pour les distributions dérivées de Debian (apt), tirée de
la [documentation NVIDIA](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
Pour les autres distributions, se reporter à la même page.

```bash
# Prérequis
sudo apt-get update && sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg2

# Dépôt NVIDIA : clé de signature et source apt
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update

# Toolkit, version épinglée
export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.20.1-1
sudo apt-get install -y \
  nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}
nvidia-ctk --version
```

### Étape 3 : déclarer le runtime NVIDIA à Docker

```bash
sudo nvidia-ctk runtime configure --runtime=docker   # modifie /etc/docker/daemon.json
sudo systemctl restart docker
docker info | grep -i runtimes                       # « nvidia » doit apparaître
```

### Étape 4 : vérifier que Docker voit le GPU

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

Le même tableau qu'à l'étape 1 doit s'afficher, cette fois depuis un
conteneur. Sans cette vérification, Ollama démarre quand même, mais tourne sur
le CPU **sans aucun message d'erreur**, avec une inférence de plusieurs
minutes par photo.

### Étape 5 : démarrer le service Ollama

```bash
docker compose --profile ai pull ollama
docker compose --profile ai up -d ollama
docker compose exec ollama ollama --version
```

La version affichée doit être `0.40.12`.

### Étape 6 : télécharger le modèle

```bash
docker compose exec ollama ollama pull qwen3-vl:4b-instruct-q4_K_M
docker compose exec ollama ollama list
```

L'identifiant affiché doit être `84f7ed8042fa` : c'est la preuve que la
variante installée est bien « instruct » et non « thinking ».

Le modèle est stocké dans le volume Docker `ollama_models`. Il est conservé
après un redémarrage ou un `docker compose down`, mais pas après un
`docker compose down -v`.

### Étape 7 : vérifier que le modèle se charge sur le GPU

```bash
docker compose exec ollama ollama run qwen3-vl:4b-instruct-q4_K_M "Réponds seulement : ok"
docker compose exec ollama ollama ps
nvidia-smi
```

Dans `ollama ps`, la colonne `PROCESSOR` doit indiquer `100% GPU`. Une valeur
comme `40%/60% CPU/GPU` signifie que le modèle ne tient pas entièrement en
VRAM. Le premier appel est plus lent, car il charge le modèle en mémoire.

<!-- Captures à ajouter : captures/nvidia_ctk_version.png, captures/docker_gpu_nvidia_smi.png,
     captures/ollama_version.png, captures/ollama_list.png, captures/ollama_ps.png -->

### Problèmes rencontrés et résolutions

| Symptôme | Cause | Résolution |
|---|---|---|
| `docker: Error response from daemon: failed to discover GPU vendor from CDI: no known GPU vendor found` au lancement de `docker run --gpus all` (rencontré le 03/11/2026) | NVIDIA Container Toolkit absent : `nvidia-ctk` introuvable, et Docker ne connaît que le runtime `runc`. Le pilote, lui, fonctionnait (`nvidia-smi` correct sur l'hôte) | Étapes 2 et 3 ci-dessus. Si l'erreur mentionne encore CDI après coup, générer la spécification : `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` |
| `could not select device driver "nvidia"` | Runtime NVIDIA non déclaré à Docker | Étape 3 |
| `manifest unknown` au `pull` de l'image Ollama | Tag absent de Docker Hub | Épingler la version stable précédente (`0.40.10`) dans le compose et dans ce document |
| `ollama ps` affiche une part de CPU | VRAM insuffisante : une autre application occupe le GPU | Vérifier avec `nvidia-smi`, fermer l'application concernée |
| `failed to bind host port 127.0.0.1:11434/tcp: address already in use` à la recréation du conteneur (rencontré le 03/11/2026) | Un Ollama installé nativement sur l'hôte (service systemd) occupait déjà le port 11434 | `sudo systemctl stop ollama && sudo systemctl disable ollama`, ou un autre port publié via `OLLAMA_PORT` dans le `.env` |


## 4. Configuration

### Service Docker (`docker-compose.yml`)

| Paramètre | Valeur | Rôle |
|---|---|---|
| `image` | `ollama/ollama:0.40.12` | Version épinglée, compatible Qwen3-VL |
| `profiles` | `ai` | Le service ne démarre qu'à la demande : la CI et les postes sans GPU n'en ont pas besoin |
| `OLLAMA_KEEP_ALIVE` | `10m` | Garde le modèle en VRAM 10 minutes après le dernier appel, ce qui évite de le recharger à chaque photo |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Un seul modèle en mémoire, à cause des 6 Go de VRAM |
| `deploy.resources.reservations.devices` | GPU NVIDIA | Donne au conteneur l'accès à la carte graphique |

### Backend (`.env`)

| Variable | Valeur par défaut | Rôle | Justification |
|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Adresse du service. En local, hors Docker : `http://localhost:11434` | — |
| `OLLAMA_MODEL` | `qwen3-vl:4b-instruct-q4_K_M` | Tag exact du modèle | § 1 |
| `OLLAMA_TIMEOUT_SECONDS` | `30` | Délai maximal d'attente d'une réponse | Pire cas mesuré : 17,3 s au premier appel (chargement en VRAM compris), environ 0,6 s ensuite (§ 8) |
| `OLLAMA_NUM_CTX` | `4096` | Taille du contexte du modèle, en tokens | Une photo réduite à 1024 px en coûte environ 1 300 |
| `VLM_IMAGE_MAX_PX` | `1024` | Plus grand côté de l'image envoyée, après réduction par le backend | Sans réduction, une photo de téléphone coûte 4 186 tokens et dépasse le contexte (§ 8) |
| `VLM_CONFIDENCE_THRESHOLD` | `0.5` | En dessous, l'aliment est considéré comme non identifié | Garde-fou seulement : la confiance déclarée est peu discriminante (§ 9) |

Ces valeurs sont lues et validées par `get_ollama_settings()`
(`backend/app/core/config.py`). Une valeur absurde (modèle vide, délai, contexte
ou taille d'image nul ou négatif, seuil hors de [0, 1]) bloque le démarrage avec
un message explicite. Tests : `backend/tests/test_config_ollama.py`.

### Prompt et format de sortie

Le prompt et le schéma sont dans `backend/app/services/vision_service.py`
(`PROMPT_SYSTEME`, `PROMPT_UTILISATEUR`, `SCHEMA_REPONSE`). Ils sont identiques à
ceux de l'outil de test `scripts/vlm_curl_test.sh`.

La sortie est contrainte par les **sorties structurées** d'Ollama : un schéma JSON
est passé dans le champ `format` de la requête, et le modèle ne peut produire que
des objets qui le respectent.

```json
{
  "contenu": "aliment_unique | plusieurs_aliments | plat_prepare | aucun_aliment",
  "label": "nom générique en français, ou \"\" si contenu ≠ aliment_unique",
  "confidence": 0.98
}
```

L'ordre des propriétés compte : le modèle **classe d'abord la photo**
(`contenu`), **puis nomme l'aliment** (`label`). Cette version 2 du prompt
remplace une v1 qui ne demandait que `label` et `confidence` (résultats
comparés au § 8).

| Option de génération | Valeur | Pourquoi |
|---|---|---|
| `temperature` | `0` | Classification : réponse la plus probable, identique d'un appel à l'autre |
| `num_ctx` | `OLLAMA_NUM_CTX` | Voir ci-dessus |
| `stream` | `false` | Une seule réponse JSON complète |

La sortie est revérifiée par le backend (`analyser_reponse`) : valeur de
`contenu` connue, `label` texte, `confidence` nombre entre 0 et 1. Une sortie
inexploitable donne le statut `echec`, jamais une erreur 500.

## 5. Interconnexions avec les autres composants

```
Frontend ──(photo, JWT)──▶ POST /ai/vision ──▶ vision_service
                                                 │ 1. Pillow : vérifie, redresse, réduit à 1024 px, retire les EXIF
                                                 │ 2. Ollama : POST /api/chat (prompt v2 + schéma)
                                                 │ 3. si aliment_unique : aliment_repository.rechercher_par_nom (pg_trgm)
                                                 │    puis choisir_aliment (écarte « Pomme de terre » pour « pomme »)
                                                 │ 4. score_service + alternative_service
                                                 │ 5. log_vlm_repository (PostgreSQL)
Frontend ◀──(statut, score, disclaimer)──────────┘
```

| Issue | Code HTTP | Contenu de la réponse |
|---|---|---|
| Aliment reconnu et présent dans CIQUAL | 200 | `statut: reconnu`, `resultat` = même charge utile que `GET /score/aliment/{id}` (score, badges, alternatives, disclaimer, mention projet étudiant) |
| Aliment reconnu, absent de CIQUAL | 200 | `statut: non_rapproche`, message vers la recherche par nom |
| Plusieurs aliments, plat préparé, aucun aliment, confiance trop basse, sortie inexploitable | 200 | `statut: echec`, `contenu`, message adapté vers la recherche par nom |
| Fichier qui n'est pas une image lisible | 422 | Message d'erreur, rien n'est envoyé au VLM |
| Ollama injoignable, trop lent ou en erreur | 503 | « Le service de reconnaissance photo est temporairement indisponible, essayez la recherche textuelle. » |

Les contrôles 415 (type de fichier) et 413 (plus de 5 Mo) sont faits par la
route, avant le service.

## 6. Données impliquées

| Donnée | Où elle va | Conservée ? |
|---|---|---|
| Photo envoyée | Mémoire du backend, puis Ollama (local, même machine) | **Non.** Elle n'est écrite ni sur disque, ni en base, ni dans les logs |
| Métadonnées EXIF (dont position GPS) | Supprimées par le réencodage JPEG, avant l'envoi au VLM | Non : elles ne sortent jamais du backend |
| `contenu`, `label`, `confidence` | Réponse API + log applicatif (`contenu` seulement) | Libellé et confiance dans `log_vlm` |
| Statut et aliment rapproché | Table `log_vlm` | Oui, sans lien avec l'utilisatrice (aucun identifiant de compte) |

Aucune donnée ne quitte la machine : le modèle tourne en local, contrairement à
une API de vision hébergée. Si la fiche du registre des traitements
(`docs/rgpd/registre-traitement-alimendo.ods`) ne mentionne pas encore la
reconnaissance photo, ce traitement y est à ajouter.

## 7. Monitorage

| Source | Contenu | Commande |
|---|---|---|
| Log applicatif, une ligne par appel | `appel ollama : statut=200 modele=… latence_ms=… tokens_entree=… tokens_sortie=… contenu=… json_valide=…` ; en cas de panne : `appel ollama en échec : statut=…` ou `erreur_reseau=…` | `docker compose logs api \| grep "appel ollama"` |
| Table `log_vlm`, une ligne par inférence | Statut (`reconnu`, `non_rapproche`, `echec`), libellé, confiance, aliment, horodatage | `SELECT statut, count(*) FROM log_vlm GROUP BY statut;` |
| Charge du modèle | Modèle chargé, part GPU/CPU, mémoire, expiration | `docker compose exec ollama ollama ps` |
| Mémoire GPU | VRAM occupée | `nvidia-smi` |

La table `log_vlm` permet de suivre le taux de reconnaissance et sa dérive dans
le temps. C'est l'entrée du monitorage du modèle (compétence C11).

## 8. Procédure de test

### Tests automatisés, sans réseau ni GPU

```bash
cd backend
uv run pytest tests/test_vision_service.py tests/test_config_ollama.py -v
```

Ollama est remplacé par `httpx.MockTransport`, la base par des doublures.

| Famille de cas | Ce qui est vérifié |
|---|---|
| Préparation de l'image | Réduction à 1024 px, proportions conservées, pas d'agrandissement, EXIF et GPS supprimés, orientation appliquée, fichiers illisibles refusés |
| Requête envoyée | Modèle, schéma (ordre `contenu` → `label`), `temperature: 0`, `num_ctx`, image réduite en JPEG |
| Reconnu | Score et disclaimer renvoyés, ligne `log_vlm` complète |
| Non reconnu | `plusieurs_aliments`, `plat_prepare`, `aucun_aliment`, confiance sous le seuil, label vide, absent de CIQUAL, 6 sorties de modèle inexploitables |
| Image invalide | Exception levée, Ollama jamais appelé, rien journalisé |
| Service indisponible | Connexion refusée, timeout, HTTP 400 / 404 / 500 : exception levée et échec journalisé |
| Rapprochement CIQUAL | « pomme » ne donne pas « Pomme de terre », accents ignorés, ordre de la recherche conservé |
| Monitorage | Ligne `appel ollama` présente, image absente des logs, panne de journalisation sans effet sur la réponse |

Les tests de la route (`tests/test_ai_endpoints.py`) vérifient les codes 200,
422 et 503 de `POST /ai/vision`.

### Test sur le vrai modèle : jeu de photos de contrôle

Outil : `scripts/vlm_curl_test.sh` (même prompt, même schéma, mêmes options que
le backend). Photos personnelles, sans personne visible, réduites à 1024 px.
Poste : RTX 3060 6 Go, Ollama 0.40.12, `qwen3-vl:4b-instruct-q4_K_M`.

**Prompt v1** (`label` + `confidence`), photos non réduites, 03/11/2026 :

| Photo | Attendu | Obtenu |
|---|---|---|
| Tomate cerise (1024 px) | tomate | tomate · 0,95 ✅ |
| Tomate cerise (pleine résolution) | tomate | HTTP 400 : 4 186 tokens > contexte de 4 096 |
| Brocoli | brocoli | brocoli · 0,98 ✅ |
| Banane | banane | banane · 0,98 ✅ |
| Pomme tenue en main | pomme | HTTP 400 (contexte dépassé) |
| Assortiment de légumes | aucun | **laitue · 0,95** ❌ |
| Assiette repas | aucun | **riz · 0,95** ❌ |
| Souris d'ordinateur | aucun | HTTP 400 (contexte dépassé) |
| Pommes, photo floue | à observer | HTTP 400 (contexte dépassé) |

**Prompt v2** (`contenu` → `label` → `confidence`), photos réduites à 1024 px, 03/11/2026 :

| Photo | Attendu | `contenu` | `label` · confiance | |
|---|---|---|---|---|
| Tomate cerise (×2 versions) | tomate | aliment_unique | tomate · 0,98 | ✅ |
| Banane | banane | aliment_unique | banane · 0,98 | ✅ |
| Brocoli | brocoli | aliment_unique | brocoli · 0,98 | ✅ |
| Pomme tenue en main | pomme | aliment_unique | pomme · 0,95 | ✅ |
| Assortiment de légumes | aucun | plusieurs_aliments | — · 0,98 | ✅ |
| Assiette repas | aucun | plat_prepare | — · 0,98 | ✅ |
| Souris d'ordinateur | aucun | aucun_aliment | — · 1,0 | ✅ |
| Pommes, photo floue | à observer | aliment_unique | pomme · 0,95 | ✅ |

JSON valide sur 9 appels sur 9.

| Mesure | Valeur |
|---|---|
| Durée au premier appel (chargement du modèle compris) | 17,3 s (6,2 s de chargement) |
| Durée à chaud | 0,5 à 0,6 s par photo |
| Tokens d'entrée, photo réduite à 1024 px | 1 298 à 1 342 |
| Mémoire GPU, modèle chargé | 4 499 à 4 703 Mio sur 6 144 |
| Mémoire GPU maximale relevée (après appel, modèle chargé) | 4 703 Mio sur 6 144 (≈ 1,4 Go de marge) |

**Interprétation.** La v1 a révélé deux problèmes : les photos non réduites
dépassent le contexte, et le modèle nomme un aliment même quand la photo n'en
montre pas un seul, avec une confiance aussi haute que pour une bonne réponse.
La v2 corrige le second en faisant classer la photo avant de la nommer. Le
premier est corrigé par la réduction à 1024 px dans le backend. Ces 8 photos
forment un **jeu de contrôle** : elles valident le paramétrage, elles ne
mesurent pas une précision.

## 9. Limites connues

- **Confiance non calibrée.** Le modèle déclare entre 0,95 et 1,0 sur toutes les
  photos, y compris ses erreurs en v1 et une photo floue. La décision repose
  donc sur `contenu`, et le seuil de confiance n'est qu'un garde-fou.
- **Jeu de contrôle réduit.** 8 photos personnelles. Une évaluation sérieuse
  demanderait un jeu étiqueté de plusieurs centaines de photos (piste de
  monitorage C11 : comparer `log_vlm` à des retours utilisateur).
- **Un seul aliment par photo.** Une assiette ou un assortiment renvoie vers la
  recherche par nom. La reconnaissance de plusieurs aliments est une prochaine
  étape (« recettes via photo du frigo »).
- **Rapprochement CIQUAL heuristique.** Le libellé du modèle (« pomme ») est
  rapproché par recherche floue, puis on privilégie le nom exact et les aliments
  crus. Une variété précise (« tomate cerise ») est ramenée à l'aliment générique.
- **Premier appel lent.** 17 s après un démarrage ou 10 minutes d'inactivité,
  le temps de charger le modèle en VRAM. Piste : un appel de préchauffage au
  démarrage de l'API.
- **Format HEIC.** Les photos d'iPhone en HEIC sont refusées (415). En général,
  les navigateurs mobiles les convertissent en JPEG à l'envoi, ce qui reste à
  vérifier en démonstration.
- **Matériel.** 6 Go de VRAM au minimum. Sans GPU, Ollama bascule sur le CPU
  sans erreur, avec plusieurs secondes à plusieurs minutes par photo.