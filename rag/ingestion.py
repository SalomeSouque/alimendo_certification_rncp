"""Ingestion : chunks.jsonl -> embeddings e5 -> index ChromaDB persistant (cosinus).

Entrée : rag/data/processed/chunks.jsonl   (produit par chunking.py)
Sortie : index ChromaDB persistant dans CHROMA_DIR (lu plus tard par le backend
         via la variable d'env CHROMA_PERSIST_DIR).

Deux points de vigilance :
  1. Le modèle e5 EXIGE des préfixes : "passage: " sur les chunks indexés,
     "query: " sur les questions.
  2. Métrique COSINUS, et embeddings normalisés - cohérent avec l'entraînement d'e5.

Lancement :
    uv run python rag/ingestion.py                 # (re)construit l'index + requêtes de démo
    uv run python rag/ingestion.py --query "..."   # interroge l'index existant
"""
from __future__ import annotations

import argparse
import json
import logging
from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    DISTANCE_METRIC,
    EMBEDDING_MODEL,
    EMBEDDING_PASSAGE_PREFIX,
    EMBEDDING_QUERY_PREFIX,
    PROCESSED_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("ingestion")

CHUNKS_PATH: Path = PROCESSED_DIR / "chunks.jsonl"


# Modèle d'embeddings 

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Charge le modèle e5 une seule fois (téléchargé au 1er run, puis en cache).

    Local = souverain (aucune donnée ne sort), gratuit, hors-ligne, reproductible.
    """
    logger.info("Chargement du modèle d'embeddings : %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


def embed(texts: list[str], *, is_query: bool) -> list[list[float]]:
    """Encode des textes en vecteurs, en ajoutant le préfixe e5 adapté.

    is_query=True  -> préfixe "query: "   (une question)
    is_query=False -> préfixe "passage: " (un chunk à indexer)
    normalize_embeddings=True -> vecteurs unitaires, ce qu'attend la métrique cosinus.
    """
    prefix = EMBEDDING_QUERY_PREFIX if is_query else EMBEDDING_PASSAGE_PREFIX
    prefixed = [prefix + t for t in texts]
    vectors = get_model().encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=not is_query,
    )
    return vectors.tolist()


# ChromaDB 

def get_collection(reset: bool = False) -> chromadb.Collection:
    """Ouvre (ou recrée) la collection Chroma persistante en métrique cosinus.

    reset=True supprime la collection existante pour une reconstruction propre
    et déterministe - c'est le comportement de l'indexation complète.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info("Ancienne collection supprimée (reconstruction propre).")
        except Exception:
            # La collection n'existait pas encore : cas normal au premier run.
            pass
    # hnsw:space fixe la métrique de distance.
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": DISTANCE_METRIC},
    )


def load_chunks() -> list[dict]:
    """Charge chunks.jsonl (une ligne JSON par chunk)."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"{CHUNKS_PATH} introuvable - lance d'abord chunking.py."
        )
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_index() -> None:
    """Construit l'index complet : chunks -> embeddings -> Chroma."""
    chunks = load_chunks()
    logger.info("%d chunks chargés depuis %s", len(chunks), CHUNKS_PATH)

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]      # texte PROPRE, sans préfixe
    metadatas = [c["metadata"] for c in chunks]
    embeddings = embed(documents, is_query=False)  # préfixe "passage: " appliqué ici

    collection = get_collection(reset=True)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info("Index construit : %d chunks dans '%s' (%s).",
                collection.count(), COLLECTION_NAME, DISTANCE_METRIC)
    logger.info("Persistance : %s", CHROMA_DIR)


# Requête de test

def query(question: str, n_results: int = 3) -> None:
    """Interroge l'index et affiche les chunks récupérés AVEC leurs sources.

    """
    collection = get_collection(reset=False)
    q_vector = embed([question], is_query=True)  # préfixe "query: " appliqué ici
    res = collection.query(query_embeddings=q_vector, n_results=n_results)

    print(f"\n❓ {question}\n" + "─" * 70)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    for rank, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
        # Distance cosinus -> score de similarité (1 - distance) pour lisibilité.
        score = 1 - dist
        marqueurs = {k: v for k, v in meta.items()
                     if k not in ("id_source", "titre", "url", "licence_indicative",
                                  "theme", "couche", "langue", "chunk_index")}
        print(f"\n#{rank}  score={score:.3f}  [{meta['id_source']} · {meta['theme']} "
              f"· couche {meta['couche']} · {meta['langue']}]")
        print(f"    source : {meta['titre']}")
        print(f"    url    : {meta['url']}")
        print(f"    licence: {meta['licence_indicative']}")
        if marqueurs:
            print(f"    marqueurs : {marqueurs}")
        print(f"    extrait: {doc[:220].strip()}…")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion RAG EndoNutrition")
    parser.add_argument("--query", type=str, default=None,
                        help="Interroge l'index existant sans le reconstruire.")
    parser.add_argument("--n", type=int, default=3, help="Nombre de chunks à retourner.")
    args = parser.parse_args()

    if args.query:
        query(args.query, n_results=args.n)
        return

    build_index()

    # Requêtes de démonstration
    query("C'est quoi l'endométriose ?", n_results=args.n)
    query("Est-ce que manger des légumes réduit mes douleurs ?", n_results=args.n)


if __name__ == "__main__":
    main()
