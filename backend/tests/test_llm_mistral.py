"""Tests du client Mistral (critère C8-CR3 : monitorage du service).

But du fichier : prouver que chaque appel à Mistral laisse une ligne de log
exploitable (statut, latence, tokens) et qu'aucun secret ne s'y retrouve.

Aucun appel réseau : httpx.MockTransport joue le rôle de l'API Mistral.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest

from app.services import llm_mistral

NOM_LOGGER = "app.services.llm_mistral"

# Réponse type de l'API Mistral (format /v1/chat/completions).
REPONSE_MISTRAL = {
    "model": "mistral-small-2603",
    "choices": [{"message": {"role": "assistant", "content": " Réponse de test. "}}],
    "usage": {"prompt_tokens": 120, "completion_tokens": 35, "total_tokens": 155},
}


def _brancher_faux_mistral(monkeypatch, statut: int, corps: dict) -> None:
    """Remplace l'API Mistral par une réponse fixe, sans réseau."""
    vrai_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda requete: httpx.Response(statut, json=corps))
    monkeypatch.setattr(
        llm_mistral.httpx,
        "AsyncClient",
        lambda **options: vrai_client(transport=transport, **options),
    )


def test_appel_reussi_journalise_statut_latence_et_tokens(monkeypatch, caplog):
    _brancher_faux_mistral(monkeypatch, 200, REPONSE_MISTRAL)

    with caplog.at_level(logging.INFO, logger=NOM_LOGGER):
        texte = asyncio.run(llm_mistral.generer_reponse("Une question ?", ["Un extrait."]))

    assert texte == "Réponse de test."
    assert "statut=200" in caplog.text
    assert "latence_ms=" in caplog.text
    assert "tokens_entree=120" in caplog.text
    assert "tokens_sortie=35" in caplog.text


def test_les_logs_ne_contiennent_ni_cle_ni_question(monkeypatch, caplog):
    _brancher_faux_mistral(monkeypatch, 200, REPONSE_MISTRAL)

    with caplog.at_level(logging.INFO, logger=NOM_LOGGER):
        asyncio.run(llm_mistral.generer_reponse("Ma question privée", ["Un extrait."]))

    # "cle-de-test" est la clé posée par conftest.py.
    assert "cle-de-test" not in caplog.text
    assert "Ma question privée" not in caplog.text


def test_erreur_mistral_journalisee_et_convertie(monkeypatch, caplog):
    _brancher_faux_mistral(monkeypatch, 401, {"message": "Unauthorized"})

    with (
        caplog.at_level(logging.INFO, logger=NOM_LOGGER),
        pytest.raises(llm_mistral.LLMIndisponibleError),
    ):
        asyncio.run(llm_mistral.generer_reponse("Une question ?", ["Un extrait."]))

    assert "statut=401" in caplog.text
    assert "latence_ms=" in caplog.text