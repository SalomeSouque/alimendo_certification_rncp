"""Badges nutritionnels fer et magnésium.

Ils sont hors score et purement factuels. Ils s'appuient sur les
seuils réglementaires du Règlement UE 1169/2011, qui définissent
quand un aliment peut être déclaré « source de » ou « riche en » un nutriment.

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NiveauBadge(StrEnum):
    """Niveau déclaratif d'un nutriment selon le Règlement UE 1169/2011."""

    RICHE = "riche"            # >= 30 % de la VNR pour 100 g
    SOURCE = "source"          # >= 15 % de la VNR pour 100 g
    AUCUN = "aucun"            # sous le seuil déclaratif
    NON_RENSEIGNE = "non_renseigne"  # donnée absente en base


@dataclass(frozen=True)
class SeuilsNutriment:
    """Seuils déclaratifs d'un nutriment, en unité CIQUAL pour 100 g."""

    nutriment: str
    unite: str
    vnr: float           # valeur nutritionnelle de référence
    seuil_source: float  # 15 % de la VNR
    seuil_riche: float   # 30 % de la VNR


SEUILS_BADGES: dict[str, SeuilsNutriment] = {
    "fer": SeuilsNutriment(
        nutriment="fer", unite="mg", vnr=14.0, seuil_source=2.1, seuil_riche=4.2
    ),
    "magnesium": SeuilsNutriment(
        nutriment="magnesium", unite="mg", vnr=375.0, seuil_source=56.3, seuil_riche=112.5
    ),
}

# Libellés
LIBELLES: dict[tuple[str, NiveauBadge], str] = {
    ("fer", NiveauBadge.SOURCE): "Source de fer",
    ("fer", NiveauBadge.RICHE): "Riche en fer",
    ("magnesium", NiveauBadge.SOURCE): "Source de magnésium",
    ("magnesium", NiveauBadge.RICHE): "Riche en magnésium",
}


@dataclass(frozen=True)
class Badge:

    nutriment: str
    niveau: NiveauBadge
    libelle: str | None
    valeur: float | None
    unite: str


def evaluer_badge(nutriment: str, valeur: float | None) -> Badge:
    """Évalue le niveau déclaratif d'un nutriment.

    Args:
        nutriment: "fer" ou "magnesium".
        valeur: teneur pour 100 g, ou None si non mesurée.

    Returns:
        Le badge correspondant. `libelle` vaut None quand rien n'est
        déclarable 
    Raises:
        KeyError: si le nutriment n'est pas géré par les badges.
    """
    seuils = SEUILS_BADGES[nutriment]

    if valeur is None:
        return Badge(nutriment, NiveauBadge.NON_RENSEIGNE, None, None, seuils.unite)

    if valeur >= seuils.seuil_riche:
        niveau = NiveauBadge.RICHE
    elif valeur >= seuils.seuil_source:
        niveau = NiveauBadge.SOURCE
    else:
        niveau = NiveauBadge.AUCUN

    return Badge(
        nutriment=nutriment,
        niveau=niveau,
        libelle=LIBELLES.get((nutriment, niveau)),
        valeur=valeur,
        unite=seuils.unite,
    )


def evaluer_badges(profil: dict[str, float | None]) -> list[Badge]:
    """Évalue tous les badges gérés pour un profil nutritionnel donné."""
    return [evaluer_badge(nom, profil.get(nom)) for nom in SEUILS_BADGES]
