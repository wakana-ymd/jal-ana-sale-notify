from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from watcher.models import WatchTarget
from watcher.parser import (
    SALE_PERIOD_IN_WINDOW,
    SALE_PERIOD_OUT_OF_WINDOW,
    extract_field,
)


JST = ZoneInfo("Asia/Tokyo")


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

    if sale_period_status == SALE_PERIOD_IN_WINDOW:
        lines = []
        if sales_period:
            lines.append(sales_period)
        if boarding_period:
            lines.append(boarding_period)
    else:
        return (
            f"{target.airline}：セール期間外"
            if sale_period_status == SALE_PERIOD_OUT_OF_WINDOW
            else f"{target.airline}：販売期間判定不可"
        )
    return "\n".join(lines[:2])


def format_jst(iso_timestamp: str) -> str:
    dt = datetime.fromisoformat(iso_timestamp).astimezone(JST)
    return dt.strftime("%Y-%m-%d %H:%M JST")


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "<empty>"
    return str(payload)
