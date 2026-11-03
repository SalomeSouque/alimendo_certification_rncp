"""Reconnaissance d'aliment par photo via le VLM (Qwen3-VL servi par Ollama).

Chaîne :

1. l'image est vérifiée, redressée, débarrassée de ses métadonnées (EXIF, GPS)
   et réduite à `VLM_IMAGE_MAX_PX` de côté, puis réencodée en JPEG ;
2. elle est envoyée à Ollama avec un schéma JSON imposé (sorties structurées) :
   le modèle classe d'abord la photo (`contenu`), puis nomme l'aliment (`label`) ;
3. seul un `aliment_unique`, nommé, au-dessus du seuil de confiance, est
   rapproché d'un aliment CIQUAL par la recherche existante ;
4. le score est calculé par le service de score existant ;
5. l'inférence est journalisée dans `log_vlm`, sans jamais stocker l'image.

Paramétrage et mesures qui le justifient : `docs/services/ollama.md`.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import time
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_ollama_settings
from app.core.disclaimers import (
    CITATION_SOURCE_COURTE,
    DISCLAIMER_SCORE,
    LIBELLE_ALTERNATIVES,
    MENTION_PROJET_ETUDIANT,
)
from app.db.models import STATUT_ECHEC, STATUT_NON_RAPPROCHE, STATUT_RECONNU, Aliment
from app.repositories import aliment_repository, log_vlm_repository
from app.schemas.aliment import AlimentDetail, AlimentResume
from app.schemas.chat import VisionResponse
from app.services import alternative_service, score_service

logger = logging.getLogger(__name__)


class VLMIndisponibleError(RuntimeError):
    """Levée quand Ollama est injoignable, trop lent ou répond en erreur."""


class ImageInvalideError(ValueError):
    """Levée quand le fichier reçu n'est pas une image lisible."""


# Classement de la photo imposé au modèle (champ `contenu`).
CONTENU_ALIMENT_UNIQUE = "aliment_unique"
CONTENU_PLUSIEURS_ALIMENTS = "plusieurs_aliments"
CONTENU_PLAT_PREPARE = "plat_prepare"
CONTENU_AUCUN_ALIMENT = "aucun_aliment"
CONTENUS_VALIDES: tuple[str, ...] = (
    CONTENU_ALIMENT_UNIQUE,
    CONTENU_PLUSIEURS_ALIMENTS,
    CONTENU_PLAT_PREPARE,
    CONTENU_AUCUN_ALIMENT,
)

# Prompt v2, validé sur le jeu de photos de contrôle (ollama.md § 8). La v1
# (label + confiance seuls) nommait un assortiment de légumes et un plat cuisiné
# avec 0,95 de confiance : la v2 fait d'abord classer la photo.
PROMPT_SYSTEME = (
    "Tu identifies un aliment brut sur une photo, pour une application de nutrition. "
    "Tu réponds uniquement avec l'objet JSON demandé, sans aucun autre texte."
)

PROMPT_UTILISATEUR = """Décris le contenu de cette photo selon ces règles.
- contenu : choisis exactement une valeur.
  "aliment_unique" : un seul aliment brut, ou plusieurs exemplaires du même aliment (trois pommes, une grappe de raisin).
  "plusieurs_aliments" : des aliments bruts différents, sans qu'un seul occupe l'essentiel de la photo.
  "plat_prepare" : un plat cuisiné, une assiette composée, un produit transformé.
  "aucun_aliment" : pas d'aliment visible.
- label : si contenu vaut "aliment_unique", nom générique de l'aliment en français, au singulier, en minuscules, sans marque ni préparation (exemples : "tomate", "pomme", "brocoli", "saumon", "lentille"). Sinon, chaîne vide "".
- confidence : ta confiance dans ta réponse, entre 0 et 1."""

# Schéma imposé à la génération. L'ordre des propriétés compte : le modèle
# écrit `contenu` avant `label`.
SCHEMA_REPONSE: dict[str, object] = {
    "type": "object",
    "properties": {
        "contenu": {"type": "string", "enum": list(CONTENUS_VALIDES)},
        "label": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["contenu", "label", "confidence"],
}

# Qualité du JPEG réencodé : bon compromis netteté / poids pour le VLM.
QUALITE_JPEG = 90

# Nombre de candidats remontés par la recherche floue avant le choix final.
NOMBRE_CANDIDATS = 20

# Messages affichés quand aucun score ne peut être proposé.
MESSAGES_NON_RECONNU: dict[str, str] = {
    CONTENU_PLUSIEURS_ALIMENTS: (
        "Plusieurs aliments sont visibles sur la photo. Photographiez un seul "
        "aliment, ou utilisez la recherche par nom."
    ),
    CONTENU_PLAT_PREPARE: (
        "Cette photo semble montrer un plat préparé. La reconnaissance photo "
        "fonctionne avec un aliment brut : utilisez la recherche par nom."
    ),
    CONTENU_AUCUN_ALIMENT: (
        "Aucun aliment n'a été reconnu sur cette photo. Essayez avec une photo "
        "plus nette, ou utilisez la recherche par nom."
    ),
}
MESSAGE_INCERTAIN = (
    "L'aliment n'a pas pu être identifié avec assez de certitude. Essayez avec "
    "une autre photo, ou utilisez la recherche par nom."
)
MESSAGE_ABSENT_DE_LA_BASE = (
    "« {label} » a été reconnu, mais cet aliment n'est pas dans notre base. "
    "Essayez la recherche par nom."
)

# « cru », « crue », « crus », « crues » dans un nom CIQUAL.
_MOT_CRU = re.compile(r"\bcrue?s?\b")


@dataclass(frozen=True)
class ReponseVLM:
    """Réponse du VLM, validée."""

    contenu: str
    label: str
    confiance: float


# Étape 1 : préparation de l'image


def preparer_image(image: bytes, taille_max: int) -> bytes:
    """Vérifie, redresse, réduit et nettoie une photo avant l'envoi au VLM.

    Le réencodage en JPEG ne recopie pas les métadonnées : la position GPS et
    les autres EXIF d'une photo de téléphone ne sortent pas de cette fonction.

    Args:
        image: contenu brut du fichier reçu.
        taille_max: plus grand côté autorisé, en pixels.

    Returns:
        L'image en JPEG, au plus `taille_max` pixels de côté.

    Raises:
        ImageInvalideError: si le fichier n'est pas une image lisible, ou si
            ses dimensions sont démesurées (protection « bombe de décompression »).
    """
    try:
        with Image.open(io.BytesIO(image)) as source:
            # Applique l'orientation EXIF avant de la perdre au réencodage.
            redressee = ImageOps.exif_transpose(source)
            rgb = redressee.convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ImageInvalideError("Le fichier envoyé n'est pas une image lisible.") from exc

    rgb.thumbnail((taille_max, taille_max), Image.Resampling.LANCZOS)
    sortie = io.BytesIO()
    rgb.save(sortie, format="JPEG", quality=QUALITE_JPEG)
    return sortie.getvalue()


# Étape 2 : appel au VLM


def _latence_ms(debut: float) -> int:
    """Durée écoulée depuis `debut` (time.perf_counter), en millisecondes."""
    return round((time.perf_counter() - debut) * 1000)


def analyser_reponse(texte: str) -> ReponseVLM | None:
    """Valide la sortie JSON du modèle.

    Le schéma imposé à Ollama rend une sortie invalide très improbable, mais
    on ne fait jamais confiance à une sortie de modèle sans la vérifier.

    Returns:
        La réponse validée, ou None si elle est inexploitable.
    """
    try:
        donnees = json.loads(texte)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(donnees, dict):
        return None

    contenu = donnees.get("contenu")
    label = donnees.get("label")
    confiance = donnees.get("confidence")
    if contenu not in CONTENUS_VALIDES or not isinstance(label, str):
        return None
    # bool est un sous-type de int en Python : on l'écarte explicitement.
    if isinstance(confiance, bool) or not isinstance(confiance, int | float):
        return None
    if not 0.0 <= float(confiance) <= 1.0:
        return None
    return ReponseVLM(contenu=contenu, label=label.strip().lower(), confiance=float(confiance))


async def _appeler_vlm(image_jpeg: bytes) -> ReponseVLM | None:
    """Envoie l'image au VLM et renvoie sa réponse validée.

    Returns:
        La réponse validée, ou None si le modèle a répondu quelque chose
        d'inexploitable.

    Raises:
        VLMIndisponibleError: si Ollama est injoignable, dépasse le délai
            d'attente ou répond avec un code d'erreur.
    """
    settings = get_ollama_settings()
    charge_utile = {
        "model": settings.model,
        "stream": False,
        "format": SCHEMA_REPONSE,
        "options": {"temperature": 0, "num_ctx": settings.num_ctx},
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEME},
            {
                "role": "user",
                "content": PROMPT_UTILISATEUR,
                "images": [base64.b64encode(image_jpeg).decode("ascii")],
            },
        ],
    }

    # Monitorage du service (C8) : une ligne de log par appel. Jamais l'image.
    debut = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            reponse = await client.post(f"{settings.base_url}/api/chat", json=charge_utile)
            reponse.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "appel ollama en échec : statut=%s latence_ms=%d",
            exc.response.status_code,
            _latence_ms(debut),
        )
        raise VLMIndisponibleError("Le service de reconnaissance photo a répondu en erreur.") from exc
    except httpx.HTTPError as exc:
        logger.error(
            "appel ollama en échec : erreur_reseau=%s latence_ms=%d",
            type(exc).__name__,
            _latence_ms(debut),
        )
        raise VLMIndisponibleError("Le service de reconnaissance photo est injoignable.") from exc

    try:
        donnees = reponse.json()
        texte = donnees["message"]["content"]
    except (ValueError, KeyError, TypeError):
        logger.error("réponse Ollama inattendue : corps illisible ou sans message.content")
        return None

    resultat = analyser_reponse(texte)
    logger.info(
        "appel ollama : statut=%s modele=%s latence_ms=%d tokens_entree=%s tokens_sortie=%s "
        "contenu=%s json_valide=%s",
        reponse.status_code,
        donnees.get("model", settings.model),
        _latence_ms(debut),
        donnees.get("prompt_eval_count"),
        donnees.get("eval_count"),
        resultat.contenu if resultat else None,
        resultat is not None,
    )
    return resultat


# Étape 3 : rapprochement CIQUAL


def _normaliser(texte: str) -> str:
    """Minuscules, sans accents ni espaces superflus : pour comparer des noms."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    return " ".join(sans_accents.lower().split())


def choisir_aliment(label: str, candidats: Sequence[Aliment]) -> Aliment | None:
    """Choisit, parmi les résultats de la recherche floue, l'aliment photographié.

    La recherche par nom est tolérante : « pomme » remonte aussi « Pomme de
    terre ». On reclasse donc les candidats ; à priorité égale, l'ordre de la
    recherche (similarité décroissante) est conservé :

    1. d'abord les noms qui commencent par le libellé suivi d'une virgule, ou
       qui lui sont égaux (« Pomme, crue… » pour « pomme ») ;
    2. parmi eux, d'abord les aliments crus : la photo montre un aliment brut.

    Args:
        label: libellé renvoyé par le VLM.
        candidats: résultats de `aliment_repository.rechercher_par_nom`, du
            plus proche au plus éloigné.

    Returns:
        L'aliment retenu, ou None s'il n'y a aucun candidat.
    """
    if not candidats:
        return None
    libelle = _normaliser(label)

    def priorite(aliment: Aliment) -> tuple[int, int]:
        nom = _normaliser(aliment.nom)
        nom_exact = nom == libelle or nom.startswith(f"{libelle},")
        cru = bool(_MOT_CRU.search(nom))
        return (0 if nom_exact else 1, 0 if cru else 1)

    # min() garde le premier des candidats de même priorité : l'ordre de la recherche.
    return min(candidats, key=priorite)


async def _construire_detail(session: AsyncSession, aliment: Aliment) -> AlimentDetail:
    """Score, badges et alternatives : même charge utile que `GET /score/aliment/{id}`."""
    return AlimentDetail(
        aliment=AlimentResume.model_validate(aliment),
        score=score_service.scorer_aliment(aliment),
        badges=score_service.badges_aliment(aliment),
        alternatives=await alternative_service.trouver_alternatives(session, aliment),
        libelle_alternatives=LIBELLE_ALTERNATIVES,
        disclaimer=DISCLAIMER_SCORE,
        mention_projet_etudiant=MENTION_PROJET_ETUDIANT,
        citation_source=CITATION_SOURCE_COURTE,
    )


async def _journaliser(
    session: AsyncSession,
    *,
    statut: str,
    reponse: ReponseVLM | None,
    id_aliment: int | None,
) -> None:
    """Écrit l'inférence dans `log_vlm`. Une panne ici ne casse jamais la réponse."""
    try:
        await log_vlm_repository.enregistrer(
            session,
            statut=statut,
            label_identifie=(reponse.label or None) if reponse else None,
            score_confiance=reponse.confiance if reponse else None,
            id_aliment=id_aliment,
        )
        await session.commit()
    except Exception:
        logger.exception("échec de la journalisation VLM : la réponse est renvoyée quand même")
        await session.rollback()


# Point d'entrée


async def analyser_image(session: AsyncSession, image: bytes) -> VisionResponse:
    """Identifie un aliment sur une photo et renvoie son score.

    Args:
        session: session SQLAlchemy.
        image: contenu binaire de l'image envoyée.

    Returns:
        Le résultat de l'analyse. Chaque inférence est journalisée dans `log_vlm`.

    Raises:
        ImageInvalideError: si le fichier n'est pas une image lisible. Rien
            n'est envoyé au VLM, rien n'est journalisé.
        VLMIndisponibleError: si Ollama ne répond pas. L'échec est journalisé.
    """
    settings = get_ollama_settings()
    image_jpeg = preparer_image(image, settings.image_max_px)

    try:
        reponse = await _appeler_vlm(image_jpeg)
    except VLMIndisponibleError:
        await _journaliser(session, statut=STATUT_ECHEC, reponse=None, id_aliment=None)
        raise

    # Réponse inexploitable, photo sans aliment unique, ou modèle trop incertain.
    if reponse is None:
        await _journaliser(session, statut=STATUT_ECHEC, reponse=None, id_aliment=None)
        return VisionResponse(statut=STATUT_ECHEC, message=MESSAGE_INCERTAIN)

    if reponse.contenu != CONTENU_ALIMENT_UNIQUE:
        await _journaliser(session, statut=STATUT_ECHEC, reponse=reponse, id_aliment=None)
        return VisionResponse(
            statut=STATUT_ECHEC,
            contenu=reponse.contenu,
            score_confiance=reponse.confiance,
            message=MESSAGES_NON_RECONNU[reponse.contenu],
        )

    if not reponse.label or reponse.confiance < settings.confidence_threshold:
        await _journaliser(session, statut=STATUT_ECHEC, reponse=reponse, id_aliment=None)
        return VisionResponse(
            statut=STATUT_ECHEC,
            contenu=reponse.contenu,
            label_identifie=reponse.label or None,
            score_confiance=reponse.confiance,
            message=MESSAGE_INCERTAIN,
        )

    candidats = await aliment_repository.rechercher_par_nom(
        session, reponse.label, limite=NOMBRE_CANDIDATS
    )
    aliment = choisir_aliment(reponse.label, candidats)
    if aliment is None:
        await _journaliser(session, statut=STATUT_NON_RAPPROCHE, reponse=reponse, id_aliment=None)
        return VisionResponse(
            statut=STATUT_NON_RAPPROCHE,
            contenu=reponse.contenu,
            label_identifie=reponse.label,
            score_confiance=reponse.confiance,
            message=MESSAGE_ABSENT_DE_LA_BASE.format(label=reponse.label),
        )

    detail = await _construire_detail(session, aliment)
    await _journaliser(session, statut=STATUT_RECONNU, reponse=reponse, id_aliment=aliment.id_aliment)
    return VisionResponse(
        statut=STATUT_RECONNU,
        contenu=reponse.contenu,
        label_identifie=reponse.label,
        score_confiance=reponse.confiance,
        id_aliment=aliment.id_aliment,
        resultat=detail,
    )