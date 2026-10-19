"""Date de dernière connexion des comptes, pour la procédure de tri RGPD.

La procédure de tri (docs/rgpd/procedure_tri.md) supprime les comptes inactifs
depuis 3 ans. Sans date de dernière connexion, on ne peut pas distinguer un
compte ancien mais utilisé d'un compte abandonné : `created_at` ne suffit pas.

La colonne est nullable : les comptes créés avant cette migration n'ont pas
encore de connexion enregistrée. La requête de tri utilise alors `created_at`
(COALESCE(last_login, created_at)).

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "utilisateur",
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Perte assumée : les dates de dernière connexion sont effacées.
    op.drop_column("utilisateur", "last_login")
