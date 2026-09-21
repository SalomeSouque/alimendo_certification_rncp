"""Modèle ORM `log_vlm`, trace de chaque appel au VLM de reconnaissance photo.

Permet de mesurer a posteriori le taux de reconnaissance et la dérive du VLM. 
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Issue du VLM pour une image donnée.
STATUT_RECONNU = "reconnu"          # label identifié & rapproché d'un aliment
STATUT_NON_RAPPROCHE = "non_rapproche"  # label identifié mais absent de la base
STATUT_ECHEC = "echec"              # le VLM n'a rien identifié
STATUTS_VALIDES: tuple[str, ...] = (STATUT_RECONNU, STATUT_NON_RAPPROCHE, STATUT_ECHEC)


class LogVlm(Base):
    """Trace d'une inférence VLM."""

    __tablename__ = "log_vlm"

    id_log: Mapped[int] = mapped_column(primary_key=True)
    id_aliment: Mapped[int | None] = mapped_column(
        ForeignKey("aliment.id_aliment", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    label_identifie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score_confiance: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"LogVlm(id={self.id_log}, label={self.label_identifie!r}, statut={self.statut!r})"
