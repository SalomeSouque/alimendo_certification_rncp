"""Modèles ORM `categorie` et `aliment`, transcrits du MPD Merise.

23 colonnes nutritionnelles qui alimentent le score.
Toutes les colonnes nutritionnelles sont nullables (!= 0 dans CIQUAL).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Colonnes nutritionnelles 
PARAMETRES_NUTRITIONNELS: tuple[str, ...] = (
    "glucides",
    "proteines",
    "lipides",
    "graisses_saturees",
    "cholesterol",
    "fer",
    "vitamine_b12",
    "fibres",
    "omega3",
    "omega6",
    "vitamine_a",
    "beta_carotene",
    "vitamine_c",
    "vitamine_d",
    "vitamine_e",
    "vitamine_b6",
    "folates",
    "thiamine",
    "riboflavine",
    "niacine",
    "magnesium",
    "selenium",
    "zinc",
)


class Categorie(Base):
    """Catégorie alimentaire - sert de périmètre à la logique d'alternatives."""

    __tablename__ = "categorie"

    id_categorie: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)

    aliments: Mapped[list[Aliment]] = relationship(back_populates="categorie")

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"Categorie(id={self.id_categorie}, nom={self.nom!r})"


class Aliment(Base):
    """Aliment brut (CIQUAL) ou produit transformé (Open Food Facts).

    `source` distingue l'origine de la donnée : "CIQUAL" pour les aliments
    seedés en base, "OFF" pour les produits récupérés via l'API. Le score est
    recalculé à la volée dans les deux cas - il n'est jamais stocké ici.
    """

    __tablename__ = "aliment"

    id_aliment: Mapped[int] = mapped_column(primary_key=True)
    id_categorie: Mapped[int | None] = mapped_column(
        ForeignKey("categorie.id_categorie", ondelete="SET NULL"), nullable=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    url_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Identifiant CIQUAL (alim_code) : rend l'import relançable sans doublon (migration 0002)
    code_ciqual: Mapped[int | None] = mapped_column(Integer, nullable=True)

    energie: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Paramètres pro-inflammatoires
    glucides: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    proteines: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    lipides: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    graisses_saturees: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    cholesterol: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    fer: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_b12: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Paramètres anti-inflammatoires
    fibres: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    omega3: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    omega6: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_a: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    beta_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_c: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_e: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    vitamine_b6: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    folates: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    thiamine: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    riboflavine: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    niacine: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    magnesium: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    selenium: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    zinc: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    categorie: Mapped[Categorie | None] = relationship(back_populates="aliments")

    __table_args__ = (
        # Recherche textuelle tolérante 
        Index("ix_aliment_id_categorie", "id_categorie"),
        UniqueConstraint("code_ciqual", name="uq_aliment_code_ciqual"),
    )

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"Aliment(id={self.id_aliment}, nom={self.nom!r}, source={self.source!r})"

    def profil_nutritionnel(self) -> dict[str, float | None]:
        """Extrait les 23 paramètres du score sous forme de floats.

        Returns:
            Un dictionnaire {nom_du_paramètre: valeur ou None}.
        """
        profil: dict[str, float | None] = {}
        for nom in PARAMETRES_NUTRITIONNELS:
            valeur = getattr(self, nom)
            profil[nom] = float(valeur) if valeur is not None else None
        return profil
