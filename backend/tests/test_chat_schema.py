"""Tests unitaires du nettoyage de la question envoyée au chatbot.

But du fichier : prouver que la question est validée et nettoyée avant
d'atteindre le classifieur d'intention et le prompt Mistral (critères
C9-CR3 et C17-CR8, OWASP API8 et A03).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_question_normale_inchangee():
    question = "Qu'est-ce que l'endométriose ?"

    assert ChatRequest(question=question).question == question


def test_espaces_autour_retires():
    requete = ChatRequest(question="   Le curcuma est-il étudié ?  \n")

    assert requete.question == "Le curcuma est-il étudié ?"


def test_caracteres_de_controle_retires():
    requete = ChatRequest(question="Le gluten\x00 et\x1b[31m l'inflammation\x7f ?")

    assert requete.question == "Le gluten et[31m l'inflammation ?"


def test_saut_de_ligne_interne_conserve():
    requete = ChatRequest(question="Première ligne\nDeuxième ligne")

    assert requete.question == "Première ligne\nDeuxième ligne"


@pytest.mark.parametrize("question", ["     ", "\x00\x00\x00\x00", "  a\x00 "])
def test_question_vide_apres_nettoyage_refusee(question):
    with pytest.raises(ValidationError):
        ChatRequest(question=question)


def test_question_trop_longue_refusee():
    with pytest.raises(ValidationError):
        ChatRequest(question="a" * 1001)


def test_question_non_textuelle_refusee():
    with pytest.raises(ValidationError):
        ChatRequest(question=123)