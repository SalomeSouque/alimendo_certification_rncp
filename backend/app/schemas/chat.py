"""Schémas Pydantic du chatbot RAG."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.aliment import AlimentDetail

# Caractères de contrôle invisibles (octets nuls, retour arrière, échappements
# de terminal...). On garde seulement la tabulation (\x09) et le saut de ligne
# (\x0a), utiles dans une question écrite sur plusieurs lignes.
_CARACTERES_DE_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


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

    @field_validator("question", mode="before")
    @classmethod
    def nettoyer_question(cls, valeur: object) -> object:
        """Nettoie la question avant qu'elle n'atteigne le classifieur et le prompt.

        Exécuté avant la vérification des longueurs (mode="before") : une
        question faite seulement d'espaces ou de caractères invisibles est
        donc refusée en 422 par min_length, au lieu de partir vers Mistral.
        Une valeur qui n'est pas une chaîne est laissée telle quelle :
        Pydantic la refusera ensuite avec son message habituel.
        """
        if not isinstance(valeur, str):
            return valeur
        return _CARACTERES_DE_CONTROLE.sub("", valeur).strip()


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
    """Réponse de `POST /ai/vision` : reconnaissance d'aliment par photo.

    Quand l'aliment est reconnu et rapproché de la base, `resultat` porte la
    même charge utile que `GET /score/aliment/{id}` (score, badges,
    alternatives, disclaimer, mention projet étudiant). Sinon `resultat` est
    null et `message` oriente vers la recherche par nom.
    """

    statut: str = Field(description="reconnu | non_rapproche | echec")
    contenu: str | None = Field(
        default=None,
        description=(
            "Classement de la photo par le VLM : aliment_unique | "
            "plusieurs_aliments | plat_prepare | aucun_aliment. Null si le VLM "
            "n'a pas renvoyé de réponse exploitable."
        ),
    )
    label_identifie: str | None = None
    score_confiance: float | None = Field(
        default=None,
        description="Confiance déclarée par le modèle (0 à 1), indicative et peu calibrée.",
    )
    id_aliment: int | None = Field(
        default=None, description="Aliment rapproché en base, si le rapprochement a abouti."
    )
    resultat: AlimentDetail | None = Field(
        default=None, description="Score et alternatives de l'aliment reconnu."
    )
    message: str | None = None