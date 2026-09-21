"""Tests de l'authentification"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import get_security_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# Mots de passe

def test_hash_puis_verification_reussit():
    hash_bcrypt = hash_password("motdepasse-correct")
    assert verify_password("motdepasse-correct", hash_bcrypt) is True


def test_mauvais_mot_de_passe_rejete():
    hash_bcrypt = hash_password("motdepasse-correct")
    assert verify_password("motdepasse-faux", hash_bcrypt) is False


def test_hash_fait_bien_60_caracteres():
    """Contrainte MPD : `utilisateur.password` est VARCHAR(60)."""
    assert len(hash_password("motdepasse")) == 60


def test_deux_hash_du_meme_mot_de_passe_different():
    """Le sel est aléatoire : deux hachages ne doivent jamais être identiques.

    Sans sel, deux comptes avec même mdp auraient même hash (se lit directement dans un dump de base)
    """
    assert hash_password("identique") != hash_password("identique")


def test_hash_corrompu_renvoie_false_sans_lever():
    """Un hash illisible en base doit produire un 401, pas une 500."""
    assert verify_password("peu importe", "pas-un-hash-bcrypt") is False



# Jetons JWT

def test_aller_retour_du_jeton():
    token = create_access_token(utilisateur_id=42, email="test@example.com", role="user")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "user"


def test_jeton_expire_rejete():
    """Un jeton périmé doit produire un 401 explicite."""
    settings = get_security_settings()
    payload = {
        "sub": "1",
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token_expire = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(HTTPException) as erreur:
        decode_access_token(token_expire)

    assert erreur.value.status_code == 401


def test_jeton_signe_avec_une_autre_cle_rejete():
    """Un jeton fabriqué ailleurs ne doit jamais être accepté."""
    settings = get_security_settings()
    token_falsifie = jwt.encode(
        {"sub": "1", "email": "pirate@example.com", "role": "admin"},
        "une-autre-cle",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as erreur:
        decode_access_token(token_falsifie)

    assert erreur.value.status_code == 401


def test_jeton_malforme_rejete():
    with pytest.raises(HTTPException) as erreur:
        decode_access_token("ceci-nest-pas-un-jwt")

    assert erreur.value.status_code == 401
