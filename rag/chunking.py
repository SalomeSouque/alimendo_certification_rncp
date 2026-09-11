"""Chunking piloté par le manifest -> chunks porteurs des métadonnées de citation.

Entrée : rag/data/processed/{id}.txt   (produit par extraction.py)
         corpus_manifest.csv            (métadonnées + consignes note_chunking)
Sortie : rag/data/processed/chunks.jsonl        (1 chunk/ligne : id + texte + métadonnées)
         rag/data/processed/_chunking_log.csv    (stats par source)
         rag/data/processed/_chunking_dropped.csv (chunks écartés en mode sélectif - À AUDITER)

Deux principes :
  1. Le découpage respecte note_chunking par source (intégral/sélectif & marqueurs).
  2. Chaque chunk porte les métadonnées de citation obligatoires (id_source, titre,
     url, licence, theme, couche + marqueurs).

Lancement :
    uv run python rag/chunking.py
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    PROCESSED_DIR,
    MANIFEST_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("chunking")

CHUNKS_PATH: Path = PROCESSED_DIR / "chunks.jsonl"
CHUNKING_LOG_PATH: Path = PROCESSED_DIR / "_chunking_log.csv"
DROPPED_LOG_PATH: Path = PROCESSED_DIR / "_chunking_dropped.csv"


#  Politique de chunking par source --
# Dérivée EXPLICITEMENT de la colonne note_chunking du manifest. Toute source
# absente de ce dict est traitée en "integral" avec un WARNING : on n'indexe
# jamais en silence une source dont la consigne n'a pas été relue.
#
#   strategy : "integral"  -> on découpe tout le texte.
#              "selective" -> on découpe tout, puis on ÉCARTE de l'index les
#                            chunks contenant un mot-clé `exclude` (hors périmètre).

@dataclass
class ChunkPolicy:
    strategy: str = "integral"
    exclude: tuple[str, ...] = ()
    markers: dict[str, str] = field(default_factory=dict)


CHUNK_POLICY: dict[str, ChunkPolicy] = {
    # S1 - "Chunker intégralement. Source de synthèse la plus haute du corpus."
    "S1": ChunkPolicy(markers={"niveau_synthese": "umbrella_review"}),
    # S2 - "Priorité au chapitre Non-medical management. Exclure diagnostic/chirurgie/fertilité."
    "S2": ChunkPolicy(
        strategy="selective",
        exclude=("diagnosis", "surgery", "surgical", "fertility", "infertility",
                 "laparoscop", "hormonal therapy", "medication", "in vitro"),
        markers={"portee": "cadre_institutionnel"},
    ),
    # S3 - "Chunker intégralement. Marquer : RISQUE de développer, PAS symptômes."
    "S3": ChunkPolicy(markers={"portee": "risque_pas_symptomes"}),
    # S4 - "Source principale des mécanismes (inflammation / œstrogènes / microbiote)."
    "S4": ChunkPolicy(markers={"usage": "mecanismes"}),
    # S5 - "Seule source du corpus couvrant le volet digestif."
    "S5": ChunkPolicy(markers={"theme_specifique": "digestif_endo_belly"}),
    # S6 - stub rédigé (synthèse éditoriale FR). Intégral sur le texte reformulé.
    "S6": ChunkPolicy(markers={"registre": "editorial_fr"}),
    # S8 - stub rédigé (synthèse Inserm ciblée). Intégral sur le texte reformulé.
    "S8": ChunkPolicy(markers={"usage": "ancrage_maladie"}),
    # S9 - "Sélectif : garder définition/épidémio/physiopath/impact.
    #        EXCLURE management/chirurgie/hormonal."
    "S9": ChunkPolicy(
        strategy="selective",
        exclude=("management", "treatment", "surgery", "surgical",
                 "hormonal", "medication", "laparoscop", "excision"),
        markers={"usage": "ancrage_maladie"},
    ),
    # S10 - "Document court. Chiffres de référence (~190 M, ~10 %)."
    "S10": ChunkPolicy(markers={"usage": "chiffres_reference"}),
    # S7 - EN RÉSERVE : non extrait, donc jamais présent ici. Pas d'entrée volontairement.
}

DEFAULT_POLICY = ChunkPolicy()


#  Cœur du module --

def make_splitter() -> RecursiveCharacterTextSplitter:
    """Le splitter récursif essaie de couper aux frontières naturelles d'abord.

    Ordre des séparateurs : paragraphe -> ligne -> phrase -> mot -> caractère.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,  # longueur en caractères
    )


def should_keep_chunk(text: str, policy: ChunkPolicy) -> tuple[bool, str]:
    """Décide si un chunk entre dans l'index (mode sélectif uniquement).

    Retourne (garder, mot_cle_declencheur).
    """
    if policy.strategy != "selective":
        return True, ""
    low = text.lower()
    for kw in policy.exclude:
        if kw in low:
            return False, kw
    return True, ""


def build_metadata(row: dict[str, str], policy: ChunkPolicy, chunk_index: int) -> dict:
    """Construit les métadonnées de citation d'un chunk depuis la ligne du manifest.
    id_source, titre, url, licence_indicative, theme, couche. On ajoute langue
    et chunk_index (bookkeeping), puis les marqueurs scalaires de la source.
    """
    couche_raw = row.get("couche", "").strip()
    meta: dict[str, object] = {
        "id_source": row["id_source"],
        "titre": row["titre"],
        "url": row["url_recuperable"],
        "licence_indicative": row["licence_indicative"],
        "theme": row["theme"],
        "couche": int(couche_raw) if couche_raw.isdigit() else couche_raw,
        "langue": row["langue"],
        "chunk_index": chunk_index,
    }
    # Marqueurs imposés par note_chunking (ex. S3 -> portee=risque_pas_symptomes).
    meta.update(policy.markers)
    return meta


def read_manifest() -> dict[str, dict[str, str]]:
    """Manifest indexé par id_source : {id: {colonne: valeur}}."""
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        return {row["id_source"]: row for row in csv.DictReader(f)}


@dataclass
class SourceStats:
    id_source: str
    strategy: str
    kept: int = 0
    dropped: int = 0


def chunk_source(
    row: dict[str, str],
    splitter: RecursiveCharacterTextSplitter,
    out_f,
    dropped_writer,
) -> SourceStats | None:
    """Découpe une source, filtre (sélectif), écrit ses chunks. None si non extraite."""
    id_source = row["id_source"]
    txt_path = PROCESSED_DIR / f"{id_source}.txt"
    if not txt_path.exists():
        return None

    policy = CHUNK_POLICY.get(id_source)
    if policy is None:
        logger.warning("%s : aucune politique définie -> 'integral' par défaut.", id_source)
        policy = DEFAULT_POLICY

    text = txt_path.read_text(encoding="utf-8")
    raw_chunks = splitter.split_text(text)

    stats = SourceStats(id_source=id_source, strategy=policy.strategy)
    kept_index = 0
    for chunk_text in raw_chunks:
        keep, kw = should_keep_chunk(chunk_text, policy)
        if not keep:
            stats.dropped += 1
            dropped_writer.writerow([id_source, kw, chunk_text[:120].replace("\n", " ")])
            continue
        meta = build_metadata(row, policy, kept_index)
        record = {
            "id": f"{id_source}::{kept_index:03d}",  # id stable -> upsert idempotent
            "text": chunk_text,
            "metadata": meta,
        }
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        kept_index += 1
    stats.kept = kept_index
    return stats


def main() -> None:
    manifest = read_manifest()
    splitter = make_splitter()

    with (
        CHUNKS_PATH.open("w", encoding="utf-8") as out_f,
        DROPPED_LOG_PATH.open("w", encoding="utf-8", newline="") as dropped_f,
    ):
        dropped_writer = csv.writer(dropped_f)
        dropped_writer.writerow(["id_source", "mot_cle_declencheur", "apercu"])

        all_stats: list[SourceStats] = []
        for row in manifest.values():
            stats = chunk_source(row, splitter, out_f, dropped_writer)
            if stats is not None:
                all_stats.append(stats)

    # Journal des stats par source.
    with CHUNKING_LOG_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id_source", "strategy", "chunks_gardes", "chunks_ecartes"])
        for s in all_stats:
            writer.writerow([s.id_source, s.strategy, s.kept, s.dropped])

    total = sum(s.kept for s in all_stats)
    logger.info("Terminé : %d chunks écrits pour %d sources.", total, len(all_stats))
    for s in all_stats:
        flag = f" ({s.dropped} écartés)" if s.dropped else ""
        logger.info("  %-4s [%s] %d chunks%s", s.id_source, s.strategy, s.kept, flag)
    logger.info("Chunks   : %s", CHUNKS_PATH)
    logger.info("Écartés (à auditer) : %s", DROPPED_LOG_PATH)


if __name__ == "__main__":
    main()
