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
    ATTRIBUTION_OPEN_FOOD_FACTS,
    CITATION_SOURCE_COURTE,
    DISCLAIMER_SCORE,
    LIBELLE_ALTERNATIVES,
    MENTION_PROJET_ETUDIANT,
)
from app.db.session import get_session
from app.repositories import aliment_repository
from app.schemas.aliment import AlimentDetail, AlimentResume
from app.services import alternative_service, openfoodfacts_service, score_service

router = APIRouter(prefix="/score", tags=["score"])


@router.get(
    "/aliment/{id_aliment}",
    response_model=AlimentDetail,
    summary="Score et alternatives d'un aliment",
    responses={404: {"description": "Aliment introuvable."}},
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
    responses={
        404: {"description": "Produit inconnu d'Open Food Facts."},
        503: {"description": "Open Food Facts injoignable ou en erreur."},
    },
)
async def score_code_barre(
    code: Annotated[
        str,
        Path(pattern=r"^\d{8,14}$", description="Code-barre EAN : 8 à 14 chiffres"),
    ],
) -> AlimentDetail:
    """Score d'un produit transformé identifié par son code-barre.

    Le produit est demandé à Open Food Facts au moment de l'appel, il n'est
    pas stocké en base (docs/specs_extraction.md, § 5). Pas d'alternatives
    pour un produit transformé : prévu en V2.

    Raises:
        HTTPException: 404 si OFF ne connaît pas ce code-barre,
            503 si OFF est injoignable.
    """
    try:
        produit = await openfoodfacts_service.recuperer_produit(code)
    except openfoodfacts_service.OpenFoodFactsIndisponibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Open Food Facts est temporairement indisponible, réessayez dans un instant.",
        ) from exc

    if produit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit introuvable dans Open Food Facts.",
        )

    return AlimentDetail(
        aliment=AlimentResume(
            id_aliment=None,
            nom=produit.nom,
            source="OFF",
            url_image=produit.url_image,
        ),
        score=score_service.scorer_profil(produit.profil),
        badges=score_service.badges_profil(produit.profil),
        alternatives=[],
        libelle_alternatives=LIBELLE_ALTERNATIVES,
        disclaimer=DISCLAIMER_SCORE,
        mention_projet_etudiant=MENTION_PROJET_ETUDIANT,
        citation_source=f"{CITATION_SOURCE_COURTE} {ATTRIBUTION_OPEN_FOOD_FACTS}",
    )