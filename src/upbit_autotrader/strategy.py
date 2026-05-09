from __future__ import annotations

from decimal import Decimal
import json

from .config import SUPPORTED_STRATEGY_NAMES, TradingSettings
from .alex_strategy import evaluate_alex_techniques
from .maeuknam_strategy import evaluate_maeuknam_techniques
from .models import Candle, Signal


STRATEGY_CATALOG = {
    "adaptive_learning": {
        "label": "학습형 적응",
        "description": "과거 데이터 학습 모델이 코인별로 가장 점수가 높았던 전략을 선택합니다.",
        "risk": "보통",
    },
    "guarded_momentum": {
        "label": "보수적 모멘텀",
        "description": "추세, 거래대금, 변동성을 함께 확인하고 조건이 맞을 때만 진입합니다.",
        "risk": "보통",
    },
    "probability_edge": {
        "label": "확률 우위",
        "description": "추세, 통계 신뢰도, 칼만 속도, 거래대금, VWAP, 변동성, 손익비를 결합해 기대값이 높은 자리만 진입합니다.",
        "risk": "보통",
    },
    "maeuknam_cards": {
        "label": "매억남 카드 전용",
        "description": "매억남 영상 분석에서 추출한 지지, 눌림, 리테스트, 파동 카드가 통과할 때만 진입합니다.",
        "risk": "높음",
    },
    "alex_method": {
        "label": "알렉스 매매기법",
        "description": "0.5 평균값, 프리미엄/디스카운트, 유동성 회수, 1-2-3-4 확인을 점수화해 롱/숏을 고정하지 않고 판단합니다.",
        "risk": "높음",
    },
    "sma_cross": {
        "label": "SMA 교차",
        "description": "단기 이동평균이 장기 이동평균을 상향/하향 돌파하는 순간을 봅니다.",
        "risk": "보통",
    },
    "breakout": {
        "label": "고점 돌파",
        "description": "최근 박스권 고점을 거래대금과 함께 돌파할 때 추세 진입을 시도합니다.",
        "risk": "높음",
    },
    "mean_reversion": {
        "label": "평균회귀",
        "description": "가격이 장기 평균보다 과하게 밀렸을 때 반등 후보로 보고, 평균 위 과열은 매도 후보로 봅니다.",
        "risk": "높음",
    },
    "rsi_reversal": {
        "label": "RSI 반전",
        "description": "RSI 과매도 구간은 반등 후보, 과매수 구간은 청산 후보로 봅니다.",
        "risk": "높음",
    },
    "macd_cross": {
        "label": "MACD 교차",
        "description": "MACD선과 시그널선의 교차로 추세 전환 후보를 찾습니다.",
        "risk": "보통",
    },
    "statistical_filter": {
        "label": "통계 필터",
        "description": "회귀 기울기, 칼만 추정오차, 가격·거래대금 공분산오차를 함께 확인합니다.",
        "risk": "보통",
    },
    "bollinger_band": {
        "label": "볼린저밴드",
        "description": "하단 밴드 이탈은 반등 후보, 상단 밴드 돌파는 과열 후보로 봅니다.",
        "risk": "높음",
    },
    "stochastic": {
        "label": "스토캐스틱",
        "description": "%K와 %D 교차를 과매도/과매수 영역과 함께 확인합니다.",
        "risk": "높음",
    },
    "ichimoku_trend": {
        "label": "일목균형표",
        "description": "전환선, 기준선, 구름대 위치로 추세 우위를 판단합니다.",
        "risk": "보통",
    },
    "vwap_reversion": {
        "label": "VWAP 회귀",
        "description": "거래량 가중 평균가격에서 크게 벗어난 구간의 회귀를 노립니다.",
        "risk": "높음",
    },
    "donchian_channel": {
        "label": "Donchian 채널",
        "description": "최근 고가/저가 채널 돌파와 이탈을 추세 신호로 봅니다.",
        "risk": "높음",
    },
}

STRATEGY_ORDER = (
    "adaptive_learning",
    "guarded_momentum",
    "probability_edge",
    "maeuknam_cards",
    "alex_method",
    "sma_cross",
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
)


def strategy_catalog(active: str) -> list[dict[str, str | bool]]:
    return [
        {
            "name": name,
            **STRATEGY_CATALOG[name],
            "active": name == active,
        }
        for name in STRATEGY_ORDER
    ]


def is_supported_strategy(name: str) -> bool:
    return name in SUPPORTED_STRATEGY_NAMES


def moving_average(values: list[Decimal], window: int) -> Decimal:
    if window <= 0:
        raise ValueError("이동평균 기간은 1 이상이어야 합니다")
    if len(values) < window:
        raise ValueError("이동평균을 계산할 값이 부족합니다")
    return sum(values[-window:], Decimal("0")) / Decimal(window)


def pct_change(start: Decimal, end: Decimal) -> Decimal:
    if start == 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def true_range_pct(candles: list[Candle], window: int) -> Decimal:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if not ordered:
        return Decimal("0")
    subset = ordered[-window:]
    ranges = [
        (candle.high_price - candle.low_price) / candle.trade_price * Decimal("100")
        for candle in subset
        if candle.trade_price > 0
    ]
    if not ranges:
        return Decimal("0")
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def volume_ratio(candles: list[Candle], window: int) -> Decimal:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if len(ordered) < window + 1:
        return Decimal("1")
    previous = [candle.candle_acc_trade_price for candle in ordered[-window - 1 : -1]]
    previous_avg = sum(previous, Decimal("0")) / Decimal(len(previous))
    if previous_avg <= 0:
        return Decimal("1")
    return ordered[-1].candle_acc_trade_price / previous_avg


def standard_deviation(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    average = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((value - average) ** 2 for value in values) / Decimal(len(values))
    return variance.sqrt()


def relative_strength_index(values: list[Decimal], period: int = 14) -> Decimal:
    if len(values) < period + 1:
        return Decimal("50")
    changes = [values[index] - values[index - 1] for index in range(len(values) - period, len(values))]
    gains = [change for change in changes if change > 0]
    losses = [-change for change in changes if change < 0]
    average_gain = sum(gains, Decimal("0")) / Decimal(period)
    average_loss = sum(losses, Decimal("0")) / Decimal(period)
    if average_loss == 0:
        return Decimal("100") if average_gain > 0 else Decimal("50")
    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def exponential_moving_average_series(values: list[Decimal], period: int) -> list[Decimal]:
    if not values:
        return []
    multiplier = Decimal("2") / Decimal(period + 1)
    ema = values[0]
    rows: list[Decimal] = []
    for value in values:
        ema = (value - ema) * multiplier + ema
        rows.append(ema)
    return rows


def stochastic_k(candles: list[Candle], period: int = 14) -> Decimal:
    if len(candles) < period:
        return Decimal("50")
    subset = candles[-period:]
    highest_high = max(candle.high_price for candle in subset)
    lowest_low = min(candle.low_price for candle in subset)
    if highest_high == lowest_low:
        return Decimal("50")
    return (subset[-1].trade_price - lowest_low) / (highest_high - lowest_low) * Decimal("100")


def vwap(candles: list[Candle]) -> Decimal:
    volume = sum(candle.candle_acc_trade_volume for candle in candles)
    if volume > 0:
        return sum(candle.trade_price * candle.candle_acc_trade_volume for candle in candles) / volume
    trade_value = sum(candle.candle_acc_trade_price for candle in candles)
    fallback_volume = sum(
        candle.candle_acc_trade_price / candle.trade_price
        for candle in candles
        if candle.trade_price > 0
    )
    if fallback_volume <= 0:
        return candles[-1].trade_price if candles else Decimal("0")
    return trade_value / fallback_volume


def returns_pct(values: list[Decimal]) -> list[Decimal]:
    return [
        pct_change(values[index - 1], values[index])
        for index in range(1, len(values))
        if values[index - 1] != 0
    ]


def covariance(values_a: list[Decimal], values_b: list[Decimal]) -> Decimal:
    size = min(len(values_a), len(values_b))
    if size <= 1:
        return Decimal("0")
    rows_a = values_a[-size:]
    rows_b = values_b[-size:]
    average_a = sum(rows_a, Decimal("0")) / Decimal(size)
    average_b = sum(rows_b, Decimal("0")) / Decimal(size)
    return sum((a - average_a) * (b - average_b) for a, b in zip(rows_a, rows_b)) / Decimal(size)


def correlation(values_a: list[Decimal], values_b: list[Decimal]) -> Decimal:
    size = min(len(values_a), len(values_b))
    if size <= 1:
        return Decimal("0")
    rows_a = values_a[-size:]
    rows_b = values_b[-size:]
    deviation_a = standard_deviation(rows_a)
    deviation_b = standard_deviation(rows_b)
    if deviation_a == 0 or deviation_b == 0:
        return Decimal("0")
    return covariance(rows_a, rows_b) / (deviation_a * deviation_b)


def regression_metrics(values: list[Decimal]) -> dict[str, Decimal]:
    if len(values) < 3 or values[0] == 0:
        return {"slopePct": Decimal("0"), "rSquared": Decimal("0"), "residualStdPct": Decimal("0")}

    y_values = [pct_change(values[0], value) for value in values]
    x_values = [Decimal(index) for index in range(len(y_values))]
    size = Decimal(len(y_values))
    average_x = sum(x_values, Decimal("0")) / size
    average_y = sum(y_values, Decimal("0")) / size
    variance_x = sum((x - average_x) ** 2 for x in x_values)
    if variance_x == 0:
        return {"slopePct": Decimal("0"), "rSquared": Decimal("0"), "residualStdPct": Decimal("0")}

    slope = sum((x - average_x) * (y - average_y) for x, y in zip(x_values, y_values)) / variance_x
    intercept = average_y - slope * average_x
    predicted = [intercept + slope * x for x in x_values]
    residuals = [y - estimate for y, estimate in zip(y_values, predicted)]
    ss_residual = sum(residual ** 2 for residual in residuals)
    ss_total = sum((y - average_y) ** 2 for y in y_values)
    r_squared = Decimal("0") if ss_total == 0 else Decimal("1") - ss_residual / ss_total
    r_squared = max(Decimal("0"), min(Decimal("1"), r_squared))
    residual_std = (ss_residual / size).sqrt()
    return {"slopePct": slope, "rSquared": r_squared, "residualStdPct": residual_std}


def kalman_price_metrics(values: list[Decimal]) -> dict[str, Decimal]:
    if len(values) < 3 or values[0] == 0:
        return {
            "estimatePct": Decimal("0"),
            "velocityPct": Decimal("0"),
            "residualPct": Decimal("0"),
            "errorPct": Decimal("0"),
        }

    measurements = [pct_change(values[0], value) for value in values]
    measurement_std = standard_deviation(returns_pct(values)) or Decimal("0.01")
    measurement_variance = max(measurement_std ** 2, Decimal("0.0001"))
    process_variance = max(measurement_variance * Decimal("0.08"), Decimal("0.00001"))
    estimate = measurements[0]
    previous_estimate = estimate
    error_covariance = Decimal("1")

    for measurement in measurements[1:]:
        error_covariance += process_variance
        gain = error_covariance / (error_covariance + measurement_variance)
        previous_estimate = estimate
        estimate = estimate + gain * (measurement - estimate)
        error_covariance = (Decimal("1") - gain) * error_covariance

    residual = measurements[-1] - estimate
    return {
        "estimatePct": estimate,
        "velocityPct": estimate - previous_estimate,
        "residualPct": residual,
        "errorPct": error_covariance.sqrt(),
    }


def covariance_error_metrics(price_returns: list[Decimal], trade_value_returns: list[Decimal]) -> dict[str, Decimal]:
    corr = correlation(price_returns, trade_value_returns)
    error = Decimal("1") - min(Decimal("1"), abs(corr))
    return {"correlation": corr, "error": error}


def midpoint(candles: list[Candle]) -> Decimal:
    highest_high = max(candle.high_price for candle in candles)
    lowest_low = min(candle.low_price for candle in candles)
    return (highest_high + lowest_low) / Decimal("2")


def clamp_decimal(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return max(lower, min(upper, value))


def path_efficiency(closes: list[Decimal], window: int) -> Decimal:
    rows = closes[-window:]
    if len(rows) < 2:
        return Decimal("0")
    total_path = sum(
        abs(pct_change(rows[index - 1], rows[index]))
        for index in range(1, len(rows))
        if rows[index - 1] != 0
    )
    if total_path == 0:
        return Decimal("0")
    return min(Decimal("1"), abs(pct_change(rows[0], rows[-1])) / total_path)


class SmaCrossStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        market = latest.market

        required = self.settings.long_window + 1
        if len(closes) < required:
            return Signal(
                "hold",
                market,
                latest.trade_price,
                f"최소 {required}개의 캔들이 필요합니다",
            )

        previous_closes = closes[:-1]
        previous_short = moving_average(previous_closes, self.settings.short_window)
        previous_long = moving_average(previous_closes, self.settings.long_window)
        current_short = moving_average(closes, self.settings.short_window)
        current_long = moving_average(closes, self.settings.long_window)

        if previous_short <= previous_long and current_short > current_long:
            return Signal(
                "buy",
                market,
                latest.trade_price,
                f"SMA{self.settings.short_window}이 SMA{self.settings.long_window}을 상향 돌파했습니다",
            )
        if previous_short >= previous_long and current_short < current_long:
            return Signal(
                "sell",
                market,
                latest.trade_price,
                f"SMA{self.settings.short_window}이 SMA{self.settings.long_window}을 하향 이탈했습니다",
            )

        return Signal(
            "hold",
            market,
            latest.trade_price,
            f"SMA{self.settings.short_window}={current_short:.2f}, SMA{self.settings.long_window}={current_long:.2f}",
        )


class GuardedMomentumStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        required = self.settings.long_window + 2
        if len(closes) < required:
            return Signal("hold", latest.market, latest.trade_price, f"최소 {required}개의 캔들이 필요합니다")

        current_short = moving_average(closes, self.settings.short_window)
        current_long = moving_average(closes, self.settings.long_window)
        previous_long = moving_average(closes[:-1], self.settings.long_window)
        trend_pct = pct_change(current_long, current_short)
        long_slope_pct = pct_change(previous_long, current_long)
        volatility_pct = true_range_pct(ordered, min(self.settings.long_window, len(ordered)))
        trade_value_ratio = volume_ratio(ordered, min(self.settings.short_window, len(ordered) - 1))
        recent_high = max(closes[-self.settings.long_window :])
        pullback_pct = pct_change(recent_high, latest.trade_price)

        if volatility_pct > self.settings.strategy_max_volatility_pct:
            return Signal(
                "hold",
                latest.market,
                latest.trade_price,
                f"변동성 {volatility_pct:.2f}%가 상한 {self.settings.strategy_max_volatility_pct}%를 넘었습니다",
                Decimal("0.35"),
            )

        if (
            current_short > current_long
            and trend_pct >= self.settings.strategy_min_trend_pct
            and long_slope_pct >= 0
            and trade_value_ratio >= self.settings.strategy_min_volume_ratio
        ):
            strength = min(Decimal("2"), Decimal("1") + trend_pct / Decimal("10"))
            return Signal(
                "buy",
                latest.market,
                latest.trade_price,
                f"보수적 모멘텀 매수: 추세 {trend_pct:.2f}%, 거래대금 {trade_value_ratio:.2f}배, 변동성 {volatility_pct:.2f}%",
                strength,
            )

        if current_short < current_long or pullback_pct <= -self.settings.strategy_pullback_sell_pct:
            return Signal(
                "sell",
                latest.market,
                latest.trade_price,
                f"보수적 모멘텀 매도: 추세 {trend_pct:.2f}%, 고점대비 {pullback_pct:.2f}%",
            )

        return Signal(
            "hold",
            latest.market,
            latest.trade_price,
            f"관망: 추세 {trend_pct:.2f}%, 거래대금 {trade_value_ratio:.2f}배, 변동성 {volatility_pct:.2f}%",
            Decimal("0.5"),
        )


class ProbabilityEdgeStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        closes = [candle.trade_price for candle in ordered]
        required = max(52, self.settings.long_window * 2 + 5)
        if len(closes) < required:
            return Signal("hold", latest.market, latest.trade_price, f"확률 우위 계산에는 최소 {required}개 캔들이 필요합니다")

        window = min(len(ordered), max(required, self.settings.long_window * 3))
        subset = ordered[-window:]
        subset_closes = [candle.trade_price for candle in subset]
        current_short = moving_average(subset_closes, self.settings.short_window)
        current_long = moving_average(subset_closes, self.settings.long_window)
        previous_long = moving_average(subset_closes[:-1], self.settings.long_window)
        trend_pct = pct_change(current_long, current_short)
        long_slope_pct = pct_change(previous_long, current_long)
        trend_12 = pct_change(subset_closes[-13], subset_closes[-1]) if len(subset_closes) >= 13 else Decimal("0")
        trend_30 = pct_change(subset_closes[-31], subset_closes[-1]) if len(subset_closes) >= 31 else Decimal("0")
        regression = regression_metrics(subset_closes[-min(len(subset_closes), 36):])
        kalman = kalman_price_metrics(subset_closes[-min(len(subset_closes), 36):])
        trade_value_ratio = volume_ratio(ordered, min(self.settings.short_window, len(ordered) - 1))
        volatility_pct = true_range_pct(subset, min(self.settings.long_window, len(subset)))
        rsi = relative_strength_index(subset_closes, min(14, len(subset_closes) - 1))
        current_vwap = vwap(subset[-min(len(subset), self.settings.long_window * 2):])
        vwap_deviation_pct = pct_change(current_vwap, latest.trade_price)
        recent_high = max(candle.high_price for candle in subset[-self.settings.long_window:])
        recent_low = min(candle.low_price for candle in subset[-self.settings.long_window:])
        previous_channel = subset[-self.settings.long_window - 1:-1]
        channel_high = max(candle.high_price for candle in previous_channel) if previous_channel else recent_high
        channel_low = min(candle.low_price for candle in previous_channel) if previous_channel else recent_low
        channel_width_pct = pct_change(channel_low, channel_high) if channel_low > 0 else Decimal("0")
        drawdown_pct = max(Decimal("0"), Decimal("0") - pct_change(recent_high, latest.trade_price))
        range_position = (
            (latest.trade_price - recent_low) / (recent_high - recent_low) * Decimal("100")
            if recent_high != recent_low
            else Decimal("50")
        )
        support_risk_pct = (
            (latest.trade_price - recent_low) / latest.trade_price * Decimal("100")
            if latest.trade_price > 0 and latest.trade_price > recent_low
            else Decimal("0.2")
        )
        expected_reward_pct = max(
            self.settings.take_profit_pct / Decimal("2"),
            max(Decimal("0"), pct_change(latest.trade_price, channel_high)),
            channel_width_pct / Decimal("4"),
        )
        planned_risk_pct = max(Decimal("0.2"), min(self.settings.stop_loss_pct, support_risk_pct))
        risk_reward = expected_reward_pct / planned_risk_pct if planned_risk_pct > 0 else Decimal("0")
        efficiency = path_efficiency(subset_closes, min(24, len(subset_closes)))
        energy = (
            (max(Decimal("0"), trend_12) + max(Decimal("0"), trend_30) / Decimal("2"))
            * min(Decimal("2"), trade_value_ratio)
            / max(Decimal("0.35"), volatility_pct)
        )

        edge = Decimal("0.50")
        edge += clamp_decimal(trend_pct / Decimal("3"), Decimal("-0.12"), Decimal("0.12"))
        edge += clamp_decimal(long_slope_pct / Decimal("1.2"), Decimal("-0.08"), Decimal("0.08"))
        edge += clamp_decimal(trend_12 / Decimal("8"), Decimal("-0.10"), Decimal("0.10"))
        edge += clamp_decimal(regression["slopePct"] / Decimal("0.45"), Decimal("-0.10"), Decimal("0.10"))
        edge += regression["rSquared"] * Decimal("0.07")
        edge += clamp_decimal(kalman["velocityPct"] / Decimal("0.35"), Decimal("-0.08"), Decimal("0.08"))
        edge += clamp_decimal((trade_value_ratio - Decimal("1")) / Decimal("5"), Decimal("-0.04"), Decimal("0.08"))
        edge += clamp_decimal((risk_reward - Decimal("1")) / Decimal("5"), Decimal("-0.06"), Decimal("0.10"))
        edge += clamp_decimal((efficiency - Decimal("0.18")) / Decimal("3"), Decimal("-0.04"), Decimal("0.05"))
        edge += clamp_decimal(energy / Decimal("30"), Decimal("0"), Decimal("0.04"))
        if Decimal("42") <= rsi <= Decimal("68"):
            edge += Decimal("0.04")
        if Decimal("-1.2") <= vwap_deviation_pct <= Decimal("3.2"):
            edge += Decimal("0.04")
        if drawdown_pct <= self.settings.strategy_pullback_sell_pct / Decimal("2"):
            edge += Decimal("0.03")
        if volatility_pct < self.settings.realtime_low_volatility_pct:
            edge -= Decimal("0.08")
        if volatility_pct > self.settings.strategy_max_volatility_pct:
            edge -= Decimal("0.18")
        if rsi >= Decimal("74") or range_position >= Decimal("94") or vwap_deviation_pct >= self.settings.take_profit_pct:
            edge -= Decimal("0.10")
        edge = clamp_decimal(edge, Decimal("0"), Decimal("0.99"))

        reason = (
            f"확률 우위 {edge * Decimal('100'):.1f}%: "
            f"추세 {trend_pct:.2f}%/12봉 {trend_12:.2f}%, "
            f"회귀 R² {regression['rSquared']:.2f}, 칼만속도 {kalman['velocityPct']:.3f}%, "
            f"거래대금 {trade_value_ratio:.2f}배, 변동성 {volatility_pct:.2f}%, "
            f"RSI {rsi:.1f}, VWAP {vwap_deviation_pct:.2f}%, 손익비 {risk_reward:.2f}, "
            f"효율 {efficiency:.2f}, 에너지 {energy:.2f}"
        )

        breakdown = (
            (current_short < current_long and long_slope_pct < 0)
            or (trend_12 <= Decimal("0") - self.settings.strategy_pullback_sell_pct / Decimal("2") and kalman["velocityPct"] < 0)
            or latest.trade_price < channel_low
            or drawdown_pct >= self.settings.strategy_pullback_sell_pct
        )
        if breakdown:
            return Signal("sell", latest.market, latest.trade_price, f"{reason} · 추세 붕괴/손절 우선", Decimal("0.85"))

        buy_gate = (
            edge >= Decimal("0.68")
            and current_short > current_long
            and trend_pct >= self.settings.strategy_min_trend_pct
            and long_slope_pct >= 0
            and trend_12 > Decimal("0")
            and regression["slopePct"] > 0
            and kalman["velocityPct"] > 0
            and trade_value_ratio >= self.settings.strategy_min_volume_ratio
            and risk_reward >= Decimal("1.25")
            and self.settings.realtime_low_volatility_pct <= volatility_pct <= self.settings.strategy_max_volatility_pct
            and rsi < Decimal("74")
            and range_position < Decimal("94")
        )
        if buy_gate:
            strength = clamp_decimal(
                Decimal("0.75") + (edge - Decimal("0.62")) * Decimal("4"),
                Decimal("0.75"),
                Decimal("2"),
            )
            return Signal("buy", latest.market, latest.trade_price, f"{reason} · 매수 게이트 통과", strength)

        if edge < Decimal("0.46") and (trend_12 < 0 or kalman["velocityPct"] <= 0):
            return Signal("sell", latest.market, latest.trade_price, f"{reason} · 기대값 약화", Decimal("0.7"))

        return Signal("hold", latest.market, latest.trade_price, f"{reason} · 관망", Decimal("0.5"))


class BreakoutStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        required = self.settings.long_window + 1
        if len(ordered) < required:
            return Signal("hold", latest.market, latest.trade_price, f"최소 {required}개의 캔들이 필요합니다")

        previous = ordered[-required:-1]
        previous_high = max(candle.high_price for candle in previous)
        previous_low = min(candle.low_price for candle in previous)
        trade_value_ratio = volume_ratio(ordered, min(self.settings.short_window, len(ordered) - 1))
        breakout_pct = pct_change(previous_high, latest.trade_price)
        breakdown_pct = pct_change(previous_low, latest.trade_price)

        if latest.trade_price > previous_high and trade_value_ratio >= self.settings.strategy_min_volume_ratio:
            strength = min(Decimal("2"), Decimal("1") + breakout_pct / Decimal("5"))
            return Signal(
                "buy",
                latest.market,
                latest.trade_price,
                f"고점 돌파 매수: 최근 고점 대비 {breakout_pct:.2f}%, 거래대금 {trade_value_ratio:.2f}배",
                strength,
            )

        if latest.trade_price < previous_low:
            return Signal(
                "sell",
                latest.market,
                latest.trade_price,
                f"박스권 하단 이탈: 최근 저점 대비 {breakdown_pct:.2f}%",
            )

        return Signal(
            "hold",
            latest.market,
            latest.trade_price,
            f"돌파 대기: 고점 대비 {breakout_pct:.2f}%, 거래대금 {trade_value_ratio:.2f}배",
            Decimal("0.5"),
        )


class MeanReversionStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        required = self.settings.long_window
        if len(closes) < required:
            return Signal("hold", latest.market, latest.trade_price, f"최소 {required}개의 캔들이 필요합니다")

        average = moving_average(closes, self.settings.long_window)
        deviation_pct = pct_change(average, latest.trade_price)
        buy_threshold = Decimal("0") - self.settings.strategy_pullback_sell_pct
        sell_threshold = self.settings.take_profit_pct

        if deviation_pct <= buy_threshold:
            strength = min(Decimal("2"), Decimal("1") + abs(deviation_pct) / Decimal("10"))
            return Signal(
                "buy",
                latest.market,
                latest.trade_price,
                f"평균회귀 매수 후보: 장기 평균 대비 {deviation_pct:.2f}%",
                strength,
            )

        if deviation_pct >= sell_threshold:
            return Signal(
                "sell",
                latest.market,
                latest.trade_price,
                f"평균 대비 과열: 장기 평균 대비 {deviation_pct:.2f}%",
            )

        return Signal(
            "hold",
            latest.market,
            latest.trade_price,
            f"평균회귀 대기: 장기 평균 대비 {deviation_pct:.2f}%",
            Decimal("0.5"),
        )


class RsiReversalStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        period = min(14, max(self.settings.long_window, 14))
        if len(closes) < period + 1:
            return Signal("hold", latest.market, latest.trade_price, f"RSI 계산에는 최소 {period + 1}개의 캔들이 필요합니다")

        rsi = relative_strength_index(closes, period)
        if rsi <= Decimal("30"):
            return Signal("buy", latest.market, latest.trade_price, f"RSI 과매도 반전 후보: RSI {rsi:.2f}", Decimal("0.8"))
        if rsi >= Decimal("70"):
            return Signal("sell", latest.market, latest.trade_price, f"RSI 과매수 청산 후보: RSI {rsi:.2f}")
        return Signal("hold", latest.market, latest.trade_price, f"RSI 중립: RSI {rsi:.2f}", Decimal("0.5"))


class MacdCrossStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        if len(closes) < 35:
            return Signal("hold", latest.market, latest.trade_price, "MACD 계산에는 최소 35개의 캔들이 필요합니다")

        ema_fast = exponential_moving_average_series(closes, 12)
        ema_slow = exponential_moving_average_series(closes, 26)
        macd_rows = [fast - slow for fast, slow in zip(ema_fast, ema_slow)]
        signal_rows = exponential_moving_average_series(macd_rows, 9)
        previous_macd, current_macd = macd_rows[-2], macd_rows[-1]
        previous_signal, current_signal = signal_rows[-2], signal_rows[-1]

        if previous_macd <= previous_signal and current_macd > current_signal:
            return Signal("buy", latest.market, latest.trade_price, f"MACD 상향 교차: MACD {current_macd:.2f}, Signal {current_signal:.2f}")
        if previous_macd >= previous_signal and current_macd < current_signal:
            return Signal("sell", latest.market, latest.trade_price, f"MACD 하향 교차: MACD {current_macd:.2f}, Signal {current_signal:.2f}")
        return Signal("hold", latest.market, latest.trade_price, f"MACD 대기: MACD {current_macd:.2f}, Signal {current_signal:.2f}", Decimal("0.5"))


class StatisticalFilterStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        required = max(self.settings.long_window + 5, 20)
        if len(ordered) < required:
            return Signal("hold", latest.market, latest.trade_price, f"통계 필터 계산에는 최소 {required}개의 캔들이 필요합니다")

        window = min(len(ordered), max(self.settings.long_window * 2, required))
        subset = ordered[-window:]
        closes = [candle.trade_price for candle in subset]
        trade_values = [candle.candle_acc_trade_price for candle in subset]
        regression = regression_metrics(closes)
        kalman = kalman_price_metrics(closes)
        covariance_error = covariance_error_metrics(returns_pct(closes), returns_pct(trade_values))
        volatility_pct = true_range_pct(subset, min(self.settings.long_window, len(subset)))
        trade_value_ratio = volume_ratio(ordered, min(self.settings.short_window, len(ordered) - 1))
        slope_floor = max(Decimal("0.02"), self.settings.strategy_min_trend_pct / Decimal("2"))
        confidence = regression["rSquared"] * (Decimal("1") - covariance_error["error"] / Decimal("2"))

        reason = (
            f"통계 필터: 회귀기울기 {regression['slopePct']:.3f}%/봉, "
            f"R² {regression['rSquared']:.2f}, 칼만속도 {kalman['velocityPct']:.3f}%, "
            f"칼만오차 {kalman['errorPct']:.3f}%, 공분산오차 {covariance_error['error']:.2f}, "
            f"거래대금 {trade_value_ratio:.2f}배"
        )

        if volatility_pct > self.settings.strategy_max_volatility_pct:
            return Signal(
                "hold",
                latest.market,
                latest.trade_price,
                f"{reason} · 변동성 {volatility_pct:.2f}%가 상한을 넘었습니다",
                Decimal("0.35"),
            )

        if (
            regression["slopePct"] >= slope_floor
            and regression["rSquared"] >= Decimal("0.35")
            and kalman["velocityPct"] > 0
            and kalman["residualPct"] >= Decimal("0") - self.settings.strategy_pullback_sell_pct / Decimal("3")
            and covariance_error["correlation"] >= Decimal("-0.15")
            and trade_value_ratio >= self.settings.strategy_min_volume_ratio * Decimal("0.9")
        ):
            strength = min(
                Decimal("2"),
                Decimal("0.75")
                + regression["slopePct"] / Decimal("0.25")
                + confidence / Decimal("2")
                + max(Decimal("0"), covariance_error["correlation"]) / Decimal("3"),
            )
            return Signal("buy", latest.market, latest.trade_price, f"{reason} · 통계 상승 추세 승인", strength)

        if (
            regression["slopePct"] <= Decimal("0") - slope_floor
            and kalman["velocityPct"] <= 0
        ) or (
            kalman["residualPct"] <= Decimal("0") - self.settings.strategy_pullback_sell_pct / Decimal("2")
            and regression["slopePct"] < 0
        ):
            return Signal("sell", latest.market, latest.trade_price, f"{reason} · 통계 하락 전환")

        return Signal("hold", latest.market, latest.trade_price, reason, Decimal("0.5"))


class BollingerBandStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        closes = [candle.trade_price for candle in ordered]
        latest = ordered[-1]
        window = max(self.settings.long_window, 20)
        if len(closes) < window:
            return Signal("hold", latest.market, latest.trade_price, f"볼린저밴드 계산에는 최소 {window}개의 캔들이 필요합니다")

        subset = closes[-window:]
        middle = moving_average(closes, window)
        deviation = standard_deviation(subset)
        upper = middle + deviation * Decimal("2")
        lower = middle - deviation * Decimal("2")
        if latest.trade_price <= lower:
            return Signal("buy", latest.market, latest.trade_price, f"볼린저 하단 이탈 반등 후보: 하단 {lower:.2f}", Decimal("0.75"))
        if latest.trade_price >= upper:
            return Signal("sell", latest.market, latest.trade_price, f"볼린저 상단 과열 후보: 상단 {upper:.2f}")
        band_pct = pct_change(middle, latest.trade_price)
        return Signal("hold", latest.market, latest.trade_price, f"볼린저밴드 내부: 중심 대비 {band_pct:.2f}%", Decimal("0.5"))


class StochasticStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        period = 14
        if len(ordered) < period + 3:
            return Signal("hold", latest.market, latest.trade_price, f"스토캐스틱 계산에는 최소 {period + 3}개의 캔들이 필요합니다")

        k_rows = [stochastic_k(ordered[:index], period) for index in range(period, len(ordered) + 1)]
        current_k = k_rows[-1]
        previous_k = k_rows[-2]
        current_d = sum(k_rows[-3:], Decimal("0")) / Decimal("3")
        previous_d = sum(k_rows[-4:-1], Decimal("0")) / Decimal("3")

        if previous_k <= previous_d and current_k > current_d and current_k <= Decimal("35"):
            return Signal("buy", latest.market, latest.trade_price, f"스토캐스틱 과매도 상향 교차: K {current_k:.2f}, D {current_d:.2f}")
        if previous_k >= previous_d and current_k < current_d and current_k >= Decimal("65"):
            return Signal("sell", latest.market, latest.trade_price, f"스토캐스틱 과매수 하향 교차: K {current_k:.2f}, D {current_d:.2f}")
        return Signal("hold", latest.market, latest.trade_price, f"스토캐스틱 대기: K {current_k:.2f}, D {current_d:.2f}", Decimal("0.5"))


class IchimokuTrendStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        if len(ordered) < 52:
            return Signal("hold", latest.market, latest.trade_price, "일목균형표 계산에는 최소 52개의 캔들이 필요합니다")

        tenkan = midpoint(ordered[-9:])
        kijun = midpoint(ordered[-26:])
        span_a = (tenkan + kijun) / Decimal("2")
        span_b = midpoint(ordered[-52:])
        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)

        if latest.trade_price > cloud_top and tenkan > kijun:
            return Signal("buy", latest.market, latest.trade_price, f"일목 상승 추세: 전환선 {tenkan:.2f} > 기준선 {kijun:.2f}")
        if latest.trade_price < cloud_bottom or tenkan < kijun:
            return Signal("sell", latest.market, latest.trade_price, f"일목 약세 신호: 전환선 {tenkan:.2f}, 기준선 {kijun:.2f}")
        return Signal("hold", latest.market, latest.trade_price, f"일목 구름대 대기: 구름 {cloud_bottom:.2f}~{cloud_top:.2f}", Decimal("0.5"))


class VwapReversionStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        window = max(self.settings.long_window, 20)
        if len(ordered) < window:
            return Signal("hold", latest.market, latest.trade_price, f"VWAP 계산에는 최소 {window}개의 캔들이 필요합니다")

        current_vwap = vwap(ordered[-window:])
        deviation_pct = pct_change(current_vwap, latest.trade_price)
        buy_threshold = Decimal("0") - self.settings.strategy_pullback_sell_pct
        sell_threshold = self.settings.take_profit_pct
        if deviation_pct <= buy_threshold:
            return Signal("buy", latest.market, latest.trade_price, f"VWAP 하단 회귀 후보: VWAP 대비 {deviation_pct:.2f}%", Decimal("0.75"))
        if deviation_pct >= sell_threshold:
            return Signal("sell", latest.market, latest.trade_price, f"VWAP 상단 과열 후보: VWAP 대비 {deviation_pct:.2f}%")
        return Signal("hold", latest.market, latest.trade_price, f"VWAP 대기: VWAP 대비 {deviation_pct:.2f}%", Decimal("0.5"))


class DonchianChannelStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        window = max(self.settings.long_window, 20)
        if len(ordered) < window + 1:
            return Signal("hold", latest.market, latest.trade_price, f"Donchian 계산에는 최소 {window + 1}개의 캔들이 필요합니다")

        previous = ordered[-window - 1 : -1]
        channel_high = max(candle.high_price for candle in previous)
        channel_low = min(candle.low_price for candle in previous)
        if latest.trade_price > channel_high:
            return Signal("buy", latest.market, latest.trade_price, f"Donchian 상단 돌파: 상단 {channel_high:.2f}")
        if latest.trade_price < channel_low:
            return Signal("sell", latest.market, latest.trade_price, f"Donchian 하단 이탈: 하단 {channel_low:.2f}")
        channel_position = (latest.trade_price - channel_low) / (channel_high - channel_low) * Decimal("100") if channel_high != channel_low else Decimal("50")
        return Signal("hold", latest.market, latest.trade_price, f"Donchian 채널 내부: 위치 {channel_position:.2f}%", Decimal("0.5"))


class MaeuknamCardsStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "매억남 카드 계산에 필요한 캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        signal = evaluate_maeuknam_techniques(ordered, allowed_directions=("LONG",))
        if signal is None:
            return Signal(
                "hold",
                latest.market,
                latest.trade_price,
                "매억남 카드 계산에는 전략 카드 파일과 최소 30개 캔들이 필요합니다",
                Decimal("0.35"),
            )

        blocks = ", ".join(signal.hard_blocks) if signal.hard_blocks else "없음"
        reason = (
            f"매억남 카드 {signal.technique_name}: 점수 {signal.score:.3f}/{signal.entry_threshold:.2f}, "
            f"손절 {signal.stop_price:.8g}, 1차목표 {signal.target1_price:.8g}, "
            f"2차목표 {signal.target2_price:.8g}, RR {signal.reward_risk:.2f}, 차단 {blocks}"
        )
        if signal.entry_allowed:
            strength = clamp_decimal(
                Decimal("0.85") + (signal.score - signal.entry_threshold) * Decimal("2"),
                Decimal("0.85"),
                Decimal("2"),
            )
            return Signal("buy", latest.market, latest.trade_price, f"{reason} · 진입 허용", strength)
        if signal.score >= signal.watch_threshold:
            return Signal("hold", latest.market, latest.trade_price, f"{reason} · 감시만", Decimal("0.55"))
        return Signal("hold", latest.market, latest.trade_price, f"{reason} · 기준 미달", Decimal("0.35"))


class AlexMethodStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        if not candles:
            return Signal("hold", self.settings.market, Decimal("0"), "알렉스 매매기법 계산에 필요한 캔들 데이터가 없습니다")

        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        latest = ordered[-1]
        # Spot trading can only open long exposure, so the spot strategy exports the LONG gate.
        # Binance futures paper mode evaluates both LONG and SHORT in binance_paper.py.
        signal = evaluate_alex_techniques(ordered, allowed_directions=("LONG",))
        if signal is None:
            return Signal(
                "hold",
                latest.market,
                latest.trade_price,
                "알렉스 매매기법은 최소 30개 캔들과 0.5/유동성/4카운트 구조가 필요합니다.",
                Decimal("0.35"),
            )

        blocks = ", ".join(signal.hard_blocks) if signal.hard_blocks else "없음"
        reason = (
            f"알렉스 {signal.technique_name}: 점수 {signal.score:.3f}/{signal.entry_threshold:.2f}, "
            f"손절 {signal.stop_price:.8g}, 1차목표 {signal.target1_price:.8g}, "
            f"2차목표 {signal.target2_price:.8g}, RR {signal.reward_risk:.2f}, 차단 {blocks}"
        )
        if signal.entry_allowed:
            strength = clamp_decimal(
                Decimal("0.85") + (signal.score - signal.entry_threshold) * Decimal("2"),
                Decimal("0.85"),
                Decimal("2"),
            )
            return Signal("buy", latest.market, latest.trade_price, f"{reason} · 진입 허용", strength)
        if signal.score >= signal.watch_threshold:
            return Signal("hold", latest.market, latest.trade_price, f"{reason} · 관찰", Decimal("0.55"))
        return Signal("hold", latest.market, latest.trade_price, f"{reason} · 기준 미달", Decimal("0.35"))


class AdaptiveLearningStrategy:
    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    def evaluate(self, candles: list[Candle]) -> Signal:
        market = candles[0].market if candles else self.settings.market
        selected = self._recommendation(market)
        if selected is None:
            fallback = GuardedMomentumStrategy(self.settings).evaluate(candles)
            return Signal(
                fallback.action,
                fallback.market,
                fallback.reference_price,
                f"학습 모델 없음: 보수적 모멘텀으로 대체 · {fallback.reason}",
                fallback.strength,
            )

        strategy_name = str(selected.get("bestStrategy") or "")
        label = str(selected.get("label") or STRATEGY_CATALOG.get(strategy_name, {}).get("label") or strategy_name)
        score = str(selected.get("score") or "-")
        strategy = make_strategy_by_name(self.settings, strategy_name)
        signal = strategy.evaluate(candles)
        return Signal(
            signal.action,
            signal.market,
            signal.reference_price,
            f"학습형 선택: {label} · 점수 {score} · {signal.reason}",
            signal.strength,
        )

    def _recommendation(self, market: str) -> dict[str, object] | None:
        path = self.settings.state_file.parent / "learning_model.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        markets = payload.get("markets") if isinstance(payload, dict) else None
        if not isinstance(markets, dict):
            return None
        recommendation = markets.get(market)
        if not isinstance(recommendation, dict):
            return None
        strategy_name = str(recommendation.get("bestStrategy") or "")
        if strategy_name not in SUPPORTED_STRATEGY_NAMES or strategy_name == "adaptive_learning":
            return None
        return recommendation


StrategyType = (
    AdaptiveLearningStrategy
    | SmaCrossStrategy
    | GuardedMomentumStrategy
    | ProbabilityEdgeStrategy
    | BreakoutStrategy
    | MeanReversionStrategy
    | RsiReversalStrategy
    | MacdCrossStrategy
    | StatisticalFilterStrategy
    | BollingerBandStrategy
    | StochasticStrategy
    | IchimokuTrendStrategy
    | VwapReversionStrategy
    | DonchianChannelStrategy
    | MaeuknamCardsStrategy
    | AlexMethodStrategy
)


def make_strategy(settings: TradingSettings) -> StrategyType:
    return make_strategy_by_name(settings, settings.strategy_name)


def make_strategy_by_name(settings: TradingSettings, strategy_name: str) -> StrategyType:
    if strategy_name == "adaptive_learning":
        return AdaptiveLearningStrategy(settings)
    if strategy_name == "sma_cross":
        return SmaCrossStrategy(settings)
    if strategy_name == "probability_edge":
        return ProbabilityEdgeStrategy(settings)
    if strategy_name == "maeuknam_cards":
        return MaeuknamCardsStrategy(settings)
    if strategy_name == "alex_method":
        return AlexMethodStrategy(settings)
    if strategy_name == "breakout":
        return BreakoutStrategy(settings)
    if strategy_name == "mean_reversion":
        return MeanReversionStrategy(settings)
    if strategy_name == "rsi_reversal":
        return RsiReversalStrategy(settings)
    if strategy_name == "macd_cross":
        return MacdCrossStrategy(settings)
    if strategy_name == "statistical_filter":
        return StatisticalFilterStrategy(settings)
    if strategy_name == "bollinger_band":
        return BollingerBandStrategy(settings)
    if strategy_name == "stochastic":
        return StochasticStrategy(settings)
    if strategy_name == "ichimoku_trend":
        return IchimokuTrendStrategy(settings)
    if strategy_name == "vwap_reversion":
        return VwapReversionStrategy(settings)
    if strategy_name == "donchian_channel":
        return DonchianChannelStrategy(settings)
    return GuardedMomentumStrategy(settings)
