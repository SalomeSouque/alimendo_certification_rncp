"""Configuration centralisée du pipeline RAG offline.

Toutes les valeurs "réglables" du pipeline (extraction → chunking → ingestion)
vivent ici : chemins, modèle d'embeddings, nom de la collection Chroma,
paramètres de chunk. On évite ainsi les magic numbers dispersés dans les
modules (convention projet : configs externalisées, jamais de valeurs en dur).

Ce fichier grandira à chaque module. Pour l'étape 1 (extraction), seules les
sections Chemins et Nettoyage sont réellement utilisées ; le reste est déjà
posé pour ne pas y revenir.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Chemins ---------------------------------------------------------------
# RAG_DIR = dossier rag/ (ce fichier vit à sa racine).
RAG_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = RAG_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"              # produit par collecte.py
PROCESSED_DIR: Path = DATA_DIR / "processed"  # produit par extraction.py
# ⚠️ OBSOLÈTE : CHROMA_DIR / CHROMA_PERSIST_DIR ont été retirés. L'index n'est plus
# un dossier local (rag/data/chroma) mais vit dans le SERVICE ChromaDB du
# docker-compose, partagé avec le backend. Voir la section ChromaDB plus bas.

# Manifest du corpus = source de vérité (métadonnées + consignes de chunking).
# Adapte ce chemin si collecte.py l'a écrit ailleurs.
MANIFEST_PATH: Path = RAW_DIR / "corpus_manifest.csv"
# Journal d'extraction (traçabilité C2 : quoi nettoyé, comment, quels cas particuliers).
EXTRACTION_LOG_PATH: Path = PROCESSED_DIR / "_extraction_log.csv"

# --- Embeddings (utilisés au module ingestion) -----------------------------
# Modèle LOCAL multilingue : souverain (RGPD), gratuit, hors-ligne, reproductible.
# e5 EXIGE des préfixes "query:" / "passage:" — sinon la qualité s'effondre.
EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"
EMBEDDING_QUERY_PREFIX: str = "query: "
EMBEDDING_PASSAGE_PREFIX: str = "passage: "

# --- ChromaDB (utilisés au module ingestion) -------------------------------
# L'ingestion parle au service ChromaDB en HTTP — le MÊME index que le backend.
# Valeurs par défaut = vue depuis la machine de développement (port publié par
# le compose). Le backend, lui, utilise chromadb:8000 (réseau Docker interne) :
# c'est la même instance vue de deux endroits, la différence est normale.
CHROMA_HOST: str = os.environ.get("CHROMA_HOST", "localhost")
# CHROMA_PORT en priorité ; sinon CHROMADB_PORT (la variable qui fixe le port
# publié dans docker-compose.yml) ; sinon 8001. Évite un décalage silencieux si
# tu changes le port publié dans ton .env.
CHROMA_PORT: int = int(os.environ.get("CHROMA_PORT") or os.environ.get("CHROMADB_PORT") or "8001")

# ⚠️ Doit être IDENTIQUE à CHROMA_COLLECTION dans le .env du backend.
COLLECTION_NAME: str = os.environ.get("CHROMA_COLLECTION", "endo_corpus")
DISTANCE_METRIC: str = "cosine"

# --- Chunking (utilisés au module chunking) --------------------------------
CHUNK_SIZE: int = 1200      # ~caractères ; calibré pour la fenêtre d'e5 (~512 tokens)
CHUNK_OVERLAP: int = 200

# --- Nettoyage (utilisés dès l'extraction) ---------------------------------
# En dessous de ce seuil, une extraction est considérée suspecte (PDF illisible,
# HTML sur-nettoyé) et journalisée comme "empty" plutôt qu'écrite silencieusement.
MIN_CHARS_VALID: int = 300
