from requests.exceptions import HTTPError

from flask import Blueprint, render_template, jsonify, current_app

from .auth import validate_api_key

bp = Blueprint("main", __name__)
bp.before_request(validate_api_key)


def _get_data_source():
    if current_app.config["DATA_SOURCE"] == "db":
        from . import iris_db
        return iris_db
    from . import iris_api
    return iris_api


@bp.route("/")
def index():
    """Show all cases list."""
    ds = _get_data_source()
    try:
        cases = ds.get_cases_list()
    except Exception as e:
        return render_template("error.html", error=str(e)), 500
    return render_template("cases.html", cases=cases)


@bp.route("/case/<int:case_id>")
def case_explorer(case_id):
    """Render interactive explorer page for a case."""
    ds = _get_data_source()
    try:
        data = ds.get_case_data(case_id)
    except HTTPError as e:
        code = e.response.status_code if e.response is not None else 500
        return render_template("error.html", error=str(e)), code
    except Exception as e:
        return render_template("error.html", error=str(e)), 500
    return render_template("explorer.html", case_id=case_id, data=data)


@bp.route("/api/case/<int:case_id>")
def case_api(case_id):
    """JSON endpoint returning all case entities."""
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
