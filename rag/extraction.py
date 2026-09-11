"""Extraction & nettoyage du corpus brut -> texte propre.

Entrée : rag/data/raw/   (PDF, HTML, ou {id}.synthese.md produits par collecte.py)
Sortie : rag/data/processed/{id_source}.txt        (UTF-8, nettoyé)
         rag/data/processed/_extraction_log.csv     (traçabilité C2)

Principe : le module est piloté par le MANIFEST.
Lancement :
    uv run python rag/extraction.py
"""
from __future__ import annotations

import csv
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
import trafilatura

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    MANIFEST_PATH,
    EXTRACTION_LOG_PATH,
    MIN_CHARS_VALID,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("extraction")


@dataclass
class ExtractionResult:
    """Résultat par source, sérialisé ensuite dans le journal C2."""
    id_source: str
    status: str            # ok | skipped_stub | missing | empty | error
    method: str = ""       # html | pdf | markdown |
    chars: int = 0
    note: str = ""


#  Extracteurs par format 

def extract_html(path: Path) -> str:
    """Extrait le contenu principal d'une page HTML sauvegardée.

    trafilatura isole le corps de l'article et jette le boilerplate
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = trafilatura.extract(
        raw,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    return text or ""


def extract_pdf(path: Path) -> str:
    """Extrait le texte d'un PDF, page par page.

    Limite connue : sur un PDF scientifique en 2 colonnes, l'ordre de lecture
    peut être imparfait.
    """
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


_FRONTMATTER_RE = re.compile(r"^\n(.*?)\n\n", re.DOTALL)


def extract_markdown_stub(path: Path) -> tuple[str, bool]:
    """Lit un stub {id}.synthese.md (synthèse rédigée à la main pour S6/S9).

    Retourne (texte, est_redige). est_redige=False si le frontmatter porte
    `statut: A_REDIGER` ou si le corps est vide
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    statut = ""
    body = raw
    m = _FRONTMATTER_RE.match(raw)
    if m:
        body = raw[m.end():]
        sm = re.search(r"statut\s*:\s*(\S+)", m.group(1))
        if sm:
            statut = sm.group(1).strip().upper()
    body = body.strip()
    est_redige = statut != "A_REDIGER" and len(body) > 0
    return body, est_redige


#  Nettoyage -

def clean_text(text: str) -> str:
    """Normalise du texte extrait de PDF/HTML en texte propre et homogène.

    Chaque étape corrige un artefact classique d'extraction :
    """
    # 1. Normalisation Unicode.
    text = unicodedata.normalize("NFC", text)
    # 2. Mots coupés en fin de ligne par le PDF : "inflamma-\ntion" -> "inflammation".
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # 3. Retour à la ligne SIMPLE au milieu d'un paragraphe. On préserve les doubles = paragraphes.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # 4. Espaces/tabulations multiples -> un seul espace.
    text = re.sub(r"[ \t]+", " ", text)
    # 5. Plus de 2 sauts de ligne consécutifs -> 2 (séparateur de paragraphe net).
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


#  Localisation du fichier brut 

def find_source_file(id_source: str) -> tuple[Path | None, str]:
    """Localise le fichier brut d'une source et le type d'extraction à appliquer.

    """
    prefix_re = re.compile(rf"^{re.escape(id_source)}[._-]")
    # Tri pour un résultat déterministe si plusieurs fichiers matchent.
    candidates = sorted(
        p for p in RAW_DIR.iterdir()
        if p.is_file() and prefix_re.match(p.name)
    )

    # 1. Stub rédigé à la main (S6/S9) : {id}...synthese.md
    for p in candidates:
        if p.name.endswith(".synthese.md"):
            return p, "markdown"
    # 2. HTML d'abord
    for p in candidates:
        if p.suffix.lower() in (".html", ".htm"):
            return p, "html"
    # 3. PDF en dernier recours.
    for p in candidates:
        if p.suffix.lower() == ".pdf":
            return p, "pdf"
    return None, ""


#  Orchestration 

def process_source(id_source: str) -> ExtractionResult:
    """Extrait, nettoie et écrit une source ; renvoie son résultat journalisable."""
    path, method = find_source_file(id_source)
    if path is None:
        return ExtractionResult(id_source, status="missing", note="aucun fichier dans raw/")

    try:
        if method == "markdown":
            body, est_redige = extract_markdown_stub(path)
            if not est_redige:
                return ExtractionResult(
                    id_source, status="skipped_stub", method="markdown",
                    note="stub non rédigé (A_REDIGER/vide) - ignoré",
                )
            # Le stub est déjà propre normalisation minimale
            text = unicodedata.normalize("NFC", body).strip()
        elif method == "html":
            text = clean_text(extract_html(path))
        else:  # pdf
            text = clean_text(extract_pdf(path))
    except Exception as exc:
        # On journalise et on continue
        logger.error("Échec extraction %s (%s) : %s", id_source, method, exc)
        return ExtractionResult(id_source, status="error", method=method, note=str(exc)[:200])

    if len(text) < MIN_CHARS_VALID:
        return ExtractionResult(
            id_source, status="empty", method=method, chars=len(text),
            note=f"texte trop court (<{MIN_CHARS_VALID}) - extraction suspecte",
        )

    out_path = PROCESSED_DIR / f"{id_source}.txt"
    out_path.write_text(text, encoding="utf-8")
    return ExtractionResult(id_source, status="ok", method=method, chars=len(text))


def read_manifest_ids() -> list[str]:
    """Liste des id_source à traiter, dans l'ordre du manifest."""
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        return [row["id_source"] for row in csv.DictReader(f)]


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    ids = read_manifest_ids()
    results = [process_source(i) for i in ids]

    # Journal : trace exactement ce qui a été nettoyé et les cas non standard.
    with EXTRACTION_LOG_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id_source", "status", "method", "chars", "note"])
        for r in results:
            writer.writerow([r.id_source, r.status, r.method, r.chars, r.note])

    ok = [r for r in results if r.status == "ok"]
    logger.info("Terminé : %d/%d sources extraites.", len(ok), len(results))
    for r in results:
        if r.status != "ok":
            logger.warning("  %-4s -> %-13s %s", r.id_source, r.status, r.note)
    logger.info("Texte propre : %s", PROCESSED_DIR)
    logger.info("Journal C2   : %s", EXTRACTION_LOG_PATH)


if __name__ == "__main__":
    main()