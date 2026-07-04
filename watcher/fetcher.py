from __future__ import annotations

import requests


class FetchError(RuntimeError):
    """Raised when a monitored page cannot be fetched successfully."""


class PageFetcher:
    def __init__(self, timeout_seconds: int, user_agent: str):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch(self, url: str) -> str:
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise FetchError(f"request failed: {exc}") from exc

        if response.status_code != 200:
            raise FetchError(f"unexpected status code: {response.status_code}")

        response.encoding = response.encoding or response.apparent_encoding
        return response.text
