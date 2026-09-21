"""Schéma initial : categorie, aliment, role, utilisateur, log_vlm.

Transcription directe des MPD Merise.
Première migration pose aussi l'extension `pg_trgm`, l'index trigramme de recherche et les rôles par défaut,
qu'Alembic ne peut pas deviner depuis les modèles.

Revision ID: 0001
Revises:
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _colonne_nutritionnelle(nom: str) -> sa.Column:
    """Colonne NUMERIC(8,3) nullable / NULL = « non mesuré », jamais zéro."""
    return sa.Column(nom, sa.Numeric(8, 3), nullable=True)


def upgrade() -> None:
    # Extension pour recherche tolérante aux fautes, pg_trgm fournit l'opérateur de similarité trigramme 
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # categorie
    op.create_table(
        "categorie",
        sa.Column("id_categorie", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("image", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id_categorie"),
        sa.UniqueConstraint("nom", name="uq_categorie_nom"),
    )

    # aliment
    op.create_table(
        "aliment",
        sa.Column("id_aliment", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_categorie", sa.Integer(), nullable=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("url_image", sa.Text(), nullable=True),
        sa.Column("energie", sa.Numeric(8, 2), nullable=True),
        _colonne_nutritionnelle("glucides"),
        _colonne_nutritionnelle("proteines"),
        _colonne_nutritionnelle("lipides"),
        _colonne_nutritionnelle("graisses_saturees"),
        _colonne_nutritionnelle("cholesterol"),
        _colonne_nutritionnelle("fer"),
        _colonne_nutritionnelle("vitamine_b12"),
        _colonne_nutritionnelle("fibres"),
        _colonne_nutritionnelle("omega3"),
        _colonne_nutritionnelle("omega6"),
        _colonne_nutritionnelle("vitamine_a"),
        _colonne_nutritionnelle("beta_carotene"),
        _colonne_nutritionnelle("vitamine_c"),
        _colonne_nutritionnelle("vitamine_d"),
        _colonne_nutritionnelle("vitamine_e"),
        _colonne_nutritionnelle("vitamine_b6"),
        _colonne_nutritionnelle("folates"),
        _colonne_nutritionnelle("thiamine"),
        _colonne_nutritionnelle("riboflavine"),
        _colonne_nutritionnelle("niacine"),
        _colonne_nutritionnelle("magnesium"),
        _colonne_nutritionnelle("selenium"),
        _colonne_nutritionnelle("zinc"),
        sa.PrimaryKeyConstraint("id_aliment"),
        sa.ForeignKeyConstraint(
            ["id_categorie"],
            ["categorie.id_categorie"],
            name="fk_aliment_id_categorie_categorie",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_aliment_id_categorie", "aliment", ["id_categorie"])
    # Index trigramme = accélère recherche tolérante aux fautes de frappe
    op.execute(
        "CREATE INDEX ix_aliment_nom_trgm ON aliment USING gin (nom gin_trgm_ops)"
    )

    # role
    op.create_table(
        "role",
        sa.Column("id_role", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("libelle", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id_role"),
        sa.UniqueConstraint("libelle", name="uq_role_libelle"),
    )
    # Les deux rôles du projet, insérés dès la création 
    op.execute("INSERT INTO role (libelle) VALUES ('user'), ('admin')")

    # utilisateur
    op.create_table(
        "utilisateur",
        sa.Column("id_utilisateur", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        # 60 caractères = longueur exacte d'un hash bcrypt.
        sa.Column("password", sa.String(60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id_role", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_utilisateur"),
        sa.UniqueConstraint("email", name="uq_utilisateur_email"),
        sa.ForeignKeyConstraint(
            ["id_role"],
            ["role.id_role"],
            name="fk_utilisateur_id_role_role",
            ondelete="RESTRICT",
        ),
    )

    # log_vlm
    op.create_table(
        "log_vlm",
        sa.Column("id_log", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_aliment", sa.Integer(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("label_identifie", sa.String(255), nullable=True),
        sa.Column("score_confiance", sa.Numeric(5, 4), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id_log"),
        sa.ForeignKeyConstraint(
            ["id_aliment"],
            ["aliment.id_aliment"],
            name="fk_log_vlm_id_aliment_aliment",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_log_vlm_timestamp", "log_vlm", ["timestamp"])


def downgrade() -> None:
    # Ordre inverse de la création, pour respecter les clés étrangères.
    op.drop_index("ix_log_vlm_timestamp", table_name="log_vlm")
    op.drop_table("log_vlm")
    op.drop_table("utilisateur")
    op.drop_table("role")
    op.execute("DROP INDEX IF EXISTS ix_aliment_nom_trgm")
    op.drop_index("ix_aliment_id_categorie", table_name="aliment")
    op.drop_table("aliment")
    op.drop_table("categorie")

