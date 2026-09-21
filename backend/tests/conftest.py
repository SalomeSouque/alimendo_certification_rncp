"""Fixtures partagées par les tests.

"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("POSTGRES_USER", "alimendo_test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "alimendo_test")
os.environ.setdefault("JWT_SECRET_KEY", "secret-de-test-non-utilise-en-production")
os.environ.setdefault("MISTRAL_API_KEY", "cle-de-test")
# bcrypt à 4 tours : le minimum autorisé, pour que la suite de tests reste rapide.
os.environ.setdefault("BCRYPT_ROUNDS", "4")

from app.domain.score.referentiel_v1 import COEFS, RepereParametre


@pytest.fixture
def reperes_synthetiques() -> dict[str, RepereParametre]:
    """Repères de normalisation artificiels, identiques pour tous les paramètres.

    med=10, p10=0, p90=20 : une teneur de 20 donne une normalisation de +1,
    une teneur de 0 donne −1, une teneur de 10 donne 0, Rendant les
    résultats calculables à la main.

    """
    return {nom: RepereParametre(med=10.0, p10=0.0, p90=20.0) for nom in COEFS}


@pytest.fixture
def patch_reperes(monkeypatch, reperes_synthetiques):
    """Remplace les repères réels par les repères synthétiques."""
    monkeypatch.setattr(
        "app.domain.score.calcul.get_reperes", lambda: reperes_synthetiques
    )
    return reperes_synthetiques
