from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_JAL_URL = "https://www.jal.co.jp/jp/ja/dom/special/timesale/"
DEFAULT_ANA_URL = "https://www.ana.co.jp/ja/jp/domestic/theme/timesale/sale/"
DEFAULT_STATE_DB_PATH = "data/watch_states.sqlite3"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class WatchTargetConfig:
    document_id: str
    airline: str
    url: str


@dataclass(frozen=True)
class Settings:
    line_channel_access_token: str
    line_user_id: str
    state_db_path: str
    request_timeout_seconds: int
    user_agent: str
    targets: tuple[WatchTargetConfig, ...]


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    jal_url = os.getenv("JAL_SALE_URL", DEFAULT_JAL_URL).strip() or DEFAULT_JAL_URL
    ana_url = os.getenv("ANA_SALE_URL", DEFAULT_ANA_URL).strip() or DEFAULT_ANA_URL
    state_db_path = os.path.expanduser(
        os.path.expandvars(
            os.getenv("STATE_DB_PATH", DEFAULT_STATE_DB_PATH).strip()
            or DEFAULT_STATE_DB_PATH
        )
    )

    return Settings(
        line_channel_access_token=_require_env("LINE_CHANNEL_ACCESS_TOKEN"),
        line_user_id=_require_env("LINE_USER_ID"),
        state_db_path=state_db_path,
        request_timeout_seconds=int(
            os.getenv("REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS)
        ),
        user_agent=os.getenv("HTTP_USER_AGENT", DEFAULT_USER_AGENT).strip()
        or DEFAULT_USER_AGENT,
        targets=(
            WatchTargetConfig(
                document_id="jal_domestic_sale", airline="JAL", url=jal_url
            ),
            WatchTargetConfig(
                document_id="ana_domestic_sale", airline="ANA", url=ana_url
            ),
        ),
    )
