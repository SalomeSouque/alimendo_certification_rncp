"""Tests des badges nutritionnels fer et magnésium."""

from __future__ import annotations

import pytest

from app.domain.score.badges import NiveauBadge, evaluer_badge, evaluer_badges


@pytest.mark.parametrize(
    ("valeur", "niveau_attendu"),
    [
        (0.0, NiveauBadge.AUCUN),
        (2.0, NiveauBadge.AUCUN),
        (2.1, NiveauBadge.SOURCE),   # seuil 15 % de la VNR, borne incluse
        (4.1, NiveauBadge.SOURCE),
        (4.2, NiveauBadge.RICHE),    # seuil 30 % de la VNR, borne incluse
        (12.0, NiveauBadge.RICHE),
    ],
)
def test_seuils_fer(valeur, niveau_attendu):
    assert evaluer_badge("fer", valeur).niveau is niveau_attendu


@pytest.mark.parametrize(
    ("valeur", "niveau_attendu"),
    [
        (50.0, NiveauBadge.AUCUN),
        (56.3, NiveauBadge.SOURCE),
        (112.5, NiveauBadge.RICHE),
    ],
)
def test_seuils_magnesium(valeur, niveau_attendu):
    assert evaluer_badge("magnesium", valeur).niveau is niveau_attendu


def test_donnee_absente_nest_pas_une_absence_de_nutriment():
    """« Non renseigné » et « n'en contient pas » sont deux choses différentes.
    """
    badge = evaluer_badge("fer", None)

    assert badge.niveau is NiveauBadge.NON_RENSEIGNE
    assert badge.libelle is None
    assert badge.valeur is None


def test_aucun_libelle_sous_le_seuil_declaratif():
    """Sous le seuil, rien n'est déclarable = aucun libellé produit."""
    assert evaluer_badge("fer", 1.0).libelle is None


def test_libelles_conformes_au_referentiel():
    """Les libellés affichés sont ceux validés."""
    assert evaluer_badge("fer", 5.0).libelle == "Riche en fer"
    assert evaluer_badge("fer", 3.0).libelle == "Source de fer"
    assert evaluer_badge("magnesium", 200.0).libelle == "Riche en magnésium"


def test_evaluer_badges_couvre_les_deux_nutriments():
    badges = evaluer_badges({"fer": 5.0, "magnesium": None})

    assert {b.nutriment for b in badges} == {"fer", "magnesium"}


def test_nutriment_non_gere_leve_une_erreur():
    """Un nutriment hors périmètre doit échouer 'bruyamment'"""
    with pytest.raises(KeyError):
        evaluer_badge("calcium", 100.0)
