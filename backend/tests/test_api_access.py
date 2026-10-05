"""Tests d'intégration du contrôle d'accès 

Vérifie le périmètre d'authentification décidé avec le
frontend : les features IA sont protégées, le reste est public. Ne
nécessit pas de db, les dépendances de sécurité s'exécutent avant d'atteindre la couche de persistance.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_est_public(client):
    """La sonde de vivacité ne doit jamais demander d'authentification."""
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


@pytest.mark.parametrize("chemin", ["/ai/chat", "/ai/vision"])
def test_features_ia_protegees_sans_jeton(client, chemin):
    """Sans jeton, les deux features IA renvoient 401."""
    reponse = client.post(chemin, json={"question": "Qu'est-ce que l'endométriose ?"})

    assert reponse.status_code == 401


@pytest.mark.parametrize("chemin", ["/ai/chat", "/ai/vision"])
def test_features_ia_refusent_un_jeton_invalide(client, chemin):
    """Un jeton fantaisiste ne doit pas passer."""
    reponse = client.post(
        chemin,
        json={"question": "Qu'est-ce que l'endométriose ?"},
        headers={"Authorization": "Bearer pas-un-vrai-jeton"},
    )

    assert reponse.status_code == 401


def test_jeton_valide_franchit_le_mur_dauthentification(client):
    """Avec un jeton valide, on dépasse la couche d'authentification.

    """
    jeton = create_access_token(utilisateur_id=1, email="test@example.com", role="user")

    reponse = client.post(
        "/ai/chat",
        json={"question": "Comment l'alimentation influence-t-elle l'inflammation ?"},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    assert reponse.status_code != 401


def test_recherche_est_publique(client, monkeypatch):
    """La recherche par nom reste accessible sans compte.

    Le dépôt de données est simulé : ce test porte sur le contrôle d'accès et
    le contrat de réponse, pas sur le SQL.
    """
    async def _faux_resultat(session, terme, *, limite=20):
        return []

    monkeypatch.setattr(
        "app.repositories.aliment_repository.rechercher_par_nom", _faux_resultat
    )

    reponse = client.get("/search/aliments", params={"q": "tomate"})

    assert reponse.status_code == 200
    assert reponse.json()["nombre_resultats"] == 0
