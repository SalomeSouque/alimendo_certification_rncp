"""Accès aux features IA sur validation manuelle.

L'inscription reste libre, mais /ai/chat et /ai/vision consomment la clé
Mistral (payante) et le VLM du serveur. Un compte n'y accède qu'une fois
validé par une admin : `acces_ia` passe alors à vrai.

Faux par défaut, y compris pour les comptes existants : chaque accès est
ouvert explicitement (endpoint admin ou script `python -m app.cli`).

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "utilisateur",
        sa.Column(
            "acces_ia",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    # Perte assumée : les validations d'accès sont effacées.
    op.drop_column("utilisateur", "acces_ia")
