"""Tests du script d'extraction SQL, sans base de données.

On vérifie ce qui peut casser sans PostgreSQL : le découpage des fichiers .sql
en requêtes nommées, la correspondance entre les requêtes et leurs paramètres,
et la mise en forme de l'affichage.
L'exécution réelle des requêtes est vérifiée à la main (docs/requetes.md, § 5) :
la CI n'a pas de service PostgreSQL.

Usage :
    uv run --group dev pytest scripts/tests -q
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_extractions import (
    FICHIERS_SQL,
    formater_tableau,
    lire_requetes,
    parametres_pour,
)

ARGS_DEMO = argparse.Namespace(terme="saumon", categorie="poissons", jours=30)


def ecrire_sql(dossier: Path, contenu: str) -> Path:
    chemin = dossier / "test.sql"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_decoupe_les_requetes_nommees_et_ignore_l_entete(tmp_path):
    chemin = ecrire_sql(tmp_path, (
        "-- En-tête du fichier, ignoré\n\n"
        "-- name: premiere\nSELECT 1;\n\n"
        "-- name: seconde\n-- un commentaire garde sa place\nSELECT 2;\n"
    ))
    requetes = lire_requetes(chemin)
    assert list(requetes) == ["premiere", "seconde"]
    assert requetes["premiere"] == "SELECT 1;"
    assert requetes["seconde"].endswith("SELECT 2;")


def test_refuse_un_nom_en_double(tmp_path):
    chemin = ecrire_sql(tmp_path, "-- name: a\nSELECT 1;\n-- name: a\nSELECT 2;\n")
    with pytest.raises(ValueError, match="en double"):
        lire_requetes(chemin)


def test_refuse_une_requete_vide(tmp_path):
    chemin = ecrire_sql(tmp_path, "-- name: vide\n\n-- name: pleine\nSELECT 1;\n")
    with pytest.raises(ValueError, match="vide"):
        lire_requetes(chemin)


def test_requete_inconnue_signalee():
    with pytest.raises(ValueError, match="sans paramètres"):
        parametres_pour("requete_inventee", ARGS_DEMO)


@pytest.mark.parametrize("fichier", FICHIERS_SQL, ids=lambda f: f.name)
def test_chaque_requete_du_depot_a_les_bons_parametres(fichier):
    """Garde-fou : si on ajoute :x dans un .sql sans toucher au script, ce test échoue."""
    for nom, sql in lire_requetes(fichier).items():
        # On ignore les commentaires, puis on cherche les « :nom ».
        # (?<![:\w]) écarte les conversions de type comme « ::numeric ».
        code = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
        attendus = set(re.findall(r"(?<![:\w]):([a-z_]\w*)", code))
        assert set(parametres_pour(nom, ARGS_DEMO)) == attendus, nom


def test_tableau_aligne_et_tronque():
    texte = formater_tableau(["id", "nom"], [(1, "Saumon"), (2, None), (3, "Riz")], maximum=2)
    lignes = texte.splitlines()
    assert lignes[0] == "id | nom   "
    assert lignes[3] == "2  |       "                # None affiché vide, pas « None »
    assert lignes[-1] == "... 1 ligne(s) non affichée(s)"
