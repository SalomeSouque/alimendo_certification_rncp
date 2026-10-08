"""Tests de l'intégration du classifieur d'intention dans le backend.

But du fichier : vérifier que le service de routage utilise bien le modèle
entraîné, que le filet de sécurité garde la priorité sur lui, et que le
backend reste utilisable si le fichier du modèle manque.

Les tests de combinaison utilisent un faux modèle (`FauxModele`) : on teste
le code d'intégration, pas la qualité des prédictions. Le dernier test
charge le vrai `intent_classifier.pkl` et est ignoré tant qu'il n'est pas
déposé dans `app/ml/`.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pytest
import sklearn

from app.services import intent_service
from app.services.intent_safety_net import est_detresse
from app.services.intent_service import Intention, router

CLASSES = [i.value for i in Intention]


class FauxModele:
    """Imite un pipeline scikit-learn : renvoie toujours la même classe."""

    def __init__(self, classe: str, probabilite: float = 0.8, classes: list[str] | None = None):
        self.classes_ = np.array(classes or CLASSES)
        self._classe = classe
        self._probabilite = probabilite

    def predict_proba(self, questions):
        reste = (1 - self._probabilite) / (len(self.classes_) - 1)
        ligne = [self._probabilite if c == self._classe else reste for c in self.classes_]
        return np.array([ligne] * len(questions))


@pytest.fixture
def cache_vide():
    """Vide le cache du chargeur avant et après le test qui modifie le chemin."""
    intent_service.charger_modele.cache_clear()
    yield
    intent_service.charger_modele.cache_clear()


# Étage 1 : filet de sécurité (cas repris du notebook 02_classifieur)

@pytest.mark.parametrize(
    "message",
    [
        "Je suis complètement paralysée par les crampes, aidez-moi s'il vous plaît.",
        "SOS jpp de cette souffrance de malade",
        "jcraque complet avec ces douleurs h24",
        "bjr g une douleure insuportable o ba du ventre",
        "jss a bou de force avec cet maladi",
        "dsl de deranger mai je soufre tro koi faire",
        "je souffre le martyre",
    ],
)
def test_filet_detecte_la_detresse_meme_avec_des_fautes(message):
    assert est_detresse(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Est-ce que l'alimentation peut aider les douleurs ?",
        "quels aliments je dois éviter ?",
    ],
)
def test_filet_ne_se_declenche_pas_sur_une_question_neutre(message):
    assert est_detresse(message) is False


# Combinaison filet + modèle

def test_le_filet_prime_sur_le_modele(monkeypatch):
    """Même si le modèle répond in_scope, une détresse ne doit jamais aller au RAG."""
    monkeypatch.setattr(intent_service, "charger_modele", lambda: FauxModele("in_scope"))

    resultat = router("j'ai trop mal je n'en peux plus")

    assert resultat.intent is Intention.DETRESSE_URGENCE
    assert resultat.source == "safety_net"
    assert resultat.routage.llm is False


def test_le_modele_decide_hors_detresse(monkeypatch):
    """Sans détresse, c'est la prédiction du modèle qui est retenue, avec sa probabilité."""
    monkeypatch.setattr(
        intent_service, "charger_modele", lambda: FauxModele("food_specific", 0.8)
    )

    resultat = router("le saumon c'est bien ?")

    assert resultat.intent is Intention.FOOD_SPECIFIC
    assert resultat.source == "model"
    assert resultat.confidence == pytest.approx(0.8)
    assert resultat.routage.action == "REDIRECT_SCAN"


def test_repli_heuristique_sans_modele(monkeypatch):
    monkeypatch.setattr(intent_service, "charger_modele", lambda: None)

    resultat = router("qu'est-ce que le microbiote ?")

    assert resultat.source == "heuristique_provisoire"
    assert resultat.confidence == 0.0


# Chargement du fichier

def test_fichier_absent_donne_le_repli(monkeypatch, tmp_path, cache_vide):
    monkeypatch.setattr(intent_service, "CHEMIN_MODELE", tmp_path / "absent.pkl")

    assert intent_service.charger_modele() is None


def test_modele_aux_classes_inattendues_est_refuse(monkeypatch, tmp_path, cache_vide):
    """Un modèle qui ne connaît pas nos 5 classes produirait des intentions sans routage."""
    chemin = tmp_path / "mauvais.pkl"
    joblib.dump(FauxModele("a", classes=["a", "b"]), chemin)
    monkeypatch.setattr(intent_service, "CHEMIN_MODELE", chemin)

    assert intent_service.charger_modele() is None


# Vrai modèle livré

@pytest.mark.skipif(
    not intent_service.CHEMIN_MODELE.exists(),
    reason="intent_classifier.pkl pas encore déposé dans app/ml/",
)
def test_le_vrai_modele_se_charge_et_predit(cache_vide):
    meta = json.loads(
        (intent_service.CHEMIN_MODELE.parent / "intent_classifier_meta.json").read_text(
            encoding="utf-8"
        )
    )
    # Même version qu'à l'entraînement : sinon la désérialisation n'est pas garantie.
    assert sklearn.__version__ == meta["sklearn_version"]

    modele = intent_service.charger_modele()
    assert modele is not None

    resultat = router("Qu'est-ce que l'endométriose ?")
    assert resultat.source == "model"
    assert resultat.intent in set(Intention)
    assert 0.0 < resultat.confidence <= 1.0
