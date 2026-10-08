"""Routage d'intention des questions du chatbot : cinq classes.

But du fichier : décider, avant tout appel au RAG ou au LLM, ce que le backend
fait d'une question. Seule `in_scope` déclenche la recherche documentaire et
la génération ; les quatre autres classes renvoient un texte figé des
guidelines.

Deux étages, le filet prime :

```
question --> [1] filet de sécurité déterministe se déclenche ?
            oui ------> detresse_urgence   (le modèle n'est pas consulté)
            non ------> [2] modèle TF-IDF + LogReg ---> une des 5 classes
```

L'ordre compte : une personne en souffrance ne doit recevoir ni une
réponse documentaire fluide, ni un « votre question sort du périmètre ».

Le modèle de l'étage 2 est le classifieur entraîné dans le notebook
`02_classifieur.ipynb` (dépôt alimendo_data_science), livré sous forme de
fichier `app/ml/intent_classifier.pkl`. Si ce fichier est absent ou
inutilisable, l'étage 2 bascule sur une heuristique par mots-clés
(`source = "heuristique_provisoire"`) pour que le chatbot reste utilisable ;
le filet de sécurité, lui, s'applique dans tous les cas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.services.intent_safety_net import est_detresse, normaliser

logger = logging.getLogger(__name__)

# Artefact du modèle entraîné : app/services/ -> app/ -> app/ml/
CHEMIN_MODELE = Path(__file__).resolve().parents[1] / "ml" / "intent_classifier.pkl"


class Intention(StrEnum):
    """Les cinq classes d'intention, par ordre de priorité décroissante."""

    DETRESSE_URGENCE = "detresse_urgence"
    RESTRICTION_ALIMENTAIRE = "restriction_alimentaire"
    OUT_OF_SCOPE = "out_of_scope"
    FOOD_SPECIFIC = "food_specific"
    IN_SCOPE = "in_scope"


@dataclass(frozen=True)
class Routage:
    """Comportement backend associé à une intention.

    Attributes:
        action: identifiant d'action lu par le service RAG.
        retrieval: faut-il interroger l'index vectoriel ?
        llm: faut-il appeler le modèle de génération ?
        text_ref: section des guidelines portant le texte figé à afficher.
    """

    action: str
    retrieval: bool
    llm: bool
    text_ref: str


#: Classe -> comportement attendu. Transcription de `route_intent.py`.
ROUTING: dict[Intention, Routage] = {
    Intention.DETRESSE_URGENCE: Routage(
        action="SAFE_RESPONSE_DISTRESS", retrieval=False, llm=False, text_ref="§7.5"
    ),
    Intention.RESTRICTION_ALIMENTAIRE: Routage(
        action="SAFE_RESPONSE_RESTRICTION", retrieval=False, llm=False, text_ref="§7.6"
    ),
    Intention.OUT_OF_SCOPE: Routage(
        action="STATIC_RESPONSE_OOS", retrieval=False, llm=False, text_ref="§7.1"
    ),
    Intention.FOOD_SPECIFIC: Routage(
        action="REDIRECT_SCAN", retrieval=False, llm=False, text_ref="§7.2"
    ),
    Intention.IN_SCOPE: Routage(
        action="RAG_RETRIEVAL", retrieval=True, llm=True, text_ref="§7.3 (repli)"
    ),
}


@dataclass(frozen=True)
class ResultatRoutage:
    """Résultat complet d'un routage, aligné sur le retour de `route()`."""

    question: str
    intent: Intention
    source: str          # "safety_net" | "model" | "heuristique_provisoire"
    confidence: float
    routage: Routage

    def to_dict(self) -> dict[str, Any]:
        """Représentation identique à celle du composant d'origine."""
        return {
            "question": self.question,
            "intent": self.intent.value,
            "source": self.source,
            "confidence": self.confidence,
            "action": self.routage.action,
            "retrieval": self.routage.retrieval,
            "llm": self.routage.llm,
            "text_ref": self.routage.text_ref,
        }


# Étage 2 : le modèle entraîné

@lru_cache(maxsize=1)
def charger_modele() -> Any | None:
    """Charge le classifieur entraîné une seule fois (mis en cache).

    Returns:
        Le pipeline scikit-learn, ou None s'il est absent ou incohérent
        avec les cinq classes attendues. None déclenche le repli heuristique.
    """
    if not CHEMIN_MODELE.exists():
        logger.warning(
            "classifieur d'intention introuvable (%s) : repli sur l'heuristique",
            CHEMIN_MODELE,
        )
        return None

    try:
        modele = joblib.load(CHEMIN_MODELE)
    except Exception:  # fichier corrompu, version de scikit-learn incompatible...
        logger.exception("chargement du classifieur d'intention impossible : repli sur l'heuristique")
        return None

    # Garde-fou : un modèle qui ne connaît pas exactement nos 5 classes
    # produirait des intentions sans routage défini.
    classes_modele = {str(c) for c in getattr(modele, "classes_", [])}
    if classes_modele != {i.value for i in Intention}:
        logger.error(
            "classes du classifieur inattendues (%s) : repli sur l'heuristique",
            sorted(classes_modele),
        )
        return None

    logger.info("classifieur d'intention chargé : %s", CHEMIN_MODELE.name)
    return modele


def modele_est_charge() -> bool:
    """Indique si l'étage 2 utilise le modèle entraîné, utilisé par le healthcheck."""
    return charger_modele() is not None


def _classer_par_modele(modele: Any, question: str) -> tuple[Intention, float]:
    """Prédit l'intention avec le modèle entraîné.

    Returns:
        L'intention la plus probable et sa probabilité (la confiance).
    """
    probabilites = modele.predict_proba([question])[0]
    meilleur = int(probabilites.argmax())
    return Intention(str(modele.classes_[meilleur])), float(probabilites[meilleur])


# Repli : heuristique par mots-clés, utilisée seulement sans modèle.
# La détresse n'y figure plus : elle est entièrement gérée par le filet.

# Marqueurs d'une demande d'éviction ou de restriction alimentaire.
_MOTIFS_RESTRICTION: tuple[str, ...] = (
    "supprimer",
    "eliminer",
    "arreter de manger",
    "eviter",
    "je dois eviter",
    "interdit",
    "quoi ne pas manger",
    "regime",
    "menu type",
    "plan alimentaire",
    "combien de portions",
    "culpabil",
    "coupable",
)

# Marqueurs d'une question portant sur un aliment nommé.
_MOTIFS_ALIMENT: tuple[str, ...] = (
    "quel est le score",
    "quel score",
    "combien de calories",
)

# Marqueurs explicitement hors périmètre.
_MOTIFS_HORS_PERIMETRE: tuple[str, ...] = (
    "diagnostic",
    "est ce que j ai",
    "operation",
    "chirurgie",
    "traitement",
    "pilule",
    "contraception",
    "fertilite",
    "tomber enceinte",
    "grossesse",
    "fiv",
    "pma",
    "gluten",
    "fodmap",
)

# Marqueurs du domaine couvert par le corpus.
_MOTIFS_DOMAINE: tuple[str, ...] = (
    "endometriose",
    "inflammation",
    "inflammatoire",
    "nutrition",
    "alimentation",
    "alimentaire",
    "microbiote",
    "ballonnement",
    "endo belly",
    "digestion",
    "digestif",
    "fibre",
    "omega",
    "nutriment",
    "symptome",
)


def _classer_par_repli(question: str) -> Intention:
    """Classe une question sans le modèle entraîné.

    Ordre de priorité : restriction, hors périmètre, aliment, domaine.
    Par défaut, hors périmètre (prudence : pas d'appel au LLM).
    """
    texte = normaliser(question)

    if any(motif in texte for motif in _MOTIFS_RESTRICTION):
        return Intention.RESTRICTION_ALIMENTAIRE

    if any(motif in texte for motif in _MOTIFS_HORS_PERIMETRE):
        return Intention.OUT_OF_SCOPE

    est_une_definition = texte.startswith("qu est ce que") or "c est quoi" in texte

    if not est_une_definition and any(motif in texte for motif in _MOTIFS_ALIMENT):
        return Intention.FOOD_SPECIFIC

    if any(motif in texte for motif in _MOTIFS_DOMAINE):
        return Intention.IN_SCOPE

    return Intention.OUT_OF_SCOPE


# Point d'entrée

def router(question: str) -> ResultatRoutage:
    """Route une question vers une intention et l'action backend associée.

    Args:
        question: la question posée par l'utilisatrice.

    Returns:
        Le résultat du routage, dont l'appelant lit `routage.action`.
    """
    modele = charger_modele()

    if est_detresse(question):
        # Étage 1 : le filet prime, le modèle n'est pas consulté.
        intent, source, confidence = Intention.DETRESSE_URGENCE, "safety_net", 1.0
    elif modele is not None:
        # Étage 2 : le modèle entraîné.
        intent, confidence = _classer_par_modele(modele, question)
        source = "model"
    else:
        # Repli : confiance 0.0 pour signaler qu'aucun modèle évalué n'a décidé.
        intent, source, confidence = _classer_par_repli(question), "heuristique_provisoire", 0.0

    # Une ligne de log par routage, sans le texte de la question (donnée
    # potentiellement sensible). Sert au suivi du modèle et du filet.
    niveau = logging.WARNING if intent is Intention.DETRESSE_URGENCE else logging.INFO
    logger.log(
        niveau,
        "routage intent=%s source=%s confidence=%.3f",
        intent.value,
        source,
        confidence,
    )

    return ResultatRoutage(
        question=question,
        intent=intent,
        source=source,
        confidence=confidence,
        routage=ROUTING[intent],
    )
