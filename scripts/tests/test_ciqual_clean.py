"""Tests unitaires des règles de nettoyage CIQUAL (sans fichier source ni réseau).

Usage :
    uv run --group data --group dev pytest scripts/tests -q
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ciqual_clean import (
    categories_depuis_code,
    classer_format,
    convertir_valeur,
    fusionner_doublons,
    trouver_colonne_unique,
    unite_colonne,
)


@pytest.mark.parametrize("brute, attendu", [
    ("", "vide"), (" - ", "tiret"), ("Traces", "traces"), ("< 0,1", "inférieur à (< X)"),
    ("12.5", "nombre (point)"), ("1e-05", "nombre (point)"), ("12,5", "nombre (virgule)"),
    ("\xa012,5", "nombre (virgule)"), ("#REF!", "autre texte"), (None, "vide"),
])
def test_classer_format(brute, attendu):
    assert classer_format(brute) == attendu


@pytest.mark.parametrize("brute, attendu", [
    ("12,5", 12.5), ("12.5", 12.5), ("0", 0.0), ("traces", 0.0), ("< 0,1", 0.0), ("1e-05", 1e-05),
])
def test_convertir_valeur_nombres(brute, attendu):
    assert convertir_valeur(brute) == attendu


@pytest.mark.parametrize("brute", ["", "-", "#REF!", None])
def test_non_mesure_devient_null_jamais_zero(brute):
    """Règle centrale du référentiel v1.0 : non mesuré ≠ 0."""
    assert math.isnan(convertir_valeur(brute))


def test_trouver_colonne_unique_refuse_ambiguite():
    colonnes = ["Vitamine B1 (mg/100 g)", "Vitamine B12 (µg/100 g)"]
    assert trouver_colonne_unique(colonnes, ["vitamine b12"]) == "Vitamine B12 (µg/100 g)"
    with pytest.raises(KeyError):
        trouver_colonne_unique(colonnes, ["vitamine b1"])     # 2 colonnes correspondent


def test_unite_colonne():
    assert unite_colonne("Sélénium (µg/100 g)") == "µg"
    assert unite_colonne("Energie, Règlement UE N° 1169/2011 (kcal/100 g)") == "kcal"


def _ident(codes, noms, grp_codes=None, grp_noms=None):
    n = len(codes)
    return pd.DataFrame({"alim_code": codes, "alim_nom_fr": noms,
                         "alim_grp_code": grp_codes or ["01"] * n, "alim_grp_nom_fr": grp_noms or ["g"] * n})


def test_fusion_doublons_sans_conflit():
    ident = _ident(["1", "1", "2"], ["a", "a", "b"])
    valeurs = pd.DataFrame({"x": [1.0, np.nan, 3.0], "y": [np.nan, 2.0, 4.0]})
    fusion, rejets = fusionner_doublons(ident, valeurs)
    assert len(rejets) == 1
    garde = 1 - rejets[0]["index"]
    assert fusion.loc[garde].tolist() == [1.0, 2.0]


def test_fusion_doublons_conflit_rejette_tout():
    ident = _ident(["1", "1"], ["a", "a"])
    valeurs = pd.DataFrame({"x": [1.0, 5.0]})
    _, rejets = fusionner_doublons(ident, valeurs)
    assert {r["index"] for r in rejets} == {0, 1}


def test_categorie_reparee_depuis_code():
    ident = _ident(["1", "2", "3"], ["a", "b", "c"], ["03", "03", "00"], ["céréales", "", ""])
    assert categories_depuis_code(ident).tolist()[:2] == ["céréales", "céréales"]
    assert pd.isna(categories_depuis_code(ident).iloc[2])


def test_categorie_ambigue_refusee():
    ident = _ident(["1", "2"], ["a", "b"], ["03", "03"], ["céréales", "pains"])
    with pytest.raises(ValueError):
        categories_depuis_code(ident)
