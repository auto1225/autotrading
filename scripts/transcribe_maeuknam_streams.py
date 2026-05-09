from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from maeuknam_decision_analysis import build_decision_analysis, write_decision_json, write_decision_report
from maeuknam_strategy_extraction import build_cards, load_decisions, write_outputs


ROOT = Path(__file__).resolve().parents[1]
PLAYLIST_FILE = ROOT / "maeuknam_streams_flat.json"
AUDIO_DIR = ROOT / "reports" / "maeuknam_audio"
TRANSCRIPT_DIR = ROOT / "reports" / "maeuknam_transcripts"
ANALYSIS_DIR = ROOT / "reports" / "maeuknam_video_analysis"
COMBINED_REPORT = ROOT / "reports" / "maeuknam_video_content_analysis.md"

KEYWORD_GROUPS: dict[str, list[str]] = {
    "market_bias": ["상승장", "하락장", "롱", "숏", "롱을", "숏을", "포지션", "추격 롱", "추격 숏"],
    "entry": ["진입", "들어가", "매수", "매도", "떨어질 때", "올라올 때", "눌림", "반등", "뚫고"],
    "risk": ["손절", "손절선", "손절 라인", "스탑", "본절", "익절", "수익", "리스크"],
    "structure": ["고점", "저점", "지지", "저항", "라인", "채널", "추세", "뚫고", "이탈"],
    "wave": ["파동", "상승파", "하락파", "3파", "5파", "조정", "abc", "사이클"],
    "macro": ["비트코인", "기관", "고래", "나스닥", "달러", "금리", "ETF", "자금"],
}
ALL_KEYWORDS = sorted({keyword for values in KEYWORD_GROUPS.values() for keyword in values}, key=len, reverse=True)


def read_playlist() -> list[dict[str, Any]]:
    try:
        payload = json.loads(PLAYLIST_FILE.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        payload = json.loads(PLAYLIST_FILE.read_text(encoding="utf-16"))
    return [entry for entry in payload.get("entries", []) if isinstance(entry, dict)]


def video_url(entry: dict[str, Any]) -> str:
    return str(entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}")


def audio_path(video_id: str) -> Path:
    existing = sorted(AUDIO_DIR.glob(f"{video_id}.*"))
    if existing:
        return existing[0]
    return AUDIO_DIR / f"{video_id}.m4a"


def transcript_json_path(video_id: str, model_name: str) -> Path:
    safe_model = model_name.replace("/", "_")
    return TRANSCRIPT_DIR / f"{video_id}.{safe_model}.ko.json"


def transcript_txt_path(video_id: str, model_name: str) -> Path:
    safe_model = model_name.replace("/", "_")
    return TRANSCRIPT_DIR / f"{video_id}.{safe_model}.ko.txt"


def download_audio(entry: dict[str, Any]) -> Path:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    video_id = str(entry["id"])
    path = audio_path(video_id)
    if path.exists() and path.stat().st_size > 0:
        return path
    output_template = str(AUDIO_DIR / "%(id)s.%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "140/bestaudio[ext=m4a]/bestaudio",
        "--no-playlist",
        "-o",
        output_template,
        video_url(entry),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    path = audio_path(video_id)
    if not path.exists():
        raise FileNotFoundError(f"audio download missing for {video_id}")
    return path


def transcribe_audio(model: WhisperModel, entry: dict[str, Any], model_name: str) -> dict[str, Any]:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    video_id = str(entry["id"])
    json_path = transcript_json_path(video_id, model_name)
    txt_path = transcript_txt_path(video_id, model_name)
    if json_path.exists():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        payload.setdefault("id", video_id)
        payload.setdefault("title", entry.get("title"))
        payload.setdefault("url", video_url(entry))
        payload.setdefault("duration", entry.get("duration"))
        payload.setdefault("model", model_name)
        return payload
    path = download_audio(entry)
    started = time.time()
    segments_iter, info = model.transcribe(
        str(path),
        language="ko",
        vad_filter=True,
        beam_size=1,
    )
    segments = [
        {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": segment.text.strip()}
        for segment in segments_iter
    ]
    payload = {
        "id": video_id,
        "title": entry.get("title"),
        "url": video_url(entry),
        "duration": getattr(info, "duration", entry.get("duration")),
        "language": getattr(info, "language", "ko"),
        "model": model_name,
        "elapsed_seconds": round(time.time() - started, 1),
        "segments": segments,
    }
    txt_path.write_text(
        "\n".join(f"[{row['start']:.2f}-{row['end']:.2f}] {row['text']}" for row in segments),
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def count_keywords(text: str) -> tuple[Counter[str], Counter[str]]:
    term_counts: Counter[str] = Counter()
    for keyword in ALL_KEYWORDS:
        count = text.count(keyword)
        if count:
            term_counts[keyword] = count
    group_counts: Counter[str] = Counter()
    for group, keywords in KEYWORD_GROUPS.items():
        group_counts[group] = sum(term_counts[keyword] for keyword in keywords)
    return term_counts, group_counts


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{sec:02d}"


def extract_evidence(segments: list[dict[str, Any]], max_items: int = 12) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text") or "")
        score = sum(text.count(keyword) for keyword in ALL_KEYWORDS)
        if score <= 0:
            continue
        context = " ".join(
            str(row.get("text") or "")
            for row in segments[max(0, index - 1) : min(len(segments), index + 2)]
        )
        scored.append(
            (
                score,
                {
                    "time": format_time(float(segment.get("start") or 0)),
                    "start": segment.get("start"),
                    "text": re.sub(r"\s+", " ", context).strip(),
                },
            )
        )
    scored.sort(key=lambda row: (row[0], row[1]["start"]), reverse=True)
    evidence: list[dict[str, Any]] = []
    seen = set()
    for _, row in scored:
        minute_bucket = int(float(row["start"] or 0) // 90)
        if minute_bucket in seen:
            continue
        seen.add(minute_bucket)
        evidence.append(row)
        if len(evidence) >= max_items:
            break
    return evidence


def infer_rules(group_counts: Counter[str], term_counts: Counter[str]) -> list[str]:
    rules: list[str] = []
    if group_counts["market_bias"] and term_counts["롱"] >= term_counts["숏"]:
        rules.append("롱/상승 시나리오 비중이 높다. 하락 추격 숏보다 눌림 롱 또는 반등 롱을 먼저 검토한다.")
    elif group_counts["market_bias"]:
        rules.append("숏/하락 시나리오 비중이 높다. 상승 실패와 저항 재확인을 숏 조건으로 본다.")
    if group_counts["risk"] >= 3:
        rules.append("진입보다 손절선 산정이 먼저다. 손절선이 멀면 추격 진입의 품질을 낮춘다.")
    if group_counts["structure"] >= 5:
        rules.append("고점/저점, 지지/저항, 채널 돌파 여부를 구조 필터로 사용한다.")
    if group_counts["wave"] >= 3:
        rules.append("상승파/조정파 같은 파동 위치를 시나리오 필터로 사용한다.")
    if group_counts["macro"] >= 3:
        rules.append("기관/고래/자금 흐름 같은 거시 맥락을 방향 필터로 보조 반영한다.")
    if not rules:
        rules.append("매매 규칙 추출에 충분한 신호가 적다. 이 영상은 전략 학습 우선순위를 낮춘다.")
    return rules


def analyze_transcript(payload: dict[str, Any]) -> dict[str, Any]:
    segments = payload.get("segments") or []
    text = " ".join(str(segment.get("text") or "") for segment in segments)
    term_counts, group_counts = count_keywords(text)
    decision_analysis = build_decision_analysis(payload)
    return {
        "id": payload["id"],
        "title": payload.get("title"),
        "url": payload.get("url"),
        "duration": payload.get("duration"),
        "model": payload.get("model"),
        "term_counts": dict(term_counts.most_common(30)),
        "group_counts": dict(group_counts),
        "evidence": extract_evidence(segments),
        "rules": infer_rules(group_counts, term_counts),
        "decision_analysis": decision_analysis,
    }


def write_combined_report(analyses: list[dict[str, Any]]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 매억남 영상 실제 내용 분석",
        "",
        f"- 분석 완료 영상: {len(analyses)}개",
        "- 방식: YouTube 오디오 다운로드 -> 로컬 faster-whisper STT -> 매매 키워드/규칙 추출",
        "- 주의: STT는 자동 전사라 일부 오인식이 있으며, 원문 전체를 답변에 복제하지 않는다.",
        "",
    ]
    aggregate_groups: Counter[str] = Counter()
    aggregate_terms: Counter[str] = Counter()
    for analysis in analyses:
        aggregate_groups.update(analysis.get("group_counts", {}))
        aggregate_terms.update(analysis.get("term_counts", {}))
    lines.extend(
        [
            "## 전체 키워드 요약",
            "",
            "| 그룹 | 횟수 |",
            "|---|---:|",
        ]
    )
    for group, count in aggregate_groups.most_common():
        lines.append(f"| {group} | {count} |")
    lines.extend(["", "## 상위 용어", "", ", ".join(f"{term}({count})" for term, count in aggregate_terms.most_common(20)), ""])
    for index, analysis in enumerate(analyses, 1):
        lines.extend(
            [
                f"## {index}. {analysis.get('title')}",
                "",
                f"- URL: {analysis.get('url')}",
                f"- 길이: {round(float(analysis.get('duration') or 0) / 60, 1)}분",
                f"- 그룹 카운트: {json.dumps(analysis.get('group_counts'), ensure_ascii=False)}",
                "",
                "### 추출 규칙",
                "",
            ]
        )
        lines.extend(f"- {rule}" for rule in analysis.get("rules", []))
        lines.extend(["", "### 근거 구간", ""])
        for item in analysis.get("evidence", [])[:8]:
            snippet = str(item.get("text") or "")
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            lines.append(f"- {item.get('time')}: {snippet}")
        lines.append("")
    COMBINED_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--delete-audio-after", action="store_true")
    args = parser.parse_args()
    entries = read_playlist()[args.start : args.start + args.limit]
    if not entries:
        raise SystemExit("no entries selected")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"loading whisper model {args.model}")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    analyses = []
    for number, entry in enumerate(entries, 1):
        print(f"[{number}/{len(entries)}] {entry.get('id')} {entry.get('title')}")
        payload = transcribe_audio(model, entry, args.model)
        analysis = analyze_transcript(payload)
        analyses.append(analysis)
        path = ANALYSIS_DIR / f"{analysis['id']}.analysis.json"
        path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        write_decision_json(analysis["decision_analysis"])
        print(f"  groups={analysis['group_counts']}")
        if args.delete_audio_after:
            path = audio_path(str(entry["id"]))
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        existing = []
        for path in sorted(ANALYSIS_DIR.glob("*.analysis.json")):
            existing.append(json.loads(path.read_text(encoding="utf-8")))
        write_combined_report(existing)
        write_decision_report(
            [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(ANALYSIS_DIR.glob("*.decision.json"))
            ]
        )
        decisions = load_decisions()
        write_outputs(build_cards(decisions), decisions)
    existing = []
    for path in sorted(ANALYSIS_DIR.glob("*.analysis.json")):
        existing.append(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps({"completed_this_run": len(analyses), "total_reports": len(existing), "report": str(COMBINED_REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
