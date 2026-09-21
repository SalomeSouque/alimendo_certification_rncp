"""Schémas Pydantic de l'authentification.


* `POST /auth/login` -> `{ "access_token": ..., "user": { "id", "email", "role" } }`
* `GET  /auth/me`    -> `{ "id", "email", "role" }`

Ne pas modifier ces noms de champs sans mettre à jour `services/auth.js` côté
React : permet de basculer `VITE_AUTH_MOCK=false` sans toucher aux pages.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UtilisateurPublic(BaseModel):
    """Représentation d'un utilisateur exposée par l'API.

    Ne contient jamais le hash du mot de passe.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str


class LoginRequest(BaseModel):
    """Corps de `POST /auth/login`."""

    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    """Corps de `POST /auth/register`.

    La longueur minimale de 8 caractères (OWASP A07)
    Aucune règle de complexité imposée (déconseillées au profit de la longueur.)
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Réponse de `POST /auth/login`"""

    access_token: str
    token_type: str = "bearer"
    user: UtilisateurPublic
