import hashlib
import logging
import time
from collections import OrderedDict

import requests
from flask import current_app

from .auth import get_api_key

log = logging.getLogger(__name__)

# Bounded LRU cache: max 256 entries, evicts oldest on overflow
_CACHE_MAX_ENTRIES = 256
_cache = OrderedDict()


def _cache_key(api_key, *parts):
    """Generate a cache key from API key hash and parts."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return f"{key_hash}:{':'.join(str(p) for p in parts)}"


def _get_cached(key):
    entry = _cache.get(key)
    if entry and entry["expires"] > time.time():
        _cache.move_to_end(key)
        return entry["data"]
    # Expired — remove it
    if entry:
        del _cache[key]
    return None


def _set_cached(key, data):
    ttl = current_app.config["CACHE_TTL"]
    _cache[key] = {"data": data, "expires": time.time() + ttl}
    _cache.move_to_end(key)
    # Evict oldest entries if over limit
    while len(_cache) > _CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


def _get(path, params=None):
    """Make authenticated GET request to IRIS API using the active user's key."""
    api_key = get_api_key()
    resp = requests.get(
        f"{current_app.config['IRIS_URL']}{path}",
        headers={"Authorization": f"Bearer {api_key}"},
        verify=current_app.config["IRIS_VERIFY_SSL"],
        timeout=30,
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


_MAX_PAGINATED_ITEMS = 10_000


def _collect_paginated(path):
    """Fetch all pages from a paginated IRIS API v2 endpoint."""
    page = 1
    per_page = 100
    all_items = []

    while True:
        result = _get(path, params={"page": page, "per_page": per_page})
        items = result.get("data", [])
        if isinstance(items, list):
            all_items.extend(items)
        else:
            return items

        total = result.get("total")
        if total is not None and len(all_items) >= total:
            break
        if len(items) < per_page:
            break
        if len(all_items) >= _MAX_PAGINATED_ITEMS:
            log.warning("Pagination limit reached (%d items) for %s", len(all_items), path)
            break
        page += 1

    return all_items


def _get_legacy(path, params=None):
    """Fetch from legacy (non-v2) IRIS API endpoint."""
    result = _get(path, params=params)
    return result.get("data", result)


def invalidate_cache(api_key, case_id, entity=None):
    """Remove cached data for a case entity (or all entities for that case)."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    if entity:
        _cache.pop(f"{key_hash}:{case_id}:{entity}", None)
    else:
        prefix = f"{key_hash}:{case_id}:"
        for k in list(_cache.keys()):
            if k.startswith(prefix):
                del _cache[k]


def _get_entity_cached(case_id, entity, bust_cache=False):
    """Fetch and cache a single entity type for a case."""
    api_key = get_api_key()
    ck = _cache_key(api_key, case_id, entity)

    if not bust_cache:
        cached = _get_cached(ck)
        if cached is not None:
            return cached

    fetchers = {
        "case": lambda: _get_case_summary(case_id),
        "assets": lambda: _collect_paginated(f"/api/v2/cases/{case_id}/assets"),
        "iocs": lambda: _collect_paginated(f"/api/v2/cases/{case_id}/iocs"),
        "events": lambda: _get_events(case_id),
        "tasks": lambda: _collect_paginated(f"/api/v2/cases/{case_id}/tasks"),
        "notes": lambda: _get_notes(case_id),
        "evidences": lambda: _collect_paginated(f"/api/v2/cases/{case_id}/evidences"),
    }

    data = fetchers[entity]()
    _set_cached(ck, data)
    return data


def _get_case_summary(case_id):
    result = _get(f"/api/v2/cases/{case_id}")
    return result.get("data", result)


def _get_events(case_id):
    data = _get_legacy("/case/timeline/events/list", params={"cid": case_id})
    return data.get("timeline", []) if isinstance(data, dict) else data


def _get_notes(case_id):
    data = _get_legacy("/case/notes/directories/filter", params={"cid": case_id})
    if not isinstance(data, list):
        return []
    notes = []
    for directory in data:
        if isinstance(directory, dict):
            for note in directory.get("notes", []):
                notes.append(note)
    return notes


def get_case_summary(case_id):
    return _get_entity_cached(case_id, "case")


def get_entity(case_id, entity, bust_cache=False):
    """Fetch a single entity type for a case (cached)."""
    return _get_entity_cached(case_id, entity, bust_cache=bust_cache)


def get_case_data(case_id):
    """Fetch all case entities via IRIS REST API."""
    return {
        "case": get_case_summary(case_id),
        "assets": get_entity(case_id, "assets"),
        "iocs": get_entity(case_id, "iocs"),
        "events": get_entity(case_id, "events"),
        "tasks": get_entity(case_id, "tasks"),
        "notes": get_entity(case_id, "notes"),
        "evidences": get_entity(case_id, "evidences"),
    }


def get_cases_list(bust_cache=False):
    api_key = get_api_key()
    ck = _cache_key(api_key, "cases_list")
    if not bust_cache:
        cached = _get_cached(ck)
        if cached is not None:
            return cached
    data = _collect_paginated("/api/v2/cases")
    _set_cached(ck, data)
    return data
