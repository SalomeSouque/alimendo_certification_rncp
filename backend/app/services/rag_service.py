"""Orchestration du chatbot RAG

Enchaînement : routage d'intention -> puis selon l'intention recherche vectorielle et génération.

Quatre des cinq intentions stop le pipeline et renvoient un texte figé des guidelines.

"""

from __future__ import annotations

import logging

from app.core.disclaimers import (
    DISCLAIMER_CHATBOT_COURT,
    SECTIONS_SANS_DISCLAIMER,
    TEXTE_FALLBACK,
    texte_valide,
)
from app.schemas.chat import ChatResponse, SourceCitee
from app.services import chroma_service, embedding_service, intent_service, llm_mistral
from app.services.intent_service import ResultatRoutage

logger = logging.getLogger(__name__)


def _disclaimer_pour(text_ref: str) -> str | None:
    """Détermine le disclaimer à joindre à une réponse.

    Les réponses détresse restriction n'en portent pas, le texte porte déjà son message.
    """
    if text_ref in SECTIONS_SANS_DISCLAIMER:
        return None
    return DISCLAIMER_CHATBOT_COURT


def _reponse_figee(resultat: ResultatRoutage) -> ChatResponse:
    """Construit une réponse à partir d'un texte figé des guidelines.

    Aucun appel à l'index ni au modèle de génération.
    """
    text_ref = resultat.routage.text_ref
    return ChatResponse(
        reponse=texte_valide(text_ref),
        intention=resultat.intent.value,
        action=resultat.routage.action,
        sources=[],
        disclaimer=_disclaimer_pour(text_ref),
    )


def _extraire_sources(resultat: dict) -> tuple[list[str], list[SourceCitee]]:
    """Transforme la réponse brute de ChromaDB en extraits et sources citées.

    Les métadonnées attendues sont celles posées à l'ingestion : `id_source`,
    `titre`, `url`, `licence_indicative`. La distance cosinus est convertie en
    score de similarité (1 − distance) pour rester lisible.
    """
    documents = (resultat.get("documents") or [[]])[0]
    metadonnees = (resultat.get("metadatas") or [[]])[0]
    distances = (resultat.get("distances") or [[]])[0]

    extraits: list[str] = []
    sources: list[SourceCitee] = []

    for document, meta, distance in zip(documents, metadonnees, distances, strict=False):
        extraits.append(document)
        sources.append(
            SourceCitee(
                id_source=str(meta.get("id_source", "inconnue")),
                titre=str(meta.get("titre", "Source sans titre")),
                url=meta.get("url"),
                licence_indicative=meta.get("licence_indicative"),
                score_similarite=round(1 - float(distance), 3),
            )
        )

    return extraits, sources


async def repondre(question: str) -> ChatResponse:
    """Traite une question du chatbot de bout en bout.

    Args:
        question: la question posée par l'utilisatrice.

    Returns:
        La réponse, avec ses sources éventuelles et le disclaimer adéquat.

    Raises:
        embedding_service.EmbeddingIndisponibleError: modèle d'embeddings
            inaccessible.
        chroma_service.IndexIndisponibleError: index vectoriel injoignable.
        llm_mistral.LLMIndisponibleError: génération en échec.
    """
    resultat = intent_service.router(question)

    # Quatre intentions sur cinq s'arrêtent ici : ni retrieval, ni LLM.
    if not resultat.routage.retrieval:
        logger.info(
            "routage sans retrieval : intent=%s action=%s",
            resultat.intent.value,
            resultat.routage.action,
        )
        return _reponse_figee(resultat)

    vecteur = embedding_service.encoder_question(question)
    brut = chroma_service.rechercher(vecteur)
    extraits, sources = _extraire_sources(brut)

    # Repli : rien de pertinent n'est remonté. On n'invente pas, on ne
    # complète pas depuis la connaissance générale du modèle.
    if not extraits:
        logger.warning("aucun extrait remonté - bascule sur le repli §7.3")
        return ChatResponse(
            reponse=TEXTE_FALLBACK,
            intention=resultat.intent.value,
            action=resultat.routage.action,
            sources=[],
            disclaimer=DISCLAIMER_CHATBOT_COURT,
        )

    reponse = await llm_mistral.generer_reponse(question, extraits)

    return ChatResponse(
        reponse=reponse,
        intention=resultat.intent.value,
        action=resultat.routage.action,
        sources=sources,
        disclaimer=DISCLAIMER_CHATBOT_COURT,
    )
