import requests
from flask import current_app


def _get(path, params=None):
    """Make authenticated GET request to IRIS API."""
    resp = requests.get(
        f"{current_app.config['IRIS_URL']}{path}",
        headers={"Authorization": f"Bearer {current_app.config['IRIS_API_KEY']}"},
        verify=current_app.config["IRIS_VERIFY_SSL"],
        timeout=30,
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def _collect_paginated(path, data_key=None):
    """Fetch all pages from a paginated IRIS API v2 endpoint."""
    page = 1
    per_page = 100
    all_items = []

    while True:
        data = _get(path, params={"page": page, "per_page": per_page})

        # v2 API wraps data in {"status": "success", "data": [...]}
        # or {"status": "success", "data": {"total": N, "<key>": [...]}}
        payload = data.get("data", data)

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and data_key and data_key in payload:
            items = payload[data_key]
        elif isinstance(payload, dict):
            # Try to find the list in the dict values
            items = []
            for v in payload.values():
                if isinstance(v, list):
                    items = v
                    break
            if not items:
                # Single object, not a list
                return payload
        else:
            items = []

        all_items.extend(items)

        # Check if there are more pages
        total = None
        if isinstance(payload, dict):
            total = payload.get("total")
        if total is not None and len(all_items) >= total:
            break
        if len(items) < per_page:
            break
        page += 1

    return all_items


def get_case_summary(case_id):
    """Fetch case metadata."""
    data = _get(f"/api/v2/cases/{case_id}")
    return data.get("data", data)


def get_case_assets(case_id):
    """Fetch all assets for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/assets", "assets")


def get_case_iocs(case_id):
    """Fetch all IOCs for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/iocs", "iocs")


def get_case_events(case_id):
    """Fetch all timeline events for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/events", "events")


def get_case_tasks(case_id):
    """Fetch all tasks for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/tasks", "tasks")


def get_case_notes(case_id):
    """Fetch all notes for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/notes", "notes")


def get_case_evidences(case_id):
    """Fetch all evidences for a case."""
    return _collect_paginated(f"/api/v2/cases/{case_id}/evidences", "evidences")


def get_case_data(case_id):
    """Fetch all case entities via IRIS REST API v2."""
    return {
        "case": get_case_summary(case_id),
        "assets": get_case_assets(case_id),
        "iocs": get_case_iocs(case_id),
        "events": get_case_events(case_id),
        "tasks": get_case_tasks(case_id),
        "notes": get_case_notes(case_id),
        "evidences": get_case_evidences(case_id),
    }


def get_cases_list():
    """Fetch list of all cases."""
    return _collect_paginated("/api/v2/cases", "cases")
