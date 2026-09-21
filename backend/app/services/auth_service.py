"""Service d'authentification : inscription, connexion, émission du jeton."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Utilisateur
from app.repositories import user_repository
from app.schemas.auth import TokenResponse, UtilisateurPublic

logger = logging.getLogger(__name__)


def _vers_public(utilisateur: Utilisateur) -> UtilisateurPublic:
    """Projette un utilisateur ORM vers sa représentation publique."""
    return UtilisateurPublic(
        id=utilisateur.id_utilisateur,
        email=utilisateur.email,
        role=utilisateur.role.libelle,
    )


async def inscrire(
    session: AsyncSession, *, email: str, password: str
) -> TokenResponse:
    """Crée un compte et connecte immédiatement l'utilisatrice.

    Raises:
        HTTPException: 409 si l'email est déjà utilisé.
    """
    email_normalise = email.strip().lower()

    if await user_repository.get_by_email(session, email_normalise):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )

    utilisateur = await user_repository.creer(
        session,
        email=email_normalise,
        password_hash=hash_password(password),
    )
    await session.commit()

    logger.info("inscription réussie", extra={"utilisateur_id": utilisateur.id_utilisateur})
    return _emettre_jeton(utilisateur)


async def authentifier(
    session: AsyncSession, *, email: str, password: str
) -> TokenResponse:
    """Vérifie les identifiants et émet un jeton d'accès.

    Message d'erreur identique pour email inconnu ou mdp faux (OWASP A07).

    Raises:
        HTTPException: 401 si les identifiants sont invalides.
    """
    utilisateur = await user_repository.get_by_email(session, email)

    if utilisateur is None or not verify_password(password, utilisateur.password):
        # On ne journalise jamais le mot de passe saisi, ni le hash stocké.
        logger.warning("échec d'authentification", extra={"email_fourni": email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _emettre_jeton(utilisateur)


def _emettre_jeton(utilisateur: Utilisateur) -> TokenResponse:
    """Fabrique la réponse attendue par le frontend."""
    public = _vers_public(utilisateur)
    token = create_access_token(
        utilisateur_id=public.id, email=public.email, role=public.role
    )
    return TokenResponse(access_token=token, user=public)
