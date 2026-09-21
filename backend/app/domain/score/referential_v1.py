"""Référentiel de score inflammatoire - v1.0, figé.

Séparation :
-La règle (coefficients, seuils, constantes) dans ce fichier Python;
-Les repères de normalisation (médiane, p10, p90 par paramètre)
  dans `landmarks_v1.json`, car données produites par calibration (avec CIQUAL).

"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Version
VERSION_REFERENTIEL = "v1.0"

# Coefficients d'effet inflammatoire
# Signe positif = pro-inflammatoire, négatif = anti-inflammatoire.
COEFS: dict[str, float] = {
    # Pro-inflammatoires (7)
    "glucides": 0.097,
    "proteines": 0.021,
    "lipides": 0.298,
    "graisses_saturees": 0.373,
    "cholesterol": 0.110,
    "fer": 0.032,
    "vitamine_b12": 0.106,
    # Anti-inflammatoires (16)
    "fibres": -0.663,
    "omega3": -0.436,
    "omega6": -0.159,
    "vitamine_a": -0.401,
    "beta_carotene": -0.584,
    "vitamine_c": -0.424,
    "vitamine_d": -0.446,
    "vitamine_e": -0.419,
    "vitamine_b6": -0.365,
    "folates": -0.190,
    "thiamine": -0.098,
    "riboflavine": -0.068,
    "niacine": -0.246,
    "magnesium": -0.484,
    "selenium": -0.191,
    "zinc": -0.313,
}

# Seuils de discrétisation = quintiles observés sur CIQUAL
SEUILS: dict[str, float] = {
    "S1": -0.7268,
    "S2": 0.0307,
    "S3": 0.7063,
    "S4": 1.5368,
}

# Part minimale de paramètres renseignés pour qu'un score soit calculé.
SEUIL_COMPLETUDE = 0.5

# Somme minimale glucides + protéines + lipides, en g/100 g.
SEUIL_APPORT_MINIMAL = 1.0

# Param pour test d'apport nutritionnel min.
MACRONUTRIMENTS: tuple[str, str, str] = ("glucides", "proteines", "lipides")

# Emplacement des repères de normalisation (calibration CIQUAL).
REPERES_PATH = Path(__file__).with_name("landmarks_v1.json")


class ReferentielIncompletError(RuntimeError):
    """Levée quand les repères de normalisation sont absents ou incomplets.

    Un score calculé avec des repères partiels serait faux.
    """


@dataclass(frozen=True)
class RepereParametre:
    """Repères de normalisation d'un paramètre, sur la base de calibration.

    Attributes:
        med: médiane observée sur CIQUAL pour 100 g.
        p10
        p90
    """

    med: float
    p10: float
    p90: float

    @property
    def amplitude_haute(self) -> float:
        """Écart médiane -> p90, dénominateur de la branche positive."""
        return self.p90 - self.med

    @property
    def amplitude_basse(self) -> float:
        """Écart p10 -> médiane, dénominateur de la branche négative."""
        return self.med - self.p10


@lru_cache(maxsize=1)
def get_reperes() -> dict[str, RepereParametre]:
    """Charge et valide les repères de normalisation (mis en cache).

    Returns:
        Dictionnaire {paramètre: RepereParametre} couvrant les 23 paramètres.

    Raises:
        ReferentielIncompletError: si le fichier est absent, mal formé, ou s'il
            manque un paramètre présent dans `COEFS`.
    """
    if not REPERES_PATH.exists():
        raise ReferentielIncompletError(
            f"Repères de normalisation introuvables : {REPERES_PATH}. "
            "Exportez-les depuis la cellule de contrôle final du notebook de "
            "calibration (voir score-referentiel.md §6, clé REPERES)."
        )

    try:
        brut = json.loads(REPERES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReferentielIncompletError(
            f"{REPERES_PATH.name} n'est pas un JSON valide : {exc}"
        ) from exc

    valeurs = brut.get("reperes", brut)

    manquants = sorted(set(COEFS) - set(valeurs))
    if manquants:
        raise ReferentielIncompletError(
            f"Repères manquants pour {len(manquants)} paramètre(s) : "
            f"{', '.join(manquants)}. Le score ne peut pas être calculé sans eux."
        )

    reperes: dict[str, RepereParametre] = {}
    for parametre in COEFS:
        entree = valeurs[parametre]
        try:
            # Le notebook de calibration exporte la clé sous le nom `mediane`,
            # ce module la nomme `med` : les deux sont acceptées pour éviter
            # une conversion manuelle à chaque réexport.
            mediane = entree.get("med", entree.get("mediane"))
            repere = RepereParametre(
                med=float(mediane),
                p10=float(entree["p10"]),
                p90=float(entree["p90"]),
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ReferentielIncompletError(
                f"Repère invalide pour {parametre!r} : attendu "
                '{"med" (ou "mediane"): ..., "p10": ..., "p90": ...}, reçu '
                + repr(entree)
            ) from exc
        reperes[parametre] = repere

    return reperes


def referentiel_est_pret() -> bool:
    """Indique si les repères sont chargeables - utilisé par le healthcheck."""
    try:
        get_reperes()
    except ReferentielIncompletError:
        return False
    return True
