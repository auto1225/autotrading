from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "reports" / "maeuknam_video"
ANALYSIS_DIR = ROOT / "reports" / "maeuknam_video_analysis"
FRAME_DIR = ROOT / "reports" / "maeuknam_chart_frames"


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{sec:02d}"


def read_analysis(video_id: str) -> dict[str, Any]:
    path = ANALYSIS_DIR / f"{video_id}.analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def video_path(video_id: str) -> Path:
    candidates = sorted(VIDEO_DIR.glob(f"{video_id}.*"))
    if not candidates:
        raise FileNotFoundError(f"video file not found for {video_id}")
    return candidates[0]


def download_video(video_id: str, url: str) -> Path:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(VIDEO_DIR.glob(f"{video_id}.*"))
    if existing:
        return existing[0]
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "134/18",
        "--no-playlist",
        "-o",
        str(VIDEO_DIR / "%(id)s.%(ext)s"),
        url,
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return video_path(video_id)


def extract_frame(capture: cv2.VideoCapture, second: float, output: Path) -> bool:
    fps = capture.get(cv2.CAP_PROP_FPS) or 30
    capture.set(cv2.CAP_PROP_POS_FRAMES, max(int(second * fps), 0))
    ok, frame = capture.read()
    if not ok or frame is None:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        return False
    output.write_bytes(encoded.tobytes())
    return True


def make_contact_sheet(video_id: str, frames: list[dict[str, Any]]) -> Path:
    images: list[tuple[Image.Image, dict[str, Any]]] = []
    for item in frames:
        path = Path(item["path"])
        if path.exists():
            images.append((Image.open(path).convert("RGB"), item))
    if not images:
        raise FileNotFoundError("no extracted frames")
    thumb_width = 360
    label_height = 58
    columns = 2
    rows = (len(images) + columns - 1) // columns
    thumb_height = int(images[0][0].height * thumb_width / images[0][0].width)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("malgun.ttf", 15)
        small_font = ImageFont.truetype("malgun.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    for index, (image, item) in enumerate(images):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        thumb = image.resize((thumb_width, thumb_height))
        sheet.paste(thumb, (x, y))
        label = f"{item['time']} | {item.get('reason', '')}"
        text = str(item.get("text") or "")
        if len(text) > 48:
            text = text[:45] + "..."
        draw.text((x + 6, y + thumb_height + 5), label, fill=(0, 0, 0), font=font)
        draw.text((x + 6, y + thumb_height + 29), text, fill=(50, 50, 50), font=small_font)
    output = FRAME_DIR / f"{video_id}_contact_sheet.jpg"
    sheet.save(output, quality=92)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--max-frames", type=int, default=8)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--delete-video-after", action="store_true")
    args = parser.parse_args()
    analysis = read_analysis(args.video_id)
    path = download_video(args.video_id, str(analysis.get("url") or "")) if args.download else video_path(args.video_id)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError("could not open video")
    selected: list[dict[str, Any]] = []
    for item in analysis.get("evidence", [])[: args.max_frames]:
        center = float(item.get("start") or 0)
        # Use a frame just after the spoken evidence starts, when the chart annotation is usually visible.
        second = center + 1.0
        output = FRAME_DIR / args.video_id / f"{int(second):06d}.jpg"
        if extract_frame(capture, second, output):
            selected.append(
                {
                    "second": second,
                    "time": format_time(second),
                    "path": str(output),
                    "reason": "evidence-frame",
                    "text": item.get("text"),
                }
            )
    capture.release()
    sheet = make_contact_sheet(args.video_id, selected)
    payload = {
        "id": args.video_id,
        "title": analysis.get("title"),
        "url": analysis.get("url"),
        "frames": selected,
        "contact_sheet": str(sheet),
    }
    (FRAME_DIR / f"{args.video_id}_frames.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.delete_video_after:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
