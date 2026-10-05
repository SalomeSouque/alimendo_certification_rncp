"""Formulations médicales validées / transcription littérale de deux documents.

Sources :

- `score_medical-guidelines.md` : tout ce qui touche au score des aliments.
- `RAG_medical-guidelines.md` section 7 : tout ce qui touche au chatbot.
"""

from __future__ import annotations

from typing import Final

# Versions des référentiels de formulations

#: Version des guidelines du chatbot (RAG_medical-guidelines.md, en-tête).
VERSION_GUIDELINES_RAG: Final[str] = "guidelines-v1.0-2026-09"


# SCORE / source : score_medical-guidelines.md

# Disclaimer court, à afficher à côté de CHAQUE score.
DISCLAIMER_SCORE: Final[str] = (
    "Score indicatif, basé sur le profil nutritionnel de l'aliment. "
    "Il ne constitue pas un avis médical et ne prédit pas l'effet de cet "
    "aliment sur vos symptômes."
)

# Mention projet étudiant, obligatoire sur toutes les pages.
MENTION_PROJET_ETUDIANT: Final[str] = (
    "Projet étudiant à but pédagogique. Ce service n'a pas vocation à être "
    "utilisé comme outil de santé. Réalisé dans le cadre d'une certification "
    "en développement d'intelligence artificielle, sans expertise médicale."
)

# Citation de source courte, affichée avec le score.
CITATION_SOURCE_COURTE: Final[str] = (
    "Approche inspirée du Dietary Inflammatory Index (Shivappa et al., 2014)."
)

# Citation de source longue, page « Comment lire ce score ».
CITATION_SOURCE_LONGUE: Final[str] = (
    "Le score est calculé selon une approche inspirée du Dietary Inflammatory "
    "Index (Shivappa N., Steck S.E., Hurley T.G., Hussey J.R., Hébert J.R., "
    "Public Health Nutrition, 2014), à partir des données de composition de la "
    "table CIQUAL 2020 (ANSES) et de la base Open Food Facts. Les coefficients "
    "officiels du DII étant propriétaires, ce score n'en est pas une "
    "reproduction : il en reprend la direction et l'intensité relative des "
    "paramètres, avec une normalisation propre décrite dans notre "
    "documentation méthodologique."
)

# Libellés des niveaux de score. Aucun vocabulaire moral.
LIBELLES_NIVEAU: Final[dict[int, str]] = {
    2: "Fortement pro-inflammatoire",
    1: "Modérément pro-inflammatoire",
    0: "Neutre",
    -1: "Modérément anti-inflammatoire",
    -2: "Fortement anti-inflammatoire",
}

# Messages de score indisponible, par cause.
MESSAGE_COMPLETUDE_INSUFFISANTE: Final[str] = (
    "Score indisponible : données nutritionnelles insuffisantes pour cet aliment."
)
MESSAGE_HORS_PERIMETRE: Final[str] = (
    "Score indisponible : cet aliment n'a pas de profil nutritionnel "
    "significatif (moins de 1 g de glucides, protéines et lipides pour 100 g)."
)

# Introduction d'une liste d'alternatives.
LIBELLE_ALTERNATIVES: Final[str] = (
    "Autres options au profil nutritionnel moins pro-inflammatoire"
)



# CHATBOT / source : RAG_medical-guidelines.md 

#`out_of_scope` : question hors périmètre.
TEXTE_OUT_OF_SCOPE: Final[str] = (
    "Je suis un assistant documentaire limité à l'endométriose et à "
    "l'alimentation. Votre question sort de ce périmètre, je ne peux donc pas "
    "y répondre.\n\n"
    "Pour toute question de santé, en particulier sur un diagnostic ou un "
    "traitement, adressez-vous à un professionnel de santé."
)

# `food_specific` : redirection produit vers le scan ou la recherche.
TEXTE_FOOD_SPECIFIC: Final[str] = (
    "Je n'ai pas accès à la base d'aliments du site : je ne peux pas vous "
    "donner le score d'un aliment précis.\n\n"
    "Pour cela, utilisez le scan ou la recherche d'aliments. Je peux en "
    "revanche vous expliquer ce que la littérature dit des mécanismes en jeu, "
    "si cela vous intéresse."
)

# repli : le retrieval n'a rien remonté de suffisamment pertinent.
TEXTE_FALLBACK: Final[str] = (
    "Je n'ai pas trouvé, dans ma documentation, de source fiable permettant de "
    "répondre à cette question.\n\n"
    "Je préfère ne rien affirmer plutôt que de vous donner une information "
    "incertaine. Vous pouvez reformuler votre question, ou en poser une autre "
    "sur l'endométriose et l'alimentation."
)

# redirection vers le parcours de soins.
TEXTE_REDIRECTION_PROFESSIONNEL: Final[str] = (
    "Je ne peux pas évaluer une situation personnelle. Pour cela, un "
    "professionnel de santé est la bonne interlocutrice ou le bon "
    "interlocuteur.\n\n"
    "En France, des centres experts et des filières de soins dédiés à "
    "l'endométriose existent dans plusieurs régions. Votre médecin traitant ou "
    "votre gynécologue peut vous orienter."
)

# `detresse_urgence` : sortie du mode documentaire.
TEXTE_DETRESSE_URGENCE: Final[str] = (
    "Ce que vous décrivez mérite l'attention d'une personne, pas d'un outil "
    "documentaire comme moi.\n\n"
    "Si votre douleur est intense, soudaine ou inhabituelle, contactez sans "
    "attendre un médecin, ou le 15 en cas d'urgence.\n\n"
    "Si vous traversez un moment difficile, en parler à votre médecin, à un "
    "proche ou à une association de patientes peut vraiment aider. Vous n'avez "
    "pas à gérer cela seule."
)

# `restriction_alimentaire` : refus d'aider à restreindre.
TEXTE_RESTRICTION_ALIMENTAIRE: Final[str] = (
    "Je ne peux pas vous aider à supprimer ou limiter des aliments.\n\n"
    "Les données actuelles ne permettent de recommander aucun régime "
    "spécifique dans l'endométriose, et un régime restrictif suivi sans "
    "accompagnement expose à des carences et à un rapport difficile à "
    "l'alimentation.\n\n"
    "Si vous souhaitez faire évoluer votre alimentation, un médecin ou un "
    "diététicien pourra vous accompagner en tenant compte de votre situation."
)

# disclaimer long : bandeau permanent + première ouverture du chatbot.
DISCLAIMER_CHATBOT_LONG: Final[str] = (
    "Projet étudiant / prototype de démonstration.\n"
    "Cet assistant répond uniquement à partir d'un petit ensemble de documents "
    "sélectionnés. Il ne consulte pas Internet et n'utilise pas de "
    "connaissances médicales au-delà de ces documents.\n"
    "Il ne pose aucun diagnostic, ne recommande aucun traitement et ne "
    "remplace en aucun cas l'avis d'un professionnel de santé.\n"
    "À ce jour, les recommandations internationales ne permettent de "
    "conseiller aucun régime alimentaire spécifique dans l'endométriose."
)

# disclaimer court : sous chaque réponse de fond uniquement.
DISCLAIMER_CHATBOT_COURT: Final[str] = (
    "Information générale issue d'un corpus documentaire limité. "
    "Ne remplace pas un avis médical."
)

# Correspondance texte <-> référence de section, pour la traçabilité et pour les tests de conformité.
TEXTES_PAR_REFERENCE: Final[dict[str, str]] = {
    "§7.1": TEXTE_OUT_OF_SCOPE,
    "§7.2": TEXTE_FOOD_SPECIFIC,
    "§7.3": TEXTE_FALLBACK,
    "§7.4": TEXTE_REDIRECTION_PROFESSIONNEL,
    "§7.5": TEXTE_DETRESSE_URGENCE,
    "§7.6": TEXTE_RESTRICTION_ALIMENTAIRE,
    "§7.7": DISCLAIMER_CHATBOT_LONG,
    "§7.8": DISCLAIMER_CHATBOT_COURT,
}

# Sections dont le texte NE DOIT PAS être accompagné du disclaimer court.
SECTIONS_SANS_DISCLAIMER: Final[frozenset[str]] = frozenset({"§7.5", "§7.6"})


def libelle_niveau(niveau: int) -> str:
    """Renvoie le libellé validé d'un niveau de score.

    Raises:
        KeyError: si le niveau sort de l'échelle [-2, +2].
    """
    return LIBELLES_NIVEAU[niveau]


def texte_valide(reference: str) -> str:
    """Renvoie le texte figé associé à une référence de section (« §7.5 »).

    Raises:
        KeyError: si la référence n'existe pas / ce qui signifie qu'on tente
            d'afficher un texte non validé.
    """
    return TEXTES_PAR_REFERENCE[reference]
