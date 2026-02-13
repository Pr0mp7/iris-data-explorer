"""Shadowserver API client with HMAC-SHA256 authentication."""

import hashlib
import hmac
import json
import logging
import time

import requests

from .config import Config

log = logging.getLogger(__name__)


class ShadowserverClient:
    def __init__(self):
        self.api_url = Config.SS_API_URL.rstrip("/")
        self.api_key = Config.SS_API_KEY
        self.api_secret = Config.SS_API_SECRET
        self.page_size = Config.PAGE_SIZE
        self.request_delay = Config.REQUEST_DELAY_SECONDS

    def _sign(self, data):
        return hmac.new(
            self.api_secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _call(self, method, params=None):
        url = f"{self.api_url}/{method}"
        body = params or {}
        body["apikey"] = self.api_key

        body_json = json.dumps(body, sort_keys=True)
        signature = self._sign(body_json)

        resp = requests.post(
            url,
            data=body_json,
            headers={"Content-Type": "application/json", "HMAC2": signature},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def ping(self):
        """Test API connectivity."""
        return self._call("test/ping")

    def list_reports(self, date_str):
        """List available reports for a date (YYYY-MM-DD)."""
        result = self._call("reports/list", {"date": date_str})
        return result if isinstance(result, list) else []

    def query_report(self, date_str, report_type, page=1):
        """Fetch one page of events for a report type + date.

        Uses reports/query with 'query' dict per Shadowserver API spec.
        Max limit per page is 1000.
        """
        limit = min(self.page_size, 1000)
        result = self._call("reports/query", {
            "date": date_str,
            "query": {"type": report_type},
            "page": page,
            "limit": limit,
        })
        return result if isinstance(result, list) else []

    def fetch_all_events(self, date_str, report_type):
        """Fetch all pages for a report. Yields batches (lists) of events."""
        page = 1  # Shadowserver API pages start at 1
        limit = min(self.page_size, 1000)
        while True:
            log.info("  Fetching %s/%s page %d...", date_str, report_type, page)
            events = self.query_report(date_str, report_type, page=page)
            if not events:
                break
            yield events
            if len(events) < limit:
                break
            page += 1
            time.sleep(self.request_delay)
