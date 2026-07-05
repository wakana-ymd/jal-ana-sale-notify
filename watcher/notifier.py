from __future__ import annotations

import requests

from watcher.models import WatchTarget
from watcher.parser import (
    SALE_PERIOD_IN_WINDOW,
    SALE_PERIOD_OUT_OF_WINDOW,
    extract_field,
)


class LineNotifier:
    def __init__(self, channel_access_token: str, user_id: str):
        self.channel_access_token = channel_access_token
        self.user_id = user_id

    def send_sale_notification(
        self,
        target: WatchTarget,
        important_text: str,
        detected_at_iso: str,
        *,
        sale_period_status: str,
    ) -> None:
        body = build_sale_notification_text(
            target,
            important_text,
            detected_at_iso,
            sale_period_status=sale_period_status,
        )
        self._push(body)

    def send_error_notification(self, target: WatchTarget, error_message: str) -> None:
        body = "\n".join(
            [
                "【監視エラー】",
                f"{target.airline}公式ページの監視で3回連続エラーが発生しました。",
                f"URL: {target.url}",
                f"エラー: {error_message}",
            ]
        )
        self._push(body)

    def send_recovery_notification(self, target: WatchTarget) -> None:
        body = "\n".join(
            [
                "【監視復旧】",
                f"{target.airline}公式ページの監視が復旧しました。",
                f"URL: {target.url}",
            ]
        )
        self._push(body)

    def _push(self, text: str) -> None:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {self.channel_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "to": self.user_id,
                "messages": [{"type": "text", "text": text}],
            },
            timeout=10,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = _extract_error_detail(response)
            raise requests.HTTPError(
                f"{exc} response={detail}",
                response=response,
            ) from exc


def build_sale_notification_text(
    target: WatchTarget,
    important_text: str,
    detected_at_iso: str,
    *,
    sale_period_status: str,
) -> str:
    sales_period = extract_field(important_text, ("販売期間", "予約・購入期間"))
    boarding_period = extract_field(important_text, ("搭乗期間", "対象搭乗期間"))
    excerpt_lines = _build_excerpt_lines(
        important_text,
        excluded_lines=(sales_period, boarding_period),
        max_lines=4,
    )
    lines = [f"【{target.airline}】"]

    if sale_period_status == SALE_PERIOD_IN_WINDOW:
        if sales_period:
            lines.append(sales_period)
        if boarding_period:
            lines.append(boarding_period)
        lines.extend(excerpt_lines)
        lines.append(f"URL: {target.url}")
    else:
        lines.append(
            "セール期間外"
            if sale_period_status == SALE_PERIOD_OUT_OF_WINDOW
            else "販売期間判定不可"
        )
    return "\n".join(lines)


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "<empty>"
    return str(payload)


def _build_excerpt_lines(
    important_text: str,
    *,
    excluded_lines: tuple[str | None, ...],
    max_lines: int,
) -> list[str]:
    excluded = {line for line in excluded_lines if line}
    lines = [
        line
        for line in important_text.split("\n")
        if line and line not in excluded
    ]
    return lines[:max_lines]
