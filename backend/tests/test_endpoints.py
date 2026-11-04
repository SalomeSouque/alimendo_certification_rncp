"""Tests d'intégration de tous les points de terminaison de l'API.

But du fichier (critères C9-CR5, C9-CR6, C17-CR9) : chaque route est appelée
par HTTP, comme le ferait le frontend, et on vérifie le code de réponse et
le contrat de la réponse pour :

- 200 / 201 : le cas nominal ;
- 401 : jeton absent, invalide, ou clé d'API manquante ;
- 404 / 409 / 413 / 415 / 503 : les erreurs métier prévues par les specs ;
- 422 : une entrée refusée par la validation Pydantic.

403 n'est pas testé ici : aucune route n'est réservée à un rôle (seules les
features IA demandent un compte, quel que soit le rôle). Voir docs/tests_api.md.

Ni base, ni ChromaDB, ni Mistral : la session est une doublure (conftest.py)
et les repositories et services externes sont simulés avec monkeypatch.
Les routes de /ai/chat déjà testées (out_of_scope, détresse, question trop
courte) sont dans test_ai_endpoints.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest

from app.core.config import get_security_settings
from app.core.disclaimers import DISCLAIMER_CHATBOT_COURT, DISCLAIMER_SCORE
from app.core.security import hash_password
from app.repositories import aliment_repository, user_repository
from app.services import (
    alternative_service,
    chroma_service,
    embedding_service,
    intent_service,
    llm_mistral,
)
from tests.test_intent_classifier import FauxModele


def _faux_utilisateur(mot_de_passe: str = "motdepasse-correct") -> SimpleNamespace:
    """Utilisateur minimal : ce que le service lit pour émettre le jeton."""
    return SimpleNamespace(
        id_utilisateur=7,
        email="lea@example.com",
        password=hash_password(mot_de_passe),
        role=SimpleNamespace(libelle="user"),
        last_login=None,
    )


def _faux_aliment() -> SimpleNamespace:
    """Aliment minimal sans aucune valeur nutritionnelle.

    Profil vide : le score est « indisponible » (complétude insuffisante),
    ce qui évite de dépendre des repères de normalisation dans ce test d'API.
    """
    return SimpleNamespace(
        id_aliment=42,
        nom="Tomate, crue",
        source="CIQUAL",
        url_image=None,
        id_categorie=3,
        profil_nutritionnel=dict,
    )


# Santé


def test_health_detail_repond_200_meme_si_une_dependance_manque(client_api, monkeypatch):
    """/health/detail ne renvoie jamais d'erreur HTTP : il décrit l'état de chaque brique."""
    monkeypatch.setattr(chroma_service, "est_disponible", lambda: False)

    reponse = client_api.get("/health/detail")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["base_de_donnees"] == "ok"
    assert corps["index_vectoriel"] == "indisponible"


# Authentification


def test_register_cree_le_compte_et_renvoie_un_jeton(client_api, monkeypatch):
    monkeypatch.setattr(user_repository, "get_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(user_repository, "creer", AsyncMock(return_value=_faux_utilisateur()))

    reponse = client_api.post(
        "/auth/register", json={"email": "lea@example.com", "password": "motdepasse-correct", "consentement": True}
    )

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["access_token"]
    assert corps["user"] == {"id": 7, "email": "lea@example.com", "role": "user"}


def test_register_refuse_un_email_deja_utilise(client_api, monkeypatch):
    monkeypatch.setattr(
        user_repository, "get_by_email", AsyncMock(return_value=_faux_utilisateur())
    )

    reponse = client_api.post(
        "/auth/register", json={"email": "lea@example.com", "password": "motdepasse-correct", "consentement": True}
    )

    assert reponse.status_code == 409


def test_register_refuse_un_mot_de_passe_trop_court(client_api):
    """Moins de 8 caractères : refusé par Pydantic avant tout appel à la base."""
    reponse = client_api.post(
        "/auth/register", json={"email": "lea@example.com", "password": "court", "consentement": True}
    )

    assert reponse.status_code == 422


@pytest.mark.parametrize("corps_consentement", [{}, {"consentement": False}])
def test_register_refuse_sans_consentement_explicite(client_api, corps_consentement):
    """Sans `consentement: true`, refus 422 avant tout appel à la base (RGPD art. 9.2.a)."""
    reponse = client_api.post(
        "/auth/register",
        json={"email": "lea@example.com", "password": "motdepasse-correct", **corps_consentement},
    )

    assert reponse.status_code == 422


def test_login_renvoie_un_jeton(client_api, monkeypatch):
    monkeypatch.setattr(
        user_repository, "get_by_email", AsyncMock(return_value=_faux_utilisateur())
    )
    monkeypatch.setattr(user_repository, "enregistrer_connexion", AsyncMock())

    reponse = client_api.post(
        "/auth/login", json={"email": "lea@example.com", "password": "motdepasse-correct", "consentement": True}
    )

    assert reponse.status_code == 200
    assert reponse.json()["token_type"] == "bearer"


def test_login_refuse_un_mauvais_mot_de_passe(client_api, monkeypatch):
    monkeypatch.setattr(
        user_repository, "get_by_email", AsyncMock(return_value=_faux_utilisateur())
    )

    reponse = client_api.post(
        "/auth/login", json={"email": "lea@example.com", "password": "motdepasse-faux"}
    )

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Email ou mot de passe incorrect."


def test_login_refuse_un_email_mal_forme(client_api):
    reponse = client_api.post("/auth/login", json={"email": "pas-un-email", "password": "x"})

    assert reponse.status_code == 422


def test_me_renvoie_l_utilisatrice_du_jeton(client_api, entetes_auth):
    reponse = client_api.get("/auth/me", headers=entetes_auth)

    assert reponse.status_code == 200
    assert reponse.json() == {"id": 1, "email": "test@example.com", "role": "user"}


def test_me_sans_jeton_renvoie_401(client_api):
    reponse = client_api.get("/auth/me")

    assert reponse.status_code == 401


def test_me_avec_un_jeton_expire_renvoie_401(client_api):
    """Cas utilisé par le frontend pour déconnecter : le jeton a expiré."""
    reglages = get_security_settings()
    passe = datetime.now(UTC) - timedelta(hours=2)
    jeton_expire = jwt.encode(
        {"sub": "1", "email": "test@example.com", "role": "user", "iat": passe,
         "exp": passe + timedelta(minutes=1)},
        reglages.jwt_secret_key,
        algorithm=reglages.jwt_algorithm,
    )

    reponse = client_api.get("/auth/me", headers={"Authorization": f"Bearer {jeton_expire}"})

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Session expirée, reconnectez-vous."


# Recherche (publique)


def test_recherche_refuse_un_terme_trop_court(client_api):
    reponse = client_api.get("/search/aliments", params={"q": "a"})

    assert reponse.status_code == 422


def test_categories_sont_publiques(client_api, monkeypatch):
    categories = [SimpleNamespace(id_categorie=3, nom="fruits", image=None)]
    monkeypatch.setattr(
        aliment_repository, "lister_categories", AsyncMock(return_value=categories)
    )

    reponse = client_api.get("/search/categories")

    assert reponse.status_code == 200
    assert reponse.json() == [{"id_categorie": 3, "nom": "fruits", "image": None}]


# Score (public)


def test_score_aliment_renvoie_le_detail_avec_le_disclaimer(client_api, monkeypatch):
    monkeypatch.setattr(aliment_repository, "get_by_id", AsyncMock(return_value=_faux_aliment()))
    monkeypatch.setattr(alternative_service, "trouver_alternatives", AsyncMock(return_value=[]))

    reponse = client_api.get("/score/aliment/42")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["aliment"]["nom"] == "Tomate, crue"
    assert corps["score"]["disponible"] is False
    assert corps["disclaimer"] == DISCLAIMER_SCORE


def test_score_aliment_inconnu_renvoie_404(client_api, monkeypatch):
    monkeypatch.setattr(aliment_repository, "get_by_id", AsyncMock(return_value=None))

    reponse = client_api.get("/score/aliment/9999")

    assert reponse.status_code == 404


def test_score_aliment_refuse_un_identifiant_negatif(client_api):
    reponse = client_api.get("/score/aliment/0")

    assert reponse.status_code == 422


# Chatbot (JWT)


def _brancher_un_faux_rag(monkeypatch) -> AsyncMock:
    """Simule toute la chaîne RAG : classifieur, embeddings, ChromaDB et Mistral.

    Returns:
        Le faux Mistral, pour vérifier ce qu'il a reçu.
    """
    monkeypatch.setattr(intent_service, "charger_modele", lambda: FauxModele("in_scope"))
    monkeypatch.setattr(embedding_service, "encoder_question", lambda question: [0.1, 0.2])
    monkeypatch.setattr(
        chroma_service,
        "rechercher",
        lambda vecteur: {
            "documents": [["L'endométriose touche environ une femme sur dix."]],
            "metadatas": [[{"id_source": "S1", "titre": "Fiche Inserm endométriose"}]],
            "distances": [[0.2]],
        },
    )
    faux_mistral = AsyncMock(return_value="Réponse générée à partir des extraits.")
    monkeypatch.setattr(llm_mistral, "generer_reponse", faux_mistral)
    return faux_mistral


def test_chat_in_scope_renvoie_une_reponse_sourcee(client_api, entetes_auth, monkeypatch):
    """Parcours RAG complet, avec un faux Mistral : 200, sources et disclaimer."""
    faux_mistral = _brancher_un_faux_rag(monkeypatch)

    reponse = client_api.post(
        "/ai/chat", json={"question": "Qu'est-ce que l'endométriose ?"}, headers=entetes_auth
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["intention"] == "in_scope"
    assert corps["sources"][0]["titre"] == "Fiche Inserm endométriose"
    assert corps["sources"][0]["score_similarite"] == 0.8
    assert corps["disclaimer"] == DISCLAIMER_CHATBOT_COURT

    # Mistral reçoit le titre de la source avec l'extrait, pour pouvoir le citer.
    extraits_envoyes = faux_mistral.await_args.args[1]
    assert extraits_envoyes[0].startswith("Source : Fiche Inserm endométriose")


def test_chat_renvoie_503_si_mistral_est_indisponible(client_api, entetes_auth, monkeypatch):
    faux_mistral = _brancher_un_faux_rag(monkeypatch)
    faux_mistral.side_effect = llm_mistral.LLMIndisponibleError("timeout")

    reponse = client_api.post(
        "/ai/chat", json={"question": "Qu'est-ce que l'endométriose ?"}, headers=entetes_auth
    )

    assert reponse.status_code == 503


@pytest.fixture
def cle_api_active(monkeypatch):
    """Active le garde-fou X-API-Key le temps d'un test.

    La configuration est mise en cache : on vide le cache avant et après pour
    que les autres tests retrouvent la configuration sans clé.
    """
    monkeypatch.setenv("ALIMENDO_API_KEY", "cle-de-test")
    get_security_settings.cache_clear()
    yield "cle-de-test"
    monkeypatch.delenv("ALIMENDO_API_KEY")
    get_security_settings.cache_clear()


def test_chat_refuse_un_appel_sans_cle_api_quand_elle_est_configuree(
    client_api, entetes_auth, cle_api_active
):
    reponse = client_api.post(
        "/ai/chat", json={"question": "Qu'est-ce que l'endométriose ?"}, headers=entetes_auth
    )

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Clé d'API manquante ou invalide."


def test_chat_accepte_un_appel_avec_la_bonne_cle_api(
    client_api, entetes_auth, cle_api_active, monkeypatch
):
    _brancher_un_faux_rag(monkeypatch)

    reponse = client_api.post(
        "/ai/chat",
        json={"question": "Qu'est-ce que l'endométriose ?"},
        headers={**entetes_auth, "X-API-Key": cle_api_active},
    )

    assert reponse.status_code == 200


# Vision (JWT)


def test_vision_refuse_un_fichier_qui_n_est_pas_une_image(client_api, entetes_auth):
    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("notes.txt", b"du texte", "text/plain")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 415


def test_vision_refuse_une_image_trop_lourde(client_api, entetes_auth):
    six_mo = b"0" * (6 * 1024 * 1024)

    reponse = client_api.post(
        "/ai/vision",
        files={"image": ("grosse.png", six_mo, "image/png")},
        headers=entetes_auth,
    )

    assert reponse.status_code == 413