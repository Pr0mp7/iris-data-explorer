import time

import requests
from flask import current_app, request, abort, g

# Cache: {api_key: {"expires": timestamp, "valid": bool}}
_auth_cache = {}


def validate_api_key():
    """Validate IRIS API key from config. Called before each request."""
    # Skip auth for health check
    if request.path == "/health":
        return

    api_key = current_app.config["IRIS_API_KEY"]
    if not api_key:
        abort(401, description="IRIS_API_KEY not configured")

    now = time.time()
    cached = _auth_cache.get(api_key)
    if cached and cached["expires"] > now:
        if not cached["valid"]:
            abort(401, description="Invalid IRIS API key")
        return

    # Validate against IRIS API
    ttl = current_app.config["AUTH_CACHE_TTL"]
    try:
        resp = requests.get(
            f"{current_app.config['IRIS_URL']}/api/v2/cases",
            headers={"Authorization": f"Bearer {api_key}"},
            verify=current_app.config["IRIS_VERIFY_SSL"],
            timeout=10,
            params={"per_page": 1},
        )
        valid = resp.status_code == 200
    except requests.RequestException:
        valid = False

    _auth_cache[api_key] = {"expires": now + ttl, "valid": valid}

    if not valid:
        abort(401, description="Invalid IRIS API key or IRIS unreachable")
