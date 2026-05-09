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
    d,
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
from upbit_autotrader.upbit_client import UpbitClient  # noqa: E402


TRAIN_START_KST = datetime.fromisoformat(os.environ.get("SIM_TRAIN_START_KST", "2026-04-04T00:00:00+09:00"))
TEST_START_KST = datetime.fromisoformat(os.environ.get("SIM_TEST_START_KST", "2026-05-04T00:00:00+09:00"))
TEST_END_KST = datetime.fromisoformat(os.environ.get("SIM_TEST_END_KST", "2026-05-05T00:00:00+09:00"))
PRESELECT_LOOKBACK_DAYS = int(os.environ.get("SIM_PRESELECT_LOOKBACK_DAYS", "3"))
UNIT = int(os.environ.get("SIM_UNIT", "5"))
MAX_MARKETS = int(os.environ.get("SIM_MAX_MARKETS", "80"))
STARTING_CASH = Decimal(os.environ.get("SIM_STARTING_CASH", "1000000"))
MIN_TRAIN_CANDLES = int(os.environ.get("SIM_MIN_TRAIN_CANDLES", "220"))


def main() -> int:
    os.chdir(ROOT)
    settings = load_settings()
    settings = replace(
        settings,
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
        "walk-forward="
        f"train {TRAIN_START_KST.isoformat()}..{TEST_START_KST.isoformat()} "
        f"test {TEST_START_KST.isoformat()}..{TEST_END_KST.isoformat()} "
        f"unit={UNIT}m maxMarkets={MAX_MARKETS}"
    )
    markets = krw_markets(client)
    print(f"krwMarkets={len(markets)}")

    preselect_start = TEST_START_KST - timedelta(days=PRESELECT_LOOKBACK_DAYS)
    preselect_rows: list[tuple[Decimal, str, list[Candle]]] = []
    errors: list[dict[str, str]] = []
    for index, market in enumerate(markets, start=1):
        try:
            candles = fetch_range_candles(client, market, UNIT, preselect_start, TEST_START_KST - timedelta(seconds=1))
        except Exception as exc:  # noqa: BLE001
            errors.append({"market": market, "stage": "preselect", "message": str(exc)})
            print(f"[preselect {index}/{len(markets)}] {market} error={exc}")
            continue
        if len(candles) < settings.long_window + 30:
            continue
        liquidity = sum((candle.candle_acc_trade_price for candle in candles), Decimal("0"))
        volatility = day_preselect_volatility(candles)
        preselect_rows.append((liquidity * (Decimal("1") + volatility / Decimal("100")), market, candles))
        print(f"[preselect {index}/{len(markets)}] {market} candles={len(candles)} score={decimal_to_str(preselect_rows[-1][0])}")

    preselect_rows.sort(reverse=True)
    selected = [market for _score, market, _candles in preselect_rows[:MAX_MARKETS]]
    print("selected=" + ",".join(selected))

    train_by_market: dict[str, list[Candle]] = {}
    test_by_market: dict[str, list[Candle]] = {}
    for index, market in enumerate(selected, start=1):
        try:
            train = fetch_range_candles(client, market, UNIT, TRAIN_START_KST, TEST_START_KST - timedelta(seconds=1))
            test = fetch_range_candles(client, market, UNIT, TEST_START_KST, TEST_END_KST)
        except Exception as exc:  # noqa: BLE001
            errors.append({"market": market, "stage": "fetch", "message": str(exc)})
            print(f"[fetch {index}/{len(selected)}] {market} error={exc}")
            continue
        if len(train) < max(settings.long_window + 60, MIN_TRAIN_CANDLES) or len(test) < 12:
            errors.append(
                {
                    "market": market,
                    "stage": "fetch",
                    "message": f"not enough candles train={len(train)} test={len(test)}",
                }
            )
            print(f"[fetch {index}/{len(selected)}] {market} skipped train={len(train)} test={len(test)}")
            continue
        train_by_market[market] = train
        test_by_market[market] = test
        print(f"[fetch {index}/{len(selected)}] {market} train={len(train)} test={len(test)}")

    picks: dict[str, StrategyPick] = {}
    pick_details: dict[str, list[StrategyPick]] = {}
    for index, (market, candles) in enumerate(train_by_market.items(), start=1):
        pick, all_picks = pick_strategy_for_market(market, candles, settings, prior={})
        picks[market] = pick
        pick_details[market] = all_picks
        print(
            f"[learn {index}/{len(train_by_market)}] {market} {pick.strategy} "
            f"score={decimal_to_str(pick.score)} trainReturn={decimal_to_str(pick.total_return_pct)}%"
        )

    pattern_model = build_pattern_model_for_picks(train_by_market, picks, settings)
    save_pattern_model(settings, pattern_model)
    print(
        "patternLearning "
        f"observations={pattern_model.get('observationCount', 0)} "
        f"profit={pattern_model.get('profitCount', 0)} loss={pattern_model.get('lossCount', 0)}"
    )

    portfolio_input = {
        market: [*train_by_market[market][-settings.long_window - 5 :], *test_by_market[market]]
        for market in picks
        if market in test_by_market
    }
    portfolio = run_walkforward_portfolio_simulation(portfolio_input, picks, settings, pattern_model) if portfolio_input else {}

    result = {
        "generatedAt": datetime.now(KST).isoformat(),
        "mode": "walk_forward_aggressive_no_lookahead",
        "range": {
            "trainStartKst": TRAIN_START_KST.isoformat(),
            "trainEndKst": TEST_START_KST.isoformat(),
            "testStartKst": TEST_START_KST.isoformat(),
            "testEndKst": TEST_END_KST.isoformat(),
            "candleUnitMinutes": UNIT,
        },
        "universe": {
            "preselectMarketCount": len(preselect_rows),
            "requestedMaxMarkets": MAX_MARKETS,
            "marketCount": len(portfolio_input),
            "markets": list(portfolio_input.keys()),
            "selectionMethod": f"all KRW markets ranked only by {PRESELECT_LOOKBACK_DAYS} pre-test days liquidity and volatility",
        },
        "assumptions": {
            "startingCashKrw": STARTING_CASH,
            "feeRate": settings.fee_rate,
            "historicalOrderbookIncluded": False,
            "slippageIncluded": False,
            "marketRegimeIncluded": True,
            "noLookahead": True,
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
        "portfolio": portfolio,
        "errors": errors,
    }

    suffix = TEST_START_KST.strftime("%Y%m%d")
    path = settings.state_file.parent / f"day_walkforward_aggressive_{suffix}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={path}")
    if portfolio:
        print(
            "summary "
            f"final={decimal_to_str(portfolio['finalEquityKrw'])} "
            f"return={decimal_to_str(portfolio['totalReturnPct'])}% "
            f"fees={decimal_to_str(portfolio['feesPaidKrw'])} "
            f"orders={portfolio['orderCount']} "
            f"mdd={decimal_to_str(portfolio['maxDrawdownPct'])}%"
        )
    return 0


def day_preselect_volatility(candles: list[Candle]) -> Decimal:
    returns = [
        (candles[index].trade_price - candles[index - 1].trade_price)
        / candles[index - 1].trade_price
        * Decimal("100")
        for index in range(1, len(candles))
        if candles[index - 1].trade_price > 0
    ]
    if not returns:
        return Decimal("0")
    average = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum((row - average) ** 2 for row in returns) / Decimal(len(returns))
    return variance.sqrt()


def run_walkforward_portfolio_simulation(
    candles_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: Any,
    pattern_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from upbit_autotrader.strategy import make_strategy_by_name

    markets = tuple(candles_by_market.keys())
    portfolio_settings = replace(settings, markets=markets)
    strategies = {
        market: make_strategy_by_name(
            replace(portfolio_settings, market=market, strategy_name=pick.strategy),
            pick.strategy,
        )
        for market, pick in picks.items()
    }
    candles_by_time: dict[str, dict[int, Candle]] = {
        market: {candle.timestamp: candle for candle in candles}
        for market, candles in candles_by_market.items()
    }
    all_times = sorted({timestamp for rows in candles_by_time.values() for timestamp in rows})
    histories: dict[str, list[Candle]] = {market: [] for market in markets}
    latest_prices: dict[str, Decimal] = {}
    state = SimulationState(cash_krw=STARTING_CASH, positions={})
    peak = STARTING_CASH
    max_drawdown = Decimal("0")
    curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    open_entries: dict[str, dict[str, Any]] = {}
    test_start_ms = int(TEST_START_KST.timestamp() * 1000)
    bar_count = 0

    for timestamp in all_times:
        updated_markets: list[str] = []
        current_day = ""
        for market, rows in candles_by_time.items():
            candle = rows.get(timestamp)
            if candle is None:
                continue
            histories[market].append(candle)
            if len(histories[market]) > 240:
                histories[market] = histories[market][-240:]
            latest_prices[market] = candle.trade_price
            updated_markets.append(market)
            current_day = candle.candle_date_time_kst[:10]

        if timestamp < test_start_ms:
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

        deployed = sum(
            position.value(latest_prices.get(market, Decimal("0")))
            for market, position in state.positions.items()
            if position.volume > 0
        )
        current_equity = equity(state, latest_prices)
        candidates = []
        for market in updated_markets:
            if state.daily_order_count >= settings.max_daily_orders:
                break
            history = histories[market]
            if len(history) < settings.long_window + 1:
                continue
            position = state.positions.get(market, SimPosition(market=market))
            price = latest_prices.get(market, Decimal("0"))
            current_value = position.value(price)
            target_value = current_equity * settings.allocation_max_position_pct
            if current_value >= target_value:
                continue
            signal = strategies[market].evaluate(history)
            if signal.action != "buy":
                continue
            pick = picks[market]
            pattern_score = score_current_pattern(pattern_model, market, pick.strategy, history)
            risk_signal = simulation_risk_signal(settings, pattern_model, market, position, history, pick.strategy)
            if pattern_score.blocked or risk_signal.block_entry or market_regime.block_new_entries:
                continue
            rank = pick.score + signal.strength + pattern_score.adjustment + risk_signal.score_adjustment + market_regime.score_adjustment
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
    total_return_pct = (final_equity - STARTING_CASH) / STARTING_CASH * Decimal("100")
    open_positions = [
        {
            "market": market,
            "volume": position.volume,
            "avgEntryPrice": position.avg_entry_price,
            "lastPrice": latest_prices.get(market, Decimal("0")),
            "valueKrw": position.value(latest_prices.get(market, Decimal("0"))),
            "pnlPct": (
                (latest_prices.get(market, Decimal("0")) - position.avg_entry_price)
                / position.avg_entry_price
                * Decimal("100")
                if position.avg_entry_price > 0
                else Decimal("0")
            ),
        }
        for market, position in state.positions.items()
        if position.volume > 0
    ]
    open_positions.sort(key=lambda item: item["valueKrw"], reverse=True)
    return {
        "startEquityKrw": STARTING_CASH,
        "finalEquityKrw": final_equity,
        "totalReturnPct": total_return_pct,
        "realizedPnlKrw": state.realized_pnl_krw,
        "feesPaidKrw": state.fees_paid_krw,
        "orderCount": state.order_count,
        "maxDrawdownPct": max_drawdown,
        "openPositions": open_positions,
        "equityCurve": curve[-240:],
        "trades": trades[-200:],
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


if __name__ == "__main__":
    raise SystemExit(main())
