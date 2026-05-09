from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol
import json
import time

from .backtest import BacktestReport, run_backtest
from .config import TradingSettings
from .models import Candle, decimal_to_str
from .strategy import STRATEGY_CATALOG, STRATEGY_ORDER


MODEL_VERSION = 1
LEARNABLE_STRATEGY_NAMES = tuple(name for name in STRATEGY_ORDER if name != "adaptive_learning")


class CandleClient(Protocol):
    def get_markets(self, is_details: bool = False) -> list[dict[str, Any]]:
        ...

    def get_minute_candles(
        self,
        market: str,
        unit: int = 5,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class StrategyLearningRow:
    market: str
    strategy: str
    label: str
    score: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    order_count: int
    final_equity_krw: Decimal
    regime: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "strategy": self.strategy,
            "label": self.label,
            "score": decimal_to_str(self.score),
            "totalReturnPct": decimal_to_str(self.total_return_pct),
            "maxDrawdownPct": decimal_to_str(self.max_drawdown_pct),
            "orderCount": self.order_count,
            "finalEquityKrw": decimal_to_str(self.final_equity_krw),
            "regime": self.regime,
        }


@dataclass(frozen=True)
class LearningResult:
    trained_at: str
    candle_unit: int
    candle_count: int
    scope: str
    requested_market_count: int
    rows: tuple[StrategyLearningRow, ...]
    errors: tuple[dict[str, str], ...]

    def to_model(self) -> dict[str, Any]:
        ranked = sorted(self.rows, key=lambda row: row.score, reverse=True)
        markets: dict[str, dict[str, Any]] = {}
        for row in ranked:
            if row.market not in markets:
                markets[row.market] = {
                    "market": row.market,
                    "bestStrategy": row.strategy,
                    "label": row.label,
                    "score": decimal_to_str(row.score),
                    "totalReturnPct": decimal_to_str(row.total_return_pct),
                    "maxDrawdownPct": decimal_to_str(row.max_drawdown_pct),
                    "orderCount": row.order_count,
                    "regime": row.regime,
                    "reason": f"{row.regime}에서 {row.label} 점수가 가장 높았습니다",
                }

        overall = overall_strategy_summary(ranked)
        return {
            "version": MODEL_VERSION,
            "trainedAt": self.trained_at,
            "candleUnit": self.candle_unit,
            "candleCount": self.candle_count,
            "scope": self.scope,
            "requestedMarketCount": self.requested_market_count,
            "marketCount": len(markets),
            "strategyCount": len({row.strategy for row in self.rows}),
            "overall": overall,
            "markets": markets,
            "ranking": [row.to_dict() for row in ranked[:30]],
            "errors": list(self.errors),
        }


def learning_model_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "learning_model.json"


def load_learning_model(settings: TradingSettings) -> dict[str, Any]:
    path = learning_model_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_learning_model(settings: TradingSettings, model: dict[str, Any]) -> Path:
    path = learning_model_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def fetch_historical_candles(
    client: CandleClient,
    settings: TradingSettings,
    market: str,
    target_count: int,
    pause_seconds: float = 0.08,
) -> list[Candle]:
    safe_target = max(settings.long_window + 5, target_count)
    candles_by_timestamp: dict[int, Candle] = {}
    cursor_to: str | None = None

    while len(candles_by_timestamp) < safe_target:
        page_size = min(200, safe_target - len(candles_by_timestamp))
        raw_page = client.get_minute_candles(
            market=market,
            unit=settings.candle_unit,
            count=page_size,
            to=cursor_to,
        )
        if not raw_page:
            break

        page = [Candle.from_upbit(item) for item in raw_page]
        previous_size = len(candles_by_timestamp)
        for candle in page:
            candles_by_timestamp[candle.timestamp] = candle

        oldest = min(page, key=lambda candle: candle.timestamp)
        cursor_to = oldest.candle_date_time_utc
        if len(candles_by_timestamp) == previous_size or len(raw_page) < page_size:
            break
        time.sleep(pause_seconds)

    return sorted(candles_by_timestamp.values(), key=lambda candle: candle.timestamp, reverse=True)[:safe_target]


def krw_market_codes(
    client: CandleClient,
    exclude_warnings: bool = True,
    max_markets: int = 0,
) -> tuple[str, ...]:
    raw_markets = client.get_markets(is_details=exclude_warnings)
    markets: list[str] = []
    for item in raw_markets:
        market = str(item.get("market") or "").upper()
        if not market.startswith("KRW-"):
            continue
        if exclude_warnings and is_warning_market(item):
            continue
        markets.append(market)
    unique = tuple(dict.fromkeys(markets))
    if max_markets > 0:
        return unique[:max_markets]
    return unique


def is_warning_market(item: dict[str, Any]) -> bool:
    event = item.get("market_event")
    if not isinstance(event, dict):
        return False
    if event.get("warning"):
        return True
    caution = event.get("caution")
    if isinstance(caution, dict):
        return any(bool(value) for value in caution.values())
    return bool(caution)


def run_historical_learning(
    settings: TradingSettings,
    client: CandleClient,
    count: int,
    strategy_names: Iterable[str] = LEARNABLE_STRATEGY_NAMES,
    markets: Iterable[str] | None = None,
    scope: str = "watchlist",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> LearningResult:
    from datetime import datetime, timezone

    safe_count = min(max(count, settings.long_window + 30), 1200)
    rows: list[StrategyLearningRow] = []
    errors: list[dict[str, str]] = []
    strategies = tuple(name for name in strategy_names if name in STRATEGY_CATALOG and name != "adaptive_learning")
    learning_markets = tuple(dict.fromkeys((markets or settings.markets)))
    total_markets = len(learning_markets)

    if progress_callback is not None:
        progress_callback(
            {
                "status": "running",
                "scope": scope,
                "processedMarkets": 0,
                "totalMarkets": total_markets,
                "currentMarket": None,
                "errors": 0,
            }
        )

    for market_index, market in enumerate(learning_markets):
        if progress_callback is not None:
            progress_callback(
                {
                    "status": "running",
                    "scope": scope,
                    "processedMarkets": market_index,
                    "totalMarkets": total_markets,
                    "currentMarket": market,
                    "errors": len(errors),
                }
            )
        try:
            candles = fetch_historical_candles(client, settings, market, safe_count)
        except Exception as exc:
            errors.append({"market": market, "message": f"과거 캔들 수집 실패: {exc}"})
            continue

        if len(candles) < settings.long_window + 5:
            errors.append({"market": market, "message": f"학습할 캔들이 부족합니다: {len(candles)}개"})
            continue

        regime = classify_market_regime(candles)
        for strategy in strategies:
            try:
                strategy_settings = replace(
                    settings,
                    market=market,
                    markets=(market,),
                    strategy_name=strategy,
                    candle_count=len(candles),
                )
                report = run_backtest(candles, strategy_settings)
                rows.append(score_report(report, strategy, regime))
            except Exception as exc:
                errors.append({"market": market, "strategy": strategy, "message": str(exc)})

        if progress_callback is not None:
            progress_callback(
                {
                    "status": "running",
                    "scope": scope,
                    "processedMarkets": market_index + 1,
                    "totalMarkets": total_markets,
                    "currentMarket": market,
                    "errors": len(errors),
                }
            )

        if market_index < total_markets - 1:
            time.sleep(0.12)

    return LearningResult(
        trained_at=datetime.now(timezone.utc).isoformat(),
        candle_unit=settings.candle_unit,
        candle_count=safe_count,
        scope=scope,
        requested_market_count=total_markets,
        rows=tuple(rows),
        errors=tuple(errors),
    )


def score_report(report: BacktestReport, strategy: str, regime: str) -> StrategyLearningRow:
    drawdown_penalty = abs(report.max_drawdown_pct) * Decimal("0.65")
    idle_penalty = Decimal("2.5") if report.order_count == 0 else Decimal("0")
    churn_penalty = max(0, report.order_count - 40) * Decimal("0.04")
    score = report.total_return_pct - drawdown_penalty - idle_penalty - churn_penalty
    catalog = STRATEGY_CATALOG[strategy]
    return StrategyLearningRow(
        market=report.market,
        strategy=strategy,
        label=str(catalog["label"]),
        score=score,
        total_return_pct=report.total_return_pct,
        max_drawdown_pct=report.max_drawdown_pct,
        order_count=report.order_count,
        final_equity_krw=report.final_equity_krw,
        regime=regime,
    )


def classify_market_regime(candles: list[Candle]) -> str:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if len(ordered) < 20:
        return "데이터 부족"

    first = ordered[0].trade_price
    last = ordered[-1].trade_price
    total_return = (last - first) / first * Decimal("100") if first else Decimal("0")
    recent = ordered[-20:]
    high = max(candle.high_price for candle in recent)
    low = min(candle.low_price for candle in recent)
    volatility = (high - low) / last * Decimal("100") if last else Decimal("0")

    if volatility >= Decimal("9"):
        return "변동성 확대"
    if total_return >= Decimal("5"):
        return "상승 추세"
    if total_return <= Decimal("-5"):
        return "하락 추세"
    return "횡보/평균회귀"


def overall_strategy_summary(rows: list[StrategyLearningRow]) -> dict[str, Any]:
    if not rows:
        return {}

    buckets: dict[str, list[StrategyLearningRow]] = {}
    for row in rows:
        buckets.setdefault(row.strategy, []).append(row)

    summaries: list[tuple[Decimal, str, list[StrategyLearningRow]]] = []
    for strategy, strategy_rows in buckets.items():
        average_score = sum((row.score for row in strategy_rows), Decimal("0")) / Decimal(len(strategy_rows))
        summaries.append((average_score, strategy, strategy_rows))

    average_score, strategy, strategy_rows = max(summaries, key=lambda item: item[0])
    average_return = sum((row.total_return_pct for row in strategy_rows), Decimal("0")) / Decimal(len(strategy_rows))
    average_drawdown = sum((row.max_drawdown_pct for row in strategy_rows), Decimal("0")) / Decimal(len(strategy_rows))
    return {
        "strategy": strategy,
        "label": STRATEGY_CATALOG[strategy]["label"],
        "score": decimal_to_str(average_score),
        "averageReturnPct": decimal_to_str(average_return),
        "averageDrawdownPct": decimal_to_str(average_drawdown),
        "marketCount": len(strategy_rows),
    }
