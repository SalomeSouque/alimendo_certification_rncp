"""Schémas Pydantic des routes admin.

Données minimales (RGPD, minimisation) : ni hash, ni date de dernière connexion.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UtilisateurAdmin(BaseModel):
    """Une ligne de la liste des comptes vue par une admin."""

    id: int
    email: EmailStr
    role: str
    created_at: datetime
    acces_ia: bool


class AccesIaUpdate(BaseModel):
    """Corps de `PATCH /admin/utilisateurs/{id}/acces-ia`."""

    acces_ia: bool
