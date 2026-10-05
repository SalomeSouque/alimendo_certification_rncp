"""Point d'entrée de l'API Alimendo.

Lancement en développement :
    uv run uvicorn app.main:app --reload --port 8000
Documentation interactive : http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_app_settings
from app.core.logging_config import configurer_logging
from app.db.session import dispose_engine, init_engine
from app.domain.score import referentiel_est_pret
from app.routers import ai, auth, health, score, search

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le démarrage et l'arrêt propres de l'application.

    Au démarrage : création du pool de connexions et vérification que le
    référentiel de score est exploitable.
    """
    settings = get_app_settings()
    configurer_logging(settings.log_level)
    logger.info("démarrage de l'API Alimendo (environnement=%s)", settings.environment)

    init_engine()

    if not referentiel_est_pret():
        logger.warning(
            "Les repères de normalisation du score sont absents ou incomplets : "
            "les routes de score renverront une erreur tant que "
            "app/domain/score/reperes_v1_0.json n'est pas renseigné."
        )

    yield

    logger.info("arrêt de l'API Alimendo")
    await dispose_engine()


def creer_application() -> FastAPI:
    """Construit l'application FastAPI.

    Passer par une fabrique plutôt que par un objet global facilite les tests :
    on peut instancier une application neuve par scénario.
    """
    settings = get_app_settings()

    application = FastAPI(
        title="Alimendo : API",
        description=(
            "API du projet étudiant Alimendo. Score inflammatoire des aliments "
            "et assistant documentaire sur l'endométriose.\n\n"
            "Projet étudiant à but pédagogique, sans expertise médicale."
        ),
        version="0.1.0",
        lifespan=lifespan,
        # Documentation désactivée hors développement : elle expose la cartographie complète de l'API.
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
    )

    # CORS restreint aux origines déclarées : le frontend appelle l'API depuis
    # un autre port (et un autre domaine en production).
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(search.router)
    application.include_router(score.router)
    application.include_router(ai.router)

    return application


app = creer_application()
