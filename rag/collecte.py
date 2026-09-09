#!/usr/bin/env python3
"""Collecte automatisée du corpus documentaire RAG (projet Alimendo / EndoNutrition).

Lit un manifest CSV de sources et récupère chaque source SELON SON STATUT LÉGAL,
qui est encodé dans les colonnes `acces` et `note_chunking` du manifest :

  • acces == "integral"            -> téléchargement du document complet (PDF/HTML)
  • acces protégé (reference_editoriale / synthese, ex. S6, S9)
                                    -> PAS de scraping. Création d'un stub de synthèse
                                      à rédiger manuellement en reformulation originale
                                      + lien + attribution.
  • note commençant par "EN RESERVE" (ex. S8)
                                    -> source mise de côté, non collectée par défaut.

Chaque exécution produit un log de traçabilité (_collecte_log.csv) : action, statut
HTTP, chemin, type MIME, taille, sha256, horodatage. C'est le livrable "collecte
automatisée + traçabilité" attendu pour C1/C2.

Usage :
    python collecte_rag.py --manifest corpus_manifest.csv --out data/raw/rag
    python collecte_rag.py --force          # re-télécharge même si déjà présent
    python collecte_rag.py --include-reserve # collecte aussi les sources EN RESERVE
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests



HERE = Path(__file__).resolve().parent          # = rag/

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("collecte_rag")

USER_AGENT = "Alimendo-RAG-collect/1.0 (projet etudiant EndoNutrition)"
TIMEOUT = 60
CHUNK = 8192


# ─── Utilitaires ─────────────────────────────────────────────────────────────
def slugify(text: str, maxlen: int = 60) -> str:
    """Transforme un titre en nom de fichier sûr."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen].strip("-")


def sha256_of(path: Path) -> str:
    """Empreinte SHA-256 d'un fichier, pour vérifier l'intégrité entre runs."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def classify(row: dict) -> str:
    """Détermine l'action à mener pour une source d'après le manifest.

    Retourne : "download" | "manual_synthesis" | "reserve".
    """
    note = (row.get("note_chunking") or "").strip().upper()
    if note.startswith("EN RESERVE"):
        return "reserve"
    if (row.get("acces") or "").strip() == "integral":
        return "download"
    return "manual_synthesis"


def ext_from_response(resp: requests.Response, url: str) -> str:
    """Devine l'extension de fichier à partir du Content-Type puis de l'URL."""
    ctype = resp.headers.get("Content-Type", "").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return "pdf"
    if "html" in ctype or url.lower().endswith((".html", ".htm")):
        return "html"
    return "bin"


# ─── Actions ─────────────────────────────────────────────────────────────────
def do_download(row: dict, out_dir: Path, force: bool) -> dict:
    """Télécharge une source `integral` (document complet)."""
    src_id = row["id_source"]
    url = row["url_recuperable"].strip()
    base = f"{src_id}__{slugify(row['titre'])}"

    # Skip si un fichier de cette source existe déjà (idempotence)
    existing = list(out_dir.glob(f"{src_id}__*"))
    existing = [p for p in existing if p.suffix != ".md"]
    if existing and not force:
        p = existing[0]
        logger.info("↩ %s déjà présent (%s) - skip", src_id, p.name)
        return _log_entry(row, "download", "skipped", None, p)

    try:
        with requests.get(url, stream=True, timeout=TIMEOUT,
                          headers={"User-Agent": USER_AGENT}) as r:
            r.raise_for_status()
            ext = ext_from_response(r, url)
            dest = out_dir / f"{base}.{ext}"
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK):
                    f.write(chunk)
            status = str(r.status_code)
            ctype = r.headers.get("Content-Type", "")
    except requests.RequestException as e:
        logger.error("%s échec téléchargement : %s", src_id, e)
        return _log_entry(row, "download", f"error:{type(e).__name__}", None, None)

    logger.info("%s téléchargé -> %s (%d Ko)", src_id, dest.name,
                dest.stat().st_size // 1024)
    return _log_entry(row, "download", status, ctype, dest)


def do_manual_synthesis(row: dict, out_dir: Path, force: bool) -> dict:
    """Source protégée : crée un stub de synthèse à rédiger à la main.

    On ne télécharge JAMAIS le corps de ces pages (S6, S8). On prépare un
    fichier .md à compléter en reformulation originale, avec lien + attribution.
    """
    src_id = row["id_source"]
    dest = out_dir / f"{src_id}__{slugify(row['titre'])}.synthese.md"
    if dest.exists() and not force:
        logger.info("↩ %s stub déjà présent - skip", src_id)
        return _log_entry(row, "manual_synthesis", "skipped", None, dest)

    stub = f"""---
id_source: {src_id}
titre: "{row['titre']}"
url: {row['url_recuperable']}
langue: {row['langue']}
couche: {row['couche']}
theme: {row['theme']}
licence: "{row['licence_indicative']}"
statut: A_REDIGER
---

<!--
SOURCE PROTÉGÉE - NE PAS COPIER LE TEXTE INTÉGRAL.
Consigne manifest : {row['note_chunking']}

À faire manuellement :
  1. Lire la page source.
  2. Rédiger ci-dessous une synthèse EN REFORMULATION ORIGINALE (tes mots).
  3. Conserver le lien et l'attribution (déjà en en-tête).
  Cette synthèse sera indexée dans ChromaDB à la place du texte original.
-->

# Synthèse - {row['titre']}

_(à rédiger)_

Source : {row['url_recuperable']}
Attribution : {row['licence_indicative']}
"""
    dest.write_text(stub, encoding="utf-8")
    logger.info("%s stub de synthèse créé -> %s", src_id, dest.name)
    return _log_entry(row, "manual_synthesis", "stub_created", "text/markdown", dest)


def do_reserve(row: dict, *_args) -> dict:
    """Source EN RESERVE : non collectée par défaut."""
    logger.info("%s EN RESERVE - non collectée (utilise --include-reserve pour forcer)",
                row["id_source"])
    return _log_entry(row, "reserve", "skipped_reserve", None, None)


# ─── Log de traçabilité ──────────────────────────────────────────────────────
def _log_entry(row: dict, action: str, status: str,
               ctype: str | None, path: Path | None) -> dict:
    return {
        "id_source": row["id_source"],
        "titre": row["titre"],
        "action": action,
        "statut": status,
        "content_type": ctype or "",
        "chemin": str(path) if path else "",
        "taille_octets": path.stat().st_size if path and path.exists() else "",
        "sha256": sha256_of(path) if path and path.exists() and path.is_file() else "",
        "url": row["url_recuperable"],
        "licence": row["licence_indicative"],
        "recupere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_log(entries: list[dict], out_dir: Path) -> None:
    log_path = out_dir / "_collecte_log.csv"
    fields = ["id_source", "titre", "action", "statut", "content_type", "chemin",
              "taille_octets", "sha256", "url", "licence", "recupere_le"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(entries)
    logger.info("Log de collecte écrit -> %s", log_path)


# ─── Orchestration ───────────────────────────────────────────────────────────
def run(manifest: Path, out_dir: Path, force: bool, include_reserve: bool,
        delay: float) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(manifest, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    logger.info("Manifest : %d sources", len(rows))
    handlers = {
        "download": do_download,
        "manual_synthesis": do_manual_synthesis,
        "reserve": do_reserve,
    }

    entries: list[dict] = []
    for row in rows:
        action = classify(row)
        if action == "reserve" and include_reserve:
            action = "download"  # override explicite demandé par l'utilisateur
        entry = handlers[action](row, out_dir, force)
        entries.append(entry)
        if action == "download" and entry["statut"] not in ("skipped",):
            time.sleep(delay)  # politesse : on n'enchaîne pas les requêtes

    write_log(entries, out_dir)

    # Récapitulatif
    from collections import Counter
    summary = Counter(e["action"] for e in entries)
    logger.info("Terminé - %s", dict(summary))
    logger.info("Pense à compléter les stubs .synthese.md des sources protégées.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collecte du corpus RAG EndoNutrition.")
    p.add_argument("--manifest", type=Path, default=HERE / "corpus_manifest.csv")
    p.add_argument("--out",      type=Path, default=HERE / "data" / "raw")
    p.add_argument("--force", action="store_true", help="Re-télécharge même si présent.")
    p.add_argument("--include-reserve", action="store_true",
                   help="Collecte aussi les sources marquées EN RESERVE.")
    p.add_argument("--delay", type=float, default=1.0,
                   help="Pause en secondes entre deux téléchargements.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.manifest, args.out, args.force, args.include_reserve, args.delay)
