#!/usr/bin/env python3
"""Nettoyage reproductible de la table CIQUAL 2020 (ANSES) pour Alimendo.

Transforme le fichier brut CIQUAL en un jeu d'aliments prêt pour l'import
PostgreSQL (table `aliment`, voir backend/app/db/models/aliment.py).
Toutes les règles ci-dessous ont été établies et mesurées dans le notebook
`03_nettoyage_ciqual.ipynb` (dépôt alimendo_data_science), qui sert de
justification à chaque choix.

Étapes :
  1. Téléchargement (si absent) puis chargement BRUT : toutes les cellules en texte.
  2. Identification des formats non normalisés (virgule, « - », vide, traces, « < X »).
  3. Conversion selon le référentiel de score v1.0 (§4 étape 1) :
       vide / « - » -> NULL (non mesuré, jamais 0) ; traces / « < X » -> 0 ;
       virgule décimale -> point.
  4. Dictionnaire de données : 1 mot-clé = 1 colonne, unités contrôlées.
  5. Doublons d'alim_code : fusion si aucune valeur ne se contredit, rejet sinon.
  6. Catégorie = groupe CIQUAL, réparé depuis le code quand le nom est vide.
  7. Entrées corrompues : 5 règles de cohérence physique -> rejet motivé.
  8. Contrôles : schéma PostgreSQL, non-régression des repères v1.0 (optionnel).
  9. Export : aliments, catégories, rejets, rapport JSON, log.

Usage :
    uv run --group data python scripts/ciqual_clean.py
    uv run --group data python scripts/ciqual_clean.py --landmarks backend/app/domain/score/landmarks_v1.json
    uv run --group data python scripts/ciqual_clean.py --force-download

Codes de sortie : 0 = succès, 1 = erreur (source illisible, unité inattendue,
format inconnu…). Le script préfère s'arrêter plutôt que produire un jeu faux.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent          # racine du dépôt
logger = logging.getLogger("ciqual_clean")

# Configuration 
CIQUAL_VERSION = "2020"   # référentiel de score v1.0 calibré sur cette version
CIQUAL_URL = "https://www.data.gouv.fr/api/1/datasets/r/bcdb7fec-875c-42aa-ba6e-460adf97aad3"
CITATION = "Anses. 2020. Table de composition nutritionnelle des aliments Ciqual."
USER_AGENT = "Alimendo-datacollect/1.0 (projet etudiant)"
TIMEOUT = 60
SOURCE = "CIQUAL"                                     # valeur de aliment.source

# Seuils des règles d'entrée corrompue (justifiés au § 4 du notebook 03)
TOLERANCE_SOUS_ENSEMBLE_G = 1.0     # arrondis observés : max 0,6 g
SEUIL_COMPOSITION_G = 105.0         # plafond observé ≈ 103,1 g
SEUIL_ECART_ENERGIE_PCT = 20.0      # les deux seuils ensemble : le % seul
SEUIL_ECART_ENERGIE_KCAL = 20.0     # pénalise les aliments peu énergétiques

# Schéma PostgreSQL visé : NUMERIC(précision, échelle) - à aligner sur les migrations Alembic
SCHEMA_NUTRIMENTS = (10, 4)         # aligné sur la migration Alembic 0002
SCHEMA_ENERGIE = (8, 2)

# Nom logique (= colonne BDD) : (mots-clés de la colonne CIQUAL, unité attendue)
PARAMETRES: dict[str, tuple[list[str], str]] = {
    "energie":           (["règlement ue", "kcal"], "kcal"),
    "glucides":          (["glucides (g"], "g"),
    "proteines":         (["protéines, n x 6.25"], "g"),
    "lipides":           (["lipides (g"], "g"),
    "graisses_saturees": (["ag saturés"], "g"),
    "fibres":            (["fibres alimentaires"], "g"),
    "cholesterol":       (["cholestérol"], "mg"),
    "fer":               (["fer (mg"], "mg"),
    "magnesium":         (["magnésium"], "mg"),
    "selenium":          (["sélénium"], "µg"),
    "zinc":              (["zinc"], "mg"),
    "vitamine_a":        (["rétinol"], "µg"),
    "beta_carotene":     (["carotène"], "µg"),
    "vitamine_d":        (["vitamine d"], "µg"),
    "vitamine_e":        (["vitamine e"], "mg"),
    "vitamine_c":        (["vitamine c"], "mg"),
    "thiamine":          (["thiamine"], "mg"),
    "riboflavine":       (["riboflavine"], "mg"),
    "niacine":           (["niacine"], "mg"),
    "vitamine_b6":       (["vitamine b6"], "mg"),
    "folates":           (["folates"], "µg"),
    "vitamine_b12":      (["vitamine b12"], "µg"),
}
# Oméga = sommes d'acides gras, toutes en g (référentiel §3.3)
COMPOSANTES_OMEGA: dict[str, list[str]] = {
    "omega3": ["alpha-linolénique", "epa", "dha"],
    "omega6": ["linoléique", "arachidonique"],
}
# Ordre des colonnes = PARAMETRES_NUTRITIONNELS de backend/app/db/models/aliment.py
PARAMETRES_NUTRITIONNELS: tuple[str, ...] = (
    "glucides", "proteines", "lipides", "graisses_saturees", "cholesterol", "fer", "vitamine_b12",
    "fibres", "omega3", "omega6", "vitamine_a", "beta_carotene", "vitamine_c", "vitamine_d",
    "vitamine_e", "vitamine_b6", "folates", "thiamine", "riboflavine", "niacine",
    "magnesium", "selenium", "zinc",
)
COLONNES_SORTIE = ["code_ciqual", "nom", "categorie", "source", "energie", *PARAMETRES_NUTRITIONNELS]
FACTEUR_EN_G = {"g": 1.0, "mg": 1e-3, "µg": 1e-6}


# 1. Téléchargement et chargement brut
def telecharger(url: str, dest: Path, force: bool = False) -> Path:
    """Télécharge le fichier CIQUAL s'il n'est pas déjà présent (idempotent)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        logger.info("Source déjà présente : %s (%.1f Mo)", dest, dest.stat().st_size / 1e6)
        return dest
    logger.info("Téléchargement CIQUAL depuis data.gouv.fr…")
    with requests.get(url, stream=True, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.writelines(r.iter_content(chunk_size=8192))
    logger.info("Enregistré : %s (%.1f Mo)", dest, dest.stat().st_size / 1e6)
    return dest


def charger_brut(path: Path) -> tuple[pd.DataFrame, str]:
    """Charge CIQUAL sans aucune interprétation : toutes les cellules restent du texte.

    Returns:
        (DataFrame 100 % texte, format de fichier détecté).

    Raises:
        ValueError: format de fichier non reconnu.
    """
    entete = path.read_bytes()[:8]
    options = {"dtype": str, "keep_default_na": False, "na_values": []}
    if entete.startswith(b"PK\x03\x04"):
        return pd.read_excel(path, engine="openpyxl", **options), "xlsx"
    if entete.startswith(b"\xD0\xCF\x11\xE0"):
        return pd.read_excel(path, engine="xlrd", **options), "xls (OLE2)"
    if entete.lstrip()[:1] == b"<":
        # thousands=None : sinon '12,5' serait lu comme 125
        return pd.read_html(path, thousands=None, keep_default_na=False)[0].astype(str), "html déguisé en .xls"
    raise ValueError(f"Format CIQUAL non reconnu (premiers octets : {entete!r})")


# 2-3. Formats et conversion
def classer_format(valeur: object) -> str:
    """Retourne le format d'une valeur brute CIQUAL (aucune conversion)."""
    v = "" if pd.isna(valeur) else str(valeur).replace("\xa0", " ").strip()
    if v == "":
        return "vide"
    if v == "-":
        return "tiret"
    if v.lower() == "traces":
        return "traces"
    if v.startswith("<"):
        return "inférieur à (< X)"
    if re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", v):
        return "nombre (point)"
    if re.fullmatch(r"-?\d+,\d+", v):
        return "nombre (virgule)"
    return "autre texte"


def convertir_valeur(valeur: object) -> float:
    """Convertit une valeur brute CIQUAL en float (référentiel v1.0, §4 étape 1).

    vide / '-'         -> NaN  (non mesuré : JAMAIS 0)
    'traces' / '< X'   -> 0.0  (convention POC = « lower bound » EFSA)
    '12,5' / '12.5'    -> 12.5
    autre texte        -> NaN  (erreur de source, comptée dans le rapport)
    """
    fmt = classer_format(valeur)
    if fmt in ("vide", "tiret", "autre texte"):
        return np.nan
    if fmt in ("traces", "inférieur à (< X)"):
        return 0.0
    return float(str(valeur).replace("\xa0", "").strip().replace(",", "."))


# 4. Dictionnaire de données
def trouver_colonne_unique(colonnes: list[str], mots: list[str]) -> str:
    """Retourne LA colonne contenant tous les mots-clés ; KeyError si 0 ou plusieurs."""
    candidates = [c for c in colonnes if all(m.lower() in c.lower() for m in mots)]
    if len(candidates) != 1:
        raise KeyError(f"{mots} -> {len(candidates)} colonne(s) : {candidates}")
    return candidates[0]


def unite_colonne(nom_colonne: str) -> str:
    """Extrait l'unité de l'en-tête CIQUAL, ex. 'Fer (mg/100 g)' -> 'mg'."""
    m = re.search(r"\(([^()/]+)/100\s?g\)", nom_colonne)
    return m.group(1).strip() if m else "?"


def construire_dictionnaire(colonnes: list[str]) -> pd.DataFrame:
    """Associe chaque nom logique à sa colonne CIQUAL et contrôle l'unité.

    Raises:
        KeyError: mot-clé ambigu ou introuvable.
        ValueError: unité différente de celle du référentiel.
    """
    lignes = []
    for nom, (mots, unite) in PARAMETRES.items():
        col = trouver_colonne_unique(colonnes, mots)
        lignes.append({"nom_logique": nom, "colonne_ciqual": col, "unite_ciqual": unite_colonne(col),
                       "unite_attendue": unite})
    for omega, mots_composantes in COMPOSANTES_OMEGA.items():
        for mot in mots_composantes:
            col = trouver_colonne_unique(colonnes, [mot])
            lignes.append({"nom_logique": f"{omega} ← {mot}", "colonne_ciqual": col,
                           "unite_ciqual": unite_colonne(col), "unite_attendue": "g"})
    dictionnaire = pd.DataFrame(lignes)
    mauvaises = dictionnaire[dictionnaire["unite_ciqual"] != dictionnaire["unite_attendue"]]
    if not mauvaises.empty:
        raise ValueError(f"Unités inattendues :\n{mauvaises.to_string(index=False)}")
    return dictionnaire


def table_parametres(valeurs: pd.DataFrame, dictionnaire: pd.DataFrame) -> pd.DataFrame:
    """Énergie + 23 paramètres du score, en noms logiques (oméga = sommes, NULL si rien mesuré)."""
    col = dict(zip(dictionnaire["nom_logique"], dictionnaire["colonne_ciqual"]))
    t = pd.DataFrame(index=valeurs.index)
    t["energie"] = valeurs[col["energie"]]
    for p in PARAMETRES_NUTRITIONNELS:
        if p in col:
            t[p] = valeurs[col[p]]
    for omega in COMPOSANTES_OMEGA:
        cols = dictionnaire.loc[dictionnaire["nom_logique"].str.startswith(f"{omega} ←"), "colonne_ciqual"]
        t[omega] = valeurs[cols.tolist()].sum(axis=1, min_count=1)
    return t[["energie", *PARAMETRES_NUTRITIONNELS]]


# 5. Doublons 
def fusionner_doublons(ident: pd.DataFrame, valeurs: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Fusionne les lignes d'un même alim_code si aucune valeur ne se contredit.

    La ligne la plus complète est conservée et complétée par les autres.
    En cas de contradiction, toutes les lignes du code sont rejetées.

    Returns:
        (valeurs avec les lignes fusionnées, liste des rejets motivés).
    """
    valeurs = valeurs.copy()
    rejets: list[dict] = []
    for code, groupe in ident.groupby("alim_code"):
        if len(groupe) == 1:
            continue
        bloc = valeurs.loc[groupe.index]
        if (bloc.nunique() > 1).any():
            logger.warning("alim_code %s : %d lignes contradictoires -> rejetées", code, len(groupe))
            rejets += [{"index": i, "alim_code": code, "alim_nom_fr": ident.loc[i, "alim_nom_fr"],
                        "motif": "doublon de alim_code avec valeurs contradictoires"} for i in groupe.index]
            continue
        garde = bloc.notna().sum(axis=1).idxmax()
        fusion = bloc.loc[garde]
        for i in groupe.index.drop(garde):
            fusion = fusion.combine_first(bloc.loc[i])
            rejets.append({"index": i, "alim_code": code, "alim_nom_fr": ident.loc[i, "alim_nom_fr"],
                           "motif": f"doublon de alim_code, valeurs fusionnées dans la ligne {garde}"})
        valeurs.loc[garde] = fusion
        logger.info("alim_code %s : %d lignes fusionnées (0 contradiction)", code, len(groupe))
    return valeurs, rejets


# 6. Table aliments
def categories_depuis_code(ident: pd.DataFrame) -> pd.Series:
    """Catégorie = nom du groupe CIQUAL, réparé depuis le code quand il est vide.

    Raises:
        ValueError: un code de groupe correspond à plusieurs noms (réparation impossible).
    """
    nommes = ident[~ident["alim_grp_nom_fr"].isin(["", "-"])]
    noms_par_code = nommes.groupby("alim_grp_code")["alim_grp_nom_fr"].nunique()
    if (noms_par_code > 1).any():
        raise ValueError(f"Codes groupe à plusieurs noms : {noms_par_code[noms_par_code > 1].to_dict()}")
    correspondance = nommes.groupby("alim_grp_code")["alim_grp_nom_fr"].first()
    return ident["alim_grp_code"].map(correspondance)   # code sans nom (00) -> NaN -> catégorie NULL


# 7. Entrées corrompues
def detecter_corrompues(valeurs: pd.DataFrame, colonnes: list[str],
                        aliments: pd.DataFrame) -> pd.DataFrame:
    """Applique les 5 règles de cohérence physique. Une valeur NULL ne déclenche jamais une règle.

    Returns:
        DataFrame booléen (aliments × règles).
    """
    def col(*mots: str) -> pd.Series:
        return valeurs[trouver_colonne_unique(colonnes, list(mots))]

    cols_masse = [c for c in colonnes if unite_colonne(c) in FACTEUR_EN_G]
    en_grammes = valeurs[cols_masse].mul([FACTEUR_EN_G[unite_colonne(c)] for c in cols_masse], axis=1)

    lipides, satures = col("lipides (g"), col("ag saturés")
    ag_total = satures + col("ag monoinsaturés") + col("ag polyinsaturés")
    glucides, sucres = col("glucides (g"), col("sucres (g")
    fibres, proteines_625 = col("fibres alimentaires"), col("protéines, n x 6.25")
    polyols = col("polyols").fillna(0)    # inclus dans « glucides » (Règlement UE 1169/2011)
    omegas = aliments["omega3"].fillna(0) + aliments["omega6"].fillna(0)

    composition = (pd.concat([col("eau (g"), col("protéines, n x facteur de jones"), glucides, lipides, fibres,
                              col("alcool"), col("cendres"), col("acides organiques"), col("polyols")], axis=1)
                   .sum(axis=1, min_count=1) - polyols)

    # Énergie UE 1169/2011, annexe XIV (polyols retirés des glucides pour éviter le double compte)
    energie_calculee = (4 * proteines_625 + 4 * (glucides - polyols) + 9 * lipides + 2 * fibres
                        + 7 * col("alcool").fillna(0) + 3 * col("acides organiques").fillna(0) + 2.4 * polyols)
    energie_declaree = aliments["energie"]
    comparables = (pd.concat([proteines_625, glucides, lipides, fibres], axis=1).notna().all(axis=1)
                   & energie_declaree.gt(0))
    ecart_kcal = (energie_declaree - energie_calculee).where(comparables)
    ecart_pct = ecart_kcal / energie_declaree * 100

    sous_ensemble = pd.concat([satures - lipides, ag_total - lipides, sucres - glucides, omegas - lipides],
                              axis=1).gt(TOLERANCE_SOUS_ENSEMBLE_G).any(axis=1)
    return pd.DataFrame({
        "valeur négative": (valeurs < 0).any(axis=1),
        "teneur > 100 g/100 g": (en_grammes > 100).any(axis=1),
        f"sous-ensemble > ensemble + {TOLERANCE_SOUS_ENSEMBLE_G:g} g": sous_ensemble,
        f"somme de composition > {SEUIL_COMPOSITION_G:g} g": composition > SEUIL_COMPOSITION_G,
        f"énergie incohérente (> {SEUIL_ECART_ENERGIE_PCT:g} % et > {SEUIL_ECART_ENERGIE_KCAL:g} kcal)":
            (ecart_pct.abs() > SEUIL_ECART_ENERGIE_PCT) & (ecart_kcal.abs() > SEUIL_ECART_ENERGIE_KCAL),
    })


# 8. Contrôles
def controler_schema(aliments: pd.DataFrame) -> dict[str, list[str]]:
    """Compare les valeurs au schéma PostgreSQL visé (débordement, arrondi)."""
    resultat: dict[str, list[str]] = {"deborde": [], "arrondi": []}
    for c in ["energie", *PARAMETRES_NUTRITIONNELS]:
        precision, echelle = SCHEMA_ENERGIE if c == "energie" else SCHEMA_NUTRIMENTS
        x = aliments[c].dropna()
        if (x > 10 ** (precision - echelle) - 10 ** (-echelle)).any():
            resultat["deborde"].append(c)
        if ((x - x.round(echelle)).abs() > 1e-9).any():
            resultat["arrondi"].append(c)
    for c in resultat["deborde"]:
        logger.warning("Schéma : « %s » dépasse NUMERIC%s -> l'import échouera (migration nécessaire)",
                       c, SCHEMA_ENERGIE if c == "energie" else SCHEMA_NUTRIMENTS)
    return resultat


def calculer_reperes(t: pd.DataFrame) -> pd.DataFrame:
    """Médiane, p10, p90 par paramètre, hors aliments sans apport (règle du notebook 01)."""
    apport = t[["glucides", "proteines", "lipides"]].sum(axis=1, min_count=1).fillna(0)
    base = t.loc[apport >= 1.0, list(PARAMETRES_NUTRITIONNELS)]
    return pd.DataFrame({"mediane": base.median(), "p10": base.quantile(0.10), "p90": base.quantile(0.90)})


def verifier_reperes(t_brut: pd.DataFrame, chemin: Path) -> bool:
    """Non-régression : la conversion reproduit-elle les repères figés v1.0 ?"""
    figes = json.loads(chemin.read_text(encoding="utf-8"))["landmarks"]
    reference = pd.DataFrame(figes).T[["mediane", "p10", "p90"]].astype(float)
    ecart = (calculer_reperes(t_brut) - reference).abs().max().max()
    if ecart < 1e-9:
        logger.info("Non-régression : repères v1.0 reproduits à l'identique")
        return True
    logger.warning("Non-régression : écart de %.3g avec %s -> conversion différente de la calibration",
                   ecart, chemin)
    return False


# Orchestration 
def sha256_of(path: Path) -> str:
    """Empreinte SHA-256 : prouve quel fichier source a été nettoyé."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(raw_file: Path, out_dir: Path, force_download: bool, landmarks: Path | None) -> int:
    """Exécute le nettoyage complet. Retourne le code de sortie."""
    out_dir.mkdir(parents=True, exist_ok=True)
    telecharger(CIQUAL_URL, raw_file, force_download)
    brut, format_source = charger_brut(raw_file)
    if brut.empty:
        raise ValueError("Fichier CIQUAL vide")
    logger.info("Chargé : %d lignes × %d colonnes (%s)", *brut.shape, format_source)

    cols_ident = ["alim_code", "alim_nom_fr", "alim_grp_code", "alim_grp_nom_fr"]
    ident = brut[cols_ident].fillna("").apply(lambda s: s.str.strip())
    if (ident["alim_code"] == "").any() or (ident["alim_nom_fr"] == "").any():
        raise ValueError("Lignes sans alim_code ou sans nom : source à vérifier")
    colonnes = [c for c in brut.columns if not c.startswith("alim_")]

    # 2-3. Formats puis conversion
    formats = brut[colonnes].apply(lambda s: s.map(classer_format))
    compte_formats = formats.stack().value_counts().astype(int).to_dict()
    logger.info("Formats bruts : %s", compte_formats)
    if compte_formats.get("autre texte", 0):
        logger.warning("%d cellules au texte inattendu -> NULL", compte_formats["autre texte"])
    valeurs = brut[colonnes].apply(lambda s: s.map(convertir_valeur)).astype(float)

    # 4. Dictionnaire + non-régression (sur toutes les lignes, comme la calibration)
    dictionnaire = construire_dictionnaire(colonnes)
    reperes_ok = verifier_reperes(table_parametres(valeurs, dictionnaire), landmarks) if landmarks else None

    # 5. Doublons
    valeurs, rejets = fusionner_doublons(ident, valeurs)
    a_retirer = [r["index"] for r in rejets]
    valeurs, ident = valeurs.drop(index=a_retirer), ident.drop(index=a_retirer)
    n_apres_doublons = len(valeurs)

    # 6. Table aliments
    categorie = categories_depuis_code(ident)
    aliments = table_parametres(valeurs, dictionnaire)
    aliments.insert(0, "code_ciqual", ident["alim_code"].astype(int))
    aliments.insert(1, "nom", ident["alim_nom_fr"].str.replace(r"\s+", " ", regex=True))
    aliments.insert(2, "categorie", categorie)
    aliments.insert(3, "source", SOURCE)
    aliments = aliments[COLONNES_SORTIE]

    # 7. Entrées corrompues
    regles = detecter_corrompues(valeurs, colonnes, aliments)
    est_corrompu = regles.any(axis=1)
    for i in aliments.index[est_corrompu]:
        motif = " ; ".join(regles.columns[regles.loc[i]])
        rejets.append({"index": i, "alim_code": str(aliments.loc[i, "code_ciqual"]),
                       "alim_nom_fr": aliments.loc[i, "nom"], "motif": f"entrée corrompue : {motif}"})
        logger.info("Entrée corrompue rejetée : %s (%s)", aliments.loc[i, "nom"], motif)
    aliments = aliments.loc[~est_corrompu]

    # 8. Contrôle de schéma
    schema = controler_schema(aliments)

    # 9. Export
    sorties = {
        "aliments": out_dir / f"aliments_ciqual_{CIQUAL_VERSION}_clean.csv",
        "categories": out_dir / f"categories_ciqual_{CIQUAL_VERSION}.csv",
        "rejets": out_dir / f"rejets_ciqual_{CIQUAL_VERSION}.csv",
    }
    aliments.to_csv(sorties["aliments"], index=False, encoding="utf-8")
    pd.DataFrame({"nom": sorted(aliments["categorie"].dropna().unique())}).to_csv(
        sorties["categories"], index=False, encoding="utf-8")
    pd.DataFrame(rejets).drop(columns="index").to_csv(sorties["rejets"], index=False, encoding="utf-8")

    rapport = {
        "date_execution": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"fichier": str(raw_file), "version": CIQUAL_VERSION, "citation": CITATION,
                   "sha256": sha256_of(raw_file), "format_detecte": format_source},
        "environnement": {"python": sys.version.split()[0], "pandas": pd.__version__},
        "lignes": {"fichier brut": len(brut), "après fusion des doublons": n_apres_doublons,
                   "après suppression des entrées corrompues": len(aliments)},
        "formats_bruts": compte_formats,
        "corrections": {"groupes_repares_depuis_code": int(((ident["alim_grp_nom_fr"] == "")
                                                              & categorie.notna()).sum()),
                        "aliments_sans_categorie": int(aliments["categorie"].isna().sum())},
        "regles_corruption": regles.sum().astype(int).to_dict(),
        "controles": {"schema": schema, "reperes_v1_reproduits": reperes_ok},
        "sorties": {k: str(v) for k, v in sorties.items()},
    }
    chemin_rapport = out_dir / f"rapport_nettoyage_ciqual_{CIQUAL_VERSION}.json"
    chemin_rapport.write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Terminé : %d -> %d -> %d lignes. Sorties dans %s",
                len(brut), n_apres_doublons, len(aliments), out_dir)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Nettoyage reproductible de la table CIQUAL (Alimendo).")
    p.add_argument("--raw", type=Path, default=ROOT / "data" / "ciqual" / "raw" / f"ciqual_{CIQUAL_VERSION}.xls",
                   help="Fichier CIQUAL brut (téléchargé s'il est absent).")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "ciqual" / "clean",
                   help="Dossier des sorties.")
    p.add_argument("--force-download", action="store_true", help="Re-télécharge même si présent.")
    p.add_argument("--landmarks", type=Path, default=None,
                   help="landmarks_v1.json : active le test de non-régression des repères.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(args.out / "ciqual_clean.log", mode="w", encoding="utf-8")],
    )
    try:
        return run(args.raw, args.out, args.force_download, args.landmarks)
    except requests.RequestException as e:
        logger.error("Téléchargement impossible : %s", e)
    except (ValueError, KeyError, FileNotFoundError) as e:
        logger.error("Nettoyage interrompu : %s", e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
