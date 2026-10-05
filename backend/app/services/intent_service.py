"""Routage d'intention des questions du chatbot : cinq classes.

Deux étages, le filet prime :

```
question --> [1] filet de sécurité déterministe se déclenche ?
            oui ------> detresse_urgence   (le modèle n'est pas consulté)
            non ------> [2] modèle TF-IDF + LogReg ---> une des 5 classes
```

L'ordre compte : Une personne en souffrance ne doit recevoir ni une
réponse documentaire fluide, ni un « votre question sort du périmètre ».

"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


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


# Repli provisoire -> à remplacer par le vrai routeur

def _normaliser(texte: str) -> str:
    """Minuscules, sans accents, sans ponctuation.

    Même principe que `intent_safety_net.normalize` : les messages réels
    contiennent des fautes et des accents manquants, les règles doivent y
    résister.
    """
    texte = texte.lower()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^a-z0-9 ]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


# Sous-ensemble réduit des motifs de `intent_safety_net.py`.
# Volontairement incomplet : c'est un repli, pas le filet de sécurité.
_MOTIFS_DETRESSE_PROVISOIRES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(motif)
    for motif in (
        r"\bsos\b",
        r"au secours",
        r"aid(ez|e)?[ ]?moi",
        r"\bjpp\b",
        r"(en|ne) peux\b.{0,12}\bplus",
        r"\ba bou",
        r"epuis",
        r"craqu",
        r"a quoi bon",
        r"pleure",
        r"trop de mal|trop mal|tro mal|si mal|tellement mal",
        r"souffr|soufr",
        r"insupportable|insuportable",
        r"pliee|plie en deux",
        r"\bmal\b.{0,20}\bmal\b",
        r"evanoui",
        r"\burgence",
    )
)

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


def _classer_par_repli(question: str) -> tuple[Intention, str, float]:
    """Classe une question sans le modèle entraîné.

    Détresse, puis restriction, puis hors périmètre, puis aliment, puis
    domaine. La confiance renvoyée est volontairement basse (0.0) sauf pour la
    détresse : elle signale à l'appelant que cette décision ne vient pas d'un
    modèle évalué.
    """
    texte = _normaliser(question)

    if any(motif.search(texte) for motif in _MOTIFS_DETRESSE_PROVISOIRES):
        return Intention.DETRESSE_URGENCE, "heuristique_provisoire", 1.0

    if any(motif in texte for motif in _MOTIFS_RESTRICTION):
        return Intention.RESTRICTION_ALIMENTAIRE, "heuristique_provisoire", 0.0

    if any(motif in texte for motif in _MOTIFS_HORS_PERIMETRE):
        return Intention.OUT_OF_SCOPE, "heuristique_provisoire", 0.0

    est_une_definition = texte.startswith("qu est ce que") or "c est quoi" in texte

    if not est_une_definition and any(motif in texte for motif in _MOTIFS_ALIMENT):
        return Intention.FOOD_SPECIFIC, "heuristique_provisoire", 0.0

    if any(motif in texte for motif in _MOTIFS_DOMAINE):
        return Intention.IN_SCOPE, "heuristique_provisoire", 0.0

    return Intention.OUT_OF_SCOPE, "heuristique_provisoire", 0.0



# Point d'entrée

def router(question: str) -> ResultatRoutage:
    """Route une question vers une intention et l'action backend associée.

    Args:
        question: la question posée par l'utilisatrice.

    Returns:
        Le résultat du routage, dont l'appelant lit `routage.action`.
    """
    intent, source, confidence = _classer_par_repli(question)

    if intent is Intention.DETRESSE_URGENCE:
        # Journalisé en avertissement : ces routages doivent être relus
        # régulièrement pour enrichir le filet (amélioration continue).
        logger.warning("routage détresse déclenché (source=%s)", source)

    return ResultatRoutage(
        question=question,
        intent=intent,
        source=source,
        confidence=confidence,
        routage=ROUTING[intent],
    )
