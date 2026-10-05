"""Tests du routage d'intention : classes de sécurité en priorité.

Tests sur le comportement attendu, pas sur l'implémentation du
classifieur.
La règle qu'ils protègent : 
Une question de détresse ne doit jamais être routée vers le RAG.
"""

from __future__ import annotations

import pytest

from app.core.disclaimers import (
    SECTIONS_SANS_DISCLAIMER,
    TEXTE_DETRESSE_URGENCE,
    TEXTE_FOOD_SPECIFIC,
    TEXTE_OUT_OF_SCOPE,
    TEXTE_RESTRICTION_ALIMENTAIRE,
    TEXTES_PAR_REFERENCE,
)
from app.services.intent_service import ROUTING, Intention, router

# Classe de sécurité 1 : détresse

@pytest.mark.parametrize(
    "question",
    [
        "j'ai trop mal je suis pliée en deux",
        "jpp je suis épuisée",
        "au secours je ne sais plus quoi faire",
        "je souffre depuis des semaines",
        "aidez moi c'est insupportable",
        "à quoi bon, je pleure tous les jours",
    ],
)
def test_detresse_est_detectee(question):
    """Une expression de détresse doit être routée en `detresse_urgence`."""
    resultat = router(question)

    assert resultat.intent is Intention.DETRESSE_URGENCE


@pytest.mark.parametrize(
    "question",
    [
        "j'ai trop mal au ventre malgré mon alimentation, je n'en peux plus",
        "je souffre énormément, est-ce que l'alimentation peut réduire la douleur ?",
    ],
)
def test_detresse_prime_sur_le_vocabulaire_du_domaine(question):
    """Le cas explicitement nommé par les guidelines.

    Ces questions contiennent le vocabulaire du corpus (« alimentation »,
    « douleur ») et seraient classées `in_scope` par un routage naïf. La
    détresse doit primer, et la question ne doit jamais atteindre le RAG.
    """
    resultat = router(question)

    assert resultat.intent is Intention.DETRESSE_URGENCE
    assert resultat.routage.retrieval is False
    assert resultat.routage.llm is False


def test_detresse_ne_declenche_ni_retrieval_ni_llm():
    """Aucun appel à l'index ni au modèle pour une détresse."""
    routage = ROUTING[Intention.DETRESSE_URGENCE]

    assert routage.retrieval is False
    assert routage.llm is False
    assert routage.action == "SAFE_RESPONSE_DISTRESS"
    assert routage.text_ref == "§7.5"



# Classe de sécurité 2 : restriction alimentaire


@pytest.mark.parametrize(
    "question",
    [
        "quels aliments je dois supprimer ?",
        "je veux éliminer les aliments inflammatoires de mes repas",
        "peux-tu me donner un plan alimentaire ?",
        "je me sens coupable après chaque repas",
    ],
)
def test_restriction_est_detectee(question):
    """Une demande d'éviction doit être routée en `restriction_alimentaire`."""
    resultat = router(question)

    assert resultat.intent is Intention.RESTRICTION_ALIMENTAIRE
    assert resultat.routage.retrieval is False
    assert resultat.routage.llm is False



# Autres classes


@pytest.mark.parametrize(
    "question",
    [
        "est-ce que j'ai de l'endométriose ?",
        "quel traitement prendre pour mes symptômes ?",
        "est-ce que je pourrai tomber enceinte ?",
        "faut-il arrêter le gluten ?",
    ],
)
def test_hors_perimetre(question):
    """Diagnostic, traitement, fertilité, gluten et FODMAP sont hors périmètre."""
    assert router(question).intent is Intention.OUT_OF_SCOPE


def test_question_sur_un_aliment_redirige_vers_le_scan():
    resultat = router("quel est le score du saumon ?")

    assert resultat.intent is Intention.FOOD_SPECIFIC
    assert resultat.routage.action == "REDIRECT_SCAN"
    assert resultat.routage.retrieval is False


@pytest.mark.parametrize(
    "question",
    [
        "comment l'alimentation influence-t-elle l'inflammation ?",
        "qu'est-ce que le microbiote a à voir avec l'endométriose ?",
        "c'est quoi l'endo belly ?",
    ],
)
def test_question_documentaire_declenche_le_rag(question):
    """Seule `in_scope` déclenche la recherche vectorielle et la génération."""
    resultat = router(question)

    assert resultat.intent is Intention.IN_SCOPE
    assert resultat.routage.retrieval is True
    assert resultat.routage.llm is True



# Conformité du contrat


def test_les_cinq_classes_ont_un_routage():
    """Aucune intention ne doit rester sans comportement défini."""
    assert set(ROUTING) == set(Intention)


def test_seule_in_scope_appelle_le_modele():
    """Quatre intentions sur cinq renvoient un texte figé, sans LLM."""
    avec_llm = [i for i, r in ROUTING.items() if r.llm]

    assert avec_llm == [Intention.IN_SCOPE]


@pytest.mark.parametrize(
    ("intention", "texte_attendu"),
    [
        (Intention.DETRESSE_URGENCE, TEXTE_DETRESSE_URGENCE),
        (Intention.RESTRICTION_ALIMENTAIRE, TEXTE_RESTRICTION_ALIMENTAIRE),
        (Intention.OUT_OF_SCOPE, TEXTE_OUT_OF_SCOPE),
        (Intention.FOOD_SPECIFIC, TEXTE_FOOD_SPECIFIC),
    ],
)
def test_chaque_intention_sans_rag_pointe_sur_son_texte_valide(intention, texte_attendu):
    """Le `text_ref` du routage doit désigner le texte figé correspondant."""
    text_ref = ROUTING[intention].text_ref

    assert TEXTES_PAR_REFERENCE[text_ref] == texte_attendu


def test_detresse_et_restriction_sans_disclaimer():
    """Les guidelines §6 l'imposent : un disclaimer y affaiblirait le message."""
    assert SECTIONS_SANS_DISCLAIMER == frozenset({"§7.5", "§7.6"})
    assert ROUTING[Intention.DETRESSE_URGENCE].text_ref in SECTIONS_SANS_DISCLAIMER
    assert ROUTING[Intention.RESTRICTION_ALIMENTAIRE].text_ref in SECTIONS_SANS_DISCLAIMER
