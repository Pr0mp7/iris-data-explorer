import re

from requests.exceptions import HTTPError

from flask import (
    Blueprint, render_template, jsonify, request,
    current_app, session, redirect, url_for,
)

from .auth import require_auth, validate_key_against_iris, get_api_key

bp = Blueprint("main", __name__)
bp.before_request(require_auth)


def _get_data_source():
    if current_app.config["DATA_SOURCE"] == "db":
        from . import iris_db
        return iris_db
    from . import iris_api
    return iris_api


# ── Auth routes ──────────────────────────────────────────────────

@bp.route("/login", methods=["GET", "POST"])
def login():
    # If env key is set (service mode), skip login
    if current_app.config["IRIS_API_KEY"]:
        return redirect(url_for("main.index"))

    error = None
    if request.method == "POST":
        api_key = request.form.get("api_key", "").strip()
        if not api_key:
            error = "API key is required"
        else:
            valid, msg = validate_key_against_iris(api_key)
            if valid:
                session["api_key"] = api_key
                next_url = request.args.get("next", url_for("main.index"))
                return redirect(next_url)
            else:
                error = msg or "Invalid API key"

    return render_template("login.html", error=error,
                           iris_url=current_app.config["IRIS_EXTERNAL_URL"])


@bp.route("/logout")
def logout():
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
    ds = _get_data_source()
    try:
        case_info = ds.get_case_summary(case_id)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        return render_template("error.html", error=str(e)), code
    except Exception as e:
        return render_template("error.html", error=str(e)), 500
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not isinstance(all_data, list):
        all_data = []

    draw = request.args.get("draw", 1, type=int)
    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 25, type=int)
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
        return jsonify({"error": str(e)}), code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not isinstance(all_data, list):
        all_data = []

    draw = request.args.get("draw", 1, type=int)
    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 25, type=int)
    search_value = request.args.get("search[value]", "").strip().lower()

    records_total = len(all_data)

    # Filter
    if search_value:
        filtered = []
        for row in all_data:
            for v in row.values():
                if v is not None and search_value in str(v).lower():
                    filtered.append(row)
                    break
        all_data = filtered

    records_filtered = len(all_data)

    # Sort
    order_col_idx = request.args.get("order[0][column]", None, type=int)
    order_dir = request.args.get("order[0][dir]", "asc")
    columns_param = request.args.get("columns", "")

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


# ── JSON API (full dump, kept for programmatic access) ───────────

@bp.route("/api/case/<int:case_id>")
def case_api(case_id):
    ds = _get_data_source()
    try:
        data = ds.get_case_data(case_id)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        return jsonify({"status": "error", "message": str(e)}), code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "success", "data": data})


@bp.route("/health")
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
    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 25, type=int)
    search_value = request.args.get("search[value]", "").strip()
    report_type = request.args.get("report_type", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None
    order_column = request.args.get("order_column", "report_date")
    order_dir = request.args.get("order_dir", "desc")

    try:
        return jsonify(ss_db.query_events(
            draw=draw, start=start, length=length,
            search_value=search_value, report_type=report_type,
            date_from=date_from, date_to=date_to,
            order_column=order_column, order_dir=order_dir,
        ))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 25, type=int)
    search_value = request.args.get("search[value]", "").strip()
    order_column = request.args.get("order_column", "report_date")
    order_dir = request.args.get("order_dir", "desc")

    try:
        return jsonify(ss_db.query_events_by_indicators(
            draw=draw, start=start, length=length,
            ips=list(ips), hostnames=list(hostnames), asns=list(asns),
            search_value=search_value,
            order_column=order_column, order_dir=order_dir,
        ))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/shadowserver/report-types")
def shadowserver_report_types():
    if not current_app.config.get("SS_ENABLED"):
        return jsonify({"error": "Shadowserver not enabled"}), 404

    from . import shadowserver_db as ss_db

    try:
        return jsonify(ss_db.get_report_types())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
