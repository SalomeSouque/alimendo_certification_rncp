"""Tests du calcul de score 
Ces tests ne touchent ni la base, ni le réseau, ni FastAPI.
"""

from __future__ import annotations

import pytest

from app.domain.score.calcul import (
    CauseIndisponibilite,
    calculer_score,
    discretiser,
    normaliser,
)
from app.domain.score.referentiel_v1 import COEFS, SEUILS, RepereParametre


# Normalisation


@pytest.fixture
def repere() -> RepereParametre:
    return RepereParametre(med=10.0, p10=0.0, p90=20.0)


def test_normalisation_mediane_vaut_zero(repere):
    """Une teneur médiane est neutre non « absente »."""
    assert normaliser(10.0, repere) == 0.0


def test_normalisation_bornee_a_un(repere):
    """Au-delà du p90, la contribution est plafonnée à +1."""
    assert normaliser(20.0, repere) == 1.0
    assert normaliser(1_000.0, repere) == 1.0


def test_normalisation_bornee_a_moins_un(repere):
    """En dessous du p10, la contribution est plafonnée à −1."""
    assert normaliser(0.0, repere) == -1.0
    assert normaliser(-50.0, repere) == -1.0


def test_normalisation_lineaire_entre_reperes(repere):
    """Entre médiane et p90, la normalisation est proportionnelle."""
    assert normaliser(15.0, repere) == pytest.approx(0.5)
    assert normaliser(5.0, repere) == pytest.approx(-0.5)


def test_normalisation_distribution_degeneree():
    """Si p90 == médiane, on ne peut pas discriminer : contribution neutre.

    Ce cas existe, certains micronutriments sont à zéro sur plus
    de 90 % de la table CIQUAL. Sans ce garde-fou, on diviserait par zéro.
    """
    plat = RepereParametre(med=0.0, p10=0.0, p90=0.0)
    assert normaliser(0.0, plat) == 0.0
    assert normaliser(5.0, plat) == 0.0



# Discrétisation


@pytest.mark.parametrize(
    ("score_brut", "attendu"),
    [
        (-5.0, -2),
        (SEUILS["S1"], -2),          # borne incluse dans le niveau inférieur
        (SEUILS["S1"] + 0.001, -1),
        (SEUILS["S2"], -1),
        (SEUILS["S2"] + 0.001, 0),
        (SEUILS["S3"], 0),
        (SEUILS["S3"] + 0.001, 1),
        (SEUILS["S4"], 1),
        (SEUILS["S4"] + 0.001, 2),
        (10.0, 2),
    ],
)
def test_discretisation_respecte_les_seuils(score_brut, attendu):
    """Les bornes sont fermées à droite"""
    assert discretiser(score_brut) == attendu



# Règles de non-calcul


def _profil_complet(valeur: float = 10.0) -> dict[str, float | None]:
    """Profil où les 23 paramètres sont renseignés à la même valeur."""
    return dict.fromkeys(COEFS, valeur)


def test_completude_insuffisante(patch_reperes):
    """Moins de 50 % de paramètres = aucun score calculé."""
    profil: dict[str, float | None] = dict.fromkeys(COEFS, None)
    for nom in ("glucides", "proteines", "lipides", "fibres", "fer"):
        profil[nom] = 10.0

    resultat = calculer_score(profil)

    assert resultat.disponible is False
    assert CauseIndisponibilite.COMPLETUDE_INSUFFISANTE in resultat.causes
    assert resultat.niveau is None


def test_hors_perimetre_cas_de_l_eau(patch_reperes):
    """Un produit sans apport nutritionnel est hors périmètre.
    """
    profil = _profil_complet(10.0)
    profil["glucides"] = 0.0
    profil["proteines"] = 0.0
    profil["lipides"] = 0.0

    resultat = calculer_score(profil)

    assert resultat.disponible is False
    assert CauseIndisponibilite.HORS_PERIMETRE in resultat.causes


def test_les_deux_causes_peuvent_se_cumuler(patch_reperes):
    """Un aliment peut cumuler les deux causes"""
    profil: dict[str, float | None] = dict.fromkeys(COEFS, None)
    profil["fibres"] = 2.0  # 1 paramètre sur 23, et aucun macronutriment

    resultat = calculer_score(profil)

    assert resultat.disponible is False
    assert set(resultat.causes) == {
        CauseIndisponibilite.COMPLETUDE_INSUFFISANTE,
        CauseIndisponibilite.HORS_PERIMETRE,
    }



# Score brut


def test_profil_median_donne_un_score_nul(patch_reperes):
    """Tous les paramètres à la médiane : toutes les contributions s'annulent."""
    resultat = calculer_score(_profil_complet(10.0))

    assert resultat.disponible is True
    assert resultat.score_brut == pytest.approx(0.0)
    assert resultat.parametres_utilises == len(COEFS)
    assert resultat.completude == 1.0


def test_profil_riche_en_tout_penche_vers_anti_inflammatoire(patch_reperes):
    """Avec toutes les teneurs au p90, la somme des coefficients l'emporte.

    """
    resultat = calculer_score(_profil_complet(20.0))

    assert resultat.disponible is True
    assert resultat.score_brut == pytest.approx(sum(COEFS.values()), abs=1e-6)
    assert resultat.score_brut < 0


def test_parametre_manquant_est_exclu_et_non_mis_a_zero(patch_reperes):
    """Un paramètre non mesuré ne doit pas être traité comme « médian ».

    Ici on retire un paramètre fortement anti-inflammatoire (les fibres) : le
    score doit remonter d'exactement sa contribution
    """
    profil_complet = _profil_complet(20.0)
    profil_sans_fibres = dict(profil_complet)
    profil_sans_fibres["fibres"] = None

    avec = calculer_score(profil_complet)
    sans = calculer_score(profil_sans_fibres)

    assert sans.parametres_utilises == avec.parametres_utilises - 1
    assert sans.score_brut == pytest.approx(avec.score_brut - COEFS["fibres"], abs=1e-6)


def test_version_referentiel_toujours_exposee(patch_reperes):
    """Toute réponse portant un score expose la version de la règle"""
    resultat = calculer_score(_profil_complet(10.0))
    assert resultat.version_referentiel == "v1.0"
