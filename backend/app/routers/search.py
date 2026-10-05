"""Routes de recherche d'aliments, accès public.

Rappel du périmètre d'authentification décidé côté frontend : seules les deux
features IA (photo et chatbot) sont derrière un mur de connexion. La recherche
par nom et le scan code-barre restent accessibles sans compte.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories import aliment_repository
from app.schemas.aliment import AlimentResume, CategorieOut, RechercheResultat

router = APIRouter(prefix="/search", tags=["recherche"])


@router.get(
    "/aliments",
    response_model=RechercheResultat,
    summary="Rechercher un aliment par nom",
)
async def rechercher_aliments(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str, Query(min_length=2, max_length=100, description="Terme recherché")],
    limite: Annotated[int, Query(ge=1, le=50)] = 20,
) -> RechercheResultat:
    """Recherche tolérante aux fautes de frappe et aux variantes orthographiques.

    Une liste vide affiche un message explicite « aucun résultat » dans le frontend.
    """
    aliments = await aliment_repository.rechercher_par_nom(session, q, limite=limite)
    return RechercheResultat(
        terme=q,
        nombre_resultats=len(aliments),
        resultats=[AlimentResume.model_validate(a) for a in aliments],
    )


@router.get(
    "/categories",
    response_model=list[CategorieOut],
    summary="Lister les catégories alimentaires",
)
async def lister_categories(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CategorieOut]:
    """Liste les catégories utilisées par le filtrage et les alternatives."""
    categories = await aliment_repository.lister_categories(session)
    return [CategorieOut.model_validate(c) for c in categories]
