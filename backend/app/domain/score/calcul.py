"""Calcul du score inflammatoire / implémentation du référentiel v1.0.

Le calcul suit 4 étapes :
1. nettoyage des valeurs (fait en amont, à l'ETL) ;
2. normalisation centrée sur [−1, +1] à partir de la médiane et des centiles ;
3. score brut = somme pondérée des paramètres renseignés ;
4. discrétisation en niveau entier de −2 à +2.

2 règles de "non-calcul" : complétude insuffisante / absence d'apport nutritionnel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.score.referential_v1 import (
    COEFS,
    MACRONUTRIMENTS,
    SEUIL_APPORT_MINIMAL,
    SEUIL_COMPLETUDE,
    SEUILS,
    VERSION_REFERENTIEL,
    LandmarkParameter,
    get_landmarks,
)


class CauseIndisponibilite(StrEnum):
    """Raison pour aucun score calculé"""

    # Moins de 50 % des params renseignés.
    COMPLETUDE_INSUFFISANTE = "completude_insuffisante"
    # glucides + protéines + lipides < 1 g/100 g (eaux, thés, boissons light).
    HORS_PERIMETRE = "hors_perimetre"


@dataclass(frozen=True)
class ResultatScore:
    """Résultat complet d'un calcul de score.

    Attributes:
        disponible: False si une des règles non-calcul.
        niveau: niveau discret de −2 à +2, ou None si indisponible.
        score_brut: somme pondérée avant discrétisation, ou None.
        causes: causes de non-calcul.
        completude: part des paramètres renseignés, entre 0 et 1.
        parametres_utilises: nombre de paramètres entrés dans le calcul.
        version_referentiel: version de la règle.
    """

    disponible: bool
    niveau: int | None
    score_brut: float | None
    completude: float
    parametres_utilises: int
    causes: tuple[CauseIndisponibilite, ...] = field(default_factory=tuple)
    version_referentiel: str = VERSION_REFERENTIEL


def normaliser(valeur: float, repere: LandmarkParameter) -> float:
    """Normalise une teneur sur [−1, +1], centrée sur la médiane.

    Teneur supérieure médiane = contribution positive. 
    Teneur inférieure médiane = contribution négative. 
    Zéro = profil médian.

    Args:
        valeur: teneur mesurée pour 100 g.
        repere: médiane, p10 et p90 du paramètre sur la base de calibration.

    Returns:
        La valeur normalisée, bornée à [−1, +1].
    """
    if valeur >= repere.med:
        amplitude = repere.amplitude_haute
        # Distribution dégénérée (p90 == médiane) : on ne peut pas discriminer
        # au-dessus de la médiane, la contribution est neutre.
        if amplitude <= 0:
            return 0.0
        return min((valeur - repere.med) / amplitude, 1.0)

    amplitude = repere.amplitude_basse
    if amplitude <= 0:
        return 0.0
    return max((valeur - repere.med) / amplitude, -1.0)


def discretiser(score_brut: float) -> int:
    """Convertit un score brut en niveau entier de −2 à +2."""
    if score_brut <= SEUILS["S1"]:
        return -2
    if score_brut <= SEUILS["S2"]:
        return -1
    if score_brut <= SEUILS["S3"]:
        return 0
    if score_brut <= SEUILS["S4"]:
        return 1
    return 2


def _causes_indisponibilite(
    profil: dict[str, float | None], completude: float
) -> tuple[CauseIndisponibilite, ...]:
    """Applique les deux règles de "non-calcul".
    """
    causes: list[CauseIndisponibilite] = []

    if completude < SEUIL_COMPLETUDE:
        causes.append(CauseIndisponibilite.COMPLETUDE_INSUFFISANTE)

    apport = sum(profil.get(nom) or 0.0 for nom in MACRONUTRIMENTS)
    if apport < SEUIL_APPORT_MINIMAL:
        causes.append(CauseIndisponibilite.HORS_PERIMETRE)

    return tuple(causes)


def calculer_score(profil: dict[str, float | None]) -> ResultatScore:
    """Calcule le score inflammatoire d'un aliment à partir de son profil.

    Args:
        profil: dictionnaire {paramètre: teneur pour 100 g ou None} (clés absentes
            traitées comme non renseignées).

    Returns:
        Un `ResultatScore`, disponible ou non.

    Raises:
        ReferentielIncompletError: si les repères de normalisation ne sont pas
            chargeables (fichier `landmarks_v1.json` absent ou incomplet).
    """
    landmarks = get_landmarks()

    renseignes = {
        nom: valeur
        for nom, valeur in profil.items()
        if nom in COEFS and valeur is not None
    }
    completude = len(renseignes) / len(COEFS)

    causes = _causes_indisponibilite(profil, completude)
    if causes:
        return ResultatScore(
            disponible=False,
            niveau=None,
            score_brut=None,
            completude=completude,
            parametres_utilises=len(renseignes),
            causes=causes,
        )

    score_brut = sum(
        normaliser(valeur, landmarks[nom]) * COEFS[nom]
        for nom, valeur in renseignes.items()
    )

    return ResultatScore(
        disponible=True,
        niveau=discretiser(score_brut),
        score_brut=round(score_brut, 4),
        completude=completude,
        parametres_utilises=len(renseignes),
    )


def contributions(profil: dict[str, float | None]) -> dict[str, float]:
    """Détaille la contribution de chaque paramètre au score brut.

    Utile pour le débogage, la page « Comment lire ce score » et
    la justification à l'oral. 
    Returns:
        {paramètre: contribution signée}, trié du plus pro-inflammatoire au
        plus anti-inflammatoire.
    """
    landmarks = get_landmarks()
    detail = {
        nom: normaliser(valeur, landmarks[nom]) * COEFS[nom]
        for nom, valeur in profil.items()
        if nom in COEFS and valeur is not None
    }
    return dict(sorted(detail.items(), key=lambda item: item[1], reverse=True))
