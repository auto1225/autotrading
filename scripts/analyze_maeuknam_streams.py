from __future__ import annotations

import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi


SOURCE_URL = "https://www.youtube.com/@-1maeuknam435/streams"
INPUT_FILE = Path("maeuknam_streams_flat.json")
REPORT_DIR = Path("reports")

CATEGORIES: dict[str, list[str]] = {
    "long_short_execution": ["롱", "숏", "롱포", "숏포", "포지션", "진입", "진입가", "매수", "매도", "청산"],
    "risk_management": ["손절", "스탑", "본절", "익절", "리스크", "비중", "분할", "절반", "손익비", "수익비", "무리"],
    "support_resistance": ["지지", "저항", "매물대", "구간", "라인", "추세선", "고점", "저점"],
    "breakout_breakdown": ["돌파", "이탈", "브레이크", "뚫", "깨", "눌림", "반등", "되돌림"],
    "wave_structure": ["파동", "엘리엇", "임펄스", "조정", "abc", "상승파", "하락파"],
    "fibonacci_levels": ["피보나치", "피보", "되돌림", "확장", "0.382", "0.5", "0.618", "618"],
    "indicators": ["이평", "이동평균", "rsi", "macd", "볼린저", "다이버", "다이버전스", "거래량", "캔들"],
    "market_context": ["비트코인", "나스닥", "달러", "금리", "도미넌스", "알트", "이더리움", "펀딩", "미결제"],
    "patience_confirmation": ["기다", "확인", "관망", "성급", "확정", "마감", "분봉", "일봉", "시간봉"],
}
ALL_TERMS = sorted({term for values in CATEGORIES.values() for term in values}, key=len, reverse=True)


def read_flat_playlist() -> list[dict[str, Any]]:
    try:
        payload = json.loads(INPUT_FILE.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        payload = json.loads(INPUT_FILE.read_text(encoding="utf-16"))
    return [entry for entry in payload.get("entries", []) if isinstance(entry, dict)]


def count_terms(text: str) -> tuple[Counter[str], Counter[str]]:
    lowered = text.lower()
    term_counts: Counter[str] = Counter()
    for term in ALL_TERMS:
        if re.search(r"[A-Za-z]", term):
            count = lowered.count(term.lower())
        else:
            count = text.count(term)
        if count:
            term_counts[term] = count
    category_counts: Counter[str] = Counter()
    for category, terms in CATEGORIES.items():
        category_counts[category] = sum(term_counts[term] for term in terms)
    return term_counts, category_counts


def extract_date(title: str) -> str:
    match = re.search(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", title or "")
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def fetch_one(api: YouTubeTranscriptApi, entry: dict[str, Any]) -> dict[str, Any]:
    video_id = str(entry.get("id") or "")
    title = str(entry.get("title") or "")
    url = str(entry.get("url") or f"https://www.youtube.com/watch?v={video_id}")
    result: dict[str, Any] = {
        "id": video_id,
        "title": title,
        "url": url,
        "date": extract_date(title),
        "duration_seconds": entry.get("duration"),
        "status": "ok",
    }
    try:
        fetched = api.fetch(video_id, languages=("ko", "en"))
        snippets = list(fetched)
        text = " ".join(snippet.text.replace("\n", " ") for snippet in snippets)
        text = re.sub(r"\s+", " ", text).strip()
        term_counts, category_counts = count_terms(text)
        duration = float(entry.get("duration") or 0)
        if not duration and snippets:
            duration = float(snippets[-1].start + snippets[-1].duration)
        hours = duration / 3600 if duration else 1
        strategy_hits = sum(category_counts.values())
        tags = [category for category, count in category_counts.items() if count >= 5]
        if not tags:
            tags = [category for category, count in category_counts.most_common(3) if count > 0]
        result.update(
            {
                "transcript_language": getattr(fetched, "language_code", ""),
                "snippet_count": len(snippets),
                "char_count": len(text),
                "strategy_hits": strategy_hits,
                "strategy_density_per_hour": round(strategy_hits / hours, 2) if hours else strategy_hits,
                "category_counts": dict(category_counts),
                "top_terms": [{"term": term, "count": count} for term, count in term_counts.most_common(14)],
                "tags": tags,
            }
        )
        return result
    except Exception as exc:
        result.update({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:500]})
        return result


def build_report(summary: dict[str, Any]) -> str:
    category_totals = Counter(summary["category_totals"])
    category_video_counts = Counter(summary["category_video_counts"])
    ok_count = summary["transcript_ok"]
    category_lines = [
        f"| {category} | {total} | {category_video_counts[category]} / {ok_count} |"
        for category, total in category_totals.most_common()
    ]
    video_lines = []
    for index, row in enumerate(summary["top_strategy_dense_videos"][:15], 1):
        tags = ", ".join(row.get("tags") or [])
        video_lines.append(
            f"| {index} | {row.get('date') or ''} | [{row.get('title')}]({row.get('url')}) | "
            f"{row.get('strategy_density_per_hour')} | {tags} |"
        )
    top_terms = ", ".join(f"{item['term']}({item['count']})" for item in summary["top_terms"][:20])
    rules = [
        "1. 방향 맞히기보다 먼저 시장 구조를 나눕니다: 고점/저점, 구간, 추세선, 지지/저항, 매물대.",
        "2. 진입은 돌파/이탈 자체보다 확인 캔들, 마감, 눌림/반등, 되돌림 이후가 핵심입니다.",
        "3. 손절/익절은 고정 퍼센트보다 무효화 구간 밖 손절, 다음 구조 구간 익절이 더 적합합니다.",
        "4. 파동/조정/피보나치 키워드가 반복되어 현재 위치가 충동파인지 조정파인지 먼저 분류해야 합니다.",
        "5. 자동매매에는 단일 신호보다 구조 점수, 확인 점수, 손익비 점수, 변동성 점수, 비중 점수를 분리해야 합니다.",
    ]
    return f"""# 매억남 YouTube Streams Trading Analysis

Source: {SOURCE_URL}
Generated: {summary['generated_at']}

## Coverage

- Videos listed: {summary['video_count']}
- Transcripts fetched: {summary['transcript_ok']}
- Transcript failures: {summary['transcript_failed']}
- Total stream duration: {summary['total_duration_hours']} hours
- Transcript characters analyzed: {summary['total_transcript_chars']}

## Top Terms

{top_terms}

## Category Frequency

| Category | Keyword hits | Videos with hits |
|---|---:|---:|
{chr(10).join(category_lines)}

## Most Strategy-Dense Videos

| Rank | Date | Video | Hits/hour | Tags |
|---:|---|---|---:|---|
{chr(10).join(video_lines)}

## Extracted Trading-Rule Shape

{chr(10).join(rules)}

## Implementation Notes For The Bot

- Add a market-structure layer before entry scoring: range, support/resistance, recent high/low, trendline proxy, volatility regime.
- Require a confirmation trigger: candle close beyond level, retest/failed retest, volume expansion, or rejection wick.
- Position sizing should be scenario-based: strong confirmation uses higher margin, weak confirmation stays small or watches.
- Stop should be placed outside the invalidation level, not a fixed percent only.
- Take profit should be staged: first target near next level, remainder trailed by structure.
- Contrarian execution should be tested as one mode, but execution direction should ultimately follow measured win rate by structure type.

## Machine Files

- JSON detail: reports/maeuknam_streams_analysis.json
"""


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    entries = read_flat_playlist()
    api = YouTubeTranscriptApi()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_one, api, entry) for entry in entries]
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 25 == 0 or index == len(entries):
                print(f"processed {index}/{len(entries)}")
    order = {entry.get("id"): index for index, entry in enumerate(entries)}
    results.sort(key=lambda row: order.get(row.get("id"), 10**9))
    ok = [row for row in results if row.get("status") == "ok"]
    failed = [row for row in results if row.get("status") != "ok"]
    category_totals: Counter[str] = Counter()
    category_video_counts: Counter[str] = Counter()
    term_totals: Counter[str] = Counter()
    for row in ok:
        for category, count in row.get("category_counts", {}).items():
            category_totals[category] += count
            if count > 0:
                category_video_counts[category] += 1
        for item in row.get("top_terms", []):
            term_totals[item["term"]] += item["count"]
    ranked = sorted(ok, key=lambda row: row.get("strategy_density_per_hour", 0), reverse=True)
    summary = {
        "source_url": SOURCE_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_title": "MAEUKNAM - The man who makes a million a month",
        "video_count": len(entries),
        "transcript_ok": len(ok),
        "transcript_failed": len(failed),
        "failure_types": dict(Counter(row.get("error_type", "unknown") for row in failed)),
        "total_duration_hours": round(sum(float(row.get("duration_seconds") or 0) for row in results) / 3600, 2),
        "total_transcript_chars": sum(row.get("char_count", 0) for row in ok),
        "category_totals": dict(category_totals),
        "category_video_counts": dict(category_video_counts),
        "top_terms": [{"term": term, "count": count} for term, count in term_totals.most_common(30)],
        "top_strategy_dense_videos": [
            {
                "date": row.get("date"),
                "title": row.get("title"),
                "url": row.get("url"),
                "duration_minutes": round(float(row.get("duration_seconds") or 0) / 60, 1),
                "strategy_density_per_hour": row.get("strategy_density_per_hour"),
                "tags": row.get("tags"),
                "top_terms": row.get("top_terms")[:6],
            }
            for row in ranked[:25]
        ],
        "videos": results,
    }
    (REPORT_DIR / "maeuknam_streams_analysis.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORT_DIR / "maeuknam_streams_analysis.md").write_text(build_report(summary), encoding="utf-8")
    print(
        json.dumps(
            {
                "videos": len(entries),
                "ok": len(ok),
                "failed": len(failed),
                "failure_types": summary["failure_types"],
                "hours": summary["total_duration_hours"],
                "chars": summary["total_transcript_chars"],
                "top_categories": category_totals.most_common(8),
                "top_terms": term_totals.most_common(12),
                "report": str(REPORT_DIR / "maeuknam_streams_analysis.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
