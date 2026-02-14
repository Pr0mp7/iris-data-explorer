import re
from urllib.parse import urlparse

from requests.exceptions import HTTPError

from flask import (
    Blueprint, render_template, jsonify, request,
    current_app, session, redirect, url_for,
)

from .auth import require_auth, validate_key_against_iris, get_api_key
from . import limiter

import hashlib
import logging
import secrets

log = logging.getLogger(__name__)

bp = Blueprint("main", __name__)
bp.before_request(require_auth)


def _is_safe_redirect(target):
    """Only allow redirects to relative paths on the same host."""
    if not target:
        return False
    # Normalize backslashes to forward slashes (Finding 13)
    target = target.replace("\\", "/")
    # Use urlparse for robust validation
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    return target.startswith("/")


def _get_data_source():
    if current_app.config["DATA_SOURCE"] == "db":
        from . import iris_db
        return iris_db
    from . import iris_api
    return iris_api


# ── Auth routes ──────────────────────────────────────────────────

@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    # If env key is set (service mode), skip login
    if current_app.config["IRIS_API_KEY"]:
        return redirect(url_for("main.index"))

    error = None
    if request.method == "POST":
        # CSRF check
        token = request.form.get("csrf_token", "")
        if not token or token != session.get("csrf_token"):
            error = "Invalid form submission — please try again"
        else:
            api_key = request.form.get("api_key", "").strip()
            if not api_key:
                error = "API key is required"
            else:
                valid, msg = validate_key_against_iris(api_key)
                if valid:
                    session["api_key"] = api_key
                    next_url = request.args.get("next", "")
                    if not next_url or not _is_safe_redirect(next_url):
                        next_url = url_for("main.index")
                    return redirect(next_url)
                else:
                    error = msg or "Invalid API key"

    # Generate CSRF token for the form
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    return render_template("login.html", error=error,
                           csrf_token=session["csrf_token"],
                           iris_url=current_app.config["IRIS_EXTERNAL_URL"])


@bp.route("/logout", methods=["POST"])
def logout():
    """Logout via POST with CSRF token (Finding 5)."""
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        return redirect(url_for("main.login"))

    # Invalidate cache for this user's API key (Finding 12)
    api_key = get_api_key()
    if api_key and current_app.config["DATA_SOURCE"] == "api":
        from . import iris_api
        iris_api.invalidate_user_cache(api_key)

    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/logout", methods=["GET"])
def logout_get():
    """GET /logout redirects to login (backwards compat, no session clear without CSRF)."""
    session.clear()
    return redirect(url_for("main.login"))


# ── Page routes ──────────────────────────────────────────────────

@bp.route("/")
def index():
    return render_template("cases.html",
                           iris_url=current_app.config["IRIS_EXTERNAL_URL"],
                           refresh_interval=current_app.config["REFRESH_INTERVAL"])


@bp.route("/case/<int:case_id>")
def case_explorer(case_id):
    log.info("Case %s accessed from %s", case_id, request.remote_addr)
    ds = _get_data_source()
    try:
        case_info = ds.get_case_summary(case_id)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        log.warning("IRIS API error for case %s: HTTP %s", case_id, code)
        msg = "Case not found" if code == 404 else "Failed to load case"
        return render_template("error.html", error=msg), code
    except Exception:
        log.error("Unexpected error loading case %s", case_id)
        return render_template("error.html", error="Internal error"), 500
    return render_template("explorer.html", case_id=case_id, case=case_info,
                           iris_url=current_app.config["IRIS_EXTERNAL_URL"],
                           refresh_interval=current_app.config["REFRESH_INTERVAL"])


# ── DataTables server-side AJAX endpoints ────────────────────────

ENTITIES = ("assets", "iocs", "events", "tasks", "notes", "evidences")


@bp.route("/api/dt/cases")
def datatable_cases():
    """Server-side DataTables endpoint for the cases list."""
    ds = _get_data_source()
    bust = request.args.get("refresh") == "1"
    try:
        all_data = ds.get_cases_list(bust_cache=bust)
    except Exception:
        log.error("Failed to fetch cases list")
        return jsonify({"error": "Failed to load cases"}), 500

    if not isinstance(all_data, list):
        all_data = []

    draw = request.args.get("draw", 1, type=int)
    start = max(0, request.args.get("start", 0, type=int))
    length = min(max(1, request.args.get("length", 25, type=int)), 500)
    search_value = request.args.get("search[value]", "").strip().lower()

    records_total = len(all_data)

    if search_value:
        filtered = []
        for row in all_data:
            for v in row.values():
                if v is not None and search_value in str(v).lower():
                    filtered.append(row)
                    break
        all_data = filtered

    all_data = _apply_column_filters(all_data, request.args)
    records_filtered = len(all_data)

    order_col_idx = request.args.get("order[0][column]", None, type=int)
    order_dir = request.args.get("order[0][dir]", "asc")
    if order_col_idx is not None:
        col_name = request.args.get(f"columns[{order_col_idx}][data]", "")
        if col_name and all_data:
            all_data.sort(key=lambda r: _sort_key(r.get(col_name)), reverse=(order_dir == "desc"))

    page_data = all_data[start:start + length]

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": page_data,
    })


@bp.route("/api/dt/case/<int:case_id>/<entity>")
def datatable_entity(case_id, entity):
    """Server-side DataTables endpoint.

    Fetches all data from IRIS (cached), then filters/sorts/paginates
    in Python and returns DataTables-compatible JSON.
    """
    if entity not in ENTITIES:
        return jsonify({"error": "Invalid entity"}), 400

    ds = _get_data_source()
    bust = request.args.get("refresh") == "1"
    try:
        all_data = ds.get_entity(case_id, entity, bust_cache=bust)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        log.warning("IRIS API error for case %s entity %s: HTTP %s", case_id, entity, code)
        return jsonify({"error": "Failed to load entity data"}), code
    except Exception:
        log.error("Unexpected error for case %s entity %s", case_id, entity)
        return jsonify({"error": "Internal error"}), 500

    if not isinstance(all_data, list):
        all_data = []

    draw = request.args.get("draw", 1, type=int)
    start = max(0, request.args.get("start", 0, type=int))
    length = min(max(1, request.args.get("length", 25, type=int)), 500)
    search_value = request.args.get("search[value]", "").strip().lower()

    records_total = len(all_data)

    # Filter — global search
    if search_value:
        filtered = []
        for row in all_data:
            for v in row.values():
                if v is not None and search_value in str(v).lower():
                    filtered.append(row)
                    break
        all_data = filtered

    # Filter — per-column search
    all_data = _apply_column_filters(all_data, request.args)
    records_filtered = len(all_data)

    # Sort
    order_col_idx = request.args.get("order[0][column]", None, type=int)
    order_dir = request.args.get("order[0][dir]", "asc")

    if order_col_idx is not None:
        # Get column name from columns[N][data] parameter
        col_name = request.args.get(f"columns[{order_col_idx}][data]", "")
        if col_name and all_data:
            reverse = order_dir == "desc"
            all_data.sort(
                key=lambda r: _sort_key(r.get(col_name)),
                reverse=reverse,
            )

    # Paginate
    page_data = all_data[start:start + length]

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": page_data,
    })


def _sort_key(val):
    """Generate a sort key that handles None and mixed types."""
    if val is None:
        return ""
    return str(val).lower()


def _extract_column_filters(args):
    """Extract per-column search values from DataTables columns[N] params."""
    filters = {}
    idx = 0
    while True:
        col_data = args.get(f"columns[{idx}][data]")
        if col_data is None:
            break
        search_val = args.get(f"columns[{idx}][search][value]", "").strip()
        if search_val:
            filters[col_data] = search_val
        idx += 1
    return filters


def _apply_column_filters(data, args):
    """Apply per-column search filters from DataTables columns[N][search][value] params."""
    col_idx = 0
    while True:
        col_data = args.get(f"columns[{col_idx}][data]")
        if col_data is None:
            break
        search_val = args.get(f"columns[{col_idx}][search][value]", "").strip().lower()
        if search_val:
            data = [
                row for row in data
                if row.get(col_data) is not None
                and search_val in str(row[col_data]).lower()
            ]
        col_idx += 1
    return data


# ── Entity counts (for upfront badge loading) ────────────────────

@bp.route("/api/case/<int:case_id>/counts")
def case_entity_counts(case_id):
    """Return record counts for all entity types — used to populate tab badges on page load."""
    ds = _get_data_source()
    counts = {}
    for entity in ENTITIES:
        try:
            data = ds.get_entity(case_id, entity)
            counts[entity] = len(data) if isinstance(data, list) else 0
        except Exception:
            counts[entity] = 0
    return jsonify(counts)


# ── IRIS Lookup API (#4 — resolve IDs to human labels) ───────────

@bp.route("/api/lookups")
def api_lookups():
    """Return IRIS lookup tables (asset types, IOC types, TLP, etc.) for client-side label resolution."""
    lookups = {}

    try:
        from . import iris_api

        # Try common IRIS lookup endpoints
        lookup_endpoints = {
            'asset_type': '/manage/asset-type/list',
            'ioc_type': '/manage/ioc-types/list',
            'tlp': '/manage/tlp/list',
            'case_status': '/manage/case-states/list',
            'severity': '/manage/severities/list',
            'task_status': '/manage/task-status/list',
            'compromise_status': '/manage/compromise-status/list',
        }

        for key, endpoint in lookup_endpoints.items():
            try:
                result = iris_api._get(endpoint)
                data = result.get('data', result) if isinstance(result, dict) else result
                mapping = {}
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            # IRIS returns different key patterns; try common ones
                            item_id = (
                                item.get(f'{key}_id') or
                                item.get('id') or
                                item.get(f'{key.split("_")[0]}_id')
                            )
                            item_name = (
                                item.get(f'{key}_name') or
                                item.get('name') or
                                item.get(f'{key.split("_")[0]}_name') or
                                item.get('status_name') or
                                item.get('severity_name') or
                                item.get('type_name') or
                                item.get('tlp_name')
                            )
                            if item_id is not None and item_name:
                                mapping[str(item_id)] = item_name
                lookups[key] = mapping
            except Exception:
                lookups[key] = {}
    except Exception:
        log.warning("Failed to fetch IRIS lookups")

    return jsonify(lookups)


# ── Case neighbors (#8 — previous/next case navigation) ─────────

@bp.route("/api/case-neighbors/<int:case_id>")
def case_neighbors(case_id):
    """Return the previous and next case IDs for sequential navigation."""
    ds = _get_data_source()
    try:
        all_cases = ds.get_cases_list()
    except Exception:
        return jsonify({"prev": None, "next": None})

    if not isinstance(all_cases, list):
        return jsonify({"prev": None, "next": None})

    # Sort by case_id
    ids = sorted(set(c.get("case_id") for c in all_cases if c.get("case_id") is not None))

    prev_id = None
    next_id = None
    try:
        idx = ids.index(case_id)
        if idx > 0:
            prev_id = ids[idx - 1]
        if idx < len(ids) - 1:
            next_id = ids[idx + 1]
    except ValueError:
        pass

    return jsonify({"prev": prev_id, "next": next_id})


# ── JSON API (full dump, kept for programmatic access) ───────────

@bp.route("/api/case/<int:case_id>")
def case_api(case_id):
    ds = _get_data_source()
    try:
        data = ds.get_case_data(case_id)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        log.warning("IRIS API error for case %s full data: HTTP %s", case_id, code)
        return jsonify({"status": "error", "message": "Failed to load case data"}), code
    except Exception:
        log.error("Unexpected error loading case %s data", case_id)
        return jsonify({"status": "error", "message": "Internal error"}), 500
    return jsonify({"status": "success", "data": data})


@bp.route("/health")
@limiter.exempt
def health():
    return jsonify({"status": "ok"})


# ── Shadowserver routes ──────────────────────────────────────────

@bp.route("/shadowserver")
def shadowserver():
    if not current_app.config.get("SS_ENABLED"):
        return render_template("error.html", error="Shadowserver integration is not enabled"), 404
    return render_template("shadowserver.html")


@bp.route("/api/dt/shadowserver")
def datatable_shadowserver():
    """True server-side DataTables endpoint — SQL LIMIT/OFFSET pagination."""
    if not current_app.config.get("SS_ENABLED"):
        return jsonify({"error": "Shadowserver not enabled"}), 404

    from . import shadowserver_db as ss_db

    draw = request.args.get("draw", 1, type=int)
    start = max(0, request.args.get("start", 0, type=int))
    length = min(max(1, request.args.get("length", 25, type=int)), 500)
    search_value = request.args.get("search[value]", "").strip()
    report_type = request.args.get("report_type", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None
    order_column = request.args.get("order_column", "report_date")
    order_dir = request.args.get("order_dir", "desc")

    column_filters = _extract_column_filters(request.args)

    try:
        return jsonify(ss_db.query_events(
            draw=draw, start=start, length=length,
            search_value=search_value, report_type=report_type,
            date_from=date_from, date_to=date_to,
            order_column=order_column, order_dir=order_dir,
            column_filters=column_filters,
        ))
    except Exception:
        log.error("Shadowserver query_events error")
        return jsonify({"error": "Failed to query Shadowserver data"}), 500


@bp.route("/api/dt/case/<int:case_id>/shadowserver")
def datatable_case_shadowserver(case_id):
    """Shadowserver tab inside case explorer — correlates by IPs, hostnames, ASNs."""
    if not current_app.config.get("SS_ENABLED"):
        return jsonify({"error": "Shadowserver not enabled"}), 404

    from . import shadowserver_db as ss_db

    # 1. Get case IOCs and assets to extract indicators
    ds = _get_data_source()
    bust = request.args.get("refresh") == "1"

    ips = set()
    hostnames = set()
    asns = set()

    try:
        iocs = ds.get_entity(case_id, "iocs", bust_cache=bust)
        for ioc in (iocs or []):
            val = ioc.get("ioc_value") or ""
            ioc_type = str(ioc.get("ioc_type_id", ioc.get("ioc_type", "")))
            # IP types (exact ID depends on IRIS config, also try by value pattern)
            if _looks_like_ip(val):
                ips.add(val.strip())
            elif _looks_like_domain(val):
                hostnames.add(val.strip().lower())
            elif ioc_type in ("asn",) or val.startswith("AS"):
                try:
                    asns.add(int(val.replace("AS", "").strip()))
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    try:
        assets = ds.get_entity(case_id, "assets", bust_cache=bust)
        for asset in (assets or []):
            ip = asset.get("asset_ip") or ""
            if ip.strip():
                ips.add(ip.strip())
            domain = asset.get("asset_domain") or ""
            if domain.strip():
                hostnames.add(domain.strip().lower())
    except Exception:
        pass

    # 2. Query Shadowserver events matching these indicators
    draw = request.args.get("draw", 1, type=int)
    start = max(0, request.args.get("start", 0, type=int))
    length = min(max(1, request.args.get("length", 25, type=int)), 500)
    search_value = request.args.get("search[value]", "").strip()
    order_column = request.args.get("order_column", "report_date")
    order_dir = request.args.get("order_dir", "desc")

    column_filters = _extract_column_filters(request.args)

    try:
        result = ss_db.query_events_by_indicators(
            draw=draw, start=start, length=length,
            ips=list(ips), hostnames=list(hostnames), asns=list(asns),
            search_value=search_value,
            order_column=order_column, order_dir=order_dir,
            column_filters=column_filters,
        )
        # #17: Add indicator count feedback
        result["indicators"] = {
            "ips": len(ips),
            "hostnames": len(hostnames),
            "asns": len(asns),
        }
        return jsonify(result)
    except Exception:
        log.error("Shadowserver case correlation error for case %s", case_id)
        return jsonify({"error": "Failed to query Shadowserver data"}), 500


def _looks_like_ip(val):
    """Quick check if a string looks like an IPv4 or IPv6 address."""
    if not val or not val.strip():
        return False
    val = val.strip()
    # IPv4
    parts = val.split(".")
    if len(parts) == 4:
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    # IPv6 (contains colons)
    return ":" in val and all(c in "0123456789abcdefABCDEF:" for c in val)


def _looks_like_domain(val):
    """Quick check if a string looks like a domain name."""
    if not val or not val.strip():
        return False
    val = val.strip().lower()
    return "." in val and not _looks_like_ip(val) and all(
        c.isalnum() or c in ".-_" for c in val
    )


@bp.route("/api/shadowserver/stats")
def shadowserver_stats():
    if not current_app.config.get("SS_ENABLED"):
        return jsonify({"error": "Shadowserver not enabled"}), 404

    from . import shadowserver_db as ss_db

    try:
        stats = ss_db.get_stats()
        # Serialize dates for JSON
        for key in ("earliest_date", "latest_date"):
            if stats.get(key):
                stats[key] = str(stats[key])
        for run in stats.get("recent_runs", []):
            for k in ("run_started", "run_finished"):
                if run.get(k):
                    run[k] = run[k].isoformat()
        return jsonify(stats)
    except Exception:
        log.error("Shadowserver stats error")
        return jsonify({"error": "Failed to load stats"}), 500


@bp.route("/api/shadowserver/report-types")
def shadowserver_report_types():
    if not current_app.config.get("SS_ENABLED"):
        return jsonify({"error": "Shadowserver not enabled"}), 404

    from . import shadowserver_db as ss_db

    try:
        return jsonify(ss_db.get_report_types())
    except Exception:
        log.error("Shadowserver report-types error")
        return jsonify({"error": "Failed to load report types"}), 500
