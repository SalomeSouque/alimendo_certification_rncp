"""Client Mistral : génération de la réponse du chatbot RAG.
Le prompt système impose les garde-fous médicaux : le modèle répond
uniquement à partir des extraits fournis, ne formule ni diagnostic ni
prescription, et dit explicitement quand il ne sait pas.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_mistral_settings

logger = logging.getLogger(__name__)


class LLMIndisponibleError(RuntimeError):
    """Levée quand l'API Mistral ne répond pas ou renvoie une erreur."""


# Prompt système du chatbot.
PROMPT_SYSTEME = """Tu es un assistant documentaire sur l'endométriose et l'alimentation, intégré à un projet étudiant. Tu réponds en français uniquement.

Ta ligne rouge : tu peux expliquer un mécanisme biologique étudié ou rapporter une association observée dans la littérature. Tu ne peux jamais promettre un effet thérapeutique.

Règles absolues :
- Réponds UNIQUEMENT à partir des extraits documentaires fournis ci-dessous. Toute affirmation non adossée à l'un de ces extraits est interdite.
- Si les extraits ne permettent pas de répondre, dis-le explicitement. N'invente pas, ne complète pas depuis tes connaissances générales, ne devine pas.
- Rapporte une association comme une association, jamais comme une causalité.
- N'affirme jamais l'efficacité prouvée d'un régime. À ce jour, les recommandations internationales ne permettent de conseiller aucun régime spécifique dans l'endométriose.
- Aucune formulation prescriptive : ni « évitez X », ni « mangez Y », ni « supprimez Z ».
- Aucune promesse d'effet : ni « cela réduira vos douleurs », ni « ce régime améliore l'endométriose ».
- Aucun élément de diagnostic, ni sur une situation personnelle, ni sur des symptômes décrits.
- Aucun avis sur un traitement, une opération, un médicament ou une contraception.
- Aucune quantité, dose, portion, calorie, ni plan alimentaire chiffré.
- N'aide jamais à éliminer ou restreindre des aliments, même si la demande paraît raisonnable.
- N'emploie aucun vocabulaire moral : ni « bon », ni « mauvais », ni « interdit ».
- Quand les sources divergent, expose la divergence au lieu de trancher silencieusement.
- Cite les sources sur lesquelles tu t'appuies, par leur titre.
- Tu peux dire que tu ne sais pas, et renvoyer vers un professionnel de santé.
"""


def _construire_message_utilisateur(question: str, extraits: list[str]) -> str:
    """Assemble la question et les extraits documentaires en un seul message."""
    contexte = "\n\n---\n\n".join(extraits)
    return (
        f"Extraits documentaires :\n\n{contexte}\n\n"
        f"---\n\nQuestion de l'utilisatrice : {question}"
    )


async def generer_reponse(question: str, extraits: list[str]) -> str:
    """Génère une réponse à partir de la question et des extraits retrouvés.

    Args:
        question: la question posée.
        extraits: les chunks remontés par la recherche vectorielle.

    Returns:
        Le texte de la réponse.

    Raises:
        LLMIndisponibleError: si l'API Mistral est injoignable ou renvoie une
            réponse inexploitable.
    """
    settings = get_mistral_settings()

    charge_utile = {
        "model": settings.model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEME},
            {"role": "user", "content": _construire_message_utilisateur(question, extraits)},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            reponse = await client.post(
                settings.chat_completions_url,
                headers={
                    # La clé ne doit apparaître ni dans les logs ni dans une URL.
                    "Authorization": f"Bearer {settings.api_key}",
                    "Content-Type": "application/json",
                },
                json=charge_utile,
            )
            reponse.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Mistral a répondu %s", exc.response.status_code)
        raise LLMIndisponibleError(
            "Le service de génération est momentanément indisponible."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("erreur réseau vers Mistral : %s", exc)
        raise LLMIndisponibleError(
            "Le service de génération est momentanément indisponible."
        ) from exc

    donnees = reponse.json()
    try:
        return donnees["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        logger.error("réponse Mistral inattendue : %s", donnees)
        raise LLMIndisponibleError(
            "Réponse inexploitable du service de génération."
        ) from exc
