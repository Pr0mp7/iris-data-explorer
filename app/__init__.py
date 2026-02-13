import re

from flask import Flask
from markupsafe import Markup

from .config import Config

_TAG_RE = re.compile(r"<[^>]+>|<!--.*?-->", re.DOTALL)


def _strip_tags(value):
    """Strip HTML/XML tags and comments from a string."""
    if not value:
        return ""
    return _TAG_RE.sub("", str(value)).strip()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.jinja_env.filters["strip_tags"] = _strip_tags

    from .routes import bp
    app.register_blueprint(bp)

    @app.after_request
    def set_security_headers(response):
        iris_ext = app.config["IRIS_EXTERNAL_URL"]
        response.headers["Content-Security-Policy"] = (
            f"frame-ancestors 'self' {iris_ext}"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app
