"""Accès aux données `utilisateur` et `role`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ROLE_ADMIN, ROLE_USER, Role, Utilisateur


async def get_by_email(session: AsyncSession, email: str) -> Utilisateur | None:
    """Récupère un utilisateur par son email (normalisé en minuscules)."""
    requete = select(Utilisateur).where(Utilisateur.email == email.strip().lower())
    resultat = await session.execute(requete)
    return resultat.scalar_one_or_none()


async def get_by_id(session: AsyncSession, id_utilisateur: int) -> Utilisateur | None:
    """Récupère un utilisateur par sa clé primaire."""
    return await session.get(Utilisateur, id_utilisateur)


async def get_role_by_libelle(session: AsyncSession, libelle: str) -> Role | None:
    """Récupère un rôle par son libellé ("user" ou "admin")."""
    requete = select(Role).where(Role.libelle == libelle)
    resultat = await session.execute(requete)
    return resultat.scalar_one_or_none()


async def enregistrer_connexion(session: AsyncSession, utilisateur: Utilisateur) -> None:
    """Note la date de la connexion réussie (base de la procédure de tri RGPD).

    Le commit reste à la charge du service appelant.
    """
    utilisateur.last_login = datetime.now(UTC)
    await session.flush()


async def creer(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    role_libelle: str = ROLE_USER,
) -> Utilisateur:
    """Crée un utilisateur et le persiste.

    Le mdp est reçu haché : ce repository ne connaît pas
    bcrypt, c'est le service d'authentification qui s'en charge.

    Args:
        session: session SQLAlchemy.
        email: email, normalisé en minuscules.
        password_hash: hash bcrypt de 60 caractères.
        role_libelle: rôle à attribuer, "user" par défaut.

    Returns:
        L'utilisateur créé, avec sa clé primaire renseignée.

    Raises:
        ValueError: si le rôle demandé n'existe pas en base.
    """
    role = await get_role_by_libelle(session, role_libelle)
    if role is None:
        raise ValueError(
            f"Rôle {role_libelle!r} absent de la base. "
            "La migration 0001 doit avoir inséré 'user' et 'admin'."
        )

    utilisateur = Utilisateur(
        email=email.strip().lower(),
        password=password_hash,
        id_role=role.id_role,
    )
    session.add(utilisateur)
    await session.flush()   # attribue la clé primaire sans clore la transaction
    await session.refresh(utilisateur, attribute_names=["role", "created_at"])
    return utilisateur


async def lister(session: AsyncSession) -> list[Utilisateur]:
    """Liste les comptes, du plus récent au plus ancien (vue admin)."""
    requete = select(Utilisateur).order_by(Utilisateur.created_at.desc())
    resultat = await session.execute(requete)
    return list(resultat.scalars().all())


async def definir_acces_ia(
    session: AsyncSession, utilisateur: Utilisateur, acces_ia: bool
) -> None:
    """Ouvre ou ferme l'accès aux routes /ai/* d'un compte.

    Le commit reste à la charge de l'appelant.
    """
    utilisateur.acces_ia = acces_ia
    await session.flush()


async def promouvoir_admin(session: AsyncSession, utilisateur: Utilisateur) -> None:
    """Donne le rôle admin à un compte et lui ouvre l'accès IA.

    L'accès IA est ouvert en même temps : la règle d'accès ne fait pas
    d'exception pour le rôle admin, une admin sans accès IA ne pourrait pas
    tester le chatbot. Le commit reste à la charge de l'appelant.

    Raises:
        ValueError: si le rôle admin est absent de la base.
    """
    role = await get_role_by_libelle(session, ROLE_ADMIN)
    if role is None:
        raise ValueError("Rôle 'admin' absent de la base (migration 0001).")
    utilisateur.id_role = role.id_role
    utilisateur.acces_ia = True
    await session.flush()