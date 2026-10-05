"""Service d'alternatives : propose des aliments au profil moins pro-inflammatoire.

- ne proposer une alternative qu'au sein de la même catégorie ;
- formuler comme une option nutritionnelle.

Note : le score n'étant pas stocké, on calcule celui de tous les aliments de la catégorie à chaque requête. 
Sur une catégorie de quelques centaines d'aliments le calcul est de l'ordre de
la milliseconde : acceptable pour le POC.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Aliment
from app.repositories import aliment_repository
from app.schemas.aliment import AlimentResume, AlternativeOut
from app.services import score_service

# Catégories exclues de toute proposition d'alternative.
CATEGORIES_EXCLUES: frozenset[str] = frozenset(
    {
        "aides culinaires et ingrédients divers",  # épices, condiments, bouillons
        "aliments infantiles",                     # produits enrichis
    }
)

# Nombre maximum d'alternatives renvoyées.
NOMBRE_ALTERNATIVES = 3


def _categorie_autorisee(nom_categorie: str | None) -> bool:
    """Indique si une catégorie peut fournir des alternatives."""
    if nom_categorie is None:
        return False
    return nom_categorie.strip().lower() not in CATEGORIES_EXCLUES


async def trouver_alternatives(
    session: AsyncSession,
    aliment: Aliment,
    *,
    limite: int = NOMBRE_ALTERNATIVES,
) -> list[AlternativeOut]:
    """Cherche des alternatives au profil moins pro-inflammatoire.

    Args:
        session: session SQLAlchemy.
        aliment: aliment consulté par l'utilisatrice.
        limite: nombre maximum d'alternatives à renvoyer.

    Returns:
        Alternatives triées du plus favorable au moins favorable. 
        Liste vide si : pas de catégorie exploitable, catégorie exclue, score indisponible.
    """
    if aliment.id_categorie is None:
        return []

    categorie = await aliment_repository.get_categorie(session, aliment.id_categorie)
    if categorie is None or not _categorie_autorisee(categorie.nom):
        return []

    score_reference = score_service.scorer_aliment(aliment)
    if not score_reference.disponible or score_reference.niveau is None:
        return []

    candidats = await aliment_repository.lister_par_categorie(
        session, aliment.id_categorie, exclure_id=aliment.id_aliment
    )

    alternatives: list[tuple[float, AlternativeOut]] = []
    for candidat in candidats:
        score = score_service.scorer_aliment(candidat)
        if not score.disponible or score.score_brut is None:
            continue
        # Strictement meilleur : un score égal n'apporte rien à l'utilisatrice.
        if score.niveau is not None and score.niveau >= score_reference.niveau:
            continue
        alternatives.append(
            (
                score.score_brut,
                AlternativeOut(
                    aliment=AlimentResume.model_validate(candidat), score=score
                ),
            )
        )

    alternatives.sort(key=lambda couple: couple[0])
    return [alternative for _, alternative in alternatives[:limite]]
