"""Configuration du service LLM (Mistral La Plateforme).

Toutes les valeurs proviennent de variables d'environnement, chargées depuis un
fichier `.env` non versionné. Aucune clé ni valeur de réglage n'est écrite en
dur dans le code (OWASP A02 — défaillances cryptographiques / secrets exposés).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Racine du projet : app/core/config.py -> app -> backend -> racine
PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(RuntimeError):
    """Levée quand une variable d'environnement est absente ou invalide."""


@dataclass(frozen=True)
class MistralSettings:
    """Paramètres d'appel au LLM du chatbot RAG."""

    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float

    @property
    def chat_completions_url(self) -> str:
        """URL complète de l'endpoint de génération."""
        return f"{self.base_url}/chat/completions"


def _require(name: str) -> str:
    """Lit une variable d'environnement obligatoire.

    Raises:
        ConfigurationError: si la variable est absente ou vide.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Variable d'environnement manquante : {name}. "
            "Copiez `.env.example` en `.env` et renseignez-la."
        )
    return value


def _read_float(name: str, default: str) -> float:
    raw = os.getenv(name, default).strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} doit être un nombre, reçu : {raw!r}") from exc


def _read_int(name: str, default: str) -> int:
    raw = os.getenv(name, default).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} doit être un entier, reçu : {raw!r}") from exc


@lru_cache(maxsize=1)
def get_mistral_settings() -> MistralSettings:
    """Construit et met en cache la configuration Mistral.

    Le cache évite de relire l'environnement à chaque requête HTTP entrante.
    À vider avec `get_mistral_settings.cache_clear()` dans les tests.

    Raises:
        ConfigurationError: si une variable obligatoire manque ou est invalide.
    """
    return MistralSettings(
        api_key=_require("MISTRAL_API_KEY"),
        base_url=os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/"),
        model=os.getenv("MISTRAL_MODEL", "mistral-small-2603").strip(),
        temperature=_read_float("MISTRAL_TEMPERATURE", "0.15"),
        max_tokens=_read_int("MISTRAL_MAX_TOKENS", "800"),
        timeout_seconds=_read_float("MISTRAL_TIMEOUT_SECONDS", "30"),
    )