from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
import json
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_range_simulation import (  # noqa: E402
    KST,
    SCAN_STRIDE,
    SimPosition,
    SimulationState,
    StrategyPick,
    buy,
    equity,
    fetch_range_candles,
    krw_markets,
    pick_strategy_for_market,
    record_simulation_entry,
    record_simulation_exit,
    sell,
    simulation_risk_signal,
    to_jsonable,
    trend_hold_exit,
)
from scripts.run_day_walkforward_simulation import day_preselect_volatility  # noqa: E402
from upbit_autotrader.config import load_settings  # noqa: E402
from upbit_autotrader.learning import LEARNABLE_STRATEGY_NAMES  # noqa: E402
from upbit_autotrader.market_regime import evaluate_market_regime  # noqa: E402
from upbit_autotrader.models import Candle, decimal_to_str  # noqa: E402
from upbit_autotrader.pattern_learning import (  # noqa: E402
    build_pattern_model,
    save_pattern_model,
    score_current_pattern,
    simulate_strategy_observations,
)
from upbit_autotrader.strategy import make_strategy_by_name  # noqa: E402
from upbit_autotrader.upbit_client import UpbitClient  # noqa: E402


TRAIN_START_KST = datetime.fromisoformat(os.environ.get("SIM_TRAIN_START_KST", "2026-03-01T00:00:00+09:00"))
TEST_START_KST = datetime.fromisoformat(os.environ.get("SIM_TEST_START_KST", "2026-04-01T00:00:00+09:00"))
TEST_END_KST = datetime.fromisoformat(os.environ.get("SIM_TEST_END_KST", "2026-05-01T00:00:00+09:00"))
PRESELECT_LOOKBACK_DAYS = int(os.environ.get("SIM_PRESELECT_LOOKBACK_DAYS", "1"))
UNIT = int(os.environ.get("SIM_UNIT", "5"))
MAX_MARKETS = int(os.environ.get("SIM_MAX_MARKETS", "80"))
STARTING_CASH = Decimal(os.environ.get("SIM_STARTING_CASH", "1000000"))
MIN_TRAIN_CANDLES = int(os.environ.get("SIM_MIN_TRAIN_CANDLES", "220"))
HISTORY_LIMIT = int(os.environ.get("SIM_HISTORY_LIMIT", "240"))


def main() -> int:
    os.chdir(ROOT)
    settings = replace(
        load_settings(),
        candle_unit=UNIT,
        paper_cash_krw=STARTING_CASH,
        max_order_krw=STARTING_CASH,
        max_position_krw=STARTING_CASH,
        max_daily_orders=1_000_000,
        max_open_positions=1_000_000,
        allocation_max_deploy_pct=Decimal("1"),
        allocation_max_position_pct=Decimal("1"),
        realtime_max_order_pct=Decimal("1"),
        realtime_candidate_top_n=MAX_MARKETS,
        cooldown_seconds=0,
    )
    client = UpbitClient(settings.base_url, timeout_seconds=20)
    print(
        "april-unknown-daily "
        f"train={TRAIN_START_KST.isoformat()}..{TEST_START_KST.isoformat()} "
        f"test={TEST_START_KST.isoformat()}..{TEST_END_KST.isoformat()} "
        f"unit={UNIT} maxMarkets={MAX_MARKETS}",
        flush=True,
    )

    all_markets = krw_markets(client)
    selected = preselect_markets(client, all_markets, settings)
    candles_by_market = fetch_selected_ranges(client, selected, settings)
    train_by_market = {
        market: [candle for candle in candles if candle.timestamp < int(TEST_START_KST.timestamp() * 1000)]
        for market, candles in candles_by_market.items()
    }
    train_by_market = {
        market: candles
        for market, candles in train_by_market.items()
        if len(candles) >= max(settings.long_window + 60, MIN_TRAIN_CANDLES)
    }

    picks: dict[str, StrategyPick] = {}
    pick_details: dict[str, list[StrategyPick]] = {}
    for index, (market, candles) in enumerate(train_by_market.items(), start=1):
        pick, rows = pick_strategy_for_market(market, candles, settings, prior={})
        picks[market] = pick
        pick_details[market] = rows
        print(
            f"[learn {index}/{len(train_by_market)}] {market} {pick.strategy} "
            f"score={decimal_to_str(pick.score)} trainReturn={decimal_to_str(pick.total_return_pct)}%",
            flush=True,
        )

    pattern_model = build_pattern_model_for_picks(train_by_market, picks, settings)
    save_pattern_model(settings, pattern_model)
    print(
        "patternLearning "
        f"observations={pattern_model.get('observationCount', 0)} "
        f"profit={pattern_model.get('profitCount', 0)} loss={pattern_model.get('lossCount', 0)}",
        flush=True,
    )

    daily_results = []
    current = TEST_START_KST
    while current < TEST_END_KST:
        day_end = min(current + timedelta(days=1), TEST_END_KST)
        day_payload = build_day_payload(candles_by_market, picks, settings, current, day_end, pattern_model)
        if day_payload["portfolio"]:
            daily_results.append(day_payload)
            portfolio = day_payload["portfolio"]
            print(
                f"[day] {current.date()} return={decimal_to_str(portfolio['totalReturnPct'])}% "
                f"final={decimal_to_str(portfolio['finalEquityKrw'])} "
                f"orders={portfolio['orderCount']} mdd={decimal_to_str(portfolio['maxDrawdownPct'])}%",
                flush=True,
            )
        current = day_end

    summary = summarize_daily_results(daily_results)
    result = {
        "generatedAt": datetime.now(KST).isoformat(),
        "mode": "april_unknown_daily_walk_forward_aggressive",
        "range": {
            "trainStartKst": TRAIN_START_KST.isoformat(),
            "trainEndKst": TEST_START_KST.isoformat(),
            "testStartKst": TEST_START_KST.isoformat(),
            "testEndKst": TEST_END_KST.isoformat(),
            "candleUnitMinutes": UNIT,
        },
        "universe": {
            "requestedMaxMarkets": MAX_MARKETS,
            "marketCount": len(candles_by_market),
            "markets": list(candles_by_market.keys()),
            "selectionMethod": f"all KRW markets ranked only by {PRESELECT_LOOKBACK_DAYS} pre-April days liquidity and volatility",
        },
        "assumptions": {
            "startingCashKrw": STARTING_CASH,
            "feeRate": settings.fee_rate,
            "historicalOrderbookIncluded": False,
            "slippageIncluded": False,
            "marketRegimeIncluded": True,
            "noAprilDataInTraining": True,
            "strategyNames": list(LEARNABLE_STRATEGY_NAMES),
            "strategyScanStrideCandles": SCAN_STRIDE,
            "maxDailyOrders": settings.max_daily_orders,
            "maxOpenPositions": settings.max_open_positions,
            "maxPositionPct": settings.allocation_max_position_pct,
            "maxDeployPct": settings.allocation_max_deploy_pct,
            "maxOrderPct": settings.realtime_max_order_pct,
            "candidateTopN": settings.realtime_candidate_top_n,
        },
        "patternLearning": {
            "observationCount": pattern_model.get("observationCount", 0),
            "profitCount": pattern_model.get("profitCount", 0),
            "lossCount": pattern_model.get("lossCount", 0),
            "averageProfitPct": pattern_model.get("averageProfitPct", "0"),
            "averageLossPct": pattern_model.get("averageLossPct", "0"),
        },
        "strategyPicks": [pick.to_dict() for pick in sorted(picks.values(), key=lambda item: item.score, reverse=True)],
        "strategyScanTop3": {
            market: [pick.to_dict() for pick in rows[:3]]
            for market, rows in pick_details.items()
        },
        "dailyResults": daily_results,
        "summary": summary,
    }
    path = settings.state_file.parent / "april_unknown_daily_aggressive_202604.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={path}", flush=True)
    print(
        "summary "
        f"avg={summary['averageReturnPct']}% best={summary['best']['date']}:{summary['best']['totalReturnPct']}% "
        f"worst={summary['worst']['date']}:{summary['worst']['totalReturnPct']}%",
        flush=True,
    )
    return 0


def preselect_markets(client: UpbitClient, markets: list[str], settings: Any) -> list[str]:
    preselect_start = TEST_START_KST - timedelta(days=PRESELECT_LOOKBACK_DAYS)
    rows: list[tuple[Decimal, str]] = []
    for index, market in enumerate(markets, start=1):
        try:
            candles = fetch_range_candles(client, market, UNIT, preselect_start, TEST_START_KST - timedelta(seconds=1))
        except Exception as exc:  # noqa: BLE001
            print(f"[preselect {index}/{len(markets)}] {market} error={exc}", flush=True)
            continue
        if len(candles) < settings.long_window + 30:
            continue
        liquidity = sum((candle.candle_acc_trade_price for candle in candles), Decimal("0"))
        volatility = day_preselect_volatility(candles)
        score = liquidity * (Decimal("1") + volatility / Decimal("100"))
        rows.append((score, market))
        print(f"[preselect {index}/{len(markets)}] {market} candles={len(candles)} score={decimal_to_str(score)}", flush=True)
    rows.sort(reverse=True)
    selected = [market for _score, market in rows[:MAX_MARKETS]]
    print("selected=" + ",".join(selected), flush=True)
    return selected


def fetch_selected_ranges(client: UpbitClient, selected: list[str], settings: Any) -> dict[str, list[Candle]]:
    candles_by_market: dict[str, list[Candle]] = {}
    for index, market in enumerate(selected, start=1):
        try:
            candles = fetch_range_candles(client, market, UNIT, TRAIN_START_KST, TEST_END_KST)
        except Exception as exc:  # noqa: BLE001
            print(f"[fetch {index}/{len(selected)}] {market} error={exc}", flush=True)
            continue
        train_count = sum(1 for candle in candles if candle.timestamp < int(TEST_START_KST.timestamp() * 1000))
        test_count = len(candles) - train_count
        if train_count < max(settings.long_window + 60, MIN_TRAIN_CANDLES) or test_count < 12:
            print(f"[fetch {index}/{len(selected)}] {market} skipped train={train_count} test={test_count}", flush=True)
            continue
        candles_by_market[market] = candles
        print(f"[fetch {index}/{len(selected)}] {market} train={train_count} test={test_count}", flush=True)
    return candles_by_market


def build_day_payload(
    candles_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: Any,
    day_start: datetime,
    day_end: datetime,
    pattern_model: dict[str, Any] | None,
) -> dict[str, Any]:
    day_start_ms = int(day_start.timestamp() * 1000)
    day_end_ms = int(day_end.timestamp() * 1000)
    sim_input: dict[str, list[Candle]] = {}
    for market, candles in candles_by_market.items():
        if market not in picks:
            continue
        seed = [candle for candle in candles if candle.timestamp < day_start_ms][-settings.long_window - 5 :]
        day = [candle for candle in candles if day_start_ms <= candle.timestamp < day_end_ms]
        if len(seed) >= settings.long_window and day:
            sim_input[market] = [*seed, *day]
    portfolio = run_single_day_simulation(sim_input, picks, settings, day_start, day_end, pattern_model) if sim_input else {}
    return {
        "date": day_start.date().isoformat(),
        "marketCount": len(sim_input),
        "portfolio": portfolio,
    }


def run_single_day_simulation(
    candles_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: Any,
    day_start: datetime,
    day_end: datetime,
    pattern_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    markets = tuple(candles_by_market.keys())
    portfolio_settings = replace(settings, markets=markets)
    strategies = {
        market: make_strategy_by_name(
            replace(portfolio_settings, market=market, strategy_name=picks[market].strategy),
            picks[market].strategy,
        )
        for market in markets
    }
    candles_by_time = {
        market: {candle.timestamp: candle for candle in candles}
        for market, candles in candles_by_market.items()
    }
    all_times = sorted({timestamp for rows in candles_by_time.values() for timestamp in rows})
    day_start_ms = int(day_start.timestamp() * 1000)
    day_end_ms = int(day_end.timestamp() * 1000)
    histories: dict[str, list[Candle]] = {market: [] for market in markets}
    latest_prices: dict[str, Decimal] = {}
    state = SimulationState(cash_krw=STARTING_CASH, positions={})
    peak = STARTING_CASH
    max_drawdown = Decimal("0")
    trades: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    open_entries: dict[str, dict[str, Any]] = {}
    bar_count = 0

    for timestamp in all_times:
        updated_markets = []
        current_day = ""
        for market, rows in candles_by_time.items():
            candle = rows.get(timestamp)
            if candle is None:
                continue
            histories[market].append(candle)
            histories[market] = histories[market][-HISTORY_LIMIT:]
            latest_prices[market] = candle.trade_price
            updated_markets.append(market)
            current_day = candle.candle_date_time_kst[:10]

        if timestamp < day_start_ms or timestamp >= day_end_ms:
            continue

        bar_count += 1
        if current_day and current_day != state.current_day:
            state.current_day = current_day
            state.daily_order_count = 0

        market_regime = evaluate_market_regime(settings, histories)

        for market in list(state.positions):
            if market not in updated_markets or state.daily_order_count >= settings.max_daily_orders:
                continue
            position = state.positions[market]
            if position.volume <= 0:
                continue
            history = histories[market]
            if len(history) < settings.long_window + 1:
                continue
            signal = strategies[market].evaluate(history)
            pattern_score = score_current_pattern(pattern_model, market, picks[market].strategy, history)
            risk_signal = simulation_risk_signal(settings, pattern_model, market, position, history, picks[market].strategy)
            if (
                signal.action == "sell"
                or trend_hold_exit(history, position, settings)
                or pattern_score.exit_now
                or risk_signal.exit_now
                or market_regime.block_new_entries
            ):
                before_cash = state.cash_krw
                price = latest_prices[market]
                sell(state, market, price, settings.fee_rate)
                pattern_model = record_simulation_exit(pattern_model, open_entries, market, history, price, settings.fee_rate)
                trades.append(
                    {
                        "time": history[-1].candle_date_time_kst,
                        "market": market,
                        "side": "sell",
                        "price": price,
                        "cashAfter": state.cash_krw,
                        "cashDelta": state.cash_krw - before_cash,
                        "patternScore": pattern_score.to_dict(),
                        "risk": risk_signal.to_dict(),
                    }
                )

        current_equity = equity(state, latest_prices)
        deployed = sum(
            position.value(latest_prices.get(market, Decimal("0")))
            for market, position in state.positions.items()
            if position.volume > 0
        )
        candidates = []
        for market in updated_markets:
            if state.daily_order_count >= settings.max_daily_orders:
                break
            history = histories[market]
            if len(history) < settings.long_window + 1:
                continue
            price = latest_prices.get(market, Decimal("0"))
            position = state.positions.get(market, SimPosition(market=market))
            current_value = position.value(price)
            target_value = current_equity * settings.allocation_max_position_pct
            if current_value >= target_value:
                continue
            signal = strategies[market].evaluate(history)
            if signal.action != "buy":
                continue
            pattern_score = score_current_pattern(pattern_model, market, picks[market].strategy, history)
            risk_signal = simulation_risk_signal(settings, pattern_model, market, position, history, picks[market].strategy)
            if pattern_score.blocked or risk_signal.block_entry or market_regime.block_new_entries:
                continue
            rank = (
                picks[market].score
                + signal.strength
                + pattern_score.adjustment
                + risk_signal.score_adjustment
                + market_regime.score_adjustment
            )
            if rank < settings.realtime_min_score + settings.risk_min_entry_score_buffer + market_regime.min_score_adjustment:
                continue
            candidates.append((rank, market, pattern_score, risk_signal))

        candidates.sort(key=lambda item: item[0], reverse=True)
        for _rank, market, pattern_score, risk_signal in candidates[: settings.realtime_candidate_top_n]:
            if state.daily_order_count >= settings.max_daily_orders or state.cash_krw < settings.min_order_krw:
                break
            current_equity = equity(state, latest_prices)
            price = latest_prices[market]
            position = state.positions.get(market, SimPosition(market=market))
            current_value = position.value(price)
            target_value = current_equity * settings.allocation_max_position_pct
            deploy_limit = current_equity * settings.allocation_max_deploy_pct * market_regime.deploy_multiplier
            available_deploy = max(Decimal("0"), deploy_limit - deployed)
            budget = min(
                state.cash_krw,
                current_equity * settings.realtime_max_order_pct,
                target_value - current_value,
                available_deploy,
            )
            budget = budget.quantize(Decimal("1"))
            if budget < settings.min_order_krw:
                continue
            buy(state, market, price, budget, settings.fee_rate)
            record_simulation_entry(open_entries, market, picks[market].strategy, histories[market], price)
            deployed += budget
            trades.append(
                {
                    "time": histories[market][-1].candle_date_time_kst,
                    "market": market,
                    "side": "buy",
                    "price": price,
                    "budgetKrw": budget,
                    "cashAfter": state.cash_krw,
                    "patternScore": pattern_score.to_dict(),
                    "risk": risk_signal.to_dict(),
                }
            )

        current_equity = equity(state, latest_prices)
        peak = max(peak, current_equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (current_equity - peak) / peak * Decimal("100"))
        if len(curve) == 0 or bar_count % 12 == 0 or timestamp == all_times[-1]:
            curve.append(
                {
                    "time": datetime.fromtimestamp(timestamp / 1000, KST).isoformat(),
                    "equityKrw": current_equity,
                    "cashKrw": state.cash_krw,
                    "openPositions": sum(1 for position in state.positions.values() if position.volume > 0),
                }
            )

    final_equity = equity(state, latest_prices)
    return {
        "startEquityKrw": STARTING_CASH,
        "finalEquityKrw": final_equity,
        "totalReturnPct": (final_equity - STARTING_CASH) / STARTING_CASH * Decimal("100"),
        "realizedPnlKrw": state.realized_pnl_krw,
        "feesPaidKrw": state.fees_paid_krw,
        "orderCount": state.order_count,
        "maxDrawdownPct": max_drawdown,
        "openPositions": [
            {
                "market": market,
                "volume": position.volume,
                "avgEntryPrice": position.avg_entry_price,
                "lastPrice": latest_prices.get(market, Decimal("0")),
                "valueKrw": position.value(latest_prices.get(market, Decimal("0"))),
            }
            for market, position in state.positions.items()
            if position.volume > 0
        ],
        "equityCurve": curve[-120:],
        "trades": trades[-120:],
    }


def build_pattern_model_for_picks(
    train_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: Any,
) -> dict[str, Any]:
    observations = []
    for market, pick in picks.items():
        observations.extend(simulate_strategy_observations(market, train_by_market.get(market, []), settings, pick.strategy))
    return build_pattern_model(observations)


def summarize_daily_results(daily_results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "date": item["date"],
            "totalReturnPct": Decimal(str(item["portfolio"]["totalReturnPct"])),
            "finalEquityKrw": Decimal(str(item["portfolio"]["finalEquityKrw"])),
            "feesPaidKrw": Decimal(str(item["portfolio"]["feesPaidKrw"])),
            "orderCount": int(item["portfolio"]["orderCount"]),
            "maxDrawdownPct": Decimal(str(item["portfolio"]["maxDrawdownPct"])),
        }
        for item in daily_results
        if item.get("portfolio")
    ]
    if not rows:
        return {}
    best = max(rows, key=lambda row: row["totalReturnPct"])
    worst = min(rows, key=lambda row: row["totalReturnPct"])
    average_return = sum((row["totalReturnPct"] for row in rows), Decimal("0")) / Decimal(len(rows))
    win_days = sum(1 for row in rows if row["totalReturnPct"] > 0)
    return {
        "dayCount": len(rows),
        "winDays": win_days,
        "winRatePct": Decimal(win_days) / Decimal(len(rows)) * Decimal("100"),
        "averageReturnPct": average_return,
        "best": best,
        "worst": worst,
        "totalFeesPaidKrw": sum((row["feesPaidKrw"] for row in rows), Decimal("0")),
        "totalOrderCount": sum((row["orderCount"] for row in rows), 0),
    }


if __name__ == "__main__":
    raise SystemExit(main())
