import tempfile
import unittest
from pathlib import Path

from watcher.models import WatchState
from watcher.state_store import SQLiteStateStore


class SQLiteStateStoreTests(unittest.TestCase):
    def test_load_returns_empty_state_for_missing_document(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStateStore(str(Path(tmpdir) / "watch.sqlite3"))
            state = store.load("jal_domestic_sale", "JAL", "https://example.com")
            self.assertEqual(state.airline, "JAL")
            self.assertEqual(state.url, "https://example.com")
            self.assertEqual(state.last_hash, "")

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStateStore(str(Path(tmpdir) / "watch.sqlite3"))
            original = WatchState(
                airline="ANA",
                url="https://example.com/ana",
                last_hash="abc",
                last_notified_hash="def",
                last_important_text="sale",
                last_checked_at="2026-07-04T10:00:00+09:00",
                last_changed_at="2026-07-04T10:00:00+09:00",
                consecutive_error_count=2,
                last_error="timeout",
                is_error_notified=True,
            )
            store.save("ana_domestic_sale", original)

            loaded = store.load(
                "ana_domestic_sale", "ANA", "https://should-not-be-used.example"
            )
            self.assertEqual(loaded.airline, original.airline)
            self.assertEqual(loaded.url, original.url)
            self.assertEqual(loaded.last_hash, original.last_hash)
            self.assertEqual(loaded.last_notified_hash, original.last_notified_hash)
            self.assertEqual(loaded.last_important_text, original.last_important_text)
            self.assertEqual(
                loaded.consecutive_error_count, original.consecutive_error_count
            )
            self.assertEqual(loaded.last_error, original.last_error)
            self.assertEqual(loaded.is_error_notified, original.is_error_notified)


if __name__ == "__main__":
    unittest.main()
