"""Modèles ORM `role` et `utilisateur`, transcrits du MPD d'authentification.

`password` fait 60 caractères (longueur d'un hash bcrypt) 
Le mot de passe en clair n'est jamais stocké ni journalisé.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Rôles attendus en base
ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLES_PAR_DEFAUT: tuple[str, ...] = (ROLE_USER, ROLE_ADMIN)


class Role(Base):
    """Rôle applicatif : `user` ou `admin`."""

    __tablename__ = "role"

    id_role: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    utilisateurs: Mapped[list[Utilisateur]] = relationship(back_populates="role")

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"Role(id={self.id_role}, libelle={self.libelle!r})"


class Utilisateur(Base):
    """Compte utilisateur authentifié par JWT."""

    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Mise à jour à chaque connexion réussie. Sert à la procédure de tri RGPD
    # (suppression après 3 ans d'inactivité). NULL = aucune connexion enregistrée.
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Accès aux routes /ai/* : ouvert à la main par une admin (migration 0004).
    # Relu en base à chaque appel IA, pour qu'une révocation agisse tout de suite.
    acces_ia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    id_role: Mapped[int] = mapped_column(
        ForeignKey("role.id_role", ondelete="RESTRICT"), nullable=False
    )

    role: Mapped[Role] = relationship(back_populates="utilisateurs", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        # On n'affiche jamais le hash : les `repr` finissent dans les logs.
        return f"Utilisateur(id={self.id_utilisateur}, email={self.email!r})"