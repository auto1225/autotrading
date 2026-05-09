from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping
import os


DEFAULT_MARKETS = "KRW-BTC,KRW-ETH,KRW-XRP,KRW-SOL,KRW-DOGE,KRW-ADA,KRW-AVAX,KRW-LINK,KRW-DOT,KRW-TRX"
SUPPORTED_STRATEGY_NAMES = {
    "adaptive_learning",
    "sma_cross",
    "guarded_momentum",
    "probability_edge",
    "maeuknam_cards",
    "alex_method",
    "breakout",
    "mean_reversion",
    "rsi_reversal",
    "macd_cross",
    "statistical_filter",
    "bollinger_band",
    "stochastic",
    "ichimoku_trend",
    "vwap_reversion",
    "donchian_channel",
}


def load_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Env file does not exist: {env_path}")

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _get(values: Mapping[str, str], key: str, default: str) -> str:
    value = values.get(key)
    if value is None or value == "":
        return default
    return value


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _decimal(values: Mapping[str, str], key: str, default: str) -> Decimal:
    return Decimal(_get(values, key, default))


def _int(values: Mapping[str, str], key: str, default: str) -> int:
    return int(_get(values, key, default))


def parse_markets(value: str) -> tuple[str, ...]:
    markets = tuple(dict.fromkeys(part.strip().upper() for part in value.split(",") if part.strip()))
    return markets or ("KRW-BTC",)


@dataclass(frozen=True)
class TradingSettings:
    base_url: str = "https://api.upbit.com"
    access_key: str = ""
    secret_key: str = ""
    market: str = "KRW-BTC"
    markets: tuple[str, ...] = parse_markets(DEFAULT_MARKETS)
    candle_unit: int = 5
    candle_count: int = 80
    strategy_name: str = "guarded_momentum"
    short_window: int = 5
    long_window: int = 20
    strategy_min_trend_pct: Decimal = Decimal("0.12")
    strategy_min_volume_ratio: Decimal = Decimal("1.02")
    strategy_max_volatility_pct: Decimal = Decimal("9")
    strategy_pullback_sell_pct: Decimal = Decimal("4")
    learning_candle_count: int = 400
    learning_max_markets: int = 0
    learning_exclude_market_warnings: bool = True
    realtime_decision_enabled: bool = True
    realtime_decision_interval_seconds: int = 1
    realtime_watch_top_n: int = 0
    realtime_candle_top_n: int = 60
    realtime_candle_refresh_seconds: int = 60
    realtime_candidate_top_n: int = 12
    realtime_min_score: Decimal = Decimal("0.18")
    realtime_max_order_pct: Decimal = Decimal("1")
    realtime_low_volatility_pct: Decimal = Decimal("0.30")
    realtime_stagnation_exit_seconds: int = 900
    realtime_stagnation_trend_pct: Decimal = Decimal("0.20")
    realtime_stagnation_volume_ratio: Decimal = Decimal("1.10")
    realtime_idle_exit_seconds: int = 3600
    realtime_idle_exit_return_pct: Decimal = Decimal("0.30")
    realtime_idle_exit_trend_pct: Decimal = Decimal("0.40")
    realtime_weak_breakout_enabled: bool = False
    realtime_weak_breakout_score_buffer: Decimal = Decimal("0.45")
    realtime_recovery_scout_enabled: bool = False
    realtime_recovery_scout_max_position_pct: Decimal = Decimal("0.35")
    orderbook_analysis_enabled: bool = True
    orderbook_depth_levels: int = 15
    orderbook_max_slippage_pct: Decimal = Decimal("0.50")
    orderbook_min_fill_ratio: Decimal = Decimal("0.95")
    orderbook_min_depth_ratio: Decimal = Decimal("0.35")
    orderbook_liquidity_use_pct: Decimal = Decimal("0.35")
    orderbook_reprice_spread_pct: Decimal = Decimal("0.12")
    orderbook_price_step_bps: Decimal = Decimal("5")
    orderbook_hard_max_spread_pct: Decimal = Decimal("0.80")
    orderbook_min_visible_ask_krw: Decimal = Decimal("50000")
    orderbook_min_visible_bid_krw: Decimal = Decimal("50000")
    risk_crash_guard_enabled: bool = True
    risk_crash_1m_drop_pct: Decimal = Decimal("1.0")
    risk_crash_5m_drop_pct: Decimal = Decimal("2.5")
    risk_crash_30m_drop_pct: Decimal = Decimal("6")
    risk_crash_drawdown_pct: Decimal = Decimal("8")
    risk_crash_volatility_pct: Decimal = Decimal("7")
    risk_overheat_day_change_pct: Decimal = Decimal("18")
    risk_overheat_1m_reversal_pct: Decimal = Decimal("-0.35")
    risk_overheat_range_position_pct: Decimal = Decimal("92")
    risk_overheat_volume_ratio: Decimal = Decimal("3")
    risk_max_consecutive_losses: int = 2
    risk_strategy_max_consecutive_losses: int = 1
    risk_same_pattern_max_consecutive_losses: int = 1
    risk_global_max_consecutive_losses: int = 4
    risk_loss_streak_cooldown_minutes: int = 180
    risk_market_min_trade_value_24h_krw: Decimal = Decimal("300000000")
    risk_min_candle_trade_value_krw: Decimal = Decimal("10000000")
    risk_min_entry_score_buffer: Decimal = Decimal("0.08")
    risk_chase_5m_rise_pct: Decimal = Decimal("3.5")
    risk_chase_30m_rise_pct: Decimal = Decimal("8")
    risk_chase_range_position_pct: Decimal = Decimal("88")
    risk_chase_volume_ratio: Decimal = Decimal("2.2")
    risk_min_trade_pressure: Decimal = Decimal("-1.4")
    risk_regime_guard_enabled: bool = True
    risk_regime_min_market_count: int = 3
    risk_regime_trend_window_candles: int = 12
    risk_regime_min_positive_ratio: Decimal = Decimal("0.38")
    risk_regime_soft_positive_ratio: Decimal = Decimal("0.48")
    risk_regime_risk_on_positive_ratio: Decimal = Decimal("0.62")
    risk_regime_max_crash_ratio: Decimal = Decimal("0.28")
    risk_regime_crash_trend_pct: Decimal = Decimal("2.5")
    risk_regime_min_avg_trend_pct: Decimal = Decimal("-1.0")
    dynamic_allocation_enabled: bool = True
    allocation_interval_seconds: int = 300
    allocation_top_n: int = 8
    allocation_focus_top_n: int = 3
    allocation_focus_score_gap: Decimal = Decimal("0.12")
    allocation_min_score: Decimal = Decimal("0.02")
    allocation_max_deploy_pct: Decimal = Decimal("1")
    allocation_max_position_pct: Decimal = Decimal("1")
    allocation_max_orders_per_run: int = 3
    paper_cash_krw: Decimal = Decimal("1000000")
    goal_start_krw: Decimal = Decimal("1000000")
    goal_target_krw: Decimal = Decimal("100000000")
    goal_days: int = 30
    goal_scheduler_trading_enabled: bool = True
    goal_scheduler_max_entry_relief: Decimal = Decimal("0.08")
    goal_scheduler_max_deploy_boost: Decimal = Decimal("0.40")
    goal_scheduler_max_order_boost: Decimal = Decimal("0.25")
    goal_scheduler_max_position_boost: Decimal = Decimal("0.35")
    min_order_krw: Decimal = Decimal("5000")
    max_order_krw: Decimal = Decimal("100000000")
    max_position_krw: Decimal = Decimal("100000000")
    daily_loss_limit_krw: Decimal = Decimal("50000")
    stop_loss_pct: Decimal = Decimal("3")
    take_profit_pct: Decimal = Decimal("6")
    cooldown_seconds: int = 900
    max_open_positions: int = 50
    max_daily_orders: int = 80
    paper_extreme_mode: bool = False
    auto_run_enabled: bool = False
    fee_rate: Decimal = Decimal("0.0005")
    live_trading_enabled: bool = False
    web_live_trading_enabled: bool = False
    live_order_confirmation: str = ""
    live_test_order_enabled: bool = False
    ai_pm_enabled: bool = False
    ai_pm_api_key: str = ""
    ai_pm_base_url: str = "https://api.openai.com/v1"
    ai_pm_model: str = "gpt-5"
    ai_pm_interval_seconds: int = 60
    ai_pm_max_candidates: int = 8
    ops_alerts_enabled: bool = True
    dashboard_auth_enabled: bool = False
    dashboard_username: str = "admin"
    dashboard_password: str = ""
    event_log_file: Path = Path("state/events.jsonl")
    database_file: Path = Path("state/autotrading.sqlite3")
    binance_base_url: str = "https://api.binance.com"
    binance_symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    binance_api_key: str = ""
    binance_secret_key: str = ""
    binance_futures_base_url: str = "https://fapi.binance.com"
    binance_futures_testnet_enabled: bool = False
    binance_futures_symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    binance_futures_api_key: str = ""
    binance_futures_secret_key: str = ""
    state_file: Path = Path("state/paper_state.json")
    loop_sleep_seconds: int = 60

    def validate(self) -> None:
        if not self.markets:
            raise ValueError("감시 마켓은 최소 1개 이상이어야 합니다")
        if self.market not in self.markets:
            raise ValueError("기본 마켓은 감시 마켓 목록에 포함되어야 합니다")
        for market in self.markets:
            if "-" not in market:
                raise ValueError(f"마켓 형식이 올바르지 않습니다: {market}")
        if self.short_window <= 0:
            raise ValueError("단기 이동평균 기간은 1 이상이어야 합니다")
        if self.long_window <= self.short_window:
            raise ValueError("장기 이동평균 기간은 단기 이동평균 기간보다 커야 합니다")
        if self.strategy_name not in SUPPORTED_STRATEGY_NAMES:
            raise ValueError(f"지원하지 않는 전략입니다: {self.strategy_name}")
        if self.strategy_min_trend_pct < 0:
            raise ValueError("전략 추세 강도 기준은 0 이상이어야 합니다")
        if self.strategy_min_volume_ratio <= 0:
            raise ValueError("전략 거래대금 비율 기준은 0보다 커야 합니다")
        if self.strategy_max_volatility_pct <= 0:
            raise ValueError("전략 변동성 상한은 0보다 커야 합니다")
        if self.strategy_pullback_sell_pct <= 0:
            raise ValueError("전략 되돌림 매도 기준은 0보다 커야 합니다")
        if self.learning_candle_count < self.long_window + 30:
            raise ValueError("학습 캔들 수는 장기 이동평균 기간보다 충분히 커야 합니다")
        if self.learning_max_markets < 0:
            raise ValueError("학습 최대 마켓 수는 0 이상이어야 합니다")
        if self.realtime_decision_interval_seconds <= 0:
            raise ValueError("실시간 판단 주기는 1초 이상이어야 합니다")
        if self.realtime_watch_top_n < 0:
            raise ValueError("실시간 감시 후보 수는 0 이상이어야 합니다")
        if self.realtime_candle_top_n <= 0:
            raise ValueError("실시간 캔들 분석 후보 수는 1개 이상이어야 합니다")
        if self.realtime_candle_refresh_seconds <= 0:
            raise ValueError("실시간 캔들 갱신 주기는 1초 이상이어야 합니다")
        if self.realtime_candidate_top_n <= 0:
            raise ValueError("실시간 매수 후보 수는 1개 이상이어야 합니다")
        if self.realtime_min_score < 0:
            raise ValueError("실시간 판단 최소 점수는 0 이상이어야 합니다")
        if not Decimal("0") < self.realtime_max_order_pct <= Decimal("1"):
            raise ValueError("실시간 주문 비율은 0보다 크고 1 이하여야 합니다")
        if self.realtime_low_volatility_pct < 0:
            raise ValueError("실시간 저변동 기준은 0 이상이어야 합니다")
        if self.realtime_stagnation_exit_seconds < 0:
            raise ValueError("실시간 정체 보유 정리 시간은 0 이상이어야 합니다")
        if self.realtime_stagnation_trend_pct < 0:
            raise ValueError("실시간 정체 추세 기준은 0 이상이어야 합니다")
        if self.realtime_stagnation_volume_ratio <= 0:
            raise ValueError("실시간 정체 거래대금 기준은 0보다 커야 합니다")
        if self.realtime_idle_exit_seconds < 0:
            raise ValueError("실시간 시간정리 기준은 0 이상이어야 합니다")
        if self.realtime_idle_exit_return_pct < 0:
            raise ValueError("실시간 시간정리 수익률 기준은 0 이상이어야 합니다")
        if self.realtime_idle_exit_trend_pct < 0:
            raise ValueError("실시간 시간정리 추세 기준은 0 이상이어야 합니다")
        if self.realtime_weak_breakout_score_buffer < 0:
            raise ValueError("실시간 약세장 예외 진입 점수 여유는 0 이상이어야 합니다")
        if not Decimal("0") < self.realtime_recovery_scout_max_position_pct <= Decimal("1"):
            raise ValueError("실시간 회복 스카우트 최대 포지션 비율은 0보다 크고 1 이하여야 합니다")
        if self.orderbook_depth_levels not in {1, 5, 15, 30}:
            raise ValueError("호가 분석 단계는 1, 5, 15, 30 중 하나여야 합니다")
        if self.orderbook_max_slippage_pct < 0:
            raise ValueError("호가 허용 슬리피지는 0 이상이어야 합니다")
        if not Decimal("0") < self.orderbook_min_fill_ratio <= Decimal("1"):
            raise ValueError("호가 최소 체결비율은 0보다 크고 1 이하여야 합니다")
        if self.orderbook_min_depth_ratio < 0:
            raise ValueError("호가 매수/매도 잔량비 기준은 0 이상이어야 합니다")
        if not Decimal("0") < self.orderbook_liquidity_use_pct <= Decimal("1"):
            raise ValueError("호가 잔량 사용 비율은 0보다 크고 1 이하여야 합니다")
        if self.orderbook_reprice_spread_pct < 0:
            raise ValueError("호가 재지정 스프레드 기준은 0 이상이어야 합니다")
        if self.orderbook_price_step_bps < 0:
            raise ValueError("호가 지정가 보정 bps는 0 이상이어야 합니다")
        if self.orderbook_hard_max_spread_pct < 0:
            raise ValueError("ORDERBOOK_HARD_MAX_SPREAD_PCT must be 0 or greater")
        if self.orderbook_min_visible_ask_krw < 0:
            raise ValueError("ORDERBOOK_MIN_VISIBLE_ASK_KRW must be 0 or greater")
        if self.orderbook_min_visible_bid_krw < 0:
            raise ValueError("ORDERBOOK_MIN_VISIBLE_BID_KRW must be 0 or greater")
        for key, value in {
            "RISK_CRASH_1M_DROP_PCT": self.risk_crash_1m_drop_pct,
            "RISK_CRASH_5M_DROP_PCT": self.risk_crash_5m_drop_pct,
            "RISK_CRASH_30M_DROP_PCT": self.risk_crash_30m_drop_pct,
            "RISK_CRASH_DRAWDOWN_PCT": self.risk_crash_drawdown_pct,
            "RISK_CRASH_VOLATILITY_PCT": self.risk_crash_volatility_pct,
            "RISK_OVERHEAT_DAY_CHANGE_PCT": self.risk_overheat_day_change_pct,
            "RISK_OVERHEAT_RANGE_POSITION_PCT": self.risk_overheat_range_position_pct,
            "RISK_OVERHEAT_VOLUME_RATIO": self.risk_overheat_volume_ratio,
        }.items():
            if value < 0:
                raise ValueError(f"{key} must be 0 or greater")
        if self.risk_max_consecutive_losses <= 0:
            raise ValueError("RISK_MAX_CONSECUTIVE_LOSSES must be 1 or greater")
        if self.risk_strategy_max_consecutive_losses <= 0:
            raise ValueError("RISK_STRATEGY_MAX_CONSECUTIVE_LOSSES must be 1 or greater")
        if self.risk_same_pattern_max_consecutive_losses <= 0:
            raise ValueError("RISK_SAME_PATTERN_MAX_CONSECUTIVE_LOSSES must be 1 or greater")
        if self.risk_global_max_consecutive_losses <= 0:
            raise ValueError("RISK_GLOBAL_MAX_CONSECUTIVE_LOSSES must be 1 or greater")
        if self.risk_loss_streak_cooldown_minutes < 0:
            raise ValueError("RISK_LOSS_STREAK_COOLDOWN_MINUTES must be 0 or greater")
        if self.risk_market_min_trade_value_24h_krw < 0:
            raise ValueError("RISK_MARKET_MIN_TRADE_VALUE_24H_KRW must be 0 or greater")
        if self.risk_min_candle_trade_value_krw < 0:
            raise ValueError("RISK_MIN_CANDLE_TRADE_VALUE_KRW must be 0 or greater")
        if self.risk_min_entry_score_buffer < 0:
            raise ValueError("RISK_MIN_ENTRY_SCORE_BUFFER must be 0 or greater")
        for key, value in {
            "RISK_CHASE_5M_RISE_PCT": self.risk_chase_5m_rise_pct,
            "RISK_CHASE_30M_RISE_PCT": self.risk_chase_30m_rise_pct,
            "RISK_CHASE_RANGE_POSITION_PCT": self.risk_chase_range_position_pct,
            "RISK_CHASE_VOLUME_RATIO": self.risk_chase_volume_ratio,
            "RISK_REGIME_MIN_POSITIVE_RATIO": self.risk_regime_min_positive_ratio,
            "RISK_REGIME_SOFT_POSITIVE_RATIO": self.risk_regime_soft_positive_ratio,
            "RISK_REGIME_RISK_ON_POSITIVE_RATIO": self.risk_regime_risk_on_positive_ratio,
            "RISK_REGIME_MAX_CRASH_RATIO": self.risk_regime_max_crash_ratio,
            "RISK_REGIME_CRASH_TREND_PCT": self.risk_regime_crash_trend_pct,
        }.items():
            if value < 0:
                raise ValueError(f"{key} must be 0 or greater")
        if self.risk_regime_min_market_count <= 0:
            raise ValueError("RISK_REGIME_MIN_MARKET_COUNT must be 1 or greater")
        if self.risk_regime_trend_window_candles <= 0:
            raise ValueError("RISK_REGIME_TREND_WINDOW_CANDLES must be 1 or greater")
        if self.risk_regime_min_positive_ratio > Decimal("1"):
            raise ValueError("RISK_REGIME_MIN_POSITIVE_RATIO must be 1 or lower")
        if self.risk_regime_soft_positive_ratio > Decimal("1"):
            raise ValueError("RISK_REGIME_SOFT_POSITIVE_RATIO must be 1 or lower")
        if self.risk_regime_risk_on_positive_ratio > Decimal("1"):
            raise ValueError("RISK_REGIME_RISK_ON_POSITIVE_RATIO must be 1 or lower")
        if self.risk_regime_max_crash_ratio > Decimal("1"):
            raise ValueError("RISK_REGIME_MAX_CRASH_RATIO must be 1 or lower")
        if self.allocation_interval_seconds <= 0:
            raise ValueError("동적 배분 주기는 1초 이상이어야 합니다")
        if self.allocation_top_n <= 0:
            raise ValueError("동적 배분 코인 수는 1개 이상이어야 합니다")
        if self.allocation_focus_top_n <= 0:
            raise ValueError("집중 배분 코인 수는 1개 이상이어야 합니다")
        if self.allocation_focus_top_n > self.allocation_top_n:
            raise ValueError("집중 배분 코인 수는 전체 배분 코인 수보다 클 수 없습니다")
        if self.allocation_focus_score_gap < 0:
            raise ValueError("집중 배분 점수 차이는 0 이상이어야 합니다")
        if self.allocation_min_score < 0:
            raise ValueError("동적 배분 최소 점수는 0 이상이어야 합니다")
        if not Decimal("0") < self.allocation_max_deploy_pct <= Decimal("1"):
            raise ValueError("동적 배분 투입 비율은 0보다 크고 1 이하여야 합니다")
        if not Decimal("0") < self.allocation_max_position_pct <= Decimal("1"):
            raise ValueError("동적 배분 코인별 최대 비율은 0보다 크고 1 이하여야 합니다")
        if self.allocation_max_orders_per_run <= 0:
            raise ValueError("동적 배분 1회 최대 주문 수는 1 이상이어야 합니다")
        if self.candle_unit not in {1, 3, 5, 10, 15, 30, 60, 240}:
            raise ValueError("캔들 단위는 1, 3, 5, 10, 15, 30, 60, 240 중 하나여야 합니다")
        if self.min_order_krw <= 0:
            raise ValueError("최소 주문 금액은 0보다 커야 합니다")
        if self.max_order_krw < self.min_order_krw:
            raise ValueError("주문당 최대 금액은 최소 주문 금액 이상이어야 합니다")
        if self.max_position_krw < self.min_order_krw:
            raise ValueError("최대 포지션 금액은 최소 주문 금액 이상이어야 합니다")
        if not Decimal("0") <= self.fee_rate < Decimal("0.01"):
            raise ValueError("수수료율은 0 이상 0.01 미만이어야 합니다")
        if self.daily_loss_limit_krw <= 0:
            raise ValueError("일일 손실 한도는 0보다 커야 합니다")
        if self.stop_loss_pct <= 0:
            raise ValueError("손절 기준은 0보다 커야 합니다")
        if self.take_profit_pct <= 0:
            raise ValueError("익절 기준은 0보다 커야 합니다")
        if self.cooldown_seconds < 0:
            raise ValueError("재진입 대기시간은 0 이상이어야 합니다")
        if self.max_open_positions <= 0:
            raise ValueError("최대 보유 코인 수는 1 이상이어야 합니다")
        if self.max_daily_orders <= 0:
            raise ValueError("일일 최대 주문 수는 1 이상이어야 합니다")
        if self.goal_start_krw <= 0:
            raise ValueError("목표 시작 금액은 0보다 커야 합니다")
        if self.goal_target_krw <= self.goal_start_krw:
            raise ValueError("목표 금액은 시작 금액보다 커야 합니다")
        if self.goal_days <= 0:
            raise ValueError("목표 기간은 1일 이상이어야 합니다")
        if self.goal_scheduler_max_entry_relief < 0:
            raise ValueError("GOAL_SCHEDULER_MAX_ENTRY_RELIEF는 0 이상이어야 합니다")
        for key, value in {
            "GOAL_SCHEDULER_MAX_DEPLOY_BOOST": self.goal_scheduler_max_deploy_boost,
            "GOAL_SCHEDULER_MAX_ORDER_BOOST": self.goal_scheduler_max_order_boost,
            "GOAL_SCHEDULER_MAX_POSITION_BOOST": self.goal_scheduler_max_position_boost,
        }.items():
            if value < 0:
                raise ValueError(f"{key} must be 0 or greater")


        if self.dashboard_auth_enabled and not self.dashboard_username:
            raise ValueError("DASHBOARD_AUTH_ENABLED=true이면 DASHBOARD_USERNAME을 설정해야 합니다.")
        if self.dashboard_auth_enabled and not self.dashboard_password:
            raise ValueError("DASHBOARD_AUTH_ENABLED=true이면 DASHBOARD_PASSWORD를 설정해야 합니다.")
        if self.ai_pm_interval_seconds <= 0:
            raise ValueError("AI_PM_INTERVAL_SECONDS는 1초 이상이어야 합니다.")
        if self.ai_pm_max_candidates <= 0:
            raise ValueError("AI_PM_MAX_CANDIDATES는 1 이상이어야 합니다.")


def load_settings(env_file: str | Path | None = None) -> TradingSettings:
    file_values: dict[str, str] = {}
    if env_file is not None:
        file_values = load_env_file(env_file)
    else:
        default_env = Path(".env")
        if default_env.exists():
            file_values = load_env_file(default_env)

    values = {**file_values, **os.environ}
    markets = parse_markets(_get(values, "UPBIT_MARKETS", _get(values, "UPBIT_MARKET", DEFAULT_MARKETS)))
    binance_symbols = tuple(
        dict.fromkeys(part.strip().upper() for part in _get(values, "BINANCE_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if part.strip())
    ) or ("BTCUSDT",)
    binance_futures_symbols = tuple(
        dict.fromkeys(
            part.strip().upper()
            for part in _get(values, "BINANCE_FUTURES_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
            if part.strip()
        )
    ) or ("BTCUSDT",)
    settings = TradingSettings(
        base_url=_get(values, "UPBIT_BASE_URL", "https://api.upbit.com").rstrip("/"),
        access_key=_get(values, "UPBIT_ACCESS_KEY", ""),
        secret_key=_get(values, "UPBIT_SECRET_KEY", ""),
        market=markets[0],
        markets=markets,
        candle_unit=_int(values, "UPBIT_CANDLE_UNIT", "5"),
        candle_count=_int(values, "UPBIT_CANDLE_COUNT", "80"),
        strategy_name=_get(values, "STRATEGY_NAME", "guarded_momentum"),
        short_window=_int(values, "STRATEGY_SHORT_WINDOW", "5"),
        long_window=_int(values, "STRATEGY_LONG_WINDOW", "20"),
        strategy_min_trend_pct=_decimal(values, "STRATEGY_MIN_TREND_PCT", "0.12"),
        strategy_min_volume_ratio=_decimal(values, "STRATEGY_MIN_VOLUME_RATIO", "1.02"),
        strategy_max_volatility_pct=_decimal(values, "STRATEGY_MAX_VOLATILITY_PCT", "9"),
        strategy_pullback_sell_pct=_decimal(values, "STRATEGY_PULLBACK_SELL_PCT", "4"),
        learning_candle_count=_int(values, "LEARNING_CANDLE_COUNT", "400"),
        learning_max_markets=_int(values, "LEARNING_MAX_MARKETS", "0"),
        learning_exclude_market_warnings=_bool(_get(values, "LEARNING_EXCLUDE_MARKET_WARNINGS", "true")),
        realtime_decision_enabled=_bool(_get(values, "REALTIME_DECISION_ENABLED", "true")),
        realtime_decision_interval_seconds=_int(values, "REALTIME_DECISION_INTERVAL_SECONDS", "1"),
        realtime_watch_top_n=_int(values, "REALTIME_WATCH_TOP_N", "0"),
        realtime_candle_top_n=_int(values, "REALTIME_CANDLE_TOP_N", "60"),
        realtime_candle_refresh_seconds=_int(values, "REALTIME_CANDLE_REFRESH_SECONDS", "60"),
        realtime_candidate_top_n=_int(values, "REALTIME_CANDIDATE_TOP_N", "12"),
        realtime_min_score=_decimal(values, "REALTIME_MIN_SCORE", "0.18"),
        realtime_max_order_pct=_decimal(values, "REALTIME_MAX_ORDER_PCT", "1"),
        realtime_low_volatility_pct=_decimal(values, "REALTIME_LOW_VOLATILITY_PCT", "0.30"),
        realtime_stagnation_exit_seconds=_int(values, "REALTIME_STAGNATION_EXIT_SECONDS", "900"),
        realtime_stagnation_trend_pct=_decimal(values, "REALTIME_STAGNATION_TREND_PCT", "0.20"),
        realtime_stagnation_volume_ratio=_decimal(values, "REALTIME_STAGNATION_VOLUME_RATIO", "1.10"),
        realtime_idle_exit_seconds=_int(values, "REALTIME_IDLE_EXIT_SECONDS", "3600"),
        realtime_idle_exit_return_pct=_decimal(values, "REALTIME_IDLE_EXIT_RETURN_PCT", "0.30"),
        realtime_idle_exit_trend_pct=_decimal(values, "REALTIME_IDLE_EXIT_TREND_PCT", "0.40"),
        realtime_weak_breakout_enabled=_bool(_get(values, "REALTIME_WEAK_BREAKOUT_ENABLED", "false")),
        realtime_weak_breakout_score_buffer=_decimal(values, "REALTIME_WEAK_BREAKOUT_SCORE_BUFFER", "0.45"),
        realtime_recovery_scout_enabled=_bool(_get(values, "REALTIME_RECOVERY_SCOUT_ENABLED", "false")),
        realtime_recovery_scout_max_position_pct=_decimal(values, "REALTIME_RECOVERY_SCOUT_MAX_POSITION_PCT", "0.35"),
        orderbook_analysis_enabled=_bool(_get(values, "ORDERBOOK_ANALYSIS_ENABLED", "true")),
        orderbook_depth_levels=_int(values, "ORDERBOOK_DEPTH_LEVELS", "15"),
        orderbook_max_slippage_pct=_decimal(values, "ORDERBOOK_MAX_SLIPPAGE_PCT", "0.50"),
        orderbook_min_fill_ratio=_decimal(values, "ORDERBOOK_MIN_FILL_RATIO", "0.95"),
        orderbook_min_depth_ratio=_decimal(values, "ORDERBOOK_MIN_DEPTH_RATIO", "0.35"),
        orderbook_liquidity_use_pct=_decimal(values, "ORDERBOOK_LIQUIDITY_USE_PCT", "0.35"),
        orderbook_reprice_spread_pct=_decimal(values, "ORDERBOOK_REPRICE_SPREAD_PCT", "0.12"),
        orderbook_price_step_bps=_decimal(values, "ORDERBOOK_PRICE_STEP_BPS", "5"),
        orderbook_hard_max_spread_pct=_decimal(values, "ORDERBOOK_HARD_MAX_SPREAD_PCT", "0.80"),
        orderbook_min_visible_ask_krw=_decimal(values, "ORDERBOOK_MIN_VISIBLE_ASK_KRW", "50000"),
        orderbook_min_visible_bid_krw=_decimal(values, "ORDERBOOK_MIN_VISIBLE_BID_KRW", "50000"),
        risk_crash_guard_enabled=_bool(_get(values, "RISK_CRASH_GUARD_ENABLED", "true")),
        risk_crash_1m_drop_pct=_decimal(values, "RISK_CRASH_1M_DROP_PCT", "1.0"),
        risk_crash_5m_drop_pct=_decimal(values, "RISK_CRASH_5M_DROP_PCT", "2.5"),
        risk_crash_30m_drop_pct=_decimal(values, "RISK_CRASH_30M_DROP_PCT", "6"),
        risk_crash_drawdown_pct=_decimal(values, "RISK_CRASH_DRAWDOWN_PCT", "8"),
        risk_crash_volatility_pct=_decimal(values, "RISK_CRASH_VOLATILITY_PCT", "7"),
        risk_overheat_day_change_pct=_decimal(values, "RISK_OVERHEAT_DAY_CHANGE_PCT", "18"),
        risk_overheat_1m_reversal_pct=_decimal(values, "RISK_OVERHEAT_1M_REVERSAL_PCT", "-0.35"),
        risk_overheat_range_position_pct=_decimal(values, "RISK_OVERHEAT_RANGE_POSITION_PCT", "92"),
        risk_overheat_volume_ratio=_decimal(values, "RISK_OVERHEAT_VOLUME_RATIO", "3"),
        risk_max_consecutive_losses=_int(values, "RISK_MAX_CONSECUTIVE_LOSSES", "2"),
        risk_strategy_max_consecutive_losses=_int(values, "RISK_STRATEGY_MAX_CONSECUTIVE_LOSSES", "1"),
        risk_same_pattern_max_consecutive_losses=_int(values, "RISK_SAME_PATTERN_MAX_CONSECUTIVE_LOSSES", "1"),
        risk_global_max_consecutive_losses=_int(values, "RISK_GLOBAL_MAX_CONSECUTIVE_LOSSES", "4"),
        risk_loss_streak_cooldown_minutes=_int(values, "RISK_LOSS_STREAK_COOLDOWN_MINUTES", "180"),
        risk_market_min_trade_value_24h_krw=_decimal(values, "RISK_MARKET_MIN_TRADE_VALUE_24H_KRW", "300000000"),
        risk_min_candle_trade_value_krw=_decimal(values, "RISK_MIN_CANDLE_TRADE_VALUE_KRW", "10000000"),
        risk_min_entry_score_buffer=_decimal(values, "RISK_MIN_ENTRY_SCORE_BUFFER", "0.08"),
        risk_chase_5m_rise_pct=_decimal(values, "RISK_CHASE_5M_RISE_PCT", "3.5"),
        risk_chase_30m_rise_pct=_decimal(values, "RISK_CHASE_30M_RISE_PCT", "8"),
        risk_chase_range_position_pct=_decimal(values, "RISK_CHASE_RANGE_POSITION_PCT", "88"),
        risk_chase_volume_ratio=_decimal(values, "RISK_CHASE_VOLUME_RATIO", "2.2"),
        risk_min_trade_pressure=_decimal(values, "RISK_MIN_TRADE_PRESSURE", "-1.4"),
        risk_regime_guard_enabled=_bool(_get(values, "RISK_REGIME_GUARD_ENABLED", "true")),
        risk_regime_min_market_count=_int(values, "RISK_REGIME_MIN_MARKET_COUNT", "3"),
        risk_regime_trend_window_candles=_int(values, "RISK_REGIME_TREND_WINDOW_CANDLES", "12"),
        risk_regime_min_positive_ratio=_decimal(values, "RISK_REGIME_MIN_POSITIVE_RATIO", "0.38"),
        risk_regime_soft_positive_ratio=_decimal(values, "RISK_REGIME_SOFT_POSITIVE_RATIO", "0.48"),
        risk_regime_risk_on_positive_ratio=_decimal(values, "RISK_REGIME_RISK_ON_POSITIVE_RATIO", "0.62"),
        risk_regime_max_crash_ratio=_decimal(values, "RISK_REGIME_MAX_CRASH_RATIO", "0.28"),
        risk_regime_crash_trend_pct=_decimal(values, "RISK_REGIME_CRASH_TREND_PCT", "2.5"),
        risk_regime_min_avg_trend_pct=_decimal(values, "RISK_REGIME_MIN_AVG_TREND_PCT", "-1.0"),
        dynamic_allocation_enabled=_bool(_get(values, "DYNAMIC_ALLOCATION_ENABLED", "true")),
        allocation_interval_seconds=_int(values, "ALLOCATION_INTERVAL_SECONDS", "300"),
        allocation_top_n=_int(values, "ALLOCATION_TOP_N", "8"),
        allocation_focus_top_n=_int(values, "ALLOCATION_FOCUS_TOP_N", "3"),
        allocation_focus_score_gap=_decimal(values, "ALLOCATION_FOCUS_SCORE_GAP", "0.12"),
        allocation_min_score=_decimal(values, "ALLOCATION_MIN_SCORE", "0.02"),
        allocation_max_deploy_pct=_decimal(values, "ALLOCATION_MAX_DEPLOY_PCT", "1"),
        allocation_max_position_pct=_decimal(values, "ALLOCATION_MAX_POSITION_PCT", "1"),
        allocation_max_orders_per_run=_int(values, "ALLOCATION_MAX_ORDERS_PER_RUN", "3"),
        paper_cash_krw=_decimal(values, "PAPER_CASH_KRW", "1000000"),
        goal_start_krw=_decimal(values, "GOAL_START_KRW", "1000000"),
        goal_target_krw=_decimal(values, "GOAL_TARGET_KRW", "100000000"),
        goal_days=_int(values, "GOAL_DAYS", "30"),
        goal_scheduler_trading_enabled=_bool(_get(values, "GOAL_SCHEDULER_TRADING_ENABLED", "true")),
        goal_scheduler_max_entry_relief=_decimal(values, "GOAL_SCHEDULER_MAX_ENTRY_RELIEF", "0.08"),
        goal_scheduler_max_deploy_boost=_decimal(values, "GOAL_SCHEDULER_MAX_DEPLOY_BOOST", "0.40"),
        goal_scheduler_max_order_boost=_decimal(values, "GOAL_SCHEDULER_MAX_ORDER_BOOST", "0.25"),
        goal_scheduler_max_position_boost=_decimal(values, "GOAL_SCHEDULER_MAX_POSITION_BOOST", "0.35"),
        min_order_krw=_decimal(values, "RISK_MIN_ORDER_KRW", "5000"),
        max_order_krw=_decimal(values, "RISK_MAX_ORDER_KRW", "100000000"),
        max_position_krw=_decimal(values, "RISK_MAX_POSITION_KRW", "100000000"),
        daily_loss_limit_krw=_decimal(values, "RISK_DAILY_LOSS_LIMIT_KRW", "50000"),
        stop_loss_pct=_decimal(values, "RISK_STOP_LOSS_PCT", "3"),
        take_profit_pct=_decimal(values, "RISK_TAKE_PROFIT_PCT", "6"),
        cooldown_seconds=_int(values, "RISK_COOLDOWN_SECONDS", "900"),
        max_open_positions=_int(values, "RISK_MAX_OPEN_POSITIONS", "50"),
        max_daily_orders=_int(values, "RISK_MAX_DAILY_ORDERS", "80"),
        paper_extreme_mode=_bool(_get(values, "PAPER_EXTREME_MODE", "false")),
        auto_run_enabled=_bool(_get(values, "AUTO_RUN_ENABLED", "false")),
        fee_rate=_decimal(values, "RISK_FEE_RATE", "0.0005"),
        live_trading_enabled=_bool(_get(values, "LIVE_TRADING_ENABLED", "false")),
        web_live_trading_enabled=_bool(_get(values, "WEB_LIVE_TRADING_ENABLED", "false")),
        live_order_confirmation=_get(values, "LIVE_ORDER_CONFIRMATION", ""),
        live_test_order_enabled=_bool(_get(values, "LIVE_TEST_ORDER_ENABLED", "false")),
        ai_pm_enabled=_bool(_get(values, "AI_PM_ENABLED", "false")),
        ai_pm_api_key=_get(values, "AI_PM_API_KEY", _get(values, "OPENAI_API_KEY", "")),
        ai_pm_base_url=_get(values, "AI_PM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        ai_pm_model=_get(values, "AI_PM_MODEL", "gpt-5"),
        ai_pm_interval_seconds=_int(values, "AI_PM_INTERVAL_SECONDS", "60"),
        ai_pm_max_candidates=_int(values, "AI_PM_MAX_CANDIDATES", "8"),
        ops_alerts_enabled=_bool(_get(values, "OPS_ALERTS_ENABLED", "true")),
        dashboard_auth_enabled=_bool(_get(values, "DASHBOARD_AUTH_ENABLED", "false")),
        dashboard_username=_get(values, "DASHBOARD_USERNAME", "admin"),
        dashboard_password=_get(values, "DASHBOARD_PASSWORD", ""),
        event_log_file=Path(_get(values, "EVENT_LOG_FILE", "state/events.jsonl")),
        database_file=Path(_get(values, "DATABASE_FILE", "state/autotrading.sqlite3")),
        binance_base_url=_get(values, "BINANCE_BASE_URL", "https://api.binance.com").rstrip("/"),
        binance_symbols=binance_symbols,
        binance_api_key=_get(values, "BINANCE_API_KEY", ""),
        binance_secret_key=_get(values, "BINANCE_SECRET_KEY", ""),
        binance_futures_base_url=_get(values, "BINANCE_FUTURES_BASE_URL", "https://fapi.binance.com").rstrip("/"),
        binance_futures_testnet_enabled=_bool(_get(values, "BINANCE_FUTURES_TESTNET_ENABLED", "false")),
        binance_futures_symbols=binance_futures_symbols,
        binance_futures_api_key=_get(values, "BINANCE_FUTURES_API_KEY", ""),
        binance_futures_secret_key=_get(values, "BINANCE_FUTURES_SECRET_KEY", ""),
        state_file=Path(_get(values, "TRADING_STATE_FILE", "state/paper_state.json")),
        loop_sleep_seconds=_int(values, "LOOP_SLEEP_SECONDS", "60"),
    )
    settings.validate()
    return settings
