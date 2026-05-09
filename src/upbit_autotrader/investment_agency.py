from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


AGENCY_NAME = "Maeuknam Investment Agency"
REQUIRED_HTF_INTERVALS = ("1d", "1w", "1M")
MIN_INTRADAY_CANDLES = 300


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "ok"}


def _role(
    role_id: str,
    title: str,
    verdict: str,
    body: str,
    value: str = "",
    veto: bool = False,
) -> dict[str, Any]:
    verdict = verdict.upper()
    level = "ok" if verdict == "APPROVE" else "critical" if verdict == "REJECT" else "warning"
    return {
        "id": role_id,
        "title": title,
        "verdict": verdict,
        "level": level,
        "body": body,
        "value": value or verdict,
        "veto": veto,
    }


def _check(title: str, ok: bool, body: str, value: str = "") -> dict[str, str]:
    return {
        "title": title,
        "level": "ok" if ok else "critical",
        "body": body,
        "value": value or ("OK" if ok else "FAIL"),
    }


def _candidate(plan: dict[str, Any]) -> dict[str, Any]:
    situations = plan.get("situations") if isinstance(plan.get("situations"), list) else []
    return dict(situations[0]) if situations and isinstance(situations[0], dict) else {}


def _data_audit(candidate: dict[str, Any], policy: dict[str, Any]) -> tuple[list[dict[str, str]], bool]:
    closed_count = int(_decimal(candidate.get("closedCandleCount")))
    required_closed = int(_decimal(policy.get("closedCandleLimit"), "1440"))
    fetch_limit = int(_decimal(policy.get("fetchLimit"), "1500"))
    min_required = min(required_closed if required_closed > 0 else 1440, fetch_limit if fetch_limit > 0 else 1500)
    timeframe_context = candidate.get("timeframeContext") if isinstance(candidate.get("timeframeContext"), dict) else {}
    intervals = policy.get("multiTimeframeIntervals") if isinstance(policy.get("multiTimeframeIntervals"), list) else list(REQUIRED_HTF_INTERVALS)
    open_excluded = _truthy(policy.get("openCandleExcluded"))

    checks = [
        _check(
            "1m closed candle history",
            closed_count >= min_required,
            f"required {min_required}, actual {closed_count}; entry timing must not start from only fresh candles",
            f"{closed_count}/{min_required}",
        ),
        _check(
            "Open candle exclusion",
            open_excluded,
            "in-progress candles must be excluded before a card can be trusted",
            "excluded" if open_excluded else "not excluded",
        ),
    ]
    for interval in intervals:
        payload = timeframe_context.get(str(interval)) if isinstance(timeframe_context.get(str(interval)), dict) else {}
        count = int(_decimal(payload.get("count")))
        ok = count > 0 and str(payload.get("alignment") or "") != "error"
        checks.append(
            _check(
                f"{interval} higher timeframe history",
                ok,
                f"max available closed {interval} klines must be fetched for trend context",
                str(count),
            )
        )
    return checks, all(check["level"] == "ok" for check in checks)


def _htf_summary(candidate: dict[str, Any]) -> tuple[int, int, int, Decimal]:
    context = candidate.get("timeframeContext") if isinstance(candidate.get("timeframeContext"), dict) else {}
    aligned = opposed = neutral = 0
    scores: list[Decimal] = []
    for payload in context.values():
        if not isinstance(payload, dict):
            continue
        alignment = str(payload.get("alignment") or "")
        score = _decimal(payload.get("alignmentScore"))
        scores.append(score)
        if alignment == "aligned":
            aligned += 1
        elif alignment == "opposed":
            opposed += 1
        else:
            neutral += 1
    avg = sum(scores, Decimal("0")) / Decimal(len(scores)) if scores else Decimal("0")
    return aligned, opposed, neutral, avg


def build_investment_agency_report(
    plan: dict[str, Any] | None,
    status_payload: dict[str, Any] | None = None,
    cycle_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = plan if isinstance(plan, dict) else {}
    status_payload = status_payload if isinstance(status_payload, dict) else {}
    cycle_payload = cycle_payload if isinstance(cycle_payload, dict) else {}
    candidate = _candidate(plan)
    strategy_side = str(
        plan.get("strategySide") or cycle_payload.get("strategySide") or status_payload.get("strategySide") or ""
    ).upper()
    is_alex = strategy_side == "ALEX_METHOD"
    policy_key = "alexEntryPolicy" if is_alex else "maeuknamEntryPolicy"
    signal_key = "alexSignal" if is_alex else "maeuknamSignal"
    policy = plan.get(policy_key) if isinstance(plan.get(policy_key), dict) else {}
    signal = candidate.get(signal_key) if isinstance(candidate.get(signal_key), dict) else {}
    method_label = "Alex method" if is_alex else "Maeuknam card"
    strategist_id = "alex_strategist" if is_alex else "maeuknam_strategist"
    strategist_title = "Alex Strategist" if is_alex else "Maeuknam Strategist"
    intervals = policy.get("multiTimeframeIntervals") if isinstance(policy.get("multiTimeframeIntervals"), list) else list(REQUIRED_HTF_INTERVALS)
    interval_label = "/".join(str(interval) for interval in intervals)
    orders = plan.get("orders") if isinstance(plan.get("orders"), list) else []
    positions = status_payload.get("positions") if isinstance(status_payload.get("positions"), list) else []

    data_checks, data_ok = _data_audit(candidate, policy)
    htf_aligned, htf_opposed, htf_neutral, htf_score = _htf_summary(candidate)
    entry_allowed = _truthy(candidate.get("entryAllowed"))
    signal_allowed = _truthy(signal.get("entryAllowed"))
    hard_blocks = signal.get("hardBlocks") if isinstance(signal.get("hardBlocks"), list) else []
    entry_block = str(candidate.get("entryBlockReason") or plan.get("entryBlockReason") or "")
    session_block = str(plan.get("entryBlockReason") or "")
    has_candidate = bool(candidate)

    members: list[dict[str, Any]] = []
    members.append(
        _role(
            "data_custodian",
            "Data Custodian",
            "APPROVE" if data_ok else "REJECT",
            f"Audits 1m closed candles plus {interval_label} history before any thesis is trusted.",
            "complete" if data_ok else "insufficient",
            veto=True,
        )
    )
    if not has_candidate:
        members.append(
            _role(
                strategist_id,
                strategist_title,
                "REJECT",
                f"No {method_label} candidate is available, so the agency cannot form a trade thesis.",
                "no card",
                veto=True,
            )
        )
    else:
        members.append(
            _role(
                strategist_id,
                strategist_title,
                "APPROVE" if signal_allowed and not hard_blocks else "WATCH",
                f"{method_label} {signal.get('techniqueName') or signal.get('techniqueId') or 'unknown'} score {signal.get('score') or candidate.get('score') or '0'}; direction {signal.get('direction') or candidate.get('side') or 'FLAT'}.",
                str(signal.get("direction") or candidate.get("side") or "FLAT"),
            )
        )

    htf_verdict = "APPROVE" if htf_score >= Decimal("0.34") else "REJECT" if htf_score <= Decimal("-0.34") else "WATCH"
    members.append(
        _role(
            "higher_timeframe_analyst",
            "Higher Timeframe Analyst",
            htf_verdict,
            f"{interval_label} alignment: {htf_aligned} aligned, {htf_opposed} opposed, {htf_neutral} neutral; avg {htf_score}.",
            f"{htf_aligned}/{htf_aligned + htf_opposed + htf_neutral}",
        )
    )

    risk_text = f"{entry_block} {session_block}".lower()
    risk_reject = any(token in risk_text for token in ("fee drag", "fee safety", "cooldown", "session order", "emergency"))
    members.append(
        _role(
            "risk_director",
            "Risk Director",
            "REJECT" if risk_reject else "APPROVE" if entry_allowed else "WATCH",
            entry_block or "Checks fee drag, cooldown, leverage, open position count, and session order limits.",
            "blocked" if risk_reject else "clear" if entry_allowed else "watch",
            veto=risk_reject,
        )
    )

    devils_reject = htf_opposed >= 2 or bool(hard_blocks)
    devil_body = "Challenges the trade with contradiction checks: opposing HTF trend, hard blocks, stale evidence, and target/fee mismatch."
    if hard_blocks:
        devil_body = f"Hard blocks remain: {', '.join(str(item) for item in hard_blocks)}."
    elif htf_opposed >= 2:
        devil_body = f"Two or more higher timeframes oppose the card direction ({htf_opposed} opposed)."
    members.append(
        _role(
            "devils_advocate",
            "Devil's Advocate",
            "REJECT" if devils_reject else "WATCH" if htf_opposed else "APPROVE",
            devil_body,
            "objection" if devils_reject else "clear",
        )
    )

    execution_verdict = "APPROVE" if orders else "WATCH" if has_candidate or positions else "REJECT"
    members.append(
        _role(
            "execution_trader",
            "Execution Trader",
            execution_verdict,
            f"Orders {len(orders)}, positions {len(positions)}; executes only after data, card, risk, and lifecycle gates agree.",
            f"{len(orders)} orders",
        )
    )

    vetoes = [member for member in members if member["verdict"] == "REJECT" and member.get("veto")]
    rejects = [member for member in members if member["verdict"] == "REJECT"]
    approves = [member for member in members if member["verdict"] == "APPROVE"]
    if vetoes:
        verdict = "REJECT"
    elif len(approves) >= 4 and not rejects and entry_allowed:
        verdict = "APPROVE"
    elif has_candidate:
        verdict = "WATCH"
    else:
        verdict = "REJECT"

    class_name = "ok" if verdict == "APPROVE" else "critical" if verdict == "REJECT" else "warning"
    detail = (
        f"{AGENCY_NAME}: {verdict}. "
        f"Data {'OK' if data_ok else 'FAIL'}, HTF {htf_aligned} aligned/{htf_opposed} opposed, "
        f"orders {len(orders)}."
    )
    next_actions = []
    if not data_ok:
        next_actions.append("Do not explain or trade before data audit is complete.")
    if session_block:
        next_actions.append(f"Respect session gate: {session_block}.")
    if entry_block and entry_block != session_block:
        next_actions.append(f"Respect candidate gate: {entry_block}.")
    if htf_opposed >= 2:
        next_actions.append(f"Demand stronger {method_label} confirmation because higher timeframes disagree.")
    if not next_actions:
        next_actions.append("Continue card-only monitoring until a clean entry or exit event appears.")

    return {
        "name": AGENCY_NAME,
        "verdict": verdict,
        "className": class_name,
        "entryGate": verdict == "APPROVE",
        "summary": detail,
        "dataChecks": data_checks,
        "members": members,
        "nextActions": [
            {"title": f"Step {index + 1}", "body": action, "level": "waiting", "value": "next"}
            for index, action in enumerate(next_actions[:4])
        ],
        "counts": {
            "approve": len(approves),
            "reject": len(rejects),
            "veto": len(vetoes),
            "members": len(members),
        },
        "source": {
            "strategySide": plan.get("strategySide"),
            "universeSource": plan.get("universeSource"),
            "entryBlockReason": plan.get("entryBlockReason"),
            "candidateBlockReason": entry_block,
            "cycleUpdatedAt": cycle_payload.get("updatedAt") or plan.get("updatedAt"),
        },
    }
