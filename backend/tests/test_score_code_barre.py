"""Tests d'intégration de GET /score/code-barre/{code} (critères C5-CR5, C9-CR5).

Open Food Facts est simulé : on remplace `recuperer_produit` pour ne pas
dépendre du réseau ni de la limite de 15 requêtes par minute d'OFF.
La conversion des nutriments est déjà testée dans test_openfoodfacts_service.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.core.disclaimers import ATTRIBUTION_OPEN_FOOD_FACTS, DISCLAIMER_SCORE
from app.services import openfoodfacts_service
from app.services.openfoodfacts_service import (
    NUTRIMENTS_OFF,
    OpenFoodFactsIndisponibleError,
    ProduitOFF,
)

CODE = "3017620422003"


def _faux_produit() -> ProduitOFF:
    """Produit OFF sans micronutriments : cas le plus fréquent (score indisponible)."""
    return ProduitOFF(
        code_barre=CODE,
        nom="Pâte à tartiner",
        url_image="https://images.openfoodfacts.org/exemple.jpg",
        energie=539.0,
        profil=dict.fromkeys(NUTRIMENTS_OFF),
    )


def test_code_barre_connu_renvoie_le_detail(client_api, monkeypatch):
    faux_off = AsyncMock(return_value=_faux_produit())
    monkeypatch.setattr(openfoodfacts_service, "recuperer_produit", faux_off)

    reponse = client_api.get(f"/score/code-barre/{CODE}")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["aliment"]["source"] == "OFF"
    assert corps["aliment"]["id_aliment"] is None
    assert corps["score"]["disponible"] is False
    assert corps["alternatives"] == []
    assert corps["disclaimer"] == DISCLAIMER_SCORE
    assert ATTRIBUTION_OPEN_FOOD_FACTS in corps["citation_source"]
    faux_off.assert_awaited_once_with(CODE)


def test_code_barre_inconnu_renvoie_404(client_api, monkeypatch):
    monkeypatch.setattr(
        openfoodfacts_service, "recuperer_produit", AsyncMock(return_value=None)
    )

    reponse = client_api.get(f"/score/code-barre/{CODE}")

    assert reponse.status_code == 404


def test_off_indisponible_renvoie_503(client_api, monkeypatch):
    monkeypatch.setattr(
        openfoodfacts_service,
        "recuperer_produit",
        AsyncMock(side_effect=OpenFoodFactsIndisponibleError("timeout")),
    )

    reponse = client_api.get(f"/score/code-barre/{CODE}")

    assert reponse.status_code == 503


def test_code_barre_mal_forme_refuse_sans_appeler_off(client_api, monkeypatch):
    """Lettres dans le code : 422 par la validation, OFF n'est jamais appelé."""
    faux_off = AsyncMock()
    monkeypatch.setattr(openfoodfacts_service, "recuperer_produit", faux_off)

    reponse = client_api.get("/score/code-barre/12345abc")

    assert reponse.status_code == 422
    faux_off.assert_not_awaited()
