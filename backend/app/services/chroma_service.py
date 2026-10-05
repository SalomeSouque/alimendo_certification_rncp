"""Accès à l'index vectoriel ChromaDB, côté requête.

"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_chroma_settings

logger = logging.getLogger(__name__)


class IndexIndisponibleError(RuntimeError):
    """Levée quand l'index vectoriel est injoignable ou vide."""


@lru_cache(maxsize=1)
def _get_client():
    """Ouvre un client HTTP vers le service ChromaDB (mis en cache).

    Raises:
        IndexIndisponibleError: si le paquet chromadb est absent.
    """
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise IndexIndisponibleError(
            "Le paquet chromadb n'est pas installé dans le backend."
        ) from exc

    settings = get_chroma_settings()
    logger.info("connexion à ChromaDB : %s:%s", settings.host, settings.port)
    return chromadb.HttpClient(host=settings.host, port=settings.port)


def get_collection():
    """Récupère la collection du corpus RAG.

    Raises:
        IndexIndisponibleError: si le service est injoignable ou la collection
            absente.
    """
    settings = get_chroma_settings()
    try:
        return _get_client().get_collection(name=settings.collection_name)
    except Exception as exc:  # chromadb lève des exceptions variées selon la version
        raise IndexIndisponibleError(
            f"Collection {settings.collection_name!r} introuvable sur "
            f"{settings.host}:{settings.port}. L'ingestion RAG a-t-elle été "
            "lancée contre ce service ?"
        ) from exc


def rechercher(vecteur_question: list[float], *, n_resultats: int | None = None) -> dict[str, Any]:
    """Interroge l'index avec un vecteur de question déjà encodé.

    Args:
        vecteur_question: vecteur normalisé produit par `embedding_service`.
        n_resultats: nombre de chunks à remonter ; défaut = `RAG_TOP_K`.

    Returns:
        La réponse brute de ChromaDB (documents, métadonnées, distances).

    Raises:
        IndexIndisponibleError: si l'index est injoignable.
    """
    settings = get_chroma_settings()
    collection = get_collection()
    return collection.query(
        query_embeddings=[vecteur_question],
        n_results=n_resultats or settings.top_k,
    )


def est_disponible() -> bool:
    """Indique si l'index est joignable, utilisé par le healthcheck."""
    try:
        get_collection()
    except IndexIndisponibleError:
        return False
    return True
