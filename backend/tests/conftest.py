"""Fixtures partagées par les tests.

Les tests d'API n'utilisent ni base PostgreSQL, ni ChromaDB, ni Mistral :
la session de base est remplacée par une doublure et les services externes
sont simulés test par test. La CI reste rapide et ne dépend pas du réseau.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("POSTGRES_USER", "alimendo_test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "alimendo_test")
os.environ.setdefault("JWT_SECRET_KEY", "secret-de-test-non-utilise-en-production")
os.environ.setdefault("MISTRAL_API_KEY", "cle-de-test")
# bcrypt à 4 tours : le minimum autorisé, pour que la suite de tests reste rapide.
os.environ.setdefault("BCRYPT_ROUNDS", "4")

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_session
from app.domain.score.referential_v1 import COEFS, LandmarkParameter
from app.main import app
from app.repositories import user_repository


@pytest.fixture
def synthetic_landmarks() -> dict[str, LandmarkParameter]:
    """Repères de normalisation artificiels, identiques pour tous les paramètres.

    med=10, p10=0, p90=20 : une teneur de 20 donne une normalisation de +1,
    une teneur de 0 donne −1, une teneur de 10 donne 0, Rendant les
    résultats calculables à la main.

    """
    return {nom: LandmarkParameter(med=10.0, p10=0.0, p90=20.0) for nom in COEFS}


@pytest.fixture
def patch_landmarks(monkeypatch, synthetic_landmarks):
    """Remplace les repères réels par les repères synthétiques."""
    monkeypatch.setattr(
        "app.domain.score.calcul.get_landmarks", lambda: synthetic_landmarks
    )
    return synthetic_landmarks


# Fixtures des tests d'API


@pytest.fixture
def session_factice() -> Iterator[AsyncMock]:
    """Remplace la session PostgreSQL par une doublure.

    Les routes reçoivent cette doublure à la place d'une vraie connexion.
    Les fonctions du repository sont simulées dans chaque test, la doublure
    sert seulement à absorber les appels comme `commit()`.
    """
    session = AsyncMock()

    async def _fournir_session():
        yield session

    app.dependency_overrides[get_session] = _fournir_session
    yield session
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def client_api(session_factice) -> TestClient:
    """Client HTTP de test, branché sur la session factice.

    Sans `with TestClient(...)`, le lifespan ne s'exécute pas : aucune
    connexion à la base n'est ouverte au démarrage.
    """
    return TestClient(app)


@pytest.fixture
def compte_valide(monkeypatch) -> SimpleNamespace:
    """Compte n°1 en base, accès IA validé.

    `get_by_id` est simulé : `/auth/me` et la dépendance des routes /ai/*
    relisent le compte en base. Passer `acces_ia` à False dans un test
    simule un compte en attente ou révoqué.
    """
    compte = SimpleNamespace(
        id_utilisateur=1,
        email="test@example.com",
        role=SimpleNamespace(libelle="user"),
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        acces_ia=True,
    )
    monkeypatch.setattr(user_repository, "get_by_id", AsyncMock(return_value=compte))
    return compte


@pytest.fixture
def entetes_auth(compte_valide) -> dict[str, str]:
    """En-tête d'une utilisatrice connectée (jeton valide, rôle user, accès IA validé)."""
    jeton = create_access_token(utilisateur_id=1, email="test@example.com", role="user")
    return {"Authorization": f"Bearer {jeton}"}