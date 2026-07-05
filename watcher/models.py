from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class WatchTarget:
    document_id: str
    airline: str
    url: str


@dataclass
class WatchState:
    airline: str
    url: str
    last_hash: str = ""
    last_notified_hash: str = ""
    last_important_text: str = ""
    last_checked_at: str | None = None
    last_changed_at: str | None = None
    consecutive_error_count: int = 0
    last_error: str | None = None
    is_error_notified: bool = False

    @classmethod
    def empty(cls, airline: str, url: str) -> "WatchState":
        return cls(airline=airline, url=url)

    @classmethod
    def from_dict(cls, data: dict[str, object] | None, airline: str, url: str) -> "WatchState":
        if not data:
            return cls.empty(airline=airline, url=url)

        return cls(
            airline=str(data.get("airline") or airline),
            url=str(data.get("url") or url),
            last_hash=str(data.get("last_hash") or ""),
            last_notified_hash=str(data.get("last_notified_hash") or ""),
            last_important_text=str(data.get("last_important_text") or ""),
            last_checked_at=_string_or_none(data.get("last_checked_at")),
            last_changed_at=_string_or_none(data.get("last_changed_at")),
            consecutive_error_count=int(data.get("consecutive_error_count") or 0),
            last_error=_string_or_none(data.get("last_error")),
            is_error_notified=bool(data.get("is_error_notified") or False),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class CheckOutcome:
    airline: str
    url: str
    checked_at: str
    changed: bool
    notified: bool
    error: str | None = None
    error_notified: bool = False
    recovered: bool = False
    important_text: str = ""
    notification_error: str | None = None


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _string_or_none(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
