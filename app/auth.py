import requests as http_requests
from flask import current_app, request, redirect, url_for, session


def get_api_key():
    """Get the active API key — from session (pass-through) or env (service mode)."""
    env_key = current_app.config["IRIS_API_KEY"]
    if env_key:
        return env_key
    return session.get("api_key", "")


def require_auth():
    """Before-request handler: ensure user is authenticated."""
    # Skip auth for health check and login routes
    if request.path in ("/health", "/login", "/logout"):
        return
    if request.path.startswith("/static/"):
        return

    api_key = get_api_key()
    if not api_key:
        return redirect(url_for("main.login", next=request.url))


def validate_key_against_iris(api_key):
    """Validate an API key by calling IRIS. Returns (valid, user_info)."""
    try:
        resp = http_requests.get(
            f"{current_app.config['IRIS_URL']}/api/v2/cases",
            headers={"Authorization": f"Bearer {api_key}"},
            verify=current_app.config["IRIS_VERIFY_SSL"],
            timeout=10,
            params={"per_page": 1},
        )
        if resp.status_code == 200:
            return True, None
        return False, f"IRIS returned {resp.status_code}"
    except http_requests.RequestException as e:
        return False, f"Cannot reach IRIS: {e}"
