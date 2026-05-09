from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "reports" / "maeuknam_video_analysis"
STRATEGY_JSON = ROOT / "reports" / "maeuknam_strategy_cards.json"
STRATEGY_REPORT = ROOT / "reports" / "maeuknam_strategy_cards.md"


FEATURE_KEYWORDS: dict[str, list[str]] = {
    "support": ["지지", "저점", "하단", "바닥", "받", "버티", "구간", "자리", "라인"],
    "resistance": ["저항", "고점", "상단", "막히", "갱신", "돌파", "목표"],
    "pullback": ["눌림", "조정", "빠지", "내려오", "되돌림", "반등", "기다"],
    "breakout": ["돌파", "뚫", "넘", "갱신", "올라가", "상방", "확인"],
    "failure": ["이탈", "깨", "실패", "무효", "틀리", "회복하지", "하락"],
    "entry": ["진입", "들어가", "매수", "타점", "자리", "확인", "시장가", "예약"],
    "stop": ["손절", "스탑", "본절", "약손절", "마지노선", "리스크", "손실"],
    "target": ["익절", "청산", "수익", "먹", "목표", "분할", "트레일"],
    "wave": ["파동", "1파", "2파", "3파", "4파", "5파", "ABC", "조정", "임펄스", "엔딩"],
    "timeframe": ["분봉", "시간봉", "일봉", "주봉", "월봉", "마감", "캔들"],
    "avoid_chase": ["추격", "늦", "급등", "손절", "멀", "중앙", "애매", "기다"],
}

TRADING_ANCHORS = [
    "비트코인",
    "BTC",
    "차트",
    "가격",
    "캔들",
    "분봉",
    "시간봉",
    "일봉",
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
    "하락",
    "상승",
]

NOISE_TERMS = [
    "이준석",
    "정치",
    "선거",
    "머리카락",
    "모발",
    "소변",
    "국과수",
    "대회",
    "수익금",
    "후원",
    "구독",
    "좋아요",
    "댓글",
    "공지",
    "협찬",
]


TECHNIQUE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "support_pullback_long": {
        "name": "지지 확인 눌림 롱",
        "direction": "LONG",
        "required": ["support", "pullback", "entry", "stop"],
        "secondary": ["wave", "target", "timeframe"],
        "description": "상승 또는 중립 구조에서 가격이 눌린 뒤 지지/저점/채널 하단을 지키고 반등 확인이 나올 때만 롱을 검토합니다.",
    },
    "breakout_retest_long": {
        "name": "돌파 후 리테스트 롱",
        "direction": "LONG",
        "required": ["breakout", "support", "entry", "stop"],
        "secondary": ["resistance", "target", "timeframe"],
        "description": "저항 돌파 이후 되돌림에서 돌파 구간이 지지로 전환되는지 확인하고, 회복 실패 시 즉시 무효화합니다.",
    },
    "wave_continuation_long": {
        "name": "파동 진행 롱",
        "direction": "LONG",
        "required": ["wave", "pullback", "entry", "stop"],
        "secondary": ["support", "target", "timeframe"],
        "description": "조정파가 끝나고 3파/5파 또는 임펄스 진행 가능성이 커질 때만 진입을 검토합니다.",
    },
    "failed_breakdown_reversal_long": {
        "name": "이탈 실패 반전 롱",
        "direction": "LONG",
        "required": ["failure", "support", "entry", "stop"],
        "secondary": ["pullback", "target", "wave"],
        "description": "하락 이탈이 이어지지 않고 다시 구조 안으로 회복될 때 손절을 짧게 잡는 반전형 롱입니다.",
    },
    "resistance_failure_short": {
        "name": "저항 실패 숏",
        "direction": "SHORT",
        "required": ["resistance", "failure", "entry", "stop"],
        "secondary": ["target", "timeframe", "pullback"],
        "description": "저항/채널 상단에서 돌파 실패 또는 지지 이탈 후 회복 실패가 나올 때만 숏을 검토합니다.",
    },
}


def load_decisions() -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for path in sorted(ANALYSIS_DIR.glob("*.decision.json")):
        decisions.append(json.loads(path.read_text(encoding="utf-8")))
    return decisions


def count_terms(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(lower.count(term.lower()) for term in terms)


def is_trading_evidence(text: str) -> bool:
    anchor_count = count_terms(text, TRADING_ANCHORS)
    noise_count = count_terms(text, NOISE_TERMS)
    return anchor_count >= 2 and noise_count == 0


def evidence_rows(decision: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    sections = decision.get("sections") or {}
    for section_name in [
        "chart_structure",
        "entry_trigger",
        "stop_invalidation",
        "take_profit_exit",
        "wave_position",
        "direction_judgment",
        "timeframe",
    ]:
        section = sections.get(section_name) or {}
        for item in section.get("evidence") or []:
            text = str(item.get("text") or "")
            if is_trading_evidence(text):
                rows.append({"time": str(item.get("time") or ""), "section": section_name, "text": text})
    return rows


def evidence_text(decision: dict[str, Any]) -> str:
    chunks: list[str] = [row["text"] for row in evidence_rows(decision)]
    for value in (decision.get("scenario_plan") or {}).values():
        chunks.append(str(value or ""))
    return " ".join(chunks)


def feature_scores(decision: dict[str, Any]) -> dict[str, int]:
    text = evidence_text(decision)
    scores = {name: count_terms(text, terms) for name, terms in FEATURE_KEYWORDS.items()}
    category_hits = decision.get("category_hits") or {}
    scores["entry"] += min(int(category_hits.get("entry_trigger") or 0), 8)
    scores["stop"] += min(int(category_hits.get("stop_invalidation") or 0), 6)
    scores["target"] += min(int(category_hits.get("take_profit_exit") or 0), 5)
    scores["wave"] += min(int(category_hits.get("wave_position") or 0), 8)
    scores["timeframe"] += min(int(category_hits.get("timeframe") or 0), 3)
    scores["support"] += min(int(category_hits.get("chart_structure") or 0) // 3, 5)
    scores["breakout"] += min(int(category_hits.get("direction_judgment") or 0) // 12, 4)
    return scores


def feature_present(scores: dict[str, int], feature: str) -> bool:
    thresholds = {
        "support": 3,
        "resistance": 2,
        "pullback": 2,
        "breakout": 2,
        "failure": 2,
        "entry": 4,
        "stop": 2,
        "target": 2,
        "wave": 3,
        "timeframe": 1,
        "avoid_chase": 1,
    }
    return scores.get(feature, 0) >= thresholds.get(feature, 1)


def technique_match_score(decision: dict[str, Any], technique: dict[str, Any], scores: dict[str, int]) -> float:
    bias = (decision.get("bias") or {}).get("primary_bias", "UNCLEAR")
    direction = technique["direction"]
    if direction == "LONG" and bias == "SHORT":
        return 0.0
    if direction == "SHORT" and bias == "LONG":
        short_score = int((decision.get("bias") or {}).get("short_score") or 0)
        long_score = int((decision.get("bias") or {}).get("long_score") or 0)
        if short_score < max(3, long_score * 0.6):
            return 0.0
    required = technique["required"]
    secondary = technique["secondary"]
    required_hits = sum(1 for feature in required if feature_present(scores, feature))
    secondary_hits = sum(1 for feature in secondary if feature_present(scores, feature))
    if required_hits < len(required):
        return 0.0
    base = required_hits / len(required)
    support = secondary_hits / max(1, len(secondary))
    evidence_bonus = min(0.08, len(evidence_rows(decision)) / 80)
    readiness_bonus = 0.05 if (decision.get("trade_readiness") or {}).get("level") == "ACTIONABLE" else 0.0
    return round(min(1.0, (base * 0.70) + (support * 0.17) + readiness_bonus + evidence_bonus), 4)


def classify_decision(decision: dict[str, Any]) -> list[dict[str, Any]]:
    scores = feature_scores(decision)
    matches: list[dict[str, Any]] = []
    for key, technique in TECHNIQUE_DEFINITIONS.items():
        score = technique_match_score(decision, technique, scores)
        if score > 0:
            matches.append({"technique": key, "score": score})
    matches.sort(key=lambda row: row["score"], reverse=True)
    return matches[:3]


def compact_evidence(decision: dict[str, Any], feature_names: list[str], max_items: int = 6) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in evidence_rows(decision):
        text = row["text"]
        if not any(count_terms(text, FEATURE_KEYWORDS[feature]) for feature in feature_names if feature in FEATURE_KEYWORDS):
            continue
        key = f"{row.get('time')}:{text[:50]}"
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= max_items:
            return selected
    return selected


def build_cards(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actionable = [
        decision
        for decision in decisions
        if (decision.get("trade_readiness") or {}).get("level") == "ACTIONABLE"
    ]
    buckets: dict[str, list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for decision in actionable:
        for match in classify_decision(decision):
            buckets[match["technique"]].append((decision, float(match["score"])))

    cards: list[dict[str, Any]] = []
    for key, rows in buckets.items():
        if not rows:
            continue
        rows.sort(key=lambda row: row[1], reverse=True)
        definition = TECHNIQUE_DEFINITIONS[key]
        match_scores = [score for _, score in rows]
        support_count = len(rows)
        avg_score = round(statistics.mean(match_scores), 4)
        confidence = min(0.88, 0.28 + min(0.32, support_count / 110) + avg_score * 0.18)
        required = definition["required"]
        secondary = definition["secondary"]
        examples = []
        for decision, score in rows[:5]:
            examples.append(
                {
                    "id": decision.get("id"),
                    "title": decision.get("title"),
                    "url": decision.get("url"),
                    "match_score": score,
                    "bias": decision.get("bias"),
                    "trade_readiness": decision.get("trade_readiness"),
                    "evidence": compact_evidence(decision, required + secondary),
                }
            )
        cards.append(
            {
                "id": key,
                "name": definition["name"],
                "direction": definition["direction"],
                "description": definition["description"],
                "support_count": support_count,
                "avg_match_score": avg_score,
                "confidence": round(confidence, 4),
                "entry_algorithm": build_entry_algorithm(key),
                "risk_algorithm": build_risk_algorithm(key),
                "exit_algorithm": build_exit_algorithm(key),
                "avoid_conditions": build_avoid_conditions(key),
                "score_formula": build_score_formula(key),
                "validation_plan": build_validation_plan(key),
                "examples": examples,
            }
        )
    cards.sort(key=lambda row: (row["support_count"], row["avg_match_score"]), reverse=True)
    return cards


def build_entry_algorithm(key: str) -> list[str]:
    common = [
        "상위 레짐이 강한 하락이 아니거나, 최소한 단기 구조가 회복 중인지 확인한다.",
        "진입 전에 손절 기준 구조선이 먼저 계산되어 있어야 한다.",
        "손절폭 대비 1차 목표까지 기대 보상이 최소 1.4배 이상일 때만 후보로 남긴다.",
    ]
    specific = {
        "support_pullback_long": [
            "최근 상승 또는 박스 상단 돌파 후 눌림이 나온다.",
            "가격이 이전 저항의 지지 전환 구간, 채널 하단, 직전 저점 위에서 멈춘다.",
            "반등 캔들이 나오거나 저점 갱신 실패가 확인되면 분할 진입한다.",
        ],
        "breakout_retest_long": [
            "핵심 저항 또는 직전 고점을 거래량/캔들 종가 기준으로 돌파한다.",
            "되돌림에서 돌파 구간을 이탈하지 않고 지지 전환을 확인한다.",
            "재상승 캔들이 돌파 구간 위에서 마감하면 진입한다.",
        ],
        "wave_continuation_long": [
            "조정파가 충분히 진행된 뒤 3파 또는 5파 진행 가능성을 확인한다.",
            "조정 저점이 무너지지 않고 반등 구조가 형성된다.",
            "파동 무효화 지점이 가까울 때만 진입한다.",
        ],
        "failed_breakdown_reversal_long": [
            "핵심 지지 이탈 이후 추가 하락이 이어지지 않는다.",
            "가격이 빠르게 구조 안으로 회복하고 이탈 구간을 다시 지지한다.",
            "회복 실패 시 손절할 수 있는 좁은 구간에서만 진입한다.",
        ],
        "resistance_failure_short": [
            "저항 또는 채널 상단에서 돌파가 실패한다.",
            "직전 저점 또는 단기 지지를 이탈한 뒤 되돌림이 실패한다.",
            "무효화 가격이 직전 고점 근처로 짧게 잡힐 때만 진입한다.",
        ],
    }
    return specific.get(key, []) + common


def build_risk_algorithm(key: str) -> dict[str, Any]:
    direction = TECHNIQUE_DEFINITIONS[key]["direction"]
    return {
        "stop_basis": "LONG이면 지지선/눌림 저점/채널 하단 이탈, SHORT이면 저항선/직전 고점 회복을 무효화 기준으로 둡니다.",
        "max_stop_distance_pct": 0.45 if direction == "LONG" else 0.5,
        "min_reward_risk": 1.4,
        "position_sizing": "손절 시 계좌 손실이 0.6%를 넘지 않도록 수량을 역산합니다. 고확신 카드라도 1회 최대 1.0% 손실을 넘기지 않습니다.",
        "scale_rule": "확인 전 40%, 확인 후 60% 분할 진입을 기본으로 하며, 손절선이 멀어지면 추가 진입하지 않습니다.",
    }


def build_exit_algorithm(key: str) -> list[str]:
    if TECHNIQUE_DEFINITIONS[key]["direction"] == "LONG":
        return [
            "1차 목표는 직전 고점 또는 박스/채널 중단입니다.",
            "2차 목표는 채널 상단, 다음 저항, 또는 파동 목표 구간입니다.",
            "1차 목표 도달 후 절반 청산, 남은 수량은 진입가 또는 구조선 위로 트레일링합니다.",
            "반등 강도가 약해지고 저점이 다시 깨지면 목표 도달 전이라도 정리합니다.",
        ]
    return [
        "1차 목표는 직전 저점 또는 박스 하단입니다.",
        "2차 목표는 다음 지지 또는 하락 파동 목표 구간입니다.",
        "1차 목표 도달 후 절반 청산, 남은 수량은 진입가 또는 되돌림 고점 아래로 트레일링합니다.",
        "하락 이탈 후 바로 회복하면 목표 도달 전이라도 정리합니다.",
    ]


def build_avoid_conditions(key: str) -> list[str]:
    base = [
        "손절선이 멀어 기대 손익비가 1.4 미만이면 진입하지 않습니다.",
        "박스 중앙처럼 지지/저항 양쪽까지 거리가 애매한 위치는 진입하지 않습니다.",
        "이미 급등/급락 후 목표가에 가까운 위치에서는 추격하지 않습니다.",
        "차트 구조, 진입 트리거, 손절 근거 중 하나라도 비면 ACTIONABLE에서 제외합니다.",
    ]
    if key != "resistance_failure_short":
        base.append("상위 구조가 명확한 하락 추세이고 반등 실패가 반복되면 롱 카드는 중단합니다.")
    else:
        base.append("상위 구조가 강한 상승이고 저항 돌파 후 안착하면 숏 카드는 중단합니다.")
    return base


def build_score_formula(key: str) -> dict[str, Any]:
    weights = {
        "structure_score": 0.22,
        "trigger_score": 0.18,
        "stop_quality_score": 0.20,
        "reward_risk_score": 0.16,
        "wave_position_score": 0.10,
        "regime_score": 0.08,
        "volume_confirmation_score": 0.06,
        "chase_penalty": -0.16,
        "chop_penalty": -0.12,
    }
    if key == "wave_continuation_long":
        weights["wave_position_score"] = 0.18
        weights["volume_confirmation_score"] = 0.02
    if key in {"breakout_retest_long", "failed_breakdown_reversal_long"}:
        weights["trigger_score"] = 0.22
        weights["structure_score"] = 0.20
    return {
        "weights": weights,
        "entry_threshold": 0.72,
        "watch_threshold": 0.58,
        "hard_blocks": [
            "손절 기준 없음",
            "기대 손익비 1.4 미만",
            "스프레드/슬리피지 과다",
            "최근 3회 같은 카드 연속 손절",
        ],
    }


def build_validation_plan(key: str) -> dict[str, Any]:
    return {
        "backtest_unit": "1분/5분/15분 OHLCV에서 카드 조건이 처음 충족된 시점을 진입 후보로 기록합니다.",
        "labels": [
            "entry_time",
            "entry_price",
            "stop_price",
            "target1",
            "target2",
            "max_favorable_excursion",
            "max_adverse_excursion",
            "result_r_multiple",
        ],
        "minimum_sample": 80,
        "pass_criteria": {
            "win_rate_min": 0.46,
            "avg_r_min": 0.18,
            "profit_factor_min": 1.18,
            "max_drawdown_r_limit": -8.0,
        },
        "paper_trade_gate": "백테스트 통과 후 모의거래 50회에서 profit factor 1.1 이상일 때만 실거래 후보로 승격합니다.",
    }


def write_outputs(cards: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> None:
    payload = {
        "source_decisions": len(decisions),
        "actionable_decisions": sum(1 for d in decisions if (d.get("trade_readiness") or {}).get("level") == "ACTIONABLE"),
        "cards": cards,
    }
    STRATEGY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 매억남 기반 실전 기법 카드",
        "",
        f"- 분석 대상 decision: {payload['source_decisions']}개",
        f"- ACTIONABLE decision: {payload['actionable_decisions']}개",
        f"- 생성된 기법 카드: {len(cards)}개",
        "- 목적: 영상 요약이 아니라 실제 알고리즘 후보로 변환 가능한 매매 기법을 추출합니다.",
        "- 주의: 이 문서는 투자 조언이 아니며, 반드시 백테스트와 모의거래 검증을 통과해야 합니다.",
        "",
        "## 전체 결론",
        "",
        "- 현재까지 가장 강한 축은 지지/눌림/반등 기반 롱입니다.",
        "- 실전 알고리즘으로 쓰려면 방향보다 구조, 손절거리, 손익비, 진입 트리거를 먼저 계산해야 합니다.",
        "- ACTIONABLE이더라도 백테스트 전에는 실거래 기법이 아니라 후보 기법입니다.",
        "",
    ]
    for index, card in enumerate(cards, 1):
        lines.extend(
            [
                f"## {index}. {card['name']}",
                "",
                f"- ID: `{card['id']}`",
                f"- 방향: `{card['direction']}`",
                f"- 근거 영상 수: {card['support_count']}개",
                f"- 평균 매칭 점수: {card['avg_match_score']}",
                f"- 현재 신뢰도: {card['confidence']}",
                f"- 설명: {card['description']}",
                "",
                "### 사용 조건과 진입 알고리즘",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in card["entry_algorithm"])
        risk = card["risk_algorithm"]
        lines.extend(
            [
                "",
                "### 손절과 포지션 크기",
                "",
                f"- 손절 기준: {risk['stop_basis']}",
                f"- 최대 손절폭 기준: {risk['max_stop_distance_pct']}%",
                f"- 최소 손익비: {risk['min_reward_risk']}",
                f"- 수량 산정: {risk['position_sizing']}",
                f"- 분할 규칙: {risk['scale_rule']}",
                "",
                "### 익절과 청산",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in card["exit_algorithm"])
        lines.extend(["", "### 진입 금지 조건", ""])
        lines.extend(f"- {item}" for item in card["avoid_conditions"])
        formula = card["score_formula"]
        lines.extend(
            [
                "",
                "### 점수화 알고리즘",
                "",
                f"- 진입 임계값: {formula['entry_threshold']}",
                f"- 감시 임계값: {formula['watch_threshold']}",
                f"- 가중치: {json.dumps(formula['weights'], ensure_ascii=False)}",
                f"- 하드 블록: {', '.join(formula['hard_blocks'])}",
                "",
                "### 검증 계획",
                "",
                f"- 단위: {card['validation_plan']['backtest_unit']}",
                f"- 최소 표본: {card['validation_plan']['minimum_sample']}",
                f"- 통과 기준: {json.dumps(card['validation_plan']['pass_criteria'], ensure_ascii=False)}",
                f"- 모의거래 승격 조건: {card['validation_plan']['paper_trade_gate']}",
                "",
                "### 대표 근거 영상",
                "",
            ]
        )
        for example in card["examples"]:
            lines.append(f"- {example['title']} ({example['url']}) match={example['match_score']}")
            for evidence in example["evidence"][:3]:
                lines.append(f"  - {evidence['time']} [{evidence['section']}]: {evidence['text']}")
        lines.append("")
    STRATEGY_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-cards", type=int, default=1)
    args = parser.parse_args()
    decisions = load_decisions()
    cards = build_cards(decisions)
    if len(cards) < args.min_cards:
        raise SystemExit(f"only built {len(cards)} cards")
    write_outputs(cards, decisions)
    print(json.dumps({"decisions": len(decisions), "cards": len(cards), "report": str(STRATEGY_REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
