"""Routes réservées au rôle admin : validation de l'accès IA des comptes.

Le rôle est lu dans le JWT (`require_role`). Limite connue : un compte retiré
du rôle admin garde ses droits jusqu'à l'expiration de son jeton (60 min).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.models import ROLE_ADMIN, Utilisateur
from app.db.session import get_session
from app.repositories import user_repository
from app.schemas.admin import AccesIaUpdate, UtilisateurAdmin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(ROLE_ADMIN))],
    responses={
        401: {"description": "Jeton absent, invalide ou expiré."},
        403: {"description": "Compte sans rôle admin."},
    },
)


def _vers_admin(utilisateur: Utilisateur) -> UtilisateurAdmin:
    return UtilisateurAdmin(
        id=utilisateur.id_utilisateur,
        email=utilisateur.email,
        role=utilisateur.role.libelle,
        created_at=utilisateur.created_at,
        acces_ia=utilisateur.acces_ia,
    )


@router.get(
    "/utilisateurs",
    response_model=list[UtilisateurAdmin],
    summary="Lister les comptes",
)
async def lister_utilisateurs(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[UtilisateurAdmin]:
    """Liste les comptes avec leur accès IA, du plus récent au plus ancien."""
    return [_vers_admin(u) for u in await user_repository.lister(session)]


@router.patch(
    "/utilisateurs/{id_utilisateur}/acces-ia",
    response_model=UtilisateurAdmin,
    summary="Ouvrir ou fermer l'accès IA d'un compte",
    responses={404: {"description": "Compte introuvable."}},
)
async def modifier_acces_ia(
    id_utilisateur: int,
    payload: AccesIaUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UtilisateurAdmin:
    """Valide ou révoque l'accès IA. Effet immédiat sur le prochain appel /ai/*."""
    utilisateur = await user_repository.get_by_id(session, id_utilisateur)
    if utilisateur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable."
        )
    await user_repository.definir_acces_ia(session, utilisateur, payload.acces_ia)
    await session.commit()
    return _vers_admin(utilisateur)
