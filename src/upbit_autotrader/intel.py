from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
import html
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .config import TradingSettings


INTEL_INTERVAL_SECONDS = 6 * 60 * 60
MAX_NEWS_ITEMS = 48
MAX_COIN_ANALYSES = 36

RSS_SOURCES = (
    {
        "id": "coindesk",
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "kind": "rss",
        "weight": Decimal("1.10"),
    },
    {
        "id": "cointelegraph",
        "name": "Cointelegraph",
        "url": "https://cointelegraph.com/rss",
        "kind": "rss",
        "weight": Decimal("1.00"),
    },
    {
        "id": "decrypt",
        "name": "Decrypt",
        "url": "https://decrypt.co/feed",
        "kind": "rss",
        "weight": Decimal("0.95"),
    },
)

API_SOURCES = (
    {
        "id": "coingecko_trending",
        "name": "CoinGecko Trending",
        "url": "https://api.coingecko.com/api/v3/search/trending",
        "kind": "api",
    },
    {
        "id": "coingecko_global",
        "name": "CoinGecko Global",
        "url": "https://api.coingecko.com/api/v3/global",
        "kind": "api",
    },
    {
        "id": "fear_greed",
        "name": "Alternative.me Fear & Greed",
        "url": "https://api.alternative.me/fng/?limit=1",
        "kind": "api",
    },
)

POSITIVE_TERMS = (
    "approval",
    "approved",
    "etf",
    "partnership",
    "partners",
    "launch",
    "mainnet",
    "upgrade",
    "listing",
    "listed",
    "integrates",
    "integration",
    "adoption",
    "treasury",
    "inflow",
    "record high",
    "surge",
    "rally",
    "raises",
    "funding",
    "buyback",
    "burn",
)

NEGATIVE_TERMS = (
    "hack",
    "hacked",
    "exploit",
    "stolen",
    "lawsuit",
    "sec",
    "cftc",
    "ban",
    "delist",
    "delisting",
    "outage",
    "liquidation",
    "sell-off",
    "selloff",
    "crash",
    "probe",
    "investigation",
    "fraud",
    "scam",
    "rug",
    "vulnerability",
    "bankrupt",
    "bankruptcy",
    "unlock",
)

BROAD_MARKET_TERMS = (
    "crypto",
    "bitcoin",
    "ethereum",
    "market",
    "fed",
    "rate",
    "inflation",
    "dollar",
    "stocks",
    "treasury",
    "liquidity",
)

COIN_ALIASES = {
    "BTC": ("bitcoin", "btc"),
    "ETH": ("ethereum", "ether", "eth"),
    "XRP": ("xrp", "ripple"),
    "SOL": ("solana", "sol"),
    "DOGE": ("dogecoin", "doge"),
    "ADA": ("cardano", "ada"),
    "AVAX": ("avalanche", "avax"),
    "LINK": ("chainlink", "link"),
    "DOT": ("polkadot", "dot"),
    "TRX": ("tron", "trx"),
    "AAVE": ("aave",),
    "HOLO": ("holo", "hot"),
    "SAND": ("sandbox", "sand"),
    "BERA": ("berachain", "bera"),
    "BLEND": ("blend",),
    "HIVE": ("hive",),
}


def market_intel_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "market_intel.json"


def load_market_intel(settings: TradingSettings) -> dict[str, Any]:
    path = market_intel_path(settings)
    if not path.exists():
        return default_market_intel_payload()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_market_intel_payload()
    return payload if isinstance(payload, dict) else default_market_intel_payload()


def save_market_intel(settings: TradingSettings, payload: dict[str, Any]) -> None:
    path = market_intel_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def default_market_intel_payload() -> dict[str, Any]:
    return {
        "ok": False,
        "updatedAt": "",
        "nextRunAt": "",
        "intervalSeconds": INTEL_INTERVAL_SECONDS,
        "sources": [public_source(source) for source in (*RSS_SOURCES, *API_SOURCES)],
        "items": [],
        "trending": [],
        "global": {},
        "coinAnalyses": [],
        "errors": [],
        "summary": "시장정보 수집 대기 중입니다.",
    }


def collect_market_intel(settings: TradingSettings, status: dict[str, Any] | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    markets = market_terms_from_status(settings, status or {})
    errors: list[str] = []
    source_states: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for source in RSS_SOURCES:
        try:
            fetched = fetch_rss_source(source, markets)
            items.extend(fetched)
            source_states.append({**public_source(source), "ok": True, "count": len(fetched)})
        except Exception as exc:
            errors.append(f"{source['name']} 수집 실패: {exc}")
            source_states.append({**public_source(source), "ok": False, "error": str(exc)})

    global_payload: dict[str, Any] = {}
    trending: list[dict[str, Any]] = []
    for source in API_SOURCES:
        try:
            payload = fetch_json_url(str(source["url"]))
            if source["id"] == "coingecko_trending":
                trending = parse_coingecko_trending(payload)
                for item in trending[:12]:
                    items.append(trending_to_news_item(item, now))
            elif source["id"] == "coingecko_global":
                global_payload.update(parse_coingecko_global(payload))
            elif source["id"] == "fear_greed":
                global_payload.update(parse_fear_greed(payload))
            source_states.append({**public_source(source), "ok": True, "count": 1})
        except Exception as exc:
            errors.append(f"{source['name']} 수집 실패: {exc}")
            source_states.append({**public_source(source), "ok": False, "error": str(exc)})

    deduped = dedupe_news_items(items)
    deduped.sort(key=lambda item: item.get("publishedAt") or "", reverse=True)
    deduped = deduped[:MAX_NEWS_ITEMS]
    coin_analyses = analyze_coin_intel(markets, deduped, trending, global_payload)
    payload = {
        "ok": not errors or bool(deduped or trending or global_payload),
        "updatedAt": now.isoformat(),
        "nextRunAt": (now + timedelta(seconds=INTEL_INTERVAL_SECONDS)).isoformat(),
        "intervalSeconds": INTEL_INTERVAL_SECONDS,
        "sources": source_states,
        "items": deduped,
        "trending": trending,
        "global": global_payload,
        "coinAnalyses": coin_analyses,
        "errors": errors,
        "summary": market_intel_summary(deduped, trending, global_payload, coin_analyses, errors),
    }
    save_market_intel(settings, payload)
    return payload


def fetch_rss_source(source: dict[str, Any], markets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    raw = fetch_url(str(source["url"]))
    root = ET.fromstring(raw)
    channel_items = root.findall(".//item")
    rows: list[dict[str, Any]] = []
    for item in channel_items[:24]:
        title = text_of(item, "title")
        if not title:
            continue
        link = text_of(item, "link")
        description = clean_html(text_of(item, "description"))
        published = parse_rss_datetime(text_of(item, "pubDate") or text_of(item, "updated"))
        combined = f"{title} {description}"
        score, sentiment, reasons = score_news_text(combined)
        matched = match_markets(combined, markets)
        if not matched and not is_broad_market(combined):
            continue
        rows.append(
            {
                "id": stable_item_id(str(source["id"]), title, link),
                "source": source["name"],
                "sourceId": source["id"],
                "title": title[:240],
                "summary": description[:360],
                "url": link,
                "publishedAt": published,
                "sentiment": sentiment,
                "impactScore": decimal_to_payload(score * Decimal(str(source.get("weight", 1)))),
                "markets": matched,
                "reasons": reasons,
                "kind": "news",
            }
        )
    return rows


def fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "autotrading-market-intel/0.1 (+local dashboard)",
            "Accept": "application/rss+xml, application/xml, application/json, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json_url(url: str) -> dict[str, Any]:
    payload = json.loads(fetch_url(url))
    return payload if isinstance(payload, dict) else {}


def text_of(item: ET.Element, tag: str) -> str:
    found = item.find(tag)
    if found is not None and found.text:
        return found.text.strip()
    for child in item:
        if child.tag.endswith(tag) and child.text:
            return child.text.strip()
    return ""


def parse_rss_datetime(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def clean_html(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def score_news_text(value: str) -> tuple[Decimal, str, list[str]]:
    lowered = value.lower()
    positive = [term for term in POSITIVE_TERMS if term in lowered]
    negative = [term for term in NEGATIVE_TERMS if term in lowered]
    score = Decimal(len(positive)) * Decimal("1.2") - Decimal(len(negative)) * Decimal("1.45")
    if score > Decimal("0.5"):
        sentiment = "positive"
    elif score < Decimal("-0.5"):
        sentiment = "negative"
    else:
        sentiment = "neutral"
    reasons = [f"호재:{term}" for term in positive[:3]] + [f"악재:{term}" for term in negative[:3]]
    if not reasons:
        reasons = ["시장동향"]
    return score, sentiment, reasons


def match_markets(value: str, markets: dict[str, dict[str, Any]]) -> list[str]:
    lowered = value.lower()
    matched: list[str] = []
    for market, row in markets.items():
        terms = row.get("terms", [])
        for term in terms:
            if not term:
                continue
            pattern = r"(?<![a-z0-9])" + re.escape(str(term).lower()) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                matched.append(market)
                break
    return matched[:8]


def is_broad_market(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in BROAD_MARKET_TERMS)


def parse_coingecko_trending(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(payload.get("coins", []) if isinstance(payload.get("coins"), list) else []):
        item = entry.get("item", {}) if isinstance(entry, dict) else {}
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").upper()
        rows.append(
            {
                "rank": index + 1,
                "id": item.get("id"),
                "symbol": symbol,
                "name": item.get("name"),
                "marketCapRank": item.get("market_cap_rank"),
                "source": "CoinGecko",
                "url": f"https://www.coingecko.com/en/coins/{item.get('id')}" if item.get("id") else "",
            }
        )
    return rows[:12]


def parse_coingecko_global(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    market_cap_pct = data.get("market_cap_change_percentage_24h_usd")
    dominance = data.get("market_cap_percentage", {}) if isinstance(data.get("market_cap_percentage"), dict) else {}
    return {
        "marketCapChange24hPct": market_cap_pct,
        "btcDominancePct": dominance.get("btc"),
        "ethDominancePct": dominance.get("eth"),
        "activeCryptocurrencies": data.get("active_cryptocurrencies"),
        "markets": data.get("markets"),
        "source": "CoinGecko",
    }


def parse_fear_greed(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("data", []) if isinstance(payload.get("data"), list) else []
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    return {
        "fearGreedValue": first.get("value"),
        "fearGreedLabel": first.get("value_classification"),
        "fearGreedUpdatedAt": first.get("timestamp"),
        "fearGreedSource": "Alternative.me",
    }


def trending_to_news_item(item: dict[str, Any], now: datetime) -> dict[str, Any]:
    symbol = str(item.get("symbol") or "").upper()
    title = f"{symbol} 글로벌 트렌딩 {item.get('rank')}위" if symbol else f"글로벌 트렌딩 {item.get('rank')}위"
    return {
        "id": f"trend-{item.get('id') or symbol}-{item.get('rank')}",
        "source": "CoinGecko",
        "sourceId": "coingecko_trending",
        "title": title,
        "summary": f"{item.get('name') or symbol} 검색 관심도가 CoinGecko에서 상승했습니다.",
        "url": item.get("url") or "",
        "publishedAt": now.isoformat(),
        "sentiment": "positive",
        "impactScore": "1.4",
        "markets": [f"KRW-{symbol}"] if symbol else [],
        "reasons": ["트렌딩"],
        "kind": "trend",
    }


def analyze_coin_intel(
    markets: dict[str, dict[str, Any]],
    items: list[dict[str, Any]],
    trending: list[dict[str, Any]],
    global_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    trending_symbols = {str(row.get("symbol") or "").upper(): row for row in trending}
    market_cap_change = decimal_value(global_payload.get("marketCapChange24hPct"))
    fear_value = decimal_value(global_payload.get("fearGreedValue"))
    rows: list[dict[str, Any]] = []
    for market, meta in markets.items():
        symbol = str(meta.get("symbol") or market.replace("KRW-", ""))
        related = [item for item in items if market in (item.get("markets") or [])]
        broad = [item for item in items if not item.get("markets") and item.get("kind") == "news"][:4]
        impact = sum((decimal_value(item.get("impactScore")) for item in related), Decimal("0"))
        if symbol in trending_symbols:
            impact += Decimal("1.4")
        if market in {"KRW-BTC", "KRW-ETH"}:
            impact += market_cap_change / Decimal("2")
        if fear_value >= Decimal("70"):
            impact -= Decimal("0.5")
        elif Decimal("0") < fear_value <= Decimal("30"):
            impact += Decimal("0.4")
        if impact > Decimal("1.5"):
            signal = "favorable"
        elif impact < Decimal("-1.2"):
            signal = "adverse"
        else:
            signal = "watch"
        rows.append(
            {
                "market": market,
                "symbol": symbol,
                "label": meta.get("label") or market,
                "signal": signal,
                "impactScore": decimal_to_payload(impact),
                "headline": coin_intel_headline(signal, related, symbol in trending_symbols),
                "reasons": coin_intel_reasons(related, symbol in trending_symbols, global_payload),
                "articles": related[:4],
                "broadMarket": broad[:2],
            }
        )
    rows.sort(key=lambda row: decimal_value(row.get("impactScore")), reverse=True)
    return rows[:MAX_COIN_ANALYSES]


def coin_intel_headline(signal: str, related: list[dict[str, Any]], is_trending: bool) -> str:
    if related:
        lead = related[0]
        return f"{lead.get('source')} 정보 반영: {lead.get('title')}"
    if is_trending:
        return "글로벌 트렌딩 관심 상승"
    if signal == "adverse":
        return "시장 리스크를 우선 반영"
    return "직접 뉴스는 없고 시장 동향 기반 관찰"


def coin_intel_reasons(related: list[dict[str, Any]], is_trending: bool, global_payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if is_trending:
        reasons.append("CoinGecko 트렌딩")
    for item in related[:3]:
        reasons.extend(str(reason) for reason in item.get("reasons", [])[:2])
    if global_payload.get("fearGreedLabel"):
        reasons.append(f"공포탐욕 {global_payload.get('fearGreedValue')} {global_payload.get('fearGreedLabel')}")
    if global_payload.get("marketCapChange24hPct") is not None:
        reasons.append(f"글로벌 시총 24h {global_payload.get('marketCapChange24hPct')}%")
    return list(dict.fromkeys(reasons))[:6]


def market_terms_from_status(settings: TradingSettings, status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = status.get("markets", []) if isinstance(status.get("markets"), list) else []
    by_market = {str(row.get("market")): row for row in rows if isinstance(row, dict) and row.get("market")}
    markets = tuple(dict.fromkeys([*settings.markets, *by_market.keys()]))
    result: dict[str, dict[str, Any]] = {}
    for market in markets:
        symbol = market.replace("KRW-", "").upper()
        row = by_market.get(market, {})
        label = str(row.get("label") or row.get("koreanName") or market)
        terms = [symbol, *COIN_ALIASES.get(symbol, ())]
        if label and label != market:
            terms.append(label)
        result[market] = {"symbol": symbol, "label": label, "terms": list(dict.fromkeys(terms))}
    return result


def dedupe_news_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("url") or item.get("id") or item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def market_intel_summary(
    items: list[dict[str, Any]],
    trending: list[dict[str, Any]],
    global_payload: dict[str, Any],
    coin_analyses: list[dict[str, Any]],
    errors: list[str],
) -> str:
    top = coin_analyses[0] if coin_analyses else {}
    top_text = f"최상위 정보 후보는 {top.get('label')}입니다." if top else "아직 코인별 후보가 없습니다."
    fear = ""
    if global_payload.get("fearGreedValue"):
        fear = f" 공포탐욕 {global_payload.get('fearGreedValue')}({global_payload.get('fearGreedLabel')})"
    error_text = f" 수집 오류 {len(errors)}건." if errors else ""
    return f"뉴스 {len(items)}건, 트렌딩 {len(trending)}건을 반영했습니다.{fear} {top_text}{error_text}".strip()


def public_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "url": source.get("url"),
        "kind": source.get("kind"),
    }


def stable_item_id(source_id: str, title: str, link: str) -> str:
    raw = f"{source_id}:{link or title}"
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", raw)[-160:]


def decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


def decimal_to_payload(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.001")), "f")
