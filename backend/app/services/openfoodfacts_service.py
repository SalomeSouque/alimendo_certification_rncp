"""Récupération à la demande d'un produit Open Food Facts par son code-barre.

Open Food Facts n'est pas stocké en base :  le produit est demandé à l'API au moment
du scan (voir docs/specs_extraction.md, § 4).

Ce module fait trois choses :
  1. la requête HTTP vers l'API REST OFF (User-Agent exigé, timeout) ;
  2. le filtrage des champs utiles : nom, image, nutriments ;
  3. la conversion des nutriments dans les unités du référentiel de score.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import httpx

from app.core.config import get_openfoodfacts_settings

logger = logging.getLogger(__name__)

# Champs demandés à l'API : seulement ce qui sert à l'application
CHAMPS_UTILES = "code,product_name,product_name_fr,image_front_small_url,nutriments"

# Nom logique (= colonne du modèle Aliment) : (clés OFF à essayer dans l'ordre, unité du référentiel).
# OFF exprime toutes les valeurs <clé>_100g en grammes, on multiplie donc par FACTEUR_DEPUIS_G.
NUTRIMENTS_OFF: dict[str, tuple[tuple[str, ...], str]] = {
    "glucides":          (("carbohydrates",), "g"),
    "proteines":         (("proteins",), "g"),
    "lipides":           (("fat",), "g"),
    "graisses_saturees": (("saturated-fat",), "g"),
    "cholesterol":       (("cholesterol",), "mg"),
    "fer":               (("iron",), "mg"),
    "vitamine_b12":      (("vitamin-b12",), "µg"),
    "fibres":            (("fiber",), "g"),
    "omega3":            (("omega-3-fat",), "g"),
    "omega6":            (("omega-6-fat",), "g"),
    "vitamine_a":        (("vitamin-a",), "µg"),
    "beta_carotene":     (("beta-carotene",), "µg"),
    "vitamine_c":        (("vitamin-c",), "mg"),
    "vitamine_d":        (("vitamin-d",), "µg"),
    "vitamine_e":        (("vitamin-e",), "mg"),
    "vitamine_b6":       (("vitamin-b6",), "mg"),
    "folates":           (("vitamin-b9", "folates"), "µg"),
    "thiamine":          (("vitamin-b1",), "mg"),
    "riboflavine":       (("vitamin-b2",), "mg"),
    "niacine":           (("vitamin-pp",), "mg"),
    "magnesium":         (("magnesium",), "mg"),
    "selenium":          (("selenium",), "µg"),
    "zinc":              (("zinc",), "mg"),
}
FACTEUR_DEPUIS_G = {"g": 1.0, "mg": 1e3, "µg": 1e6}


class OpenFoodFactsIndisponibleError(RuntimeError):
    """Levée quand l'API OFF est injoignable ou répond en erreur (timeout, 429, 5xx)."""


@dataclass(frozen=True)
class ProduitOFF:
    """Produit OFF filtré et converti, prêt pour le calcul du score."""

    code_barre: str
    nom: str
    url_image: str | None
    energie: float | None
    profil: dict[str, float | None]     # les 23 paramètres, None = non renseigné


def lire_nombre(valeur: object) -> float | None:
    """Convertit une valeur OFF en nombre. Absente, non numérique ou négative -> None.

    None signifie « non renseigné » et n'est jamais remplacé par 0
    (même règle que pour CIQUAL dans le référentiel v1.0).
    """
    if valeur is None or isinstance(valeur, bool):
        return None
    try:
        nombre = float(str(valeur).replace(",", "."))
    except ValueError:
        return None
    if math.isnan(nombre) or math.isinf(nombre) or nombre < 0:
        return None
    return nombre


def convertir_nutriments(nutriments: dict) -> dict[str, float | None]:
    """Extrait les 23 paramètres du score, convertis dans les unités du référentiel.

    Exemple : vitamine C OFF = 0.012 (g/100 g) -> 12.0 (mg/100 g).
    Sans cette conversion, le score serait faux sans aucune erreur visible.
    """
    profil: dict[str, float | None] = {}
    for nom, (cles, unite) in NUTRIMENTS_OFF.items():
        valeur = None
        for cle in cles:
            valeur = lire_nombre(nutriments.get(f"{cle}_100g"))
            if valeur is not None:
                break
        profil[nom] = None if valeur is None else round(valeur * FACTEUR_DEPUIS_G[unite], 6)
    return profil


def filtrer_produit(code: str, produit: dict) -> ProduitOFF:
    """Garde uniquement les champs utiles d'un produit OFF."""
    nom = (produit.get("product_name_fr") or produit.get("product_name") or "").strip()
    nutriments = produit.get("nutriments") or {}
    return ProduitOFF(
        code_barre=code,
        nom=" ".join(nom.split()) or "Produit sans nom",
        url_image=produit.get("image_front_small_url") or None,
        energie=lire_nombre(nutriments.get("energy-kcal_100g")),
        profil=convertir_nutriments(nutriments),
    )


async def recuperer_produit(
    code: str, transport: httpx.AsyncBaseTransport | None = None
) -> ProduitOFF | None:
    """Interroge l'API OFF pour un code-barre.

    Args:
        code: code-barre EAN (chiffres uniquement, 8 à 14).
        transport: transport HTTP de remplacement, utilisé par les tests.

    Returns:
        Le produit filtré, ou None si OFF ne connaît pas ce code-barre.

    Raises:
        ValueError: code-barre mal formé (jamais envoyé à l'API).
        OpenFoodFactsIndisponibleError: API injoignable ou en erreur.
    """
    if not (code.isdigit() and 8 <= len(code) <= 14):
        raise ValueError("Le code-barre doit contenir 8 à 14 chiffres.")

    reglages = get_openfoodfacts_settings()
    url = f"{reglages.base_url}/api/v2/product/{code}"
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": reglages.user_agent},
            timeout=reglages.timeout_seconds,
            transport=transport,
        ) as client:
            reponse = await client.get(url, params={"fields": CHAMPS_UTILES})
    except httpx.HTTPError as erreur:
        logger.warning("OFF injoignable pour %s : %s", code, erreur)
        raise OpenFoodFactsIndisponibleError(str(erreur)) from erreur

    # 404 : produit inconnu d'OFF, ce n'est pas une panne
    if reponse.status_code == 404:
        return None
    if reponse.status_code != 200:
        logger.warning("OFF a répondu %s pour %s", reponse.status_code, code)
        raise OpenFoodFactsIndisponibleError(f"HTTP {reponse.status_code}")

    try:
        donnees = reponse.json()
    except ValueError as erreur:
        raise OpenFoodFactsIndisponibleError("réponse OFF illisible") from erreur

    # status 0 = produit introuvable, même avec un code HTTP 200
    if donnees.get("status") != 1 or not donnees.get("product"):
        return None
    logger.info("Produit OFF récupéré : %s", code)
    return filtrer_produit(code, donnees["product"])
