#!/usr/bin/env python3
"""Exécution des requêtes SQL d'extraction du dossier sql/ (critère C2).

Le script lit les fichiers .sql, découpe chaque fichier en requêtes nommées
(une requête commence par une ligne « -- name: nom_de_la_requete »), les exécute
sur PostgreSQL et affiche le résultat dans la console.

Choix techniques :
  - SQLAlchemy, comme le reste du projet (import_aliments.py, backend). Les requêtes
    restent du SQL pur dans les fichiers .sql : text() les envoie telles quelles ;
  - paramètres nommés (:terme, :jours) : la valeur saisie est envoyée à part du
    texte SQL, jamais collée dedans, ce qui protège des injections SQL ;
  - connexion en lecture seule : un script d'extraction ne doit rien modifier.

Prérequis : la base tourne (docker compose up -d db), les migrations sont
appliquées et les aliments importés (scripts/import_aliments.py).
Pour les requêtes sur log_vlm en local : charger sql/demo_log_vlm.sql.

Usage (depuis la racine du dépôt) :
    uv run python scripts/run_extractions.py
    uv run python scripts/run_extractions.py --terme "brocolli" --categorie "lait"

Codes de sortie : 0 = toutes les requêtes ont réussi, 1 = erreur.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from import_aliments import construire_url  # même lecture du .env que l'import
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parent.parent          # racine du dépôt
logger = logging.getLogger("run_extractions")

# Fichiers exécutés, dans cet ordre
FICHIERS_SQL: tuple[Path, ...] = (
    ROOT / "sql" / "extract_aliments.sql",
    ROOT / "sql" / "extract_logs_vlm.sql",
)

MARQUEUR = "-- name:"

# Réglages appliqués à chaque connexion :
#   - lecture seule : toute écriture (INSERT, UPDATE, DELETE) est refusée par PostgreSQL ;
#   - seuil de l'opérateur trigramme % : 0.2, le même que le backend (aliment_repository).
OPTIONS_CONNEXION = "-c default_transaction_read_only=on -c pg_trgm.similarity_threshold=0.2"


# 1. Lecture des fichiers .sql
def lire_requetes(chemin: Path) -> dict[str, str]:
    """Découpe un fichier .sql en requêtes nommées.

    Tout ce qui précède le premier marqueur « -- name: » (l'en-tête du fichier)
    est ignoré. Chaque requête va de son marqueur jusqu'au marqueur suivant.

    Returns:
        Un dictionnaire {nom de la requête: texte SQL}, dans l'ordre du fichier.

    Raises:
        FileNotFoundError: le fichier n'existe pas.
        ValueError: marqueur sans nom, nom en double, ou requête vide.
    """
    requetes: dict[str, str] = {}
    nom_courant: str | None = None
    lignes_courantes: list[str] = []

    def ranger() -> None:
        """Enregistre la requête en cours de lecture."""
        if nom_courant is None:
            return
        texte = "\n".join(lignes_courantes).strip()
        if not texte:
            raise ValueError(f"{chemin.name} : la requête {nom_courant!r} est vide")
        requetes[nom_courant] = texte

    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith(MARQUEUR):
            ranger()
            nom_courant = ligne[len(MARQUEUR):].strip()
            if not nom_courant:
                raise ValueError(f"{chemin.name} : marqueur « {MARQUEUR} » sans nom")
            if nom_courant in requetes:
                raise ValueError(f"{chemin.name} : requête {nom_courant!r} en double")
            lignes_courantes = []
        elif nom_courant is not None:
            lignes_courantes.append(ligne)
    ranger()
    return requetes


# 2. Paramètres de chaque requête
def parametres_pour(nom: str, args: argparse.Namespace) -> dict:
    """Retourne les valeurs des paramètres nommés (:terme...) attendus par la requête `nom`.

    Raises:
        ValueError: requête inconnue (un .sql a été modifié sans mettre à jour ce script).
    """
    parametres = {
        "recherche_par_nom": {"terme": args.terme},
        "aliments_par_categorie": {"categorie": args.categorie},
        "couverture_par_categorie": {},
        "bilan_vlm_par_jour": {"jours": args.jours},
        "labels_non_rapproches": {"jours": args.jours},
    }
    if nom not in parametres:
        raise ValueError(f"requête {nom!r} sans paramètres déclarés dans parametres_pour()")
    return parametres[nom]


# 3. Affichage
def formater_tableau(colonnes: list[str], lignes: list[tuple], maximum: int) -> str:
    """Met en forme les premières lignes d'un résultat en tableau texte aligné."""
    affichees = [["" if v is None else str(v) for v in ligne] for ligne in lignes[:maximum]]
    largeurs = [max([len(c)] + [len(l[i]) for l in affichees]) for i, c in enumerate(colonnes)]
    sortie = [
        " | ".join(c.ljust(w) for c, w in zip(colonnes, largeurs)),
        "-+-".join("-" * w for w in largeurs),
    ]
    sortie += [" | ".join(v.ljust(w) for v, w in zip(l, largeurs)) for l in affichees]
    if len(lignes) > maximum:
        sortie.append(f"... {len(lignes) - maximum} ligne(s) non affichée(s)")
    return "\n".join(sortie)


# 4. Exécution
def executer(conn: Connection, sql: str, parametres: dict) -> tuple[list[str], list[tuple]]:
    """Exécute une requête et retourne (noms des colonnes, lignes)."""
    resultat = conn.execute(text(sql), parametres)
    return list(resultat.keys()), [tuple(ligne) for ligne in resultat]


# Point de lancement
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exécute les requêtes SQL d'extraction d'Alimendo.")
    p.add_argument("--terme", default="saumon", help="Texte recherché (requête recherche_par_nom)")
    p.add_argument("--categorie", default="poissons", help="Mot du nom de catégorie (aliments_par_categorie)")
    p.add_argument("--jours", type=int, default=30, help="Période en jours (requêtes sur log_vlm)")
    p.add_argument("--lignes", type=int, default=10, help="Nombre de lignes affichées par requête")
    p.add_argument("--host", default="localhost", help="Hôte PostgreSQL vu depuis ta machine")
    p.add_argument("--port", type=int, default=None, help="Port publié (défaut : POSTGRES_PORT du .env)")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    load_dotenv(ROOT / ".env")              # identifiants de la base

    try:
        port = args.port or int(os.getenv("POSTGRES_PORT", "5432"))
        engine = create_engine(construire_url(args.host, port),
                               connect_args={"options": OPTIONS_CONNEXION})
        with engine.connect() as conn:
            for fichier in FICHIERS_SQL:
                for nom, sql in lire_requetes(fichier).items():
                    colonnes, lignes = executer(conn, sql, parametres_pour(nom, args))
                    print(f"\n== {fichier.name} :: {nom} : {len(lignes)} ligne(s)")
                    print(formater_tableau(colonnes, lignes, args.lignes))
    except (FileNotFoundError, ValueError) as erreur:
        logger.error("Extraction annulée : %s", erreur)
        return 1
    except SQLAlchemyError as erreur:
        logger.error("Erreur base de données : %s", erreur)
        return 1

    logger.info("Toutes les requêtes ont été exécutées.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
