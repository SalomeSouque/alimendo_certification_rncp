"""Gestion des comptes en ligne de commande, sur le serveur.

Sert quand `/docs` est coupé en production et que l'espace admin du front
n'existe pas encore. Exemples, depuis le dossier du docker-compose :

    docker compose exec api python -m app.cli lister
    docker compose exec api python -m app.cli ouvrir-ia jury@example.fr
    docker compose exec api python -m app.cli fermer-ia jury@example.fr
    docker compose exec api python -m app.cli promouvoir-admin moi@example.fr

`promouvoir-admin` ouvre aussi l'accès IA du compte. Le compte doit déjà
exister (inscription par le site).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session
from app.repositories import user_repository


async def _executer(commande: str, email: str | None) -> int:
    """Exécute une commande et renvoie le code de sortie du processus."""
    moteur = db_session.init_engine()
    try:
        async with AsyncSession(moteur, expire_on_commit=False) as session:
            if commande == "lister":
                for u in await user_repository.lister(session):
                    print(
                        f"{u.id_utilisateur}\t{u.email}\t{u.role.libelle}\t"
                        f"acces_ia={u.acces_ia}\t{u.created_at:%Y-%m-%d}"
                    )
                return 0

            assert email is not None  # imposé par argparse
            utilisateur = await user_repository.get_by_email(session, email)
            if utilisateur is None:
                print(f"Aucun compte avec l'email {email}.", file=sys.stderr)
                return 1

            if commande == "promouvoir-admin":
                await user_repository.promouvoir_admin(session, utilisateur)
            else:
                await user_repository.definir_acces_ia(
                    session, utilisateur, commande == "ouvrir-ia"
                )
            await session.commit()
            print(f"{commande} : fait pour {email}.")
            return 0
    finally:
        await db_session.dispose_engine()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.splitlines()[0])
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("lister", help="Lister les comptes et leur accès IA")
    for nom, aide in (
        ("ouvrir-ia", "Ouvrir l'accès IA d'un compte"),
        ("fermer-ia", "Fermer l'accès IA d'un compte"),
        ("promouvoir-admin", "Donner le rôle admin (et l'accès IA) à un compte"),
    ):
        sous.add_parser(nom, help=aide).add_argument("email")
    args = parser.parse_args(argv)
    return asyncio.run(_executer(args.commande, getattr(args, "email", None)))


if __name__ == "__main__":
    raise SystemExit(main())
