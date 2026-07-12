import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from watcher.models import WatchTarget
from watcher.parser import evaluate_sale_period
from watcher.service import WatchService, build_important_payload
from watcher.state_store import SQLiteStateStore


class StaticFetcher:
    def __init__(self, html: str):
        self.html = html

    def fetch(self, url: str) -> str:
        return self.html


class RecordingNotifier:
    def __init__(self, *, fail_sale: bool = False):
        self.fail_sale = fail_sale
        self.sale_calls = 0

    def send_sale_notification(self, *args, **kwargs) -> None:
        self.sale_calls += 1
        if self.fail_sale:
            raise RuntimeError("LINE push failed")

    def send_error_notification(self, *args, **kwargs) -> None:
        return None

    def send_recovery_notification(self, *args, **kwargs) -> None:
        return None


class WatchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = WatchTarget(
            document_id="jal_domestic_sale",
            airline="JAL",
            url="https://example.com/sale",
        )
        self.sale_html = """
        <html><body>
          <h1>タイムセール</h1>
          <p>販売期間 2026/7/14-2026/7/15</p>
          <p>搭乗期間 2026/8/24-2026/9/30</p>
          <p>対象運賃 プロモーション</p>
        </body></html>
        """

    def _build_service(self, notifier: RecordingNotifier) -> tuple[WatchService, SQLiteStateStore]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        store = SQLiteStateStore(str(Path(tmpdir.name) / "watch.sqlite3"))
        service = WatchService(
            (self.target,),
            StaticFetcher(self.sale_html),
            store,
            notifier,
        )
        return service, store

    def test_sale_notification_failure_keeps_change_detectable(self):
        notifier = RecordingNotifier(fail_sale=True)
        service, store = self._build_service(notifier)

        first = service.run(dry_run=False)
        second = service.run(dry_run=False)
        state = store.load(self.target.document_id, self.target.airline, self.target.url)

        self.assertFalse(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(notifier.sale_calls, 2)
        self.assertTrue(first["results"][0]["changed"])
        self.assertTrue(second["results"][0]["changed"])
        self.assertEqual(state.last_hash, "")
        self.assertEqual(state.last_notified_hash, "")

    def test_successful_sale_notification_persists_hashes(self):
        notifier = RecordingNotifier()
        service, store = self._build_service(notifier)

        result = service.run(dry_run=False)
        state = store.load(self.target.document_id, self.target.airline, self.target.url)
        _, expected_hash = build_important_payload(self.sale_html)

        self.assertTrue(result["ok"])
        self.assertTrue(result["results"][0]["notified"])
        self.assertEqual(result["results"][0]["content_hash"], expected_hash)
        self.assertEqual(state.last_hash, expected_hash)
        self.assertEqual(state.last_notified_hash, expected_hash)

    def test_unchanged_sale_page_still_reports_sale_period_status(self):
        notifier = RecordingNotifier()
        service, _ = self._build_service(notifier)

        service.run(dry_run=False)
        second = service.run(dry_run=False)
        result = second["results"][0]
        expected_status = evaluate_sale_period(
            result["important_text"],
            reference_datetime=datetime.fromisoformat(result["checked_at"]),
        )

        self.assertTrue(second["ok"])
        self.assertFalse(result["changed"])
        self.assertEqual(result["sale_period_status"], expected_status.status)


if __name__ == "__main__":
    unittest.main()
