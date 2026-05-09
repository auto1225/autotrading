from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RESET_BALANCE_USDT = Decimal("1000")
DEFAULT_DEPLETION_FLOOR_USDT = Decimal("10")
DEFAULT_INTERVAL_SECONDS = 30
NO_TRADE_DEADLOCK_SECONDS = 1800
DEFAULT_FEE_CAP_RESET_SECONDS = 0
REPORT_DIR = Path("reports") / "maeuknam_24h_agency"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def seconds_between(start: Any, end: datetime) -> int:
    parsed = parse_datetime(start)
    if parsed is None:
        return 0
    return max(0, int((end - parsed).total_seconds()))


def parse_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    loaded = json.loads(raw)
    return loaded if isinstance(loaded, dict) else {"data": loaded}


def first_item(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def paper_payload(status: dict[str, Any]) -> dict[str, Any]:
    payload = status.get("binanceFuturesPaper")
    return payload if isinstance(payload, dict) else {}


def realtime_plan(realtime: dict[str, Any]) -> dict[str, Any]:
    last = realtime.get("last") if isinstance(realtime.get("last"), dict) else {}
    plan = last.get("plan") if isinstance(last.get("plan"), dict) else {}
    return plan


def should_reset_paper_account(paper: dict[str, Any], depletion_floor_usdt: Decimal) -> tuple[bool, str]:
    equity = parse_decimal(paper.get("equityUsdt") or paper.get("walletBalanceUsdt"))
    wallet = parse_decimal(paper.get("walletBalanceUsdt"))
    open_positions = parse_int(paper.get("openPositions"))
    if equity <= depletion_floor_usdt:
        return True, f"equity {equity} <= depletion floor {depletion_floor_usdt}"
    if open_positions <= 0 and wallet <= depletion_floor_usdt:
        return True, f"wallet {wallet} <= depletion floor {depletion_floor_usdt} with no open positions"
    return False, "not depleted"


def should_reset_operational_halt(observation: dict[str, Any], fee_cap_reset_seconds: int) -> tuple[bool, str]:
    if fee_cap_reset_seconds <= 0:
        return False, "fee cap reset disabled"
    paper = observation.get("paper") if isinstance(observation.get("paper"), dict) else {}
    open_positions = parse_int(paper.get("openPositions"))
    if open_positions > 0:
        return False, "position is open"
    actions = observation.get("actions") if isinstance(observation.get("actions"), list) else []
    if actions:
        return False, "actions are pending"
    seconds_since_last_order = parse_int(paper.get("secondsSinceLastOrder"))
    if seconds_since_last_order < fee_cap_reset_seconds:
        return False, f"halt {seconds_since_last_order}s < reset threshold {fee_cap_reset_seconds}s"
    reason = str(observation.get("entryBlockReason") or "").lower()
    if "fee drag" in reason and "reached cap" in reason:
        return True, f"fee cap operational halt persisted {seconds_since_last_order}s"
    return False, "not a fee cap halt"


def htf_alignment_counts(candidate: dict[str, Any]) -> dict[str, int]:
    context = candidate.get("timeframeContext") if isinstance(candidate.get("timeframeContext"), dict) else {}
    counts = {"aligned": 0, "opposed": 0, "neutral": 0, "missing": 0}
    for interval in ("1d", "1w", "1M"):
        payload = context.get(interval)
        if not isinstance(payload, dict):
            counts["missing"] += 1
            continue
        alignment = str(payload.get("alignment") or "neutral")
        if alignment in counts:
            counts[alignment] += 1
        else:
            counts["neutral"] += 1
    return counts


def action_text(action: dict[str, Any]) -> str:
    parts = [
        str(action.get("type") or ""),
        str(action.get("symbol") or ""),
        str(action.get("side") or ""),
        str(action.get("reason") or ""),
    ]
    return " ".join(part for part in parts if part).strip()


def is_protective_wait_reason(reason: str) -> bool:
    text = reason.lower()
    protective_tokens = (
        "investment agency veto",
        "higher timeframes oppose",
        "fee drag throttle",
        "execution proof blocked",
        "maeuknam score",
        "변동성 부족",
        "volatility",
        "reward/risk",
        "손익비",
    )
    return any(token in text for token in protective_tokens)


def build_observation(
    status: dict[str, Any],
    realtime: dict[str, Any],
    *,
    reset_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observed_at_dt = datetime.now(timezone.utc)
    observed_at = observed_at_dt.isoformat()
    paper = paper_payload(status)
    plan = realtime_plan(realtime)
    situations = plan.get("situations") if isinstance(plan.get("situations"), list) else []
    candidate = first_item(situations)
    actions = plan.get("actions") if isinstance(plan.get("actions"), list) else []
    entry_block_reason = str(plan.get("entryBlockReason") or "")
    candidate_block_reason = str(candidate.get("entryBlockReason") or "") if candidate else ""
    open_positions = parse_int(paper.get("openPositions"))
    seconds_since_last_order = seconds_between(paper.get("lastOrderAt"), observed_at_dt)
    signal = candidate.get("maeuknamSignal") if isinstance(candidate.get("maeuknamSignal"), dict) else {}
    htf_counts = htf_alignment_counts(candidate)
    issues: list[dict[str, str]] = []

    if reset_action is not None:
        issues.append(
            {
                "code": str(reset_action.get("code") or "depleted_reset"),
                "level": "critical",
                "message": str(reset_action.get("reason") or "paper account depleted and reset"),
            }
        )
    if entry_block_reason:
        issues.append(
            {
                "code": "entry_block",
                "level": "warning",
                "message": entry_block_reason,
            }
        )
    if candidate and str(candidate.get("entryStage") or "") == "agency":
        issues.append(
            {
                "code": "agency_veto",
                "level": "warning",
                "message": str(candidate.get("entryBlockReason") or "agency veto blocked entry"),
            }
        )
    effective_block_reason = entry_block_reason or candidate_block_reason
    if open_positions <= 0 and not actions and effective_block_reason and seconds_since_last_order >= NO_TRADE_DEADLOCK_SECONDS:
        source = "global entry block" if entry_block_reason else "candidate entry block"
        protective_wait = not entry_block_reason and is_protective_wait_reason(effective_block_reason)
        issues.append(
            {
                "code": "protective_wait" if protective_wait else "no_trade_deadlock",
                "level": "warning" if protective_wait else "critical",
                "message": (
                    f"no open positions and {source} persisted "
                    f"{seconds_since_last_order}s since last order: {effective_block_reason}"
                ),
            }
        )
    if htf_counts["opposed"] >= 2:
        issues.append(
            {
                "code": "inverse_risk",
                "level": "warning",
                "message": "Two or more higher timeframes oppose the current card direction.",
            }
        )
    if candidate and str(candidate.get("entryStage") or "") == "execution_proof":
        issues.append(
            {
                "code": "execution_contradiction",
                "level": "warning",
                "message": str(candidate.get("entryBlockReason") or "live price contradicted card direction"),
            }
        )
    for action in actions:
        if not isinstance(action, dict):
            continue
        realized = parse_decimal(action.get("realizedAfterFeeUsdt"))
        if str(action.get("type") or "") == "CLOSE" and realized < 0:
            issues.append(
                {
                    "code": "losing_close",
                    "level": "critical",
                    "message": action_text(action),
                }
            )

    equity = parse_decimal(paper.get("equityUsdt") or paper.get("walletBalanceUsdt"))
    fees = parse_decimal(paper.get("feesPaidUsdt"))
    if equity > 0 and fees / equity * Decimal("100") >= Decimal("5"):
        issues.append(
            {
                "code": "fee_drag",
                "level": "warning",
                "message": f"fees {fees} USDT are >= 5% of equity {equity} USDT",
            }
        )

    fingerprint_parts = [
        str(candidate.get("symbol") or ""),
        str(candidate.get("side") or ""),
        str(candidate.get("entryStage") or ""),
        str(candidate.get("entryAllowed") or ""),
        entry_block_reason,
        str(candidate.get("entryBlockReason") or ""),
        ",".join(sorted(issue["code"] for issue in issues)),
        "|".join(action_text(action) for action in actions if isinstance(action, dict)),
    ]

    return {
        "observedAt": observed_at,
        "paper": {
            "walletBalanceUsdt": str(paper.get("walletBalanceUsdt") or "0"),
            "equityUsdt": str(paper.get("equityUsdt") or "0"),
            "realizedPnlUsdt": str(paper.get("realizedPnlUsdt") or "0"),
            "feesPaidUsdt": str(paper.get("feesPaidUsdt") or "0"),
            "orderCount": parse_int(paper.get("orderCount")),
            "openPositions": open_positions,
            "lastOrderAt": str(paper.get("lastOrderAt") or ""),
            "secondsSinceLastOrder": seconds_since_last_order,
        },
        "candidate": {
            "symbol": str(candidate.get("symbol") or ""),
            "side": str(candidate.get("side") or ""),
            "entryStage": str(candidate.get("entryStage") or ""),
            "entryAllowed": bool(candidate.get("entryAllowed") is True or str(candidate.get("entryAllowed")).lower() == "true"),
            "entryBlockReason": str(candidate.get("entryBlockReason") or ""),
            "price": str(candidate.get("currentPrice") or candidate.get("price") or ""),
            "techniqueId": str(signal.get("techniqueId") or ""),
            "score": str(signal.get("score") or candidate.get("score") or ""),
            "htf": htf_counts,
        },
        "entryBlockReason": entry_block_reason,
        "actions": [action for action in actions if isinstance(action, dict)],
        "resetAction": reset_action,
        "issues": issues,
        "fingerprint": "::".join(fingerprint_parts),
    }


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return loaded if isinstance(loaded, dict) else default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def is_new_report_run(previous: dict[str, Any], started_at: str) -> bool:
    previous_ends = parse_datetime(previous.get("endsAt"))
    previous_started = parse_datetime(previous.get("startedAt"))
    current_started = parse_datetime(started_at)
    if previous_ends is None or current_started is None:
        return False
    if previous_started is not None and current_started <= previous_started:
        return False
    return current_started >= previous_ends


def update_report(report_dir: Path, observation: dict[str, Any], *, started_at: str, ends_at: str) -> dict[str, Any]:
    status_path = report_dir / "status.json"
    events_path = report_dir / "events.jsonl"
    previous = read_json(status_path, {})
    new_run = is_new_report_run(previous, started_at)
    counters = (
        {}
        if new_run
        else previous.get("counters")
        if isinstance(previous.get("counters"), dict)
        else {}
    )
    issue_counts = counters.get("issueCounts") if isinstance(counters.get("issueCounts"), dict) else {}

    counters["cycles"] = parse_int(counters.get("cycles")) + 1
    if observation.get("resetAction"):
        counters["resets"] = parse_int(counters.get("resets")) + 1
    for issue in observation.get("issues", []):
        if isinstance(issue, dict):
            code = str(issue.get("code") or "unknown")
            issue_counts[code] = parse_int(issue_counts.get(code)) + 1
    counters["issueCounts"] = issue_counts

    should_append = (
        new_run
        or observation.get("fingerprint") != previous.get("lastFingerprint")
        or bool(observation.get("actions"))
        or bool(observation.get("resetAction"))
    )
    if should_append:
        append_jsonl(events_path, observation)

    status = {
        "name": "Maeuknam 24h Paper Agency",
        "startedAt": started_at if new_run else previous.get("startedAt") or started_at,
        "updatedAt": observation["observedAt"],
        "endsAt": ends_at if new_run else previous.get("endsAt") or ends_at,
        "lastFingerprint": observation.get("fingerprint"),
        "counters": counters,
        "latestObservation": observation,
        "paths": {
            "status": str(status_path),
            "events": str(events_path),
            "report": str(report_dir / "report.md"),
        },
    }
    write_json(status_path, status)
    write_markdown_report(report_dir / "report.md", status)
    return status


def write_markdown_report(path: Path, status: dict[str, Any]) -> None:
    observation = status.get("latestObservation") if isinstance(status.get("latestObservation"), dict) else {}
    paper = observation.get("paper") if isinstance(observation.get("paper"), dict) else {}
    candidate = observation.get("candidate") if isinstance(observation.get("candidate"), dict) else {}
    entry_block_reason = str(observation.get("entryBlockReason") or "")
    counters = status.get("counters") if isinstance(status.get("counters"), dict) else {}
    issue_counts = counters.get("issueCounts") if isinstance(counters.get("issueCounts"), dict) else {}
    issues = observation.get("issues") if isinstance(observation.get("issues"), list) else []

    lines = [
        "# Maeuknam 24h Paper Agency",
        "",
        f"- Started: {status.get('startedAt')}",
        f"- Updated: {status.get('updatedAt')}",
        f"- Planned end: {status.get('endsAt')}",
        f"- Cycles: {counters.get('cycles', 0)}",
        f"- Resets: {counters.get('resets', 0)}",
        "",
        "## Paper State",
        "",
        f"- Wallet USDT: {paper.get('walletBalanceUsdt', '0')}",
        f"- Equity USDT: {paper.get('equityUsdt', '0')}",
        f"- Realized PnL USDT: {paper.get('realizedPnlUsdt', '0')}",
        f"- Fees USDT: {paper.get('feesPaidUsdt', '0')}",
        f"- Orders: {paper.get('orderCount', 0)}",
        f"- Open positions: {paper.get('openPositions', 0)}",
        "",
        "## Current Candidate",
        "",
        f"- Symbol: {candidate.get('symbol', '')}",
        f"- Side: {candidate.get('side', '')}",
        f"- Stage: {candidate.get('entryStage', '')}",
        f"- Allowed: {candidate.get('entryAllowed', False)}",
        f"- Global Block: {entry_block_reason}",
        f"- Block: {candidate.get('entryBlockReason', '')}",
        f"- Technique: {candidate.get('techniqueId', '')}",
        f"- Price: {candidate.get('price', '')}",
        "",
        "## Issue Counts",
        "",
    ]
    if issue_counts:
        lines.extend(f"- {code}: {count}" for code, count in sorted(issue_counts.items()))
    else:
        lines.append("- none")
    lines.extend(["", "## Latest Issues", ""])
    if issues:
        lines.extend(f"- [{issue.get('level')}] {issue.get('code')}: {issue.get('message')}" for issue in issues if isinstance(issue, dict))
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_once(
    *,
    base_url: str,
    report_dir: Path,
    reset_balance_usdt: Decimal,
    depletion_floor_usdt: Decimal,
    fee_cap_reset_seconds: int,
    started_at: str,
    ends_at: str,
) -> dict[str, Any]:
    request_json(base_url, "/api/health", timeout=5)
    status = request_json(base_url, "/api/status", timeout=15)
    paper = paper_payload(status)
    reset_needed, reset_reason = should_reset_paper_account(paper, depletion_floor_usdt)
    reset_action = None
    if reset_needed:
        reset_payload = request_json(
            base_url,
            "/api/binance/futures/paper/reset",
            method="POST",
            payload={"balanceUsdt": str(reset_balance_usdt)},
            timeout=15,
        )
        reset_action = {
            "type": "RESET",
            "code": "depleted_reset",
            "reason": reset_reason,
            "balanceUsdt": str(reset_balance_usdt),
            "resultEquityUsdt": str(reset_payload.get("equityUsdt") or ""),
        }
        status = request_json(base_url, "/api/status", timeout=15)
    realtime = request_json(base_url, "/api/realtime-decision", timeout=15)
    observation = build_observation(status, realtime, reset_action=reset_action)
    operational_reset_needed, operational_reset_reason = should_reset_operational_halt(
        observation,
        fee_cap_reset_seconds,
    )
    if operational_reset_needed:
        reset_payload = request_json(
            base_url,
            "/api/binance/futures/paper/reset",
            method="POST",
            payload={"balanceUsdt": str(reset_balance_usdt)},
            timeout=15,
        )
        reset_action = {
            "type": "RESET",
            "code": "operational_reset",
            "reason": operational_reset_reason,
            "balanceUsdt": str(reset_balance_usdt),
            "resultEquityUsdt": str(reset_payload.get("equityUsdt") or ""),
        }
        status = request_json(base_url, "/api/status", timeout=15)
        realtime = request_json(base_url, "/api/realtime-decision", timeout=15)
        observation = build_observation(status, realtime, reset_action=reset_action)
    return update_report(report_dir, observation, started_at=started_at, ends_at=ends_at)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Maeuknam 24h paper-trading agency.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-hours", type=float, default=24.0)
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--reset-balance-usdt", default=str(DEFAULT_RESET_BALANCE_USDT))
    parser.add_argument("--depletion-floor-usdt", default=str(DEFAULT_DEPLETION_FLOOR_USDT))
    parser.add_argument("--fee-cap-reset-seconds", type=int, default=DEFAULT_FEE_CAP_RESET_SECONDS)
    parser.add_argument("--report-dir", default=str(REPORT_DIR))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    ends = started + timedelta(hours=max(0.01, args.duration_hours))
    started_at = started.isoformat()
    ends_at = ends.isoformat()
    report_dir = Path(args.report_dir)
    reset_balance = parse_decimal(args.reset_balance_usdt, DEFAULT_RESET_BALANCE_USDT)
    depletion_floor = parse_decimal(args.depletion_floor_usdt, DEFAULT_DEPLETION_FLOOR_USDT)
    interval = max(5, int(args.interval_seconds))

    while True:
        try:
            run_once(
                base_url=args.base_url,
                report_dir=report_dir,
                reset_balance_usdt=reset_balance,
                depletion_floor_usdt=depletion_floor,
                fee_cap_reset_seconds=max(0, int(args.fee_cap_reset_seconds)),
                started_at=started_at,
                ends_at=ends_at,
            )
        except (OSError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report_dir.mkdir(parents=True, exist_ok=True)
            append_jsonl(
                report_dir / "events.jsonl",
                {
                    "observedAt": utc_now_iso(),
                    "issues": [{"code": "agency_error", "level": "critical", "message": str(exc)}],
                    "fingerprint": f"agency_error::{exc}",
                },
            )
        if args.once or datetime.now(timezone.utc) >= ends:
            break
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
