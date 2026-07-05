import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from watcher.fetcher import decode_html
from watcher.models import WatchTarget
from watcher.notifier import build_sale_notification_text
from watcher.parser import (
    SALE_PERIOD_IN_WINDOW,
    SALE_PERIOD_OUT_OF_WINDOW,
    SALE_PERIOD_UNKNOWN,
    evaluate_sale_period,
    extract_important_lines,
    extract_text,
    is_notify_target,
    normalize_text,
    parse_period_line,
)


class ParserLogicTests(unittest.TestCase):
    jst = ZoneInfo("Asia/Tokyo")
    target = WatchTarget(
        document_id="jal_domestic_sale",
        airline="JAL",
        url="https://example.com/sale",
    )

    def test_decode_html_prefers_meta_charset_over_wrong_header_guess(self):
        html_bytes = (
            '<html><head><meta charset="utf-8"></head>'
            '<body>国内航空券タイムセール 販売期間 搭乗期間</body></html>'
        ).encode("utf-8")
        decoded = decode_html(html_bytes, "ISO-8859-1")
        self.assertIn("国内航空券タイムセール", decoded)

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
        self.assertTrue(is_notify_target(text))
        self.assertFalse(is_notify_target("お知らせのみ"))

    def test_parse_period_line_uses_reference_year_when_omitted(self):
        parsed = parse_period_line("販売期間 7/1-7/10", reference_date=datetime(2026, 6, 20).date())
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.start.isoformat(), "2026-07-01")
        self.assertEqual(parsed.end.isoformat(), "2026-07-10")

    def test_parse_period_line_handles_year_boundary(self):
        parsed = parse_period_line(
            "販売期間 12/29-1/5",
            reference_date=datetime(2026, 12, 1).date(),
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.start.isoformat(), "2026-12-29")
        self.assertEqual(parsed.end.isoformat(), "2027-01-05")

    def test_evaluate_sale_period_marks_in_window_with_margin(self):
        important_text = "タイムセール\n販売期間 2026/7/1-2026/7/10\n搭乗期間 2026/8/1-2026/8/31"
        evaluation = evaluate_sale_period(
            important_text,
            reference_datetime=datetime(2026, 7, 11, 9, 0, tzinfo=self.jst),
        )
        self.assertEqual(evaluation.status, SALE_PERIOD_IN_WINDOW)

    def test_evaluate_sale_period_marks_out_of_window(self):
        important_text = "タイムセール\n販売期間 2026/7/1-2026/7/10\n搭乗期間 2026/8/1-2026/8/31"
        evaluation = evaluate_sale_period(
            important_text,
            reference_datetime=datetime(2026, 7, 12, 9, 0, tzinfo=self.jst),
        )
        self.assertEqual(evaluation.status, SALE_PERIOD_OUT_OF_WINDOW)

    def test_evaluate_sale_period_returns_unknown_for_unparseable_line(self):
        important_text = "タイムセール\n販売期間 近日公開\n搭乗期間 2026/8/1-2026/8/31"
        evaluation = evaluate_sale_period(
            important_text,
            reference_datetime=datetime(2026, 7, 1, 9, 0, tzinfo=self.jst),
        )
        self.assertEqual(evaluation.status, SALE_PERIOD_UNKNOWN)

    def test_build_sale_notification_text_uses_detailed_body_in_window(self):
        important_text = "\n".join(
            [
                "タイムセール",
                "販売期間 2026/7/1-2026/7/10",
                "搭乗期間 2026/8/1-2026/8/31",
                "運賃 7,700円から",
            ]
        )
        body = build_sale_notification_text(
            self.target,
            important_text,
            "2026-07-05T09:00:00+09:00",
            sale_period_status=SALE_PERIOD_IN_WINDOW,
        )
        self.assertEqual(
            body,
            "販売期間 2026/7/1-2026/7/10\n搭乗期間 2026/8/1-2026/8/31",
        )

    def test_build_sale_notification_text_uses_simple_body_out_of_window(self):
        important_text = "タイムセール\n販売期間 2026/7/1-2026/7/10\n搭乗期間 2026/8/1-2026/8/31"
        body = build_sale_notification_text(
            self.target,
            important_text,
            "2026-07-12T09:00:00+09:00",
            sale_period_status=SALE_PERIOD_OUT_OF_WINDOW,
        )
        self.assertEqual(body, "JAL：セール期間外")


if __name__ == "__main__":
    unittest.main()
