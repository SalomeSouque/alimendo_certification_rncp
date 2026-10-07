#!/usr/bin/env python3
"""Import du jeu CIQUAL nettoyé dans PostgreSQL (tables `categorie` et `aliment`).

Entrée : le CSV produit par scripts/ciqual_clean.py.
Sortie : la base remplie, et un log avec les comptages avant / après.

Script idempotent :
  - catégorie déjà présente (même nom) -> conservée telle quelle ;
  - aliment déjà présent (même code_ciqual) -> valeurs mises à jour, pas de doublon.
Tout se fait dans une seule transaction : en cas d'erreur, rien n'est écrit.

Prérequis : la base tourne (docker compose up -d db) et les migrations sont
appliquées jusqu'à 0002 (colonne code_ciqual).

Usage :
    uv run --group data python scripts/import_aliments.py
    uv run --group data python scripts/import_aliments.py --csv chemin/vers/aliments.csv

Codes de sortie : 0 = succès, 1 = erreur (fichier absent ou incomplet,
base injoignable, migration manquante). Rien n'est écrit en cas d'erreur.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parent.parent          # racine du dépôt
logger = logging.getLogger("import_aliments")

CSV_PAR_DEFAUT = ROOT / "data" / "ciqual" / "clean" / "aliments_ciqual_2020_clean.csv"

# Colonnes attendues dans le CSV (= sortie de ciqual_clean.py)
PARAMETRES_NUTRITIONNELS: tuple[str, ...] = (
    "glucides", "proteines", "lipides", "graisses_saturees", "cholesterol", "fer", "vitamine_b12",
    "fibres", "omega3", "omega6", "vitamine_a", "beta_carotene", "vitamine_c", "vitamine_d",
    "vitamine_e", "vitamine_b6", "folates", "thiamine", "riboflavine", "niacine",
    "magnesium", "selenium", "zinc",
)
COLONNES_NUMERIQUES: tuple[str, ...] = ("energie", *PARAMETRES_NUTRITIONNELS)
COLONNES_ATTENDUES: tuple[str, ...] = ("code_ciqual", "nom", "categorie", "source", *COLONNES_NUMERIQUES)


# 1. Lecture et contrôle du fichier
def verifier_colonnes(entete: list[str]) -> list[str]:
    """Retourne la liste des colonnes attendues absentes du CSV (vide si tout va bien)."""
    return [c for c in COLONNES_ATTENDUES if c not in entete]


def lire_valeur(texte: str) -> float | None:
    """Cellule vide -> None (non mesuré, jamais 0) ; sinon nombre."""
    texte = texte.strip()
    return None if texte == "" else float(texte)


def lire_csv(chemin: Path) -> list[dict]:
    """Lit le CSV nettoyé et convertit chaque ligne au format de la table `aliment`.

    Raises:
        FileNotFoundError: le CSV n'existe pas.
        ValueError: colonne manquante ou valeur non numérique.
    """
    with open(chemin, newline="", encoding="utf-8") as f:
        lecteur = csv.DictReader(f)
        manquantes = verifier_colonnes(lecteur.fieldnames or [])
        if manquantes:
            raise ValueError(f"colonnes absentes du CSV : {', '.join(manquantes)}")
        lignes = []
        for numero, brute in enumerate(lecteur, start=2):     # ligne 1 = en-tête
            try:
                ligne = {
                    "code_ciqual": int(brute["code_ciqual"]),
                    "nom": brute["nom"].strip(),
                    "categorie": brute["categorie"].strip() or None,
                    "source": brute["source"].strip(),
                }
                ligne.update({c: lire_valeur(brute[c]) for c in COLONNES_NUMERIQUES})
            except ValueError as erreur:
                raise ValueError(f"ligne {numero} invalide : {erreur}") from erreur
            lignes.append(ligne)
    return lignes


# 2. Connexion à la base
def construire_url(host: str, port: int) -> URL:
    """URL de connexion depuis les variables du fichier .env (jamais de secret dans le code)."""
    for variable in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        if not os.getenv(variable):
            raise ValueError(f"variable {variable} absente du fichier .env")
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=host,
        port=port,
        database=os.environ["POSTGRES_DB"],
    )


def verifier_schema(engine: Engine) -> None:
    """Vérifie que la migration 0002 est appliquée (colonne code_ciqual présente).

    Raises:
        RuntimeError: table ou colonne absente.
    """
    inspecteur = inspect(engine)
    if not inspecteur.has_table("aliment"):
        raise RuntimeError("table aliment absente : lancer « alembic upgrade head »")
    colonnes = {c["name"] for c in inspecteur.get_columns("aliment")}
    if "code_ciqual" not in colonnes:
        raise RuntimeError("colonne code_ciqual absente : lancer « alembic upgrade head » (migration 0002)")


# 3. Import (une seule transaction)
def importer(engine: Engine, lignes: list[dict]) -> dict[str, int]:
    """Insère ou met à jour catégories puis aliments. Retourne les comptages."""
    metadata = MetaData()
    table_categorie = Table("categorie", metadata, autoload_with=engine)
    table_aliment = Table("aliment", metadata, autoload_with=engine)

    def compter(conn, table: Table) -> int:
        return conn.execute(select(func.count()).select_from(table)).scalar_one()

    with engine.begin() as conn:            # commit à la fin, rollback si exception
        avant = {"categories": compter(conn, table_categorie), "aliments": compter(conn, table_aliment)}

        # Catégories d'abord : la clé étrangère de aliment en dépend
        noms = sorted({l["categorie"] for l in lignes if l["categorie"]})
        if noms:
            conn.execute(insert(table_categorie).on_conflict_do_nothing(index_elements=["nom"]),
                         [{"nom": n} for n in noms])
        ids = dict(conn.execute(select(table_categorie.c.nom, table_categorie.c.id_categorie)).all())

        # Aliments : upsert sur code_ciqual (insertion, ou mise à jour si déjà présent)
        valeurs = [
            {"id_categorie": ids.get(l["categorie"]),
             **{k: v for k, v in l.items() if k != "categorie"}}
            for l in lignes
        ]
        requete = insert(table_aliment)
        a_mettre_a_jour = ["id_categorie", "nom", "source", *COLONNES_NUMERIQUES]
        requete = requete.on_conflict_do_update(
            index_elements=["code_ciqual"],
            set_={c: requete.excluded[c] for c in a_mettre_a_jour},
        )
        conn.execute(requete, valeurs)

        apres = {"categories": compter(conn, table_categorie), "aliments": compter(conn, table_aliment)}

    inseres = apres["aliments"] - avant["aliments"]
    return {
        "lignes_csv": len(lignes),
        "categories_avant": avant["categories"], "categories_apres": apres["categories"],
        "aliments_avant": avant["aliments"], "aliments_apres": apres["aliments"],
        "aliments_inseres": inseres, "aliments_mis_a_jour": len(lignes) - inseres,
    }


# Point de lancement
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import du jeu CIQUAL nettoyé dans PostgreSQL (Alimendo).")
    p.add_argument("--csv", type=Path, default=CSV_PAR_DEFAUT, help="CSV produit par ciqual_clean.py")
    p.add_argument("--host", default="localhost", help="Hôte PostgreSQL vu depuis ta machine")
    p.add_argument("--port", type=int, default=None, help="Port publié (défaut : POSTGRES_PORT du .env)")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    load_dotenv(ROOT / ".env")              # identifiants de la base

    try:
        lignes = lire_csv(args.csv)
        logger.info("CSV lu : %d aliments (%s)", len(lignes), args.csv)
        port = args.port or int(os.getenv("POSTGRES_PORT", "5432"))
        engine = create_engine(construire_url(args.host, port))
        verifier_schema(engine)
        comptes = importer(engine, lignes)
    except FileNotFoundError:
        logger.error("CSV introuvable : %s (lancer d'abord scripts/ciqual_clean.py)", args.csv)
        return 1
    except (ValueError, RuntimeError) as erreur:
        logger.error("Import annulé : %s", erreur)
        return 1
    except SQLAlchemyError as erreur:
        logger.error("Erreur base de données, rien n'a été écrit : %s", erreur)
        return 1

    for cle, valeur in comptes.items():
        logger.info("%-22s %d", cle, valeur)
    logger.info("Import terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
