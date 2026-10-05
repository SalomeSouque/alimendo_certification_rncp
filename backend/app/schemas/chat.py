"""Schémas Pydantic du chatbot RAG."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceCitee(BaseModel):
    """Source documentaire citée dans une réponse du chatbot.

    """

    model_config = ConfigDict(from_attributes=True)

    id_source: str
    titre: str
    url: str | None = None
    licence_indicative: str | None = None
    score_similarite: float = Field(
        description="1 - distance cosinus ; 1 = identique, 0 = sans rapport."
    )


class ChatRequest(BaseModel):
    """Corps de `POST /ai/chat`."""

    question: str = Field(min_length=3, max_length=1000)


class ChatResponse(BaseModel):
    """Réponse du chatbot.

    `intention` et `action` documentent la décision du routeur : seule `in_scope` déclenche le pipeline RAG.

    `disclaimer` est nullable : les réponses de détresse et de restriction. 
    """

    reponse: str
    intention: str = Field(
        description=(
            "detresse_urgence | restriction_alimentaire | out_of_scope | "
            "food_specific | in_scope"
        )
    )
    action: str = Field(
        description=(
            "SAFE_RESPONSE_DISTRESS | SAFE_RESPONSE_RESTRICTION | "
            "STATIC_RESPONSE_OOS | REDIRECT_SCAN | RAG_RETRIEVAL"
        )
    )
    sources: list[SourceCitee] = Field(default_factory=list)
    disclaimer: str | None = Field(
        default=None,
        description="Disclaimer court à afficher sous la réponse, ou null.",
    )


class VisionResponse(BaseModel):
    """Réponse de `POST /ai/vision` : reconnaissance d'aliment par photo."""

    label_identifie: str | None = None
    score_confiance: float | None = None
    statut: str = Field(description="reconnu | non_rapproche | echec")
    id_aliment: int | None = Field(
        default=None, description="Aliment rapproché en base, si le rapprochement a abouti."
    )
    message: str | None = None
