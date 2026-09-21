"""Classe de base déclarative SQLAlchemy.

"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles Alimendo."""
