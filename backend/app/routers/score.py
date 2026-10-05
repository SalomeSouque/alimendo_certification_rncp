"""Routes de consultation du score d'un aliment, accès public.

Que l'aliment vienne d'une photo, d'un code-barre ou d'une recherche texte, le
frontend afficher la réponse.

Chaque réponse porte le disclaimer, la mention « projet étudiant » et la
citation de source. 
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.disclaimers import (
    CITATION_SOURCE_COURTE,
    DISCLAIMER_SCORE,
    LIBELLE_ALTERNATIVES,
    MENTION_PROJET_ETUDIANT,
)
from app.db.session import get_session
from app.repositories import aliment_repository
from app.schemas.aliment import AlimentDetail, AlimentResume
from app.services import alternative_service, score_service

router = APIRouter(prefix="/score", tags=["score"])


@router.get(
    "/aliment/{id_aliment}",
    response_model=AlimentDetail,
    summary="Score et alternatives d'un aliment",
)
async def score_aliment(
    session: Annotated[AsyncSession, Depends(get_session)],
    id_aliment: Annotated[int, Path(ge=1)],
) -> AlimentDetail:
    """Calcule le score d'un aliment et propose des alternatives.

    Raises:
        HTTPException: 404 si l'aliment n'existe pas.
    """
    aliment = await aliment_repository.get_by_id(session, id_aliment)
    if aliment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aliment introuvable.",
        )

    score = score_service.scorer_aliment(aliment)
    badges = score_service.badges_aliment(aliment)
    alternatives = await alternative_service.trouver_alternatives(session, aliment)

    return AlimentDetail(
        aliment=AlimentResume.model_validate(aliment),
        score=score,
        badges=badges,
        alternatives=alternatives,
        libelle_alternatives=LIBELLE_ALTERNATIVES,
        disclaimer=DISCLAIMER_SCORE,
        mention_projet_etudiant=MENTION_PROJET_ETUDIANT,
        citation_source=CITATION_SOURCE_COURTE,
    )


@router.get(
    "/code-barre/{code}",
    response_model=AlimentDetail,
    summary="Score d'un produit Open Food Facts",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def score_code_barre(code: Annotated[str, Path(min_length=8, max_length=14)]) -> AlimentDetail:
    """Score d'un produit transformé identifié par son code-barre.

    NON IMPLÉMENTÉ : le mapping des champs Open Food Facts vers les 23
    paramètres du référentiel doit d'abord être vérifié unité par unité.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Le parcours code-barre n'est pas encore disponible.",
    )
