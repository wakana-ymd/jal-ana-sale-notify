import unittest

from watcher.parser import (
    compute_hash,
    extract_important_lines,
    extract_text,
    is_notify_target,
    normalize_text,
)


class ParserLogicTests(unittest.TestCase):
    def test_extract_text_removes_noise_tags(self):
        html = """
        <html>
          <body>
            <nav>menu</nav>
            <main><h1>タイムセール</h1><p>販売期間 7/1-7/10</p></main>
            <footer>footer</footer>
          </body>
        </html>
        """
        text = extract_text(html)
        self.assertIn("タイムセール", text)
        self.assertIn("販売期間 7/1-7/10", text)
        self.assertNotIn("menu", text)
        self.assertNotIn("footer", text)

    def test_normalize_text_compacts_whitespace(self):
        raw = "  タイムセール　 \r\n\r\n  販売期間   7/1 - 7/10 "
        normalized = normalize_text(raw)
        self.assertEqual(normalized, "タイムセール\n販売期間 7/1 - 7/10")

    def test_extract_important_lines_filters_keywords(self):
        text = "\n".join(
            [
                "通常のお知らせ",
                "タイムセール開始予定",
                "販売期間 7/1-7/10",
                "関係ない行",
            ]
        )
        important = extract_important_lines(text)
        self.assertEqual(important, "タイムセール開始予定\n販売期間 7/1-7/10")

    def test_is_notify_target_matches_spec(self):
        text = "タイムセール\n販売期間 7/1-7/10\n搭乗期間 8/1-8/31"
        current_hash = compute_hash(text)
        self.assertTrue(is_notify_target(text, current_hash, "previous"))
        self.assertFalse(is_notify_target("お知らせのみ", current_hash, "previous"))
        self.assertFalse(is_notify_target(text, current_hash, current_hash))


if __name__ == "__main__":
    unittest.main()
