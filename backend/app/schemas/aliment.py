"""Schémas Pydantic des aliments, du score et des alternatives.

Chaque réponse portant un score expose `version_referentiel` puisque le score est recalculé à la volée et que
seule la règle est figée.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategorieOut(BaseModel):
    """Catégorie alimentaire."""

    model_config = ConfigDict(from_attributes=True)

    id_categorie: int
    nom: str
    image: str | None = None


class AlimentResume(BaseModel):
    """Aliment sans détail nutritionnel, pour les listes de résultats."""

    model_config = ConfigDict(from_attributes=True)

    id_aliment: int
    nom: str
    source: str
    url_image: str | None = None
    id_categorie: int | None = None


class BadgeOut(BaseModel):
    """Badge nutritionnel fer ou magnésium."""

    nutriment: str
    niveau: str = Field(description="riche | source | aucun | non_renseigne")
    libelle: str | None = Field(
        default=None,
        description="Libellé validé à afficher, ou null si rien n'est déclarable.",
    )
    valeur: float | None = None
    unite: str


class ScoreOut(BaseModel):
    """Résultat d'un calcul de score.

    Quand `disponible` est False, `niveau` et `score_brut` valent null et
    `message` porte la formulation validée à afficher.
    """

    disponible: bool
    niveau: int | None = Field(default=None, ge=-2, le=2)
    libelle: str | None = None
    score_brut: float | None = None
    causes: list[str] = Field(default_factory=list)
    completude: float = Field(ge=0.0, le=1.0)
    parametres_utilises: int
    message: str | None = None
    version_referentiel: str


class AlternativeOut(BaseModel):
    """Alternative proposée dans la même catégorie.

    Présentée comme une option nutritionnelle, non comme un conseil de santé.
    """

    aliment: AlimentResume
    score: ScoreOut


class AlimentDetail(BaseModel):
    """Réponse complète d'une consultation d'aliment.

    C'est la charge utile des trois parcours score (photo, code-barre,
    recherche texte) : ils convergent tous vers cette structure.
    """

    aliment: AlimentResume
    score: ScoreOut
    badges: list[BadgeOut] = Field(default_factory=list)
    alternatives: list[AlternativeOut] = Field(default_factory=list)
    libelle_alternatives: str
    disclaimer: str
    mention_projet_etudiant: str
    citation_source: str


class RechercheResultat(BaseModel):
    """Réponse de `GET /search/aliments`."""

    terme: str
    nombre_resultats: int
    resultats: list[AlimentResume]
