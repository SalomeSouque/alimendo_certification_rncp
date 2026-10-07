"""Tests du service Open Food Facts, sans réseau.

httpx.MockTransport remplace l'API : chaque test décide de la réponse renvoyée.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.services.openfoodfacts_service import (
    NUTRIMENTS_OFF,
    OpenFoodFactsIndisponibleError,
    convertir_nutriments,
    lire_nombre,
    recuperer_produit,
)

CODE = "3017620422003"


def transport_qui_repond(status: int, corps: dict | None = None) -> httpx.MockTransport:
    """Faux transport HTTP qui renvoie toujours la même réponse."""
    return httpx.MockTransport(lambda requete: httpx.Response(status, json=corps or {}))


def recuperer(transport: httpx.MockTransport):
    """Lance la fonction asynchrone depuis un test synchrone."""
    return asyncio.run(recuperer_produit(CODE, transport=transport))


# Parsing et conversion
@pytest.mark.parametrize("brute, attendu", [
    (12.5, 12.5), ("12,5", 12.5), (0, 0.0), (None, None), ("", None), ("abc", None), (-1, None),
])
def test_lire_nombre(brute, attendu):
    assert lire_nombre(brute) == attendu


def test_conversion_des_unites_depuis_les_grammes():
    profil = convertir_nutriments({
        "proteins_100g": 4.2,          # g -> g
        "vitamin-c_100g": 0.012,       # g -> 12 mg
        "vitamin-d_100g": 0.0000025,   # g -> 2.5 µg
    })
    assert profil["proteines"] == 4.2
    assert profil["vitamine_c"] == pytest.approx(12.0)
    assert profil["vitamine_d"] == pytest.approx(2.5)


def test_nutriment_absent_reste_none_jamais_zero():
    profil = convertir_nutriments({})
    assert set(profil) == set(NUTRIMENTS_OFF)
    assert all(v is None for v in profil.values())


def test_folates_cle_de_secours():
    assert convertir_nutriments({"folates_100g": 0.00002})["folates"] == pytest.approx(20.0)


# Appel de l'API
def test_produit_trouve_et_filtre():
    produit = {"product_name": "Spread", "product_name_fr": "Pâte à tartiner",
               "image_front_small_url": "https://img/1.jpg",
               "nutriments": {"energy-kcal_100g": 539, "fat_100g": 30.9, "iron_100g": 0.0042}}
    resultat = recuperer(transport_qui_repond(200, {"status": 1, "product": produit}))
    assert resultat.nom == "Pâte à tartiner"
    assert resultat.energie == 539
    assert resultat.profil["lipides"] == 30.9
    assert resultat.profil["fer"] == pytest.approx(4.2)


@pytest.mark.parametrize("status, corps", [(404, {"status": 0}), (200, {"status": 0})])
def test_produit_inconnu_renvoie_none(status, corps):
    assert recuperer(transport_qui_repond(status, corps)) is None


@pytest.mark.parametrize("status", [429, 500, 503])
def test_api_en_erreur(status):
    with pytest.raises(OpenFoodFactsIndisponibleError):
        recuperer(transport_qui_repond(status))


def test_api_injoignable():
    def panne(requete):
        raise httpx.ConnectError("hors ligne")
    with pytest.raises(OpenFoodFactsIndisponibleError):
        recuperer(httpx.MockTransport(panne))


def test_user_agent_et_champs_envoyes():
    vues = []

    def espion(requete: httpx.Request) -> httpx.Response:
        vues.append(requete)
        return httpx.Response(404)
    recuperer(httpx.MockTransport(espion))
    assert vues[0].headers["User-Agent"].startswith("Alimendo")
    assert "nutriments" in vues[0].url.params["fields"]


@pytest.mark.parametrize("code", ["123", "abcdefgh", "12345678/../x", "1" * 15])
def test_code_barre_invalide_refuse_avant_appel(code):
    with pytest.raises(ValueError):
        asyncio.run(recuperer_produit(code, transport=transport_qui_repond(200)))
