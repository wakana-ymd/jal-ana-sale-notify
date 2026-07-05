from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


IMPORTANT_KEYWORDS = (
    "タイムセール",
    "セール",
    "国内線",
    "販売期間",
    "予約・購入期間",
    "搭乗期間",
    "対象搭乗期間",
    "運賃",
    "プロモーション",
    "終了",
)

SALE_KEYWORDS = ("タイムセール", "セール")
PERIOD_KEYWORDS = ("販売期間", "予約・購入期間", "搭乗期間", "対象搭乗期間")
SALE_PERIOD_IN_WINDOW = "in_window"
SALE_PERIOD_OUT_OF_WINDOW = "out_of_window"
SALE_PERIOD_UNKNOWN = "unknown"
JST = ZoneInfo("Asia/Tokyo")
DATE_TOKEN_PATTERN = re.compile(
    r"(?:(?P<year>\d{4})\s*[./\-年]\s*)?"
    r"(?P<month>\d{1,2})\s*[./\-月]\s*"
    r"(?P<day>\d{1,2})\s*日?"
)


@dataclass(frozen=True)
class ParsedPeriod:
    start: date
    end: date
    source_line: str


@dataclass(frozen=True)
class SalePeriodEvaluation:
    status: str
    sale_period_line: str | None
    boarding_period_line: str | None
    parsed_sale_period: ParsedPeriod | None


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag_name in ("script", "style", "nav", "footer", "noscript", "svg"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    return soup.get_text(separator="\n")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.split("\n"):
        compact = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if compact:
            lines.append(compact)
    return "\n".join(lines)


def extract_important_lines(text: str) -> str:
    lines = text.split("\n")
    important = [
        line for line in lines if any(keyword in line for keyword in IMPORTANT_KEYWORDS)
    ]
    return "\n".join(important)


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_notify_target(important_text: str) -> bool:
    has_sale_keyword = any(keyword in important_text for keyword in SALE_KEYWORDS)
    has_period_keyword = any(keyword in important_text for keyword in PERIOD_KEYWORDS)
    return has_sale_keyword and has_period_keyword


def extract_field(important_text: str, field_names: tuple[str, ...]) -> str | None:
    for line in important_text.split("\n"):
        if any(field_name in line for field_name in field_names):
            return line
    return None


def evaluate_sale_period(
    important_text: str,
    *,
    reference_datetime: datetime | None = None,
    margin_days: int = 1,
) -> SalePeriodEvaluation:
    sale_period_line = extract_field(important_text, ("販売期間", "予約・購入期間"))
    boarding_period_line = extract_field(important_text, ("搭乗期間", "対象搭乗期間"))
    if not sale_period_line:
        return SalePeriodEvaluation(
            status=SALE_PERIOD_UNKNOWN,
            sale_period_line=None,
            boarding_period_line=boarding_period_line,
            parsed_sale_period=None,
        )

    current = (reference_datetime or datetime.now(JST)).astimezone(JST)
    parsed_sale_period = parse_period_line(sale_period_line, reference_date=current.date())
    if not parsed_sale_period:
        return SalePeriodEvaluation(
            status=SALE_PERIOD_UNKNOWN,
            sale_period_line=sale_period_line,
            boarding_period_line=boarding_period_line,
            parsed_sale_period=None,
        )

    window_start = parsed_sale_period.start - timedelta(days=margin_days)
    window_end = parsed_sale_period.end + timedelta(days=margin_days)
    status = (
        SALE_PERIOD_IN_WINDOW
        if window_start <= current.date() <= window_end
        else SALE_PERIOD_OUT_OF_WINDOW
    )
    return SalePeriodEvaluation(
        status=status,
        sale_period_line=sale_period_line,
        boarding_period_line=boarding_period_line,
        parsed_sale_period=parsed_sale_period,
    )


def parse_period_line(line: str, *, reference_date: date) -> ParsedPeriod | None:
    matches = list(DATE_TOKEN_PATTERN.finditer(line))
    if len(matches) < 2:
        return None

    start_parts = _token_to_parts(matches[0])
    end_parts = _token_to_parts(matches[1])
    start, end = _resolve_period_dates(start_parts, end_parts, reference_date)
    if not start or not end:
        return None
    return ParsedPeriod(start=start, end=end, source_line=line)


def _resolve_period_dates(
    start_parts: tuple[int | None, int, int],
    end_parts: tuple[int | None, int, int],
    reference_date: date,
) -> tuple[date | None, date | None]:
    start_year, start_month, start_day = start_parts
    end_year, end_month, end_day = end_parts

    inferred_start_year = start_year or end_year or reference_date.year
    inferred_end_year = end_year or inferred_start_year

    start = _safe_date(inferred_start_year, start_month, start_day)
    end = _safe_date(inferred_end_year, end_month, end_day)
    if not start or not end:
        return None, None

    if end >= start:
        return start, end

    if start_year is None and end_year is not None:
        previous_start = _safe_date(end.year - 1, start.month, start.day)
        if previous_start:
            return previous_start, end

    if end_year is None:
        next_end = _safe_date(start.year + 1, end.month, end.day)
        if next_end:
            return start, next_end

    if start_year is None and end_year is None:
        next_end = _safe_date(start.year + 1, end.month, end.day)
        if next_end:
            return start, next_end

    return None, None


def _token_to_parts(match: re.Match[str]) -> tuple[int | None, int, int]:
    year_text = match.group("year")
    return (
        int(year_text) if year_text else None,
        int(match.group("month")),
        int(match.group("day")),
    )


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
