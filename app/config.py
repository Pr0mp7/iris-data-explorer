import os
import secrets


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

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

    # Data cache TTL in seconds (how long fetched case data is cached)
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))
