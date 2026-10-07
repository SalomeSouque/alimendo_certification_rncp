"""Précision des nutriments et identifiant CIQUAL, préparation de l'import.

Deux besoins mesurés au nettoyage CIQUAL (scripts/README.md, § 4.5) :
  - NUMERIC(8,3) déborde (bêta-carotène des algues séchées : 393 000 µg) et
    l'arrondi à 3 décimales fait changer 2 aliments de niveau de score
    -> les 23 colonnes nutritionnelles passent en NUMERIC(10,4) ;
  - l'import doit pouvoir être relancé sans créer de doublon
    -> colonne `code_ciqual` (alim_code de la source) avec contrainte UNIQUE.
     Elle reste NULL pour les autres sources. PostgreSQL accepte plusieurs NULL
     sous une contrainte UNIQUE.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Les 23 paramètres du score, dans l'ordre du modèle ORM
COLONNES_NUTRITIONNELLES: tuple[str, ...] = (
    "glucides", "proteines", "lipides", "graisses_saturees", "cholesterol", "fer", "vitamine_b12",
    "fibres", "omega3", "omega6", "vitamine_a", "beta_carotene", "vitamine_c", "vitamine_d",
    "vitamine_e", "vitamine_b6", "folates", "thiamine", "riboflavine", "niacine",
    "magnesium", "selenium", "zinc",
)


def upgrade() -> None:
    # Élargir une colonne NUMERIC ne perd aucune donnée
    for nom in COLONNES_NUTRITIONNELLES:
        op.alter_column("aliment", nom, type_=sa.Numeric(10, 4), existing_type=sa.Numeric(8, 3),
                        existing_nullable=True)
    op.add_column("aliment", sa.Column("code_ciqual", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_aliment_code_ciqual", "aliment", ["code_ciqual"])


def downgrade() -> None:
    # Attention : revenir à NUMERIC(8,3) échoue si la base contient des valeurs
    # >= 100 000 (bêta-carotène CIQUAL). Vider la table aliment avant un downgrade.
    op.drop_constraint("uq_aliment_code_ciqual", "aliment", type_="unique")
    op.drop_column("aliment", "code_ciqual")
    for nom in COLONNES_NUTRITIONNELLES:
        op.alter_column("aliment", nom, type_=sa.Numeric(8, 3), existing_type=sa.Numeric(10, 4),
                        existing_nullable=True)
