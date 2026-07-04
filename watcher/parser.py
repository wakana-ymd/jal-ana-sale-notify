from __future__ import annotations

import hashlib
import re
import unicodedata

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


def is_notify_target(
    important_text: str, current_hash: str, last_notified_hash: str
) -> bool:
    has_sale_keyword = any(keyword in important_text for keyword in SALE_KEYWORDS)
    has_period_keyword = any(keyword in important_text for keyword in PERIOD_KEYWORDS)
    is_not_notified = current_hash != last_notified_hash
    return has_sale_keyword and has_period_keyword and is_not_notified


def extract_field(important_text: str, field_names: tuple[str, ...]) -> str | None:
    for line in important_text.split("\n"):
        if any(field_name in line for field_name in field_names):
            return line
    return None
