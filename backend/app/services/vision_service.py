"""Reconnaissance d'aliment par photo via le VLM.

Chaîne cible :

1. l'image est envoyée à Qwen3-VL via Ollama ;
2. le modèle renvoie un JSON `{label, confidence}` ;
3. le label est rapproché d'un aliment de la base par recherche floue ;
4. l'inférence est journalisée dans `log_vlm` quelle qu'en soit l'issue.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import STATUT_ECHEC, STATUT_NON_RAPPROCHE, STATUT_RECONNU
from app.repositories import aliment_repository, log_vlm_repository
from app.schemas.chat import VisionResponse

logger = logging.getLogger(__name__)


class VLMIndisponibleError(RuntimeError):
    """Levée quand le service Ollama est injoignable."""


async def _appeler_vlm(image: bytes) -> tuple[str | None, float | None]:
    """Envoie l'image au VLM et renvoie (label, confiance).

    NON IMPLÉMENTÉ : à écrire quand Ollama sera en place.

    Raises:
        NotImplementedError: systématiquement, pour l'instant.
    """
    raise NotImplementedError(
        "Le service VLM n'est pas encore branché. À implémenter : appel HTTP "
        "à Ollama (get_ollama_settings().base_url), envoi de l'image en base64, "
        "parsing du JSON {label, confidence}."
    )


async def analyser_image(session: AsyncSession, image: bytes) -> VisionResponse:
    """Identifie un aliment sur une photo et le rapproche de la base.

    Args:
        session: session SQLAlchemy.
        image: contenu binaire de l'image envoyée.

    Returns:
        Le résultat de l'analyse, toujours journalisé dans `log_vlm`.
    """
    label: str | None = None
    confiance: float | None = None
    id_aliment: int | None = None
    statut = STATUT_ECHEC

    try:
        label, confiance = await _appeler_vlm(image)
    except NotImplementedError:
        raise
    except Exception:
        logger.exception("échec de l'inférence VLM")
        label, confiance = None, None

    if label:
        candidats = await aliment_repository.rechercher_par_nom(session, label, limite=1)
        if candidats:
            id_aliment = candidats[0].id_aliment
            statut = STATUT_RECONNU
        else:
            statut = STATUT_NON_RAPPROCHE

    # La journalisation ne doit jamais casser la réponse utilisateur.
    try:
        await log_vlm_repository.enregistrer(
            session,
            statut=statut,
            label_identifie=label,
            score_confiance=confiance,
            id_aliment=id_aliment,
        )
        await session.commit()
    except Exception:
        logger.exception("échec de la journalisation VLM : la réponse est renvoyée quand même")
        await session.rollback()

    return VisionResponse(
        label_identifie=label,
        score_confiance=confiance,
        statut=statut,
        id_aliment=id_aliment,
        message=None if statut == STATUT_RECONNU else (
            "Aliment non reconnu. Essayez la recherche par nom."
        ),
    )
