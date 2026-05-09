from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .config import TradingSettings
from .models import decimal_to_str


SEVERITY_ORDER = {"ok": 0, "info": 1, "warning": 2, "critical": 3}


@dataclass(frozen=True)
class Alert:
    code: str
    level: str
    title: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "level": self.level,
            "title": self.title,
            "message": self.message,
        }


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def evaluate_alerts(
    settings: TradingSettings,
    runtime: dict[str, Any],
    account: dict[str, Any],
    live: dict[str, Any],
    *,
    emergency_stopped: bool,
    host: str,
) -> list[Alert]:
    if not settings.ops_alerts_enabled:
        return []

    alerts: list[Alert] = []
    realtime = runtime.get("realtime", {})
    autorun = runtime.get("autorun", {})

    if emergency_stopped:
        alerts.append(
            Alert(
                code="emergency_stopped",
                level="critical",
                title="긴급정지",
                message="대시보드 긴급정지가 걸려 있어 자동 실행이 차단됩니다.",
            )
        )

    daily_pnl = _decimal(account.get("dailyRealizedPnlKrw"))
    daily_loss = Decimal("0") - daily_pnl
    if daily_loss >= settings.daily_loss_limit_krw:
        alerts.append(
            Alert(
                code="daily_loss_limit",
                level="critical",
                title="일일 손실 한도",
                message=f"오늘 실현손실 {decimal_to_str(daily_loss)}원이 한도 {decimal_to_str(settings.daily_loss_limit_krw)}원 이상입니다.",
            )
        )

    daily_orders = int(account.get("dailyOrderCount") or 0)
    if daily_orders >= settings.max_daily_orders:
        alerts.append(
            Alert(
                code="daily_order_limit",
                level="warning",
                title="일일 주문 수 한도",
                message=f"오늘 주문 {daily_orders}회가 한도 {settings.max_daily_orders}회에 도달했습니다.",
            )
        )

    if realtime and not realtime.get("connected"):
        alerts.append(
            Alert(
                code="realtime_disconnected",
                level="warning",
                title="실시간 수신 끊김",
                message=str(realtime.get("lastError") or "Upbit WebSocket 실시간 수신이 연결되지 않았습니다."),
            )
        )

    if settings.auto_run_enabled and not autorun.get("running") and not emergency_stopped:
        alerts.append(
            Alert(
                code="autorun_stopped",
                level="warning",
                title="자동 실행 중지",
                message="AUTO_RUN_ENABLED=true이지만 페이퍼 자동 실행 루프가 돌고 있지 않습니다.",
            )
        )

    if live.get("webArmed"):
        alerts.append(
            Alert(
                code="web_live_armed",
                level="critical",
                title="웹 실거래 해제",
                message="웹 대시보드에서 실거래 주문 제출 잠금이 해제되어 있습니다.",
            )
        )
    elif live.get("armed"):
        alerts.append(
            Alert(
                code="live_armed",
                level="warning",
                title="실거래 준비됨",
                message="서버 실거래 잠금이 해제되어 있습니다. 웹 실거래는 별도 잠금 상태를 확인하세요.",
            )
        )

    if host in {"0.0.0.0", "::"} and not settings.dashboard_auth_enabled:
        alerts.append(
            Alert(
                code="lan_without_auth",
                level="warning",
                title="LAN 로그인 보호 꺼짐",
                message="모바일/LAN 접속을 열 때는 DASHBOARD_AUTH_ENABLED=true를 권장합니다.",
            )
        )

    return alerts


def alert_summary(alerts: list[Alert]) -> dict[str, Any]:
    if not alerts:
        return {
            "level": "ok",
            "label": "정상",
            "count": 0,
            "criticalCount": 0,
            "warningCount": 0,
        }

    highest = max(alerts, key=lambda alert: SEVERITY_ORDER.get(alert.level, 0)).level
    return {
        "level": highest,
        "label": "위험" if highest == "critical" else "주의",
        "count": len(alerts),
        "criticalCount": sum(1 for alert in alerts if alert.level == "critical"),
        "warningCount": sum(1 for alert in alerts if alert.level == "warning"),
    }


def alerts_payload(alerts: list[Alert]) -> dict[str, Any]:
    return {
        "summary": alert_summary(alerts),
        "items": [alert.to_dict() for alert in alerts],
    }
