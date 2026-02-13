"""Read-only Shadowserver PostgreSQL queries with true server-side pagination."""

import json

import psycopg2
import psycopg2.extras
from flask import current_app


def _get_conn():
    return psycopg2.connect(
        host=current_app.config["SS_DB_HOST"],
        port=current_app.config["SS_DB_PORT"],
        dbname=current_app.config["SS_DB_NAME"],
        user=current_app.config["SS_DB_USER"],
        password=current_app.config["SS_DB_PASSWORD"],
    )


def get_stats():
    """Summary stats for the dashboard cards."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM ss_events) AS total_events,
                    (SELECT COUNT(DISTINCT report_type) FROM ss_events) AS report_types,
                    (SELECT MIN(report_date) FROM ss_events) AS earliest_date,
                    (SELECT MAX(report_date) FROM ss_events) AS latest_date
            """)
            stats = dict(cur.fetchone())

            cur.execute("""
                SELECT run_started, run_finished, status,
                       reports_found, events_ingested, events_skipped, error_message
                FROM ss_ingestion_log
                ORDER BY id DESC
                LIMIT 10
            """)
            stats["recent_runs"] = [dict(r) for r in cur.fetchall()]

            return stats
    finally:
        conn.close()


def get_report_types():
    """List distinct report types for the filter dropdown."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT report_type FROM ss_events ORDER BY report_type")
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def query_events(draw, start, length, search_value="",
                 report_type=None, date_from=None, date_to=None,
                 order_column="report_date", order_dir="desc"):
    """True server-side paginated query — SQL LIMIT/OFFSET, not in-memory.

    Returns DataTables-compatible dict: {draw, recordsTotal, recordsFiltered, data}.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Total count (unfiltered)
            cur.execute("SELECT COUNT(*) FROM ss_events")
            records_total = cur.fetchone()["count"]

            # Build WHERE clause
            conditions = []
            params = []

            if report_type:
                conditions.append("report_type = %s")
                params.append(report_type)
            if date_from:
                conditions.append("report_date >= %s")
                params.append(date_from)
            if date_to:
                conditions.append("report_date <= %s")
                params.append(date_to)
            if search_value:
                conditions.append("""(
                    ip::TEXT ILIKE %s OR hostname ILIKE %s OR
                    tag ILIKE %s OR geo ILIKE %s OR
                    report_type ILIKE %s OR
                    raw_data::TEXT ILIKE %s
                )""")
                like = f"%{search_value}%"
                params.extend([like] * 6)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            # Filtered count
            cur.execute(f"SELECT COUNT(*) FROM ss_events {where}", params)
            records_filtered = cur.fetchone()["count"]

            # Validate order column to prevent SQL injection
            allowed_cols = {
                "report_date", "report_type", "ip", "port", "asn",
                "geo", "hostname", "tag", "severity", "ingested_at",
            }
            if order_column not in allowed_cols:
                order_column = "report_date"
            if order_dir not in ("asc", "desc"):
                order_dir = "desc"

            # Paginated query
            cur.execute(
                f"""
                SELECT id, report_type, report_date, ip, port, asn, geo,
                       hostname, tag, severity, raw_data, ingested_at
                FROM ss_events {where}
                ORDER BY {order_column} {order_dir} NULLS LAST
                LIMIT %s OFFSET %s
                """,
                params + [length, start],
            )
            rows = []
            for row in cur.fetchall():
                d = dict(row)
                # Serialize types for JSON
                d["report_date"] = str(d["report_date"]) if d["report_date"] else None
                d["ingested_at"] = d["ingested_at"].isoformat() if d["ingested_at"] else None
                d["ip"] = str(d["ip"]) if d["ip"] else None
                if isinstance(d["raw_data"], str):
                    d["raw_data"] = json.loads(d["raw_data"])
                rows.append(d)

            return {
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": rows,
            }
    finally:
        conn.close()
