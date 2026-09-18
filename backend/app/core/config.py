"""Configuration centralisée du backend.

Toutes les valeurs proviennent de variables d'environnement (.env / .env.example copy)
Organisation : un `@dataclass(frozen=True)` par domaine de configuration, et un
accesseur `get_*_settings()` mis en cache. Le cache évite de relire
l'environnement à chaque requête HTTP entrante ; on le vide dans les tests avec
`get_xxx_settings.cache_clear()`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Racine du projet : app/core/config.py -> app -> backend -> racine
PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(RuntimeError):
    """Levée quand une variable d'environnement est absente ou invalide."""



# Helpers de lecture


def _require(name: str) -> str:
    """Lit une variable d'environnement obligatoire.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Variable d'environnement manquante : {name}. "
            "Copiez `.env.example` en `.env` et renseignez-la."
        )
    return value


def _read_float(name: str, default: str) -> float:
    raw = os.getenv(name, default).strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} doit être un nombre, reçu : {raw!r}") from exc


def _read_int(name: str, default: str) -> int:
    raw = os.getenv(name, default).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} doit être un entier, reçu : {raw!r}") from exc


def _read_bool(name: str, default: str) -> bool:
    raw = os.getenv(name, default).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} doit être un booléen, reçu : {raw!r}")



# Application


@dataclass(frozen=True)
class AppSettings:
    """Réglages généraux de l'application FastAPI."""

    environment: str          # "local" | "preprod" | "prod"
    log_level: str
    cors_origins: tuple[str, ...]

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Construit et met en cache la configuration applicative."""
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
    return AppSettings(
        environment=os.getenv("ENVIRONMENT", "local").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        cors_origins=origins,
    )



# Base de données


@dataclass(frozen=True)
class DatabaseSettings:
    """Paramètres de connexion PostgreSQL.

    L'URL est reconstruite à partir des variables déjà utilisées par
    `docker-compose`.
    """

    user: str
    password: str
    database: str
    host: str
    port: int
    echo_sql: bool
    pool_size: int

    @property
    def url(self) -> str:
        """URL SQLAlchemy asynchrone (driver psycopg 3)."""
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def sync_url(self) -> str:
        """URL synchrone - utilisée uniquement par Alembic."""
        return self.url


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Construit et met en cache la configuration base de données."""
    return DatabaseSettings(
        user=_require("POSTGRES_USER"),
        password=_require("POSTGRES_PASSWORD"),
        database=_require("POSTGRES_DB"),
        # Dans docker-compose le service s'appelle `db` ; depuis la machine hôte
        # (scripts, DBeaver, pytest local) c'est `localhost` + POSTGRES_PORT.
        host=os.getenv("POSTGRES_HOST", "db").strip(),
        port=_read_int("POSTGRES_INTERNAL_PORT", "5432"),
        echo_sql=_read_bool("SQL_ECHO", "false"),
        pool_size=_read_int("DB_POOL_SIZE", "5"),
    )



# Sécurité (JWT + hachage)


@dataclass(frozen=True)
class SecuritySettings:
    """Paramètres d'authentification.
    """

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    bcrypt_rounds: int
    api_key: str | None

    @property
    def api_key_enabled(self) -> bool:
        return bool(self.api_key)


@lru_cache(maxsize=1)
def get_security_settings() -> SecuritySettings:
    """Construit et met en cache la configuration de sécurité."""
    raw_api_key = os.getenv("ALIMENDO_API_KEY", "").strip()
    return SecuritySettings(
        jwt_secret_key=_require("JWT_SECRET_KEY"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256").strip(),
        access_token_expire_minutes=_read_int("ACCESS_TOKEN_EXPIRE_MINUTES", "60"),
        bcrypt_rounds=_read_int("BCRYPT_ROUNDS", "12"),
        api_key=raw_api_key or None,
    )



# ChromaDB + embeddings (côté requête du RAG)


@dataclass(frozen=True)
class ChromaSettings:
    """Accès à l'index vectoriel.

    Ces valeurs DOIVENT rester identiques à celles de `rag/config.py`
    (pipeline d'ingestion offline). Un modèle d'embeddings ou une métrique
    différente entre l'indexation et la requête produit des résultats faux
    sans lever la moindre erreur.
    """

    host: str
    port: int
    collection_name: str
    distance_metric: str
    embedding_model: str
    query_prefix: str
    passage_prefix: str
    top_k: int


@lru_cache(maxsize=1)
def get_chroma_settings() -> ChromaSettings:
    """Construit et met en cache la configuration ChromaDB / embeddings."""
    return ChromaSettings(
        host=os.getenv("CHROMA_HOST", "chromadb").strip(),
        port=_read_int("CHROMA_INTERNAL_PORT", "8000"),
        collection_name=os.getenv("CHROMA_COLLECTION", "endo_corpus").strip(),
        distance_metric=os.getenv("CHROMA_DISTANCE_METRIC", "cosine").strip(),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "intfloat/multilingual-e5-base"
        ).strip(),
        query_prefix=os.getenv("EMBEDDING_QUERY_PREFIX", "query: "),
        passage_prefix=os.getenv("EMBEDDING_PASSAGE_PREFIX", "passage: "),
        top_k=_read_int("RAG_TOP_K", "5"),
    )



# Mistral (LLM du chatbot RAG) 


@dataclass(frozen=True)
class MistralSettings:
    """Paramètres d'appel au LLM du chatbot RAG."""

    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float

    @property
    def chat_completions_url(self) -> str:
        """URL complète de l'endpoint de génération."""
        return f"{self.base_url}/chat/completions"


@lru_cache(maxsize=1)
def get_mistral_settings() -> MistralSettings:
    """Construit et met en cache la config Mistral.

    Le cache évite de relire l'environnement à chaque requête HTTP entrante.
    À vider avec `get_mistral_settings.cache_clear()` dans les tests.

    """
    return MistralSettings(
        api_key=_require("MISTRAL_API_KEY"),
        base_url=os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/"),
        model=os.getenv("MISTRAL_MODEL", "mistral-small-2603").strip(),
        temperature=_read_float("MISTRAL_TEMPERATURE", "0.15"),
        max_tokens=_read_int("MISTRAL_MAX_TOKENS", "800"),
        timeout_seconds=_read_float("MISTRAL_TIMEOUT_SECONDS", "30"),
    )



# Ollama (VLM) 


@dataclass(frozen=True)
class OllamaSettings:
    """Paramètres d'appel au VLM de reconnaissance photo."""

    base_url: str
    model: str
    timeout_seconds: float
    confidence_threshold: float


@lru_cache(maxsize=1)
def get_ollama_settings() -> OllamaSettings:
    """Construit et met en cache la configuration Ollama."""
    return OllamaSettings(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/"),
        model=os.getenv("OLLAMA_MODEL", "qwen3-vl:4b").strip(),
        timeout_seconds=_read_float("OLLAMA_TIMEOUT_SECONDS", "120"),
        confidence_threshold=_read_float("VLM_CONFIDENCE_THRESHOLD", "0.5"),
    )



# Open Food Facts


@dataclass(frozen=True)
class OpenFoodFactsSettings:
    """Paramètres d'appel à l'API Open Food Facts."""

    base_url: str
    user_agent: str
    timeout_seconds: float


@lru_cache(maxsize=1)
def get_openfoodfacts_settings() -> OpenFoodFactsSettings:
    """Construit et met en cache la configuration OFF.

    Le User-Agent est exigé par les conditions d'utilisation d'OFF
    """
    return OpenFoodFactsSettings(
        base_url=os.getenv("OFF_BASE_URL", "https://world.openfoodfacts.org").rstrip("/"),
        user_agent=os.getenv(
            "OFF_USER_AGENT",
            "Alimendo/0.1 (projet etudiant RNCP37827)",
        ).strip(),
        timeout_seconds=_read_float("OFF_TIMEOUT_SECONDS", "10"),
    )
