"""Encodage des questions en vecteurs , côté requête du RAG.

Doit produire les mêmes vecteurs que `rag/ingestion.py`. 
Trois paramètres identiques :

1. le modèle , `intfloat/multilingual-e5-base` ;
2. le préfixe , `"query: "` pour une question, `"passage: "` pour un chunk ;
3. la normalisation , vecteurs unitaires, cohérents avec la métrique cosinus.

"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_chroma_settings

logger = logging.getLogger(__name__)


class EmbeddingIndisponibleError(RuntimeError):
    """Levée quand le modèle d'embeddings ne peut pas être chargé.

    Traduite en 503 par le router.
    """


@lru_cache(maxsize=1)
def _get_model():
    """Charge le modèle d'embeddings une seule fois.

    Raises:
        EmbeddingIndisponibleError: si sentence-transformers n'est pas disponible.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise EmbeddingIndisponibleError(
            "sentence-transformers n'est pas installé : le chatbot RAG ne peut "
            "pas encoder les questions. Installez-le avec "
            "`uv add sentence-transformers`."
        ) from exc

    settings = get_chroma_settings()
    logger.info("chargement du modèle d'embeddings : %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def encoder_question(question: str) -> list[float]:
    """Encode une question en vecteur, avec le préfixe e5 attendu.

    Args:
        question: la question posée par l'utilisatrice.

    Returns:
        Le vecteur normalisé, prêt pour une recherche cosinus dans ChromaDB.
    """
    settings = get_chroma_settings()
    texte = settings.query_prefix + question
    vecteur = _get_model().encode(
        [texte], normalize_embeddings=True, show_progress_bar=False
    )
    return vecteur[0].tolist()


def prechauffer() -> None:
    """Force le chargement du modèle au démarrage de l'application.

    """
    _get_model()
