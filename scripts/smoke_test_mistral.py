"""Test de connectivité brut vers Mistral La Plateforme.

Ce script ne teste PAS le chatbot : ni garde-fous, ni corpus, ni disclaimers.
Il répond à une seule question — « la clé, le modèle et l'endpoint
répondent-ils ? » — et sert de preuve d'installation reproductible pour C8.

Usage :
    uv run python scripts/smoke_test_mistral.py
    uv run python scripts/smoke_test_mistral.py --prompt "Bonjour, réponds en français."
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from app.core.config import ConfigurationError, get_mistral_settings
from app.services.llm_mistral import MistralError, chat_completion

DEFAULT_PROMPT = "Réponds en une phrase, en français : quelle est la capitale de la France ?"


def _mask(secret: str) -> str:
    """Masque une clé pour un affichage sans fuite."""
    return f"{secret[:4]}…{secret[-4:]}" if len(secret) > 8 else "…"


async def run(prompt: str) -> int:
    """Exécute un appel unique et affiche le résultat. Retourne un code de sortie."""
    try:
        settings = get_mistral_settings()
    except ConfigurationError as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        return 2

    print("--- Configuration active ---")
    print(f"Endpoint          : {settings.chat_completions_url}")
    print(f"Modèle            : {settings.model}")
    print(f"Température       : {settings.temperature}")
    print(f"Clé API           : {_mask(settings.api_key)}")
    print()

    started = time.perf_counter()
    time.sleep(1)
    try:
        result = await chat_completion([{"role": "user", "content": prompt}])
    except MistralError as exc:
        print(f"[ÉCHEC] {exc}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - started

    print("--- Réponse ---")
    print(result.text.strip())
    print()
    print("--- Métriques ---")
    print(f"Modèle renvoyé    : {result.model}")
    print(f"Tokens entrée     : {result.prompt_tokens}")
    print(f"Tokens sortie     : {result.completion_tokens}")
    print(f"Motif d'arrêt     : {result.finish_reason}")
    print(f"Latence           : {elapsed:.2f} s")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Message à envoyer.")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.prompt)))


if __name__ == "__main__":
    main()

