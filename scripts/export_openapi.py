"""Exporte la documentation OpenAPI de l'API dans docs/openapi.json (critère C5-CR3).

FastAPI génère la spécification OpenAPI à partir du code (routes, schémas
Pydantic, codes d'erreur). Ce script l'écrit dans un fichier versionné, lisible
sans lancer l'API (Swagger Editor, annexe du rapport).

Aucune base ni service externe n'est nécessaire : la spécification est
construite sans démarrer l'application.

Usage (depuis backend/, pour utiliser l'environnement du backend) :
    uv run python ../scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Le script réutilise l'application du backend, sans la recopier.
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app

FICHIER_SORTIE = ROOT / "docs" / "openapi.json"


def main() -> None:
    """Génère la spécification et l'écrit dans docs/openapi.json."""
    specification = app.openapi()
    FICHIER_SORTIE.write_text(
        json.dumps(specification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    nb_routes = sum(len(methodes) for methodes in specification["paths"].values())
    print(f"OpenAPI {specification['openapi']} : {nb_routes} routes -> {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()
