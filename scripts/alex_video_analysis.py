from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ALEX_VIDEO_DIR = ROOT / "reports" / "alex_video"
ALEX_TRANSCRIPT_DIR = ROOT / "reports" / "alex_transcripts"
ALEX_FRAME_DIR = ROOT / "reports" / "alex_chart_frames"
ALEX_ANALYSIS_DIR = ROOT / "reports" / "alex_analysis"


DEFAULT_VIDEO_ID = "6fEhvy7mREc"


GROUP_PATTERNS: dict[str, list[str]] = {
    "liquidity_map": ["유동성", "롱쇼", "롱숏", "롱.*숏", "스마트머니", "스마트니", "마켓", "POI", "관전"],
    "value_zone": ["0\\.5", "평균", "디스카운", "프리미엄", "할인", "비싼"],
    "entry_trigger": ["진입", "포지션", "진입 기회", "알람", "체크리스트", "주문"],
    "four_count_confirmation": ["하나\\s*둘", "둘\\s*셋", "셋\\s*넷", "넷을\\s*기다", "네\\s*번째"],
    "risk_invalidation": ["손절", "스탑", "깨지", "반전", "박스권", "무효"],
    "session_timeframe": ["12시간", "30분", "9시", "세션", "캔들", "오전", "오후", "원데이", "한시간"],
}


@dataclass(frozen=True)
class TranscriptLine:
    start: float
    time: str
    text: str


def seconds_to_time(seconds: float) -> str:
    total = max(int(seconds), 0)
    minutes, sec = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{sec:02d}"


def parse_timecode(value: str) -> float:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minute, second = parts
        return minute * 60 + second
    if len(parts) == 3:
        hour, minute, second = parts
        return hour * 3600 + minute * 60 + second
    raise ValueError(f"invalid timecode: {value}")


def video_dir(video_id: str) -> Path:
    return ALEX_VIDEO_DIR / video_id


def info_path(video_id: str) -> Path:
    return video_dir(video_id) / f"{video_id}.info.json"


def json3_path(video_id: str) -> Path:
    return video_dir(video_id) / f"{video_id}.ko.json3"


def video_path(video_id: str) -> Path:
    candidates = sorted(video_dir(video_id).glob(f"{video_id}.*"))
    for candidate in candidates:
        if candidate.suffix.lower() in {".mp4", ".mkv", ".webm"}:
            return candidate
    raise FileNotFoundError(f"video file not found for {video_id}")


def parse_json3(video_id: str) -> list[TranscriptLine]:
    data = json.loads(json3_path(video_id).read_text(encoding="utf-8"))
    lines: list[TranscriptLine] = []
    for event in data.get("events", []):
        segments = event.get("segs") or []
        text = "".join(str(seg.get("utf8") or "") for seg in segments)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        start = float(event.get("tStartMs") or 0) / 1000.0
        lines.append(TranscriptLine(start=start, time=seconds_to_time(start), text=text))
    return lines


def write_transcript(video_id: str, lines: list[TranscriptLine]) -> Path:
    ALEX_TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    output = ALEX_TRANSCRIPT_DIR / f"{video_id}.transcript.txt"
    body = "\n".join(f"{line.time} {line.text}" for line in lines)
    output.write_text(body + "\n", encoding="utf-8")
    return output


def load_transcript(video_id: str) -> list[TranscriptLine]:
    path = ALEX_TRANSCRIPT_DIR / f"{video_id}.transcript.txt"
    if not path.exists():
        return parse_json3(video_id)
    lines: list[TranscriptLine] = []
    pattern = re.compile(r"^(\d{2}:\d{2}(?::\d{2})?)\s+(.*)$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw)
        if not match:
            continue
        timecode, text = match.groups()
        lines.append(TranscriptLine(start=parse_timecode(timecode), time=seconds_to_time(parse_timecode(timecode)), text=text))
    return lines


def compact_snippet(text: str, limit: int = 44) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def collect_evidence(lines: list[TranscriptLine]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        categories = [
            category
            for category, patterns in GROUP_PATTERNS.items()
            if any(re.search(pattern, line.text, flags=re.IGNORECASE) for pattern in patterns)
        ]
        if not categories:
            continue
        prev_text = lines[index - 1].text if index > 0 else ""
        next_text = lines[index + 1].text if index + 1 < len(lines) else ""
        joined = " ".join(part for part in [prev_text, line.text, next_text] if part)
        evidence.append(
            {
                "start": round(line.start, 3),
                "time": line.time,
                "categories": categories,
                "snippet": compact_snippet(line.text),
                "context_snippet": compact_snippet(joined, limit=72),
            }
        )
    return evidence


def select_frame_times(evidence: list[dict[str, Any]], duration: int, max_frames: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used_seconds: set[int] = set()

    def add(item: dict[str, Any], reason: str) -> None:
        second = int(float(item["start"]) + 1.0)
        if second < 0 or second > duration:
            return
        bucket = second // 8
        if bucket in used_seconds:
            return
        used_seconds.add(bucket)
        selected.append(
            {
                "second": float(second),
                "time": seconds_to_time(second),
                "reason": reason,
                "categories": item.get("categories", []),
                "snippet": item.get("snippet", ""),
            }
        )

    # Pick representative frames across the chart explanation, not only the intro.
    priority_windows = [
        (0, 40, "four_count_confirmation", "intro-4-count"),
        (200, 360, "value_zone", "0.5-value-zone"),
        (240, 330, "risk_invalidation", "stop-zone"),
        (450, 540, "four_count_confirmation", "4-count-entry"),
        (480, 560, "entry_trigger", "entry-example"),
        (620, 720, "liquidity_map", "liquidity-checklist"),
        (660, 730, "four_count_confirmation", "checklist-4-count"),
        (850, 980, "session_timeframe", "session-timeframe"),
        (900, 1000, "entry_trigger", "session-entry"),
        (1060, duration + 1, "value_zone", "0.5-wrap-up"),
    ]
    for start, end, category, reason in priority_windows:
        for item in evidence:
            second = float(item.get("start") or 0)
            if start <= second <= end and category in item.get("categories", []):
                add(item, reason)
                break

    # Fill remaining slots with chart-heavy evidence after the interview intro.
    for item in evidence:
        if float(item.get("start") or 0) < 180:
            continue
        categories = set(item.get("categories", []))
        if {"entry_trigger", "four_count_confirmation", "value_zone", "session_timeframe"} & categories:
            if any(abs(float(item["start"]) - float(existing["second"])) < 35 for existing in selected):
                continue
            add(item, "timeline-evidence")
        if len(selected) >= max_frames:
            break

    selected.sort(key=lambda item: float(item["second"]))
    return selected[:max_frames]


def frame_metrics(frame: Any) -> dict[str, float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 180)
    edge_density = float((edges > 0).sum()) / float(edges.size)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = float(hsv[:, :, 1].mean()) / 255.0
    brightness = float(gray.mean()) / 255.0
    return {
        "edgeDensity": round(edge_density, 4),
        "saturation": round(saturation, 4),
        "brightness": round(brightness, 4),
    }


def extract_frame(capture: cv2.VideoCapture, second: float, output: Path) -> dict[str, float] | None:
    fps = capture.get(cv2.CAP_PROP_FPS) or 30
    capture.set(cv2.CAP_PROP_POS_FRAMES, max(int(second * fps), 0))
    ok, frame = capture.read()
    if not ok or frame is None:
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = frame_metrics(frame)
    encoded_ok, encoded = cv2.imencode(".jpg", frame)
    if not encoded_ok:
        return None
    output.write_bytes(encoded.tobytes())
    return metrics


def make_contact_sheet(video_id: str, frames: list[dict[str, Any]]) -> Path:
    images: list[tuple[Image.Image, dict[str, Any]]] = []
    for item in frames:
        path = Path(item["path"])
        if path.exists():
            images.append((Image.open(path).convert("RGB"), item))
    if not images:
        raise FileNotFoundError("no extracted Alex frames")

    thumb_width = 380
    label_height = 72
    columns = 2
    rows = math.ceil(len(images) / columns)
    thumb_height = int(images[0][0].height * thumb_width / images[0][0].width)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "#f8fafc")
    draw = ImageDraw.Draw(sheet)
    title_font, small_font = load_korean_fonts()

    for index, (image, item) in enumerate(images):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        thumb = image.resize((thumb_width, thumb_height))
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y + thumb_height, x + thumb_width, y + thumb_height + label_height), fill="#ffffff")
        title = f"{item['time']} | {item.get('reason', '')}"
        snippet = str(item.get("snippet") or "")
        metrics = item.get("metrics") or {}
        metric_text = f"edge {metrics.get('edgeDensity', 0)} / sat {metrics.get('saturation', 0)}"
        draw.text((x + 8, y + thumb_height + 7), title, fill="#0f172a", font=title_font)
        draw.text((x + 8, y + thumb_height + 32), compact_snippet(snippet, 42), fill="#334155", font=small_font)
        draw.text((x + 8, y + thumb_height + 52), metric_text, fill="#64748b", font=small_font)

    output = ALEX_FRAME_DIR / f"{video_id}_contact_sheet.jpg"
    sheet.save(output, quality=92)
    return output


def load_korean_fonts() -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("C:/Windows/Fonts/NanumGothic.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), 16), ImageFont.truetype(str(candidate), 12)
    return ImageFont.load_default(), ImageFont.load_default()


def extract_chart_frames(video_id: str, evidence: list[dict[str, Any]], max_frames: int) -> dict[str, Any]:
    info = json.loads(info_path(video_id).read_text(encoding="utf-8"))
    duration = int(info.get("duration") or 0)
    selected = select_frame_times(evidence, duration, max_frames=max_frames)
    capture = cv2.VideoCapture(str(video_path(video_id)))
    if not capture.isOpened():
        raise RuntimeError(f"could not open Alex video: {video_path(video_id)}")
    frames: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        second = float(item["second"])
        output = ALEX_FRAME_DIR / video_id / f"{index:02d}_{int(second):06d}.jpg"
        metrics = extract_frame(capture, second, output)
        if metrics is None:
            continue
        frames.append({**item, "path": str(output), "metrics": metrics})
    capture.release()
    contact_sheet = make_contact_sheet(video_id, frames)
    payload = {
        "id": video_id,
        "title": info.get("title"),
        "url": info.get("webpage_url"),
        "frames": frames,
        "contact_sheet": str(contact_sheet),
    }
    ALEX_FRAME_DIR.mkdir(parents=True, exist_ok=True)
    (ALEX_FRAME_DIR / f"{video_id}_frames.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def first_times(evidence: list[dict[str, Any]], category: str, limit: int = 4) -> list[str]:
    times: list[str] = []
    for item in evidence:
        if category in item.get("categories", []):
            times.append(str(item["time"]))
        if len(times) >= limit:
            break
    return times


def build_strategy_cards(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "alex_liquidity_discount_long",
            "method": "알렉스 매매기법",
            "direction": "LONG",
            "title": "상승 추세 0.5 디스카운트 롱",
            "timeframes": ["HTF trend range", "30m/low timeframe confirmation"],
            "entry": [
                "고점과 저점이 높아지는 상승 구조를 먼저 확인한다.",
                "직전 의미 있는 저점-고점 범위의 0.5 평균값을 긋고, 0.5 이하 디스카운트 구간을 기다린다.",
                "하락 유동성 소진 또는 저점 훼손 실패 후 1-2-3 구조가 보이면 네 번째 확인에서만 진입한다.",
            ],
            "stop": [
                "네 번째 확인을 만든 저점 또는 디스카운트 구간 하단이 깨지면 무효화한다.",
                "0.5를 맞히려는 선진입은 금지하고, 구조가 박스권으로 바뀌면 즉시 후보에서 제외한다.",
            ],
            "takeProfit": [
                "1차 목표는 직전 고점 또는 위쪽 유동성 구간이다.",
                "강한 추세가 유지되면 프리미엄 구간의 다음 유동성까지 일부를 끌고 간다.",
            ],
            "forbidden": [
                "0.5 터치만으로 진입하지 않는다.",
                "상단 유동성 목표가 수수료와 슬리피지를 덮지 못하면 진입하지 않는다.",
                "세 번째 확인 전에는 추격 진입하지 않는다.",
            ],
            "evidenceTimes": sorted(set(first_times(evidence, "value_zone") + first_times(evidence, "four_count_confirmation"))),
        },
        {
            "id": "alex_liquidity_premium_short",
            "method": "알렉스 매매기법",
            "direction": "SHORT",
            "title": "하락 추세 0.5 프리미엄 숏",
            "timeframes": ["HTF trend range", "30m/low timeframe confirmation"],
            "entry": [
                "저점과 고점이 낮아지는 하락 구조를 먼저 확인한다.",
                "직전 의미 있는 고점-저점 범위의 0.5 평균값을 긋고, 0.5 이상 프리미엄 구간을 기다린다.",
                "상단 유동성 흡수 또는 고점 돌파 실패 후 1-2-3 구조가 보이면 네 번째 확인에서만 진입한다.",
            ],
            "stop": [
                "네 번째 확인을 만든 고점 또는 프리미엄 구간 상단이 깨지면 무효화한다.",
                "프리미엄 구간 안에서도 박스권 전환이면 숏 후보를 취소한다.",
            ],
            "takeProfit": [
                "1차 목표는 직전 저점 또는 아래쪽 유동성 구간이다.",
                "하락 추세가 유지되면 디스카운트 구간의 다음 유동성까지 일부를 끌고 간다.",
            ],
            "forbidden": [
                "프리미엄 도달만으로 진입하지 않는다.",
                "아래쪽 유동성 목표가 비용보다 작으면 진입하지 않는다.",
                "네 번째 확인 없이 반대매매 예측으로 진입하지 않는다.",
            ],
            "evidenceTimes": sorted(set(first_times(evidence, "value_zone") + first_times(evidence, "risk_invalidation"))),
        },
        {
            "id": "alex_session_open_manipulation",
            "method": "알렉스 매매기법",
            "direction": "BOTH",
            "title": "세션 오픈 조작 후 4카운트 진입",
            "timeframes": ["12h session candle", "30m execution"],
            "entry": [
                "세션 오픈 전후의 12시간 기준 범위를 잡고, 30분 단위에서 움직임을 관찰한다.",
                "초반 흔들림이 위 또는 아래 유동성을 건드린 뒤 원래 구조로 복귀하는지 확인한다.",
                "방향은 미리 고정하지 않고, 복귀 방향의 1-2-3 뒤 네 번째 확인에서 진입한다.",
            ],
            "stop": [
                "세션 조작으로 판단한 꼬리 또는 복귀 실패 지점이 깨지면 무효화한다.",
                "오픈 직후 변동성만 보고 바로 진입하지 않는다.",
            ],
            "takeProfit": [
                "첫 목표는 반대편 유동성 또는 0.5 평균값이다.",
                "반대편까지 도달한 뒤에는 잔여 물량만 다음 유동성으로 넘긴다.",
            ],
            "forbidden": [
                "세션 시간만 맞았다고 진입하지 않는다.",
                "유동성, 0.5 구간, 4카운트 중 하나라도 없으면 관찰만 한다.",
            ],
            "evidenceTimes": sorted(set(first_times(evidence, "session_timeframe") + first_times(evidence, "liquidity_map"))),
        },
    ]


def build_analysis(video_id: str, lines: list[TranscriptLine], evidence: list[dict[str, Any]], frames: dict[str, Any]) -> dict[str, Any]:
    info = json.loads(info_path(video_id).read_text(encoding="utf-8"))
    cards = build_strategy_cards(evidence)
    return {
        "methodName": "알렉스 매매기법",
        "methodSubtitle": "0.5 평균값 + 유동성 + 하나둘셋넷 확인법",
        "status": "single-video-first-pass",
        "source": {
            "id": video_id,
            "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "uploadDate": info.get("upload_date"),
            "durationSeconds": info.get("duration"),
            "url": info.get("webpage_url"),
        },
        "artifacts": {
            "transcript": str(ALEX_TRANSCRIPT_DIR / f"{video_id}.transcript.txt"),
            "framesJson": str(ALEX_FRAME_DIR / f"{video_id}_frames.json"),
            "contactSheet": frames.get("contact_sheet"),
        },
        "counts": {
            "transcriptLines": len(lines),
            "evidenceItems": len(evidence),
            "chartFrames": len(frames.get("frames", [])),
        },
        "coreRules": [
            "방향은 롱/숏을 미리 고정하지 않고, 상위 구조와 유동성 위치로 결정한다.",
            "0.5 평균값은 추세 범위의 기준선이며 상승 추세에서는 디스카운트, 하락 추세에서는 프리미엄 대기 구간으로 사용한다.",
            "진입은 1-2-3을 확인한 뒤 네 번째 신호까지 기다리는 방식으로 제한한다.",
            "손절은 0.5 자체가 아니라 진입 근거가 된 구조의 무효화 지점에 둔다.",
            "세션 오픈과 12시간/30분 구조는 조작 움직임을 추적하는 보조 필터로 쓴다.",
        ],
        "strategyCards": cards,
        "evidence": evidence,
    }


def write_strategy_cards(cards: list[dict[str, Any]]) -> Path:
    ALEX_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    output = ALEX_ANALYSIS_DIR / "alex_strategy_cards.json"
    output.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_markdown(video_id: str, analysis: dict[str, Any]) -> Path:
    source = analysis["source"]
    counts = analysis["counts"]
    cards = analysis["strategyCards"]
    evidence = analysis["evidence"]

    def evidence_lines(category: str, limit: int = 6) -> list[str]:
        rows = [item for item in evidence if category in item.get("categories", [])][:limit]
        return [f"- {item['time']} `{item['snippet']}`" for item in rows]

    lines: list[str] = [
        "# 알렉스 매매기법",
        "",
        f"- 영상: {source.get('title')}",
        f"- 채널: {source.get('channel')}",
        f"- URL: {source.get('url')}",
        f"- 상태: 단일 영상 1차 분석. 자동자막 기반이므로 차트 프레임 검수 후 규칙을 더 조정해야 합니다.",
        f"- 분석량: 자막 {counts['transcriptLines']}줄, 근거 타임스탬프 {counts['evidenceItems']}개, 차트 프레임 {counts['chartFrames']}장",
        "",
        "## 핵심 결론",
        "",
        "알렉스 매매기법은 방향을 미리 정하는 방식이 아니라, 상위 추세 범위의 0.5 평균값과 유동성 위치를 먼저 정한 뒤 1-2-3 구조 다음 네 번째 확인에서 진입하는 방식으로 정리됩니다.",
        "",
        "## 실행 규칙",
        "",
    ]
    for rule in analysis["coreRules"]:
        lines.append(f"- {rule}")

    lines.extend(["", "## 전략 카드", ""])
    for card in cards:
        lines.extend(
            [
                f"### {card['title']}",
                "",
                f"- 방향: {card['direction']}",
                f"- 타임프레임: {', '.join(card['timeframes'])}",
                f"- 진입: {' / '.join(card['entry'])}",
                f"- 손절/무효화: {' / '.join(card['stop'])}",
                f"- 익절: {' / '.join(card['takeProfit'])}",
                f"- 금지: {' / '.join(card['forbidden'])}",
                f"- 근거 시간: {', '.join(card['evidenceTimes'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## 영상 근거 타임라인",
            "",
            "### 0.5 평균값/프리미엄/디스카운트",
            *evidence_lines("value_zone"),
            "",
            "### 하나둘셋넷 확인",
            *evidence_lines("four_count_confirmation"),
            "",
            "### 유동성/롱숏 위치",
            *evidence_lines("liquidity_map"),
            "",
            "### 손절/무효화",
            *evidence_lines("risk_invalidation"),
            "",
            "### 세션/타임프레임",
            *evidence_lines("session_timeframe"),
            "",
            "## 다음 작업",
            "",
            "- 추출된 차트 프레임에서 실제 표시 도구와 가격 구간을 검수한다.",
            "- BTCUSDT/ETHUSDT 1분, 5분, 30분, 12시간 데이터로 0.5 평균값 재진입 후보를 백테스트한다.",
            "- 실거래가 아니라 모의거래에서만 검증하고, Maeuknam 카드와 섞지 않는다.",
        ]
    )
    output = ALEX_ANALYSIS_DIR / f"{video_id}.alex_trading_method.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run(video_id: str, max_frames: int) -> dict[str, Any]:
    if not info_path(video_id).exists():
        raise FileNotFoundError(f"missing info json: {info_path(video_id)}")
    if not json3_path(video_id).exists():
        raise FileNotFoundError(f"missing Korean auto caption json3: {json3_path(video_id)}")
    lines = load_transcript(video_id)
    transcript = write_transcript(video_id, lines)
    evidence = collect_evidence(lines)
    frames = extract_chart_frames(video_id, evidence, max_frames=max_frames)
    analysis = build_analysis(video_id, lines, evidence, frames)
    ALEX_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    analysis_path = ALEX_ANALYSIS_DIR / f"{video_id}.analysis.json"
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    cards_path = write_strategy_cards(analysis["strategyCards"])
    markdown_path = write_markdown(video_id, analysis)
    return {
        "analysis": str(analysis_path),
        "methodReport": str(markdown_path),
        "strategyCards": str(cards_path),
        "transcript": str(transcript),
        "frames": frames.get("frames", []),
        "contactSheet": frames.get("contact_sheet"),
        "counts": analysis["counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Alex trading method from a YouTube transcript and chart frames.")
    parser.add_argument("--video-id", default=DEFAULT_VIDEO_ID)
    parser.add_argument("--max-frames", type=int, default=14)
    args = parser.parse_args()
    payload = run(args.video_id, max_frames=args.max_frames)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
