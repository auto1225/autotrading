from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
import json
import urllib.error
import urllib.request

from .config import TradingSettings


AI_PM_INSTRUCTIONS = """
You are a read-only PM supervisor embedded in a Korean Upbit autotrading dashboard.
Your role is to explain what the trading system should watch next, not to execute orders.
Never claim guaranteed profit. Never ask the system to enable live trading. Never output raw secrets.
Focus on realtime connection, paper/live-account separation, current holdings, top candidates,
order candidates, risk flags, stop/target context, and whether the safest next state is wait,
watch, reduce risk, or prepare a paper-only action.
Return compact JSON only with these keys:
state, headline, narrative, watch, actions, risks.
watch must be a list of up to 5 objects with market, label, reason, priority.
actions and risks must be Korean strings.
Do not spend tokens on hidden reasoning. Output the JSON object immediately.
""".strip()

AI_PM_CHAT_INSTRUCTIONS = """
You are an AI PM embedded inside a Korean Upbit autotrading dashboard.
You can discuss the provided live program snapshot and recent chat, but you cannot execute trades,
change settings, enable live trading, or reveal secrets. Answer in Korean.
Be direct and operational: explain what the system is seeing, what risk matters, which candidates
deserve attention, and what should be watched next. Do not promise or imply guaranteed profit.
When the user asks for an action, frame it as a paper-only recommendation unless the snapshot says
live trading is explicitly armed by the user.
""".strip()

MAX_CHAT_MESSAGES = 80


def ai_pm_runtime_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "ai_pm_runtime.json"


def ai_pm_chat_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "ai_pm_chat.json"


def load_ai_pm_runtime(settings: TradingSettings) -> dict[str, Any]:
    path = ai_pm_runtime_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_ai_pm_runtime(settings: TradingSettings, payload: dict[str, Any]) -> None:
    path = ai_pm_runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def load_ai_pm_chat(settings: TradingSettings) -> list[dict[str, Any]]:
    path = ai_pm_chat_path(settings)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    messages = payload.get("messages", []) if isinstance(payload, dict) else payload
    if not isinstance(messages, list):
        return []
    return [sanitize_chat_message(message) for message in messages if isinstance(message, dict)][-MAX_CHAT_MESSAGES:]


def save_ai_pm_chat(settings: TradingSettings, messages: list[dict[str, Any]]) -> None:
    path = ai_pm_chat_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "messages": [sanitize_chat_message(message) for message in messages[-MAX_CHAT_MESSAGES:]],
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def ai_pm_config_payload(settings: TradingSettings) -> dict[str, Any]:
    return {
        "enabled": settings.ai_pm_enabled,
        "configured": bool(settings.ai_pm_api_key),
        "connected": settings.ai_pm_enabled and bool(settings.ai_pm_api_key),
        "model": settings.ai_pm_model,
        "intervalSeconds": settings.ai_pm_interval_seconds,
        "maxCandidates": settings.ai_pm_max_candidates,
    }


def ai_pm_status_payload(settings: TradingSettings) -> dict[str, Any]:
    runtime = load_ai_pm_runtime(settings)
    return {
        **ai_pm_config_payload(settings),
        "last": public_ai_pm_payload(runtime) if runtime else {},
    }


def ai_pm_chat_payload(settings: TradingSettings) -> dict[str, Any]:
    return {
        **ai_pm_config_payload(settings),
        "messages": load_ai_pm_chat(settings),
    }


def public_ai_pm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    public = dict(payload)
    public.pop("request", None)
    public.pop("raw", None)
    return public


def build_ai_pm_snapshot(
    settings: TradingSettings,
    status: dict[str, Any],
    live_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    realtime_decision = status.get("realtimeDecision", {})
    last = realtime_decision.get("last", {}) if isinstance(realtime_decision, dict) else {}
    plan = last.get("plan", {}) if isinstance(last, dict) else {}
    situations = plan.get("situations", []) if isinstance(plan, dict) else []
    selected = plan.get("selected", []) if isinstance(plan, dict) else []
    orders = plan.get("orders", []) if isinstance(plan, dict) else []
    markets = status.get("markets", [])
    top_situations = situations[: settings.ai_pm_max_candidates] if isinstance(situations, list) else []
    held_markets = [
        compact_market_row(row)
        for row in markets
        if isinstance(row, dict) and _decimal(row.get("positionValueKrw")) > 0
    ][: settings.ai_pm_max_candidates]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtime": compact_keys(status.get("runtime", {}), ("modeLabel", "liveTradingEnabled", "emergencyStopped", "updatedAt", "errors")),
        "realtime": compact_keys(status.get("realtime", {}), ("connected", "lastError", "lastMessageAt", "reconnects")),
        "paperAccount": compact_keys(
            status.get("account", {}),
            (
                "cashKrw",
                "positionValueKrw",
                "equityKrw",
                "realizedPnlKrw",
                "feesPaidKrw",
                "orderCount",
                "dailyRealizedPnlKrw",
                "dailyOrderCount",
            ),
        ),
        "portfolio": compact_keys(status.get("portfolio", {}), ("openPositions", "cashKrw", "positionValueKrw", "equityKrw")),
        "goal": compact_keys(status.get("goal", {}), ("startKrw", "targetKrw", "days", "equityKrw", "remainingKrw", "progressPct")),
        "live": compact_keys(status.get("live", {}), ("keyConfigured", "armed", "webArmed", "liveTradingEnabled", "webLiveTradingEnabled")),
        "liveAccountReadOnly": compact_live_check(live_check),
        "plan": {
            "mode": plan.get("mode"),
            "message": plan.get("message"),
            "universeCount": plan.get("universeCount"),
            "evaluatedCount": plan.get("evaluatedCount"),
            "selectedCount": len(selected) if isinstance(selected, list) else 0,
            "orderCandidateCount": len(orders) if isinstance(orders, list) else 0,
            "marketRegime": plan.get("marketRegime"),
        },
        "topSituations": [compact_situation(item) for item in top_situations if isinstance(item, dict)],
        "selected": [compact_situation(item) for item in selected if isinstance(item, dict)][: settings.ai_pm_max_candidates],
        "orderCandidates": [compact_order(item) for item in orders if isinstance(item, dict)][: settings.ai_pm_max_candidates],
        "heldMarkets": held_markets,
        "rules": {
            "readOnly": True,
            "liveOrdersMustRemainLockedUnlessUserExplicitlyEnables": True,
            "minOrderKrw": str(settings.min_order_krw),
            "stopLossPct": str(settings.stop_loss_pct),
            "takeProfitPct": str(settings.take_profit_pct),
        },
    }


def request_ai_pm_report(settings: TradingSettings, snapshot: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    if not settings.ai_pm_enabled:
        return disabled_ai_pm_payload(settings, "AI_PM_ENABLED=false", snapshot, now)
    if not settings.ai_pm_api_key:
        return disabled_ai_pm_payload(settings, "OPENAI_API_KEY 또는 AI_PM_API_KEY가 설정되지 않았습니다.", snapshot, now)

    request_payload = {
        "model": settings.ai_pm_model,
        "instructions": AI_PM_INSTRUCTIONS,
        "input": json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        "max_output_tokens": 1600,
        **ai_pm_reasoning_payload(settings),
    }
    try:
        raw = post_responses_api(settings, request_payload, timeout=30)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return error_ai_pm_payload(settings, f"AI PM API 오류 {exc.code}: {error_body[:300]}", snapshot, now)
    except (OSError, json.JSONDecodeError) as exc:
        return error_ai_pm_payload(settings, f"AI PM 연결 실패: {exc}", snapshot, now)

    text = extract_response_text(raw)
    parsed = parse_ai_pm_text(text)
    payload = {
        **ai_pm_config_payload(settings),
        "ok": True,
        "state": str(parsed.get("state") or "connected"),
        "headline": str(parsed.get("headline") or "AI PM 분석 완료"),
        "narrative": str(parsed.get("narrative") or text or "AI PM 응답이 비어 있습니다."),
        "watch": parsed.get("watch") if isinstance(parsed.get("watch"), list) else [],
        "actions": parsed.get("actions") if isinstance(parsed.get("actions"), list) else [],
        "risks": parsed.get("risks") if isinstance(parsed.get("risks"), list) else [],
        "updatedAt": now,
        "request": snapshot,
        "responseId": raw.get("id"),
    }
    save_ai_pm_runtime(settings, payload)
    return public_ai_pm_payload(payload)


def request_ai_pm_chat(
    settings: TradingSettings,
    snapshot: dict[str, Any],
    messages: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    if not settings.ai_pm_enabled:
        return disabled_chat_payload(settings, "AI_PM_ENABLED=false 입니다. 프로그램 안의 AI PM 호출 스위치가 꺼져 있습니다.", now)
    if not settings.ai_pm_api_key:
        return disabled_chat_payload(settings, "AI_PM_ENABLED=true 이지만 OPENAI_API_KEY 또는 AI_PM_API_KEY가 비어 있어 실제 모델 호출을 시작할 수 없습니다.", now)

    chat_context = {
        "snapshot": snapshot,
        "recentMessages": [sanitize_chat_message(message) for message in messages[-12:]],
        "userMessage": user_message,
    }
    request_payload = {
        "model": settings.ai_pm_model,
        "instructions": AI_PM_CHAT_INSTRUCTIONS,
        "input": json.dumps(chat_context, ensure_ascii=False, separators=(",", ":")),
        "max_output_tokens": 1200,
        **ai_pm_reasoning_payload(settings),
    }
    try:
        raw = post_responses_api(settings, request_payload, timeout=45)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return error_chat_payload(settings, f"AI PM API 오류 {exc.code}: {error_body[:300]}", now)
    except (OSError, json.JSONDecodeError) as exc:
        return error_chat_payload(settings, f"AI PM 연결 실패: {exc}", now)

    text = extract_response_text(raw) or "AI PM 응답이 비어 있습니다."
    return {
        **ai_pm_config_payload(settings),
        "ok": True,
        "state": "connected",
        "message": {
            "role": "assistant",
            "content": text,
            "createdAt": now,
            "ok": True,
            "responseId": raw.get("id"),
        },
        "updatedAt": now,
        "responseId": raw.get("id"),
    }


def disabled_ai_pm_payload(settings: TradingSettings, message: str, snapshot: dict[str, Any], now: str) -> dict[str, Any]:
    payload = {
        **ai_pm_config_payload(settings),
        "ok": False,
        "state": "disabled",
        "headline": "AI PM 연결 대기",
        "narrative": message,
        "watch": [],
        "actions": ["AI PM을 프로그램 안에 상주시킬 준비는 되었지만 API 연결이 아직 비활성 상태입니다."],
        "risks": [],
        "updatedAt": now,
        "request": snapshot,
    }
    save_ai_pm_runtime(settings, payload)
    return public_ai_pm_payload(payload)


def disabled_chat_payload(settings: TradingSettings, message: str, now: str) -> dict[str, Any]:
    return {
        **ai_pm_config_payload(settings),
        "ok": False,
        "state": "disabled",
        "message": {
            "role": "assistant",
            "content": message,
            "createdAt": now,
            "ok": False,
        },
        "updatedAt": now,
    }


def error_ai_pm_payload(settings: TradingSettings, message: str, snapshot: dict[str, Any], now: str) -> dict[str, Any]:
    payload = {
        **ai_pm_config_payload(settings),
        "ok": False,
        "state": "error",
        "headline": "AI PM 연결 오류",
        "narrative": message,
        "watch": [],
        "actions": ["AI PM 연결 오류를 확인하고, 그 전까지 기존 규칙 기반 관제를 유지합니다."],
        "risks": [message],
        "updatedAt": now,
        "request": snapshot,
    }
    save_ai_pm_runtime(settings, payload)
    return public_ai_pm_payload(payload)


def error_chat_payload(settings: TradingSettings, message: str, now: str) -> dict[str, Any]:
    return {
        **ai_pm_config_payload(settings),
        "ok": False,
        "state": "error",
        "message": {
            "role": "assistant",
            "content": message,
            "createdAt": now,
            "ok": False,
        },
        "updatedAt": now,
    }


def post_responses_api(settings: TradingSettings, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{settings.ai_pm_base_url}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.ai_pm_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return raw if isinstance(raw, dict) else {}


def ai_pm_reasoning_payload(settings: TradingSettings) -> dict[str, Any]:
    model = settings.ai_pm_model.lower()
    if model.startswith("gpt-5") or model.startswith("o"):
        return {"reasoning": {"effort": "minimal"}}
    return {}


def extract_response_text(raw: dict[str, Any]) -> str:
    direct = raw.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    chunks: list[str] = []
    output = raw.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
    return "\n".join(chunks).strip()


def parse_ai_pm_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"narrative": text}
    return parsed if isinstance(parsed, dict) else {"narrative": text}


def sanitize_chat_message(message: dict[str, Any]) -> dict[str, Any]:
    role = str(message.get("role") or "assistant")
    if role not in {"user", "assistant"}:
        role = "assistant"
    content = str(message.get("content") or "")[:6000]
    created_at = str(message.get("createdAt") or datetime.now(timezone.utc).isoformat())
    sanitized: dict[str, Any] = {
        "role": role,
        "content": content,
        "createdAt": created_at,
    }
    if "ok" in message:
        sanitized["ok"] = bool(message.get("ok"))
    response_id = message.get("responseId")
    if isinstance(response_id, str):
        sanitized["responseId"] = response_id
    return sanitized


def compact_keys(payload: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {key: payload.get(key) for key in keys}


def compact_situation(item: dict[str, Any]) -> dict[str, Any]:
    return compact_keys(
        item,
        (
            "market",
            "label",
            "action",
            "score",
            "confidence",
            "urgency",
            "currentPrice",
            "currentValueKrw",
            "trend1mPct",
            "trend5mPct",
            "trend30mPct",
            "dayChangePct",
            "volumeRatio",
            "tradePressure",
            "tags",
            "reason",
            "riskReason",
            "marketRegime",
        ),
    )


def compact_order(item: dict[str, Any]) -> dict[str, Any]:
    return compact_keys(item, ("market", "side", "amountKrw", "volume", "currentPrice", "reason", "strategy"))


def compact_market_row(item: dict[str, Any]) -> dict[str, Any]:
    return compact_keys(
        item,
        (
            "market",
            "label",
            "price",
            "positionValueKrw",
            "avgEntryPrice",
            "targetSellPrice",
            "stopLossPrice",
            "unrealizedPnlKrw",
            "returnPct",
            "analysis",
        ),
    )


def compact_live_check(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    account = payload.get("account", {})
    rows = account.get("accounts", []) if isinstance(account, dict) else []
    return {
        "ok": payload.get("ok"),
        "cashKrw": account.get("cashKrw") if isinstance(account, dict) else None,
        "accountCount": account.get("accountCount") if isinstance(account, dict) else None,
        "nonZeroAccounts": [
            compact_keys(row, ("currency", "market", "balance", "locked", "avgBuyPrice", "watched"))
            for row in rows
            if isinstance(row, dict) and _decimal(row.get("balance")) > 0
        ][:8],
        "errors": payload.get("errors", []),
    }


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")
