from __future__ import annotations

from decimal import Decimal
from typing import Any
import argparse
import json
import time

from .backtest import run_backtest
from .broker import PaperBroker, UpbitLiveBroker
from .config import TradingSettings, load_settings
from .live import is_live_trading_armed
from .models import Candle, decimal_to_str
from .risk import RiskManager
from .state import JsonStateStore
from .strategy import make_strategy
from .upbit_client import UpbitClient


ACTION_LABELS = {
    "buy": "매수",
    "sell": "매도",
    "hold": "관망",
}

MODE_LABELS = {
    "paper": "페이퍼",
    "live": "실거래",
}


def make_client(settings: TradingSettings) -> UpbitClient:
    return UpbitClient(
        base_url=settings.base_url,
        access_key=settings.access_key,
        secret_key=settings.secret_key,
    )


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _intent_payload(intent: Any) -> dict[str, Any] | None:
    if intent is None:
        return None
    return {
        "마켓": intent.market,
        "주문방향": "매수" if intent.side == "bid" else "매도",
        "주문유형": intent.ord_type,
        "가격또는주문총액": decimal_to_str(intent.price) if intent.price is not None else None,
        "수량": decimal_to_str(intent.volume) if intent.volume is not None else None,
        "사유": intent.reason,
        "업비트요청본문": intent.to_upbit_body(),
    }


def _paper_state_payload(state: Any, current_price: Decimal) -> dict[str, Any]:
    return {
        "현금KRW": decimal_to_str(state.cash_krw),
        "보유수량": decimal_to_str(state.position_volume),
        "평균단가": decimal_to_str(state.avg_entry_price),
        "평가금액KRW": decimal_to_str(state.position_value(current_price)),
        "총자산KRW": decimal_to_str(state.equity(current_price)),
        "실현손익KRW": decimal_to_str(state.realized_pnl_krw),
        "누적수수료KRW": decimal_to_str(state.fees_paid_krw),
        "주문횟수": state.order_count,
        "마지막주문시각": state.last_order_at,
    }


def _ticker_payload(ticker: dict[str, Any]) -> dict[str, Any]:
    return {
        "마켓": ticker.get("market"),
        "현재가": ticker.get("trade_price"),
        "전일종가": ticker.get("prev_closing_price"),
        "변화": ticker.get("change"),
        "변화금액": ticker.get("change_price"),
        "변화율": ticker.get("change_rate"),
        "24시간거래대금": ticker.get("acc_trade_price_24h"),
        "타임스탬프": ticker.get("timestamp"),
        "원본": ticker,
    }


def fetch_candles(client: UpbitClient, settings: TradingSettings, market: str | None = None) -> list[Candle]:
    raw_candles = client.get_minute_candles(
        market=market or settings.market,
        unit=settings.candle_unit,
        count=settings.candle_count,
    )
    return [Candle.from_upbit(item) for item in raw_candles]


def run_once(settings: TradingSettings, live: bool = False) -> dict[str, Any]:
    client = make_client(settings)
    candles = fetch_candles(client, settings)
    latest_price = candles[0].trade_price if candles else Decimal("0")

    store = JsonStateStore(settings.state_file)
    state = store.load(settings.paper_cash_krw)
    signal = make_strategy(settings).evaluate(candles)
    decision = RiskManager(settings).evaluate(signal, state, latest_price)

    result_payload: dict[str, Any] = {
        "마켓": settings.market,
        "현재가": decimal_to_str(latest_price),
        "신호": {
            "동작": ACTION_LABELS[signal.action],
            "원본동작": signal.action,
            "사유": signal.reason,
            "기준가격": decimal_to_str(signal.reference_price),
        },
        "리스크검사": {
            "승인": decision.approved,
            "사유": decision.reason,
            "주문계획": _intent_payload(decision.intent),
        },
        "주문결과": None,
        "페이퍼상태": _paper_state_payload(state, latest_price),
    }

    if decision.approved and decision.intent is not None:
        if live:
            result = UpbitLiveBroker(client, settings).execute(decision.intent, latest_price)
        else:
            result = PaperBroker(state, settings.fee_rate).execute(decision.intent, latest_price)
            store.save(state)

        result_payload["주문결과"] = {
            "성공": result.ok,
            "모드": MODE_LABELS[result.mode],
            "원본모드": result.mode,
            "메시지": result.message,
            "원본": result.raw,
        }
        result_payload["페이퍼상태"] = _paper_state_payload(state, latest_price)

    return result_payload


def cmd_price(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    client = make_client(settings)
    ticker = client.get_ticker(args.market)
    _print_json(_ticker_payload(ticker[0]) if ticker else {})
    return 0


def cmd_accounts(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    client = make_client(settings)
    _print_json({"계좌": client.get_accounts()})
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    if args.live and not is_live_trading_armed(settings):
        raise SystemExit("실거래 거부: LIVE_TRADING_ENABLED=true 및 LIVE_ORDER_CONFIRMATION='실거래 손실 동의'가 필요합니다")
    _print_json(run_once(settings, live=args.live))
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    if args.live and not is_live_trading_armed(settings):
        raise SystemExit("실거래 거부: LIVE_TRADING_ENABLED=true 및 LIVE_ORDER_CONFIRMATION='실거래 손실 동의'가 필요합니다")

    while True:
        _print_json(run_once(settings, live=args.live))
        time.sleep(settings.loop_sleep_seconds)


def cmd_backtest(args: argparse.Namespace) -> int:
    settings = load_settings(args.env_file)
    if args.market:
        settings = TradingSettings(**{**settings.__dict__, "market": args.market, "markets": (args.market,)})
    if args.count:
        settings = TradingSettings(**{**settings.__dict__, "candle_count": args.count})
    settings.validate()

    client = make_client(settings)
    candles = fetch_candles(client, settings)
    report = run_backtest(candles, settings)
    _print_json(
        {
            "마켓": settings.market,
            "주문횟수": report.order_count,
            "시작자산KRW": decimal_to_str(report.start_equity_krw),
            "최종자산KRW": decimal_to_str(report.final_equity_krw),
            "총수익률퍼센트": decimal_to_str(report.total_return_pct),
            "실현손익KRW": decimal_to_str(report.realized_pnl_krw),
            "누적수수료KRW": decimal_to_str(report.fees_paid_krw),
            "마지막가격": decimal_to_str(report.last_price),
            "최대낙폭퍼센트": decimal_to_str(report.max_drawdown_pct),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autotrading", description="업비트 자동매매 CLI")
    parser.add_argument("--env-file", default=None, help=".env 파일 경로")
    subparsers = parser.add_subparsers(dest="command", required=True)

    price = subparsers.add_parser("price", aliases=["현재가"], help="현재가 조회")
    price.add_argument("--market", default="KRW-BTC")
    price.set_defaults(func=cmd_price)

    accounts = subparsers.add_parser("accounts", aliases=["계좌"], help="비공개 계좌 잔고 조회")
    accounts.set_defaults(func=cmd_accounts)

    run_once_parser = subparsers.add_parser("run-once", aliases=["한번실행"], help="전략 판단을 1회 실행")
    run_once_parser.add_argument("--live", action="store_true", help="실거래 주문 제출")
    run_once_parser.set_defaults(func=cmd_run_once)

    loop = subparsers.add_parser("loop", aliases=["반복실행"], help="전략 판단을 반복 실행")
    loop.add_argument("--live", action="store_true", help="실거래 주문 제출")
    loop.set_defaults(func=cmd_loop)

    backtest = subparsers.add_parser("backtest", aliases=["백테스트"], help="최근 캔들로 간단 백테스트")
    backtest.add_argument("--market", default=None)
    backtest.add_argument("--count", type=int, default=None)
    backtest.set_defaults(func=cmd_backtest)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
