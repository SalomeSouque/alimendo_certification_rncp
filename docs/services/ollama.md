# Service Ollama (Qwen3-VL 4B) : installation, accès, monitorage et tests

Ce document décrit le VLM de reconnaissance photo tel qu'il est installé et
paramétré dans Alimendo. Il sert de preuve pour la compétence C8 (critères
CR1 à CR5), au même titre que [la documentation du service Mistral](mistral.md).

Public visé : toute personne qui doit installer, tester ou maintenir la
reconnaissance d'aliment par photo.

> **État du document.** Les parties 1 à 4 sont rédigées (étape 1 du lot VLM :
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

| Variable | Valeur par défaut | Rôle |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Adresse du service. En local, hors Docker : `http://localhost:11434` |
| `OLLAMA_MODEL` | `qwen3-vl:4b-instruct-q4_K_M` | Tag exact du modèle |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Délai maximal d'attente d'une réponse. Il inclut le premier chargement du modèle en VRAM. Il sera réduit après les mesures de l'étape 3 |
| `VLM_CONFIDENCE_THRESHOLD` | `0.5` | En dessous de ce score, l'aliment est considéré comme non identifié |

Ces valeurs sont lues et validées par `get_ollama_settings()`
(`backend/app/core/config.py`). Une valeur absurde (modèle vide, délai nul ou
négatif, seuil hors de [0, 1]) bloque le démarrage avec un message explicite.
Les tests correspondants sont dans `backend/tests/test_config_ollama.py`.

Le prompt et le format de sortie JSON seront documentés ici à l'étape 3.

## 5. Interconnexions avec les autres composants

À compléter à l'étape 3 (branchement de `vision_service.py`).

## 6. Données impliquées

À compléter. Principe déjà retenu : l'image n'est jamais stockée. Seuls le
libellé reconnu, la confiance, le statut et l'aliment rapproché sont écrits
dans `log_vlm`.

## 7. Monitorage

À compléter : ligne de log par appel (statut, latence, modèle), table
`log_vlm`, et mesure de la mémoire GPU avec `ollama ps` et `nvidia-smi`.

## 8. Procédure de test

À compléter : tests sans réseau de `vision_service.py` et jeu de photos
d'aliments.

## 9. Limites connues

À compléter après les mesures.