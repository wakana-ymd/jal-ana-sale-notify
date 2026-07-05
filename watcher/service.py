from __future__ import annotations

import logging

from watcher.config import Settings
from watcher.fetcher import FetchError, PageFetcher
from watcher.models import CheckOutcome, WatchState, WatchTarget, now_jst_iso
from watcher.notifier import LineNotifier
from watcher.parser import (
    compute_hash,
    extract_important_lines,
    extract_text,
    is_notify_target,
    normalize_text,
)
from watcher.state_store import SQLiteStateStore


logger = logging.getLogger(__name__)


class WatchService:
    def __init__(
        self,
        targets: tuple[WatchTarget, ...],
        fetcher: PageFetcher,
        state_store: SQLiteStateStore,
        notifier: LineNotifier,
    ):
        self.targets = targets
        self.fetcher = fetcher
        self.state_store = state_store
        self.notifier = notifier

    @classmethod
    def from_settings(cls, settings: Settings) -> "WatchService":
        targets = tuple(
            WatchTarget(
                document_id=target.document_id,
                airline=target.airline,
                url=target.url,
            )
            for target in settings.targets
        )
        return cls(
            targets=targets,
            fetcher=PageFetcher(
                timeout_seconds=settings.request_timeout_seconds,
                user_agent=settings.user_agent,
            ),
            state_store=SQLiteStateStore(db_path=settings.state_db_path),
            notifier=LineNotifier(
                channel_access_token=settings.line_channel_access_token,
                user_id=settings.line_user_id,
            ),
        )

    def run(self, dry_run: bool = False) -> dict[str, object]:
        outcomes = [self._check_target(target, dry_run=dry_run) for target in self.targets]
        ok = all(outcome.error is None for outcome in outcomes)
        return {
            "ok": ok,
            "dry_run": dry_run,
            "results": [outcome.__dict__ for outcome in outcomes],
        }

    def _check_target(self, target: WatchTarget, dry_run: bool) -> CheckOutcome:
        checked_at = now_jst_iso()
        state = self.state_store.load(target.document_id, target.airline, target.url)
        previous_error_notified = state.is_error_notified
        notification_error: str | None = None

        try:
            html = self.fetcher.fetch(target.url)
            important_text, current_hash = build_important_payload(html)
        except FetchError as exc:
            logger.warning("Fetch failed for %s: %s", target.airline, exc)
            state.consecutive_error_count += 1
            state.last_checked_at = checked_at
            state.last_error = str(exc)
            error_notified = False
            if state.consecutive_error_count >= 3 and not state.is_error_notified:
                if not dry_run:
                    try:
                        self.notifier.send_error_notification(target, str(exc))
                        state.is_error_notified = True
                        error_notified = True
                    except Exception as notify_exc:
                        notification_error = str(notify_exc)
                        logger.exception(
                            "Error notification failed for %s: %s",
                            target.airline,
                            notify_exc,
                        )
                else:
                    state.is_error_notified = True
                    error_notified = True
            self.state_store.save(target.document_id, state)
            return CheckOutcome(
                airline=target.airline,
                url=target.url,
                checked_at=checked_at,
                changed=False,
                notified=False,
                error=str(exc),
                error_notified=error_notified,
                notification_error=notification_error,
            )

        changed = current_hash != state.last_hash
        notified = False
        recovered = False

        if previous_error_notified and not dry_run:
            try:
                self.notifier.send_recovery_notification(target)
                recovered = True
            except Exception as notify_exc:
                notification_error = str(notify_exc)
                logger.exception(
                    "Recovery notification failed for %s: %s",
                    target.airline,
                    notify_exc,
                )
        elif previous_error_notified:
            recovered = True

        if changed and is_notify_target(
            important_text=important_text,
            current_hash=current_hash,
            last_notified_hash=state.last_notified_hash,
        ):
            if not dry_run:
                try:
                    self.notifier.send_sale_notification(
                        target, important_text, checked_at
                    )
                    state.last_notified_hash = current_hash
                    notified = True
                except Exception as notify_exc:
                    notification_error = str(notify_exc)
                    logger.exception(
                        "Sale notification failed for %s: %s",
                        target.airline,
                        notify_exc,
                    )
            else:
                state.last_notified_hash = current_hash
                notified = True
            state.last_changed_at = checked_at
        elif changed:
            state.last_changed_at = checked_at

        state.last_hash = current_hash
        state.last_important_text = important_text
        state.last_checked_at = checked_at
        state.consecutive_error_count = 0
        state.last_error = None
        state.is_error_notified = previous_error_notified and not recovered
        self.state_store.save(target.document_id, state)

        return CheckOutcome(
            airline=target.airline,
            url=target.url,
            checked_at=checked_at,
            changed=changed,
            notified=notified,
            error=notification_error,
            recovered=recovered,
            important_text=important_text,
            notification_error=notification_error,
        )


def build_important_payload(html: str) -> tuple[str, str]:
    text = extract_text(html)
    normalized = normalize_text(text)
    important_text = extract_important_lines(normalized)
    return important_text, compute_hash(important_text)
