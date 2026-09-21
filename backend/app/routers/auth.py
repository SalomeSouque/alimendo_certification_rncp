"""Routes d'authentification.

Basculer `VITE_AUTH_MOCK=false` doit suffire, sans toucher aux pages React.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_session
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UtilisateurPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte",
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Crée un compte et renvoie directement un jeton d'accès."""
    return await auth_service.inscrire(
        session, email=payload.email, password=payload.password
    )


@router.post("/login", response_model=TokenResponse, summary="Se connecter")
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Vérifie les identifiants et renvoie un jeton d'accès."""
    return await auth_service.authentifier(
        session, email=payload.email, password=payload.password
    )


@router.get("/me", response_model=UtilisateurPublic, summary="Utilisateur courant")
async def me(
    utilisateur: Annotated[CurrentUser, Depends(get_current_user)],
) -> UtilisateurPublic:
    """Renvoie l'utilisateur associé au jeton fourni.

    Le frontend appelle cette route au chargement pour savoir si le jeton
    conservé en localStorage est encore valide. Un 401 déconnecte.
    """
    return UtilisateurPublic(
        id=utilisateur.id, email=utilisateur.email, role=utilisateur.role
    )
