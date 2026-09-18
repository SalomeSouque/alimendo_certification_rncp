"""Configuration du logging applicatif.
"""

from __future__ import annotations

import logging
import re
import sys

#Motifs masqués dans les messages de log.
#On cible les en-têtes et champs qui portent des secrets, pas le mot
#« password » lui-même - ne jamais écrire la valeur.
_MOTIFS_SENSIBLES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(Authorization[\"']?\s*[:=]\s*[\"']?Bearer\s+)\S+", re.IGNORECASE),
    re.compile(r"(X-API-Key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
)

_REMPLACEMENT = r"\1***"


class FiltreSecrets(logging.Filter):
    """Masque les secrets dans les messages avant leur écriture."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        masque = message
        for motif in _MOTIFS_SENSIBLES:
            masque = motif.sub(_REMPLACEMENT, masque)

        if masque != message:
            # On réécrit le message déjà formaté et on neutralise les args,
            # sinon le formateur réappliquerait les valeurs d'origine.
            record.msg = masque
            record.args = ()

        return True


def configurer_logging(niveau: str = "INFO") -> None:
    """Configure le logging racine de l'application.

    Args:
        niveau: niveau de log ("DEBUG", "INFO", "WARNING"…).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(FiltreSecrets())

    racine = logging.getLogger()
    racine.handlers.clear()
    racine.addHandler(handler)
    racine.setLevel(niveau)

    # Uvicorn installe ses propres handlers : on les fait passer par le nôtre
    # pour que le filtre s'applique aussi aux logs d'accès.
    for nom in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        journal = logging.getLogger(nom)
        journal.handlers.clear()
        journal.propagate = True
