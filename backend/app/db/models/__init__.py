"""Point d'entrée unique des modèles ORM.

Importer tous les modèles ici garantit qu'ils sont enregistrés dans `Base.metadata` avant qu'Alembic ne compare le code au schéma réel. 
Sans cet import, `alembic revision --autogenerate` produirait une migration vide ou proposerait de supprimer des tables existantes.
"""

from app.db.base import Base
from app.db.models.aliment import (
    PARAMETRES_NUTRITIONNELS,
    Aliment,
    Categorie,
)
from app.db.models.log_vlm import (
    STATUT_ECHEC,
    STATUT_NON_RAPPROCHE,
    STATUT_RECONNU,
    STATUTS_VALIDES,
    LogVlm,
)
from app.db.models.user import (
    ROLE_ADMIN,
    ROLE_USER,
    ROLES_PAR_DEFAUT,
    Role,
    Utilisateur,
)

__all__ = [
    "PARAMETRES_NUTRITIONNELS",
    "ROLES_PAR_DEFAUT",
    "ROLE_ADMIN",
    "ROLE_USER",
    "STATUTS_VALIDES",
    "STATUT_ECHEC",
    "STATUT_NON_RAPPROCHE",
    "STATUT_RECONNU",
    "Aliment",
    "Base",
    "Categorie",
    "LogVlm",
    "Role",
    "Utilisateur",
]
