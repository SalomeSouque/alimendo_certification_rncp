"""Tests d'intégration des points de terminaison IA (/ai/chat et /ai/vision).

But du fichier : prouver que l'API donne accès aux fonctions des modèles
comme le prévoient les spécifications (critère C9-CR2) :

- /ai/chat fait passer la question par le routage d'intention (filet de
  sécurité puis classifieur) et renvoie la réponse prévue pour l'intention ;
- /ai/vision renvoie un 501 explicite tant que le VLM n'est pas branché
  (prochaine étape documentée).

Ni base de données, ni ChromaDB, ni Mistral ne sont nécessaires : les
intentions testées ici renvoient un texte figé, sans RAG ni LLM.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.disclaimers import TEXTE_DETRESSE_URGENCE, TEXTE_OUT_OF_SCOPE
from app.core.security import create_access_token
from app.db.session import get_session
from app.main import app
from app.services import intent_service
from tests.test_intent_classifier import FauxModele


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def entetes() -> dict[str, str]:
    """En-tête d'authentification d'une utilisatrice connectée."""
    jeton = create_access_token(utilisateur_id=1, email="test@example.com", role="user")
    return {"Authorization": f"Bearer {jeton}"}


def test_chat_renvoie_la_reponse_de_l_intention_predite(client, entetes, monkeypatch):
    """Le modèle classe la question hors périmètre : l'API renvoie le texte §7.1."""
    monkeypatch.setattr(intent_service, "charger_modele", lambda: FauxModele("out_of_scope"))

    reponse = client.post(
        "/ai/chat",
        json={"question": "Quel traitement hormonal choisir ?"},
        headers=entetes,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["intention"] == "out_of_scope"
    assert corps["action"] == "STATIC_RESPONSE_OOS"
    assert corps["reponse"] == TEXTE_OUT_OF_SCOPE
    assert corps["sources"] == []


def test_chat_detresse_renvoie_la_reponse_de_securite(client, entetes, monkeypatch):
    """Le filet prime : réponse §7.5, sans disclaimer, même si le modèle dit in_scope."""
    monkeypatch.setattr(intent_service, "charger_modele", lambda: FauxModele("in_scope"))

    reponse = client.post(
        "/ai/chat",
        json={"question": "j'ai tellement mal, je n'en peux plus"},
        headers=entetes,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["intention"] == "detresse_urgence"
    assert corps["reponse"] == TEXTE_DETRESSE_URGENCE
    assert corps["disclaimer"] is None


def test_chat_refuse_une_question_trop_courte(client, entetes):
    """Validation des entrées : moins de 3 caractères -> 422."""
    reponse = client.post("/ai/chat", json={"question": "ok"}, headers=entetes)

    assert reponse.status_code == 422


def test_vision_renvoie_501_tant_que_le_vlm_n_est_pas_branche(client, entetes):
    """Comportement documenté : la reconnaissance photo est une prochaine étape."""

    async def _session_factice():
        yield None

    app.dependency_overrides[get_session] = _session_factice
    try:
        reponse = client.post(
            "/ai/vision",
            files={"image": ("tomate.png", b"\x89PNG faux contenu", "image/png")},
            headers=entetes,
        )
    finally:
        app.dependency_overrides.clear()

    assert reponse.status_code == 501
    assert "pas encore disponible" in reponse.json()["detail"]
