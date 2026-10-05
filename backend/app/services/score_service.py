"""Service score : fait le pont entre le domaine pur et les schémas d'API.

Le calcul lui-même vit dans `app/domain/score/`. Ce service se contente de :

- extraire le profil nutritionnel d'un modèle ORM ;
- traduire le résultat en schéma de sortie ;
- y attacher les formulations validées (libellés, messages, disclaimers).

=> La logique métier reste testable sans FastAPI ni base de données.
"""

from __future__ import annotations

from app.core.disclaimers import (
    LIBELLES_NIVEAU,
    MESSAGE_COMPLETUDE_INSUFFISANTE,
    MESSAGE_HORS_PERIMETRE,
)
from app.db.models import Aliment
from app.domain.score import (
    VERSION_REFERENTIEL,
    CauseIndisponibilite,
    ResultatScore,
    calculer_score,
    evaluer_badges,
)
from app.schemas.aliment import BadgeOut, ScoreOut

# Message affiché pour chaque cause de non-calcul (formulations validées).
_MESSAGES_PAR_CAUSE: dict[CauseIndisponibilite, str] = {
    CauseIndisponibilite.COMPLETUDE_INSUFFISANTE: MESSAGE_COMPLETUDE_INSUFFISANTE,
    CauseIndisponibilite.HORS_PERIMETRE: MESSAGE_HORS_PERIMETRE,
}


def _message_indisponibilite(causes: tuple[CauseIndisponibilite, ...]) -> str:
    """Choisit le message à afficher quand plusieurs causes se cumulent.

    Le référentiel précise qu'un aliment peut cumuler les deux causes. On
    affiche alors celle qui est la plus informative pour l'utilisatrice.
    """
    if CauseIndisponibilite.HORS_PERIMETRE in causes:
        return MESSAGE_HORS_PERIMETRE
    return _MESSAGES_PAR_CAUSE[causes[0]]


def vers_schema(resultat: ResultatScore) -> ScoreOut:
    """Traduit un `ResultatScore` du domaine en schéma d'API."""
    if not resultat.disponible:
        return ScoreOut(
            disponible=False,
            niveau=None,
            libelle=None,
            score_brut=None,
            causes=[cause.value for cause in resultat.causes],
            completude=round(resultat.completude, 3),
            parametres_utilises=resultat.parametres_utilises,
            message=_message_indisponibilite(resultat.causes),
            version_referentiel=resultat.version_referentiel,
        )

    assert resultat.niveau is not None  # garanti quand disponible est True
    return ScoreOut(
        disponible=True,
        niveau=resultat.niveau,
        libelle=LIBELLES_NIVEAU[resultat.niveau],
        score_brut=resultat.score_brut,
        causes=[],
        completude=round(resultat.completude, 3),
        parametres_utilises=resultat.parametres_utilises,
        message=None,
        version_referentiel=resultat.version_referentiel,
    )


def scorer_aliment(aliment: Aliment) -> ScoreOut:
    """Calcule le score d'un aliment issu de la base."""
    return vers_schema(calculer_score(aliment.profil_nutritionnel()))


def scorer_profil(profil: dict[str, float | None]) -> ScoreOut:
    """Calcule le score d'un profil nutritionnel brut.

    Utilisé pour les produits Open Food Facts, qui ne sont pas stockés en base
    mais dont on connaît la composition.
    """
    return vers_schema(calculer_score(profil))


def badges_aliment(aliment: Aliment) -> list[BadgeOut]:
    """Évalue les badges fer et magnésium d'un aliment."""
    return badges_profil(aliment.profil_nutritionnel())


def badges_profil(profil: dict[str, float | None]) -> list[BadgeOut]:
    """Évalue les badges fer et magnésium d'un profil nutritionnel."""
    return [
        BadgeOut(
            nutriment=badge.nutriment,
            niveau=badge.niveau.value,
            libelle=badge.libelle,
            valeur=badge.valeur,
            unite=badge.unite,
        )
        for badge in evaluer_badges(profil)
    ]


__all__ = [
    "VERSION_REFERENTIEL",
    "badges_aliment",
    "badges_profil",
    "scorer_aliment",
    "scorer_profil",
    "vers_schema",
]
