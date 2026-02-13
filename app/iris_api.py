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


def _collect_paginated(path):
    """Fetch all pages from a paginated IRIS API v2 endpoint.

    v2 endpoints return: {"total": N, "data": [...], "current_page": 1, "next_page": 2, "last_page": 5}
    """
    page = 1
    per_page = 100
    all_items = []

    while True:
        result = _get(path, params={"page": page, "per_page": per_page})
        items = result.get("data", [])
        if isinstance(items, list):
            all_items.extend(items)
        else:
            return items  # single object, not paginated

        total = result.get("total")
        if total is not None and len(all_items) >= total:
            break
        if len(items) < per_page:
            break
        page += 1

    return all_items


def _get_legacy(path, params=None):
    """Fetch from legacy (non-v2) IRIS API endpoint.

    Legacy endpoints return: {"status": "success", "data": ...}
    """
    result = _get(path, params=params)
    return result.get("data", result)


def get_case_summary(case_id):
    """Fetch case metadata."""
    result = _get(f"/api/v2/cases/{case_id}")
    return result.get("data", result)


def get_case_assets(case_id):
    return _collect_paginated(f"/api/v2/cases/{case_id}/assets")


def get_case_iocs(case_id):
    return _collect_paginated(f"/api/v2/cases/{case_id}/iocs")


def get_case_events(case_id):
    """Fetch timeline events — uses legacy endpoint (v2 returns 405)."""
    data = _get_legacy("/case/timeline/events/list", params={"cid": case_id})
    return data.get("timeline", []) if isinstance(data, dict) else data


def get_case_tasks(case_id):
    return _collect_paginated(f"/api/v2/cases/{case_id}/tasks")


def get_case_notes(case_id):
    """Fetch notes — uses legacy endpoint (v2 returns 405).

    Returns note directories with nested notes.
    """
    data = _get_legacy("/case/notes/directories/filter", params={"cid": case_id})
    if not isinstance(data, list):
        return []
    # Flatten: directories contain notes
    notes = []
    for directory in data:
        if isinstance(directory, dict):
            for note in directory.get("notes", []):
                notes.append(note)
    return notes


def get_case_evidences(case_id):
    return _collect_paginated(f"/api/v2/cases/{case_id}/evidences")


def get_case_data(case_id):
    """Fetch all case entities via IRIS REST API."""
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
    return _collect_paginated("/api/v2/cases")
