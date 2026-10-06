# Pipeline RAG offline / EndoNutrition (Alimendo)

Construit l'index vectoriel du chatbot, dans le **service ChromaDB du
docker-compose**, à partir du corpus brut déjà collecté. L'ingestion écrit en HTTP
dans le même index que celui que le backend interroge : il n'y a **plus d'index
local** (`rag/data/chroma` et `CHROMA_PERSIST_DIR` sont obsolètes).

**Périmètre : offline uniquement** de la donnée brute à l'index.
Le retrieval + la génération LLM (Mistral) vivent dans le backend, pas ici.

---

## Choix techniques (et pourquoi)

| Décision | Choix retenu | Justification courte |
|---|---|---|
| **Framework** | LangChain, en trousse à outils fine | Écosystème le plus documenté quand on est solo ; cohérent avec le futur `langchain-mistralai`. On n'en prend que le text splitter, pas les abstractions opaques. |
| **Embeddings** | `intfloat/multilingual-e5-base` (local) | Souverain RGPD (aucune donnée ne sort), gratuit, hors-ligne, reproductible. Corpus EN + questions FR -> retrieval **cross-lingue** obligatoire, qu'e5 gère bien. |
| **Métrique** | Cosinus | Métrique pour laquelle e5 est entraîné ; embeddings normalisés. |
| **Chunking** | `RecursiveCharacterTextSplitter`, piloté par le manifest | Découpe aux frontières naturelles. Politique **par source** (intégral / sélectif + marqueurs) dérivée de `note_chunking`, jamais de découpe uniforme. |
| **Format intermédiaire** | `chunks.jsonl` | Inspectable, découple le découpage de l'embedding, montrable au jury. |
| **Stockage de l'index** | Service ChromaDB (`HttpClient`) | Le backend tourne en conteneur et ne voit pas les dossiers de la machine hôte. Ingestion et backend passent par le même service : même index en local et en déploiement, et jamais deux processus qui écrivent le même dossier. |

> **Même instance, deux adresses.** Depuis ta machine : `localhost:8001` (port
> publié par le compose). Depuis un conteneur : `chromadb:8000` (réseau Docker).

> **Point RGPD contre-intuitif à retenir :** un modèle d'embeddings *local* est
> **plus** souverain qu'un appel API  aucune donnée ne quitte la machine, aucun
> sous-traitant à contractualiser.

>  **Préfixes e5.** Le modèle exige `passage: ` sur les chunks indexés et
> `query: ` sur les questions. Oublier ces préfixes ne plante pas : ça dégrade
> silencieusement le retrieval. C'est câblé dans `config.py` + `ingestion.py`.

---

## Ordre de lancement

Les scripts s'enchaînent : chacun consomme la sortie du précédent.

```bash
# 0. Dépendances (groupe ingestion)
uv add --group ingestion pdfplumber trafilatura langchain-text-splitters sentence-transformers chromadb

# 1. Extraction & nettoyage (C2) : raw/ -> processed/{id}.txt
uv run python rag/extraction.py

# 2. Chunking piloté par le manifest : processed/ -> chunks.jsonl
uv run python rag/chunking.py

# 3. Ingestion : chunks.jsonl -> embeddings -> service ChromaDB (+ requêtes de démo)
#    PRÉREQUIS : le service doit tourner.
docker compose up -d chromadb
uv run python rag/ingestion.py

# Interroger l'index existant sans le reconstruire :
uv run python rag/ingestion.py --query "quelle est la prévalence de l'endométriose ?"
```

Le premier run de l'étape 3 télécharge le modèle e5 (~1 Go), puis il est en cache.

Variables d'environnement lues par l'ingestion (toutes optionnelles) :

| Variable | Défaut | Rôle |
|---|---|---|
| `CHROMA_HOST` | `localhost` | hôte du service ChromaDB |
| `CHROMA_PORT` | `CHROMADB_PORT`, sinon `8001` | port publié du service |
| `CHROMA_COLLECTION` | `endo_corpus` | **doit être identique** à celle du `.env` du backend |

>  **Le piège silencieux.** Si le chatbot devient incohérent sans aucune erreur
> dans les logs, la cause est presque toujours un index construit avec un autre
> modèle ou d'autres préfixes que ceux de la requête. Changer de modèle
> d'embeddings impose une **réindexation complète**.

---

## Arborescence

```
rag/
├── config.py          # chemins, modèle, collection, params de chunk (source unique de vérité)
├── collecte.py         # (déjà fait) -> data/raw/
├── extraction.py       # étape 1 : nettoyage -> data/processed/{id}.txt
├── chunking.py         # étape 2 : découpage + métadonnées -> data/processed/chunks.jsonl
├── ingestion.py        # étape 3 : embeddings + écriture HTTP dans le service ChromaDB
├── data/
│   ├── raw/            # corpus brut (PDF/HTML/*.synthese.md) + corpus_manifest.csv
│   └── processed/      # texte propre + chunks.jsonl + journaux (_*.csv)
```

L'index lui-même vit dans le volume Docker `chroma_data` du service `chromadb`.

---

## Schéma de métadonnées de chunk

Chaque chunk de l'index porte ces champs (base de la citation obligatoire) :

| Champ | Type | Source | Rôle |
|---|---|---|---|
| `id_source` | str | manifest | identifiant de la source (S1…S11) |
| `titre` | str | manifest | titre affiché dans la citation |
| `url` | str | manifest (`url_recuperable`) | lien de la citation |
| `licence_indicative` | str | manifest | licence / conditions de réutilisation |
| `theme` | str | manifest | alimentation / maladie / digestif / cadre / redirection |
| `couche` | int | manifest | niveau de la source (1 = plus haut) |
| `langue` | str | manifest | FR / EN |
| `chunk_index` | int | calculé | position du chunk dans sa source |
| *marqueurs* | str | `note_chunking` | ex. `portee=risque_pas_symptomes` (S3), `usage=mecanismes` (S4) |

> Contrainte Chroma : les métadonnées ne peuvent être que `str`/`int`/`float`/`bool`.
> Pas de liste ni de dict  les marqueurs sont donc des paires plates.

---

## Traçabilité (certification C2)

Chaque étape écrit son journal dans `data/processed/` :

- `_extraction_log.csv`  statut par source (ok / skipped_stub / missing / empty / error).
- `_chunking_log.csv`  nombre de chunks gardés/écartés par source.
- `_chunking_dropped.csv`  **chunks écartés en mode sélectif (S2, S10), à auditer à la main.**

Le chunking sélectif écarte un chunk dès qu'il contient un mot-clé hors périmètre
(chirurgie, hormonal, management…). Choix **conservateur assumé** : indexer un
passage hors périmètre que le chatbot pourrait citer est plus grave que perdre un
chunk. L'audit de `_chunking_dropped.csv` fait partie de la démarche.

---

## Hors périmètre de ce pipeline

- Retrieval + génération LLM (Mistral Small 3.2) : dans le backend.
- Classifieur d'intention (`.pkl`) : gate l'appel LLM en ligne, indépendant de l'ingestion.
- Monitoring Langfuse (C11) : plus tard.
- Rédaction des stubs S6/S9 : à faire à la main ; réindexer après (`chunking.py` + `ingestion.py`).