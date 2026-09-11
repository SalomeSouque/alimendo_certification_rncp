"""Configuration centralisée du pipeline RAG offline.

Toutes les valeurs "réglables" du pipeline (extraction -> chunking -> ingestion)
vivent ici 
"""
from __future__ import annotations

import os
from pathlib import Path

#  Chemins 
# RAG_DIR = dossier rag/ 
RAG_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = RAG_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"              # produit par collecte.py
PROCESSED_DIR: Path = DATA_DIR / "processed"  # produit par extraction.py

# Chroma : lu plus tard par le backend via la variable d'env CHROMA_PERSIST_DIR.
CHROMA_DIR: Path = Path(os.environ.get("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma")))

# Manifest du corpus 
MANIFEST_PATH: Path = RAG_DIR / "corpus_manifest.csv"
# Journal d'extraction
EXTRACTION_LOG_PATH: Path = PROCESSED_DIR / "_extraction_log.csv"

# Embeddings --
# Modèle LOCAL multilingue : souverain (RGPD), gratuit, hors-ligne, reproductible.
EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"
EMBEDDING_QUERY_PREFIX: str = "query: "
EMBEDDING_PASSAGE_PREFIX: str = "passage: "

# ChromaDB
COLLECTION_NAME: str = "endo_corpus"
DISTANCE_METRIC: str = "cosine"

# Chunking 
CHUNK_SIZE: int = 1200      # ~caractères ; calibré pour la fenêtre d'e5 (~512 tokens)
CHUNK_OVERLAP: int = 200

# Nettoyage
# En dessous de ce seuil, une extraction est considérée suspecte
MIN_CHARS_VALID: int = 300
