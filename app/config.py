import logging
import os
import secrets
from datetime import timedelta

log = logging.getLogger(__name__)

_auto_key = secrets.token_hex(32)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    if not SECRET_KEY:
        SECRET_KEY = _auto_key
        log.warning(
            "SECRET_KEY not set — using auto-generated key. "
            "Sessions will not survive container restarts. "
            "Set SECRET_KEY in .env for persistent sessions."
        )

    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.environ.get("SESSION_TIMEOUT_HOURS", "8"))
    )

    # Server-side sessions (filesystem)
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "/tmp/flask_sessions"
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "ide:"

    # Session cookie security (Finding 4)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    IRIS_URL = os.environ.get("IRIS_URL", "https://localhost:4443")
    # Browser-facing IRIS URL for deep links. Defaults to IRIS_URL if not set.
    IRIS_EXTERNAL_URL = os.environ.get("IRIS_EXTERNAL_URL", "") or os.environ.get("IRIS_URL", "https://localhost:4443")
    IRIS_VERIFY_SSL = os.environ.get("IRIS_VERIFY_SSL", "false").lower() == "true"
    DATA_SOURCE = os.environ.get("DATA_SOURCE", "api")  # "api" or "db"

    # Optional: pre-configured API key (single-user/service mode)
    # If set, users skip the login page and this key is used for all requests.
    # If empty, users must log in with their own IRIS API key.
    IRIS_API_KEY = os.environ.get("IRIS_API_KEY", "")

    # DB mode settings (only used when DATA_SOURCE=db)
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "iris_db")
    DB_USER = os.environ.get("DB_USER", "iris")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_SSL_MODE = os.environ.get("DB_SSL_MODE", "prefer")

    # Data cache TTL in seconds (how long fetched case data is cached)
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))

    # Auto-refresh interval in seconds (0 = disabled)
    REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", "30"))

    # Shadowserver integration (read-only viewer for shadowserver_db)
    SS_ENABLED = os.environ.get("SS_ENABLED", "false").lower() == "true"
    SS_DB_HOST = os.environ.get("SS_DB_HOST", "postgres")
    SS_DB_PORT = int(os.environ.get("SS_DB_PORT", "5432"))
    SS_DB_NAME = os.environ.get("SS_DB_NAME", "shadowserver_db")
    SS_DB_USER = os.environ.get("SS_DB_USER", "shadowserver_viewer")
    SS_DB_PASSWORD = os.environ.get("SS_DB_PASSWORD", "")
    SS_DB_SSL_MODE = os.environ.get("SS_DB_SSL_MODE", "prefer")
