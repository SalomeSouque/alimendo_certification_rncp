"""Tests de validation du service Mistral (critères C8-CR1, CR2, CR3).

Le script appelle le vrai service, avec la configuration du projet (.env), sur
quatre cas, puis écrit un tableau de résultats en Markdown :

1. question_connue : la réponse s'appuie sur l'extrait fourni ;
2. hors_extraits : question sans réponse dans les extraits, le modèle doit
   refuser au lieu de répondre depuis ses connaissances générales ;
3. cle_invalide : Mistral refuse l'accès, l'application lève une erreur propre ;
4. service_injoignable : Mistral ne répond pas, même comportement.

Les cas 3 et 4 ne consomment aucun token.
Ce script ne teste pas le chatbot complet (routage d'intention, ChromaDB) :
ces étapes sont couvertes par les tests du backend.

Usage (depuis la racine du dépôt, MISTRAL_API_KEY renseignée dans .env) :
    uv run python scripts/validate_mistral.py

Codes de sortie : 0 = tous les cas conformes, 1 = au moins un cas non conforme,
2 = configuration manquante.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Le script réutilise le vrai client du backend, sans le recopier.
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import ConfigurationError, get_mistral_settings
from app.core.logging_config import configurer_logging
from app.services.llm_mistral import LLMIndisponibleError, generer_reponse

SORTIE_PAR_DEFAUT = ROOT / "docs" / "services" / "resultats_validation_mistral.md"

# Extrait volontairement neutre (fait nutritionnel, pas de conseil de santé).
EXTRAIT = (
    "Titre : Fiche de test Alimendo. "
    "Les oméga-3 sont des acides gras polyinsaturés. "
    "On en trouve notamment dans les poissons gras comme la sardine et le maquereau."
)


@dataclass
class Resultat:
    """Une ligne du tableau de résultats."""

    cas: str
    attendu: str
    obtenu: str
    conforme: bool
    latence_ms: int


async def _cas_reponse(cas: str, attendu: str, question: str, mot: str, present: bool) -> Resultat:
    """Pose une question au service et vérifie la présence (ou l'absence) d'un mot."""
    debut = time.perf_counter()
    try:
        reponse = await generer_reponse(question, [EXTRAIT])
        conforme = (mot in reponse.lower()) == present
    except LLMIndisponibleError as exc:
        reponse, conforme = f"Service indisponible : {exc}", False
    latence = round((time.perf_counter() - debut) * 1000)
    return Resultat(cas, attendu, reponse, conforme, latence)


async def _cas_erreur(cas: str, attendu: str, variable: str, valeur: str) -> Resultat:
    """Rejoue un appel avec une variable d'environnement modifiée, puis la restaure."""
    ancienne = os.environ.get(variable)
    os.environ[variable] = valeur
    get_mistral_settings.cache_clear()
    debut = time.perf_counter()
    try:
        await generer_reponse("Question de test", [EXTRAIT])
        obtenu, conforme = "Réponse reçue alors qu'une erreur était attendue", False
    except LLMIndisponibleError as exc:
        obtenu, conforme = f"LLMIndisponibleError : {exc}", True
    finally:
        latence = round((time.perf_counter() - debut) * 1000)
        if ancienne is None:
            os.environ.pop(variable, None)
        else:
            os.environ[variable] = ancienne
        get_mistral_settings.cache_clear()
    return Resultat(cas, attendu, obtenu, conforme, latence)


def _en_markdown(resultats: list[Resultat], modele: str) -> str:
    """Construit le tableau de résultats (une ligne par cas)."""
    lignes = [
        "# Résultats des tests de validation du service Mistral",
        "",
        f"Date d'exécution : {date.today().isoformat()}. Modèle : `{modele}`.",
        "Généré par `scripts/validate_mistral.py`. Procédure : `docs/services/mistral.md`.",
        "",
        "| Cas | Attendu | Obtenu | Conforme | Latence (ms) |",
        "|---|---|---|---|---|",
    ]
    for r in resultats:
        obtenu = " ".join(r.obtenu.split()).replace("|", "/")
        if len(obtenu) > 300:
            obtenu = obtenu[:300] + "..."
        conforme = "Oui" if r.conforme else "Non"
        lignes.append(f"| {r.cas} | {r.attendu} | {obtenu} | {conforme} | {r.latence_ms} |")
    lignes.append("")
    return "\n".join(lignes)


async def executer() -> list[Resultat]:
    """Lance les quatre cas dans l'ordre."""
    return [
        await _cas_reponse(
            "question_connue",
            "Réponse tirée de l'extrait (cite la sardine)",
            "Dans quels aliments trouve-t-on des oméga-3 ?",
            mot="sardine",
            present=True,
        ),
        await _cas_reponse(
            "hors_extraits",
            "Refus de répondre, pas de « Canberra » (connaissance générale)",
            "Quelle est la capitale de l'Australie ?",
            mot="canberra",
            present=False,
        ),
        await _cas_erreur(
            "cle_invalide",
            "Accès refusé par Mistral (401), erreur propre côté application",
            "MISTRAL_API_KEY",
            "cle-volontairement-invalide",
        ),
        await _cas_erreur(
            "service_injoignable",
            "Aucune réponse du service, erreur propre côté application",
            "MISTRAL_BASE_URL",
            "http://127.0.0.1:9",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Tests de validation du service Mistral.")
    parser.add_argument("--sortie", type=Path, default=SORTIE_PAR_DEFAUT, help="Fichier Markdown produit.")
    args = parser.parse_args()

    # Mêmes logs que l'API : on voit statut, latence et tokens de chaque appel.
    configurer_logging("INFO")

    try:
        modele = get_mistral_settings().model
    except ConfigurationError as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        sys.exit(2)

    resultats = asyncio.run(executer())
    rapport = _en_markdown(resultats, modele)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(rapport, encoding="utf-8")
    print(rapport)
    print(f"Résultats écrits dans {args.sortie}")

    sys.exit(0 if all(r.conforme for r in resultats) else 1)


if __name__ == "__main__":
    main()