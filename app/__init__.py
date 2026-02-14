import logging
import os
import re

from authlib.integrations.flask_client import OAuth
from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from markupsafe import Markup

from .config import Config

APP_VERSION = "1.6.0"
oauth = OAuth()

_TAG_RE = re.compile(r"<[^>]+>|<!--.*?-->", re.DOTALL)

# In-memory rate limiter — per-worker state. For cross-worker sharing, use redis://
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120 per minute"],
    storage_uri="memory://",
)


def _strip_tags(value):
    """Strip HTML/XML tags and comments from a string."""
    if not value:
        return ""
    return _TAG_RE.sub("", str(value)).strip()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    # Server-side sessions (Finding 1)
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    Session(app)

    # Rate limiter
    limiter.init_app(app)

    # Keycloak OIDC (optional)
    if app.config["KEYCLOAK_ENABLED"]:
        kc_url = app.config["KEYCLOAK_SERVER_URL"].rstrip("/")
        realm = app.config["KEYCLOAK_REALM"]
        oauth.init_app(app)
        oauth.register(
            name="keycloak",
            client_id=app.config["KEYCLOAK_CLIENT_ID"],
            client_secret=app.config["KEYCLOAK_CLIENT_SECRET"],
            server_metadata_url=f"{kc_url}/realms/{realm}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email iris-api"},
        )

    # Make sessions permanent (uses PERMANENT_SESSION_LIFETIME from config)
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    app.jinja_env.filters["strip_tags"] = _strip_tags
    app.jinja_env.globals["app_version"] = APP_VERSION
    app.jinja_env.globals["keycloak_enabled"] = app.config["KEYCLOAK_ENABLED"]

    from .routes import bp
    app.register_blueprint(bp)

    # Register DB connection pool teardowns (conditional)
    if app.config["DATA_SOURCE"] == "db":
        from . import iris_db
        iris_db.init_app(app)
    if app.config.get("SS_ENABLED"):
        from . import shadowserver_db
        shadowserver_db.init_app(app)

    @app.after_request
    def set_security_headers(response):
        iris_ext = app.config["IRIS_EXTERNAL_URL"]
        kc_origin = ""
        if app.config["KEYCLOAK_ENABLED"]:
            kc_origin = app.config["KEYCLOAK_SERVER_URL"].rstrip("/")

        # Full Content-Security-Policy (Finding 7)
        connect_src = "'self'"
        if kc_origin:
            connect_src += f" {kc_origin}"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            f"connect-src {connect_src}; "
            f"frame-ancestors 'self' {iris_ext}"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Finding 15: Removed X-Frame-Options — CSP frame-ancestors handles this
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Finding 6: HSTS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    return app
