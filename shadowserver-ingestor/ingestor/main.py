"""Shadowserver Ingestor — entry point with APScheduler and health endpoint."""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from threading import Thread

from http.server import HTTPServer, BaseHTTPRequestHandler

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import Config
from .api_client import ShadowserverClient
from .schema import ensure_schema
from . import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ingestor")

# Global state for health endpoint
_last_run_status = {"status": "starting", "time": None}


def ingest_date(client, date_str):
    """Ingest all reports for a single date. Returns (total_inserted, total_skipped, report_count)."""
    log.info("Listing reports for %s...", date_str)
    try:
        report_types = client.list_reports(date_str)
    except Exception as e:
        log.error("Failed to list reports for %s: %s", date_str, e)
        return 0, 0, 0

    if not report_types:
        log.info("No reports available for %s", date_str)
        return 0, 0, 0

    # reports/list returns dicts with 'type', 'id', 'file', etc.
    # Extract unique type strings for querying
    type_names = sorted(set(
        r["type"] for r in report_types if isinstance(r, dict) and "type" in r
    ))
    log.info("Found %d unique report types for %s", len(type_names), date_str)
    total_inserted = 0
    total_skipped = 0

    for report_type in type_names:
        try:
            report_inserted = 0
            report_skipped = 0
            for batch in client.fetch_all_events(date_str, report_type):
                ins, skip = db.upsert_events(report_type, date_str, batch)
                report_inserted += ins
                report_skipped += skip

            db.upsert_report(report_type, date_str, report_inserted)
            total_inserted += report_inserted
            total_skipped += report_skipped
            log.info("  %s/%s: %d inserted, %d skipped",
                     date_str, report_type, report_inserted, report_skipped)
        except Exception as e:
            log.error("  Error processing %s/%s: %s", date_str, report_type, e)
            continue

        time.sleep(Config.REQUEST_DELAY_SECONDS)

    return total_inserted, total_skipped, len(type_names)


def run_ingestion():
    """Main ingestion cycle: fetch yesterday + today."""
    global _last_run_status
    log.info("=== Ingestion run starting ===")

    log_id = db.start_ingestion_log()
    total_inserted = 0
    total_skipped = 0
    total_reports = 0

    try:
        client = ShadowserverClient()
        today = datetime.utcnow().date()
        dates = [today - timedelta(days=1), today]

        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            ins, skip, rcount = ingest_date(client, date_str)
            total_inserted += ins
            total_skipped += skip
            total_reports += rcount

        db.finish_ingestion_log(log_id, "success", total_reports, total_inserted, total_skipped)
        _last_run_status = {"status": "ok", "time": datetime.utcnow().isoformat()}
        log.info("=== Ingestion complete: %d inserted, %d skipped across %d reports ===",
                 total_inserted, total_skipped, total_reports)

    except Exception as e:
        log.error("=== Ingestion failed: %s ===", e)
        db.finish_ingestion_log(log_id, "error", total_reports, total_inserted, total_skipped, str(e))
        _last_run_status = {"status": "error", "time": datetime.utcnow().isoformat(), "error": str(e)}


def run_backfill(client, days):
    """Backfill the last N days of data."""
    log.info("=== Backfill starting (%d days) ===", days)
    log_id = db.start_ingestion_log()
    total_inserted = 0
    total_skipped = 0
    total_reports = 0

    try:
        today = datetime.utcnow().date()
        for i in range(days, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            ins, skip, rcount = ingest_date(client, date_str)
            total_inserted += ins
            total_skipped += skip
            total_reports += rcount

        db.finish_ingestion_log(log_id, "success", total_reports, total_inserted, total_skipped)
        log.info("=== Backfill complete: %d inserted, %d skipped ===", total_inserted, total_skipped)
    except Exception as e:
        log.error("=== Backfill failed: %s ===", e)
        db.finish_ingestion_log(log_id, "error", total_reports, total_inserted, total_skipped, str(e))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        import json
        self.wfile.write(json.dumps(_last_run_status).encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


def start_health_server():
    server = HTTPServer(("0.0.0.0", Config.HEALTH_PORT), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Health endpoint listening on port %d", Config.HEALTH_PORT)


def main():
    parser = argparse.ArgumentParser(description="Shadowserver Ingestor")
    parser.add_argument("--ping", action="store_true", help="Test API connectivity and exit")
    parser.add_argument("--once", action="store_true", help="Run one ingestion cycle and exit")
    parser.add_argument("--backfill", type=int, metavar="DAYS", help="Backfill N days and exit")
    args = parser.parse_args()

    if not Config.SS_API_KEY or not Config.SS_API_SECRET:
        log.error("SS_API_KEY and SS_API_SECRET must be set")
        sys.exit(1)

    client = ShadowserverClient()

    if args.ping:
        result = client.ping()
        log.info("Ping result: %s", result)
        sys.exit(0)

    ensure_schema()

    if args.backfill:
        run_backfill(client, args.backfill)
        sys.exit(0)

    if args.once:
        run_ingestion()
        sys.exit(0)

    # Normal mode: backfill on first start, then schedule
    start_health_server()
    log.info("Running initial backfill of %d days...", Config.BACKFILL_DAYS)
    run_backfill(client, Config.BACKFILL_DAYS)

    log.info("Starting scheduler (every %d minutes)...", Config.INGEST_INTERVAL_MINUTES)
    scheduler = BlockingScheduler()
    scheduler.add_job(run_ingestion, "interval", minutes=Config.INGEST_INTERVAL_MINUTES)
    scheduler.start()


if __name__ == "__main__":
    main()
