"""Sécurité : hachage des mots de passe, jetons JWT et dépendances FastAPI.

"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import SecuritySettings, get_security_settings

# `auto_error=False` gestion du 401 pour renvoyer un message FR

_bearer_scheme = HTTPBearer(auto_error=False)



# Mots de passe

def hash_password(plain_password: str) -> str:
    """Hache un mot de passe en clair avec bcrypt.

    Le sel est généré aléatoirement et stocké dans le hash lui-même.

    Args:
        plain_password: mot de passe saisi par l'utilisatrice.

    Returns:
        Le hash bcrypt, prêt à être stocké en base.
    """
    settings = get_security_settings()
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe en clair contre son hash bcrypt.

    Ne lève jamais : un hash corrompu en base renvoie simplement False (=401), un 500 révélerait un problème
    interne à un attaquant.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False



# Jetons JWT

def create_access_token(*, utilisateur_id: int, email: str, role: str) -> str:
    """Fabrique un jeton d'accès signé.

    Le payload :
    Args:
        utilisateur_id: clé primaire de l'utilisateur (claim `sub`).
        email: email de l'utilisateur.
        role: libellé du rôle ("user" ou "admin").

    Returns:
        Le jeton encodé.
    """
    settings = get_security_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(utilisateur_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: SecuritySettings | None = None) -> dict[str, Any]:
    """Décode et valide un jeton d'accès.

    Raises:
        HTTPException: 401 si le jeton est expiré, mal signé ou malformé.
    """
    settings = settings or get_security_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée, reconnectez-vous.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'authentification invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc



# Dépendances FastAPI

class CurrentUser:
    """Utilisateur authentifié, tel qu'extrait du JWT.

    Volontairement découplé du modèle ORM : une route protégée n'a pas besoin
    d'un aller-retour en base pour connaître l'identité de l'appelant.
    """

    __slots__ = ("email", "id", "role")

    def __init__(self, *, id: int, email: str, role: str) -> None:
        self.id = id
        self.email = email
        self.role = role

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"CurrentUser(id={self.id}, email={self.email!r}, role={self.role!r})"


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> CurrentUser:
    """Dépendance : exige un JWT valide et renvoie l'utilisateur courant.

    Usage :
        @router.get("/me")
        async def me(user: Annotated[CurrentUser, Depends(get_current_user)]): ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")

    if subject is None or email is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'authentification incomplet.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        utilisateur_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'authentification invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentUser(id=utilisateur_id, email=email, role=role)


def require_role(*roles: str):
    """Fabrique une dépendance qui exige l'un des rôles donnés.

    Usage :
        @router.get("/admin/logs", dependencies=[Depends(require_role("admin"))])

    Renvoie 403 (et non 401) : l'utilisateur authentifié -> pas le droit d'accéder à la ressource.
    """
    autorises = set(roles)

    async def _checker(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if user.role not in autorises:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour accéder à cette ressource.",
            )
        return user

    return _checker


async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Dépendance : garde-fou X-API-Key, actif seulement si la clé est configurée.

    """
    settings = get_security_settings()
    if not settings.api_key_enabled:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API manquante ou invalide.",
        )
