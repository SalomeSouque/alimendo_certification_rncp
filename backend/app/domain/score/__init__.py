"""Domaine métier du score inflammatoire.

Le calcul est isolé de l'infrastructure (base, HTTP, FastAPI) :
il ne dépend que de dictionnaires de nombres. Ce qui permet de le tester
sans base de données et de le rejouer à l'identique sur des cas connus.
"""

from app.domain.score.badges import (
    SEUILS_BADGES,
    Badge,
    NiveauBadge,
    evaluer_badge,
    evaluer_badges,
)
from app.domain.score.calcul import (
    CauseIndisponibilite,
    ResultatScore,
    calculer_score,
    contributions,
    discretiser,
    normaliser,
)
from app.domain.score.referential_v1 import (
    COEFS,
    SEUIL_APPORT_MINIMAL,
    SEUIL_COMPLETUDE,
    SEUILS,
    VERSION_REFERENTIEL,
    ReferentielIncompletError,
    get_landmarks,
    referentiel_est_pret,
)

__all__ = [
    "COEFS",
    "SEUILS",
    "SEUILS_BADGES",
    "SEUIL_APPORT_MINIMAL",
    "SEUIL_COMPLETUDE",
    "VERSION_REFERENTIEL",
    "Badge",
    "CauseIndisponibilite",
    "NiveauBadge",
    "ReferentielIncompletError",
    "ResultatScore",
    "calculer_score",
    "contributions",
    "discretiser",
    "evaluer_badge",
    "evaluer_badges",
    "get_landmarks",
    "normaliser",
    "referentiel_est_pret",
]
