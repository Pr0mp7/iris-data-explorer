import os


class Config:
    IRIS_URL = os.environ.get("IRIS_URL", "https://localhost:4443")
    IRIS_API_KEY = os.environ.get("IRIS_API_KEY", "")
    IRIS_VERIFY_SSL = os.environ.get("IRIS_VERIFY_SSL", "false").lower() == "true"
    DATA_SOURCE = os.environ.get("DATA_SOURCE", "api")  # "api" or "db"

    # DB mode settings (only used when DATA_SOURCE=db)
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "iris_db")
    DB_USER = os.environ.get("DB_USER", "iris")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

    # Auth cache TTL in seconds
    AUTH_CACHE_TTL = int(os.environ.get("AUTH_CACHE_TTL", "300"))
