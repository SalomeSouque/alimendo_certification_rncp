"""Tests de la lecture du CSV par le script d'import (sans base de données).

L'insertion en base est vérifiée à la main (voir README racine, « Import des données ») :
la CI n'a pas de service PostgreSQL.

Usage :
    uv run --group data --group dev pytest scripts/tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from import_aliments import (
    COLONNES_ATTENDUES,
    COLONNES_NUMERIQUES,
    construire_url,
    lire_csv,
    lire_valeur,
    verifier_colonnes,
)


def ecrire_csv(chemin: Path, lignes: list[dict]) -> Path:
    """Écrit un petit CSV au format de ciqual_clean.py (valeurs manquantes = cellule vide)."""
    entete = ",".join(COLONNES_ATTENDUES)
    corps = [",".join(str(l.get(c, "")) for c in COLONNES_ATTENDUES) for l in lignes]
    chemin.write_text("\n".join([entete, *corps]) + "\n", encoding="utf-8")
    return chemin


def test_verifier_colonnes():
    assert verifier_colonnes(list(COLONNES_ATTENDUES)) == []
    assert verifier_colonnes(["nom", "source"]) == [c for c in COLONNES_ATTENDUES
                                                     if c not in ("nom", "source")]


@pytest.mark.parametrize("texte, attendu", [("", None), ("  ", None), ("0", 0.0), ("12.5", 12.5)])
def test_lire_valeur_vide_reste_none(texte, attendu):
    assert lire_valeur(texte) == attendu


def test_lire_csv(tmp_path):
    chemin = ecrire_csv(tmp_path / "a.csv", [
        {"code_ciqual": 13000, "nom": "Pomme", "categorie": "fruits", "source": "CIQUAL",
         "glucides": 11.6, "fibres": 0},
        {"code_ciqual": 1, "nom": "Dessert (aliment moyen)", "categorie": "", "source": "CIQUAL"},
    ])
    lignes = lire_csv(chemin)
    assert len(lignes) == 2
    pomme, dessert = lignes
    assert pomme["code_ciqual"] == 13000 and pomme["glucides"] == 11.6
    assert pomme["fibres"] == 0.0            # un vrai zéro reste zéro
    assert pomme["zinc"] is None              # une cellule vide reste NULL
    assert dessert["categorie"] is None       # aliment sans catégorie accepté
    assert set(COLONNES_NUMERIQUES) <= set(pomme)


def test_lire_csv_valeur_invalide_indique_la_ligne(tmp_path):
    chemin = ecrire_csv(tmp_path / "a.csv", [
        {"code_ciqual": 1, "nom": "A", "categorie": "x", "source": "CIQUAL", "fer": "abc"},
    ])
    with pytest.raises(ValueError, match="ligne 2"):
        lire_csv(chemin)


def test_lire_csv_colonne_manquante(tmp_path):
    chemin = tmp_path / "a.csv"
    chemin.write_text("code_ciqual,nom\n1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colonnes absentes"):
        lire_csv(chemin)


def test_construire_url(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.setenv("POSTGRES_DB", "d")
    url = construire_url("localhost", 5433)
    assert (url.host, url.port, url.database) == ("localhost", 5433, "d")


def test_construire_url_variable_absente(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_DB", "d")
    with pytest.raises(ValueError, match="POSTGRES_PASSWORD"):
        construire_url("localhost", 5433)
