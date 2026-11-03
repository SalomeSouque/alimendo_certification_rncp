"""Routes des features IA : protégées par JWT.

Ce sont les deux seules features derrière un mur de connexion.

"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user, verify_api_key
from app.db.session import get_session
from app.schemas.chat import ChatRequest, ChatResponse, VisionResponse
from app.services import (
    chroma_service,
    embedding_service,
    llm_mistral,
    rag_service,
    vision_service,
)

router = APIRouter(
    prefix="/ai",
    tags=["intelligence artificielle"],
    dependencies=[Depends(verify_api_key), Depends(get_current_user)],
    responses={
        401: {"description": "Jeton absent, invalide ou expiré, ou clé d'API invalide."},
        503: {"description": "Service IA (index, embeddings, Mistral ou Ollama) indisponible."},
    },
)

# Taille maximale acceptée pour une photo d'aliment (5 Mo).
TAILLE_MAX_IMAGE = 5 * 1024 * 1024

# Types d'images acceptés.
TYPES_IMAGE_AUTORISES = frozenset({"image/jpeg", "image/png", "image/webp"})


@router.post("/chat", response_model=ChatResponse, summary="Poser une question au chatbot")
async def chat(payload: ChatRequest) -> ChatResponse:
    """Répond à une question à partir du corpus documentaire.

    Raises:
        HTTPException: 503 si l'index vectoriel, le modèle d'embeddings ou le
            service de génération est indisponible. On renvoie un message
            explicite plutôt qu'une 500 brute.
    """
    try:
        return await rag_service.repondre(payload.question)
    except chroma_service.IndexIndisponibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base documentaire est temporairement indisponible.",
        ) from exc
    except embedding_service.EmbeddingIndisponibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de recherche documentaire est temporairement indisponible.",
        ) from exc
    except llm_mistral.LLMIndisponibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de réponse est temporairement indisponible, réessayez dans un instant.",
        ) from exc


@router.post(
    "/vision",
    response_model=VisionResponse,
    summary="Identifier un aliment sur une photo",
    responses={
        413: {"description": "Image de plus de 5 Mo."},
        415: {"description": "Format non supporté (JPEG, PNG ou WebP attendu)."},
        422: {"description": "Fichier illisible : ce n'est pas une image valide."},
    },
)
async def vision(
    session: Annotated[AsyncSession, Depends(get_session)],
    utilisateur: Annotated[CurrentUser, Depends(get_current_user)],
    image: Annotated[UploadFile, File(description="Photo d'un aliment brut")],
) -> VisionResponse:
    """Identifie un aliment brut à partir d'une photo et renvoie son score.

    La réponse est toujours un 200 quand le VLM a répondu, même si aucun
    aliment n'est reconnu : `statut` et `message` décrivent alors l'issue.
    L'image n'est jamais stockée.

    Raises:
        HTTPException: 415 si le type de fichier n'est pas une image autorisée,
            413 si l'image dépasse la taille maximale,
            422 si le fichier n'est pas une image lisible,
            503 si Ollama est injoignable, trop lent ou en erreur.
    """
    if image.content_type not in TYPES_IMAGE_AUTORISES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format d'image non supporté. Utilisez JPEG, PNG ou WebP.",
        )

    contenu = await image.read()
    if len(contenu) > TAILLE_MAX_IMAGE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image trop volumineuse (5 Mo maximum).",
        )

    try:
        return await vision_service.analyser_image(session, contenu)
    except vision_service.ImageInvalideError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Le fichier envoyé n'est pas une image lisible.",
        ) from exc
    except vision_service.VLMIndisponibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Le service de reconnaissance photo est temporairement "
                "indisponible, essayez la recherche textuelle."
            ),
        ) from exc