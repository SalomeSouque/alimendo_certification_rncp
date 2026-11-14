"""Tests d'intégration des points de terminaison IA (/ai/chat et /ai/vision).

But du fichier : prouver que l'API donne accès aux fonctions des modèles
comme le prévoient les spécifications (critère C9-CR2) :

- /ai/chat fait passer la question par le routage d'intention (filet de
  sécurité puis classifieur) et renvoie la réponse prévue pour l'intention ;
- /ai/vision renvoie l'aliment reconnu et son score, un 422 pour un fichier
  illisible et un 503 explicite quand le VLM est indisponible.

Ni base de données, ni ChromaDB, ni Mistral, ni Ollama ne sont nécessaires :
les intentions testées ici renvoient un texte figé, sans RAG ni LLM, et la
réponse du VLM est simulée.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.disclaimers import TEXTE_DETRESSE_URGENCE, TEXTE_OUT_OF_SCOPE
from app.core.security import create_access_token
from app.main import app
from app.repositories import aliment_repository, log_vlm_repository
from app.services import alternative_service, intent_service, vision_service
from tests.test_endpoints import _faux_aliment
from tests.test_intent_classifier import FauxModele


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def entetes(compte_valide) -> dict[str, str]:
    """En-tête d'authentification d'une utilisatrice connectée, accès IA validé."""
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


def _photo_png() -> bytes:
    """Petite image PNG valide, fabriquée en mémoire."""
    sortie = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 30, 30)).save(sortie, format="PNG")
    return sortie.getvalue()


@pytest.fixture
def vlm_simule(monkeypatch):
    """Base et journal simulés ; la réponse du VLM est fixée test par test."""
    monkeypatch.setattr(
        aliment_repository,
        "rechercher_par_nom",
        AsyncMock(return_value=[_faux_aliment()]),
    )
    monkeypatch.setattr(alternative_service, "trouver_alternatives", AsyncMock(return_value=[]))
    monkeypatch.setattr(log_vlm_repository, "enregistrer", AsyncMock())


def test_vision_reconnait_l_aliment_et_renvoie_son_score(
    client_api, entetes_auth, vlm_simule, monkeypatch
):
    monkeypatch.setattr(
        vision_service,
        "_appeler_vlm",
        AsyncMock(return_value=vision_service.ReponseVLM("aliment_unique", "tomate", 0.98)),
    )

    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("tomate.png", _photo_png(), "image/png")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "reconnu"
    assert corps["id_aliment"] == 42
    assert corps["resultat"]["aliment"]["nom"] == "Tomate, crue"
    assert corps["resultat"]["disclaimer"]
    assert corps["resultat"]["mention_projet_etudiant"]


def test_vision_photo_sans_aliment_unique_renvoie_200_et_un_message(
    client_api, entetes_auth, vlm_simule, monkeypatch
):
    """Pas d'aliment reconnu n'est pas une erreur HTTP : le message oriente l'utilisatrice."""
    monkeypatch.setattr(
        vision_service,
        "_appeler_vlm",
        AsyncMock(return_value=vision_service.ReponseVLM("plat_prepare", "", 0.98)),
    )

    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("assiette.png", _photo_png(), "image/png")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "echec"
    assert corps["contenu"] == "plat_prepare"
    assert corps["resultat"] is None
    assert "recherche par nom" in corps["message"]


def test_vision_refuse_un_fichier_illisible_en_422(client_api, entetes_auth, vlm_simule):
    """Le type annoncé est image/png, mais le contenu n'est pas une image."""
    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("faux.png", b"\x89PNG faux contenu", "image/png")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 422
    assert "pas une image lisible" in reponse.json()["detail"]


def test_vision_renvoie_503_si_le_vlm_est_indisponible(
    client_api, entetes_auth, vlm_simule, monkeypatch
):
    monkeypatch.setattr(
        vision_service,
        "_appeler_vlm",
        AsyncMock(side_effect=vision_service.VLMIndisponibleError("Ollama injoignable")),
    )

    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("tomate.png", _photo_png(), "image/png")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 503
    assert "recherche textuelle" in reponse.json()["detail"]