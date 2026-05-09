from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
import asyncio
import base64
import binascii
import json
import math
import os
import secrets
import threading
import time

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ai_pm import (
    ai_pm_chat_payload,
    ai_pm_status_payload,
    build_ai_pm_snapshot,
    load_ai_pm_chat,
    request_ai_pm_chat,
    request_ai_pm_report,
    save_ai_pm_chat,
)
from .alerts import alerts_payload, evaluate_alerts
from .allocation import build_dynamic_allocation_plan, execute_allocation_plan
from .autorun import AutoRunController
from .broker import PortfolioPaperBroker, UpbitLiveBroker
from .backtest import run_backtest
from .binance_client import BinanceFuturesClient, BinanceSpotClient
from .binance_paper import (
    ALEX_STRATEGY_SIDE,
    DEFAULT_LEVERAGE,
    DEFAULT_PAPER_SIDE,
    DEFAULT_WALLET_BALANCE_USDT,
    MAX_OPEN_POSITIONS,
    MIN_ENTRY_SCORE,
    MAEUKNAM_STRATEGY_SIDE,
    STRATEGY_SIDE,
    futures_paper_leverage,
    futures_paper_state_path,
    futures_paper_status,
    manual_futures_paper_trade,
    reset_futures_paper_state,
    run_futures_paper_cycle,
    scan_futures_paper_candidates,
)
from .cli import fetch_candles, make_client, run_once
from .config import TradingSettings, load_settings
from .database import SqliteStore
from .intel import INTEL_INTERVAL_SECONDS, collect_market_intel, load_market_intel
from .investment_agency import build_investment_agency_report
from .live import (
    is_confirmation_accepted,
    is_live_trading_armed,
    is_web_live_trading_armed,
    live_portfolio_state,
    live_runtime_payload,
    order_chance_payload,
    summarize_accounts,
)
from .learning import krw_market_codes, load_learning_model, run_historical_learning, save_learning_model
from .models import Candle, OrderIntent, OrderResult, Signal, decimal_to_str
from .ops import JsonlEventLog
from .orderbook import analyze_orderbook, fetch_orderbook_payload
from .realtime import UpbitRealtimeService
from .realtime_engine import (
    build_realtime_decision_plan,
    execute_realtime_plan,
    realtime_goal_pace_pressure,
    realtime_market_universe,
)
from .reverse_signal import reverse_signal_report
from .risk import PortfolioRiskManager
from .state import JsonPortfolioStateStore, PortfolioPosition, PortfolioState
from .strategy import is_supported_strategy, make_strategy, strategy_catalog


STATIC_DIR = Path(__file__).with_name("web_static")
AUTH_REALM = "Upbit Autotrading Dashboard"
AUTH_EXEMPT_PATHS = {"/api/health"}
MARKET_META_TTL_SECONDS = 300
MINUTE_CHART_FRAMES = {"1", "3", "5", "10", "15", "30", "60", "240"}
PERIOD_CHART_FRAMES = {"day", "week", "month", "year"}
CHART_PAGE_LIMIT = 200
CHART_MAX_CANDLES = 5000
CHART_PAGE_PAUSE_SECONDS = 0.04
CHART_DEFAULT_COUNTS = {
    "1": 720,
    "3": 960,
    "5": 1200,
    "10": 1440,
    "15": 1600,
    "30": 2000,
    "60": 2200,
    "240": 2500,
    "day": 3650,
    "week": 780,
    "month": 240,
    "year": 40,
}
CHART_FRAME_LABELS = {
    "1": "1분",
    "3": "3분",
    "5": "5분",
    "10": "10분",
    "15": "15분",
    "30": "30분",
    "60": "1시간",
    "240": "4시간",
    "day": "일",
    "week": "주",
    "month": "월",
    "year": "년",
}
OPS_POSITIVE_RATIO_RECOVERY_TARGET = Decimal("0.25")
OPS_STOP_WARNING_DISTANCE_PCT = Decimal("2")
OPS_STOP_CRITICAL_DISTANCE_PCT = Decimal("1")
OPS_STEEM_STOP_WARNING_DISTANCE_PCT = Decimal("3")
_market_meta_cache: dict[str, Any] = {"expires_at": 0.0, "markets": (), "meta": {}}

ACTION_LABELS = {
    "buy": "매수",
    "sell": "매도",
    "hold": "관망",
}
EXCHANGE_MODES = {
    "upbit": {
        "label": "업비트 현물",
        "description": "KRW 전체 코인 분석과 업비트 페이퍼/실거래 보호장치를 사용합니다.",
        "orderBoundary": "업비트 실거래는 별도 이중 잠금이 켜진 경우에만 가능합니다.",
    },
    "binance_spot": {
        "label": "바이낸스 현물",
        "description": "바이낸스 현물 시세와 연결 상태를 확인합니다. 자동 주문 엔진은 아직 잠금 상태입니다.",
        "orderBoundary": "현재 바이낸스 현물은 조회/감시 전용입니다.",
    },
    "binance_futures_paper": {
        "label": "바이낸스 선물 모의",
        "description": "바이낸스 USD-M 선물 공개 시세로 로컬 선물 모의 자산을 관리합니다.",
        "orderBoundary": "실제 바이낸스 주문 API는 호출하지 않습니다.",
    },
}
DEFAULT_EXCHANGE_MODE = "upbit"


class RunRequest(BaseModel):
    live: bool = False
    market: str | None = None
    all_markets: bool = False


class LiveRequest(BaseModel):
    market: str | None = None


class LiveExecuteRequest(LiveRequest):
    confirmation: str = ""


class LiveRehearsalRequest(LiveRequest):
    confirmation: str = ""


class StrategySelectRequest(BaseModel):
    strategy: str | None = None
    auto: bool | None = None


class LearnRequest(BaseModel):
    count: int | None = None
    scope: str = "watchlist"
    max_markets: int | None = None


class AllocationRequest(BaseModel):
    execute: bool = False


class AiPmChatRequest(BaseModel):
    message: str


class RecommendedMarketsRequest(BaseModel):
    markets: list[str] = []
    excludedMarkets: list[str] = []
    recommendOnly: bool | None = None


class RecommendedMarketToggleRequest(BaseModel):
    market: str
    preference: str = "recommended"
    checked: bool | None = None
    recommended: bool | None = None


class RecommendedModeRequest(BaseModel):
    recommendOnly: bool = False


class ExchangeModeRequest(BaseModel):
    mode: str


class BinanceFuturesPaperResetRequest(BaseModel):
    balanceUsdt: str | None = None


class BinanceFuturesManualTradeRequest(BaseModel):
    action: str
    amountUsdt: str | None = None
    marginPercent: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Autotrading Dashboard", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def require_dashboard_auth(request: Request, call_next: Any) -> Response:
        settings = load_web_settings()
        if not settings.dashboard_auth_enabled or is_auth_exempt_path(request.url.path):
            return await call_next(request)
        if is_basic_auth_valid(request.headers.get("authorization", ""), settings):
            return await call_next(request)
        return auth_required_response()

    @app.websocket("/ws/binance/futures/ticker/{symbol}")
    async def binance_futures_ticker_websocket(websocket: WebSocket, symbol: str) -> None:
        await websocket.accept()
        clean_symbol = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum())
        if not clean_symbol.endswith("USDT"):
            await websocket.send_json(
                {
                    "type": "error",
                    "symbol": clean_symbol,
                    "message": "Only Binance USD-M USDT futures symbols are supported.",
                }
            )
            await websocket.close(code=1008)
            return

        try:
            import websockets
        except ImportError:
            await websocket.send_json(
                {
                    "type": "error",
                    "symbol": clean_symbol,
                    "message": "The websockets package is not installed.",
                }
            )
            await websocket.close(code=1011)
            return

        upstream_url = f"wss://fstream.binance.com/ws/{clean_symbol.lower()}@trade"
        backoff_seconds = 0.25
        while True:
            try:
                async with websockets.connect(
                    upstream_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=2,
                    max_queue=64,
                ) as upstream:
                    backoff_seconds = 0.25
                    await websocket.send_json(
                        {
                            "type": "connected",
                            "source": "binance_futures_ws_trade",
                            "symbol": clean_symbol,
                            "receivedAt": int(time.time() * 1000),
                        }
                    )
                    async for raw_message in upstream:
                        tick = json.loads(raw_message)
                        event_time = int(tick.get("E") or 0)
                        trade_time = int(tick.get("T") or event_time or 0)
                        received_at = int(time.time() * 1000)
                        latency_ms = received_at - event_time if event_time else None
                        if latency_ms is not None and latency_ms < 0:
                            latency_ms = 0
                        await websocket.send_json(
                            {
                                "type": "trade",
                                "source": "binance_futures_ws_trade",
                                "symbol": clean_symbol,
                                "price": str(tick.get("p") or "0"),
                                "quantity": str(tick.get("q") or "0"),
                                "eventTime": event_time,
                                "tradeTime": trade_time,
                                "receivedAt": received_at,
                                "latencyMs": latency_ms,
                            }
                        )
            except WebSocketDisconnect:
                return
            except Exception as exc:
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "source": "binance_futures_ws_trade",
                            "symbol": clean_symbol,
                            "message": str(exc),
                            "receivedAt": int(time.time() * 1000),
                        }
                    )
                except Exception:
                    return
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(5.0, backoff_seconds * 2)

    def run_realtime_decision_guarded(
        settings: TradingSettings,
        execute_orders: bool,
        source: str,
        *,
        wait: bool = True,
    ) -> dict[str, Any] | None:
        lock = getattr(app.state, "realtime_decision_lock", None)
        if lock is None:
            return run_realtime_decision(settings, runtime_snapshot(app), execute_orders=execute_orders, source=source)
        acquired = lock.acquire(blocking=wait)
        if not acquired:
            return None
        try:
            return run_realtime_decision(settings, runtime_snapshot(app), execute_orders=execute_orders, source=source)
        finally:
            lock.release()

    def realtime_decision_monitor_scan() -> list[dict[str, Any]]:
        settings = selected_web_settings(app)
        if not settings.realtime_decision_enabled:
            return [{"market": "REALTIME", "ok": True, "message": "실시간 분석 기능이 꺼져 있습니다"}]
        autorun = getattr(app.state, "autorun_controller", None)
        if autorun is not None and autorun.snapshot().get("running"):
            return [{"market": "REALTIME", "ok": True, "message": "자동 실행 루프가 실시간 분석을 담당 중입니다"}]
        if selected_exchange_mode(app, settings) == "binance_futures_paper":
            payload = binance_futures_paper_scan(settings)
            if payload is None:
                return [{"market": "BINANCE-FUTURES-PAPER", "ok": False, "message": "Binance futures paper symbols are not configured"}]
            return [payload]
        payload = run_realtime_decision_guarded(settings, execute_orders=False, source="monitor", wait=False)
        if payload is None:
            return [{"market": "REALTIME", "ok": True, "message": "이전 실시간 분석이 아직 진행 중입니다"}]
        plan = payload.get("plan", {})
        return [
            {
                "market": "REALTIME",
                "ok": True,
                "message": payload.get("message", "실시간 전체 코인 분석 완료"),
                "universeCount": plan.get("universeCount", 0),
                "evaluatedCount": plan.get("evaluatedCount", 0),
            }
        ]

    def ai_pm_monitor_scan() -> list[dict[str, Any]]:
        settings = selected_web_settings(app)
        payload = run_ai_pm_analysis(settings, runtime_snapshot(app), source="monitor")
        return [
            {
                "market": "AI-PM",
                "ok": bool(payload.get("ok")),
                "message": payload.get("headline") or payload.get("narrative") or "AI PM 평가 완료",
            }
        ]

    def market_intel_scan() -> list[dict[str, Any]]:
        settings = selected_web_settings(app)
        payload = run_market_intel_collection(settings, runtime_snapshot(app), source="monitor")
        return [
            {
                "market": "INTEL",
                "ok": bool(payload.get("ok")),
                "message": payload.get("summary") or "시장정보 수집 완료",
            }
        ]

    def binance_futures_paper_scan(settings: TradingSettings) -> dict[str, Any] | None:
        if not settings.binance_futures_symbols:
            return None
        try:
            client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
            payload = run_futures_paper_cycle(settings, client)
            app.state.binance_futures_paper_runtime = payload
            record_futures_paper_snapshot(settings, payload, source="autorun")
        except Exception as exc:
            return {"market": "BINANCE-FUTURES-PAPER", "ok": False, "message": f"Binance futures paper failed: {exc}"}
        actions = payload.get("actions", [])
        first = actions[0] if actions else {}
        action_text = f" {first.get('type')} {first.get('symbol')} {first.get('side', '')}".strip() if first else ""
        return {
            "market": "BINANCE-FUTURES-PAPER",
            "ok": True,
            "message": f"{payload.get('message', 'Binance futures paper cycle complete')} {action_text}".strip(),
            "equityUsdt": payload.get("equityUsdt"),
            "openPositions": payload.get("openPositions"),
            "universeCount": payload.get("universeCount"),
            "evaluatedCount": payload.get("evaluatedCount"),
            "deepAnalysisCount": payload.get("deepAnalysisCount"),
        }

    def binance_spot_scan(settings: TradingSettings) -> dict[str, Any]:
        payload = binance_spot_payload(settings)
        if payload.get("publicOk"):
            return {
                "market": "BINANCE-SPOT",
                "ok": True,
                "message": f"Binance Spot {len(payload.get('prices', []))}개 가격 확인 · 현물 자동주문은 잠금 상태입니다",
            }
        return {
            "market": "BINANCE-SPOT",
            "ok": False,
            "message": payload.get("error") or "Binance Spot 연결 대기",
        }

    def auto_run_scan() -> list[dict[str, Any]]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            return [{"market": "ALL", "ok": False, "message": "Emergency stop is active; autorun skipped."}]
        exchange_mode = selected_exchange_mode(app, settings)
        if exchange_mode == "binance_spot":
            return [binance_spot_scan(settings)]
        if exchange_mode == "binance_futures_paper":
            futures_paper_result = binance_futures_paper_scan(settings)
            return [futures_paper_result] if futures_paper_result is not None else [
                {"market": "BINANCE-FUTURES-PAPER", "ok": False, "message": "Binance futures paper mode is not configured."}
            ]

        results: list[dict[str, Any]] = []
        realtime_checked = False
        if settings.realtime_decision_enabled:
            realtime_checked = True
            payload = run_realtime_decision_guarded(settings, execute_orders=True, source="autorun")
            if payload is None:
                return [{"market": "REALTIME", "ok": True, "message": "이전 실시간 분석이 아직 진행 중입니다"}]
            orders = payload.get("orders", [])
            if orders:
                return orders
            results.append({"market": "REALTIME", "ok": True, "message": payload.get("message", "실시간 상황 판단 완료")})
        if settings.dynamic_allocation_enabled:
            if is_allocation_due(settings):
                payload = run_dynamic_allocation(settings, execute_orders=True, source="autorun")
                orders = payload.get("orders", [])
                if orders:
                    results.extend(orders)
                else:
                    results.append({"market": "ALLOCATION", "ok": True, "message": payload.get("message", "동적 배분 실행 완료")})
        if settings.realtime_decision_enabled and not realtime_checked:
            payload = run_realtime_decision_guarded(settings, execute_orders=True, source="autorun")
            if payload is None:
                return [{"market": "REALTIME", "ok": True, "message": "실시간 분석이 이미 진행 중입니다"}]
            orders = payload.get("orders", [])
            if orders:
                results.extend(orders)
            else:
                results.append({"market": "REALTIME", "ok": True, "message": payload.get("message", "실시간 상황 판단 완료")})
        if results:
            return results
        if settings.dynamic_allocation_enabled:
            status = allocation_status_payload(settings)
            allocation_wait = {"market": "ALLOCATION", "ok": True, "message": status.get("nextRunMessage", "Waiting for next allocation run")}
            return [allocation_wait]
        return run_paper_scan(settings)

    @app.on_event("startup")
    async def startup() -> None:
        settings = load_web_settings()
        selection = load_strategy_selection(settings)
        app.state.strategy_name = selection["strategyName"]
        app.state.strategy_auto_select = selection["autoSelect"]
        app.state.exchange_mode = load_exchange_mode(settings)
        app.state.binance_futures_paper_runtime = {}
        app.state.learning_lock = threading.Lock()
        app.state.realtime_decision_lock = threading.Lock()
        app.state.learning_job = default_learning_job()
        SqliteStore(settings.database_file).initialize()
        state = JsonPortfolioStateStore(settings.state_file).load(settings.paper_cash_krw)
        realtime_markets = dashboard_realtime_markets(settings, state)
        realtime = UpbitRealtimeService(realtime_markets)
        autorun = AutoRunController(auto_run_scan, autorun_interval_seconds(settings))
        realtime_decision_monitor = AutoRunController(realtime_decision_monitor_scan, settings.realtime_decision_interval_seconds)
        ai_pm_monitor = AutoRunController(ai_pm_monitor_scan, settings.ai_pm_interval_seconds)
        market_intel_monitor = AutoRunController(market_intel_scan, INTEL_INTERVAL_SECONDS)
        app.state.realtime_service = realtime
        app.state.autorun_controller = autorun
        app.state.realtime_decision_monitor = realtime_decision_monitor
        app.state.ai_pm_monitor = ai_pm_monitor
        app.state.market_intel_monitor = market_intel_monitor
        await realtime.start()
        if settings.realtime_decision_enabled:
            await realtime_decision_monitor.start()
        if settings.ai_pm_enabled and settings.ai_pm_api_key:
            await ai_pm_monitor.start()
        await market_intel_monitor.start()
        if settings.auto_run_enabled and not is_emergency_stopped(settings):
            await autorun.start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        realtime = getattr(app.state, "realtime_service", None)
        autorun = getattr(app.state, "autorun_controller", None)
        realtime_decision_monitor = getattr(app.state, "realtime_decision_monitor", None)
        ai_pm_monitor = getattr(app.state, "ai_pm_monitor", None)
        market_intel_monitor = getattr(app.state, "market_intel_monitor", None)
        if market_intel_monitor is not None:
            await market_intel_monitor.stop()
        if ai_pm_monitor is not None:
            await ai_pm_monitor.stop()
        if realtime_decision_monitor is not None:
            await realtime_decision_monitor.stop()
        if autorun is not None:
            await autorun.stop()
        if realtime is not None:
            await realtime.stop()

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return build_status(settings, runtime_snapshot(app))

    @app.get("/api/strategies")
    def strategies() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return {
            "active": settings.strategy_name,
            "auto": selected_strategy_auto_select(app),
            "strategies": strategy_catalog(settings.strategy_name),
        }

    @app.post("/api/strategies/select")
    def select_strategy(request: StrategySelectRequest) -> dict[str, Any]:
        settings = set_selected_strategy(app, request.strategy, request.auto)
        return {
            "active": settings.strategy_name,
            "auto": selected_strategy_auto_select(app),
            "strategies": strategy_catalog(settings.strategy_name),
            "status": build_status(settings, runtime_snapshot(app)),
        }

    @app.post("/api/run-once")
    def run_once_endpoint(request: RunRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="긴급정지 상태입니다. 설정에서 해제한 뒤 실행하세요.")
        if request.live and not is_live_trading_armed(settings):
            raise HTTPException(status_code=403, detail="실거래 이중 잠금이 해제되지 않았습니다.")

        if request.live:
            if request.all_markets:
                raise HTTPException(status_code=400, detail="전종목 실거래는 아직 막아두었습니다. 먼저 페이퍼 전체 스캔으로 검증하세요.")
            market = request.market or settings.market
            result = run_once(settings_for_market(settings, market), live=True)
        elif request.all_markets:
            result = {"스캔결과": run_paper_scan(settings)}
        else:
            result = run_paper_market_once(settings, request.market or settings.market)
        return {
            "실행결과": result,
            "상태": build_status(settings, runtime_snapshot(app)),
        }

    @app.post("/api/scan-once")
    def scan_once() -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="긴급정지 상태입니다. 설정에서 해제한 뒤 실행하세요.")
        return {
            "스캔결과": run_paper_scan(settings),
            "상태": build_status(settings, runtime_snapshot(app)),
        }

    @app.get("/api/backtest")
    def backtest(count: int | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        return run_backtest_scan(settings, count or max(settings.candle_count, 120))

    @app.get("/api/simulations/latest")
    def latest_simulation() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return latest_range_simulation_payload(settings)

    @app.get("/api/simulations/playback")
    def simulation_playback() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return simulation_playback_payload(settings)

    @app.get("/api/reverse-signal-test")
    def reverse_signal_test() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return reverse_signal_report(settings).to_dict()

    @app.get("/api/learn")
    def learning_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return learning_payload(settings, app)

    @app.post("/api/learn")
    def learn(request: LearnRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        return start_learning_job(app, settings, request)

    @app.get("/api/realtime")
    def realtime_status() -> dict[str, Any]:
        return runtime_snapshot(app)["realtime"]

    @app.get("/api/autorun")
    def autorun_status() -> dict[str, Any]:
        return runtime_snapshot(app)["autorun"]

    @app.post("/api/live/check")
    def live_check(request: LiveRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        market = request.market or settings.market
        return live_check_payload(settings, market)

    @app.post("/api/live/preview")
    def live_preview(request: LiveRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        market = request.market or settings.market
        return build_live_preview(settings, market)

    @app.post("/api/live/execute")
    def live_execute(request: LiveExecuteRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="湲닿툒?뺤? ?곹깭?먯꽌???ㅺ굅??二쇰Ц???쒖텧?????놁뒿?덈떎")
        if not is_web_live_trading_armed(settings):
            raise HTTPException(
                status_code=403,
                detail="?ㅺ굅???좉툑???댁젣?섏? ?딆븯?듬땲?? LIVE_TRADING_ENABLED, WEB_LIVE_TRADING_ENABLED, LIVE_ORDER_CONFIRMATION???뺤씤?섏꽭??",
            )
        if not is_confirmation_accepted(request.confirmation):
            raise HTTPException(status_code=403, detail="?ㅺ굅???뺤씤 臾멸뎄媛? ?쇱튂?섏? ?딆뒿?덈떎")

        preview = build_live_preview(settings, request.market or settings.market)
        risk = preview.get("risk", {})
        intent_payload_data = risk.get("intent")
        if not risk.get("approved") or not intent_payload_data:
            raise HTTPException(status_code=409, detail=f"由ъ뒪??寃??щ? ?듦낵?섏? 紐삵뻽?듬땲?? {risk.get('reason')}")

        intent = intent_from_payload(intent_payload_data)
        latest_price = Decimal(str(preview.get("price", "0")))
        result = UpbitLiveBroker(make_client(settings), settings).execute(intent, latest_price)
        return {
            "liveResult": {
                "ok": result.ok,
                "mode": result.mode,
                "message": result.message,
                "raw": result.raw,
            },
            "preview": preview,
        }

    @app.post("/api/live/test-order")
    def live_test_order(request: LiveRehearsalRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if not settings.live_test_order_enabled:
            raise HTTPException(status_code=403, detail="LIVE_TEST_ORDER_ENABLED=true媛? ?꾨땲硫??뚯뒪??二쇰Ц 由ы뿀?ㅻ룄 李⑤떒?⑸땲??")
        if not is_confirmation_accepted(request.confirmation):
            raise HTTPException(status_code=403, detail="?ㅺ굅??由ы뿀???뺤씤 臾멸뎄媛? ?쇱튂?섏? ?딆뒿?덈떎")
        if not live_runtime_payload(settings)["armed"]:
            raise HTTPException(status_code=403, detail="二쇰Ц ?뚯뒪?몃룄 LIVE_TRADING_ENABLED?? ?뺤씤 臾멸뎄媛? ?꾩슂?⑸땲??")
        preview = build_live_preview(settings, request.market or settings.market)
        order_body = preview.get("orderBody")
        if not order_body:
            raise HTTPException(status_code=409, detail="?뚯뒪?명븷 二쇰Ц ?꾨낫媛? ?놁뒿?덈떎")
        try:
            raw = make_client(settings).test_order(order_body)
        except Exception as exc:
            log_event(settings, "live_test_order_failed", {"market": preview.get("market"), "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"?낅퉬??二쇰Ц ?앹꽦 ?뚯뒪???ㅽ뙣: {exc}") from exc
        payload = {"ok": True, "market": preview.get("market"), "raw": raw, "preview": preview}
        log_event(settings, "live_test_order_ok", {"market": preview.get("market"), "raw": raw})
        return payload

    @app.get("/api/events")
    def events(limit: int = 80) -> dict[str, Any]:
        settings = load_web_settings()
        safe_limit = min(max(limit, 1), 200)
        try:
            db_events = SqliteStore(settings.database_file).recent_events(safe_limit)
        except Exception as exc:
            return {
                "events": JsonlEventLog(settings.event_log_file).recent(safe_limit),
                "source": "jsonl",
                "warning": f"SQLite ?대깽??議고쉶 ?ㅽ뙣, JSONL 濡쒓렇濡???泥? {exc}",
            }
        if db_events:
            return {"events": db_events, "source": "sqlite"}
        return {"events": JsonlEventLog(settings.event_log_file).recent(safe_limit), "source": "jsonl"}

    @app.get("/api/db/status")
    def database_status() -> dict[str, Any]:
        settings = load_web_settings()
        return {"database": SqliteStore(settings.database_file).status()}

    @app.get("/api/alerts")
    def alerts() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return build_status(settings, runtime_snapshot(app))["alerts"]

    @app.get("/api/recommended-markets")
    def recommended_markets() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return recommendation_payload(settings)

    @app.post("/api/recommended-markets")
    def set_recommended_markets(request: RecommendedMarketsRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        preferences = save_market_preferences(
            settings,
            markets=request.markets,
            excluded_markets=request.excludedMarkets,
            recommend_only=request.recommendOnly,
        )
        log_event(
            settings,
            "recommended_markets_set",
            {
                "count": len(preferences["markets"]),
                "excludedCount": len(preferences["excludedMarkets"]),
                "recommendOnly": preferences["recommendOnly"],
                "markets": list(preferences["markets"]),
                "excludedMarkets": list(preferences["excludedMarkets"]),
            },
        )
        return recommendation_payload(settings, preferences)

    @app.post("/api/recommended-markets/toggle")
    def toggle_recommended_market(request: RecommendedMarketToggleRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        preferences = update_market_preference(settings, request)
        log_event(
            settings,
            "recommended_market_toggle",
            {
                "market": normalize_recommended_market(request.market),
                "preference": request.preference,
                "checked": preference_checked(request),
                "count": len(preferences["markets"]),
                "excludedCount": len(preferences["excludedMarkets"]),
                "recommendOnly": preferences["recommendOnly"],
            },
        )
        return recommendation_payload(settings, preferences)

    @app.post("/api/recommended-markets/mode")
    def set_recommended_mode(request: RecommendedModeRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        preferences = save_market_preferences(settings, recommend_only=request.recommendOnly)
        log_event(settings, "recommended_mode_set", {"recommendOnly": preferences["recommendOnly"]})
        return recommendation_payload(settings, preferences)

    @app.get("/api/allocation")
    def allocation_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return allocation_status_payload(settings)

    @app.post("/api/allocation/preview")
    def allocation_preview(_: AllocationRequest | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        return run_dynamic_allocation(settings, execute_orders=False, source="preview")

    @app.post("/api/allocation/run")
    def allocation_run(_: AllocationRequest | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="湲닿툒?뺤? ?곹깭?먯꽌???숈쟻 諛곕텇???ㅽ뻾?????놁뒿?덈떎")
        return run_dynamic_allocation(settings, execute_orders=True, source="manual")

    @app.get("/api/realtime-decision")
    def realtime_decision_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        if selected_exchange_mode(app, settings) == "binance_futures_paper":
            status_payload = safe_futures_paper_status(settings)
            return binance_futures_realtime_status_payload(
                settings,
                getattr(app.state, "binance_futures_paper_runtime", {}),
                status_payload,
                source="status",
            )
        return realtime_decision_status_payload(settings)

    @app.post("/api/realtime-decision/preview")
    def realtime_decision_preview(_: AllocationRequest | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if selected_exchange_mode(app, settings) == "binance_futures_paper":
            client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
            try:
                candidate_scan = scan_futures_paper_candidates(settings, client)
                candidates = candidate_scan.candidates
                status_payload = futures_paper_status(settings, client)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Binance futures paper analysis failed: {exc}") from exc
            cycle_payload = {
                "candidates": [candidate.to_dict() for candidate in candidates],
                "actions": [],
                "universeCount": candidate_scan.universe_count,
                "evaluatedCount": candidate_scan.evaluated_count,
                "universeSource": candidate_scan.universe_source,
                "tickerCount": candidate_scan.ticker_count,
                "deepAnalysisCount": candidate_scan.deep_analysis_count,
                "message": "諛붿씠?몄뒪 USD-M ?좊Ъ ?꾨낫瑜??덈줈 遺꾩꽍?덉뒿?덈떎",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            app.state.binance_futures_paper_runtime = cycle_payload
            return binance_futures_realtime_status_payload(settings, cycle_payload, status_payload, source="preview")["last"]
        payload = run_realtime_decision_guarded(settings, execute_orders=False, source="preview")
        if payload is None:
            raise HTTPException(status_code=409, detail="?댁쟾 ?ㅼ떆媛?遺꾩꽍???꾩쭅 吏꾪뻾 以묒엯?덈떎")
        return payload

    @app.post("/api/realtime-decision/run")
    def realtime_decision_run(_: AllocationRequest | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="湲닿툒?뺤? ?곹깭?먯꽌???ㅼ떆媛??먮떒 二쇰Ц???ㅽ뻾?????놁뒿?덈떎")
        if selected_exchange_mode(app, settings) == "binance_futures_paper":
            client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
            try:
                cycle_payload = run_futures_paper_cycle(settings, client)
                app.state.binance_futures_paper_runtime = cycle_payload
                record_futures_paper_snapshot(settings, cycle_payload, source="manual-realtime")
                status_payload = futures_paper_status(settings, client)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Binance futures paper cycle failed: {exc}") from exc
            return binance_futures_realtime_status_payload(settings, cycle_payload, status_payload, source="manual")["last"]
        payload = run_realtime_decision_guarded(settings, execute_orders=True, source="manual")
        if payload is None:
            raise HTTPException(status_code=409, detail="?댁쟾 ?ㅼ떆媛?遺꾩꽍???꾩쭅 吏꾪뻾 以묒엯?덈떎")
        return payload

    @app.get("/api/pm")
    def ai_pm_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return ai_pm_status_payload(settings)

    @app.post("/api/pm/analyze")
    def ai_pm_analyze() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return run_ai_pm_analysis(settings, runtime_snapshot(app), source="manual")

    @app.get("/api/pm/chat")
    def ai_pm_chat_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return ai_pm_chat_payload(settings)

    @app.post("/api/pm/chat")
    def ai_pm_chat(request: AiPmChatRequest) -> dict[str, Any]:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="AI PM?먭쾶 蹂대궪 硫붿떆吏?瑜??낅젰?섏꽭??")
        settings = selected_web_settings(app)
        return run_ai_pm_chat(settings, runtime_snapshot(app), message)

    @app.get("/api/pm/scheduler")
    def ai_pm_scheduler() -> dict[str, Any]:
        settings = selected_web_settings(app)
        status = build_status(settings, runtime_snapshot(app))
        return build_pm_scheduler(settings, status)

    @app.get("/api/intel")
    def market_intel_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        payload = load_market_intel(settings)
        monitor = getattr(app.state, "market_intel_monitor", None)
        payload["monitor"] = monitor.snapshot() if monitor is not None else {}
        return payload

    @app.post("/api/intel/refresh")
    def market_intel_refresh() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return run_market_intel_collection(settings, runtime_snapshot(app), source="manual")

    @app.get("/api/exchange-mode")
    def exchange_mode_status() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return exchange_mode_payload(settings, selected_exchange_mode(app, settings))

    @app.post("/api/exchange-mode")
    def set_exchange_mode(request: ExchangeModeRequest) -> dict[str, Any]:
        requested = str(request.mode or "").strip().lower().replace("-", "_")
        if requested not in EXCHANGE_MODES:
            raise HTTPException(status_code=400, detail=f"吏??먰븯吏? ?딅뒗 嫄곕옒??紐⑤뱶?낅땲?? {request.mode}")
        settings = selected_web_settings(app)
        app.state.exchange_mode = requested
        mode_payload = save_exchange_mode(settings, requested)
        log_event(
            settings,
            "exchange_mode_set",
            {"mode": requested, "label": mode_payload.get("label")},
        )
        return {
            "exchangeMode": exchange_mode_payload(settings, requested),
            "status": build_status(settings, runtime_snapshot(app)),
        }

    @app.get("/api/exchanges")
    def exchanges() -> dict[str, Any]:
        settings = selected_web_settings(app)
        return {
            "exchangeMode": exchange_mode_payload(settings, selected_exchange_mode(app, settings)),
            "upbit": {
                "configured": bool(settings.access_key and settings.secret_key),
                "markets": list(settings.markets),
                "publicRealtime": True,
                "liveArmed": live_runtime_payload(settings)["armed"],
            },
            "binance": binance_spot_payload(settings),
            "binanceFutures": binance_futures_payload(settings),
        }

    @app.get("/api/binance/futures")
    def binance_futures_check() -> dict[str, Any]:
        settings = load_web_settings()
        return binance_futures_payload(settings)

    @app.get("/api/binance/futures/paper")
    def binance_futures_paper_check() -> dict[str, Any]:
        settings = selected_web_settings(app)
        client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
        return futures_paper_status(settings, client)

    @app.post("/api/binance/futures/paper/run")
    def binance_futures_paper_run() -> dict[str, Any]:
        settings = selected_web_settings(app)
        client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
        try:
            payload = run_futures_paper_cycle(settings, client)
            app.state.binance_futures_paper_runtime = payload
            record_futures_paper_snapshot(settings, payload, source="manual")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Binance futures paper cycle failed: {exc}") from exc
        actions = payload.get("actions", [])
        first = actions[0] if actions else {}
        log_event(
            settings,
            "binance_futures_paper",
            {
                "message": payload.get("message"),
                "action": first.get("type"),
                "symbol": first.get("symbol"),
                "side": first.get("side"),
                "equityUsdt": payload.get("equityUsdt"),
                "openPositions": payload.get("openPositions"),
            },
        )
        return payload

    @app.post("/api/binance/futures/paper/manual")
    def binance_futures_paper_manual(request: BinanceFuturesManualTradeRequest) -> dict[str, Any]:
        settings = selected_web_settings(app)
        client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
        try:
            amount_usdt = Decimal(str(request.amountUsdt)) if request.amountUsdt not in (None, "") else None
            margin_percent = Decimal(str(request.marginPercent)) if request.marginPercent not in (None, "") else None
            if amount_usdt is not None and amount_usdt < 0:
                raise ValueError("Manual futures paper amount must be zero or greater.")
            if margin_percent is not None and margin_percent < 0:
                raise ValueError("Manual futures paper margin percent must be zero or greater.")
            payload = manual_futures_paper_trade(
                settings,
                client,
                request.action,
                margin_usdt=amount_usdt,
                margin_percent=margin_percent,
            )
            app.state.binance_futures_paper_runtime = payload
            save_exchange_mode(settings, "binance_futures_paper")
            app.state.exchange_mode = "binance_futures_paper"
            record_futures_paper_snapshot(settings, payload, source=f"manual-{payload.get('manualAction', 'trade')}".lower())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Binance futures paper manual trade failed: {exc}") from exc
        actions = payload.get("actions", [])
        first = actions[0] if actions else {}
        log_event(
            settings,
            "binance_futures_paper_manual",
            {
                "manualAction": payload.get("manualAction"),
                "action": first.get("type"),
                "symbol": first.get("symbol"),
                "side": first.get("side"),
                "equityUsdt": payload.get("equityUsdt"),
                "openPositions": payload.get("openPositions"),
            },
        )
        return {
            **payload,
            "status": build_status(settings, runtime_snapshot(app)),
        }

    @app.post("/api/binance/futures/paper/reset")
    def binance_futures_paper_reset(request: BinanceFuturesPaperResetRequest | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        raw_balance = request.balanceUsdt if request is not None and request.balanceUsdt else str(DEFAULT_WALLET_BALANCE_USDT)
        try:
            balance = Decimal(str(raw_balance))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"USDT ?쒖옉 湲덉븸???щ컮瑜댁? ?딆뒿?덈떎: {raw_balance}") from exc
        if balance <= 0:
            raise HTTPException(status_code=400, detail="USDT ?쒖옉 湲덉븸?? 0蹂대떎 而ㅼ빞 ?⑸땲??")
        reset_futures_paper_state(settings, balance)
        save_exchange_mode(settings, "binance_futures_paper")
        app.state.exchange_mode = "binance_futures_paper"
        app.state.binance_futures_paper_runtime = {}
        client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
        payload = futures_paper_status(settings, client)
        record_futures_paper_snapshot(settings, payload, source="reset")
        log_event(
            settings,
            "binance_futures_paper_reset",
            {
                "balanceUsdt": decimal_to_str(balance),
                "equityUsdt": payload.get("equityUsdt"),
                "openPositions": payload.get("openPositions"),
            },
        )
        return {
            **payload,
            "message": f"Binance futures paper account reset to {decimal_to_str(balance)} USDT.",
            "status": build_status(settings, runtime_snapshot(app)),
        }

    @app.post("/api/autorun/start")
    async def start_autorun() -> dict[str, Any]:
        settings = selected_web_settings(app)
        if is_emergency_stopped(settings):
            raise HTTPException(status_code=423, detail="긴급정지 상태에서는 자동 실행을 시작할 수 없습니다")
        controller = getattr(app.state, "autorun_controller", None)
        if controller is None:
            controller = AutoRunController(auto_run_scan, autorun_interval_seconds(settings))
            app.state.autorun_controller = controller
        await controller.start()
        return {"autorun": controller.snapshot(), "상태": build_status(settings, runtime_snapshot(app))}

    @app.post("/api/autorun/stop")
    async def stop_autorun() -> dict[str, Any]:
        settings = selected_web_settings(app)
        controller = getattr(app.state, "autorun_controller", None)
        if controller is not None:
            await controller.stop()
        return {"autorun": default_autorun_snapshot() if controller is None else controller.snapshot(), "상태": build_status(settings, runtime_snapshot(app))}

    @app.get("/api/markets")
    def markets() -> dict[str, Any]:
        settings = load_web_settings()
        client = make_client(settings)
        raw_markets = client.get_markets()
        krw_markets = [
            {"market": item["market"], "koreanName": item.get("korean_name"), "englishName": item.get("english_name")}
            for item in raw_markets
            if str(item.get("market", "")).startswith("KRW-")
        ]
        return {"markets": krw_markets}

    @app.get("/api/chart/{market}")
    def chart(market: str, unit: str | None = None, frame: str | None = None, count: int | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        market = market.upper()
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 留덉폆留?李⑦듃 議고쉶媛? 媛??ν빀?덈떎: {market}")
        chart_frame = normalize_chart_frame(frame or unit or str(settings.candle_unit))
        safe_count = normalize_chart_count(count, chart_frame, settings.candle_count)
        client = make_client(settings)
        try:
            candles = fetch_chart_candles(client, market, chart_frame, safe_count)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"李⑦듃 議고쉶 ?ㅽ뙣: {exc}") from exc
        return {
            "market": market,
            "unit": chart_frame,
            "unitLabel": chart_frame_label(chart_frame),
            "count": len(candles),
            "candles": chart_payload(candles, settings.short_window, settings.long_window),
        }

    @app.get("/api/portfolio-chart")
    def portfolio_chart(unit: str | None = None, frame: str | None = None, count: int | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        chart_frame = normalize_chart_frame(frame or unit or str(settings.candle_unit))
        safe_count = normalize_chart_count(count, chart_frame, settings.candle_count)
        snapshots = SqliteStore(settings.database_file).recent_portfolio_snapshots(
            portfolio_chart_snapshot_limit(chart_frame, safe_count)
        )
        exchange_mode = selected_exchange_mode(app, settings)
        currency = "KRW"
        if exchange_mode == "binance_futures_paper":
            snapshots = [snapshot for snapshot in snapshots if is_futures_paper_snapshot(snapshot)]
            currency = "USDT"
        candles = portfolio_chart_payload(snapshots, chart_frame, settings.short_window, settings.long_window, safe_count)
        return {
            "unit": chart_frame,
            "unitLabel": chart_frame_label(chart_frame),
            "count": len(candles),
            "metric": "equityUsdt" if currency == "USDT" else "equityKrw",
            "metricLabel": "珥앹옄??",
            "currency": currency,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "candles": candles,
        }

    @app.get("/api/orderbook/{market}")
    def orderbook(market: str, side: str = "bid", amount_krw: str | None = None, volume: str | None = None) -> dict[str, Any]:
        settings = selected_web_settings(app)
        market = market.upper()
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 留덉폆留??멸? 遺꾩꽍??媛??ν빀?덈떎: {market}")
        client = make_client(settings)
        current_price = Decimal("0")
        try:
            ticker = client.get_ticker(market)
            if ticker:
                current_price = Decimal(str(ticker[0].get("trade_price") or "0"))
        except Exception:
            current_price = Decimal("0")

        state = JsonPortfolioStateStore(settings.state_file).load(settings.paper_cash_krw)
        parsed_volume = Decimal(str(volume)) if volume is not None else None
        parsed_amount = Decimal(str(amount_krw)) if amount_krw is not None else None
        if side in {"ask", "sell", "매도"} and parsed_volume is None:
            parsed_volume = state.position(market).volume
            if parsed_amount is None and current_price > 0:
                parsed_amount = parsed_volume * current_price
        if parsed_amount is None:
            parsed_amount = settings.min_order_krw

        try:
            payload = fetch_orderbook_payload(client, market, settings)
            analysis = analyze_orderbook(
                settings=settings,
                payload=payload,
                side=side,
                amount_krw=parsed_amount,
                volume=parsed_volume,
                reference_price=current_price,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"?멸? 遺꾩꽍 ?ㅽ뙣: {exc}") from exc

        return {
            "enabled": settings.orderbook_analysis_enabled,
            "market": market,
            "side": analysis.side,
            "price": decimal_to_str(current_price),
            "analysis": analysis.to_dict(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/api/emergency-stop")
    async def emergency_stop() -> dict[str, Any]:
        settings = selected_web_settings(app)
        path = emergency_stop_path(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "stopped": True,
                    "stopped_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "web-dashboard",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        controller = getattr(app.state, "autorun_controller", None)
        if controller is not None:
            await controller.stop()
        return {"긴급정지": True, "상태": build_status(settings, runtime_snapshot(app))}

    @app.post("/api/resume-paper")
    def resume_paper() -> dict[str, Any]:
        settings = selected_web_settings(app)
        path = emergency_stop_path(settings)
        if path.exists():
            path.unlink()
        return {"긴급정지": False, "상태": build_status(settings, runtime_snapshot(app))}

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def load_web_settings() -> TradingSettings:
    env_file = os.environ.get("AUTOTRADING_ENV_FILE")
    return load_settings(env_file)


def autorun_interval_seconds(settings: TradingSettings) -> int:
    if settings.realtime_decision_enabled:
        return min(settings.loop_sleep_seconds, settings.realtime_decision_interval_seconds)
    return settings.loop_sleep_seconds


def settings_for_strategy_name(settings: TradingSettings, strategy_name: str) -> TradingSettings:
    name = strategy_name.strip()
    if not is_supported_strategy(name):
        raise HTTPException(status_code=400, detail=f"吏??먰븯吏? ?딅뒗 留ㅻℓ 湲곕쾿?낅땲?? {strategy_name}")
    selected = replace(settings, strategy_name=name)
    selected.validate()
    return selected


AUTO_STRATEGY_NAME = "adaptive_learning"


def selected_web_settings(app: FastAPI) -> TradingSettings:
    settings = load_web_settings()
    strategy_name = str(getattr(app.state, "strategy_name", settings.strategy_name))
    return settings_for_strategy_name(settings, strategy_name)


def selected_strategy_auto_select(app: FastAPI) -> bool:
    return bool(getattr(app.state, "strategy_auto_select", True))


def selected_exchange_mode(app: FastAPI, settings: TradingSettings | None = None) -> str:
    base_settings = settings or load_web_settings()
    mode = str(getattr(app.state, "exchange_mode", "") or load_exchange_mode(base_settings))
    return normalize_exchange_mode(mode)


def exchange_mode_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "exchange_mode.json"


def normalize_exchange_mode(mode: str | None) -> str:
    value = str(mode or "").strip().lower().replace("-", "_")
    return value if value in EXCHANGE_MODES else DEFAULT_EXCHANGE_MODE


def load_exchange_mode(settings: TradingSettings) -> str:
    path = exchange_mode_path(settings)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            return normalize_exchange_mode(str(payload.get("mode") or ""))
    if futures_paper_state_has_open_position(settings):
        return "binance_futures_paper"
    return DEFAULT_EXCHANGE_MODE


def futures_paper_state_has_open_position(settings: TradingSettings) -> bool:
    path = futures_paper_state_path(settings)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    positions = payload.get("positions", {}) if isinstance(payload, dict) else {}
    return bool(positions) if isinstance(positions, dict) else False


def save_exchange_mode(settings: TradingSettings, mode: str) -> dict[str, Any]:
    normalized = normalize_exchange_mode(mode)
    payload = {
        "mode": normalized,
        "label": EXCHANGE_MODES[normalized]["label"],
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = exchange_mode_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def exchange_mode_payload(settings: TradingSettings, mode: str | None = None) -> dict[str, Any]:
    active = normalize_exchange_mode(mode or load_exchange_mode(settings))
    return {
        "active": active,
        "label": EXCHANGE_MODES[active]["label"],
        "description": EXCHANGE_MODES[active]["description"],
        "orderBoundary": EXCHANGE_MODES[active]["orderBoundary"],
        "modes": [
            {
                "mode": key,
                "label": value["label"],
                "description": value["description"],
                "orderBoundary": value["orderBoundary"],
                "active": key == active,
            }
            for key, value in EXCHANGE_MODES.items()
        ],
    }


def set_selected_strategy(app: FastAPI, strategy_name: str | None, auto_select: bool | None = None) -> TradingSettings:
    base_settings = load_web_settings()
    use_auto = strategy_name is None if auto_select is None else bool(auto_select)
    if not use_auto and strategy_name is None:
        strategy_name = str(getattr(app.state, "strategy_name", base_settings.strategy_name))
    selected_name = AUTO_STRATEGY_NAME if use_auto else str(strategy_name or base_settings.strategy_name)
    settings = settings_for_strategy_name(base_settings, selected_name)
    app.state.strategy_name = settings.strategy_name
    app.state.strategy_auto_select = use_auto
    save_selected_strategy_selection(settings, use_auto)
    return settings


def strategy_selection_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "strategy_selection.json"


def load_strategy_selection(settings: TradingSettings) -> dict[str, Any]:
    path = strategy_selection_path(settings)
    if not path.exists():
        return {"strategyName": AUTO_STRATEGY_NAME, "autoSelect": True}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"strategyName": AUTO_STRATEGY_NAME, "autoSelect": True}
    auto_select = bool(payload.get("autoSelect", True))
    if auto_select:
        return {"strategyName": AUTO_STRATEGY_NAME, "autoSelect": True}
    name = str(payload.get("strategyName") or settings.strategy_name)
    if not is_supported_strategy(name):
        name = settings.strategy_name if is_supported_strategy(settings.strategy_name) else AUTO_STRATEGY_NAME
    return {"strategyName": name, "autoSelect": False}


def load_selected_strategy_name(settings: TradingSettings) -> str:
    return str(load_strategy_selection(settings)["strategyName"])


def load_selected_strategy_auto_select(settings: TradingSettings) -> bool:
    return bool(load_strategy_selection(settings)["autoSelect"])


def save_selected_strategy_name(settings: TradingSettings) -> None:
    save_selected_strategy_selection(settings, False)


def save_selected_strategy_selection(settings: TradingSettings, auto_select: bool) -> None:
    path = strategy_selection_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "strategyName": settings.strategy_name,
                "autoSelect": auto_select,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def recommended_markets_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "recommended_markets.json"


def normalize_recommended_market(market: str) -> str:
    cleaned = str(market or "").strip().upper()
    if not cleaned:
        raise HTTPException(status_code=400, detail="異붿쿇 肄붿씤 留덉폆??鍮꾩뼱 ?덉뒿?덈떎")
    if "-" not in cleaned:
        cleaned = f"KRW-{cleaned}"
    if not cleaned.startswith("KRW-") or cleaned.count("-") != 1:
        raise HTTPException(status_code=400, detail=f"KRW 留덉폆留?異붿쿇?????덉뒿?덈떎: {market}")
    return cleaned


def normalize_market_list(markets: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_market in markets:
        market = normalize_recommended_market(raw_market)
        if market not in normalized:
            normalized.append(market)
    return tuple(normalized)


def load_market_preferences(settings: TradingSettings) -> dict[str, Any]:
    path = recommended_markets_path(settings)
    if not path.exists():
        return {"markets": (), "excludedMarkets": (), "recommendOnly": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"markets": (), "excludedMarkets": (), "recommendOnly": False}
    raw_markets = payload.get("markets", []) if isinstance(payload, dict) else []
    raw_excluded_markets = payload.get("excludedMarkets", []) if isinstance(payload, dict) else []
    recommend_only = bool(payload.get("recommendOnly", False)) if isinstance(payload, dict) else False
    if not isinstance(raw_markets, list):
        raw_markets = []
    if not isinstance(raw_excluded_markets, list):
        raw_excluded_markets = []
    markets: list[str] = []
    for raw_market in raw_markets:
        try:
            market = normalize_recommended_market(str(raw_market))
        except HTTPException:
            continue
        if market not in markets:
            markets.append(market)
    excluded_markets: list[str] = []
    for raw_market in raw_excluded_markets:
        try:
            market = normalize_recommended_market(str(raw_market))
        except HTTPException:
            continue
        if market not in markets and market not in excluded_markets:
            excluded_markets.append(market)
    return {
        "markets": tuple(markets),
        "excludedMarkets": tuple(excluded_markets),
        "recommendOnly": recommend_only,
    }


def load_recommended_markets(settings: TradingSettings) -> tuple[str, ...]:
    return tuple(load_market_preferences(settings)["markets"])


def load_excluded_markets(settings: TradingSettings) -> tuple[str, ...]:
    return tuple(load_market_preferences(settings)["excludedMarkets"])


def save_market_preferences(
    settings: TradingSettings,
    markets: list[str] | tuple[str, ...] | None = None,
    excluded_markets: list[str] | tuple[str, ...] | None = None,
    recommend_only: bool | None = None,
) -> dict[str, Any]:
    current = load_market_preferences(settings)
    normalized = normalize_market_list(markets) if markets is not None else tuple(current["markets"])
    normalized_excluded = (
        normalize_market_list(excluded_markets) if excluded_markets is not None else tuple(current["excludedMarkets"])
    )
    normalized_excluded = tuple(market for market in normalized_excluded if market not in normalized)
    active_recommend_only = bool(current["recommendOnly"] if recommend_only is None else recommend_only)
    path = recommended_markets_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "markets": list(normalized),
        "excludedMarkets": list(normalized_excluded),
        "count": len(normalized),
        "excludedCount": len(normalized_excluded),
        "recommendOnly": active_recommend_only,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "markets": normalized,
        "excludedMarkets": normalized_excluded,
        "recommendOnly": active_recommend_only,
    }


def save_recommended_markets(settings: TradingSettings, markets: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(save_market_preferences(settings, markets=markets)["markets"])


def preference_checked(request: RecommendedMarketToggleRequest) -> bool:
    if request.checked is not None:
        return bool(request.checked)
    if request.recommended is not None:
        return bool(request.recommended)
    return True


def update_market_preference(
    settings: TradingSettings,
    request: RecommendedMarketToggleRequest,
) -> dict[str, Any]:
    market = normalize_recommended_market(request.market)
    preferences = load_market_preferences(settings)
    recommended = list(preferences["markets"])
    excluded = list(preferences["excludedMarkets"])
    checked = preference_checked(request)
    preference = str(request.preference or "recommended").lower()
    if preference in {"excluded", "blocked", "not_recommended", "exclude"}:
        if checked and market not in excluded:
            excluded.append(market)
        elif not checked:
            excluded = [item for item in excluded if item != market]
        if checked:
            recommended = [item for item in recommended if item != market]
    else:
        if checked and market not in recommended:
            recommended.append(market)
        elif not checked:
            recommended = [item for item in recommended if item != market]
        if checked:
            excluded = [item for item in excluded if item != market]
    return save_market_preferences(
        settings,
        markets=recommended,
        excluded_markets=excluded,
        recommend_only=bool(preferences["recommendOnly"]),
    )


def recommendation_payload(settings: TradingSettings, preferences: dict[str, Any] | tuple[str, ...] | None = None) -> dict[str, Any]:
    if isinstance(preferences, dict):
        selected = tuple(preferences.get("markets", ()))
        excluded = tuple(preferences.get("excludedMarkets", ()))
        recommend_only = bool(preferences.get("recommendOnly", False))
    else:
        loaded = load_market_preferences(settings)
        selected = tuple(preferences if preferences is not None else loaded["markets"])
        excluded = tuple(loaded["excludedMarkets"])
        recommend_only = bool(loaded["recommendOnly"])
    if recommend_only and selected:
        mode_label = "추천 우선 자산"
        description = "추천 체크된 코인을 우선 검토하되, 전체 자동 후보도 계속 분석하고 비추천 코인은 제외합니다."
    elif recommend_only:
        mode_label = "추천 우선 자동 후보"
        description = "추천 코인이 없어도 전체 자동 후보를 계속 분석하고 비추천 코인은 제외합니다."
    elif excluded:
        mode_label = "비추천 제외 자동 후보"
        description = "전체 자동 후보를 사용하되 비추천 체크된 코인은 신규 진입에서 제외합니다."
    else:
        mode_label = "전체 자동 후보"
        description = "추천 전용 모드가 꺼져 있어 학습/실시간 엔진의 전체 후보를 사용합니다."
    return {
        "active": bool(selected or excluded or recommend_only),
        "count": len(selected),
        "markets": list(selected),
        "excludedCount": len(excluded),
        "excludedMarkets": list(excluded),
        "recommendOnly": recommend_only,
        "modeLabel": mode_label,
        "description": description,
        "appliesTo": ["dynamic_allocation", "realtime_decision"],
    }


def recommended_investment_markets(
    settings: TradingSettings,
    state: PortfolioState,
    preferences: dict[str, Any] | tuple[str, ...] | None = None,
    purpose: str = "allocation",
) -> tuple[str, ...] | None:
    if isinstance(preferences, dict):
        selected = tuple(preferences.get("markets", ()))
        excluded = tuple(preferences.get("excludedMarkets", ()))
        recommend_only = bool(preferences.get("recommendOnly", False))
    elif preferences is not None:
        selected = tuple(preferences)
        excluded = ()
        recommend_only = True
    else:
        loaded = load_market_preferences(settings)
        selected = tuple(loaded["markets"])
        excluded = tuple(loaded["excludedMarkets"])
        recommend_only = bool(loaded["recommendOnly"])
    universe = default_investment_universe(settings, state, purpose)
    held = held_markets(state)
    if not selected and not excluded:
        return None
    excluded_set = set(excluded)
    preferred = [market for market in selected if market not in excluded_set]
    allowed = [market for market in universe if market not in excluded_set]
    return tuple(dict.fromkeys([*preferred, *allowed, *held]))


def default_investment_universe(settings: TradingSettings, state: PortfolioState, purpose: str) -> tuple[str, ...]:
    model = load_learning_model(settings)
    if purpose == "realtime":
        return realtime_market_universe(settings, state, model)
    learned_markets = model.get("markets") if isinstance(model.get("markets"), dict) else {}
    return tuple(learned_markets.keys() or settings.markets)


def realtime_decision_candidate_markets(
    settings: TradingSettings,
    client: Any,
    state: PortfolioState,
    preferences: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    preferences = preferences or load_market_preferences(settings)
    selected = tuple(preferences.get("markets", ()))
    excluded = tuple(preferences.get("excludedMarkets", ()))
    excluded_set = set(excluded)
    try:
        markets, _meta = krw_market_metadata(client)
    except Exception:
        fallback = recommended_investment_markets(settings, state, preferences, "realtime")
        return fallback if fallback is not None else realtime_market_universe(settings, state)
    preferred = [market for market in selected if market in markets and market not in excluded_set]
    allowed = [market for market in markets if market not in excluded_set]
    return tuple(dict.fromkeys([*preferred, *allowed, *held_markets(state)]))


def latest_range_simulation_payload(settings: TradingSettings) -> dict[str, Any]:
    state_dir = settings.state_file.parent
    paths = sorted(
        state_dir.glob("range_simulation_*.json") if state_dir.exists() else [],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not paths:
        return {
            "ok": False,
            "message": "理쒓렐 ?쒕??덉씠??寃곌낵媛? ?놁뒿?덈떎.",
            "path": None,
        }

    path = paths[0]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "message": f"?쒕??덉씠??寃곌낵瑜??쎌쓣 ???놁뒿?덈떎: {exc}",
            "path": str(path),
            "fileName": path.name,
        }

    assumptions = payload.get("assumptions", {}) if isinstance(payload.get("assumptions"), dict) else {}
    portfolio = payload.get("portfolio", {}) if isinstance(payload.get("portfolio"), dict) else {}
    simulation_range = payload.get("range", {}) if isinstance(payload.get("range"), dict) else {}
    universe = payload.get("universe", {}) if isinstance(payload.get("universe"), dict) else {}
    strategy_picks = payload.get("strategyPicks", [])
    if not isinstance(strategy_picks, list):
        strategy_picks = []

    compact_portfolio = {
        "startEquityKrw": portfolio.get("startEquityKrw", "0"),
        "finalEquityKrw": portfolio.get("finalEquityKrw", "0"),
        "totalReturnPct": portfolio.get("totalReturnPct", "0"),
        "realizedPnlKrw": portfolio.get("realizedPnlKrw", "0"),
        "feesPaidKrw": portfolio.get("feesPaidKrw", "0"),
        "orderCount": portfolio.get("orderCount", 0),
        "maxDrawdownPct": portfolio.get("maxDrawdownPct", "0"),
        "openPositions": len(portfolio.get("openPositions", []) or []),
    }

    current_settings = current_simulation_assumptions(settings)

    return {
        "ok": True,
        "path": str(path),
        "fileName": path.name,
        "generatedAt": payload.get("generatedAt"),
        "modeLabel": range_simulation_mode_label(assumptions),
        "currentModeLabel": range_simulation_mode_label(current_settings),
        "periodDays": range_simulation_period_days(simulation_range),
        "range": simulation_range,
        "universe": {
            "marketCount": universe.get("marketCount", 0),
            "requestedMaxMarkets": universe.get("requestedMaxMarkets", 0),
            "selectionMethod": universe.get("selectionMethod", ""),
        },
        "assumptions": assumptions,
        "currentSettings": current_settings,
        "settingsDrift": simulation_settings_drift(assumptions, current_settings),
        "portfolio": compact_portfolio,
        "topStrategies": decorate_simulation_strategy_picks(settings, strategy_picks[:5]),
        "riskNotes": {
            "historicalOrderbookIncluded": bool(assumptions.get("historicalOrderbookIncluded")),
            "slippageIncluded": bool(assumptions.get("slippageIncluded")),
            "feeRate": assumptions.get("feeRate", "0"),
        },
    }


def simulation_playback_payload(settings: TradingSettings) -> dict[str, Any]:
    path = latest_simulation_playback_file(settings.state_file.parent)
    if path is None:
        return {"ok": False, "message": "?ъ깮???쒕??덉씠??寃곌낵媛? ?놁뒿?덈떎"}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"?쒕??덉씠???ъ깮 ?뚯씪???쎌쓣 ???놁뒿?덈떎: {exc}"}

    frames = simulation_playback_frames(payload)
    trades = simulation_playback_trades(payload)
    if not frames:
        return {"ok": False, "message": "?ъ깮 媛??ν븳 ?먯궛 怨≪꽑???놁뒿?덈떎", "fileName": path.name}

    portfolio = payload.get("portfolio", {}) if isinstance(payload.get("portfolio"), dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    assumptions = payload.get("assumptions", {}) if isinstance(payload.get("assumptions"), dict) else {}
    simulation_range = payload.get("range", {}) if isinstance(payload.get("range"), dict) else {}
    universe = payload.get("universe", {}) if isinstance(payload.get("universe"), dict) else {}

    return {
        "ok": True,
        "path": str(path),
        "fileName": path.name,
        "generatedAt": payload.get("generatedAt"),
        "mode": payload.get("mode") or "range_simulation",
        "range": simulation_range,
        "universe": {
            "marketCount": universe.get("marketCount", 0),
            "requestedMaxMarkets": universe.get("requestedMaxMarkets", 0),
            "selectionMethod": universe.get("selectionMethod", ""),
        },
        "assumptions": assumptions,
        "portfolio": {
            "startEquityKrw": portfolio.get("startEquityKrw", assumptions.get("startingCashKrw", "0")),
            "finalEquityKrw": portfolio.get("finalEquityKrw", "0"),
            "totalReturnPct": portfolio.get("totalReturnPct", summary.get("averageReturnPct", "0")),
            "feesPaidKrw": portfolio.get("feesPaidKrw", summary.get("totalFeesPaidKrw", "0")),
            "orderCount": portfolio.get("orderCount", summary.get("totalOrderCount", len(trades))),
            "maxDrawdownPct": portfolio.get("maxDrawdownPct", "0"),
        },
        "frames": frames,
        "trades": trades,
    }


def latest_simulation_playback_file(state_dir: Path) -> Path | None:
    patterns = (
        "day_walkforward_aggressive_*.json",
        "range_simulation_*.json",
        "april_unknown_daily_aggressive_*.json",
    )
    paths: list[Path] = []
    if state_dir.exists():
        for pattern in patterns:
            paths.extend(state_dir.glob(pattern))
    return max(paths, key=lambda item: item.stat().st_mtime) if paths else None


def simulation_playback_frames(payload: dict[str, Any]) -> list[dict[str, Any]]:
    frames = portfolio_curve_frames(payload.get("portfolio"))
    daily_results = payload.get("dailyResults")
    if not frames and isinstance(daily_results, list):
        for item in daily_results:
            if isinstance(item, dict):
                frames.extend(portfolio_curve_frames(item.get("portfolio")))

    frames = sorted(frames, key=lambda item: str(item.get("time") or ""))
    return [
        {
            "time": frame.get("time"),
            "equityKrw": frame.get("equityKrw", "0"),
            "cashKrw": frame.get("cashKrw", "0"),
            "openPositions": frame.get("openPositions", 0),
        }
        for frame in frames[-1200:]
        if frame.get("time")
    ]


def portfolio_curve_frames(portfolio: Any) -> list[dict[str, Any]]:
    if not isinstance(portfolio, dict):
        return []
    curve = portfolio.get("equityCurve")
    if not isinstance(curve, list):
        return []
    return [dict(item) for item in curve if isinstance(item, dict)]


def simulation_playback_trades(payload: dict[str, Any]) -> list[dict[str, Any]]:
    trades = portfolio_trades(payload.get("portfolio"))
    daily_results = payload.get("dailyResults")
    if not trades and isinstance(daily_results, list):
        for item in daily_results:
            if isinstance(item, dict):
                trades.extend(portfolio_trades(item.get("portfolio")))

    rows = sorted(trades, key=lambda item: str(item.get("time") or ""))
    return [
        {
            "time": row.get("time"),
            "market": row.get("market", ""),
            "side": row.get("side", ""),
            "price": row.get("price", "0"),
            "budgetKrw": row.get("budgetKrw", row.get("cashDelta", "0")),
            "cashAfter": row.get("cashAfter", "0"),
        }
        for row in rows[-600:]
        if row.get("time")
    ]


def portfolio_trades(portfolio: Any) -> list[dict[str, Any]]:
    if not isinstance(portfolio, dict):
        return []
    trades = portfolio.get("trades")
    if not isinstance(trades, list):
        return []
    return [dict(item) for item in trades if isinstance(item, dict)]


def current_simulation_assumptions(settings: TradingSettings) -> dict[str, Any]:
    return {
        "feeRate": decimal_to_str(settings.fee_rate),
        "maxDailyOrders": settings.max_daily_orders,
        "maxOpenPositions": settings.max_open_positions,
        "maxPositionPct": decimal_to_str(settings.allocation_max_position_pct),
        "maxDeployPct": decimal_to_str(settings.allocation_max_deploy_pct),
        "maxOrderPct": decimal_to_str(settings.realtime_max_order_pct),
        "maxOrderKrw": decimal_to_str(settings.max_order_krw),
        "maxPositionKrw": decimal_to_str(settings.max_position_krw),
        "allocationMaxOrdersPerRun": settings.allocation_max_orders_per_run,
    }


def simulation_settings_drift(saved: dict[str, Any], current: dict[str, Any]) -> list[dict[str, str]]:
    display_keys = ("feeRate", "maxDailyOrders", "maxPositionPct", "maxDeployPct", "maxOrderPct")
    drift: list[dict[str, str]] = []
    for key in display_keys:
        if key not in saved:
            continue
        saved_value = str(saved.get(key))
        current_value = str(current.get(key))
        if saved_value != current_value:
            drift.append({"key": key, "saved": saved_value, "current": current_value})
    return drift


def range_simulation_mode_label(assumptions: dict[str, Any]) -> str:
    if (
        assumption_decimal(assumptions, "maxDeployPct") >= Decimal("1")
        and assumption_decimal(assumptions, "maxPositionPct") >= Decimal("1")
        and assumption_decimal(assumptions, "maxOrderPct") >= Decimal("1")
        and assumption_int(assumptions, "maxDailyOrders") >= 1_000_000
    ):
        return "공격형 100% 복리"
    return "최근 시뮬레이션"


def assumption_decimal(assumptions: dict[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(assumptions.get(key, "0")))
    except Exception:
        return Decimal("0")


def assumption_int(assumptions: dict[str, Any], key: str) -> int:
    try:
        return int(assumptions.get(key) or 0)
    except Exception:
        return 0


def range_simulation_period_days(simulation_range: dict[str, Any]) -> str:
    start = simulation_range.get("startKst")
    end = simulation_range.get("endKst")
    if not start or not end:
        return "0"
    try:
        delta = datetime.fromisoformat(str(end)) - datetime.fromisoformat(str(start))
    except ValueError:
        return "0"
    return decimal_to_str(Decimal(str(delta.total_seconds())) / Decimal("86400"))


def decorate_simulation_strategy_picks(settings: TradingSettings, picks: list[Any]) -> list[dict[str, Any]]:
    if not picks:
        return []

    catalog = {item["name"]: item for item in strategy_catalog(settings.strategy_name)}
    market_meta: dict[str, dict[str, Any]] = {}
    try:
        _markets, market_meta = krw_market_metadata(make_client(settings))
    except Exception:
        market_meta = {}

    decorated: list[dict[str, Any]] = []
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        market = str(pick.get("market") or "")
        meta = market_meta.get(market, {})
        strategy_name = str(pick.get("strategy") or "")
        strategy = catalog.get(strategy_name, {})
        decorated.append(
            {
                "market": market,
                "symbol": market_symbol(market),
                "koreanName": meta.get("koreanName") or "",
                "displayName": market_display_name(market, meta),
                "strategy": strategy_name,
                "strategyLabel": strategy.get("label") or strategy_name,
                "score": pick.get("score", "0"),
                "totalReturnPct": pick.get("totalReturnPct", "0"),
                "maxDrawdownPct": pick.get("maxDrawdownPct", "0"),
                "orderCount": pick.get("orderCount", 0),
                "finalEquityKrw": pick.get("finalEquityKrw", "0"),
            }
        )
    return decorated


def is_auth_exempt_path(path: str) -> bool:
    return path in AUTH_EXEMPT_PATHS


def parse_basic_auth_header(header: str) -> tuple[str, str] | None:
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded.strip():
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return username, password


def is_basic_auth_valid(header: str, settings: TradingSettings) -> bool:
    credentials = parse_basic_auth_header(header)
    if credentials is None:
        return False
    username, password = credentials
    return secrets.compare_digest(username, settings.dashboard_username) and secrets.compare_digest(
        password,
        settings.dashboard_password,
    )


def auth_required_response() -> Response:
    return Response(
        content="Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}", charset="UTF-8"'},
    )


def emergency_stop_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "emergency_stop.json"


def is_emergency_stopped(settings: TradingSettings) -> bool:
    path = emergency_stop_path(settings)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    return bool(payload.get("stopped", True))


def runtime_snapshot(app: FastAPI) -> dict[str, Any]:
    realtime = getattr(app.state, "realtime_service", None)
    autorun = getattr(app.state, "autorun_controller", None)
    realtime_decision_monitor = getattr(app.state, "realtime_decision_monitor", None)
    ai_pm_monitor = getattr(app.state, "ai_pm_monitor", None)
    market_intel_monitor = getattr(app.state, "market_intel_monitor", None)
    return {
        "realtime": default_realtime_snapshot() if realtime is None else realtime.snapshot(),
        "autorun": default_autorun_snapshot() if autorun is None else autorun.snapshot(),
        "monitors": {
            "realtimeDecision": default_autorun_snapshot()
            if realtime_decision_monitor is None
            else realtime_decision_monitor.snapshot(),
            "aiPm": default_autorun_snapshot() if ai_pm_monitor is None else ai_pm_monitor.snapshot(),
            "marketIntel": default_autorun_snapshot()
            if market_intel_monitor is None
            else market_intel_monitor.snapshot(),
        },
        "strategyAutoSelect": selected_strategy_auto_select(app),
        "exchangeMode": selected_exchange_mode(app),
        "binanceFuturesPaperRuntime": getattr(app.state, "binance_futures_paper_runtime", {}),
    }


def default_realtime_snapshot() -> dict[str, Any]:
    return {
        "connected": False,
        "reconnects": 0,
        "lastError": None,
        "lastMessageAt": None,
        "startedAt": None,
        "tickers": {},
        "trades": {},
    }


def default_autorun_snapshot() -> dict[str, Any]:
    return {
        "running": False,
        "intervalSeconds": 0,
        "iterations": 0,
        "lastStartedAt": None,
        "lastRunAt": None,
        "lastFinishedAt": None,
        "lastResultCount": 0,
        "lastError": None,
    }


def security_payload(settings: TradingSettings) -> dict[str, Any]:
    return {
        "dashboardAuthEnabled": settings.dashboard_auth_enabled,
        "dashboardUsername": settings.dashboard_username if settings.dashboard_auth_enabled else "",
        "healthCheckExempt": True,
    }


def build_status(settings: TradingSettings, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime or {
        "realtime": default_realtime_snapshot(),
        "autorun": default_autorun_snapshot(),
        "monitors": {},
    }
    errors: list[str] = []
    client = make_client(settings)
    candles: list[Candle] = []
    ticker_by_market: dict[str, dict[str, Any]] = {}
    store = JsonPortfolioStateStore(settings.state_file)
    state = store.load(settings.paper_cash_krw)
    display_markets, market_meta = dashboard_display_markets(settings, client, state)
    market_preferences = load_market_preferences(settings)

    try:
        raw_tickers = fetch_tickers(client, display_markets)
        ticker_by_market = {str(item.get("market")): item for item in raw_tickers}
    except Exception as exc:  # Network/API failures should not blank the dashboard.
        errors.append(f"?꾩옱媛? 議고쉶 ?ㅽ뙣: {exc}")

    ticker_by_market = merge_realtime_tickers(ticker_by_market, runtime.get("realtime", {}))
    active_ticker = ticker_by_market.get(settings.market, {})
    try:
        candles = fetch_candles(client, settings)
    except Exception as exc:
        errors.append(f"罹붾뱾 議고쉶 ?ㅽ뙣: {exc}")

    prices = price_map(display_markets, ticker_by_market)
    latest_price = prices.get(settings.market, latest_market_price(active_ticker, candles))
    signal = make_strategy(settings).evaluate(candles)
    risk_manager = PortfolioRiskManager(settings)
    signal = risk_manager.protective_signal(signal, state, latest_price)
    decision = risk_manager.evaluate(signal, state, latest_price)
    emergency_stopped = is_emergency_stopped(settings)
    live = live_runtime_payload(settings)
    account = paper_account_payload(state, prices, settings.market)
    alerts = evaluate_alerts(
        settings,
        runtime,
        account,
        live,
        emergency_stopped=emergency_stopped,
        host=os.environ.get("AUTOTRADING_HOST", "127.0.0.1"),
    )
    pm_status = ai_pm_status_payload(settings)
    exchange_mode = normalize_exchange_mode(str(runtime.get("exchangeMode") or ""))
    futures_paper = None
    if exchange_mode == "binance_futures_paper":
        futures_paper = safe_futures_paper_status(settings)
        if futures_paper.get("error"):
            errors.append(f"Binance futures paper status failed: {futures_paper['error']}")
        realtime_decision = binance_futures_realtime_status_payload(
            settings,
            runtime.get("binanceFuturesPaperRuntime", {}),
            futures_paper,
            source="status",
        )
    else:
        realtime_decision = realtime_decision_status_payload(settings)
    chart_levels_by_market = decision_chart_levels_by_market(realtime_decision)
    market_rows = market_rows_payload(
        display_markets,
        settings,
        ticker_by_market,
        state,
        prices,
        runtime.get("realtime", {}),
        market_meta,
        tuple(market_preferences["markets"]),
        tuple(market_preferences["excludedMarkets"]),
        chart_levels_by_market,
    )
    investment_agency = (
        realtime_decision.get("last", {}).get("plan", {}).get("investmentAgency", {})
        if isinstance(realtime_decision, dict)
        else {}
    )

    return {
        "runtime": {
            "mode": "paper",
            "modeLabel": "페이퍼",
            "liveTradingEnabled": settings.live_trading_enabled,
            "emergencyStopped": emergency_stopped,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "errors": errors,
        },
        "realtime": runtime["realtime"],
        "autorun": runtime["autorun"],
        "monitors": runtime.get("monitors", {}),
        "security": security_payload(settings),
        "live": live,
        "alerts": alerts_payload(alerts),
        "exchangeMode": exchange_mode_payload(settings, exchange_mode),
        "binanceFuturesPaper": futures_paper,
        "settings": {
            "market": settings.market,
            "markets": list(settings.markets),
            "exchangeMode": exchange_mode,
            "candleUnit": settings.candle_unit,
            "candleCount": settings.candle_count,
            "strategyName": settings.strategy_name,
            "strategyAutoSelect": bool(runtime.get("strategyAutoSelect", settings.strategy_name == AUTO_STRATEGY_NAME)),
            "strategyModeLabel": "자동설정"
            if bool(runtime.get("strategyAutoSelect", settings.strategy_name == AUTO_STRATEGY_NAME))
            else "수동선택",
            "shortWindow": settings.short_window,
            "longWindow": settings.long_window,
            "strategyMinTrendPct": decimal_to_str(settings.strategy_min_trend_pct),
            "strategyMinVolumeRatio": decimal_to_str(settings.strategy_min_volume_ratio),
            "strategyMaxVolatilityPct": decimal_to_str(settings.strategy_max_volatility_pct),
            "strategyPullbackSellPct": decimal_to_str(settings.strategy_pullback_sell_pct),
            "learningCandleCount": settings.learning_candle_count,
            "learningMaxMarkets": settings.learning_max_markets,
            "learningExcludeMarketWarnings": settings.learning_exclude_market_warnings,
            "realtimeDecisionEnabled": settings.realtime_decision_enabled,
            "realtimeDecisionIntervalSeconds": settings.realtime_decision_interval_seconds,
            "realtimeWatchTopN": settings.realtime_watch_top_n,
            "realtimeCandleTopN": settings.realtime_candle_top_n,
            "realtimeCandleRefreshSeconds": settings.realtime_candle_refresh_seconds,
            "realtimeCandidateTopN": settings.realtime_candidate_top_n,
            "realtimeMinScore": decimal_to_str(settings.realtime_min_score),
            "realtimeMaxOrderPct": decimal_to_str(settings.realtime_max_order_pct),
            "orderbookAnalysisEnabled": settings.orderbook_analysis_enabled,
            "orderbookDepthLevels": settings.orderbook_depth_levels,
            "orderbookMaxSlippagePct": decimal_to_str(settings.orderbook_max_slippage_pct),
            "orderbookMinFillRatio": decimal_to_str(settings.orderbook_min_fill_ratio),
            "orderbookMinDepthRatio": decimal_to_str(settings.orderbook_min_depth_ratio),
            "orderbookLiquidityUsePct": decimal_to_str(settings.orderbook_liquidity_use_pct),
            "orderbookRepriceSpreadPct": decimal_to_str(settings.orderbook_reprice_spread_pct),
            "orderbookPriceStepBps": decimal_to_str(settings.orderbook_price_step_bps),
            "dynamicAllocationEnabled": settings.dynamic_allocation_enabled,
            "allocationIntervalSeconds": settings.allocation_interval_seconds,
            "allocationTopN": settings.allocation_top_n,
            "allocationFocusTopN": settings.allocation_focus_top_n,
            "allocationMinScore": decimal_to_str(settings.allocation_min_score),
            "allocationMaxDeployPct": decimal_to_str(settings.allocation_max_deploy_pct),
            "allocationMaxPositionPct": decimal_to_str(settings.allocation_max_position_pct),
            "allocationMaxOrdersPerRun": settings.allocation_max_orders_per_run,
            "minOrderKrw": decimal_to_str(settings.min_order_krw),
            "maxOrderKrw": decimal_to_str(settings.max_order_krw),
            "maxPositionKrw": decimal_to_str(settings.max_position_krw),
            "dailyLossLimitKrw": decimal_to_str(settings.daily_loss_limit_krw),
            "stopLossPct": decimal_to_str(settings.stop_loss_pct),
            "takeProfitPct": decimal_to_str(settings.take_profit_pct),
            "cooldownSeconds": settings.cooldown_seconds,
            "maxOpenPositions": settings.max_open_positions,
            "maxDailyOrders": settings.max_daily_orders,
        },
        "goal": goal_payload(settings, state, prices),
        "market": market_payload(active_ticker, latest_price, market_meta),
        "signal": signal_payload(signal),
        "risk": {
            "approved": decision.approved,
            "reason": decision.reason,
            "intent": intent_payload(decision.intent),
        },
        "account": account,
        "portfolio": portfolio_payload(state, prices),
        "recommended": recommendation_payload(settings, market_preferences),
        "realtimeDecision": realtime_decision,
        "investmentAgency": investment_agency,
        "pm": pm_status,
        "opsWatch": ops_watch_payload(settings, runtime, account, live, market_rows, realtime_decision, errors),
        "markets": market_rows,
        "chart": chart_payload(candles, settings.short_window, settings.long_window),
        "logs": log_payload(errors, signal, decision.approved, decision.reason),
    }


def binance_spot_payload(settings: TradingSettings) -> dict[str, Any]:
    binance = BinanceSpotClient(
        base_url=settings.binance_base_url,
        api_key=settings.binance_api_key,
        secret_key=settings.binance_secret_key,
    )
    payload: dict[str, Any] = {
        "configured": bool(settings.binance_api_key and settings.binance_secret_key),
        "baseUrl": settings.binance_base_url,
        "symbols": list(settings.binance_symbols),
        "publicOk": False,
        "accountOk": False,
        "prices": [],
        "error": None,
    }
    try:
        binance.ping()
        payload["prices"] = [binance.ticker_price(symbol) for symbol in settings.binance_symbols[:5]]
        payload["publicOk"] = True
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


def binance_futures_base_url(settings: TradingSettings) -> str:
    if settings.binance_futures_testnet_enabled and settings.binance_futures_base_url == "https://fapi.binance.com":
        return "https://demo-fapi.binance.com"
    return settings.binance_futures_base_url


def binance_futures_payload(settings: TradingSettings) -> dict[str, Any]:
    base_url = binance_futures_base_url(settings)
    client = BinanceFuturesClient(
        base_url=base_url,
        api_key=settings.binance_futures_api_key,
        secret_key=settings.binance_futures_secret_key,
    )
    configured = bool(settings.binance_futures_api_key and settings.binance_futures_secret_key)
    payload: dict[str, Any] = {
        "configured": configured,
        "baseUrl": base_url,
        "testnet": settings.binance_futures_testnet_enabled,
        "symbols": list(settings.binance_futures_symbols),
        "publicOk": False,
        "accountOk": False,
        "shortReady": False,
        "ordersEnabled": False,
        "prices": [],
        "account": None,
        "positions": [],
        "paper": None,
        "error": None,
        "accountError": None,
    }
    try:
        client.ping()
        payload["prices"] = [client.ticker_price(symbol) for symbol in settings.binance_futures_symbols[:5]]
        payload["serverTime"] = client.server_time().get("serverTime")
        payload["publicOk"] = True
    except Exception as exc:
        payload["error"] = str(exc)

    if configured:
        try:
            account = client.account()
            account_payload, positions = binance_futures_account_summary(account)
            payload["account"] = account_payload
            payload["positions"] = positions
            payload["accountOk"] = True
            available_balance = Decimal(str(account_payload.get("availableBalance") or "0"))
            payload["funded"] = available_balance > 0
            payload["shortReady"] = bool(payload["publicOk"]) and available_balance > 0
        except Exception as exc:
            payload["accountError"] = str(exc)
    try:
        payload["paper"] = futures_paper_status(settings, client)
    except Exception as exc:
        payload["paper"] = {"simulated": True, "error": str(exc)}
    return payload


def safe_futures_paper_status(settings: TradingSettings) -> dict[str, Any]:
    client = BinanceFuturesClient(base_url=binance_futures_base_url(settings))
    try:
        return futures_paper_status(settings, client)
    except Exception as exc:
        return {
            "mode": "local-binance-futures-paper",
            "simulated": True,
            "currency": "USDT",
            "error": str(exc),
        }


def binance_futures_realtime_status_payload(
    settings: TradingSettings,
    cycle_payload: dict[str, Any] | None = None,
    status_payload: dict[str, Any] | None = None,
    source: str = "status",
) -> dict[str, Any]:
    cycle_payload = cycle_payload if isinstance(cycle_payload, dict) else {}
    status_payload = status_payload if isinstance(status_payload, dict) else {}
    candidates = futures_candidate_rows(cycle_payload)
    positions = status_payload.get("positions") if isinstance(status_payload.get("positions"), list) else []
    positions_by_symbol = {str(position.get("symbol") or ""): position for position in positions if isinstance(position, dict)}
    situations = [
        futures_candidate_situation(candidate, positions_by_symbol.get(str(candidate.get("symbol") or "")), status_payload)
        for candidate in candidates
    ]
    if not situations and positions_by_symbol:
        situations = [futures_position_situation(position, status_payload) for position in positions_by_symbol.values()]
    selected_cap = int_from_payload(
        cycle_payload.get("maxOpenPositions") or status_payload.get("maxOpenPositions"),
        MAX_OPEN_POSITIONS,
    )
    selected = [
        situation
        for situation in situations
        if situation.get("action") in {"short", "long", "hold"}
        and (situation.get("entryAllowed") or decimal_from_payload(situation.get("score")) >= MIN_ENTRY_SCORE)
    ][:selected_cap]
    orders = [
        futures_paper_action_payload(action)
        for action in cycle_payload.get("actions", [])
        if isinstance(action, dict)
    ]
    updated_at = cycle_payload.get("updatedAt") or status_payload.get("updatedAt") or datetime.now(timezone.utc).isoformat()
    universe_count = int_from_payload(
        cycle_payload.get("universeCount"),
        len(candidates) or len(settings.binance_futures_symbols),
    )
    evaluated_count = int_from_payload(cycle_payload.get("evaluatedCount"), len(situations))
    market_regime = cycle_payload.get("marketRegime") if isinstance(cycle_payload.get("marketRegime"), dict) else futures_market_regime(situations)
    default_strategy_side = (
        MAEUKNAM_STRATEGY_SIDE
        if settings.strategy_name == "maeuknam_cards"
        else ALEX_STRATEGY_SIDE
        if settings.strategy_name == "alex_method"
        else STRATEGY_SIDE
    )
    strategy_side = str(cycle_payload.get("strategySide") or status_payload.get("strategySide") or default_strategy_side)
    maeuknam_cards = strategy_side == MAEUKNAM_STRATEGY_SIDE
    alex_method = strategy_side == ALEX_STRATEGY_SIDE
    card_method = maeuknam_cards or alex_method
    leverage = str(
        cycle_payload.get("leverage")
        or status_payload.get("leverage")
        or decimal_to_str(futures_paper_leverage(card_method))
    )
    analysis_side = str(
        cycle_payload.get("analysisSide")
        or status_payload.get("analysisSide")
        or market_regime.get("analysisSide")
        or market_regime.get("tradeSide")
        or "FLAT"
    ).upper()
    execution_side = str(
        cycle_payload.get("executionSide")
        or status_payload.get("executionSide")
        or market_regime.get("executionSide")
        or "FLAT"
    ).upper()
    if not card_method and execution_side == "FLAT" and analysis_side in {"LONG", "SHORT"}:
        execution_side = "SHORT" if analysis_side == "LONG" else "LONG"
    plan = {
        "mode": (
            f"Binance Futures Maeuknam Cards {leverage}x"
            if maeuknam_cards
            else f"Binance Futures Alex Method {leverage}x"
            if alex_method
            else f"Binance Futures Contrarian {leverage}x"
        ),
        "modeLabel": "바이낸스 USD-M 선물 모의 분석",
        "scope": "binance_usdm_futures",
        "scopeLabel": "바이낸스 USD-M 선물 실시간 분석",
        "marketUnit": "USDT",
        "strategySide": strategy_side,
        "tradeSide": execution_side,
        "analysisSide": analysis_side,
        "executionSide": execution_side,
        "leverage": leverage,
        "evaluatedCount": evaluated_count,
        "universeCount": universe_count,
        "universeSource": cycle_payload.get("universeSource") or "configured_symbols_fallback",
        "tickerCount": int_from_payload(cycle_payload.get("tickerCount"), len(candidates)),
        "deepAnalysisCount": int_from_payload(cycle_payload.get("deepAnalysisCount"), 0),
        "selected": selected,
        "situations": situations,
        "orders": orders,
        "marketRegime": market_regime,
        "entryBlockReason": cycle_payload.get("entryBlockReason"),
        "maeuknamEntryPolicy": cycle_payload.get("maeuknamEntryPolicy") or {},
        "alexEntryPolicy": cycle_payload.get("alexEntryPolicy") or {},
        "message": cycle_payload.get("message", "바이낸스 USD-M 선물 후보를 실시간 분석 중입니다"),
    }
    investment_agency = build_investment_agency_report(plan, status_payload, cycle_payload)
    plan["investmentAgency"] = investment_agency
    return {
        "enabled": True,
        "intervalSeconds": settings.realtime_decision_interval_seconds,
        "watchTopN": universe_count,
        "scope": "binance_usdm_futures",
        "scopeLabel": "바이낸스 USD-M 선물 실시간 분석",
        "last": {
            "source": f"binance_futures_paper_{source}",
            "mode": plan["mode"],
            "updatedAt": updated_at,
            "message": plan["message"],
            "plan": plan,
            "orders": orders,
            "investmentAgency": investment_agency,
        },
        "investmentAgency": investment_agency,
        "recommended": {"recommendOnly": False, "markets": [], "excludedMarkets": []},
    }


def futures_candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    return [dict(candidate) for candidate in candidates if isinstance(candidate, dict)]


def futures_candidate_situation(
    candidate: dict[str, Any],
    position: dict[str, Any] | None,
    status_payload: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(candidate.get("symbol") or "")
    score = decimal_from_payload(candidate.get("score"))
    has_position = bool(position)
    analysis_side = str(candidate.get("analysisSide") or candidate.get("side") or DEFAULT_PAPER_SIDE).upper()
    execution_side = str(candidate.get("executionSide") or candidate.get("side") or DEFAULT_PAPER_SIDE).upper()
    side = execution_side
    is_contrarian = str(candidate.get("contrarian") or "").lower() == "true" or analysis_side != execution_side
    entry_allowed = str(candidate.get("entryAllowed") or "").lower() == "true"
    maeuknam_signal = candidate.get("maeuknamSignal") if isinstance(candidate.get("maeuknamSignal"), dict) else {}
    alex_signal = candidate.get("alexSignal") if isinstance(candidate.get("alexSignal"), dict) else {}
    is_maeuknam_card = bool(maeuknam_signal)
    is_alex_method = bool(alex_signal)
    is_card_method = is_maeuknam_card or is_alex_method
    action = "hold" if has_position else side.lower() if entry_allowed and (is_card_method or score >= MIN_ENTRY_SCORE) else "watch"
    leverage = str((position or {}).get("leverage") or status_payload.get("leverage") or decimal_to_str(DEFAULT_LEVERAGE))
    # Open-position PnL should follow the latest Binance ticker, not the last closed candle used for card scoring.
    current_price = str((position or {}).get("currentPrice") or candidate.get("price") or "0")
    margin_usdt = str((position or {}).get("marginUsdt") or "0")
    notional_usdt = str((position or {}).get("notionalUsdt") or "0")
    return_on_margin = str((position or {}).get("returnOnMarginPct") or "0")
    price_move = str((position or {}).get("priceMovePct") or "0")
    threshold_text = (
        "Maeuknam card confirmation gate"
        if is_maeuknam_card
        else "Alex method 0.5/liquidity/4-count gate"
        if is_alex_method
        else f"adaptive threshold {decimal_to_str(MIN_ENTRY_SCORE)}"
    )
    risk_reason = (
        "open Maeuknam card position under card exits"
        if has_position and is_maeuknam_card
        else "open Alex method position under method exits"
        if has_position and is_alex_method
        else "open futures position under ROE guard"
        if has_position
        else (
        f"analysis {analysis_side} passed; contrarian bet {execution_side}" if action in {"short", "long"} and is_contrarian else (
            f"Maeuknam card {side.lower()} confirmed" if action in {"short", "long"} and is_maeuknam_card else (
                f"Alex method {side.lower()} confirmed" if action in {"short", "long"} and is_alex_method else (
                f"{side.lower()} entry threshold passed" if action in {"short", "long"} else str(candidate.get("entryBlockReason") or f"below {threshold_text}")
            )
        )
        )
    )
    )
    return {
        "market": symbol,
        "symbol": symbol,
        "label": symbol,
        "exchange": "binance",
        "exchangeMode": "binance_futures_paper",
        "currency": "USDT",
        "quoteAsset": "USDT",
        "side": side,
        "analysisSide": analysis_side,
        "executionSide": execution_side,
        "contrarian": is_contrarian,
        "action": action,
        "score": str(candidate.get("score") or "0"),
        "currentPrice": current_price,
        "price": current_price,
        "trend5mPct": str(candidate.get("momentum5mPct") or "0"),
        "momentum5mPct": str(candidate.get("momentum5mPct") or "0"),
        "momentum15mPct": str(candidate.get("momentum15mPct") or "0"),
        "range15mPct": str(candidate.get("range15mPct") or "0"),
        "volumeRatio": str(candidate.get("volumeRatio") or "0"),
        "analysisDepth": str(candidate.get("analysisDepth") or ""),
        "priceChange24hPct": str(candidate.get("priceChange24hPct") or "0"),
        "range24hPct": str(candidate.get("range24hPct") or "0"),
        "quoteVolumeUsdt": str(candidate.get("quoteVolumeUsdt") or "0"),
        "tradeCount": str(candidate.get("tradeCount") or "0"),
        "universeSource": str(candidate.get("universeSource") or ""),
        "entryAllowed": entry_allowed,
        "entryBlockReason": str(candidate.get("entryBlockReason") or ""),
        "entryStage": str(candidate.get("entryStage") or ""),
        "confirmationCount": str(candidate.get("confirmationCount") or "0"),
        "closedCandleCount": str(candidate.get("closedCandleCount") or "0"),
        "latestCandleTimestamp": str(candidate.get("latestCandleTimestamp") or "0"),
        "timeframeContext": candidate.get("timeframeContext") or {},
        "targetMovePct": str(candidate.get("targetMovePct") or "0"),
        "feeSafetyMovePct": str(candidate.get("feeSafetyMovePct") or "0"),
        "cooldownKey": str(candidate.get("cooldownKey") or ""),
        "maeuknamSignal": maeuknam_signal,
        "alexSignal": alex_signal,
        "directionDiagnostics": candidate.get("directionDiagnostics") or {},
        "entryPrice": str((position or {}).get("entryPrice") or ""),
        "avgEntryPrice": str((position or {}).get("entryPrice") or ""),
        "targetSellPrice": str((position or {}).get("takeProfitPrice") or ""),
        "takeProfitPrice": str((position or {}).get("takeProfitPrice") or ""),
        "stopLossPrice": str((position or {}).get("stopLossPrice") or ""),
        "marginUsdt": margin_usdt,
        "notionalUsdt": notional_usdt,
        "currentValueKrw": notional_usdt,
        "currentValueUsdt": notional_usdt,
        "returnPct": return_on_margin,
        "returnOnMarginPct": return_on_margin,
        "priceMovePct": price_move,
        "leverage": leverage,
        "riskReason": risk_reason,
        "reason": str(candidate.get("reason") or ""),
        "tags": [
            "binance-usdm",
            "paper-futures",
            "maeuknam-card" if is_maeuknam_card else "alex-method" if is_alex_method else "adaptive-futures",
            str(candidate.get("analysisDepth") or "analysis"),
            f"analysis-{analysis_side.lower()}",
            f"{side.lower()}-{leverage}x",
        ],
    }


def futures_position_situation(position: dict[str, Any], status_payload: dict[str, Any]) -> dict[str, Any]:
    symbol = str(position.get("symbol") or "")
    score = abs(decimal_from_payload(position.get("returnOnMarginPct"))) / Decimal("100")
    return {
        "market": symbol,
        "symbol": symbol,
        "label": symbol,
        "exchange": "binance",
        "exchangeMode": "binance_futures_paper",
        "currency": "USDT",
        "quoteAsset": "USDT",
        "side": position.get("side") or status_payload.get("paperSide") or DEFAULT_PAPER_SIDE,
        "action": "hold",
        "score": decimal_to_str(score),
        "currentPrice": str(position.get("currentPrice") or "0"),
        "price": str(position.get("currentPrice") or "0"),
        "entryPrice": str(position.get("entryPrice") or ""),
        "avgEntryPrice": str(position.get("entryPrice") or ""),
        "targetSellPrice": str(position.get("takeProfitPrice") or ""),
        "takeProfitPrice": str(position.get("takeProfitPrice") or ""),
        "stopLossPrice": str(position.get("stopLossPrice") or ""),
        "marginUsdt": str(position.get("marginUsdt") or "0"),
        "notionalUsdt": str(position.get("notionalUsdt") or "0"),
        "currentValueKrw": str(position.get("notionalUsdt") or "0"),
        "currentValueUsdt": str(position.get("notionalUsdt") or "0"),
        "returnPct": str(position.get("returnOnMarginPct") or "0"),
        "returnOnMarginPct": str(position.get("returnOnMarginPct") or "0"),
        "priceMovePct": str(position.get("priceMovePct") or "0"),
        "leverage": str(position.get("leverage") or status_payload.get("leverage") or decimal_to_str(DEFAULT_LEVERAGE)),
        "riskReason": "open futures position under ROE guard",
        "reason": str(position.get("reason") or "position-only futures paper snapshot"),
        "tags": ["binance-usdm", "paper-futures", "open-position"],
    }


def futures_market_regime(situations: list[dict[str, Any]]) -> dict[str, Any]:
    if not situations:
        return {"label": "waiting", "tradeSide": "FLAT", "score": "0", "reason": "waiting for Binance USD-M futures analysis"}
    bearish_count = sum(1 for item in situations if futures_situation_direction_pct(item) < 0)
    bullish_count = sum(1 for item in situations if futures_situation_direction_pct(item) > 0)
    count = Decimal(len(situations))
    bearish_ratio = Decimal(bearish_count) / count if count > 0 else Decimal("0")
    bullish_ratio = Decimal(bullish_count) / count if count > 0 else Decimal("0")
    avg_5m = sum((futures_situation_direction_pct(item) for item in situations), Decimal("0")) / count
    avg_15m = sum((futures_situation_context_pct(item) for item in situations), Decimal("0")) / count
    if bearish_ratio >= Decimal("0.56") and avg_5m < Decimal("-0.20"):
        label = "short-favorable"
        trade_side = "SHORT"
    elif bullish_ratio >= Decimal("0.56") and avg_5m > Decimal("0.20"):
        label = "long-favorable"
        trade_side = "LONG"
    else:
        label = "flat"
        trade_side = "FLAT"
    return {
        "label": label,
        "tradeSide": trade_side,
        "score": decimal_to_str(max(bearish_ratio, bullish_ratio)),
        "bullishRatio": decimal_to_str(bullish_ratio),
        "bearishRatio": decimal_to_str(bearish_ratio),
        "reason": (
            f"binance-usdm symbols={len(situations)} bullish={decimal_to_str(bullish_ratio)} bearish={decimal_to_str(bearish_ratio)} "
            f"avg5m={decimal_to_str(avg_5m)}% avg15m={decimal_to_str(avg_15m)}%"
        ),
    }


def futures_situation_direction_pct(item: dict[str, Any]) -> Decimal:
    momentum = decimal_from_payload(item.get("momentum5mPct"))
    if momentum != 0:
        return momentum
    return decimal_from_payload(item.get("priceChange24hPct"))


def futures_situation_context_pct(item: dict[str, Any]) -> Decimal:
    momentum = decimal_from_payload(item.get("momentum15mPct"))
    if momentum != 0:
        return momentum
    return decimal_from_payload(item.get("priceChange24hPct"))


def futures_paper_action_payload(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("type") or "").upper()
    raw_side = str(action.get("side") or "").upper()
    if action_type in {"OPEN", "INCREASE"} and raw_side == "SHORT":
        side = "short"
    elif action_type in {"OPEN", "INCREASE"} and raw_side == "LONG":
        side = "long"
    elif action_type == "CLOSE" and raw_side == "SHORT":
        side = "cover"
    elif action_type == "CLOSE" and raw_side == "LONG":
        side = "sell"
    else:
        side = raw_side.lower()
    return {
        "market": action.get("symbol"),
        "symbol": action.get("symbol"),
        "type": action_type,
        "side": side,
        "price": action.get("price"),
        "quantity": action.get("quantity"),
        "marginUsdt": action.get("marginUsdt"),
        "notionalUsdt": action.get("notionalUsdt"),
        "pnlUsdt": action.get("pnlUsdt"),
        "returnOnMarginPct": action.get("returnOnMarginPct"),
        "analysisSide": action.get("analysisSide"),
        "executionSide": action.get("executionSide") or raw_side,
        "reason": action.get("reason"),
    }


def futures_paper_snapshot_payload(payload: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "cashKrw": payload.get("availableBalanceUsdt", "0"),
        "positionValueKrw": payload.get("totalNotionalUsdt") or payload.get("usedMarginUsdt", "0"),
        "equityKrw": payload.get("equityUsdt", "0"),
        "realizedPnlKrw": payload.get("realizedPnlUsdt", "0"),
        "feesPaidKrw": payload.get("feesPaidUsdt", "0"),
        "pricePnlKrw": payload.get("pricePnlUsdt", "0"),
        "grossRealizedPnlKrw": payload.get("grossRealizedPnlUsdt", "0"),
        "openFeesPaidKrw": payload.get("openFeesPaidUsdt", "0"),
        "closeFeesPaidKrw": payload.get("closeFeesPaidUsdt", "0"),
        "orderCount": payload.get("orderCount", 0),
        "openPositions": payload.get("openPositions", 0),
        "currency": "USDT",
        "metric": "equityUsdt",
        "source": f"binance_futures_paper_{source}",
        "walletBalanceUsdt": payload.get("walletBalanceUsdt", "0"),
        "availableBalanceUsdt": payload.get("availableBalanceUsdt", "0"),
        "usedMarginUsdt": payload.get("usedMarginUsdt", "0"),
        "totalNotionalUsdt": payload.get("totalNotionalUsdt", "0"),
        "equityUsdt": payload.get("equityUsdt", "0"),
        "unrealizedPnlUsdt": payload.get("unrealizedPnlUsdt", "0"),
        "realizedPnlUsdt": payload.get("realizedPnlUsdt", "0"),
        "pricePnlUsdt": payload.get("pricePnlUsdt", "0"),
        "grossRealizedPnlUsdt": payload.get("grossRealizedPnlUsdt", "0"),
        "openFeesPaidUsdt": payload.get("openFeesPaidUsdt", "0"),
        "closeFeesPaidUsdt": payload.get("closeFeesPaidUsdt", "0"),
        "feesPaidUsdt": payload.get("feesPaidUsdt", "0"),
    }


def is_futures_paper_snapshot(snapshot: dict[str, Any]) -> bool:
    payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else {}
    return str(payload.get("currency") or "").upper() == "USDT" or str(payload.get("source") or "").startswith(
        "binance_futures_paper"
    )


def record_futures_paper_snapshot(settings: TradingSettings, payload: dict[str, Any], source: str) -> None:
    if payload.get("error"):
        return
    try:
        SqliteStore(settings.database_file).append_portfolio_snapshot(futures_paper_snapshot_payload(payload, source))
    except Exception:
        pass


def binance_futures_account_summary(account: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    def clean_decimal(value: Any) -> str:
        text = str(value if value is not None else "").strip()
        return text if text else "0"

    summary = {
        "totalWalletBalance": clean_decimal(account.get("totalWalletBalance")),
        "availableBalance": clean_decimal(account.get("availableBalance")),
        "totalUnrealizedProfit": clean_decimal(account.get("totalUnrealizedProfit")),
        "totalMarginBalance": clean_decimal(account.get("totalMarginBalance")),
        "multiAssetsMargin": str(account.get("multiAssetsMargin", "")),
        "canTrade": str(account.get("canTrade", "")),
    }
    positions: list[dict[str, str]] = []
    for row in account.get("positions", []):
        if not isinstance(row, dict):
            continue
        amount = Decimal(str(row.get("positionAmt", "0") or "0"))
        unrealized = Decimal(str(row.get("unrealizedProfit", "0") or "0"))
        if amount == 0 and unrealized == 0:
            continue
        positions.append(
            {
                "symbol": str(row.get("symbol", "")),
                "positionAmt": decimal_to_str(amount),
                "entryPrice": str(row.get("entryPrice", "0")),
                "unrealizedProfit": decimal_to_str(unrealized),
                "leverage": str(row.get("leverage", "")),
                "positionSide": str(row.get("positionSide", "")),
            }
        )
    return summary, positions


def live_check_payload(settings: TradingSettings, market: str) -> dict[str, Any]:
    market = market.upper()
    if market not in settings.markets:
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 留덉폆留??좏깮?????덉뒿?덈떎: {market}")
        settings = replace(settings, market=market, markets=tuple(dict.fromkeys([*settings.markets, market])))

    live = live_runtime_payload(settings)
    payload: dict[str, Any] = {
        "ok": False,
        "market": market,
        "live": live,
        "account": None,
        "orderChance": None,
        "errors": [],
    }
    if not live["keyConfigured"]:
        payload["errors"].append("UPBIT_ACCESS_KEY?? UPBIT_SECRET_KEY媛? ?ㅼ젙?섏? ?딆븯?듬땲??")
        return payload

    client = make_client(settings)
    try:
        accounts = client.get_accounts()
        payload["account"] = summarize_accounts(accounts, settings)
    except Exception as exc:
        payload["errors"].append(f"怨꾩쥖 ?붽퀬 議고쉶 ?ㅽ뙣: {exc}")

    try:
        payload["orderChance"] = order_chance_payload(client.get_order_chance(market))
    except Exception as exc:
        payload["errors"].append(f"二쇰Ц 媛????뺣낫 議고쉶 ?ㅽ뙣: {exc}")

    payload["ok"] = not payload["errors"]
    return payload


def build_live_preview(settings: TradingSettings, market: str) -> dict[str, Any]:
    market = market.upper()
    if market not in settings.markets:
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 留덉폆留??좏깮?????덉뒿?덈떎: {market}")
        settings = replace(settings, market=market, markets=tuple(dict.fromkeys([*settings.markets, market])))

    live = live_runtime_payload(settings)
    if not live["keyConfigured"]:
        return {
            "ok": False,
            "market": market,
            "live": live,
            "message": "UPBIT_ACCESS_KEY?? UPBIT_SECRET_KEY媛? ?ㅼ젙?섏? ?딆븯?듬땲??",
        }

    client = make_client(settings)
    try:
        accounts = client.get_accounts()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"怨꾩쥖 ?붽퀬 議고쉶 ?ㅽ뙣: {exc}") from exc

    market_settings = settings_for_market(settings, market)
    candles = fetch_candles(client, market_settings, market)
    latest_price = candles[0].trade_price if candles else Decimal("0")
    state = live_portfolio_state(accounts, settings)
    signal = make_strategy(market_settings).evaluate(candles)
    risk_manager = PortfolioRiskManager(settings)
    signal = risk_manager.protective_signal(signal, state, latest_price)
    decision = risk_manager.evaluate(signal, state, latest_price)

    chance: dict[str, Any] | None = None
    chance_error: str | None = None
    try:
        chance = order_chance_payload(client.get_order_chance(market))
    except Exception as exc:
        chance_error = str(exc)

    return {
        "ok": True,
        "market": market,
        "mode": "live-preview",
        "price": decimal_to_str(latest_price),
        "live": live,
        "account": summarize_accounts(accounts, settings),
        "signal": signal_payload(signal),
        "risk": {
            "approved": decision.approved,
            "reason": decision.reason,
            "intent": intent_payload(decision.intent),
        },
        "orderBody": decision.intent.to_upbit_body() if decision.intent else None,
        "orderChance": chance,
        "orderChanceError": chance_error,
        "warning": "誘몃━蹂닿린??二쇰Ц???쒖텧?섏? ?딆뒿?덈떎. ?ㅺ굅?섎뒗 蹂꾨룄 ?좉툑怨??뺤씤 臾멸뎄媛? 紐⑤몢 留욎븘???⑸땲??",
    }


def intent_from_payload(payload: dict[str, Any]) -> OrderIntent:
    return OrderIntent(
        market=str(payload["market"]),
        side="bid" if payload.get("side") == "매수" else "ask",
        ord_type=str(payload["type"]),  # type: ignore[arg-type]
        price=Decimal(str(payload["price"])) if payload.get("price") is not None else None,
        volume=Decimal(str(payload["volume"])) if payload.get("volume") is not None else None,
        reason=str(payload.get("reason") or "web-live-execute"),
    )


def run_paper_scan(settings: TradingSettings) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, market in enumerate(settings.markets):
        try:
            results.append(run_paper_market_once(settings, market))
        except Exception as exc:
            results.append({"market": market, "ok": False, "message": f"?ㅼ틪 ?ㅽ뙣: {exc}"})
        if index < len(settings.markets) - 1:
            time.sleep(0.12)
    prices = {
        str(result.get("market")): Decimal(str(result.get("price", "0")))
        for result in results
        if result.get("market") and result.get("price") is not None
    }
    order_count = sum(1 for result in results if result.get("order"))
    error_count = sum(1 for result in results if result.get("ok") is False)
    log_event(
        settings,
        "paper_scan",
        {
            "markets": len(results),
            "orders": order_count,
            "errors": error_count,
        },
    )
    record_portfolio_snapshot(settings, prices, "paper_scan")
    return results


def run_dynamic_allocation(
    settings: TradingSettings,
    execute_orders: bool,
    source: str,
) -> dict[str, Any]:
    client = make_client(settings)
    store = JsonPortfolioStateStore(settings.state_file)
    state = store.load(settings.paper_cash_krw)
    market_preferences = load_market_preferences(settings)
    candidate_markets = recommended_investment_markets(settings, state, market_preferences, "allocation")
    plan = build_dynamic_allocation_plan(settings, client, state, markets=candidate_markets, pause_seconds=0.06)
    results: list[dict[str, Any]] = []
    if execute_orders:
        results = execute_allocation_plan(plan, state, settings.fee_rate, settings)
        store.save(state)
        for result in results:
            if result.get("ok"):
                log_event(
                    settings,
                    "paper_order",
                    {
                        "market": result.get("market"),
                        "ok": result.get("ok"),
                        "message": result.get("message"),
                        "raw": result.get("raw", {}),
                    },
                )
        prices = allocation_prices_from_plan(plan)
        record_portfolio_snapshot(settings, prices, "dynamic_allocation")

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "source": source,
        "executed": execute_orders,
        "plan": plan.to_dict(),
        "orders": results,
        "message": plan.message,
        "updatedAt": now,
        "recommended": recommendation_payload(settings, market_preferences),
    }
    if execute_orders:
        payload["executedAt"] = now
    else:
        payload["previewedAt"] = now
    save_allocation_runtime(settings, payload)
    if execute_orders:
        log_event(
            settings,
            "dynamic_allocation",
            {
                "source": source,
                "mode": plan.mode,
                "scannedCount": plan.scanned_count,
                "selectedCount": plan.selected_count,
                "orderCount": len(results),
                "message": plan.message,
            },
        )
    return payload


def allocation_prices_from_plan(plan: Any) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for candidate in list(plan.candidates) + list(plan.selected):
        prices[candidate.market] = candidate.current_price
    return prices


def allocation_runtime_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "allocation_runtime.json"


def load_allocation_runtime(settings: TradingSettings) -> dict[str, Any]:
    path = allocation_runtime_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_allocation_runtime(settings: TradingSettings, payload: dict[str, Any]) -> None:
    path = allocation_runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def allocation_status_payload(settings: TradingSettings) -> dict[str, Any]:
    runtime = load_allocation_runtime(settings)
    last_run_at = str(runtime.get("executedAt") or "")
    next_run_in = allocation_next_run_seconds(settings, last_run_at)
    return {
        "enabled": settings.dynamic_allocation_enabled,
        "intervalSeconds": settings.allocation_interval_seconds,
        "last": runtime,
        "nextRunInSeconds": next_run_in,
        "due": next_run_in == 0,
        "nextRunMessage": "Ready now" if next_run_in == 0 else f"{next_run_in // 60} minutes until next run",
        "recommended": recommendation_payload(settings),
    }


def is_allocation_due(settings: TradingSettings) -> bool:
    if not settings.dynamic_allocation_enabled:
        return False
    runtime = load_allocation_runtime(settings)
    return allocation_next_run_seconds(settings, str(runtime.get("executedAt") or "")) == 0


def allocation_next_run_seconds(settings: TradingSettings, last_run_at: str) -> int:
    if not last_run_at:
        return 0
    try:
        parsed = datetime.fromisoformat(last_run_at)
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return max(0, int(settings.allocation_interval_seconds - elapsed))


def run_realtime_decision(
    settings: TradingSettings,
    runtime: dict[str, Any],
    execute_orders: bool,
    source: str,
) -> dict[str, Any]:
    client = make_client(settings)
    store = JsonPortfolioStateStore(settings.state_file)
    state = store.load(settings.paper_cash_krw)
    previous_runtime = load_realtime_decision_runtime(settings)
    market_preferences = load_market_preferences(settings)
    candidate_markets = realtime_decision_candidate_markets(settings, client, state, market_preferences)
    plan = build_realtime_decision_plan(
        settings=settings,
        client=client,
        state=state,
        realtime=runtime.get("realtime", {}),
        previous_runtime=previous_runtime,
        candidate_markets=candidate_markets,
    )
    results: list[dict[str, Any]] = []
    if execute_orders:
        results = execute_realtime_plan(plan, state, settings.fee_rate, settings)
        store.save(state)
        for result in results:
            if result.get("ok"):
                log_event(
                    settings,
                    "paper_order",
                    {
                        "market": result.get("market"),
                        "ok": result.get("ok"),
                        "message": result.get("message"),
                        "raw": result.get("raw", {}),
                    },
                )
        prices = realtime_prices_from_plan(plan)
        record_portfolio_snapshot(settings, prices, "realtime_decision")

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "source": source,
        "executed": execute_orders,
        "plan": plan.to_dict(),
        "orders": results,
        "message": plan.message,
        "updatedAt": now,
        "history": plan.history,
        "candleCache": plan.candle_cache,
        "recommended": recommendation_payload(settings, market_preferences),
    }
    if execute_orders:
        payload["executedAt"] = now
    else:
        payload["previewedAt"] = now
    save_realtime_decision_runtime(settings, payload)
    if execute_orders:
        log_event(
            settings,
            "realtime_decision",
            {
                "source": source,
                "mode": plan.mode,
                "universeCount": plan.universe_count,
                "evaluatedCount": plan.evaluated_count,
                "selectedCount": len(plan.selected),
                "orderCount": len(results),
                "message": plan.message,
            },
        )
    return public_realtime_decision_payload(payload)


def realtime_prices_from_plan(plan: Any) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for situation in list(plan.situations) + list(plan.selected):
        prices[situation.market] = situation.current_price
    for order in plan.orders:
        prices[order.market] = order.current_price
    return prices


def run_ai_pm_analysis(settings: TradingSettings, runtime: dict[str, Any], source: str) -> dict[str, Any]:
    status = build_status(settings, runtime)
    live_check: dict[str, Any] | None = None
    if status.get("live", {}).get("keyConfigured"):
        try:
            live_check = live_check_payload(settings, settings.market)
        except Exception as exc:
            live_check = {"ok": False, "errors": [str(exc)]}
    snapshot = build_ai_pm_snapshot(settings, status, live_check)
    payload = request_ai_pm_report(settings, snapshot)
    log_event(
        settings,
        "ai_pm_analysis",
        {
            "source": source,
            "ok": payload.get("ok"),
            "state": payload.get("state"),
            "headline": payload.get("headline"),
        },
    )
    return payload


def run_ai_pm_chat(settings: TradingSettings, runtime: dict[str, Any], message: str) -> dict[str, Any]:
    history = load_ai_pm_chat(settings)
    now = datetime.now(timezone.utc).isoformat()
    user_entry = {
        "role": "user",
        "content": message,
        "createdAt": now,
    }
    status = build_status(settings, runtime)
    live_check: dict[str, Any] | None = None
    if status.get("live", {}).get("keyConfigured"):
        try:
            live_check = live_check_payload(settings, settings.market)
        except Exception as exc:
            live_check = {"ok": False, "errors": [str(exc)]}
    snapshot = build_ai_pm_snapshot(settings, status, live_check)
    reply_payload = request_ai_pm_chat(settings, snapshot, [*history, user_entry], message)
    assistant_entry = reply_payload.get("message")
    updated_messages = [*history, user_entry]
    if isinstance(assistant_entry, dict):
        updated_messages.append(assistant_entry)
    save_ai_pm_chat(settings, updated_messages)
    log_event(
        settings,
        "ai_pm_chat",
        {
            "ok": reply_payload.get("ok"),
            "state": reply_payload.get("state"),
            "messageLength": len(message),
        },
    )
    return {
        **reply_payload,
        "messages": load_ai_pm_chat(settings),
    }


def run_market_intel_collection(settings: TradingSettings, runtime: dict[str, Any], source: str) -> dict[str, Any]:
    status = build_status(settings, runtime)
    payload = collect_market_intel(settings, status)
    log_event(
        settings,
        "market_intel",
        {
            "source": source,
            "ok": payload.get("ok"),
            "items": len(payload.get("items") or []),
            "coinAnalyses": len(payload.get("coinAnalyses") or []),
            "errors": len(payload.get("errors") or []),
        },
    )
    return payload


def build_pm_scheduler(settings: TradingSettings, status: dict[str, Any]) -> dict[str, Any]:
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    start = max(settings.goal_start_krw, Decimal("1"))
    target = max(settings.goal_target_krw, start)
    days = max(settings.goal_days, 1)
    equity = max(decimal_from_payload(status.get("account", {}).get("equityKrw"), start), Decimal("1"))
    stretch_target = target * Decimal("1.08")
    base_multiplier = target / start
    stretch_multiplier = stretch_target / start
    daily_rate = safe_power(float(base_multiplier), 1 / days) - 1
    stretch_daily_rate = safe_power(float(stretch_multiplier), 1 / days) - 1
    recovery_hourly_rate = safe_power(float(stretch_target / equity), 1 / max(days * 24, 1)) - 1
    today_required = start * Decimal(str(safe_power(float(stretch_multiplier), 1 / days)))
    pace_pct = equity / today_required * Decimal("100") if today_required > 0 else Decimal("0")
    gap_krw = max(today_required - equity, Decimal("0"))
    live = status.get("live", {}) if isinstance(status.get("live"), dict) else {}
    pm = status.get("pm", {}) if isinstance(status.get("pm"), dict) else {}
    plan = (status.get("realtimeDecision", {}).get("last", {}) or {}).get("plan", {}) if isinstance(status.get("realtimeDecision"), dict) else {}
    selected_count = len(plan.get("selected", [])) if isinstance(plan.get("selected"), list) else 0
    order_count = len(plan.get("orders", [])) if isinstance(plan.get("orders"), list) else 0
    engine_pressure = realtime_goal_pace_pressure(settings, equity)

    return {
        "updatedAt": now.isoformat(),
        "mode": "live-ready" if live.get("armed") and live.get("webArmed") else "paper-guarded",
        "state": pm_scheduler_state(pace_pct, pm),
        "headline": "30일 1억 목표 페이스 관리",
        "narrative": (
            "수익 보장을 약속하지 않습니다. 목표를 달성해야 할 기준 페이스로 환산해 "
            "실시간 후보, 주문 후보, 손절/회전 조건을 다시 계산하고 PM 연결이 끊겨도 규칙 기반 백업 페이스를 이어갑니다."
        ),
        "target": {
            "startKrw": decimal_to_str(start),
            "targetKrw": decimal_to_str(target),
            "stretchTargetKrw": decimal_to_str(stretch_target),
            "days": days,
            "equityKrw": decimal_to_str(equity),
            "todayRequiredKrw": decimal_to_str(today_required),
            "gapKrw": decimal_to_str(gap_krw),
            "dailyRequiredPct": decimal_to_str(Decimal(str(daily_rate * 100))),
            "stretchDailyRequiredPct": decimal_to_str(Decimal(str(stretch_daily_rate * 100))),
            "hourlyRecoveryPct": decimal_to_str(Decimal(str(recovery_hourly_rate * 100))),
            "pacePct": decimal_to_str(pace_pct),
        },
        "live": {
            "keyConfigured": bool(live.get("keyConfigured")),
            "armed": bool(live.get("armed")),
            "webArmed": bool(live.get("webArmed")),
            "managementReady": bool(live.get("keyConfigured")),
            "orderBoundary": "실거래 주문은 별도 잠금과 확인 문구가 켜진 경우에만 엔진이 실행합니다.",
        },
        "pm": {
            "connected": bool(pm.get("connected")),
            "enabled": bool(pm.get("enabled")),
            "model": pm.get("model"),
            "fallbackArmed": not bool(pm.get("connected")),
        },
        "pressure": {
            "selectedCount": selected_count,
            "orderCandidateCount": order_count,
            "requiredAction": pm_required_action(pace_pct, selected_count, order_count),
            "engineApplied": bool(engine_pressure.enabled),
            "level": engine_pressure.level,
            "label": engine_pressure.label,
            "entryScoreAdjustment": decimal_to_str(engine_pressure.entry_score_adjustment),
            "deployMultiplier": decimal_to_str(engine_pressure.deploy_multiplier),
            "maxOrderMultiplier": decimal_to_str(engine_pressure.max_order_multiplier),
            "positionMultiplier": decimal_to_str(engine_pressure.position_multiplier),
            "reason": engine_pressure.reason,
        },
        "days": build_pm_calendar_days(now, start, target, stretch_target, equity, days),
        "hours": build_pm_hourly_slots(now, equity, stretch_target, days, recovery_hourly_rate, selected_count, order_count),
        "fallback": pm_fallback_algorithm(settings, pace_pct, selected_count, order_count),
    }


def build_pm_calendar_days(
    now: datetime,
    start: Decimal,
    target: Decimal,
    stretch_target: Decimal,
    equity: Decimal,
    days: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous_stretch = start
    for index in range(1, days + 1):
        date = now.date() + timedelta(days=index - 1)
        base_equity = start * Decimal(str(safe_power(float(target / start), index / days)))
        stretch_equity = start * Decimal(str(safe_power(float(stretch_target / start), index / days)))
        daily_gain = (stretch_equity / previous_stretch - Decimal("1")) * Decimal("100") if previous_stretch > 0 else Decimal("0")
        day_gap = max(stretch_equity - equity, Decimal("0")) if index == 1 else Decimal("0")
        rows.append(
            {
                "day": index,
                "date": date.isoformat(),
                "status": "today" if index == 1 else "upcoming",
                "stage": pm_scheduler_stage(index, days),
                "targetKrw": decimal_to_str(base_equity),
                "stretchTargetKrw": decimal_to_str(stretch_equity),
                "requiredGainPct": decimal_to_str(daily_gain),
                "gapKrw": decimal_to_str(day_gap),
                "pmBrief": pm_day_brief(index, days),
                "fallbackRule": pm_day_fallback_rule(index, days),
            }
        )
        previous_stretch = stretch_equity
    return rows


def build_pm_hourly_slots(
    now: datetime,
    equity: Decimal,
    stretch_target: Decimal,
    days: int,
    hourly_rate: float,
    selected_count: int,
    order_count: int,
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for index in range(1, 25):
        due = now + timedelta(hours=index)
        required = equity * Decimal(str(safe_power(1 + hourly_rate, index)))
        slots.append(
            {
                "hour": index,
                "time": due.isoformat(),
                "requiredEquityKrw": decimal_to_str(min(required, stretch_target)),
                "requiredGainPct": decimal_to_str(Decimal(str(hourly_rate * 100))),
                "focus": pm_hour_focus(index, selected_count, order_count),
                "trigger": pm_hour_trigger(index),
                "fallbackRule": pm_hour_fallback(index),
            }
        )
    return slots


def pm_scheduler_state(pace_pct: Decimal, pm: dict[str, Any]) -> dict[str, Any]:
    if pace_pct >= Decimal("108"):
        label = "목표 초과 페이스"
        class_name = "ok"
    elif pace_pct >= Decimal("100"):
        label = "필수 페이스 충족"
        class_name = "ok"
    elif pace_pct >= Decimal("90"):
        label = "추격 필요"
        class_name = "warning"
    else:
        label = "강제 복구 모드"
        class_name = "critical"
    detail = "AI PM connected" if pm.get("connected") else "AI PM local fallback"
    return {"label": label, "className": class_name, "detail": detail}


def pm_required_action(pace_pct: Decimal, selected_count: int, order_count: int) -> str:
    if order_count:
        return f"주문 후보 {order_count}개를 손절가/목표가와 함께 즉시 검증"
    if selected_count:
        return f"진입 후보 {selected_count}개를 가격/거래량/기대추세로 압축"
    if pace_pct < Decimal("90"):
        return "후보가 없으면 현금 방어 후 다음 스캔 민감도를 한 단계 높여 재평가"
    return "필수 페이스 유지, 무리한 진입보다 다음 후보 대기"


def pm_scheduler_stage(day: int, days: int) -> str:
    ratio = day / max(days, 1)
    if ratio <= 0.1:
        return "초기 연결/검증"
    if ratio <= 0.35:
        return "가속 진입"
    if ratio <= 0.7:
        return "회전/복리"
    if ratio <= 0.9:
        return "부족분 복구"
    return "마감 초과 달성"


def pm_day_brief(day: int, days: int) -> str:
    stage = pm_scheduler_stage(day, days)
    if stage == "초기 연결/검증":
        return "실거래 잠금과 실시간 스트림, 손절/목표가 계산을 검증하고 페이퍼 계좌와 실거래 계좌를 분리 감시합니다."
    if stage == "가속 진입":
        return "상위 후보만 집중하고 실패 후보는 빠르게 배제해 목표 페이스보다 빠른 누적 수익 곡선을 노립니다."
    if stage == "회전/복리":
        return "보유 종목보다 강한 후보가 나오면 회전 기준을 적용하고, 목표가 도달 종목은 보호 이익으로 전환합니다."
    if stage == "부족분 복구":
        return "부족분을 시간당 필요 수익률로 재계산해 진입 빈도와 후보 기준을 조정하되 손절 기준은 유지합니다."
    return "목표 초과분을 지키기 위해 변동성 축소, 부분 청산, 추격 금지 전략으로 관리합니다."


def pm_day_fallback_rule(day: int, days: int) -> str:
    stage = pm_scheduler_stage(day, days)
    if stage == "초기 연결/검증":
        return "PM 미응답 시 실거래 금지, 페이퍼 분석만 유지하고 전체 후보 스캔 성공률을 우선 복구"
    if stage == "가속 진입":
        return "상위 점수/거래량/기대추세 3조건 동시 충족 종목만 허용, 조건 이탈 시 즉시 제외"
    if stage == "회전/복리":
        return "보유 수익률이 목표 페이스 아래로 꺾이면 더 강한 후보와 교체 검토"
    if stage == "부족분 복구":
        return "부족분은 포지션 크기가 아니라 후보 점수 기준 완화 순서로만 보정"
    return "목표 초과분 보호를 우선하고 손실 회복 전까지 후보 진입 차단"


def pm_hour_focus(hour: int, selected_count: int, order_count: int) -> str:
    if hour % 6 == 0:
        return "위험 감사: 손절가, 슬리피지, API 오류, 보유 편중 확인"
    if hour % 4 == 0:
        return "회전 판단: 보유 종목과 신규 후보 상대 우위 비교"
    if order_count:
        return "주문 후보 정밀 검증: 가격 이탈, 미끄러짐, 목표가 대비 손익비"
    if selected_count:
        return "진입 후보 압축: 거래량, 확산, 후보 우선순위 갱신"
    return "전체 후보 재스캔, 강한 후보가 나올 때까지 현금 방어"


def pm_hour_trigger(hour: int) -> str:
    if hour % 6 == 0:
        return "2회 연속 약세 또는 슬리피지 접근 시 방어 모드"
    if hour % 4 == 0:
        return "신규 후보 점수가 보유 종목보다 높으면 회전 후보 등록"
    if hour % 3 == 0:
        return "거래량 1.2배 이상과 1/5분 추세 동시 작전 확인"
    return "현재 페이스 대비 부족분과 후보 점수를 재계산"


def pm_hour_fallback(hour: int) -> str:
    if hour % 6 == 0:
        return "PM 응답 없음: 모든 신규 진입 정지 후 리스크 로그만 생성"
    if hour % 4 == 0:
        return "PM 응답 없음: 보유 종목은 손절/목표가 기계 규칙만 적용"
    return "PM 응답 없음: 전체 스캔 점수와 후보표 기준으로 페이퍼 검증 우선"


def pm_fallback_algorithm(settings: TradingSettings, pace_pct: Decimal, selected_count: int, order_count: int) -> list[dict[str, Any]]:
    pressure = "high" if pace_pct < Decimal("90") else "normal"
    return [
        {
            "title": "1. PM 연결 감시",
            "body": "AI PM 응답 실패가 2회 연속 발생하거나 120초 이상 지연되면 fallback_mode=rules로 전환합니다.",
        },
        {
            "title": "2. 전체 KRW 후보 재평가",
            "body": "추천 코인 여부와 무관하게 전체 KRW 종목을 점수, 거래대금, 1/5/30분 추세, 가격 위험으로 정렬합니다.",
        },
        {
            "title": "3. 목표 페이스 보정",
            "body": f"현재 압력은 {pressure}입니다. 부족분을 시간당 필요 수익률로 재계산하고 후보 기준과 검토 빈도로 보정합니다.",
        },
        {
            "title": "4. 진입/회전/손절 이중장치",
            "body": f"진입 후보 {selected_count}개, 주문 후보 {order_count}개를 기준으로 보유 종목보다 강한 후보만 회전을 검토하고 손절 기준은 유지합니다.",
        },
        {
            "title": "5. 실거래 보호선",
            "body": "실거래 키가 있어도 LIVE_TRADING_ENABLED, WEB_LIVE_TRADING_ENABLED, 확인 문구가 모두 맞지 않으면 주문은 실행하지 않습니다.",
        },
    ]


def decimal_from_payload(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return default


def int_from_payload(value: Any, default: int = 0) -> int:
    try:
        return int(Decimal(str(value)))
    except Exception:
        return default


def format_ops_krw_amount(value: Any) -> str:
    amount = decimal_from_payload(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(amount):,}"


def format_ops_coin_price(value: Any) -> str:
    amount = decimal_from_payload(value)
    absolute = abs(amount)
    if absolute >= Decimal("100"):
        unit = Decimal("1")
    elif absolute >= Decimal("10"):
        unit = Decimal("0.01")
    elif absolute >= Decimal("1"):
        unit = Decimal("0.001")
    elif absolute >= Decimal("0.1"):
        unit = Decimal("0.0001")
    else:
        unit = Decimal("0.000001")
    rounded = amount.quantize(unit, rounding=ROUND_HALF_UP)
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    integer, dot, fraction = text.partition(".")
    sign = "-" if integer.startswith("-") else ""
    unsigned_integer = integer[1:] if sign else integer
    if unsigned_integer.isdigit():
        integer = f"{sign}{int(unsigned_integer):,}"
    return f"{integer}{dot}{fraction}" if dot and fraction else integer


def safe_power(base: float, exponent: float) -> float:
    if not math.isfinite(base) or base <= 0:
        return 1.0
    try:
        result = math.pow(base, exponent)
    except (OverflowError, ValueError):
        return 1.0
    return result if math.isfinite(result) else 1.0


def realtime_decision_runtime_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "realtime_runtime.json"


def load_realtime_decision_runtime(settings: TradingSettings) -> dict[str, Any]:
    path = realtime_decision_runtime_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_realtime_decision_runtime(settings: TradingSettings, payload: dict[str, Any]) -> None:
    path = realtime_decision_runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def public_realtime_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    public = dict(payload)
    public.pop("history", None)
    public.pop("candleCache", None)
    return public


def realtime_decision_status_payload(settings: TradingSettings) -> dict[str, Any]:
    runtime = load_realtime_decision_runtime(settings)
    return {
        "enabled": settings.realtime_decision_enabled,
        "intervalSeconds": settings.realtime_decision_interval_seconds,
        "watchTopN": settings.realtime_watch_top_n,
        "scope": "all_krw_markets",
        "scopeLabel": "?꾩껜 KRW ?ㅼ떆媛?遺꾩꽍",
        "last": public_realtime_decision_payload(runtime) if runtime else {},
        "recommended": recommendation_payload(settings),
    }


def ops_watch_payload(
    settings: TradingSettings,
    runtime: dict[str, Any],
    account: dict[str, Any],
    live: dict[str, Any],
    markets: list[dict[str, Any]],
    realtime_decision: dict[str, Any],
    runtime_errors: list[str],
) -> dict[str, Any]:
    last = realtime_decision.get("last", {}) if isinstance(realtime_decision.get("last"), dict) else {}
    plan = last.get("plan", {}) if isinstance(last.get("plan"), dict) else {}
    regime = plan.get("marketRegime", {}) if isinstance(plan.get("marketRegime"), dict) else {}
    watch_markets = ops_plan_rows(plan) if ops_is_futures_plan(plan) else markets
    risk_items = [
        ops_api_429_watch(runtime, watch_markets, plan, runtime_errors),
        ops_positive_ratio_watch(settings, regime),
    ]
    stop_items = ops_stop_loss_watches(watch_markets)
    candidate_items = ops_candidate_watches(settings, plan)
    operation_items = ops_operation_rules(settings, watch_markets, plan, account, live)
    all_levels = [
        *(item.get("level", "waiting") for item in risk_items),
        *(item.get("level", "waiting") for item in stop_items),
        *(item.get("level", "waiting") for item in candidate_items),
        *(item.get("level", "waiting") for item in operation_items),
    ]
    state_level = highest_ops_level(all_levels)
    held_count = sum(1 for row in watch_markets if ops_position_value(row) > 0)
    buy_orders = sum(1 for order in plan_orders(plan, last) if ops_order_side(order) == "buy")
    sell_orders = sum(1 for order in plan_orders(plan, last) if ops_order_side(order) == "sell")
    lock = ops_regime_blocks_entries(settings, regime)
    label = "즉시 개입 필요" if state_level == "critical" else "방어 관제" if lock else "운영 감시"
    detail = f"보유 {held_count}개 · 매수후보 {buy_orders}개 · 매도후보 {sell_orders}개 · 신규진입 {'잠금' if lock else '허용'}"
    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "state": {"label": label, "className": state_level, "detail": detail},
        "risk": risk_items,
        "triggers": stop_items,
        "candidates": candidate_items,
        "operations": operation_items,
        "regime": regime,
        "positiveRatioTarget": decimal_to_str(OPS_POSITIVE_RATIO_RECOVERY_TARGET),
    }


def ops_plan_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ("selected", "situations"):
        items = plan.get(key, []) if isinstance(plan.get(key), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            market = str(item.get("market") or item.get("symbol") or "")
            if not market or market in seen:
                continue
            seen.add(market)
            rows.append(item)
    return rows


def ops_is_futures_row(row: dict[str, Any]) -> bool:
    return (
        str(row.get("exchangeMode") or "") == "binance_futures_paper"
        or str(row.get("currency") or "").upper() == "USDT"
        or str(row.get("market") or row.get("symbol") or "").upper().endswith("USDT")
    )


def ops_is_futures_plan(plan: dict[str, Any]) -> bool:
    return str(plan.get("scope") or "") == "binance_usdm_futures" or any(
        ops_is_futures_row(row) for row in ops_plan_rows(plan)
    )


def ops_position_value(row: dict[str, Any]) -> Decimal:
    if ops_is_futures_row(row):
        return decimal_from_payload(row.get("currentValueUsdt") or row.get("notionalUsdt") or row.get("marginUsdt"))
    return decimal_from_payload(row.get("positionValueKrw"))


def ops_return_pct(row: dict[str, Any]) -> Decimal:
    if ops_is_futures_row(row):
        return decimal_from_payload(row.get("returnOnMarginPct") or row.get("returnPct"))
    return decimal_from_payload(row.get("returnPct"))


def ops_api_429_watch(
    runtime: dict[str, Any],
    markets: list[dict[str, Any]],
    plan: dict[str, Any],
    runtime_errors: list[str],
) -> dict[str, Any]:
    error_texts = ops_error_texts(runtime, plan, runtime_errors)
    rate_limit_errors = [text for text in error_texts if api_error_text_is_429(text)]
    futures_mode = ops_is_futures_plan(plan)
    priced_count = sum(1 for row in markets if decimal_from_payload(row.get("currentPrice") or row.get("price")) > 0)
    if rate_limit_errors:
        return {
            "key": "api429",
            "level": "critical",
            "title": "API 429 백오프 확인",
            "value": f"{len(rate_limit_errors)}건",
            "body": f"최근 429/요청초과 오류가 감지되었습니다. 백오프 후 가격 갱신이 정상화되는지 확인해야 합니다. {rate_limit_errors[0]}",
        }
    if futures_mode and priced_count:
        symbols = ", ".join(str(row.get("symbol") or row.get("market") or "") for row in markets[:3])
        return {
            "key": "api429",
            "level": "ok",
            "title": "Binance 가격 갱신",
            "value": f"{priced_count}개",
            "body": f"Binance USD-M 선물 후보 {symbols} 가격과 매억남 카드 판단이 갱신되고 있습니다.",
        }
    if priced_count:
        realtime = runtime.get("realtime", {}) if isinstance(runtime.get("realtime"), dict) else {}
        source = "WebSocket+REST" if realtime.get("connected") else "REST/罹먯떆"
        return {
            "key": "api429",
            "level": "ok",
            "title": "API 429 ?댁냼",
            "value": f"{priced_count}媛?媛?寃?",
            "body": f"?꾩옱 429 ?ㅻ쪟 ?놁씠 {priced_count}媛?醫낅ぉ 媛?寃⑹씠 {source} 寃쎈줈濡?媛깆떊?섍퀬 ?덉뒿?덈떎.",
        }
    return {
        "key": "api429",
        "level": "warning",
        "title": "媛?寃?媛깆떊 ?뺤씤 ?꾩슂",
        "value": "媛?寃??놁쓬",
        "body": "429??蹂댁씠吏? ?딆?留??꾩옱媛?媛? 鍮꾩뼱 ?덉뒿?덈떎. ?ㅼ쓬 諛깆삤???ъ“???ъ씠?댁쓣 ?뺤씤?댁빞 ?⑸땲??",
    }


def ops_positive_ratio_watch(settings: TradingSettings, regime: dict[str, Any]) -> dict[str, Any]:
    positive_ratio = decimal_from_payload(regime.get("positiveRatio"), Decimal("-1"))
    label = str(regime.get("label") or "unknown")
    if label.startswith("maeuknam_"):
        trade_side = str(regime.get("tradeSide") or "FLAT")
        level = "ok" if trade_side in {"LONG", "SHORT"} else "waiting"
        return {
            "key": "positiveRatio",
            "level": level,
            "title": "매억남 카드 게이트",
            "value": trade_side,
            "body": str(regime.get("reason") or "BTCUSDT 매억남 카드 조건을 확인하고 있습니다."),
        }
    if positive_ratio < 0:
        return {
            "key": "positiveRatio",
            "level": "waiting",
            "title": "?쒖옣 positive ratio",
            "value": "??湲?",
            "body": "?꾩쭅 ?쒖옣 ?덉쭚 ?쒕낯??遺?議깊빀?덈떎. ?꾩껜 KRW 罹붾뱾 ?섏쭛 ??0.25 ?뚮났 ?щ?瑜??쒖떆?⑸땲??",
        }
    level = "ok" if positive_ratio >= OPS_POSITIVE_RATIO_RECOVERY_TARGET else "critical"
    min_entry_ratio = settings.risk_regime_min_positive_ratio
    body = (
        f"?꾩옱 ?곸듅 醫낅ぉ 鍮꾩쑉?? {positive_ratio:.2f}?낅땲?? ?④린 ?뚮났 湲곗??? "
        f"{OPS_POSITIVE_RATIO_RECOVERY_TARGET:.2f}, ?좉퇋 吏꾩엯 ?ш???湲곗??? {min_entry_ratio:.2f}?낅땲??"
    )
    if label in {"weak", "risk-off"}:
        body = f"{body} ?꾩옱 ?덉쭚?? {label}???좉퇋 ?ъ??섏? 湲덉??섍퀬 蹂댁쑀 由ъ뒪?щ쭔 以꾩엯?덈떎."
    return {
        "key": "positiveRatio",
        "level": level,
        "title": "?쒖옣 positive ratio",
        "value": f"{positive_ratio:.2f}",
        "body": body,
    }


def ops_stop_loss_watches(markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    futures_mode = any(ops_is_futures_row(row) for row in markets)
    for row in markets:
        value = ops_position_value(row)
        if value <= 0:
            continue
        market = str(row.get("market") or "")
        price = decimal_from_payload(row.get("currentPrice") or row.get("price"))
        stop = decimal_from_payload(row.get("stopLossPrice"))
        return_pct = ops_return_pct(row)
        symbol = market_symbol(market)
        if ops_is_futures_row(row):
            side = str(row.get("side") or "").upper()
            if side == "SHORT":
                distance_pct = ((stop - price) / price * Decimal("100")) if price > 0 and stop > 0 else Decimal("999")
            else:
                distance_pct = ((price - stop) / price * Decimal("100")) if price > 0 and stop > 0 else Decimal("999")
            if price > 0 and stop > 0 and distance_pct <= 0:
                level = "critical"
                title = f"{symbol} {side} 손절선 도달"
            elif distance_pct <= OPS_STOP_CRITICAL_DISTANCE_PCT:
                level = "critical"
                title = f"{symbol} {side} 손절선 1% 이내"
            elif distance_pct <= OPS_STOP_WARNING_DISTANCE_PCT:
                level = "warning"
                title = f"{symbol} {side} 손절선 근접"
            elif return_pct < 0:
                level = "waiting"
                title = f"{symbol} {side} 손절 감시"
            else:
                level = "ok"
                title = f"{symbol} {side} 방어선 여유"
            rows.append(
                {
                    "key": f"stop:{market}",
                    "market": market,
                    "symbol": symbol,
                    "level": level,
                    "title": title,
                    "value": f"{distance_pct:.2f}%",
                    "body": (
                        f"현재가 {format_ops_coin_price(price)} USDT, 손절선 {format_ops_coin_price(stop)} USDT, "
                        f"손절선까지 {distance_pct:.2f}% 여유, ROE {return_pct:.2f}%입니다."
                    ),
                    "distancePct": decimal_to_str(distance_pct),
                    "returnPct": decimal_to_str(return_pct),
                    "focus": symbol == "BTCUSDT",
                }
            )
            continue
        is_steem = symbol == "STEEM"
        distance_pct = ((price - stop) / price * Decimal("100")) if price > 0 and stop > 0 else Decimal("999")
        warning_threshold = OPS_STEEM_STOP_WARNING_DISTANCE_PCT if is_steem else OPS_STOP_WARNING_DISTANCE_PCT
        if price > 0 and stop > 0 and price <= stop:
            level = "critical"
            title = f"{symbol} ?먯젅???꾨떖"
        elif distance_pct <= OPS_STOP_CRITICAL_DISTANCE_PCT:
            level = "critical"
            title = f"{symbol} ?먯젅??1% ?대궡"
        elif distance_pct <= warning_threshold:
            level = "warning"
            title = f"{symbol} ?먯젅??洹쇱젒"
        elif return_pct < 0 or is_steem:
            level = "warning" if is_steem else "waiting"
            title = f"{symbol} ?먯젅 媛먯떆"
        else:
            level = "ok"
            title = f"{symbol} 諛⑹뼱???ъ쑀"
        rows.append(
            {
                "key": f"stop:{market}",
                "market": market,
                "symbol": symbol,
                "level": level,
                "title": title,
                "value": f"{distance_pct:.2f}%",
                "body": (
                    f"?꾩옱媛? {format_ops_coin_price(price)}?? ?먯젅??{format_ops_coin_price(stop)}?? "
                    f"?먯젅?좉퉴吏? {distance_pct:.2f}% ?ъ쑀, 蹂댁쑀?섏씡瑜?{return_pct:.2f}%?낅땲??"
                ),
                "distancePct": decimal_to_str(distance_pct),
                "returnPct": decimal_to_str(return_pct),
                "focus": is_steem,
            }
        )
    rows.sort(key=lambda item: (ops_level_rank(item["level"]) * -1, not item.get("focus"), decimal_from_payload(item["distancePct"])))
    if rows:
        return rows
    if futures_mode:
        return [
            {
                "key": "stop:none",
                "level": "waiting",
                "title": "BTCUSDT 포지션 없음",
                "value": "대기",
                "body": "현재 BTCUSDT 100x 모의 포지션은 없어서 손절선 감시 대상도 없습니다.",
            }
        ]
    return [
        {
            "key": "stop:none",
            "level": "waiting",
            "title": "보유 종목 없음",
            "value": "대기",
            "body": "현재 손절선 근접 알림 대상 보유 종목은 없습니다.",
        }
    ]

def ops_candidate_watches(settings: TradingSettings, plan: dict[str, Any]) -> list[dict[str, Any]]:
    selected = plan.get("selected", []) if isinstance(plan.get("selected"), list) else []
    situations = plan.get("situations", []) if isinstance(plan.get("situations"), list) else []
    candidates = [item for item in [*selected, *situations] if isinstance(item, dict)]
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    candidate_limit = min(max(settings.realtime_candidate_top_n, 6), 20)
    for item in candidates:
        market = str(item.get("market") or "")
        if not market or market in seen:
            continue
        seen.add(market)
        deduped.append(item)
        if len(deduped) >= candidate_limit:
            break
    if not deduped:
        return [
            {
                "key": "candidate:none",
                "level": "waiting",
                "title": f"?꾨낫 {candidate_limit}醫?媛쒖꽑 ??湲?",
                "value": f"0/{candidate_limit}",
                "body": "?ㅼ떆媛??꾨낫媛? ?꾩쭅 ?놁뒿?덈떎. ?ㅼ쓬 ?꾩껜 KRW 遺꾩꽍?먯꽌 嫄곕옒??湲덇낵 泥닿껐媛뺣룄 媛쒖꽑???ㅼ떆 遊낅땲??",
            }
        ]
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(deduped, start=1):
        market = str(item.get("market") or "")
        symbol = market_symbol(market)
        if ops_is_futures_row(item):
            score = decimal_from_payload(item.get("score"))
            entry_allowed = str(item.get("entryAllowed") or "").lower() == "true"
            action = str(item.get("action") or "watch")
            side = str(item.get("executionSide") or item.get("side") or "FLAT")
            level = "ok" if entry_allowed and action in {"long", "short"} else "waiting"
            rows.append(
                {
                    "key": f"candidate:{market}",
                    "market": market,
                    "symbol": symbol,
                    "level": level,
                    "title": f"{index}. {symbol} 매억남 카드 후보",
                    "value": f"{side} 점수 {score:.2f}",
                    "body": str(item.get("riskReason") or item.get("entryBlockReason") or item.get("reason") or "매억남 카드 조건 확인 중"),
                    "score": decimal_to_str(score),
                    "volumeRatio": decimal_to_str(decimal_from_payload(item.get("volumeRatio"))),
                    "tradePressure": decimal_to_str(decimal_from_payload(item.get("tradePressure"))),
                }
            )
            continue
        volume_ratio = decimal_from_payload(item.get("volumeRatio"))
        trade_pressure = decimal_from_payload(item.get("tradePressure"))
        score = decimal_from_payload(item.get("score"))
        volume_ok = volume_ratio >= Decimal("1.2")
        pressure_ok = trade_pressure > 0
        level = "ok" if volume_ok and pressure_ok else "warning" if volume_ok or pressure_ok else "waiting"
        rows.append(
            {
                "key": f"candidate:{market}",
                "market": market,
                "symbol": symbol,
                "level": level,
                "title": f"{index}. {symbol} 후보 개선",
                "value": f"점수 {score:.2f}",
                "body": (
                    f"거래량 {volume_ratio:.2f}배, 체결강도 {trade_pressure:.2f}. "
                    f"{'개선 확인' if level == 'ok' else '부분 개선' if level == 'warning' else '개선 대기'} 상태입니다."
                ),
                "score": decimal_to_str(score),
                "volumeRatio": decimal_to_str(volume_ratio),
                "tradePressure": decimal_to_str(trade_pressure),
            }
        )
    return rows


def ops_operation_rules(
    settings: TradingSettings,
    markets: list[dict[str, Any]],
    plan: dict[str, Any],
    account: dict[str, Any],
    live: dict[str, Any],
) -> list[dict[str, Any]]:
    regime = plan.get("marketRegime", {}) if isinstance(plan.get("marketRegime"), dict) else {}
    lock = ops_regime_blocks_entries(settings, regime)
    futures_mode = ops_is_futures_plan(plan)
    held = [row for row in markets if ops_position_value(row) > 0]
    losses = sorted((row for row in held if ops_return_pct(row) < 0), key=ops_return_pct)
    profits = sorted((row for row in held if ops_return_pct(row) > 0), key=ops_return_pct, reverse=True)
    if futures_mode:
        leverage = str(plan.get("leverage") or "100")
        loss_text = " · ".join(f"{market_symbol(str(row.get('market') or ''))} ROE {ops_return_pct(row):.2f}%" for row in losses[:4])
        profit_text = " · ".join(f"{market_symbol(str(row.get('market') or ''))} ROE {ops_return_pct(row):.2f}%" for row in profits[:4])
        return [
            {
                "key": "op:new-entries",
                "level": "warning" if lock else "ok",
                "title": "BTCUSDT 신규 진입 잠금" if lock else "BTCUSDT 조건부 진입 허용",
                "value": "LOCK" if lock else "OPEN",
                "body": "BTCUSDT 1종목만 감시하며, 매억남 카드 점수/수수료 게이트/2회 확인/쿨다운을 모두 통과할 때만 100x 모의 진입합니다.",
            },
            {
                "key": "op:loss-cut",
                "level": "critical" if losses else "ok",
                "title": "BTCUSDT 손실 포지션 점검",
                "value": f"{len(losses)}개 손실",
                "body": loss_text if losses else "현재 BTCUSDT 모의 포지션 손실 컷 대상은 없습니다.",
            },
            {
                "key": "op:trailing",
                "level": "ok" if profits else "waiting",
                "title": "BTCUSDT 이익 보호",
                "value": f"{len(profits)}개 이익",
                "body": profit_text if profits else "카드 목표가 도달 후 같은 방향 카드가 계속 유효하면 본절 스탑으로 이익을 보호하며 더 보유합니다.",
            },
            {
                "key": "op:execution",
                "level": "ok",
                "title": "모의 실행 경계",
                "value": f"{leverage}x paper",
                "body": "현재 실행은 Binance USD-M 선물 모의거래이며 실거래 주문 잠금과 분리되어 있습니다.",
            },
        ]
    cash = decimal_from_payload(account.get("cashKrw"))
    items = [
        {
            "key": "op:new-entries",
            "level": "warning" if lock else "ok",
            "title": "異붽? ?ъ???湲덉?" if lock else "?좉퇋 ?ъ???議곌굔遺? ?덉슜",
            "value": "LOCK" if lock else "OPEN",
            "body": (
                "?덉쭚 ?쎌꽭???좉퇋 留ㅼ닔??留뚮뱾吏? ?딄퀬, ?꾧툑?? 諛⑹뼱?섎ŉ 蹂댁쑀 醫낅ぉ???먯젅/?몃젅?쇰쭅留??ㅽ뻾?⑸땲??"
                if lock
                else "?쒖옣 ?덉쭚???쎌꽭 李⑤떒 ?곹깭???꾨땲吏?留? ?좉퇋 留ㅼ닔???먯닔쨌嫄곕옒??湲댟룹껜寃곌컯?꽷룻샇媛? 蹂댄샇瑜?紐⑤몢 ?듦낵?댁빞 ?⑸땲??"
            ),
        },
        {
            "key": "op:loss-cut",
            "level": "critical" if losses and decimal_from_payload(losses[0].get("returnPct")) <= -settings.stop_loss_pct else "warning" if losses else "ok",
            "title": "?먯떎 ?뺣???醫낅ぉ遺???而?",
            "value": f"{len(losses)}媛??먯떎",
            "body": (
                " 쨌 ".join(f"{market_symbol(str(row.get('market') or ''))} {decimal_from_payload(row.get('returnPct')):.2f}%" for row in losses[:4])
                if losses
                else "?꾩옱 ?먯떎 ?ъ??섏씠 ?놁뼱 洹쒖튃??而????곸? ?놁뒿?덈떎."
            ),
        },
        {
            "key": "op:trailing",
            "level": "ok" if profits else "waiting",
            "title": "?댁씡 ?ъ????몃젅?쇰쭅",
            "value": f"{len(profits)}媛??댁씡",
            "body": (
                "紐⑺몴媛? ?꾧퉴吏? ?깃툒???꾨웾 ?듭젅蹂대떎 ?몃젅?쇰쭅 以묒떖?쇰줈 蹂댄샇?⑸땲?? "
                + " 쨌 ".join(f"{market_symbol(str(row.get('market') or ''))} {decimal_from_payload(row.get('returnPct')):.2f}%" for row in profits[:4])
                if profits
                else "?댁씡 ?ъ??섏씠 ?앷린硫?紐⑺몴媛? ?꾧퉴吏? ?몃젅?쇰쭅 湲곗??쇰줈 蹂댄샇?⑸땲??"
            ),
        },
        {
            "key": "op:execution",
            "level": "warning" if live.get("webArmed") else "ok",
            "title": "?ㅽ뻾 寃쎄퀎",
            "value": f"?꾧툑 {format_ops_krw_amount(cash)}??",
            "body": "?ㅺ굅???좉툑???대젮 ?덉뒿?덈떎. PM ?먮떒, ?덉쭚, ?먯젅?? ?멸? 蹂댄샇瑜?紐⑤몢 ?ы솗?명빐???⑸땲??"
            if live.get("webArmed")
            else "?ㅺ굅??二쇰Ц ?좉툑?? ?ロ? ?덇퀬, ?꾩옱 ?댁쁺 洹쒖튃?? ?섏씠??愿???湲곗??쇰줈 ?곸슜?⑸땲??",
        },
    ]
    return items


def ops_regime_blocks_entries(settings: TradingSettings, regime: dict[str, Any]) -> bool:
    label = str(regime.get("label") or "").lower()
    positive_ratio = decimal_from_payload(regime.get("positiveRatio"), Decimal("1"))
    return bool(regime.get("blockNewEntries")) or label in {"weak", "risk-off"} or positive_ratio < settings.risk_regime_min_positive_ratio


def plan_orders(plan: dict[str, Any], last: dict[str, Any]) -> list[dict[str, Any]]:
    orders = plan.get("orders", []) if isinstance(plan.get("orders"), list) else []
    executed = last.get("orders", []) if isinstance(last.get("orders"), list) else []
    return [order for order in (executed or orders) if isinstance(order, dict)]


def ops_order_side(order: dict[str, Any]) -> str:
    intent = order.get("intent")
    side_value = order.get("side")
    if not side_value and isinstance(intent, dict):
        side_value = intent.get("side")
    side = str(side_value or "").lower()
    if "ask" in side or "sell" in side or "매도" in side:
        return "sell"
    if "bid" in side or "buy" in side or "매수" in side:
        return "buy"
    return ""


def ops_error_texts(runtime: dict[str, Any], plan: dict[str, Any], runtime_errors: list[str]) -> list[str]:
    texts: list[str] = [str(error) for error in runtime_errors if error]
    realtime = runtime.get("realtime", {}) if isinstance(runtime.get("realtime"), dict) else {}
    autorun = runtime.get("autorun", {}) if isinstance(runtime.get("autorun"), dict) else {}
    for error in (realtime.get("lastError"), autorun.get("lastError")):
        if error:
            texts.append(str(error))
    for error in plan.get("errors", []) if isinstance(plan.get("errors"), list) else []:
        if isinstance(error, dict):
            texts.append(str(error.get("message") or error))
        elif error:
            texts.append(str(error))
    return texts


def api_error_text_is_429(text: str) -> bool:
    lowered = text.lower()
    return "429" in lowered or "too_many_requests" in lowered or "too many requests" in lowered


def highest_ops_level(levels: list[str]) -> str:
    if not levels:
        return "waiting"
    return max(levels, key=ops_level_rank)


def ops_level_rank(level: str) -> int:
    return {"waiting": 0, "ok": 1, "warning": 2, "critical": 3}.get(str(level), 0)


def run_backtest_scan(settings: TradingSettings, count: int) -> dict[str, Any]:
    client = make_client(settings)
    reports: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for index, market in enumerate(settings.markets):
        try:
            market_settings = replace(settings, market=market, markets=(market,), candle_count=min(max(count, settings.long_window + 5), 200))
            candles = fetch_candles(client, market_settings, market)
            reports.append(run_backtest(candles, market_settings).to_dict())
        except Exception as exc:
            errors.append({"market": market, "message": str(exc)})
        if index < len(settings.markets) - 1:
            time.sleep(0.12)

    ranked = sorted(reports, key=lambda row: Decimal(str(row.get("totalReturnPct", "0"))), reverse=True)
    try:
        SqliteStore(settings.database_file).append_backtest_reports(settings.strategy_name, ranked)
    except Exception:
        pass
    return {
        "count": count,
        "strategy": settings.strategy_name,
        "reports": ranked,
        "errors": errors,
        "best": ranked[0] if ranked else None,
        "worst": ranked[-1] if ranked else None,
    }


def learning_payload(settings: TradingSettings, app: FastAPI | None = None) -> dict[str, Any]:
    model = load_learning_model(settings)
    latest: dict[str, Any] | None = None
    try:
        latest = SqliteStore(settings.database_file).latest_learning_run()
    except Exception:
        latest = None
    return {
        "model": model,
        "latest": latest,
        "job": default_learning_job() if app is None else learning_job_snapshot(app),
        "modelPath": str(settings.state_file.parent / "learning_model.json"),
    }


def default_learning_job() -> dict[str, Any]:
    return {
        "running": False,
        "status": "idle",
        "scope": "watchlist",
        "processedMarkets": 0,
        "totalMarkets": 0,
        "currentMarket": None,
        "startedAt": None,
        "updatedAt": None,
        "finishedAt": None,
        "error": None,
        "message": "대기 중",
        "modelMarketCount": 0,
        "storedId": None,
    }


def learning_lock(app: FastAPI) -> threading.Lock:
    lock = getattr(app.state, "learning_lock", None)
    if lock is None:
        lock = threading.Lock()
        app.state.learning_lock = lock
    return lock


def learning_job_snapshot(app: FastAPI) -> dict[str, Any]:
    with learning_lock(app):
        job = getattr(app.state, "learning_job", None)
        return dict(default_learning_job() if job is None else job)


def update_learning_job(app: FastAPI, **updates: Any) -> dict[str, Any]:
    with learning_lock(app):
        current = dict(getattr(app.state, "learning_job", default_learning_job()))
        current.update(updates)
        current["updatedAt"] = datetime.now(timezone.utc).isoformat()
        app.state.learning_job = current
        return dict(current)


def start_learning_job(app: FastAPI, settings: TradingSettings, request: LearnRequest) -> dict[str, Any]:
    scope = normalize_learning_scope(request.scope)
    count = request.count or settings.learning_candle_count
    max_markets = request.max_markets if request.max_markets is not None else settings.learning_max_markets
    if max_markets < 0:
        raise HTTPException(status_code=400, detail="학습 최대 마켓 수는 0 이상이어야 합니다")
    if learning_job_snapshot(app)["running"]:
        raise HTTPException(status_code=409, detail="이미 과거 데이터 학습이 실행 중입니다")

    started_at = datetime.now(timezone.utc).isoformat()
    update_learning_job(
        app,
        running=True,
        status="running",
        scope=scope,
        processedMarkets=0,
        totalMarkets=0,
        currentMarket=None,
        startedAt=started_at,
        finishedAt=None,
        error=None,
        message="학습 준비 중",
        modelMarketCount=0,
        storedId=None,
    )

    thread = threading.Thread(
        target=run_learning_job,
        args=(app, settings, scope, count, max_markets),
        daemon=True,
    )
    thread.start()
    return {
        "job": learning_job_snapshot(app),
        "model": load_learning_model(settings),
        "message": "과거 데이터 학습을 시작했습니다",
    }


def normalize_learning_scope(scope: str) -> str:
    cleaned = scope.strip().lower()
    if cleaned in {"watchlist", "watched", "markets"}:
        return "watchlist"
    if cleaned in {"all_krw", "krw", "all"}:
        return "all_krw"
    raise HTTPException(status_code=400, detail=f"지원하지 않는 학습 범위입니다: {scope}")


def run_learning_job(
    app: FastAPI,
    settings: TradingSettings,
    scope: str,
    count: int,
    max_markets: int,
) -> None:
    try:
        client = make_client(settings)
        update_learning_job(app, message="학습 마켓 목록을 준비하는 중")
        if scope == "all_krw":
            markets = krw_market_codes(
                client,
                exclude_warnings=settings.learning_exclude_market_warnings,
                max_markets=max_markets,
            )
        else:
            markets = settings.markets[:max_markets] if max_markets > 0 else settings.markets
        if not markets:
            raise RuntimeError("학습할 KRW 마켓이 없습니다")

        learning_settings = replace(settings, market=markets[0], markets=tuple(markets))

        def progress(progress_payload: dict[str, Any]) -> None:
            processed = int(progress_payload.get("processedMarkets", 0) or 0)
            total = int(progress_payload.get("totalMarkets", 0) or 0)
            current = progress_payload.get("currentMarket")
            message = f"{processed}/{total} markets learning" if total else "Preparing learning"
            if current:
                message = f"{message} 쨌 {current}"
            update_learning_job(app, **progress_payload, message=message)

        result = run_historical_learning(
            learning_settings,
            client,
            count=count,
            markets=markets,
            scope=scope,
            progress_callback=progress,
        )
        model = result.to_model()
        save_learning_model(settings, model)
        stored_id: int | None = None
        try:
            stored_id = SqliteStore(settings.database_file).append_learning_run(model)
        except Exception:
            stored_id = None
        log_event(
            settings,
            "learning_run",
            {
                "scope": scope,
                "requestedMarketCount": model.get("requestedMarketCount", 0),
                "marketCount": model.get("marketCount", 0),
                "strategyCount": model.get("strategyCount", 0),
                "overall": model.get("overall", {}),
                "errors": len(model.get("errors", [])),
            },
        )
        update_learning_job(
            app,
            running=False,
            status="completed",
            scope=scope,
            processedMarkets=model.get("requestedMarketCount", 0),
            totalMarkets=model.get("requestedMarketCount", 0),
            currentMarket=None,
            finishedAt=datetime.now(timezone.utc).isoformat(),
            error=None,
            message="과거 데이터 학습 완료",
            modelMarketCount=model.get("marketCount", 0),
            storedId=stored_id,
        )
    except Exception as exc:
        update_learning_job(
            app,
            running=False,
            status="failed",
            finishedAt=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
            message=f"학습 실패: {exc}",
        )


def run_paper_market_once(settings: TradingSettings, market: str) -> dict[str, Any]:
    if market not in settings.markets:
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 마켓만 선택할 수 있습니다: {market}")
        settings = replace(settings, market=market, markets=tuple(dict.fromkeys([*settings.markets, market])))

    market_settings = settings_for_market(settings, market)
    client = make_client(market_settings)
    candles = fetch_candles(client, market_settings, market)
    latest_price = candles[0].trade_price if candles else Decimal("0")
    store = JsonPortfolioStateStore(settings.state_file)
    state = store.load(settings.paper_cash_krw)
    signal = make_strategy(market_settings).evaluate(candles)
    risk_manager = PortfolioRiskManager(settings)
    signal = risk_manager.protective_signal(signal, state, latest_price)
    decision = risk_manager.evaluate(signal, state, latest_price)
    result: OrderResult | None = None

    if decision.approved and decision.intent is not None:
        result = PortfolioPaperBroker(state, settings.fee_rate).execute(decision.intent, latest_price)
        store.save(state)
        log_event(
            settings,
            "paper_order",
            {
                "market": market,
                "ok": result.ok,
                "message": result.message,
                "raw": result.raw,
            },
        )

    return {
        "market": market,
        "price": decimal_to_str(latest_price),
        "signal": signal_payload(signal),
        "risk": {
            "approved": decision.approved,
            "reason": decision.reason,
            "intent": intent_payload(decision.intent),
        },
        "order": None
        if result is None
        else {
            "ok": result.ok,
            "mode": result.mode,
            "message": result.message,
            "raw": result.raw,
        },
    }


def log_event(settings: TradingSettings, event_type: str, payload: dict[str, Any]) -> None:
    try:
        JsonlEventLog(settings.event_log_file).append(event_type, payload)
    except Exception:
        pass
    try:
        SqliteStore(settings.database_file).append_event(event_type, payload)
    except Exception:
        pass


def record_portfolio_snapshot(
    settings: TradingSettings,
    prices: dict[str, Decimal],
    source: str,
) -> None:
    try:
        state = JsonPortfolioStateStore(settings.state_file).load(settings.paper_cash_krw)
        prices = complete_portfolio_prices(settings, state, prices)
        payload = {
            **portfolio_payload(state, prices),
            "source": source,
            "marketCount": len(prices),
        }
        SqliteStore(settings.database_file).append_portfolio_snapshot(payload)
    except Exception:
        pass


def complete_portfolio_prices(
    settings: TradingSettings,
    state: PortfolioState,
    prices: dict[str, Decimal],
) -> dict[str, Decimal]:
    completed = dict(prices)
    missing_markets = tuple(
        market
        for market, position in state.positions.items()
        if position.volume > 0 and completed.get(market, Decimal("0")) <= 0
    )
    if missing_markets:
        try:
            client = make_client(settings)
            fetched = fetch_tickers(client, missing_markets)
            completed.update(price_map(missing_markets, {str(item.get("market")): item for item in fetched}))
        except Exception:
            pass
    for market, position in state.positions.items():
        if position.volume > 0 and completed.get(market, Decimal("0")) <= 0 and position.avg_entry_price > 0:
            completed[market] = position.avg_entry_price
    return completed


def settings_for_market(settings: TradingSettings, market: str) -> TradingSettings:
    if market not in settings.markets:
        if not market.startswith("KRW-"):
            raise HTTPException(status_code=400, detail=f"KRW 留덉폆留??좏깮?????덉뒿?덈떎: {market}")
        expanded = tuple(dict.fromkeys([*settings.markets, market]))
        return replace(settings, market=market, markets=expanded)
    return replace(settings, market=market, markets=(market,))


def dashboard_realtime_markets(settings: TradingSettings, state: PortfolioState) -> tuple[str, ...]:
    client = make_client(settings)
    preferences = load_market_preferences(settings)
    checked_markets = tuple(dict.fromkeys([*preferences["markets"], *preferences["excludedMarkets"]]))
    try:
        markets, _meta = krw_market_metadata(client)
        return tuple(dict.fromkeys([*markets, *held_markets(state)]))
    except Exception:
        if checked_markets:
            return tuple(dict.fromkeys([*checked_markets, *held_markets(state)]))
        if settings.realtime_decision_enabled:
            return realtime_market_universe(settings, state)
        return portfolio_display_markets(settings, state)


def dashboard_display_markets(
    settings: TradingSettings,
    client: Any,
    state: PortfolioState,
) -> tuple[tuple[str, ...], dict[str, dict[str, Any]]]:
    try:
        markets, meta = krw_market_metadata(client)
        display_markets = tuple(dict.fromkeys([*markets, *held_markets(state)]))
        return display_markets, meta
    except Exception:
        preferences = load_market_preferences(settings)
        checked_markets = tuple(dict.fromkeys([*preferences["markets"], *preferences["excludedMarkets"]]))
        display_markets = tuple(dict.fromkeys([*portfolio_display_markets(settings, state), *checked_markets]))
        return display_markets, {}


def held_markets(state: PortfolioState) -> list[str]:
    return [market for market, position in state.positions.items() if position.volume > 0]


def portfolio_display_markets(settings: TradingSettings, state: PortfolioState) -> tuple[str, ...]:
    held_markets = [market for market, position in state.positions.items() if position.volume > 0]
    return tuple(dict.fromkeys([*settings.markets, *held_markets]))


def krw_market_metadata(client: Any) -> tuple[tuple[str, ...], dict[str, dict[str, Any]]]:
    now = time.monotonic()
    if now < float(_market_meta_cache.get("expires_at", 0) or 0):
        return tuple(_market_meta_cache["markets"]), dict(_market_meta_cache["meta"])

    raw_markets = client.get_markets(is_details=True)
    markets: list[str] = []
    meta: dict[str, dict[str, Any]] = {}
    for item in raw_markets:
        market = str(item.get("market") or "").upper()
        if not market.startswith("KRW-"):
            continue
        markets.append(market)
        meta[market] = {
            "market": market,
            "symbol": market_symbol(market),
            "koreanName": item.get("korean_name") or "",
            "englishName": item.get("english_name") or "",
        }

    unique_markets = tuple(dict.fromkeys(markets))
    _market_meta_cache["expires_at"] = now + MARKET_META_TTL_SECONDS
    _market_meta_cache["markets"] = unique_markets
    _market_meta_cache["meta"] = meta
    return unique_markets, meta


def fetch_tickers(client: Any, markets: tuple[str, ...], chunk_size: int = 80) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    market_list = list(markets)
    for index in range(0, len(market_list), chunk_size):
        chunk = market_list[index : index + chunk_size]
        for attempt in range(3):
            try:
                rows.extend(client.get_ticker(chunk))
                break
            except Exception as exc:
                if is_api_rate_limit_error(exc) and attempt < 2:
                    time.sleep(0.8 + attempt * 0.7)
                    continue
                raise
        if index + chunk_size < len(market_list):
            time.sleep(0.06)
    return rows


def is_api_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "too_many_requests" in text or "too many requests" in text


def market_symbol(market: str) -> str:
    return market.split("-", 1)[1] if "-" in market else market


def market_display_name(market: str, meta: dict[str, Any]) -> str:
    symbol = str(meta.get("symbol") or market_symbol(market))
    korean_name = str(meta.get("koreanName") or "")
    return f"{korean_name} {symbol}" if korean_name else symbol


def price_map(markets: tuple[str, ...], ticker_by_market: dict[str, dict[str, Any]]) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for market in markets:
        ticker = ticker_by_market.get(market, {})
        if ticker.get("trade_price") is not None:
            prices[market] = Decimal(str(ticker["trade_price"]))
    return prices


def merge_realtime_tickers(
    ticker_by_market: dict[str, dict[str, Any]],
    realtime: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    merged = {market: dict(ticker) for market, ticker in ticker_by_market.items()}
    realtime_tickers = realtime.get("tickers", {})
    if not isinstance(realtime_tickers, dict):
        return merged
    for market, ticker in realtime_tickers.items():
        if not isinstance(ticker, dict) or not ticker:
            continue
        row = dict(merged.get(str(market), {"market": str(market)}))
        if ticker.get("tradePrice") is not None:
            row["trade_price"] = ticker["tradePrice"]
        if ticker.get("change") is not None:
            row["change"] = ticker["change"]
        if ticker.get("signedChangeRate") is not None:
            row["change_rate"] = ticker["signedChangeRate"]
        elif ticker.get("changeRate") is not None:
            row["change_rate"] = ticker["changeRate"]
        if ticker.get("tradeValue24h") is not None:
            row["acc_trade_price_24h"] = ticker["tradeValue24h"]
        row["source"] = "websocket"
        merged[str(market)] = row
    return merged


def latest_market_price(ticker: dict[str, Any], candles: list[Candle]) -> Decimal:
    if ticker.get("trade_price") is not None:
        return Decimal(str(ticker["trade_price"]))
    if candles:
        return candles[0].trade_price
    return Decimal("0")


def market_payload(
    ticker: dict[str, Any],
    latest_price: Decimal,
    market_meta: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    market = str(ticker.get("market") or "KRW-BTC")
    meta = (market_meta or {}).get(market, {})
    change_rate = ticker.get("signed_change_rate", ticker.get("change_rate", "0"))
    return {
        "market": market,
        "symbol": market_symbol(market),
        "koreanName": meta.get("koreanName") or "",
        "englishName": meta.get("englishName") or "",
        "displayName": market_display_name(market, meta),
        "price": decimal_to_str(latest_price),
        "change": ticker.get("change") or "EVEN",
        "changePrice": decimal_to_str(Decimal(str(ticker.get("change_price", "0")))),
        "changeRate": decimal_to_str(Decimal(str(change_rate)) * Decimal("100")),
        "volume24h": decimal_to_str(Decimal(str(ticker.get("acc_trade_volume_24h", "0")))),
        "tradeValue24h": decimal_to_str(Decimal(str(ticker.get("acc_trade_price_24h", "0")))),
    }


def normalize_chart_frame(value: str | int | None) -> str:
    text = str(value or "5").strip().lower()
    minute_aliases = {f"{unit}m": unit for unit in MINUTE_CHART_FRAMES}
    aliases = {
        **minute_aliases,
        "d": "day",
        "1d": "day",
        "daily": "day",
        "days": "day",
        "day": "day",
        "일": "day",
        "일봉": "day",
        "?쇰큺": "day",
        "w": "week",
        "1w": "week",
        "weekly": "week",
        "weeks": "week",
        "week": "week",
        "주": "week",
        "주봉": "week",
        "二쇰큺": "week",
        "monthly": "month",
        "months": "month",
        "month": "month",
        "월": "month",
        "월봉": "month",
        "?붾큺": "month",
        "y": "year",
        "1y": "year",
        "yearly": "year",
        "years": "year",
        "year": "year",
        "년": "year",
        "년봉": "year",
        "연봉": "year",
        "?꾨큺": "year",
    }
    chart_frame = aliases.get(text, text)
    if chart_frame in MINUTE_CHART_FRAMES or chart_frame in PERIOD_CHART_FRAMES:
        return chart_frame
    raise HTTPException(status_code=400, detail=f"지원하지 않는 차트 단위입니다: {value}")


def chart_frame_label(chart_frame: str | int | None) -> str:
    return CHART_FRAME_LABELS.get(str(chart_frame), f"{chart_frame}분")


def normalize_chart_count(count: int | None, chart_frame: str, fallback_count: int) -> int:
    default_count = CHART_DEFAULT_COUNTS.get(chart_frame, fallback_count)
    requested_count = default_count if count is None else max(int(count), default_count)
    return min(max(requested_count, 1), CHART_MAX_CANDLES)


def fetch_chart_candles(client: Any, market: str, chart_frame: str, count: int) -> list[Candle]:
    if chart_frame not in MINUTE_CHART_FRAMES and chart_frame not in PERIOD_CHART_FRAMES:
        raise HTTPException(status_code=400, detail=f"吏??먰븯吏? ?딅뒗 李⑦듃 ?⑥쐞?낅땲?? {chart_frame}")

    safe_count = min(max(int(count), 1), CHART_MAX_CANDLES)
    candles_by_timestamp: dict[int, Candle] = {}
    cursor_to: str | None = None

    while len(candles_by_timestamp) < safe_count:
        page_size = min(CHART_PAGE_LIMIT, safe_count - len(candles_by_timestamp))
        if chart_frame in MINUTE_CHART_FRAMES:
            raw_page = client.get_minute_candles(market, unit=int(chart_frame), count=page_size, to=cursor_to)
        elif chart_frame == "day":
            raw_page = client.get_day_candles(market, count=page_size, to=cursor_to)
        elif chart_frame == "week":
            raw_page = client.get_week_candles(market, count=page_size, to=cursor_to)
        elif chart_frame == "month":
            raw_page = client.get_month_candles(market, count=page_size, to=cursor_to)
        else:
            raw_page = client.get_year_candles(market, count=page_size, to=cursor_to)
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
        time.sleep(CHART_PAGE_PAUSE_SECONDS)

    return sorted(candles_by_timestamp.values(), key=lambda candle: candle.timestamp, reverse=True)[:safe_count]


def signal_payload(signal: Signal) -> dict[str, Any]:
    return {
        "action": signal.action,
        "label": ACTION_LABELS[signal.action],
        "reason": signal.reason,
        "referencePrice": decimal_to_str(signal.reference_price),
    }


def intent_payload(intent: OrderIntent | None) -> dict[str, Any] | None:
    if intent is None:
        return None
    return {
        "market": intent.market,
        "side": "매수" if intent.side == "bid" else "매도",
        "type": intent.ord_type,
        "price": decimal_to_str(intent.price) if intent.price is not None else None,
        "volume": decimal_to_str(intent.volume) if intent.volume is not None else None,
        "reason": intent.reason,
    }


def paper_account_payload(
    state: PortfolioState,
    prices: dict[str, Decimal],
    active_market: str,
) -> dict[str, Any]:
    active_position = state.position(active_market)
    return {
        "cashKrw": decimal_to_str(state.cash_krw),
        "positionVolume": decimal_to_str(active_position.volume),
        "avgEntryPrice": decimal_to_str(active_position.avg_entry_price),
        "positionValueKrw": decimal_to_str(state.total_position_value(prices)),
        "equityKrw": decimal_to_str(state.equity(prices)),
        "realizedPnlKrw": decimal_to_str(state.realized_pnl_krw),
        "feesPaidKrw": decimal_to_str(state.fees_paid_krw),
        "orderCount": state.order_count,
        "lastOrderAt": state.last_order_at,
        "dailyRealizedPnlKrw": decimal_to_str(state.daily_realized_pnl_krw),
        "dailyOrderCount": state.daily_order_count,
        "riskDate": state.risk_date,
    }


def portfolio_payload(state: PortfolioState, prices: dict[str, Decimal]) -> dict[str, Any]:
    return {
        "cashKrw": decimal_to_str(state.cash_krw),
        "positionValueKrw": decimal_to_str(state.total_position_value(prices)),
        "equityKrw": decimal_to_str(state.equity(prices)),
        "realizedPnlKrw": decimal_to_str(state.realized_pnl_krw),
        "feesPaidKrw": decimal_to_str(state.fees_paid_krw),
        "orderCount": state.order_count,
        "openPositions": sum(1 for position in state.positions.values() if position.volume > 0),
    }


def goal_payload(settings: TradingSettings, state: PortfolioState, prices: dict[str, Decimal]) -> dict[str, Any]:
    equity = state.equity(prices)
    progress = (equity - settings.goal_start_krw) / (settings.goal_target_krw - settings.goal_start_krw) * Decimal("100")
    progress = max(Decimal("0"), min(progress, Decimal("100")))
    return {
        "startKrw": decimal_to_str(settings.goal_start_krw),
        "targetKrw": decimal_to_str(settings.goal_target_krw),
        "days": settings.goal_days,
        "equityKrw": decimal_to_str(equity),
        "remainingKrw": decimal_to_str(max(settings.goal_target_krw - equity, Decimal("0"))),
        "progressPct": decimal_to_str(progress),
        "currentMultiple": decimal_to_str(equity / settings.goal_start_krw),
        "targetMultiple": decimal_to_str(settings.goal_target_krw / settings.goal_start_krw),
    }


def decision_chart_levels_by_market(realtime_decision: dict[str, Any]) -> dict[str, dict[str, Any]]:
    last = realtime_decision.get("last", {}) if isinstance(realtime_decision.get("last"), dict) else {}
    plan = last.get("plan", {}) if isinstance(last.get("plan"), dict) else {}
    rows = []
    for key in ("situations", "selected", "orders"):
        value = plan.get(key)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
    levels: dict[str, dict[str, Any]] = {}
    for row in rows:
        market = str(row.get("market") or "")
        chart_levels = row.get("chartLevels")
        if market and isinstance(chart_levels, dict):
            levels[market] = chart_levels
    return levels


def market_rows_payload(
    markets: tuple[str, ...],
    settings: TradingSettings,
    ticker_by_market: dict[str, dict[str, Any]],
    state: PortfolioState,
    prices: dict[str, Decimal],
    realtime: dict[str, Any] | None = None,
    market_meta: dict[str, dict[str, Any]] | None = None,
    recommended_markets: tuple[str, ...] = (),
    excluded_markets: tuple[str, ...] = (),
    chart_levels_by_market: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    realtime = realtime or {}
    market_meta = market_meta or {}
    recommended_set = set(recommended_markets)
    excluded_set = set(excluded_markets)
    chart_levels_by_market = chart_levels_by_market or {}
    realtime_tickers = realtime.get("tickers", {})
    realtime_trades = realtime.get("trades", {})
    for market in markets:
        meta = market_meta.get(market, {})
        ticker = ticker_by_market.get(market, {})
        price = prices.get(market, Decimal("0"))
        position = state.position(market)
        value = position.value(price)
        cost_basis = position.volume * position.avg_entry_price
        unrealized_pnl = value - cost_basis
        return_pct = unrealized_pnl / cost_basis * Decimal("100") if cost_basis > 0 else Decimal("0")
        realized_by_market = state.realized_pnl_by_market or {}
        realized_pnl = realized_by_market.get(market, Decimal("0"))
        change_rate = ticker.get("signed_change_rate", ticker.get("change_rate", "0"))
        latest_trades = realtime_trades.get(market, []) if isinstance(realtime_trades, dict) else []
        latest_trade = latest_trades[0] if latest_trades else {}
        latest_trade_price = latest_trade.get("tradePrice") if latest_trade else None
        last_reason = (state.last_order_reason_by_market or {}).get(market, "")
        decision_analysis = market_decision_analysis(
            settings,
            price,
            position,
            return_pct,
            Decimal(str(change_rate)),
            Decimal(str(ticker.get("acc_trade_price_24h", "0"))),
            last_reason,
            chart_levels_by_market.get(market),
        )
        rows.append(
            {
                "market": market,
                "symbol": market_symbol(market),
                "koreanName": meta.get("koreanName") or "",
                "englishName": meta.get("englishName") or "",
                "displayName": market_display_name(market, meta),
                "recommended": market in recommended_set,
                "excluded": market in excluded_set,
                "price": decimal_to_str(price),
                "change": ticker.get("change") or "EVEN",
                "changePrice": decimal_to_str(Decimal(str(ticker.get("change_price", "0")))),
                "changeRate": decimal_to_str(Decimal(str(change_rate)) * Decimal("100")),
                "volume24h": decimal_to_str(Decimal(str(ticker.get("acc_trade_volume_24h", "0")))),
                "tradeValue24h": decimal_to_str(Decimal(str(ticker.get("acc_trade_price_24h", "0")))),
                "stream": "실시간" if isinstance(realtime_tickers, dict) and realtime_tickers.get(market) else "REST",
                "lastTradePrice": decimal_to_str(Decimal(str(latest_trade_price))) if latest_trade_price is not None else "0",
                "lastTradeSide": latest_trade.get("askBid") if latest_trade else None,
                "status": "보유" if position.volume > 0 else "감시",
                "positionVolume": decimal_to_str(position.volume),
                "avgEntryPrice": decimal_to_str(position.avg_entry_price),
                "targetSellPrice": decimal_to_str(decision_analysis["targetSellPrice"]),
                "stopLossPrice": decimal_to_str(decision_analysis["stopLossPrice"]),
                "positionValueKrw": decimal_to_str(value),
                "unrealizedPnlKrw": decimal_to_str(unrealized_pnl),
                "realizedPnlKrw": decimal_to_str(realized_pnl),
                "returnPct": decimal_to_str(return_pct),
                "analysis": {
                    "title": decision_analysis["title"],
                    "buyReason": decision_analysis["buyReason"],
                    "sellReason": decision_analysis["sellReason"],
                    "targetReason": decision_analysis["targetReason"],
                    "narrative": decision_analysis["narrative"],
                },
            }
        )
    return rows


def market_decision_analysis(
    settings: TradingSettings,
    price: Decimal,
    position: PortfolioPosition,
    return_pct: Decimal,
    change_rate: Decimal,
    trade_value_24h: Decimal,
    last_order_reason: str = "",
    chart_levels: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_sell_price = Decimal("0")
    stop_loss_price = Decimal("0")
    if position.avg_entry_price > 0:
        target_sell_price = position.avg_entry_price * (Decimal("1") + settings.take_profit_pct / Decimal("100"))
        stop_loss_price = position.avg_entry_price * (Decimal("1") - settings.stop_loss_pct / Decimal("100"))
    if chart_levels:
        dynamic_target = decimal_from_payload(chart_levels.get("takeProfitPrice"))
        dynamic_stop = decimal_from_payload(chart_levels.get("stopLossPrice"))
        if dynamic_target > 0:
            target_sell_price = dynamic_target
        if dynamic_stop > 0:
            stop_loss_price = dynamic_stop

    if position.volume > 0 and position.avg_entry_price > 0:
        buy_reason = last_order_reason or "최근 매수 사유 기록은 없지만, 현재 보유 수량은 평균 매수가 기준으로 관리 중입니다."
        if return_pct >= settings.take_profit_pct:
            sell_reason = f"익절 기준 +{settings.take_profit_pct}%를 충족해 매도 검토 구간입니다."
        elif return_pct <= -settings.stop_loss_pct:
            sell_reason = f"손절 기준 -{settings.stop_loss_pct}%에 도달해 손실 제한이 우선입니다."
        elif change_rate < 0:
            sell_reason = "당일 하락이 강해 추세 훼손, 가격 방어, 체결 강도 약화를 함께 확인합니다."
        else:
            sell_reason = "목표가 전에는 보유하되, 급락 감지나 추세 재이탈 필터가 켜지면 청산을 우선합니다."
        target_reason = f"목표가는 평균 매수가 대비 +{settings.take_profit_pct}%인 {decimal_to_str(target_sell_price)}이고, 방어선은 -{settings.stop_loss_pct}%인 {decimal_to_str(stop_loss_price)}입니다."
        title = "보유 판단"
        narrative = f"매수 근거: {buy_reason} 매도 근거: {sell_reason} {target_reason}"
    else:
        buy_reason = (
            f"미보유 상태입니다. 실시간 점수 {settings.realtime_min_score} 이상, 거래대금 {decimal_to_str(trade_value_24h)}와 "
            "급등 추격 금지, 시장 안전 필터를 통과할 때만 신규 진입 후보가 됩니다."
        )
        sell_reason = "보유 수량이 없어 매도 판단은 대기 상태입니다."
        target_reason = "진입 전에는 목표가를 확정하지 않고, 매수 체결 후 평균 매수가 기준으로 목표가와 손절가를 산정합니다."
        title = "진입 대기"
        narrative = f"{buy_reason} {target_reason}"

    if chart_levels:
        target_reason = (
            f"차트 지지/저항, ATR, VWAP 기준 진입 {chart_levels.get('entryPrice', '0')}, "
            f"목표 {chart_levels.get('takeProfitPrice', decimal_to_str(target_sell_price))}, "
            f"손절 {chart_levels.get('stopLossPrice', decimal_to_str(stop_loss_price))}, "
            f"트레일링 {chart_levels.get('trailingStopPrice', '0')}, "
            f"손익비 {chart_levels.get('riskReward', '0')}입니다."
        )
        narrative = f"{narrative} {target_reason}"

    return {
        "title": title,
        "buyReason": buy_reason,
        "sellReason": sell_reason,
        "targetReason": target_reason,
        "narrative": narrative,
        "targetSellPrice": target_sell_price,
        "stopLossPrice": stop_loss_price,
    }


def chart_payload(candles: list[Candle], short_window: int = 5, long_window: int = 20) -> list[dict[str, str | None]]:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    closes = [candle.trade_price for candle in ordered]
    rows: list[dict[str, str | None]] = []
    for index, candle in enumerate(ordered):
        rows.append(
            {
                "time": candle.candle_date_time_kst,
                "open": decimal_to_str(candle.opening_price),
                "high": decimal_to_str(candle.high_price),
                "low": decimal_to_str(candle.low_price),
                "close": decimal_to_str(candle.trade_price),
                "volume": decimal_to_str(candle.candle_acc_trade_volume),
                "tradeValue": decimal_to_str(candle.candle_acc_trade_price),
                "maShort": moving_average_at(closes, index, short_window),
                "maLong": moving_average_at(closes, index, long_window),
            }
        )
    return rows


def portfolio_chart_payload(
    snapshots: list[dict[str, Any]],
    chart_frame: str,
    short_window: int = 5,
    long_window: int = 20,
    count: int = 120,
) -> list[dict[str, str | None]]:
    points: list[dict[str, Any]] = []
    for snapshot in snapshots:
        timestamp = parse_snapshot_time(str(snapshot.get("time") or ""))
        if timestamp is None:
            continue
        points.append(
            {
                "time": timestamp,
                "bucket": portfolio_chart_bucket(timestamp, chart_frame),
                "position": decimal_from_snapshot(snapshot, "positionValueKrw"),
                "cash": decimal_from_snapshot(snapshot, "cashKrw"),
                "equity": decimal_from_snapshot(snapshot, "equityKrw"),
                "realized": decimal_from_snapshot(snapshot, "realizedPnlKrw"),
                "fees": decimal_from_snapshot(snapshot, "feesPaidKrw"),
                "pricePnl": decimal_from_snapshot(snapshot, "pricePnlKrw"),
                "openFees": decimal_from_snapshot(snapshot, "openFeesPaidKrw"),
                "closeFees": decimal_from_snapshot(snapshot, "closeFeesPaidKrw"),
                "orders": int(snapshot.get("orderCount", 0) or 0),
                "openPositions": int(snapshot.get("openPositions", 0) or 0),
                "source": str((snapshot.get("payload") or {}).get("source") or ""),
                "currency": str((snapshot.get("payload") or {}).get("currency") or "KRW"),
            }
        )

    points.sort(key=lambda point: point["time"])
    buckets: dict[datetime, list[dict[str, Any]]] = {}
    for point in points:
        buckets.setdefault(point["bucket"], []).append(point)

    closes: list[Decimal] = []
    rows: list[dict[str, str | None]] = []
    for bucket_time in sorted(buckets):
        bucket_points = buckets[bucket_time]
        equities = [point["equity"] for point in bucket_points]
        positions = [point["position"] for point in bucket_points]
        cash_values = [point["cash"] for point in bucket_points]
        realized_values = [point["realized"] for point in bucket_points]
        price_pnl_values = [point["pricePnl"] for point in bucket_points]
        open_fee_values = [point["openFees"] for point in bucket_points]
        close_fee_values = [point["closeFees"] for point in bucket_points]
        total_fee_values = [point["fees"] for point in bucket_points]
        movement = Decimal("0")
        for previous, current in zip(equities, equities[1:]):
            movement += abs(current - previous)
        latest = bucket_points[-1]
        close = equities[-1]
        previous_close = closes[-1] if closes else None
        if movement == 0 and previous_close is not None:
            movement = abs(close - previous_close)
        closes.append(close)
        rows.append(
            {
                "time": bucket_time.isoformat(),
                "open": decimal_to_str(equities[0]),
                "high": decimal_to_str(max(equities)),
                "low": decimal_to_str(min(equities)),
                "close": decimal_to_str(close),
                "volume": decimal_to_str(movement),
                "tradeValue": decimal_to_str(movement),
                "maShort": moving_average_at(closes, len(closes) - 1, short_window),
                "maLong": moving_average_at(closes, len(closes) - 1, long_window),
                "equityKrw": decimal_to_str(equities[-1]),
                "equityHighKrw": decimal_to_str(max(equities)),
                "equityLowKrw": decimal_to_str(min(equities)),
                "positionValueKrw": decimal_to_str(positions[-1]),
                "positionHighKrw": decimal_to_str(max(positions)),
                "positionLowKrw": decimal_to_str(min(positions)),
                "cashKrw": decimal_to_str(cash_values[-1]),
                "realizedPnlKrw": decimal_to_str(realized_values[-1]),
                "pricePnlKrw": decimal_to_str(price_pnl_values[-1]),
                "openFeesPaidKrw": decimal_to_str(open_fee_values[-1]),
                "closeFeesPaidKrw": decimal_to_str(close_fee_values[-1]),
                "feesPaidKrw": decimal_to_str(total_fee_values[-1]),
                "openPositions": str(latest["openPositions"]),
                "orderCount": str(latest["orders"]),
                "source": latest["source"],
                "currency": latest["currency"],
            }
        )
    return rows[-count:]


def parse_snapshot_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def portfolio_chart_bucket(timestamp: datetime, chart_frame: str) -> datetime:
    kst = timestamp.astimezone(timezone(timedelta(hours=9)))
    if chart_frame in MINUTE_CHART_FRAMES:
        minutes = int(chart_frame)
        floored_minute = (kst.minute // minutes) * minutes
        return kst.replace(minute=floored_minute, second=0, microsecond=0)
    if chart_frame == "day":
        return kst.replace(hour=0, minute=0, second=0, microsecond=0)
    if chart_frame == "week":
        week_start = kst - timedelta(days=kst.weekday())
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    if chart_frame == "month":
        return kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if chart_frame == "year":
        return kst.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return kst.replace(second=0, microsecond=0)


def decimal_from_snapshot(snapshot: dict[str, Any], key: str) -> Decimal:
    value = snapshot.get(key)
    if value is None and isinstance(snapshot.get("payload"), dict):
        value = snapshot["payload"].get(key)
    try:
        return Decimal(str(value if value is not None else "0"))
    except Exception:
        return Decimal("0")


def portfolio_chart_snapshot_limit(chart_frame: str, count: int) -> int:
    if chart_frame in MINUTE_CHART_FRAMES:
        interval_minutes = max(1, int(chart_frame))
        return min(12000, max(400, count * interval_minutes * 16))
    return 12000


def moving_average_at(values: list[Decimal], index: int, window: int) -> str | None:
    if window <= 0 or index + 1 < window:
        return None
    subset = values[index + 1 - window : index + 1]
    return decimal_to_str(sum(subset, Decimal("0")) / Decimal(window))


def log_payload(
    errors: list[str],
    signal: Signal,
    risk_approved: bool,
    risk_reason: str,
) -> list[dict[str, str]]:
    now = datetime.now(timezone.utc).isoformat()
    logs = [
        {"time": now, "level": "info", "message": f"전략 신호: {ACTION_LABELS[signal.action]} - {signal.reason}"},
        {"time": now, "level": "ok" if risk_approved else "warn", "message": f"리스크 검토: {risk_reason}"},
    ]
    logs.extend({"time": now, "level": "error", "message": error} for error in errors)
    return logs


app = create_app()


def main() -> int:
    import uvicorn

    host = os.environ.get("AUTOTRADING_HOST", "127.0.0.1")
    port = int(os.environ.get("AUTOTRADING_PORT", "8000"))
    uvicorn.run("upbit_autotrader.web:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
