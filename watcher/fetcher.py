from __future__ import annotations

import requests
from bs4 import UnicodeDammit


class FetchError(RuntimeError):
    """Raised when a monitored page cannot be fetched successfully."""


class PageFetcher:
    def __init__(self, timeout_seconds: int, user_agent: str):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch(self, url: str) -> str:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise FetchError(f"request failed: {exc}") from exc

        if response.status_code != 200:
            raise FetchError(f"unexpected status code: {response.status_code}")

        return decode_html(response.content, response.apparent_encoding)


def decode_html(content: bytes, apparent_encoding: str | None) -> str:
    dammit = UnicodeDammit(content, is_html=True)
    if dammit.unicode_markup is not None:
        return dammit.unicode_markup

    fallback_encoding = apparent_encoding or "utf-8"
    return content.decode(fallback_encoding, errors="replace")
