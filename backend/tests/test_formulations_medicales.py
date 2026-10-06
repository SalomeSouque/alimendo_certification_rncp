"""Conformité des formulations médicales.

Ces tests vérifient règle de conformité : toute
formulation à caractère médical ou nutritionnel affichée ne doit jamais glisser vers un conseil de santé.

- tranche de score : le service traduit chaque niveau par le libellé validé,
  purement descriptif, sans vocabulaire moral ;
- disclaimer : les disclaimers du score et du chatbot sont les textes figés
  exacts, et les deux textes de sécurité n'en portent aucun ;
- ucun mot prescriptif : les formulations du score ne contiennent aucun
  verbe de prescription, de promesse d'effet, de jugement moral ni de posologie.

"""

from __future__ import annotations

import re

import pytest

from app.core.disclaimers import (
    DISCLAIMER_CHATBOT_COURT,
    DISCLAIMER_SCORE,
    LIBELLE_ALTERNATIVES,
    LIBELLES_NIVEAU,
    MESSAGE_COMPLETUDE_INSUFFISANTE,
    MESSAGE_HORS_PERIMETRE,
    SECTIONS_SANS_DISCLAIMER,
    TEXTES_PAR_REFERENCE,
)
from app.domain.score import CauseIndisponibilite, ResultatScore
from app.domain.score.badges import LIBELLES as LIBELLES_BADGES
from app.services.score_service import vers_schema

# 1. Tranche de score -> libellé validé

def test_chaque_niveau_recoit_le_libelle_valide():
    """Le service attache à chaque niveau le libellé figé de l'échelle.

    C'est la garantie qu'aucun libellé de tranche n'est inventé côté service :
    il provient toujours de LIBELLES_NIVEAU, lui-même transcrit du référentiel.
    """
    libelles_attendus = {
        2: "Fortement pro-inflammatoire",
        1: "Modérément pro-inflammatoire",
        0: "Neutre",
        -1: "Modérément anti-inflammatoire",
        -2: "Fortement anti-inflammatoire",
    }
    assert LIBELLES_NIVEAU == libelles_attendus

    for niveau, libelle in libelles_attendus.items():
        resultat = ResultatScore(
            disponible=True,
            niveau=niveau,
            score_brut=0.0,
            completude=0.8,
            parametres_utilises=18,
        )
        out = vers_schema(resultat)
        assert out.niveau == niveau
        assert out.libelle == libelle


def test_score_indisponible_affiche_un_message_valide_sans_libelle():
    """Quand le score est indisponible, pas de libellé de tranche, et le
    message affiché est l'une des deux formulations validées."""
    resultat = ResultatScore(
        disponible=False,
        niveau=None,
        score_brut=None,
        completude=0.2,
        parametres_utilises=4,
        causes=(CauseIndisponibilite.COMPLETUDE_INSUFFISANTE,),
    )
    out = vers_schema(resultat)

    assert out.niveau is None
    assert out.libelle is None
    assert out.message in {MESSAGE_COMPLETUDE_INSUFFISANTE, MESSAGE_HORS_PERIMETRE}



# 2. Disclaimers : textes figés exacts


def test_disclaimers_sont_les_textes_figes_exacts():
    """Les disclaimers affichés sont les formulations validées.
    """
    assert DISCLAIMER_SCORE == (
        "Score indicatif, basé sur le profil nutritionnel de l'aliment. "
        "Il ne constitue pas un avis médical et ne prédit pas l'effet de cet "
        "aliment sur vos symptômes."
    )
    assert DISCLAIMER_CHATBOT_COURT == (
        "Information générale issue d'un corpus documentaire limité. "
        "Ne remplace pas un avis médical."
    )
    # Les huit sections figées du chatbot sont bien présentes et non vides.
    assert set(TEXTES_PAR_REFERENCE) == {f"§7.{i}" for i in range(1, 9)}
    assert all(texte.strip() for texte in TEXTES_PAR_REFERENCE.values())


# 3. Les deux textes de sécurité ne portent pas de disclaimer

def test_seules_les_sections_de_securite_sont_sans_disclaimer():
    """détresse et restriction sont les seules sans disclaimer.
    """
    assert SECTIONS_SANS_DISCLAIMER == frozenset({"§7.5", "§7.6"})
    # Les sections de contenu documentaire ne sont pas dans l'ensemble.
    for reference in ("§7.1", "§7.2", "§7.3", "§7.4"):
        assert reference not in SECTIONS_SANS_DISCLAIMER



# 4. Aucun mot prescriptif dans les formulations du score


# Formulations affirmatives affichées côté score (libellés, messages, badges).
FORMULATIONS_SCORE: list[str] = [
    *LIBELLES_NIVEAU.values(),
    LIBELLE_ALTERNATIVES,
    DISCLAIMER_SCORE,
    MESSAGE_COMPLETUDE_INSUFFISANTE,
    MESSAGE_HORS_PERIMETRE,
    *LIBELLES_BADGES.values(),
]

# Vocabulaire proscrit : promesse d'effet, prescription, jugement moral,
# posologie. Les motifs sont ancrés sur des limites de mots pour ne pas
# heurter des termes autorisés (ex. « anti-inflammatoire » reste permis).
MOTS_PRESCRIPTIFS: list[str] = [
    r"gu[ée]ri\w*",
    r"soigne\w*",
    r"soulage\w*",
    r"anti-?douleur",
    r"r[ée]duit l'inflammation",
    r"mangez", r"[ée]vitez", r"supprimez", r"consommez", r"bannissez",
    r"privil[ée]giez", r"limitez",
    r"il faut", r"vous devez",
    r"malsain\w*", r"sain\b", r"saine\b",
    r"posologie", r"doses?\b", r"par jour", r"portion\w*",
]


@pytest.mark.parametrize("texte", FORMULATIONS_SCORE)
def test_aucun_mot_prescriptif_dans_les_formulations_score(texte: str):
    """Aucune formulation du score ne prescrit, ne promet un effet, ne juge."""
    minuscule = texte.lower()
    trouves = [
        motif for motif in MOTS_PRESCRIPTIFS
        if re.search(motif, minuscule)
    ]
    assert not trouves, f"Vocabulaire proscrit dans {texte!r} : {trouves}"
