"""Filet de sécurité déterministe : détection de la détresse (version 1.0).

But du fichier : repérer, par des règles lexicales, un message où la personne
exprime sa propre souffrance présente. Si le filet se déclenche, la question
est routée en `detresse_urgence` SANS consulter le modèle statistique.

Pourquoi un filet en plus du modèle : un message de détresse mal routé est
l'erreur la plus grave du chatbot. Sur le jeu de test, le modèle seul retrouve
72 % des détresses ; avec le filet, 100 % (25/25).

Origine : transcription à l'identique de la cellule « Filet de sécurité
déterministe » du notebook `02_classifieur.ipynb` (dépôt alimendo_data_science).
Toute modification des motifs doit être faite dans les deux dépôts, et la
version `VERSION_FILET` incrémentée.

Aucune dépendance externe : le filet fonctionne même si le modèle est absent.
"""

from __future__ import annotations

import re
import unicodedata

# Version des motifs, reprise de `intent_classifier_meta.json` (safety_net_version).
VERSION_FILET = "1.0"


def normaliser(texte: str) -> str:
    """Met le texte en minuscules, sans accents et sans ponctuation.

    Les messages réels contiennent des fautes et des accents manquants :
    « soufre » / « souffre », « à bout » / « a bou » deviennent comparables.
    C'est ce qui rend les règles robustes aux fautes.
    """
    texte = texte.lower()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))  # é -> e
    texte = re.sub(r"[^a-z0-9 ]", " ", texte)  # apostrophes, ponctuation -> espace
    return re.sub(r"\s+", " ", texte).strip()


# Motifs regroupés par type de signal. On cherche le RAPPEL maximal :
# mieux vaut sur-déclencher que rater une détresse.
MOTIFS_DETRESSE: tuple[str, ...] = (
    # Appel à l'aide explicite (déclencheurs durs, quasi jamais hors détresse)
    r"\bsos\b", r"au secours", r"aid(ez|e)?[ ]?moi",
    # Épuisement, désespoir
    r"\bjpp\b", r"(en|ne) peux\b.{0,12}\bplus", r"\ba bou", r"epuis",
    r"craqu", r"a quoi bon", r"pleure", r"detruit",
    r"personne ne.{0,8}comprend", r"martyr",
    # Douleur intense en 1re personne (avec intensité, pour ne pas capter
    # les questions abstraites sur la douleur)
    r"trop de mal|trop mal|tro mal|si mal|tellement mal",
    r"souffr|soufr", r"insupportable|insuportable", r"pliee|plie en deux",
    r"douleur.{0,15}(horrible|insupportable|insuportable|atroce|affreuse)",
    r"mal.{0,10}(insupportable|atroce|horrible)",
    r"\bmal\b.{0,20}\bmal\b",  # répétition : « jai mal jai mal »
    # Symptômes aigus, orientation urgente
    r"evanoui", r"vertige", r"\burgence", r"\bh ?24\b",
    r"saignement.{0,15}abondant|(tres )?abondant",
)

_MOTIFS_COMPILES: tuple[re.Pattern[str], ...] = tuple(re.compile(m) for m in MOTIFS_DETRESSE)


def est_detresse(texte: str) -> bool:
    """Indique si au moins un motif de détresse est présent dans le texte."""
    texte_normalise = normaliser(texte)
    return any(motif.search(texte_normalise) for motif in _MOTIFS_COMPILES)
