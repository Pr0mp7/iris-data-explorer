import logging
import re

from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import Markup

from .config import Config

_TAG_RE = re.compile(r"<[^>]+>|<!--.*?-->", re.DOTALL)

limiter = Limiter(key_func=get_remote_address, default_limits=[], storage_uri="memory://")


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

    # Rate limiter
    limiter.init_app(app)

    # Make sessions permanent (uses PERMANENT_SESSION_LIFETIME from config)
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    app.jinja_env.filters["strip_tags"] = _strip_tags

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
        response.headers["Content-Security-Policy"] = (
            f"frame-ancestors 'self' {iris_ext}"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    return app
