"""Accès aux données `log_vlm` : journalisation des inférences VLM.

Cette table alimente le monitoring modèle. Si la journalisation tombe, l'analyse
photo doit quand même répondre.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import STATUTS_VALIDES, LogVlm


async def enregistrer(
    session: AsyncSession,
    *,
    statut: str,
    label_identifie: str | None = None,
    score_confiance: float | None = None,
    id_aliment: int | None = None,
) -> LogVlm:
    """Enregistre une inférence VLM.

    Args:
        session: session SQLAlchemy.
        statut: l'un de `STATUTS_VALIDES`.
        label_identifie: libellé renvoyé par le VLM, si reconnaissance.
        score_confiance: confiance entre 0 et 1.
        id_aliment: aliment rapproché en base, si le rapprochement a abouti.

    Returns:
        La ligne de journal créée.

    Raises:
        ValueError: si le statut n'est pas reconnu.
    """
    if statut not in STATUTS_VALIDES:
        raise ValueError(
            f"Statut {statut!r} invalide. Attendu : {', '.join(STATUTS_VALIDES)}."
        )

    log = LogVlm(
        statut=statut,
        label_identifie=label_identifie,
        score_confiance=Decimal(str(score_confiance)) if score_confiance is not None else None,
        id_aliment=id_aliment,
    )
    session.add(log)
    await session.flush()
    return log


async def lister_recents(session: AsyncSession, *, limite: int = 100) -> list[LogVlm]:
    """Liste les inférences les plus récentes : réservé à l'espace admin."""
    requete = select(LogVlm).order_by(LogVlm.timestamp.desc()).limit(limite)
    resultat = await session.execute(requete)
    return list(resultat.scalars().all())
