# Pipeline RAG offline - Alimendo

Construit un index ChromaDB persistant et interrogeable à partir du corpus brut
déjà collecté. **Périmètre : offline uniquement** - de la donnée brute à l'index.
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

> **Point RGPD contre-intuitif à retenir :** un modèle d'embeddings *local* est
> **plus** souverain qu'un appel API - aucune donnée ne quitte la machine, aucun
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

# 3. Ingestion : chunks.jsonl -> embeddings -> index ChromaDB (+ requêtes de démo)
uv run python rag/ingestion.py

# Interroger l'index existant sans le reconstruire :
uv run python rag/ingestion.py --query "quelle est la prévalence de l'endométriose ?"
```

Le premier run de l'étape 3 télécharge le modèle e5 (~1 Go), puis il est en cache.

---

## Arborescence

```
rag/
├── config.py          # chemins, modèle, collection, params de chunk (source unique de vérité)
├── collecte.py         # (déjà fait) -> data/raw/
├── extraction.py       # étape 1 : nettoyage -> data/processed/{id}.txt
├── chunking.py         # étape 2 : découpage + métadonnées -> data/processed/chunks.jsonl
├── ingestion.py        # étape 3 : embeddings + index ChromaDB
├── data/
│   ├── raw/            # corpus brut (PDF/HTML/*.synthese.md) + corpus_manifest.csv
│   ├── processed/      # texte propre + chunks.jsonl + journaux (_*.csv)
│   └── chroma/         # index persistant (lu par le backend via CHROMA_PERSIST_DIR)
```

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
> Pas de liste ni de dict - les marqueurs sont donc des paires plates.

---

## Traçabilité

Chaque étape écrit son journal dans `data/processed/` :

- `_extraction_log.csv` - statut par source (ok / skipped_stub / missing / empty / error).
- `_chunking_log.csv` - nombre de chunks gardés/écartés par source.
- `_chunking_dropped.csv` - **chunks écartés en mode sélectif (S2, S10), à auditer à la main.**

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
