"""Client d'appel au LLM Mistral (endpoint compatible OpenAI).

Ce module ne connaît RIEN du RAG : il ne fait qu'envoyer des messages et
retourner du texte. Le retrieval, l'injection de contexte et les garde-fous
médicaux vivent dans une couche au-dessus. Cette séparation permet de tester le
LLM seul tant que l'index ChromaDB n'existe pas.

Appel exclusivement côté backend. La clé API ne traverse jamais le frontend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import MistralSettings, get_mistral_settings

logger = logging.getLogger(__name__)

Role = Literal["system", "user", "assistant"]


class MistralError(RuntimeError):
    """Erreur d'appel au service Mistral."""


class MistralAuthError(MistralError):
    """Clé API absente, invalide ou révoquée (HTTP 401 / 403)."""


class MistralRateLimitError(MistralError):
    """Quota du tier atteint (HTTP 429).

    Le tier gratuit est limité à 1 requête par seconde : sérialiser les appels
    (jeu d'évaluation compris) plutôt que de les paralléliser.
    """


@dataclass(frozen=True)
class LLMResponse:
    """Réponse du modèle, dépouillée de l'enveloppe HTTP."""

    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _build_payload(
    messages: list[dict[str, str]],
    settings: MistralSettings,
) -> dict[str, Any]:
    """Assemble le corps de la requête de génération."""
    return {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
    }


def _parse_response(payload: dict[str, Any]) -> LLMResponse:
    """Extrait le texte et la comptabilité de tokens d'une réponse Mistral.

    Raises:
        MistralError: si la structure attendue est absente.
    """
    try:
        choice = payload["choices"][0]
        usage = payload.get("usage", {})
        return LLMResponse(
            text=choice["message"]["content"],
            model=payload.get("model", "inconnu"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "inconnu"),
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise MistralError(
            f"Réponse Mistral inexploitable : structure inattendue ({exc})."
        ) from exc


def _raise_for_status(response: httpx.Response) -> None:
    """Traduit un code HTTP d'erreur en exception métier explicite."""
    if response.status_code < 400:
        return

    detail = response.text[:500]
    if response.status_code in (401, 403):
        raise MistralAuthError(
            f"Authentification refusée (HTTP {response.status_code}). "
            f"Vérifiez MISTRAL_API_KEY. Détail : {detail}"
        )
    if response.status_code == 429:
        raise MistralRateLimitError(
            "Limite de débit atteinte (HTTP 429). Le tier gratuit autorise "
            f"1 requête/seconde. Détail : {detail}"
        )
    raise MistralError(f"Erreur Mistral HTTP {response.status_code} : {detail}")


async def chat_completion(
    messages: list[dict[str, str]],
    settings: MistralSettings | None = None,
) -> LLMResponse:
    """Envoie une liste de messages au modèle et retourne sa réponse.

    Args:
        messages: messages au format `{"role": ..., "content": ...}`.
        settings: configuration à utiliser. Par défaut, celle de l'environnement.

    Raises:
        MistralAuthError: clé invalide.
        MistralRateLimitError: quota atteint.
        MistralError: toute autre erreur d'appel ou réponse illisible.
    """
    settings = settings or get_mistral_settings()
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.post(
                settings.chat_completions_url,
                headers=headers,
                json=_build_payload(messages, settings),
            )
    except httpx.TimeoutException as exc:
        raise MistralError(
            f"Délai dépassé après {settings.timeout_seconds} s."
        ) from exc
    except httpx.HTTPError as exc:
        raise MistralError(f"Échec réseau vers Mistral : {exc}") from exc

    _raise_for_status(response)
    parsed = _parse_response(response.json())

    # Log structuré : ne journalise jamais la clé, ni le contenu des questions
    # (elles peuvent contenir des données personnelles de santé).
    logger.info(
        "mistral_call",
        extra={
            "model": parsed.model,
            "prompt_tokens": parsed.prompt_tokens,
            "completion_tokens": parsed.completion_tokens,
            "finish_reason": parsed.finish_reason,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000),
        },
    )
    return parsed
