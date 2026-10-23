"""Tests du client Mistral (critères C8-CR2 et C8-CR3).

But du fichier : prouver que chaque appel à Mistral laisse une ligne de log
exploitable (statut, latence, tokens), qu'aucun secret ne s'y retrouve, et
que le paramétrage prévu (reasoning_effort) part bien dans la requête.

Aucun appel réseau : httpx.MockTransport joue le rôle de l'API Mistral.
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest

from app.core.config import ConfigurationError, get_mistral_settings
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


def test_reasoning_effort_envoye_a_mistral(monkeypatch):
    # On fixe la valeur, puis on vide le cache pour que la config soit relue.
    monkeypatch.setenv("MISTRAL_REASONING_EFFORT", "none")
    get_mistral_settings.cache_clear()
    requetes: list[httpx.Request] = []

    def faux_mistral(requete: httpx.Request) -> httpx.Response:
        requetes.append(requete)
        return httpx.Response(200, json=REPONSE_MISTRAL)

    vrai_client = httpx.AsyncClient
    transport = httpx.MockTransport(faux_mistral)
    monkeypatch.setattr(
        llm_mistral.httpx,
        "AsyncClient",
        lambda **options: vrai_client(transport=transport, **options),
    )

    asyncio.run(llm_mistral.generer_reponse("Une question ?", ["Un extrait."]))
    get_mistral_settings.cache_clear()

    assert json.loads(requetes[0].content)["reasoning_effort"] == "none"


def test_reasoning_effort_inconnu_refuse(monkeypatch):
    monkeypatch.setenv("MISTRAL_REASONING_EFFORT", "moyen")
    get_mistral_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError):
            get_mistral_settings()
    finally:
        # Les tests suivants doivent relire une configuration valide.
        get_mistral_settings.cache_clear()