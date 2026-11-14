"""Tests de l'accès IA sur validation (lot 36, OWASP API5).

Vérifie que :

- un compte inscrit mais non validé reçoit un 403 explicite sur /ai/* ;
- après validation par une admin, le même jeton passe (200) ;
- une révocation agit au prochain appel, sans attendre l'expiration du jeton ;
- les routes /admin sont refusées sans jeton (401) et à un compte non admin (403) ;
- l'échec de connexion ne journalise pas l'email saisi.

Pas de base : la session est une doublure et `get_by_id` renvoie le compte
simulé de `compte_valide` (conftest.py).
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from app.core.security import MESSAGE_ACCES_IA_EN_ATTENTE, create_access_token
from app.repositories import user_repository
from app.schemas.chat import ChatResponse
from app.services import rag_service

QUESTION = {"question": "Comment l'alimentation influence-t-elle l'inflammation ?"}


@pytest.fixture
def entetes_admin() -> dict[str, str]:
    jeton = create_access_token(utilisateur_id=99, email="admin@example.com", role="admin")
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture
def faux_rag(monkeypatch) -> None:
    reponse = ChatResponse(reponse="Réponse simulée.", intention="in_scope", action="RAG_RETRIEVAL")
    monkeypatch.setattr(rag_service, "repondre", AsyncMock(return_value=reponse))


@pytest.mark.parametrize("chemin", ["/ai/chat", "/ai/vision"])
def test_compte_non_valide_recoit_403(client_api, entetes_auth, compte_valide, chemin):
    compte_valide.acces_ia = False

    reponse = client_api.post(chemin, json=QUESTION, headers=entetes_auth)

    assert reponse.status_code == 403
    assert reponse.json()["detail"] == MESSAGE_ACCES_IA_EN_ATTENTE


def test_compte_supprime_recoit_401(client_api, entetes_auth, monkeypatch):
    """Jeton encore valide mais compte supprimé (tri RGPD) : 401, pas 500."""
    monkeypatch.setattr(user_repository, "get_by_id", AsyncMock(return_value=None))

    reponse = client_api.post("/ai/chat", json=QUESTION, headers=entetes_auth)

    assert reponse.status_code == 401


def test_validation_puis_revocation_agissent_sur_le_meme_jeton(
    client_api, entetes_auth, entetes_admin, compte_valide, faux_rag
):
    compte_valide.acces_ia = False
    assert client_api.post("/ai/chat", json=QUESTION, headers=entetes_auth).status_code == 403

    ouverture = client_api.patch(
        "/admin/utilisateurs/1/acces-ia", json={"acces_ia": True}, headers=entetes_admin
    )
    assert ouverture.status_code == 200
    assert ouverture.json()["acces_ia"] is True
    assert client_api.post("/ai/chat", json=QUESTION, headers=entetes_auth).status_code == 200

    fermeture = client_api.patch(
        "/admin/utilisateurs/1/acces-ia", json={"acces_ia": False}, headers=entetes_admin
    )
    assert fermeture.status_code == 200
    assert client_api.post("/ai/chat", json=QUESTION, headers=entetes_auth).status_code == 403


def test_me_expose_acces_ia(client_api, entetes_auth, compte_valide):
    compte_valide.acces_ia = False

    reponse = client_api.get("/auth/me", headers=entetes_auth)

    assert reponse.status_code == 200
    assert reponse.json()["acces_ia"] is False


def test_admin_liste_les_comptes_avec_donnees_minimales(
    client_api, entetes_admin, compte_valide, monkeypatch
):
    monkeypatch.setattr(user_repository, "lister", AsyncMock(return_value=[compte_valide]))

    reponse = client_api.get("/admin/utilisateurs", headers=entetes_admin)

    assert reponse.status_code == 200
    assert set(reponse.json()[0]) == {"id", "email", "role", "created_at", "acces_ia"}


def test_admin_patch_compte_inconnu_renvoie_404(client_api, entetes_admin, monkeypatch):
    monkeypatch.setattr(user_repository, "get_by_id", AsyncMock(return_value=None))

    reponse = client_api.patch(
        "/admin/utilisateurs/404/acces-ia", json={"acces_ia": True}, headers=entetes_admin
    )

    assert reponse.status_code == 404


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("get", "/admin/utilisateurs"), ("patch", "/admin/utilisateurs/1/acces-ia")],
)
def test_routes_admin_refusees_a_un_compte_non_admin(client_api, entetes_auth, methode, chemin):
    reponse = client_api.request(methode, chemin, json={"acces_ia": True}, headers=entetes_auth)

    assert reponse.status_code == 403


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("get", "/admin/utilisateurs"), ("patch", "/admin/utilisateurs/1/acces-ia")],
)
def test_routes_admin_refusees_sans_jeton(client_api, methode, chemin):
    reponse = client_api.request(methode, chemin, json={"acces_ia": True})

    assert reponse.status_code == 401


def test_echec_de_connexion_ne_journalise_pas_l_email(client_api, monkeypatch, caplog):
    monkeypatch.setattr(user_repository, "get_by_email", AsyncMock(return_value=None))

    with caplog.at_level(logging.WARNING):
        reponse = client_api.post(
            "/auth/login", json={"email": "lea@example.com", "password": "x"}
        )

    assert reponse.status_code == 401
    for enregistrement in caplog.records:
        assert "lea@example.com" not in enregistrement.getMessage()
        assert "lea@example.com" not in str(vars(enregistrement))
