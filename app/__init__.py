from flask import Flask

from .config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
