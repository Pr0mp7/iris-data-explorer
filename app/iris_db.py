import psycopg2
import psycopg2.extras
from flask import current_app

_pool = None


def _get_conn():
    """Get a PostgreSQL connection using app config."""
    return psycopg2.connect(
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        dbname=current_app.config["DB_NAME"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
    )


def _query(sql, params=None):
    """Execute a query and return all rows as dicts."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _query_one(sql, params=None):
    """Execute a query and return a single row as dict."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_case_summary(case_id):
    return _query_one(
        """
        SELECT c.case_id, c.name AS case_name, c.description,
               c.open_date, c.close_date, c.soc_id,
               c.status_id, c.severity_id,
               c.classification_id, c.owner_id,
               c.custom_attributes
        FROM cases c
        WHERE c.case_id = %s
        """,
        (case_id,),
    )


def get_case_assets(case_id):
    return _query(
        """
        SELECT ca.asset_id, ca.asset_name, ca.asset_description,
               ca.asset_ip, ca.asset_domain, ca.asset_compromise_status_id,
               ca.asset_type_id, ca.analysis_status_id,
               ca.date_added, ca.date_update,
               ca.custom_attributes
        FROM case_assets ca
        WHERE ca.case_id = %s
        ORDER BY ca.date_added DESC
        """,
        (case_id,),
    )


def get_case_iocs(case_id):
    return _query(
        """
        SELECT i.ioc_id, i.ioc_value, i.ioc_description,
               i.ioc_type_id, i.ioc_tlp_id,
               i.ioc_tags, i.custom_attributes,
               il.ioc_link_id
        FROM ioc i
        JOIN ioc_link il ON i.ioc_id = il.ioc_id
        WHERE il.case_id = %s
        ORDER BY i.ioc_id DESC
        """,
        (case_id,),
    )


def get_case_events(case_id):
    return _query(
        """
        SELECT ce.event_id, ce.event_title, ce.event_content,
               ce.event_raw, ce.event_source, ce.event_date,
               ce.event_tz, ce.event_in_summary,
               ce.event_in_graph, ce.event_color,
               ce.event_tags, ce.custom_attributes,
               ce.modification_history
        FROM cases_events ce
        WHERE ce.case_id = %s
        ORDER BY ce.event_date DESC
        """,
        (case_id,),
    )


def get_case_tasks(case_id):
    return _query(
        """
        SELECT ct.id AS task_id, ct.task_title, ct.task_description,
               ct.task_status_id, ct.task_tags,
               ct.task_open_date, ct.task_close_date,
               ct.custom_attributes
        FROM case_tasks ct
        WHERE ct.case_id = %s
        ORDER BY ct.task_open_date DESC
        """,
        (case_id,),
    )


def get_case_notes(case_id):
    return _query(
        """
        SELECT n.note_id, n.note_title, n.note_content,
               n.note_creationdate, n.note_lastupdate,
               n.custom_attributes
        FROM notes n
        JOIN notes_group ng ON n.note_group_id = ng.group_id
        WHERE ng.group_case_id = %s
        ORDER BY n.note_lastupdate DESC
        """,
        (case_id,),
    )


def get_case_evidences(case_id):
    return _query(
        """
        SELECT crf.id AS evidence_id, crf.filename,
               crf.file_description, crf.file_hash,
               crf.file_size, crf.date_added,
               crf.custom_attributes
        FROM case_received_file crf
        WHERE crf.case_id = %s
        ORDER BY crf.date_added DESC
        """,
        (case_id,),
    )


def get_entity(case_id, entity):
    """Fetch a single entity type for a case."""
    fetchers = {
        "case": get_case_summary,
        "assets": get_case_assets,
        "iocs": get_case_iocs,
        "events": get_case_events,
        "tasks": get_case_tasks,
        "notes": get_case_notes,
        "evidences": get_case_evidences,
    }
    return fetchers[entity](case_id)


def get_case_data(case_id):
    """Fetch all case entities via direct PostgreSQL queries."""
    summary = get_case_summary(case_id)
    if not summary:
        raise ValueError(f"Case {case_id} not found")
    return {
        "case": summary,
        "assets": get_case_assets(case_id),
        "iocs": get_case_iocs(case_id),
        "events": get_case_events(case_id),
        "tasks": get_case_tasks(case_id),
        "notes": get_case_notes(case_id),
        "evidences": get_case_evidences(case_id),
    }


def get_cases_list():
    """Fetch list of all cases."""
    return _query(
        """
        SELECT c.case_id, c.name AS case_name, c.description,
               c.open_date, c.close_date, c.soc_id,
               c.status_id, c.severity_id, c.owner_id
        FROM cases c
        ORDER BY c.case_id DESC
        """
    )
