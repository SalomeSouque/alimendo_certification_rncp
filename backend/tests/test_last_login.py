"""Tests de la date de dernière connexion (procédure de tri RGPD).

La procédure de tri supprime les comptes inactifs depuis 3 ans : elle dépend
de `last_login`. Ces tests vérifient que la date est posée à chaque connexion
réussie, et seulement dans ce cas. Pas de base réelle : la session et le
repository sont remplacés par des doublures.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.security import hash_password
from app.repositories import user_repository
from app.services import auth_service


def _faux_utilisateur(mot_de_passe: str) -> SimpleNamespace:
    """Utilisateur minimal, avec ce que le service lit pour émettre le jeton."""
    return SimpleNamespace(
        id_utilisateur=1,
        email="test@example.com",
        password=hash_password(mot_de_passe),
        role=SimpleNamespace(libelle="user"),
        last_login=None,
    )


def _fausse_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def test_connexion_reussie_met_a_jour_last_login(monkeypatch):
    utilisateur = _faux_utilisateur("motdepasse-correct")
    session = _fausse_session()
    monkeypatch.setattr(
        user_repository, "get_by_email", AsyncMock(return_value=utilisateur)
    )

    avant = datetime.now(UTC)
    asyncio.run(
        auth_service.authentifier(
            session, email="test@example.com", password="motdepasse-correct"
        )
    )

    assert utilisateur.last_login is not None
    assert utilisateur.last_login >= avant
    session.commit.assert_awaited_once()


def test_echec_de_connexion_ne_touche_pas_last_login(monkeypatch):
    utilisateur = _faux_utilisateur("motdepasse-correct")
    session = _fausse_session()
    monkeypatch.setattr(
        user_repository, "get_by_email", AsyncMock(return_value=utilisateur)
    )

    with pytest.raises(HTTPException) as erreur:
        asyncio.run(
            auth_service.authentifier(
                session, email="test@example.com", password="motdepasse-faux"
            )
        )

    assert erreur.value.status_code == 401
    assert utilisateur.last_login is None
    session.commit.assert_not_awaited()
