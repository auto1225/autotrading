from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_DIR = ROOT / "reports" / "maeuknam_transcripts"
ANALYSIS_DIR = ROOT / "reports" / "maeuknam_video_analysis"
DECISION_REPORT = ROOT / "reports" / "maeuknam_decision_structure_report.md"


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "market_context": [
        "비트코인",
        "시장",
        "상승장",
        "하락장",
        "기관",
        "고래",
        "자금",
        "금리",
        "달러",
        "ETF",
        "유동성",
        "거시",
    ],
    "direction_judgment": [
        "롱",
        "숏",
        "상승",
        "하락",
        "반등",
        "빠질",
        "올라",
        "내려",
        "상방",
        "하방",
        "돌파",
        "이탈",
    ],
    "chart_structure": [
        "고점",
        "저점",
        "지지",
        "저항",
        "라인",
        "채널",
        "추세",
        "상단",
        "하단",
        "돌파",
        "이탈",
        "눌림",
    ],
    "entry_trigger": [
        "진입",
        "들어가",
        "매수",
        "매도",
        "타점",
        "자리",
        "확인",
        "눌림",
        "반등",
        "돌파",
        "이탈",
        "받고",
    ],
    "stop_invalidation": [
        "손절",
        "스탑",
        "본절",
        "깨면",
        "이탈하면",
        "무효",
        "틀리면",
        "리스크",
        "손실",
        "마지노선",
    ],
    "take_profit_exit": [
        "익절",
        "수익",
        "목표",
        "청산",
        "먹고",
        "분할",
        "트레일",
        "올라가면",
        "내려가면",
        "마무리",
    ],
    "timeframe": [
        "분봉",
        "시간봉",
        "일봉",
        "주봉",
        "월봉",
        "캔들",
        "마감",
        "단기",
        "중기",
        "장기",
    ],
    "wave_position": [
        "파동",
        "1파",
        "2파",
        "3파",
        "4파",
        "5파",
        "조정",
        "ABC",
        "복합",
        "임펄스",
    ],
}

LONG_TERMS = ["롱", "매수", "상승", "반등", "올라", "상방", "돌파", "지지", "눌림"]
SHORT_TERMS = ["숏", "매도", "하락", "빠질", "내려", "하방", "이탈", "저항"]
STRUCTURE_TERMS = CATEGORY_KEYWORDS["chart_structure"]
ENTRY_TERMS = CATEGORY_KEYWORDS["entry_trigger"]
STOP_TERMS = CATEGORY_KEYWORDS["stop_invalidation"]
TARGET_TERMS = CATEGORY_KEYWORDS["take_profit_exit"]
WAVE_TERMS = CATEGORY_KEYWORDS["wave_position"]
TRADING_ANCHORS = [
    "비트코인",
    "차트",
    "가격",
    "캔들",
    "봉",
    "롱",
    "숏",
    "매수",
    "매도",
    "진입",
    "손절",
    "익절",
    "청산",
    "고점",
    "저점",
    "지지",
    "저항",
    "채널",
    "추세",
    "파동",
    "조정",
    "반등",
    "돌파",
    "이탈",
    "타점",
    "포지션",
    "구간",
    "자리",
]
NOISE_TERMS = [
    "머리카락",
    "모발",
    "소변",
    "국과수",
    "대회",
    "수익금",
    "후원",
    "구독",
    "좋아요",
    "공지",
    "가족",
    "협찬",
    "댓글",
]


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{sec:02d}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def keyword_score(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(keyword.lower()) for keyword in keywords)


def trade_context_score(text: str) -> int:
    return keyword_score(text, TRADING_ANCHORS)


def noise_score(text: str) -> int:
    return keyword_score(text, NOISE_TERMS)


def is_trade_context(text: str, category: str) -> bool:
    anchors = trade_context_score(text)
    noise = noise_score(text)
    category_hits = keyword_score(text, CATEGORY_KEYWORDS[category])
    if category_hits <= 0:
        return False
    if anchors >= 2 and noise <= anchors:
        return True
    if category in {"entry_trigger", "stop_invalidation", "take_profit_exit"}:
        return anchors >= 1 and category_hits >= 2 and noise <= anchors
    if category == "market_context":
        return any(term in text for term in ["비트코인", "시장", "금리", "기관", "고래", "자금", "달러", "ETF"])
    return False


def sentence_preview(text: str, limit: int = 180) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def segment_context(segments: list[dict[str, Any]], index: int, radius: int = 1) -> str:
    rows = segments[max(0, index - radius) : min(len(segments), index + radius + 1)]
    return normalize_text(" ".join(str(row.get("text") or "") for row in rows))


def collect_category_evidence(
    segments: list[dict[str, Any]],
    category: str,
    max_items: int = 6,
) -> list[dict[str, Any]]:
    keywords = CATEGORY_KEYWORDS[category]
    scored: list[tuple[int, float, dict[str, Any]]] = []
    for index, segment in enumerate(segments):
        context = segment_context(segments, index)
        if not is_trade_context(context, category):
            continue
        score = keyword_score(context, keywords) + trade_context_score(context)
        if score <= 0:
            continue
        start = float(segment.get("start") or 0)
        scored.append(
            (
                score,
                start,
                {
                    "time": format_time(start),
                    "start": start,
                    "score": score,
                    "text": sentence_preview(context, 220),
                },
            )
        )
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    selected: list[dict[str, Any]] = []
    used_buckets: set[int] = set()
    for _, start, item in scored:
        bucket = int(start // 90)
        if bucket in used_buckets:
            continue
        used_buckets.add(bucket)
        selected.append(item)
        if len(selected) >= max_items:
            break
    selected.sort(key=lambda row: float(row.get("start") or 0))
    return selected


def count_category_hits(segments: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for index, segment in enumerate(segments):
        context = segment_context(segments, index)
        for category, keywords in CATEGORY_KEYWORDS.items():
            if is_trade_context(context, category):
                counts[category] += keyword_score(str(segment.get("text") or ""), keywords)
    return {category: counts.get(category, 0) for category in CATEGORY_KEYWORDS}


def infer_bias(segments: list[dict[str, Any]]) -> dict[str, Any]:
    focused_contexts = []
    for index, segment in enumerate(segments):
        context = segment_context(segments, index)
        if trade_context_score(context) >= 2 and noise_score(context) <= trade_context_score(context):
            focused_contexts.append(str(segment.get("text") or ""))
    text = " ".join(focused_contexts)
    long_score = keyword_score(text, LONG_TERMS)
    short_score = keyword_score(text, SHORT_TERMS)
    if long_score >= short_score * 1.35 and long_score >= 3:
        primary = "LONG"
    elif short_score >= long_score * 1.35 and short_score >= 3:
        primary = "SHORT"
    elif long_score or short_score:
        primary = "MIXED"
    else:
        primary = "UNCLEAR"
    return {
        "primary_bias": primary,
        "long_score": long_score,
        "short_score": short_score,
        "explanation": {
            "LONG": "롱/상승/반등 계열 표현이 숏/하락 표현보다 뚜렷하게 많습니다.",
            "SHORT": "숏/하락/이탈 계열 표현이 롱/상승 표현보다 뚜렷하게 많습니다.",
            "MIXED": "상승과 하락 시나리오가 함께 언급되어 조건부 판단으로 봐야 합니다.",
            "UNCLEAR": "방향 표현이 충분하지 않아 이 영상만으로 방향을 확정하기 어렵습니다.",
        }[primary],
    }


def build_summary(category: str, evidence: list[dict[str, Any]], hits: int) -> str:
    if not evidence:
        return "명확한 근거 구간이 부족합니다."
    first = max(evidence, key=lambda row: int(row.get("score") or 0))["text"]
    if category == "market_context":
        return f"시장 배경 언급이 {hits}회 잡혔고, 대표 구간은 '{sentence_preview(first, 90)}'입니다."
    if category == "direction_judgment":
        return f"방향 판단 언급이 {hits}회 잡혔습니다. 핵심은 '{sentence_preview(first, 90)}' 구간입니다."
    if category == "chart_structure":
        return f"고점/저점, 지지/저항, 채널/라인 같은 구조 판단이 {hits}회 잡혔습니다."
    if category == "entry_trigger":
        return f"진입 조건은 추격보다 확인, 눌림, 반등, 돌파 여부 중심으로 {hits}회 등장합니다."
    if category == "stop_invalidation":
        return f"손절/무효화 언급이 {hits}회 잡혔습니다. 진입 전 리스크 위치를 먼저 보는 영상입니다."
    if category == "take_profit_exit":
        return f"수익 실현/청산 언급이 {hits}회 잡혔습니다. 목표 도달 후 분할 또는 정리 맥락을 확인해야 합니다."
    if category == "timeframe":
        return f"분봉/시간봉/일봉 등 시간 프레임 언급이 {hits}회 잡혔습니다."
    if category == "wave_position":
        return f"파동/조정 위치 언급이 {hits}회 잡혔습니다. 방향보다 현재 파동 위치 해석이 중요합니다."
    return f"{category} 근거가 {hits}회 잡혔습니다."


def infer_trade_readiness(category_hits: dict[str, int]) -> dict[str, Any]:
    has_structure = category_hits.get("chart_structure", 0) >= 4
    has_entry = category_hits.get("entry_trigger", 0) >= 3
    has_stop = category_hits.get("stop_invalidation", 0) >= 2
    has_exit = category_hits.get("take_profit_exit", 0) >= 2
    has_timeframe = category_hits.get("timeframe", 0) >= 1
    has_wave = category_hits.get("wave_position", 0) >= 3
    score = sum([has_structure, has_entry, has_stop, has_exit, has_timeframe, has_wave])
    if has_structure and has_entry and has_stop and (has_exit or has_wave):
        level = "ACTIONABLE"
        reason = "구조, 진입, 손절이 함께 잡혀 있고 청산 또는 파동 필터까지 있어 실전 규칙 후보로 볼 수 있습니다."
    elif score >= 3:
        level = "CONDITIONAL"
        reason = "일부 조건은 잡히지만 빠진 축이 있어 차트 프레임 확인 후 규칙화해야 합니다."
    else:
        level = "LEARNING_ONLY"
        reason = "매매 실행 조건보다 시장 설명이나 회고 비중이 높아 직접 규칙화하기 어렵습니다."
    return {"level": level, "score": score, "reason": reason}


def infer_scenario_plan(
    bias: dict[str, Any],
    category_hits: dict[str, int],
    evidence_by_category: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    direction = bias["primary_bias"]
    if direction == "LONG":
        entry_if = "지지/채널/저점 구조가 유지되고 눌림 후 반등 확인이 나올 때만 롱 후보로 본다."
        invalidated_if = "저점 또는 채널 하단이 깨지고 회복하지 못하면 롱 시나리오를 폐기한다."
    elif direction == "SHORT":
        entry_if = "저항/채널 상단에서 막히거나 핵심 지지 이탈 후 되돌림 실패가 나올 때만 숏 후보로 본다."
        invalidated_if = "이탈 구간을 빠르게 회복하거나 직전 고점을 돌파하면 숏 시나리오를 폐기한다."
    elif direction == "MIXED":
        entry_if = "상승/하락 양쪽 시나리오가 모두 있어, 지지/저항 중 어느 쪽이 먼저 깨지는지 확인 후 진입한다."
        invalidated_if = "방향 확인 전 추격 진입은 금지하고, 확인한 구조가 반대로 회복되면 폐기한다."
    else:
        entry_if = "방향 근거가 약하므로 이 영상은 바로 진입 신호로 쓰지 않는다."
        invalidated_if = "구조, 진입, 손절 중 하나라도 비어 있으면 매매 규칙 후보에서 제외한다."
    stop_logic = (
        "손절선은 진입가가 아니라 시나리오가 틀렸다고 판단되는 구조선 기준으로 둔다."
        if category_hits.get("stop_invalidation", 0)
        else "손절 근거가 부족하므로 별도 차트 검증 없이는 진입하지 않는다."
    )
    if category_hits.get("take_profit_exit", 0) >= 2:
        target_logic = "목표가는 다음 저항/지지 또는 파동 목표 부근에서 분할 청산하고 남은 물량은 추세 유지 여부로 관리한다."
    elif category_hits.get("wave_position", 0) >= 3:
        target_logic = "직접적인 익절 언급은 약하므로 파동 목표와 다음 구조선을 임시 목표로만 쓰고, 별도 차트 검증 전에는 거래하지 않는다."
    else:
        target_logic = "익절 근거가 부족하므로 목표가 없이 진입하지 않는다."
    avoid_if = "손절 거리가 멀거나, 구조 확인 없이 단어 하나만으로 방향을 정해야 하는 구간은 피한다."
    if not evidence_by_category.get("chart_structure"):
        avoid_if += " 특히 차트 구조 근거가 부족한 영상은 학습용으로만 둔다."
    return {
        "entry_if": entry_if,
        "invalidated_if": invalidated_if,
        "stop_logic": stop_logic,
        "target_logic": target_logic,
        "avoid_if": avoid_if,
    }


def infer_algorithm_rules(
    bias: dict[str, Any],
    readiness: dict[str, Any],
    category_hits: dict[str, int],
) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = [
        {
            "name": "structure_first",
            "rule": "방향 신호보다 지지/저항/채널/고점저점 구조 확인을 우선한다.",
            "reason": f"차트 구조 히트 {category_hits.get('chart_structure', 0)}회",
        },
        {
            "name": "stop_before_entry",
            "rule": "진입 전에 손절/무효화 가격을 먼저 계산하고, 손절 폭이 크면 거래하지 않는다.",
            "reason": f"손절/무효화 히트 {category_hits.get('stop_invalidation', 0)}회",
        },
        {
            "name": "conditional_aggression",
            "rule": "공격적 진입은 구조, 진입조건, 손절조건이 동시에 잡힌 ACTIONABLE 영상 패턴에서만 허용한다.",
            "reason": f"현재 판정 {readiness['level']}",
        },
    ]
    if bias["primary_bias"] in {"LONG", "SHORT"}:
        rules.append(
            {
                "name": "direction_bias",
                "rule": f"이 영상은 {bias['primary_bias']} 우위 시나리오로 분류하되, 반대 구조 돌파/이탈 시 즉시 폐기한다.",
                "reason": f"long={bias['long_score']}, short={bias['short_score']}",
            }
        )
    if category_hits.get("wave_position", 0) >= 3:
        rules.append(
            {
                "name": "wave_filter",
                "rule": "파동 위치가 조정 중인지, 3파/5파 진행 중인지 확인한 뒤 진입 방향을 확정한다.",
                "reason": f"파동/조정 히트 {category_hits.get('wave_position', 0)}회",
            }
        )
    return rules


def quality_flags(
    category_hits: dict[str, int],
    evidence_by_category: dict[str, list[dict[str, Any]]],
) -> list[str]:
    flags: list[str] = []
    if category_hits.get("entry_trigger", 0) == 0:
        flags.append("진입 조건 근거가 부족합니다.")
    if category_hits.get("stop_invalidation", 0) == 0:
        flags.append("손절/무효화 조건 근거가 부족합니다.")
    if category_hits.get("chart_structure", 0) < 3:
        flags.append("차트 구조 근거가 약합니다. 영상 프레임 확인이 필요합니다.")
    if not evidence_by_category.get("timeframe"):
        flags.append("시간 프레임이 명확하지 않습니다.")
    if not flags:
        flags.append("기본 매매 판단 축이 모두 감지되었습니다.")
    return flags


def build_decision_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    segments = payload.get("segments") or []
    category_hits = count_category_hits(segments)
    evidence_by_category = {
        category: collect_category_evidence(segments, category)
        for category in CATEGORY_KEYWORDS
    }
    sections = {
        category: {
            "hits": category_hits.get(category, 0),
            "summary": build_summary(category, evidence_by_category[category], category_hits.get(category, 0)),
            "evidence": evidence_by_category[category],
        }
        for category in CATEGORY_KEYWORDS
    }
    bias = infer_bias(segments)
    readiness = infer_trade_readiness(category_hits)
    scenario_plan = infer_scenario_plan(bias, category_hits, evidence_by_category)
    return {
        "schema": "maeuknam_decision_structure.v1",
        "id": payload.get("id"),
        "title": payload.get("title"),
        "url": payload.get("url"),
        "duration": payload.get("duration"),
        "model": payload.get("model"),
        "bias": bias,
        "trade_readiness": readiness,
        "category_hits": category_hits,
        "sections": sections,
        "scenario_plan": scenario_plan,
        "algorithm_rules": infer_algorithm_rules(bias, readiness, category_hits),
        "quality_flags": quality_flags(category_hits, evidence_by_category),
    }


def read_transcript(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def transcript_paths(model: str) -> list[Path]:
    return sorted(TRANSCRIPT_DIR.glob(f"*.{model}.ko.json"))


def decision_path(video_id: str) -> Path:
    return ANALYSIS_DIR / f"{video_id}.decision.json"


def write_decision_json(decision: dict[str, Any]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    decision_path(str(decision["id"])).write_text(
        json.dumps(decision, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_decision_files() -> list[dict[str, Any]]:
    decisions = []
    for path in sorted(ANALYSIS_DIR.glob("*.decision.json")):
        decisions.append(json.loads(path.read_text(encoding="utf-8")))
    return decisions


def aggregate_decisions(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    readiness = Counter()
    bias = Counter()
    categories = Counter()
    rules = Counter()
    for decision in decisions:
        readiness[decision.get("trade_readiness", {}).get("level", "UNKNOWN")] += 1
        bias[decision.get("bias", {}).get("primary_bias", "UNKNOWN")] += 1
        categories.update(decision.get("category_hits", {}))
        for rule in decision.get("algorithm_rules", []):
            rules[rule.get("name", "unknown")] += 1
    return {
        "readiness": dict(readiness),
        "bias": dict(bias),
        "categories": dict(categories),
        "rules": dict(rules),
    }


def write_decision_report(decisions: list[dict[str, Any]]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    summary = aggregate_decisions(decisions)
    lines = [
        "# 매억남 영상 매매 판단 구조 분석",
        "",
        f"- 구조 분석 완료 영상: {len(decisions)}개",
        "- 방식: STT 구간을 매매 판단 축으로 재분류해서 시장상황, 방향판단, 차트구조, 진입조건, 손절/무효화, 익절/청산, 시간프레임을 분리합니다.",
        "- 주의: 이 리포트는 투자 조언이 아니라 영상 속 판단 구조를 알고리즘 후보로 정리한 자료입니다.",
        "",
        "## 전체 요약",
        "",
        f"- 방향 분포: {json.dumps(summary['bias'], ensure_ascii=False)}",
        f"- 규칙화 가능성: {json.dumps(summary['readiness'], ensure_ascii=False)}",
        f"- 판단 축 누적: {json.dumps(summary['categories'], ensure_ascii=False)}",
        "",
        "## 반복적으로 보이는 매매 구조",
        "",
        "- 방향보다 구조가 먼저입니다. 지지/저항, 채널, 고점/저점, 추세선이 잡히지 않으면 진입 신호로 쓰지 않습니다.",
        "- 손절선이 먼저입니다. 손절선이 멀면 아무리 방향이 좋아 보여도 추격 진입 품질을 낮춥니다.",
        "- 공격성은 조건부입니다. 구조, 진입 트리거, 손절/무효화, 목표가가 동시에 잡힌 경우에만 레버리지나 비중을 올릴 수 있습니다.",
        "- 파동/조정 위치는 필터입니다. 상승/하락 단어 자체보다 현재가 조정 끝인지, 3파/5파 진행인지가 더 중요합니다.",
        "",
    ]
    for index, decision in enumerate(decisions, 1):
        title = decision.get("title") or decision.get("id")
        bias = decision.get("bias", {})
        readiness = decision.get("trade_readiness", {})
        plan = decision.get("scenario_plan", {})
        lines.extend(
            [
                f"## {index}. {title}",
                "",
                f"- URL: {decision.get('url')}",
                f"- 방향 판단: {bias.get('primary_bias')} (long={bias.get('long_score')}, short={bias.get('short_score')})",
                f"- 규칙화 가능성: {readiness.get('level')} - {readiness.get('reason')}",
                "",
                "### 매매 판단 구조",
                "",
                f"- 시장상황: {decision['sections']['market_context']['summary']}",
                f"- 방향판단: {decision['sections']['direction_judgment']['summary']}",
                f"- 차트구조: {decision['sections']['chart_structure']['summary']}",
                f"- 진입조건: {decision['sections']['entry_trigger']['summary']}",
                f"- 손절/무효화: {decision['sections']['stop_invalidation']['summary']}",
                f"- 익절/청산: {decision['sections']['take_profit_exit']['summary']}",
                f"- 시간프레임: {decision['sections']['timeframe']['summary']}",
                f"- 파동위치: {decision['sections']['wave_position']['summary']}",
                "",
                "### 시나리오 계획",
                "",
                f"- 진입: {plan.get('entry_if')}",
                f"- 무효화: {plan.get('invalidated_if')}",
                f"- 손절: {plan.get('stop_logic')}",
                f"- 목표/청산: {plan.get('target_logic')}",
                f"- 회피: {plan.get('avoid_if')}",
                "",
                "### 핵심 근거 구간",
                "",
            ]
        )
        evidence_pool: list[dict[str, Any]] = []
        for section_name in [
            "chart_structure",
            "entry_trigger",
            "stop_invalidation",
            "take_profit_exit",
            "wave_position",
        ]:
            for item in decision["sections"][section_name]["evidence"][:2]:
                evidence_pool.append({"section": section_name, **item})
        evidence_pool.sort(key=lambda row: float(row.get("start") or 0))
        for item in evidence_pool[:10]:
            lines.append(f"- {item.get('time')} [{item.get('section')}]: {item.get('text')}")
        lines.extend(["", "### 알고리즘 후보 규칙", ""])
        for rule in decision.get("algorithm_rules", []):
            lines.append(f"- {rule.get('name')}: {rule.get('rule')} ({rule.get('reason')})")
        lines.extend(["", "### 품질 플래그", ""])
        for flag in decision.get("quality_flags", []):
            lines.append(f"- {flag}")
        lines.append("")
    DECISION_REPORT.write_text("\n".join(lines), encoding="utf-8")


def rebuild_decisions(model: str, limit: int | None = None, video_id: str | None = None) -> list[dict[str, Any]]:
    paths = transcript_paths(model)
    if video_id:
        paths = [path for path in paths if path.name.startswith(f"{video_id}.")]
    if limit is not None:
        paths = paths[:limit]
    decisions = []
    for path in paths:
        payload = read_transcript(path)
        decision = build_decision_analysis(payload)
        write_decision_json(decision)
        decisions.append(decision)
    write_decision_report(load_decision_files())
    return decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--video-id")
    args = parser.parse_args()
    decisions = rebuild_decisions(args.model, args.limit, args.video_id)
    print(
        json.dumps(
            {
                "rebuilt": len(decisions),
                "total_decisions": len(load_decision_files()),
                "report": str(DECISION_REPORT),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
