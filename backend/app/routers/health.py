"""Endpoints de santé : support du monitoring applicatif.

Deux niveaux volontairement distincts :

- `/health` : réponse immédiate, sans dépendance. 
* `/health/detail` : état de chaque dépendance, pour le diagnostic et les tableaux de bord.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.score import VERSION_REFERENTIEL, referentiel_est_pret
from app.services import chroma_service

router = APIRouter(tags=["santé"])


@router.get("/health", summary="Sonde de vivacité")
async def health() -> dict[str, str]:
    """Indique que le processus répond. Aucune dépendance interrogée."""
    return {"status": "ok"}


@router.get("/health/detail", summary="État détaillé des dépendances")
async def health_detail(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Vérifie chaque dépendance et renvoie son état.

    Ne renvoie jamais une erreur HTTP : l'intérêt est justement de pouvoir
    lire quelle brique est tombée.
    """
    try:
        await session.execute(text("SELECT 1"))
        base_de_donnees = "ok"
    except Exception as exc:  # noqa: BLE001, on veut le diagnostic, pas une 500
        base_de_donnees = f"indisponible : {type(exc).__name__}"

    return {
        "status": "ok",
        "base_de_donnees": base_de_donnees,
        "index_vectoriel": "ok" if chroma_service.est_disponible() else "indisponible",
        "referentiel_score": "ok" if referentiel_est_pret() else "reperes_manquants",
        "version_referentiel": VERSION_REFERENTIEL,
    }
