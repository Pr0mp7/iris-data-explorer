import logging
import os
import re

from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from markupsafe import Markup

from .config import Config

APP_VERSION = "1.5.0"

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

    # Make sessions permanent (uses PERMANENT_SESSION_LIFETIME from config)
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    app.jinja_env.filters["strip_tags"] = _strip_tags
    app.jinja_env.globals["app_version"] = APP_VERSION

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

        # Full Content-Security-Policy (Finding 7)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
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
