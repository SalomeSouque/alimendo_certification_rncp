"""Tests de la configuration Ollama (critère C8-CR2 : paramétrage du VLM).

But du fichier : prouver que le paramétrage du VLM vient bien du `.env`
(aucune valeur en dur dans le code), que les valeurs par défaut désignent le
bon modèle, et qu'une valeur absurde est refusée au démarrage plutôt que de
provoquer une erreur obscure au premier appel.

Aucun appel réseau : on ne teste que la lecture de la configuration.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import ConfigurationError, get_ollama_settings

VARIABLES_OLLAMA = (
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "VLM_CONFIDENCE_THRESHOLD",
)


@pytest.fixture(autouse=True)
def config_vierge(monkeypatch) -> Iterator[None]:
    """Part d'un environnement sans variable Ollama et d'un cache vide.

    `get_ollama_settings` est mis en cache (lru_cache) : sans `cache_clear`,
    un test lirait la configuration construite par le test précédent.
    """
    for nom in VARIABLES_OLLAMA:
        monkeypatch.delenv(nom, raising=False)
    get_ollama_settings.cache_clear()
    yield
    get_ollama_settings.cache_clear()


def test_valeurs_par_defaut():
    settings = get_ollama_settings()

    assert settings.base_url == "http://ollama:11434"
    assert settings.timeout_seconds == 120.0
    assert settings.confidence_threshold == 0.5


def test_modele_par_defaut_est_la_variante_instruct():
    """`qwen3-vl:4b` est la variante thinking : le défaut doit l'éviter."""
    modele = get_ollama_settings().model

    assert modele == "qwen3-vl:4b-instruct-q4_K_M"
    assert "thinking" not in modele


def test_valeurs_lues_depuis_l_environnement(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "  qwen3-vl:2b-instruct  ")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("VLM_CONFIDENCE_THRESHOLD", "0.7")

    settings = get_ollama_settings()

    # La barre finale est retirée : on construit ensuite base_url + "/api/chat".
    assert settings.base_url == "http://localhost:11434"
    assert settings.model == "qwen3-vl:2b-instruct"
    assert settings.timeout_seconds == 45.0
    assert settings.confidence_threshold == 0.7


@pytest.mark.parametrize(
    ("variable", "valeur"),
    [
        ("OLLAMA_MODEL", "   "),
        ("OLLAMA_TIMEOUT_SECONDS", "0"),
        ("OLLAMA_TIMEOUT_SECONDS", "-5"),
        ("OLLAMA_TIMEOUT_SECONDS", "deux minutes"),
        ("VLM_CONFIDENCE_THRESHOLD", "1.5"),
        ("VLM_CONFIDENCE_THRESHOLD", "-0.1"),
    ],
)
def test_valeur_invalide_refusee(monkeypatch, variable, valeur):
    monkeypatch.setenv(variable, valeur)

    with pytest.raises(ConfigurationError, match=variable):
        get_ollama_settings()
