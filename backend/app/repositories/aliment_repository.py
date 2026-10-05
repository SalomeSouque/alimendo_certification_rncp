"""Accès aux données `aliment` et `categorie`.

Toute requête SQL touchant ces tables vit ici. Les routers et les services
appellent des fonctions nommées.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Aliment, Categorie


async def get_by_id(session: AsyncSession, id_aliment: int) -> Aliment | None:
    """Récupère un aliment par sa clé primaire."""
    return await session.get(Aliment, id_aliment)


async def rechercher_par_nom(
    session: AsyncSession, terme: str, *, limite: int = 20
) -> list[Aliment]:
    """Recherche des aliments par nom, tolérante aux fautes de frappe.

    Utilise l'opérateur de similarité trigramme de `pg_trgm` (extension posée
    par la migration 0001). Un `ILIKE %terme%` seul ne trouverait pas
    « tomate » à partir de « tomates » mal orthographié, ni l'inverse.

    Le tri combine deux critères : d'abord la similarité décroissante, puis
    le nom, pour que deux aliments également proches sortent dans un ordre
    stable d'un appel à l'autre.

    Args:
        session: session SQLAlchemy.
        terme: texte saisi par l'utilisatrice.
        limite: nombre maximum de résultats.

    Returns:
        La liste des aliments correspondants, du plus proche au plus éloigné.
    """
    terme_propre = terme.strip()
    if not terme_propre:
        return []

    similarite = func.similarity(Aliment.nom, terme_propre)

    requete = (
        select(Aliment)
        .where(
            # Le ILIKE rattrape les sous-chaînes exactes que le trigramme
            # noterait bas sur un terme court (« riz » dans « riz blanc cuit »).
            or_(
                similarite > 0.2,
                Aliment.nom.ilike(f"%{terme_propre}%"),
            )
        )
        .order_by(similarite.desc(), Aliment.nom)
        .limit(limite)
    )
    resultat = await session.execute(requete)
    return list(resultat.scalars().all())


async def lister_par_categorie(
    session: AsyncSession,
    id_categorie: int,
    *,
    exclure_id: int | None = None,
) -> list[Aliment]:
    """Liste les aliments d'une catégorie : base de la recherche d'alternatives.

    Args:
        session: session SQLAlchemy.
        id_categorie: catégorie dans laquelle chercher.
        exclure_id: aliment à exclure (celui que l'utilisatrice consulte).

    Returns:
        Tous les aliments de la catégorie. Le tri par score se fait ensuite en
        Python, puisque le score n'est pas stocké en base.
    """
    requete = select(Aliment).where(Aliment.id_categorie == id_categorie)
    if exclure_id is not None:
        requete = requete.where(Aliment.id_aliment != exclure_id)
    resultat = await session.execute(requete)
    return list(resultat.scalars().all())


async def get_categorie(session: AsyncSession, id_categorie: int) -> Categorie | None:
    """Récupère une catégorie par sa clé primaire."""
    return await session.get(Categorie, id_categorie)


async def lister_categories(session: AsyncSession) -> list[Categorie]:
    """Liste toutes les catégories, triées par nom."""
    resultat = await session.execute(select(Categorie).order_by(Categorie.nom))
    return list(resultat.scalars().all())


async def compter_aliments(session: AsyncSession) -> int:
    """Compte les aliments en base / utilisé par le healthcheck détaillé."""
    resultat = await session.execute(select(func.count()).select_from(Aliment))
    return int(resultat.scalar_one())
