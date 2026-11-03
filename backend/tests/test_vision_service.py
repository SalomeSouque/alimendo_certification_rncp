"""Tests du service de reconnaissance photo (lot VLM, critères C8-CR2, C9-CR2, C12).

But du fichier : prouver, sans réseau ni GPU, que `vision_service` :

- prépare l'image (réduction, redressement, suppression des EXIF/GPS) ;
- envoie à Ollama le prompt, le schéma JSON et les options validés ;
- décide correctement dans les quatre familles de cas du lot : reconnu,
  non reconnu, image invalide, service indisponible ;
- choisit le bon aliment CIQUAL quand la recherche floue est ambiguë ;
- journalise chaque inférence dans `log_vlm`, sans jamais l'image.

Ollama est remplacé par `httpx.MockTransport`, la base par des doublures.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from app.core.config import get_ollama_settings
from app.db.models import STATUT_ECHEC, STATUT_NON_RAPPROCHE, STATUT_RECONNU
from app.repositories import aliment_repository, log_vlm_repository
from app.services import alternative_service, vision_service

NOM_LOGGER = "app.services.vision_service"


# Fabriques


def _image(largeur: int = 64, hauteur: int = 48, fmt: str = "PNG", exif: Image.Exif | None = None) -> bytes:
    """Fabrique une vraie image en mémoire."""
    sortie = io.BytesIO()
    options = {"exif": exif} if exif is not None else {}
    Image.new("RGB", (largeur, hauteur), (200, 30, 30)).save(sortie, format=fmt, **options)
    return sortie.getvalue()


def _aliment(id_aliment: int, nom: str) -> SimpleNamespace:
    """Aliment minimal : profil vide, donc score « indisponible » mais calculé."""
    return SimpleNamespace(
        id_aliment=id_aliment,
        nom=nom,
        source="CIQUAL",
        url_image=None,
        id_categorie=None,
        profil_nutritionnel=dict,
    )


def _reponse_ollama(contenu: dict | str) -> dict:
    """Corps type de `POST /api/chat` d'Ollama (stream: false)."""
    texte = contenu if isinstance(contenu, str) else json.dumps(contenu)
    return {
        "model": "qwen3-vl:4b-instruct-q4_K_M",
        "message": {"role": "assistant", "content": texte},
        "done": True,
        "prompt_eval_count": 1298,
        "eval_count": 31,
    }


def _brancher_faux_ollama(monkeypatch, gestionnaire: Callable[[httpx.Request], httpx.Response]) -> None:
    """Remplace Ollama par un gestionnaire local, sans réseau."""
    vrai_client = httpx.AsyncClient
    transport = httpx.MockTransport(gestionnaire)
    monkeypatch.setattr(
        vision_service.httpx,
        "AsyncClient",
        lambda **options: vrai_client(transport=transport, **options),
    )


def _ollama_repond(monkeypatch, contenu: dict | str, statut: int = 200) -> list[httpx.Request]:
    """Ollama répond toujours la même chose ; renvoie la liste des requêtes reçues."""
    requetes: list[httpx.Request] = []

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        requetes.append(requete)
        return httpx.Response(statut, json=_reponse_ollama(contenu))

    _brancher_faux_ollama(monkeypatch, gestionnaire)
    return requetes


# Fixtures


@pytest.fixture(autouse=True)
def config_ollama(monkeypatch):
    """Configuration connue et cache vidé avant et après chaque test."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama-test:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3-vl:4b-instruct-q4_K_M")
    monkeypatch.setenv("VLM_CONFIDENCE_THRESHOLD", "0.5")
    monkeypatch.setenv("VLM_IMAGE_MAX_PX", "1024")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")
    get_ollama_settings.cache_clear()
    yield
    get_ollama_settings.cache_clear()


@pytest.fixture
def journal(monkeypatch) -> AsyncMock:
    """Remplace l'écriture dans log_vlm et permet de vérifier ce qui y est écrit."""
    enregistrer = AsyncMock()
    monkeypatch.setattr(log_vlm_repository, "enregistrer", enregistrer)
    return enregistrer


@pytest.fixture
def recherche(monkeypatch) -> AsyncMock:
    """Recherche CIQUAL simulée : par défaut, une tomate crue."""
    rechercher = AsyncMock(return_value=[_aliment(42, "Tomate, crue")])
    monkeypatch.setattr(aliment_repository, "rechercher_par_nom", rechercher)
    monkeypatch.setattr(alternative_service, "trouver_alternatives", AsyncMock(return_value=[]))
    return rechercher


def _analyser(image: bytes):
    return asyncio.run(vision_service.analyser_image(AsyncMock(), image))


# Préparation de l'image


def test_grande_photo_reduite_a_1024_px_et_reencodee_en_jpeg():
    """Une photo de téléphone non réduite dépassait le contexte (4186 tokens > 4096)."""
    sortie = vision_service.preparer_image(_image(4000, 3000), 1024)

    with Image.open(io.BytesIO(sortie)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 1024
        assert image.size == (1024, 768)  # proportions conservées


def test_petite_photo_jamais_agrandie():
    sortie = vision_service.preparer_image(_image(300, 200), 1024)

    with Image.open(io.BytesIO(sortie)) as image:
        assert image.size == (300, 200)


def test_metadonnees_exif_et_gps_supprimees():
    exif = Image.Exif()
    exif[0x010F] = "Fabricant du téléphone"  # Make
    exif[0x8825] = {2: (48.0, 51.0, 24.0)}   # GPSInfo : latitude
    photo = _image(800, 600, fmt="JPEG", exif=exif)
    with Image.open(io.BytesIO(photo)) as originale:
        assert len(originale.getexif()) > 0  # le test part bien d'une photo avec EXIF

    sortie = vision_service.preparer_image(photo, 1024)

    with Image.open(io.BytesIO(sortie)) as image:
        assert len(image.getexif()) == 0


def test_orientation_exif_appliquee_avant_suppression():
    """Une photo prise en portrait (orientation 6) doit arriver debout au VLM."""
    exif = Image.Exif()
    exif[0x0112] = 6  # rotation de 90° à appliquer à l'affichage
    photo = _image(400, 300, fmt="JPEG", exif=exif)

    sortie = vision_service.preparer_image(photo, 1024)

    with Image.open(io.BytesIO(sortie)) as image:
        assert image.size == (300, 400)


@pytest.mark.parametrize(
    "contenu",
    [b"", b"du texte qui n'est pas une image", b"\x89PNG\r\n\x1a\n tronque"],
    ids=["vide", "texte", "png_tronque"],
)
def test_fichier_illisible_refuse(contenu):
    with pytest.raises(vision_service.ImageInvalideError):
        vision_service.preparer_image(contenu, 1024)


# Requête envoyée à Ollama


def test_requete_ollama_porte_le_prompt_le_schema_et_les_options(monkeypatch, journal, recherche):
    requetes = _ollama_repond(
        monkeypatch, {"contenu": "aliment_unique", "label": "tomate", "confidence": 0.98}
    )

    _analyser(_image(2000, 1500))

    assert len(requetes) == 1
    requete = requetes[0]
    assert str(requete.url) == "http://ollama-test:11434/api/chat"
    corps = json.loads(requete.content)
    assert corps["model"] == "qwen3-vl:4b-instruct-q4_K_M"
    assert corps["stream"] is False
    assert corps["format"] == vision_service.SCHEMA_REPONSE
    assert list(corps["format"]["properties"]) == ["contenu", "label", "confidence"]
    assert corps["options"] == {"temperature": 0, "num_ctx": 4096}
    # L'image envoyée est bien la version réduite, en JPEG.
    image_envoyee = base64.b64decode(corps["messages"][1]["images"][0])
    with Image.open(io.BytesIO(image_envoyee)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 1024


# Cas « reconnu »


def test_aliment_reconnu_renvoie_le_score_et_journalise(monkeypatch, journal, recherche):
    _ollama_repond(monkeypatch, {"contenu": "aliment_unique", "label": "Tomate", "confidence": 0.98})

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_RECONNU
    assert resultat.contenu == "aliment_unique"
    assert resultat.label_identifie == "tomate"  # normalisé en minuscules
    assert resultat.id_aliment == 42
    assert resultat.resultat is not None
    assert resultat.resultat.aliment.nom == "Tomate, crue"
    assert resultat.resultat.score is not None
    # Conformité médicale : le score part toujours avec son disclaimer.
    assert resultat.resultat.disclaimer
    assert resultat.resultat.mention_projet_etudiant
    assert resultat.message is None

    recherche.assert_awaited_once()
    assert recherche.await_args.args[1] == "tomate"
    journal.assert_awaited_once()
    assert journal.await_args.kwargs == {
        "statut": STATUT_RECONNU,
        "label_identifie": "tomate",
        "score_confiance": 0.98,
        "id_aliment": 42,
    }


# Cas « non reconnu »


@pytest.mark.parametrize(
    ("contenu", "extrait_message"),
    [
        ("plusieurs_aliments", "Plusieurs aliments"),
        ("plat_prepare", "plat préparé"),
        ("aucun_aliment", "Aucun aliment"),
    ],
)
def test_photo_sans_aliment_unique_ni_recherche_ni_score(
    monkeypatch, journal, recherche, contenu, extrait_message
):
    """Cas réels du jeu de contrôle : assortiment de légumes, assiette, souris."""
    _ollama_repond(monkeypatch, {"contenu": contenu, "label": "", "confidence": 0.98})

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_ECHEC
    assert resultat.contenu == contenu
    assert resultat.resultat is None
    assert extrait_message in resultat.message
    assert "recherche par nom" in resultat.message
    recherche.assert_not_awaited()
    assert journal.await_args.kwargs["statut"] == STATUT_ECHEC
    assert journal.await_args.kwargs["label_identifie"] is None


def test_confiance_sous_le_seuil_traitee_comme_non_reconnue(monkeypatch, journal, recherche):
    _ollama_repond(monkeypatch, {"contenu": "aliment_unique", "label": "pomme", "confidence": 0.3})

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_ECHEC
    assert resultat.label_identifie == "pomme"
    assert "certitude" in resultat.message
    recherche.assert_not_awaited()


def test_aliment_unique_sans_label_traite_comme_non_reconnu(monkeypatch, journal, recherche):
    _ollama_repond(monkeypatch, {"contenu": "aliment_unique", "label": "  ", "confidence": 0.9})

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_ECHEC
    recherche.assert_not_awaited()


def test_aliment_reconnu_mais_absent_de_la_base(monkeypatch, journal, recherche):
    _ollama_repond(monkeypatch, {"contenu": "aliment_unique", "label": "durian", "confidence": 0.9})
    recherche.return_value = []

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_NON_RAPPROCHE
    assert resultat.label_identifie == "durian"
    assert resultat.resultat is None
    assert "« durian »" in resultat.message
    assert journal.await_args.kwargs["statut"] == STATUT_NON_RAPPROCHE


@pytest.mark.parametrize(
    "sortie_modele",
    [
        "ceci n'est pas du JSON",
        '["tomate", 0.9]',
        '{"contenu": "fruit", "label": "tomate", "confidence": 0.9}',
        '{"contenu": "aliment_unique", "label": "tomate", "confidence": 1.7}',
        '{"contenu": "aliment_unique", "label": "tomate", "confidence": true}',
        '{"contenu": "aliment_unique", "confidence": 0.9}',
    ],
    ids=["pas_json", "liste", "contenu_inconnu", "confiance_hors_bornes", "confiance_bool", "sans_label"],
)
def test_sortie_inexploitable_traitee_comme_echec(monkeypatch, journal, recherche, sortie_modele):
    """Le schéma rend ces cas improbables, mais une sortie de modèle se vérifie toujours."""
    _ollama_repond(monkeypatch, sortie_modele)

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_ECHEC
    assert resultat.contenu is None
    recherche.assert_not_awaited()
    assert journal.await_args.kwargs["statut"] == STATUT_ECHEC


# Cas « image invalide »


def test_image_invalide_n_appelle_pas_ollama_et_ne_journalise_rien(monkeypatch, journal, recherche):
    requetes = _ollama_repond(monkeypatch, {"contenu": "aucun_aliment", "label": "", "confidence": 1})

    with pytest.raises(vision_service.ImageInvalideError):
        _analyser(b"pas une image")

    assert requetes == []
    journal.assert_not_awaited()


# Cas « service indisponible »


@pytest.mark.parametrize(
    "panne",
    [
        httpx.ConnectError("connexion refusée"),
        httpx.ReadTimeout("délai dépassé"),
    ],
    ids=["injoignable", "timeout"],
)
def test_ollama_injoignable_ou_trop_lent(monkeypatch, journal, recherche, panne):
    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        raise panne

    _brancher_faux_ollama(monkeypatch, gestionnaire)

    with pytest.raises(vision_service.VLMIndisponibleError):
        _analyser(_image())

    # L'échec est journalisé : c'est ce qui permet de mesurer la disponibilité.
    assert journal.await_args.kwargs["statut"] == STATUT_ECHEC
    recherche.assert_not_awaited()


@pytest.mark.parametrize("statut", [400, 404, 500])
def test_ollama_en_erreur_http(monkeypatch, journal, recherche, statut):
    """400 : contexte dépassé ; 404 : modèle non téléchargé ; 500 : erreur interne."""
    _ollama_repond(monkeypatch, {"error": "..."}, statut=statut)

    with pytest.raises(vision_service.VLMIndisponibleError):
        _analyser(_image())


# Monitorage


def test_chaque_appel_laisse_une_ligne_de_log_sans_l_image(monkeypatch, journal, recherche, caplog):
    requetes = _ollama_repond(
        monkeypatch, {"contenu": "aliment_unique", "label": "tomate", "confidence": 0.98}
    )

    with caplog.at_level(logging.INFO, logger=NOM_LOGGER):
        _analyser(_image())

    assert "appel ollama : statut=200" in caplog.text
    assert "latence_ms=" in caplog.text
    assert "tokens_entree=1298" in caplog.text
    assert "contenu=aliment_unique" in caplog.text
    image_envoyee = json.loads(requetes[0].content)["messages"][1]["images"][0]
    assert image_envoyee[:40] not in caplog.text


def test_panne_de_journalisation_ne_casse_pas_la_reponse(monkeypatch, recherche):
    _ollama_repond(monkeypatch, {"contenu": "aliment_unique", "label": "tomate", "confidence": 0.98})
    monkeypatch.setattr(
        log_vlm_repository, "enregistrer", AsyncMock(side_effect=RuntimeError("base indisponible"))
    )

    resultat = _analyser(_image())

    assert resultat.statut == STATUT_RECONNU


# Rapprochement CIQUAL


def test_pomme_ne_donne_pas_pomme_de_terre():
    """La recherche floue remonte « Pomme de terre » pour « pomme » : on doit l'écarter."""
    candidats = [
        _aliment(1, "Pomme de terre, cuite à l'eau"),
        _aliment(2, "Pomme, cuite"),
        _aliment(3, "Pomme, crue, pulpe et peau"),
    ]

    choisi = vision_service.choisir_aliment("pomme", candidats)

    assert choisi.id_aliment == 3


def test_accents_et_casse_ignores():
    candidats = [_aliment(1, "Céleri-rave, cuit"), _aliment(2, "Céleri branche, cru")]

    assert vision_service.choisir_aliment("celeri branche", candidats).id_aliment == 2


def test_sans_nom_exact_l_ordre_de_la_recherche_est_conserve():
    candidats = [_aliment(1, "Tomate cerise, crue"), _aliment(2, "Tomate, séchée")]

    # Aucun nom ne commence par « tomates, » : on garde le premier cru.
    assert vision_service.choisir_aliment("tomates", candidats).id_aliment == 1


def test_aucun_candidat():
    assert vision_service.choisir_aliment("tomate", []) is None
